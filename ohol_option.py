import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from fyers_apiv3 import fyersModel, accessToken
import datetime

# --- CONFIGURATION ---
# Note: Github par dalte waqt Security ka dhyan rakhein (Secrets use karein)
CLIENT_ID = "YOUR_CLIENT_ID" 
SECRET_KEY = "YOUR_SECRET_KEY"
REDIRECT_URI = "https://google.com" 

def get_fyers_instance():
    if 'access_token' not in st.session_state:
        st.sidebar.header("🔑 Fyers Login")
        session = accessToken.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, 
                                         redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
        auth_url = session.generate_auth_code()
        st.sidebar.markdown(f"[1. Click Here to Login]({auth_url})")
        auth_code = st.sidebar.text_input("2. Paste Auth Code from URL:")
        if auth_code:
            session.set_token(auth_code)
            response = session.generate_token()
            st.session_state.access_token = response["access_token"]
            st.rerun()
        return None
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- HELPERS ---
def play_sound():
    st.components.v1.html('<audio autoplay><source src="https://soundjay.com"></audio>', height=0)

def get_opt_sym(stock, ltp, type="CE"):
    expiry = "24MAY" # Update this weekly
    strike = round(ltp / 100) * 100 if "NIFTY" in stock else round(ltp / 10) * 10
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{strike}{type}"

# --- APP UI ---
st.set_page_config(layout="wide", page_title="OHL Pro Scanner")
fyers = get_fyers_instance()

if fyers:
    st.title("🚀 Live OHL Stocks & Options Scanner")
    stocks = ["NSE:SBIN-EQ", "NSE:NIFTY50-INDEX", "NSE:RELIANCE-EQ", "NSE:BANKNIFTY-INDEX"]
    
    col1, col2, col3 = st.columns([1, 1, 2]) # Scanner | Alerts | Chart

    # Data Fetching & OHL Logic
    results = []
    alerts = []
    today = datetime.date.today().strftime('%Y-%m-%d')
    
    for s in stocks:
        try:
            q = fyers.quotes({"symbols": s})['d'][0]['v']['lp']
            all_syms = [s, get_opt_sym(s, q, "CE"), get_opt_sym(s, q, "PE")]
            
            for sym in all_syms:
                res = fyers.history(data={"symbol": sym, "resolution": "15", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
                if res['s'] == 'ok' and len(res['candles']) > 0:
                    df = pd.DataFrame(res['candles'], columns=['T','O','H','L','C','V'])
                    o, h, l, c = df.iloc[0]['O'], df['H'].max(), df['L'].min(), df.iloc[-1]['C']
                    
                    status = "Normal"
                    if o == l: 
                        status = "Bullish (O=L)"
                        if c >= h * 0.99: alerts.append(f"🔥 Buy Breakout: {sym}")
                    elif o == h: 
                        status = "Bearish (O=H)"
                        if c <= l * 1.01: alerts.append(f"🧊 Sell Breakdown: {sym}")
                    
                    results.append({"Symbol": sym, "Status": status, "LTP": c, "%": round(((c-o)/o)*100, 2)})
        except: pass

    with col1:
        st.subheader("📋 Scanner")
        df_res = pd.DataFrame(results)
        if not df_res.empty:
            sel = st.radio("Select Symbol:", df_res['Symbol'].tolist())
            st.dataframe(df_res)
        if st.button("Refresh 🔄"): st.rerun()

    with col2:
        st.subheader("⚠️ Alerts")
        for a in alerts:
            st.success(a)
            play_sound()

    with col3:
        st.subheader(f"📊 Chart: {sel}")
        # Plotly logic (Same as before)
