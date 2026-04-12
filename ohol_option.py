import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from fyers_apiv3 import fyersModel
# Naye version mein accessToken ka rasta ye hai:
from fyers_apiv3.fyersModel import accessToken
import datetime

# --- 1. CONFIGURATION ---
# Apni details yahan bharein
CLIENT_ID = "YOUR_CLIENT_ID" 
SECRET_KEY = "YOUR_SECRET_KEY"
REDIRECT_URI = "https://google.com"

# --- 2. LOGIN LOGIC (Fixed for v3) ---
def get_fyers_instance():
    if 'access_token' not in st.session_state:
        st.sidebar.header("🔑 Fyers Login")
        # SessionModel ab accessToken ke andar hota hai
        session = accessToken.SessionModel(
            client_id=CLIENT_ID, 
            secret_key=SECRET_KEY, 
            redirect_uri=REDIRECT_URI, 
            response_type="code", 
            grant_type="authorization_code"
        )
        
        auth_url = session.generate_auth_code()
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
    else:
        return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- 3. HELPERS: SOUND & SYMBOLS ---
def play_sound():
    sound_html = """<audio autoplay><source src="https://soundjay.com"></audio>"""
    st.components.v1.html(sound_html, height=0)

def get_opt_sym(stock, ltp, type="CE"):
    expiry = "24MAY" # Isse har hafte update karein
    strike = round(ltp / 100) * 100 if "NIFTY" in stock else round(ltp / 10) * 10
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{int(strike)}{type}"

# --- 4. MAIN DASHBOARD ---
st.set_page_config(layout="wide", page_title="Pro OHL Scanner")
st.title("⚡ Live OHL & Breakout Dashboard")

fyers = get_fyers_instance()

if fyers:
    st.sidebar.success("✅ Connected")
    stocks_to_scan = ["NSE:SBIN-EQ", "NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX", "NSE:RELIANCE-EQ"]
    
    col1, col2, col3 = st.columns([1, 1, 2]) # Scanner | Alerts | Chart

    results = []
    alerts = []
    today = datetime.date.today().strftime('%Y-%m-%d')

    for s in stocks_to_scan:
        try:
            # Get LTP for Options
            q = fyers.quotes({"symbols": s})['d'][0]['v']['lp']
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
        st.subheader("📋 OHL List")
        if results:
            df_res = pd.DataFrame(results)
            selected = st.radio("Select for Chart:", df_res['Symbol'].tolist())
            st.table(df_res)
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
                fig.update_layout(template="plotly_dark", height=500)
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sidebar se login karein tabhi scanner start hoga.")
