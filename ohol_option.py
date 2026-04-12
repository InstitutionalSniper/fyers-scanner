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

# --- 2. LOGIN LOGIC (Keep this same) ---
def get_fyers_instance():
    if 'access_token' not in st.session_state:
        st.sidebar.header("🔑 Fyers Login")
        session = SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
        auth_url = session.generate_authcode()
        st.sidebar.markdown(f'''<a href="{auth_url}" target="_blank"><button style="width:100%; background-color:#ff4b4b; color:white; border:none; padding:12px; border-radius:5px; cursor:pointer; font-weight:bold;">1. Login with Fyers</button></a>''', unsafe_allow_html=True)
        st.sidebar.write("---")
        full_url = st.sidebar.text_input("2. Login ke baad pura Google URL yahan paste karein:")
        if st.sidebar.button("3. Generate Token 🚀"):
            if "auth_code=" in full_url:
                try:
                    auth_code = full_url.split("auth_code=")[1].split("&")[0]
                    session.set_token(auth_code)
                    response = session.generate_token()
                    if 'access_token' in response:
                        st.session_state.access_token = response["access_token"]
                        st.rerun()
                except Exception as e: st.sidebar.error(f"Logic Error: {str(e)}")
        return None
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- 3. OPTION SYMBOL GENERATOR ---
def get_opt_sym(stock, ltp, type="CE"):
    expiry = "16APR26" # Current Expiry
    step = 100 if "NIFTY" in stock else 10
    strike = round(ltp / step) * step
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{int(strike)}{type}"

# --- 4. DASHBOARD UI ---
st.set_page_config(layout="wide", page_title="Master OHL Scanner")
st.title("🚀 Master OHL & Gainer Dashboard")

fyers = get_fyers_instance()

if fyers:
    # Mix of Index, Top Stocks & Gainers
    watch_list = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX", "NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:HDFCBANK-EQ", "NSE:ICICIBANK-EQ", "NSE:TATASTEEL-EQ"]
    
    results = []
    today = datetime.date.today().strftime('%Y-%m-%d')

    with st.spinner("Scanning Market Data..."):
        for s in watch_list:
            try:
                # 1. Get Live Price
                q_res = fyers.quotes({"symbols": s})
                ltp = q_res['d'][0]['v']['lp']
                
                # 2. Add Options for Index/Stocks
                symbols_to_check = [s, get_opt_sym(s, ltp, "CE"), get_opt_sym(s, ltp, "PE")]
                
                for sym in symbols_to_check:
                    res = fyers.history(data={"symbol": sym, "resolution": "15", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
                    
                    if res['s'] == 'ok' and len(res['candles']) > 0:
                        df = pd.DataFrame(res['candles'], columns=['T','O','H','L','C','V'])
                        o = df.iloc[0]['O']
                        h = df['H'].max()
                        l = df['L'].min()
                        curr = df.iloc[-1]['C']
                        change = round(((curr - o) / o) * 100, 2)
                        
                        # LOGIC: OHL + Gainer/Loser Status
                        signal = "Neutral"
                        if o == l: signal = "🚀 BUY (O=L)"
                        elif o == h: signal = "🔻 SELL (O=H)"
                        
                        # Extra Status for Gainers
                        if change > 2.0: signal += " | 🔥 GAINER"
                        elif change < -2.0: signal += " | 🧊 LOSER"

                        results.append({
                            "Symbol": sym,
                            "Signal/Status": signal,
                            "LTP": curr,
                            "% Change": change,
                            "Day High": h,
                            "Day Low": l
                        })
            except: continue

    # UI Rendering
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("📋 Live Scanner (Stocks & Options)")
        if results:
            df_res = pd.DataFrame(results)
            # Sort by Change to see Gainers on Top
            df_res = df_res.sort_values(by="% Change", ascending=False)
            
            selected = st.selectbox("Select for Chart:", df_res['Symbol'].tolist())
            st.dataframe(df_res, use_container_width=True)
        else:
            st.info("9:30 AM ke baad data refresh karein.")
        
        if st.button("🔄 Refresh Market Data"): st.rerun()

    with col2:
        if 'selected' in locals():
            st.subheader(f"📈 Chart: {selected}")
            c_res = fyers.history(data={"symbol": selected, "resolution": "5", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
            if c_res['s'] == 'ok' and len(c_res['candles']) > 0:
                c_df = pd.DataFrame(c_res['candles'], columns=['T', 'O', 'H', 'L', 'C', 'V'])
                fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(c_df['T'], unit='s'), open=c_df['O'], high=c_df['H'], low=c_df['L'], close=c_df['C'])])
                fig.update_layout(template="plotly_dark", height=600)
                st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Sidebar se Login karein.")
