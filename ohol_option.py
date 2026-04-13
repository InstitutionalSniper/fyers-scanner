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

# CSS for Scrolling Ticker and UI
st.markdown("""
    <style>
    .ticker-wrapper { background: #1a1a2e; color: #00ff00; padding: 10px; overflow: hidden; border-bottom: 2px solid #333; }
    .ticker { display: inline-block; white-space: nowrap; animation: ticker 30s linear infinite; font-weight: bold; font-size: 18px; }
    @keyframes ticker { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    .stApp { background: #0b0e14; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TOKEN ENGINE ---
def get_fyers_instance():
    if 'access_token' not in st.session_state:
        with st.sidebar:
            st.markdown("### 🔐 ACCESS GATEWAY")
            session = SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
            auth_url = session.generate_authcode()
            st.markdown(f'''<a href="{auth_url}" target="_blank"><button style="width:100%; height:50px; background: linear-gradient(90deg, #ff4b2b, #ff416c); color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold;">🔑 LOGIN FYERS</button></a>''', unsafe_allow_html=True)
            full_url = st.text_input("PASTE REDIRECT URL")
            if st.button("INITIALIZE"):
                if "auth_code=" in full_url:
                    try:
                        auth_code = full_url.split("auth_code=").split("&")
                        session.set_token(auth_code)
                        response = session.generate_token()
                        if 'access_token' in response:
                            st.session_state.access_token = response["access_token"]
                            st.rerun()
                    except: st.error("Token Error")
        return None
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- 3. OPTIONS SYMBOL GEN ---
def get_opt_sym(stock, ltp, type="CE"):
    expiry = "16APR26" 
    step = 100 if "NIFTY" in stock else 100 if "BANK" in stock else 10
    strike = round(ltp / step) * step
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{int(strike)}{type}"

# --- 4. DATA ENGINE & UI ---
st.title("⚡ TERMINAL ALPHA: PRO OHL SCANNER")
fyers = get_fyers_instance()

if fyers:
    watch_list = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX", "NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:HDFCBANK-EQ", "NSE:ICICIBANK-EQ", "NSE:TATASTEEL-EQ"]
    today = datetime.date.today().strftime('%Y-%m-%d')
    results = []

    with st.spinner("SYNCING EXCHANGE DATA..."):
        for s in watch_list:
            try:
                q = fyers.quotes({"symbols": s})['d']['v']['lp']
                syms = [s, get_opt_sym(s, q, "CE"), get_opt_sym(s, q, "PE")]
                for sym in syms:
                    res = fyers.history(data={"symbol": sym, "resolution": "15", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
                    if res['s'] == 'ok' and len(res['candles']) > 0:
                        df = pd.DataFrame(res['candles'], columns=['T','O','H','L','C','V'])
                        o, h_max, l_min, ltp, vol = df.iloc['O'], df['H'].max(), df['L'].min(), df.iloc[-1]['C'], df['V'].sum()
                        
                        # OHL Logic with Buffer
                        is_ol = abs(o - l_min) <= (o * 0.0005)
                        is_oh = abs(o - h_max) <= (o * 0.0005)
                        sig = "WAIT"
                        if is_ol: sig = "🟢 BUY (O=L)"
                        elif is_oh: sig = "🔴 SELL (O=H)"
                        
                        chg = round(((ltp - o) / o) * 100, 2)
                        results.append({"SYMBOL": sym, "ACTION": sig, "LTP": ltp, "% CHG": chg, "VOL": vol, "OPEN": o, "HIGH": h_max, "LOW": l_min})
            except: continue

    # --- LIVE TICKER ---
    if results:
        df_res = pd.DataFrame(results)
        gainers = df_res[df_res['% CHG'] > 0].sort_values(by='% CHG', ascending=False).head(5)
        losers = df_res[df_res['% CHG'] < 0].sort_values(by='% CHG', ascending=True).head(5)
        
        ticker_text = " 🔥 GAINERS: " + " | ".join([f"{r['SYMBOL']} ({r['% CHG']}%)" for idx, r in gainers.iterrows()]) + \
                      " 🧊 LOSERS: " + " | ".join([f"{r['SYMBOL']} ({r['% CHG']}%)" for idx, r in losers.iterrows()])
        
        st.markdown(f'<div class="ticker-wrapper"><div class="ticker">{ticker_text}</div></div>', unsafe_allow_html=True)

    # --- MAIN DISPLAY ---
    c_left, c_right = st.columns([1.3, 1.7])
    
    with c_left:
        st.subheader("📡 LIVE OHL SCANNER")
        if results:
            df_final = pd.DataFrame(results).sort_values(by="% CHG", ascending=False)
            selected = st.radio("SELECT ASSET:", df_final['SYMBOL'].tolist())
            
            def style_rows(val):
                if 'BUY' in val: return 'background-color: #0a3d1d; color: #00ff00; font-weight: bold'
                if 'SELL' in val: return 'background-color: #4d0a0a; color: #ff4b4b; font-weight: bold'
                return ''
            
            st.dataframe(df_final.style.map(style_rows, subset=['ACTION']), height=500, use_container_width=True)
            if st.button("⚡ REFRESH"): st.rerun()

    with c_right:
        if 'selected' in locals():
            st.subheader(f"📊 CHART: {selected}")
            chart_res = fyers.history(data={"symbol": selected, "resolution": "5", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
            if chart_res['s'] == 'ok' and len(chart_res['candles']) > 0:
                c_df = pd.DataFrame(chart_res['candles'], columns=['T', 'O', 'H', 'L', 'C', 'V'])
                fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(c_df['T'], unit='s'), open=c_df['O'], high=c_df['H'], low=c_df['L'], close=c_df['C'])])
                fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("💡 SIDEBAR SE LOGIN KAREIN.")
