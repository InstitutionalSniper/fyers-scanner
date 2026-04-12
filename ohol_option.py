import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from fyers_apiv3 import fyersModel
from fyers_apiv3.fyersModel import SessionModel

# --- 1. PRO THEME & CONFIG ---
st.set_page_config(layout="wide", page_title="Alpha OHL Scanner")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e1e1; }
    .metric-card { background-color: #1a1e26; border-radius: 10px; padding: 15px; border-left: 5px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

CLIENT_ID = "7PHDU5GN1H-100"  
SECRET_KEY = "8JXSML4ARB"
REDIRECT_URI = "https://google.com" 

# --- 2. THE TOKEN BUTTON (SIDEBAR) ---
def get_fyers_instance():
    with st.sidebar:
        st.header("🔑 SECURE ACCESS")
        if 'access_token' not in st.session_state:
            session = SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
            auth_url = session.generate_authcode()
            
            st.markdown(f'''<a href="{auth_url}" target="_blank"><button style="width:100%; background-color:#ED1C24; color:white; border:none; padding:12px; border-radius:5px; cursor:pointer; font-weight:bold; font-size:16px;">🚀 STEP 1: LOGIN FYERS</button></a>''', unsafe_allow_html=True)
            st.write("")
            full_url = st.text_area("STEP 2: PASTE GOOGLE URL HERE", height=100)
            
            if st.button("STEP 3: GENERATE TERMINAL TOKEN"):
                if "auth_code=" in full_url:
                    try:
                        auth_code = full_url.split("auth_code=")[1].split("&")[0]
                        session.set_token(auth_code)
                        response = session.generate_token()
                        if 'access_token' in response:
                            st.session_state.access_token = response["access_token"]
                            st.success("ACCESS GRANTED!")
                            st.rerun()
                    except: st.error("Invalid URL! Login again.")
            return None
        else:
            st.success("✅ TERMINAL ONLINE")
            if st.button("LOGOUT"):
                del st.session_state.access_token
                st.rerun()
            return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- 3. PRO SCANNER LOGIC ---
def get_opt_sym(stock, ltp, type="CE"):
    expiry = "16APR26" # Fix for current date
    step = 100 if "NIFTY" in stock else 10
    strike = round(ltp / step) * step
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{int(strike)}{type}"

# --- 4. MAIN TERMINAL UI ---
st.title("⚡ ALPHA INTRADAY: OHL & BREAKOUT TERMINAL")
fyers = get_fyers_instance()

if fyers:
    watch_list = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX", "NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:HDFCBANK-EQ"]
    results = []
    today = datetime.date.today().strftime('%Y-%m-%d')

    # Top Row Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("MARKET STATUS", "LIVE" if datetime.datetime.now().hour < 16 else "CLOSED")
    m2.metric("SCANNING TIME", "15 MIN")
    
    with st.spinner("FETCHING REAL-TIME DATA..."):
        for s in watch_list:
            try:
                q_res = fyers.quotes({"symbols": s})
                ltp = q_res['d'][0]['v']['lp']
                syms = [s, get_opt_sym(s, ltp, "CE"), get_opt_sym(s, ltp, "PE")]
                
                for sym in syms:
                    res = fyers.history(data={"symbol": sym, "resolution": "15", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
                    if res['s'] == 'ok' and len(res['candles']) > 0:
                        df = pd.DataFrame(res['candles'], columns=['T','O','H','L','C','V'])
                        o, h, l, c = df.iloc[0]['O'], df['H'].max(), df['L'].min(), df.iloc[-1]['C']
                        change = round(((c - o) / o) * 100, 2)
                        
                        signal = "WAIT"
                        if o == l and c >= h * 0.995: signal = "🔥 STRONG BUY (O=L)"
                        elif o == h and c <= l * 1.005: signal = "🧊 STRONG SELL (O=H)"
                        elif change > 2.0: signal = "🚀 MOMENTUM UP"

                        results.append({"SYMBOL": sym, "ACTION": signal, "LTP": c, "% CHG": change, "DAY HIGH": h, "DAY LOW": l})
            except: continue

    col_left, col_right = st.columns([1.3, 1.7])
    
    with col_left:
        st.subheader("🎯 TRADE SIGNALS")
        if results:
            df_res = pd.DataFrame(results).sort_values(by="% CHG", ascending=False)
            selected = st.selectbox("SELECT SYMBOL TO ANALYZE:", df_res['SYMBOL'].tolist())
            
            # Styling Table
            def style_action(val):
                if 'BUY' in val: return 'color: #00ff00; font-weight: bold'
                if 'SELL' in val: return 'color: #ff4b4b; font-weight: bold'
                return ''
            st.dataframe(df_res.style.applymap(style_action, subset=['ACTION']), height=500, use_container_width=True)
            if st.button("REFRESH TERMINAL"): st.rerun()
        else:
            st.info("9:30 AM ke baad yahan Live Signals chamkenge!")

    with col_right:
        if 'selected' in locals():
            st.subheader(f"📊 INTERACTIVE CHART: {selected}")
            c_res = fyers.history(data={"symbol": selected, "resolution": "5", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
            if c_res['s'] == 'ok' and len(c_res['candles']) > 0:
                c_df = pd.DataFrame(c_res['candles'], columns=['T', 'O', 'H', 'L', 'C', 'V'])
                fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(c_df['T'], unit='s'), open=c_df['O'], high=c_df['H'], low=c_df['L'], close=c_df['C'])])
                fig.update_layout(template="plotly_dark", height=600, paper_bgcolor="#0b0e14", plot_bgcolor="#0b0e14", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("👈 SIDEBAR SE LOGIN KAREIN: LOGIN -> URL PASTE -> GENERATE TOKEN")
