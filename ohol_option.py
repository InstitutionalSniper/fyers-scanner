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

# --- 2. MANUAL URL PASTE LOGIN LOGIC ---
def get_fyers_instance():
    if 'access_token' not in st.session_state:
        st.sidebar.header("🔑 Fyers Login (Manual)")
        
        session = SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, 
                              redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
        
        auth_url = session.generate_authcode()
        
        # Step 1: Login Button
        st.sidebar.markdown(f'''
            <a href="{auth_url}" target="_blank">
                <button style="width:100%; background-color:#ff4b4b; color:white; border:none; padding:12px; border-radius:5px; cursor:pointer; font-weight:bold;">
                    1. Login with Fyers
                </button>
            </a>
            ''', unsafe_allow_html=True)
        
        st.sidebar.write("---")
        
        # Step 2: Paste Full URL
        full_url = st.sidebar.text_input("2. Login ke baad pura Google URL yahan paste karein:")
        
        # Step 3: Button to Generate Token
        if st.sidebar.button("3. Generate Token 🚀"):
            if "auth_code=" in full_url:
                try:
                    # URL se auth_code khud nikalne ka logic
                    auth_code = full_url.split("auth_code=")[1].split("&")[0]
                    
                    session.set_token(auth_code)
                    response = session.generate_token()
                    
                    if 'access_token' in response:
                        st.session_state.access_token = response["access_token"]
                        st.sidebar.success("Token Mil Gaya! ✅")
                        st.rerun()
                    else:
                        st.sidebar.error(f"Error: {response.get('message', 'Invalid URL')}")
                except Exception as e:
                    st.sidebar.error(f"Logic Error: {str(e)}")
            else:
                st.sidebar.warning("Sahi URL paste karein jisme 'auth_code' ho.")
        
        return None
    
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- 3. OHL SCANNER ENGINE ---
def get_opt_sym(stock, ltp, type="CE"):
    expiry = "24MAY" 
    step = 100 if "NIFTY" in stock else 50 if "BANK" in stock else 10
    strike = round(ltp / step) * step
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{int(strike)}{type}"

# --- 4. DASHBOARD UI ---
st.set_page_config(layout="wide", page_title="OHL Pro Scanner")
st.title("📊 Live OHL & Options Dashboard")

fyers = get_fyers_instance()

if fyers:
    st.sidebar.success("✅ Dashboard Active")
    watch_stocks = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX", "NSE:SBIN-EQ", "NSE:RELIANCE-EQ"]
    
    col1, col2 = st.columns([1, 2])
    results = []
    today = datetime.date.today().strftime('%Y-%m-%d')

    with st.spinner("Market Scan Chal Raha Hai..."):
        for s in watch_stocks:
            try:
                q_res = fyers.quotes({"symbols": s})
                q = q_res['d'][0]['v']['lp']
                symbols = [s, get_opt_sym(s, q, "CE"), get_opt_sym(s, q, "PE")]
                
                for sym in symbols:
                    res = fyers.history(data={"symbol": sym, "resolution": "15", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
                    if res['s'] == 'ok' and len(res['candles']) > 0:
                        df = pd.DataFrame(res['candles'], columns=['T','O','H','L','C','V'])
                        # First Candle Indexing Fix
                        o, h_max, l_min, ltp = df.iloc[0]['O'], df['H'].max(), df['L'].min(), df.iloc[-1]['C']
                        
                        signal = "Neutral"
                        if o == l_min: signal = "🚀 O=L (Bullish)"
                        elif o == h_max: signal = "🔻 O=H (Bearish)"
                        
                        change = round(((ltp - o) / o) * 100, 2)
                        results.append({"Symbol": sym, "Signal": signal, "LTP": ltp, "% Chg": change})
            except: continue

    with col1:
        st.subheader("📋 Signals")
        if results:
            df_res = pd.DataFrame(results)
            selected = st.selectbox("Select for Chart:", df_res['Symbol'].tolist())
            st.dataframe(df_res.style.applymap(lambda x: 'color: green' if 'Bullish' in str(x) else ('color: red' if 'Bearish' in str(x) else ''), subset=['Signal']))
        if st.button("🔄 Refresh Data"): st.rerun()

    with col2:
        if 'selected' in locals():
            st.subheader(f"📈 Chart: {selected}")
            c_res = fyers.history(data={"symbol": selected, "resolution": "5", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
            if c_res['s'] == 'ok':
                c_df = pd.DataFrame(c_res['candles'], columns=['T', 'O', 'H', 'L', 'C', 'V'])
                fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(c_df['T'], unit='s'), open=c_df['O'], high=c_df['H'], low=c_df['L'], close=c_df['C'])])
                fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("👈 Sidebar se Step 1 aur Step 2 poora karein.")
