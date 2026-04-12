import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from fyers_apiv3 import fyersModel
from fyers_apiv3.fyersModel import SessionModel

# --- 1. TERMINAL STYLING (Ultra Pro) ---
st.set_page_config(layout="wide", page_title="TERMINAL ALPHA v3")
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f0f12 0%, #1a1a2e 100%); color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #0a0a0c; border-right: 1px solid #2d2d3d; }
    .stMetric { background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 12px; border: 1px solid #333; }
    .stDataFrame { border: 1px solid #444; border-radius: 8px; }
    h1 { color: #00d2ff; text-shadow: 0px 0px 10px #00d2ff; }
    </style>
    """, unsafe_allow_html=True)

CLIENT_ID = "7PHDU5GN1H-100"  
SECRET_KEY = "8JXSML4ARB"
REDIRECT_URI = "https://google.com" 

# --- 2. THE TOKEN ENGINE ---
def get_fyers_instance():
    with st.sidebar:
        st.markdown("### 🔐 ACCESS GATEWAY")
        if 'access_token' not in st.session_state:
            session = SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
            auth_url = session.generate_authcode()
            st.markdown(f'''<a href="{auth_url}" target="_blank"><button style="width:100%; height:50px; background: linear-gradient(90deg, #ff4b2b, #ff416c); color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold; font-size:16px;">🔑 STEP 1: AUTHENTICATE</button></a>''', unsafe_allow_html=True)
            st.write("")
            full_url = st.text_input("STEP 2: PASTE REDIRECT URL", placeholder="https://google.com...")
            if st.button("STEP 3: INITIALIZE TERMINAL"):
                if "auth_code=" in full_url:
                    try:
                        auth_code = full_url.split("auth_code=")[1].split("&")[0]
                        session.set_token(auth_code)
                        response = session.generate_token()
                        if 'access_token' in response:
                            st.session_state.access_token = response["access_token"]
                            st.rerun()
                    except: st.error("Access Code Expired or Invalid.")
            return None
        else:
            st.success("🛰️ TERMINAL ENCRYPTED & LIVE")
            if st.button("🔴 DISCONNECT"):
                del st.session_state.access_token
                st.rerun()
            return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- 3. CORE LOGIC ---
def get_opt_sym(stock, ltp, type="CE"):
    expiry = "16APR26" 
    step = 100 if "NIFTY" in stock else 10
    strike = round(ltp / step) * step
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{int(strike)}{type}"

# --- 4. TERMINAL INTERFACE ---
st.title("⚡ TERMINAL ALPHA: INSTITUTIONAL OHL SCANNER")
fyers = get_fyers_instance()

if fyers:
    watch_list = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX", "NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:HDFCBANK-EQ", "NSE:TATASTEEL-EQ"]
    
    # Dashboard Tiles
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("SESSION", "INTRADAY", "LIVE")
    t2.metric("SCAN FREQUENCY", "15-MIN OHLC")
    t3.metric("EXPIRY SELECTED", "16-APR-2026")
    t4.metric("SYSTEM LOAD", "OPTIMAL", "0.2ms")

    today = datetime.date.today().strftime('%Y-%m-%d')
    results = []

    with st.spinner("SYNCING WITH EXCHANGE..."):
        for s in watch_list:
            try:
                q = fyers.quotes({"symbols": s})['d'][0]['v']['lp']
                syms = [s, get_opt_sym(s, q, "CE"), get_opt_sym(s, q, "PE")]
                
                for sym in syms:
                    res = fyers.history(data={"symbol": sym, "resolution": "15", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
                    if res['s'] == 'ok' and len(res['candles']) > 0:
                        df = pd.DataFrame(res['candles'], columns=['T','O','H','L','C','V'])
                        o, h, l, c = df.iloc[0]['O'], df['H'].max(), df['L'].min(), df.iloc[-1]['C']
                        chg = round(((c - o) / o) * 100, 2)
                        
                        sig = "WAIT"
                        if o == l and c >= h * 0.998: sig = "🟢 STRONG BUY (O=L)"
                        elif o == h and c <= l * 1.002: sig = "🔴 STRONG SELL (O=H)"
                        elif chg > 2.0: sig = "🔥 MOMENTUM"

                        results.append({"SYMBOL": sym, "ACTION": sig, "LTP": c, "% CHG": chg, "HIGH": h, "LOW": l})
            except: continue

    c_left, c_right = st.columns([1, 1.8])
    
    with c_left:
        st.subheader("📡 LIVE SIGNALS")
        if results:
            df_final = pd.DataFrame(results).sort_values(by="% CHG", ascending=False)
            selected = st.radio("SELECT ASSET:", df_final['SYMBOL'].tolist())
            
            def color_rows(val):
                if 'BUY' in val: return 'background-color: #0a3d1d; color: #00ff00'
                if 'SELL' in val: return 'background-color: #4d0a0a; color: #ff4b4b'
                return ''
            st.dataframe(df_final.style.applymap(color_rows, subset=['ACTION']), height=500, use_container_width=True)
            if st.button("⚡ FORCE REFRESH"): st.rerun()
        else:
            st.warning("⚠️ WAITING FOR 9:30 AM CANDLE CLOSURE...")

    with c_right:
        if 'selected' in locals():
            st.subheader(f"📈 ADVANCED CHART: {selected}")
            chart_res = fyers.history(data={"symbol": selected, "resolution": "5", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
            if chart_res['s'] == 'ok' and len(chart_res['candles']) > 0:
                c_df = pd.DataFrame(chart_res['candles'], columns=['T', 'O', 'H', 'L', 'C', 'V'])
                fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(c_df['T'], unit='s'), open=c_df['O'], high=c_df['H'], low=c_df['L'], close=c_df['C'])])
                fig.update_layout(template="plotly_dark", height=600, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("💡 TERMINAL DISCONNECTED. PLEASE USE THE SIDEBAR ACCESS GATEWAY.")
