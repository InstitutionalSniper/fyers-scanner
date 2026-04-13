import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from fyers_apiv3 import fyersModel
from fyers_apiv3.fyersModel import SessionModel

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(layout="wide", page_title="TERMINAL ALPHA v3")
CLIENT_ID = "7PHDU5GN1H-100"  
SECRET_KEY = "8JXSML4ARB"
REDIRECT_URI = "https://google.com" 

# CSS for Scrolling Ticker and Terminal Look
st.markdown("""
    <style>
    .ticker-wrapper { background: #1a1a2e; color: #00ff00; padding: 10px; overflow: hidden; border-bottom: 2px solid #333; }
    .ticker { display: inline-block; white-space: nowrap; animation: ticker 30s linear infinite; font-weight: bold; font-size: 18px; }
    @keyframes ticker { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    .stApp { background: #0b0e14; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FIXED GOOGLE URL LOGIN SYSTEM ---
def get_fyers_instance():
    if 'access_token' not in st.session_state:
        with st.sidebar:
            st.header("🔑 SECURE LOGIN")
            session = SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
            auth_url = session.generate_authcode()
            
            st.markdown(f'''<a href="{auth_url}" target="_blank"><button style="width:100%; height:50px; background: #ED1C24; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold;">1. LOGIN WITH FYERS</button></a>''', unsafe_allow_html=True)
            st.write("---")
            
            # Full Google URL Paste Box
            full_google_url = st.text_area("2. PASTE FULL GOOGLE URL HERE", height=100, placeholder="https://google.com...")
            
            if st.button("3. GENERATE TOKEN 🚀"):
                if "auth_code=" in full_google_url:
                    try:
                        # URL se auth_code nikalne ka solid formula
                        auth_code = full_google_url.split("auth_code=")[1].split("&")[0]
                        session.set_token(auth_code)
                        response = session.generate_token()
                        if 'access_token' in response:
                            st.session_state.access_token = response["access_token"]
                            st.success("LOGIN SUCCESSFUL!")
                            st.rerun()
                        else:
                            st.error(f"Error: {response}")
                    except Exception as e:
                        st.error(f"Logic Error: {str(e)}")
                else:
                    st.warning("Please paste the full URL containing 'auth_code='")
        return None
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- 3. OPTIONS & DATA ENGINE ---
def get_opt_sym(stock, ltp, type="CE"):
    expiry = "16APR26" 
    step = 100 if "NIFTY" in stock else 100 if "BANK" in stock else 10
    strike = round(ltp / step) * step
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{int(strike)}{type}"

# --- 4. MAIN TERMINAL ---
st.title("⚡ TERMINAL ALPHA: PRO OHL SCANNER")
fyers = get_fyers_instance()

if fyers:
    watch_list = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX", "NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:HDFCBANK-EQ"]
    today = datetime.date.today().strftime('%Y-%m-%d')
    results = []

    with st.spinner("SCANNING MARKET..."):
        for s in watch_list:
            try:
                q = fyers.quotes({"symbols": s})['d'][0]['v']['lp']
                syms = [s, get_opt_sym(s, q, "CE"), get_opt_sym(s, q, "PE")]
                for sym in syms:
                    res = fyers.history(data={"symbol": sym, "resolution": "15", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
                    if res['s'] == 'ok' and len(res['candles']) > 0:
                        df = pd.DataFrame(res['candles'], columns=['T','O','H','L','C','V'])
                        o, h_max, l_min, ltp = df.iloc[0]['O'], df['H'].max(), df['L'].min(), df.iloc[-1]['C']
                        
                        # Buffer OHL Logic
                        is_ol = abs(o - l_min) <= (o * 0.0005)
                        is_oh = abs(o - h_max) <= (o * 0.0005)
                        sig = "WAIT"
                        if is_ol: sig = "🟢 BUY (O=L)"
                        elif is_oh: sig = "🔴 SELL (O=H)"
                        
                        chg = round(((ltp - o) / o) * 100, 2)
                        results.append({"SYMBOL": sym, "ACTION": sig, "LTP": ltp, "% CHG": chg, "OPEN": o, "HIGH": h_max, "LOW": l_min})
            except: continue

    # --- LIVE TICKER ---
    if results:
        df_res = pd.DataFrame(results)
        gainers = df_res[df_res['% CHG'] > 0].sort_values(by='% CHG', ascending=False).head(5)
        ticker_text = " 🔥 TOP GAINERS: " + " | ".join([f"{r['SYMBOL']} ({r['% CHG']}%)" for idx, r in gainers.iterrows()])
        st.markdown(f'<div class="ticker-wrapper"><div class="ticker">{ticker_text}</div></div>', unsafe_allow_html=True)

    # --- TABLES & CHARTS ---
    col1, col2 = st.columns([1.3, 1.7])
    with col1:
        st.subheader("📡 OHL SCANNER")
        if results:
            df_final = pd.DataFrame(results).sort_values(by="% CHG", ascending=False)
            selected = st.radio("SELECT ASSET:", df_final['SYMBOL'].tolist())
            def style_rows(val):
                if 'BUY' in val: return 'background-color: #0a3d1d; color: #00ff00; font-weight: bold'
                if 'SELL' in val: return 'background-color: #4d0a0a; color: #ff4b4b; font-weight: bold'
                return ''
            st.dataframe(df_final.style.map(style_rows, subset=['ACTION']), height=500, use_container_width=True)
            if st.button("⚡ REFRESH"): st.rerun()

    with col2:
        if 'selected' in locals():
            st.subheader(f"📊 CHART: {selected}")
            chart_res = fyers.history(data={"symbol": selected, "resolution": "5", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
            if chart_res['s'] == 'ok' and len(chart_res['candles']) > 0:
                c_df = pd.DataFrame(chart_res['candles'], columns=['T', 'O', 'H', 'L', 'C', 'V'])
                fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(c_df['T'], unit='s'), open=c_df['O'], high=c_df['H'], low=c_df['L'], close=c_df['C'])])
                fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("👈 SIDEBAR SE FULL GOOGLE URL PASTE KARKE START KAREIN.")
