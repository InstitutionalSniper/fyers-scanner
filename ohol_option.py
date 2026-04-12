import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from fyers_apiv3 import fyersModel
from fyers_apiv3.fyersModel import SessionModel

# --- 1. CONFIGURATION ---
CLIENT_ID = "7PHDU5GN1H-100"  
SECRET_KEY = "8JXSML4ARB"
REDIRECT_URI = "https://google.com" 

# --- 2. LOGIN LOGIC ---
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
        
        auth_url = session.generate_authcode() 
        st.sidebar.markdown(f'<a href="{auth_url}" target="_blank" style="padding:10px; background-color:#ED1C24; color:white; border-radius:5px; text-decoration:none; display:inline-block; width:100%; text-align:center;">🚀 Click Here to Login</a>', unsafe_allow_html=True)
        
        st.sidebar.info("Login ke baad URL se 'auth_code' copy karein.")
        auth_code = st.sidebar.text_input("Yahan Auth Code paste karein:")
        
        if auth_code:
            try:
                session.set_token(auth_code)
                response = session.generate_token()
                if 'access_token' in response:
                    st.session_state.access_token = response["access_token"]
                    st.rerun()
                else:
                    st.sidebar.error(f"Token Error: {response}")
            except Exception as e:
                st.sidebar.error(f"Login Error: {str(e)}")
        return None
    
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- 3. OHL SCANNER ENGINE ---
def get_opt_sym(stock, ltp, type="CE"):
    expiry = "24MAY" # Update weekly
    step = 100 if "NIFTY" in stock else 50 if "BANK" in stock else 10
    strike = round(ltp / step) * step
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{int(strike)}{type}"

# --- 4. DASHBOARD UI ---
st.set_page_config(layout="wide", page_title="OHL Pro Scanner")
st.title("📊 Live OHL & Options Dashboard")

fyers = get_fyers_instance()

if fyers:
    # Top FNO Stocks to Scan
    watch_stocks = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX", "NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:HDFCBANK-EQ"]
    col1, col2 = st.columns([1, 2])

    results = []
    today = datetime.date.today().strftime('%Y-%m-%d')

    with st.spinner("Scanning Market..."):
        for s in watch_stocks:
            try:
                # Quotes response path fix
                q_res = fyers.quotes({"symbols": s})
                q = q_res['d'][0]['v']['lp']
                
                symbols = [s, get_opt_sym(s, q, "CE"), get_opt_sym(s, q, "PE")]
                
                for sym in symbols:
                    res = fyers.history(data={"symbol": sym, "resolution": "15", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
                    if res['s'] == 'ok' and len(res['candles']) > 0:
                        df = pd.DataFrame(res['candles'], columns=['T','O','H','L','C','V'])
                        # OHL Logic Fix: iloc[0] for first candle
                        o, h_max, l_min, ltp = df.iloc[0]['O'], df['H'].max(), df['L'].min(), df.iloc[-1]['C']
                        
                        signal = "Normal"
                        if o == l_min: signal = "🚀 O=L (Bull)"
                        elif o == h_max: signal = "🔻 O=H (Bear)"
                        
                        change = round(((ltp - o) / o) * 100, 2)
                        results.append({"Symbol": sym, "Signal": signal, "LTP": ltp, "% Chg": change})
            except: continue

    with col1:
        st.subheader("📋 Signals")
        if results:
            df_res = pd.DataFrame(results)
            selected = st.selectbox("Select for Chart:", df_res['Symbol'].tolist())
            # Coloring
            def color_signal(val):
                color = 'green' if 'Bull' in val else 'red' if 'Bear' in val else 'white'
                return f'color: {color}'
            st.dataframe(df_res.style.applymap(color_signal, subset=['Signal']))
        if st.button("🔄 Refresh Data"): st.rerun()

    with col2:
        if 'selected' in locals():
            st.subheader(f"📈 Chart: {selected}")
            c_res = fyers.history(data={"symbol": selected, "resolution": "5", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
            if c_res['s'] == 'ok':
                c_df = pd.DataFrame(c_res['candles'], columns=['T', 'O', 'H', 'L', 'C', 'V'])
                fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(c_df['T'], unit='s'), open=c_df['O'], high=c_df['H'], low=c_df['L'], close=c_df['C'])])
                fig.update_layout(template="plotly_dark", height=600, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Sidebar mein Login button se start karein.")
