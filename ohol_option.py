import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from fyers_apiv3 import fyersModel
from fyers_apiv3.fyersModel import SessionModel

# --- 1. CONFIGURATION ---
CLIENT_ID = "7PHDU5GN1H-100"  
SECRET_KEY = "8JXSML4ARB"
REDIRECT_URI = "https://google.com" # Fyers Dashboard mein bhi EXACT yahi honi chahiye

# --- 2. FULL AUTOMATIC LOGIN LOGIC ---
def get_fyers_instance():
    # URL se auth_code automatic pakadne ke liye
    query_params = st.query_params
    auth_code = query_params.get("auth_code")

    if 'access_token' not in st.session_state:
        if auth_code:
            # Agar URL mein code mil gaya toh automatic token generate karo
            try:
                session = SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, 
                                      redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
                session.set_token(auth_code)
                response = session.generate_token()
                if 'access_token' in response:
                    st.session_state.access_token = response["access_token"]
                    st.query_params.clear() # URL saaf karo
                    st.rerun()
            except Exception as e:
                st.sidebar.error(f"Login Failed: {e}")

        # Login Button agar token nahi hai
        st.sidebar.header("🔑 Fyers Login")
        session = SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, 
                              redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
        auth_url = session.generate_authcode()
        
        st.sidebar.markdown(f'''
            <a href="{auth_url}" target="_self">
                <button style="width:100%; background-color:#ff4b4b; color:white; border:none; padding:12px; border-radius:5px; cursor:pointer; font-weight:bold;">
                    🔐 Login with Fyers (Full Auto)
                </button>
            </a>
            ''', unsafe_allow_html=True)
        return None
    
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- 3. OHL SCANNER ENGINE ---
def get_opt_sym(stock, ltp, type="CE"):
    expiry = "24MAY" # Expiry update karein
    step = 100 if "NIFTY" in stock else 50 if "BANK" in stock else 10
    strike = round(ltp / step) * step
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{int(strike)}{type}"

# --- 4. DASHBOARD UI ---
st.set_page_config(layout="wide", page_title="OHL Pro Scanner")
st.title("📊 Live OHL & Options Scanner")

fyers = get_fyers_instance()

if fyers:
    st.sidebar.success("✅ Logged In")
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
                        o, h_max, l_min, ltp = df.iloc[0]['O'], df['H'].max(), df['L'].min(), df.iloc[-1]['C']
                        
                        signal = "Neutral"
                        if o == l_min: signal = "🚀 O=L (Bull)"
                        elif o == h_high: signal = "🔻 O=H (Bear)"
                        
                        change = round(((ltp - o) / o) * 100, 2)
                        results.append({"Symbol": sym, "Signal": signal, "LTP": ltp, "% Chg": change})
            except: continue

    with col1:
        st.subheader("📋 Live Signals")
        if results:
            df_res = pd.DataFrame(results)
            selected = st.selectbox("Select for Chart:", df_res['Symbol'].tolist())
            st.dataframe(df_res.style.applymap(lambda x: 'color: green' if 'Bull' in str(x) else 'color: red' if 'Bear' in str(x) else '', subset=['Signal']))
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
    st.warning("Pehle Login Button par click karein.")
