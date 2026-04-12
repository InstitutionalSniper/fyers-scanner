import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from fyers_apiv3 import fyersModel
from fyers_apiv3.fyersModel import SessionModel

# --- 1. CONFIGURATION ---
CLIENT_ID = "YOUR_CLIENT_ID" # अपनी ID डालें
SECRET_KEY = "YOUR_SECRET_KEY" # अपनी Key डालें
REDIRECT_URI = "https://google.com"

# --- 2. LOGIN LOGIC (Latest v3 Fix) ---
def get_fyers_instance():
    if 'access_token' not in st.session_state:
        st.sidebar.header("🔑 Fyers Login")
        session = SessionModel(
            client_id=CLIENT_ID, 
            secret_key=SECRET_KEY, 
            redirect_uri=REDIRECT_URI, 
            response_type="code", 
            grant_type="authorization_code"
        )
        
        # FIX: बिना अंडरस्कोर वाला फंक्शन
        auth_url = session.generate_authcode() 
        
        st.sidebar.markdown(f"[1. Click Here to Login]({auth_url})")
        
        auth_code = st.sidebar.text_input("2. Paste Auth Code from URL:")
        if auth_code:
            try:
                session.set_token(auth_code)
                response = session.generate_token()
                st.session_state.access_token = response["access_token"]
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Login Error: {e}")
        return None
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- 3. HELPERS: SOUND & SYMBOLS ---
def play_sound():
    sound_html = """<audio autoplay><source src="https://soundjay.com"></audio>"""
    st.components.v1.html(sound_html, height=0)

def get_opt_sym(stock, ltp, type="CE"):
    expiry = "24MAY" # Weekly अपडेट करें
    strike = round(ltp / 100) * 100 if "NIFTY" in stock else round(ltp / 10) * 10
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{int(strike)}{type}"

# --- 4. MAIN DASHBOARD ---
st.set_page_config(layout="wide", page_title="OHL Pro Scanner")
st.title("⚡ Live OHL & Breakout Dashboard")

fyers = get_fyers_instance()

if fyers:
    st.sidebar.success("✅ Connected")
    # Stocks List
    watch_stocks = ["NSE:SBIN-EQ", "NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX", "NSE:RELIANCE-EQ"]
    
    col1, col2, col3 = st.columns([1, 1, 2]) # Dashboard Layout

    results = []
    alerts = []
    today = datetime.date.today().strftime('%Y-%m-%d')

    for s in watch_stocks:
        try:
            q_res = fyers.quotes({"symbols": s})
            q = q_res['d'][0]['v']['lp'] # Fix for dict response
            all_syms = [s, get_opt_sym(s, q, "CE"), get_opt_sym(s, q, "PE")]

            for sym in all_syms:
                res = fyers.history(data={"symbol": sym, "resolution": "15", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
                if res['s'] == 'ok' and len(res['candles']) > 0:
                    df = pd.DataFrame(res['candles'], columns=['T','O','H','L','C','V'])
                    o, h_max, l_min, ltp = df.iloc[0]['O'], df['H'].max(), df['L'].min(), df.iloc[-1]['C']
                    
                    status = "Normal"
                    if o == l_min: 
                        status = "🚀 Bull (O=L)"
                        if ltp >= h_max * 0.998: alerts.append(f"🔥 BUY: {sym}")
                    elif o == h_max: 
                        status = "🔻 Bear (O=H)"
                        if ltp <= l_min * 1.002: alerts.append(f"🧊 SELL: {sym}")
                    
                    change = round(((ltp - o) / o) * 100, 2)
                    results.append({"Symbol": sym, "Signal": status, "LTP": ltp, "% Chg": change})
        except: continue

    with col1:
        st.subheader("📋 Scanner List")
        if results:
            df_res = pd.DataFrame(results)
            selected = st.radio("Select for Chart:", df_res['Symbol'].tolist())
            st.dataframe(df_res, use_container_width=True)
        if st.button("Refresh 🔄"): st.rerun()

    with col2:
        st.subheader("⚠️ Alerts")
        if alerts:
            play_sound()
            for a in alerts: st.success(a)
        else: st.info("No breakouts.")

    with col3:
        if 'selected' in locals():
            st.subheader(f"📊 Chart: {selected}")
            c_res = fyers.history(data={"symbol": selected, "resolution": "5", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
            if c_res['s'] == 'ok':
                c_df = pd.DataFrame(c_res['candles'], columns=['T', 'O', 'H', 'L', 'C', 'V'])
                fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(c_df['T'], unit='s'), open=c_df['O'], high=c_df['H'], low=c_df['L'], close=c_df['C'])])
                fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sidebar se login karein tabhi dashboard load hoga.")
