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

# --- 2. LOGIN LOGIC (Wahi Same Button & Paste System) ---
def get_fyers_instance():
    if 'access_token' not in st.session_state:
        st.sidebar.header("🔑 Fyers Secure Login")
        session = SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
        auth_url = session.generate_authcode()
        
        st.sidebar.markdown(f'''<a href="{auth_url}" target="_blank"><button style="width:100%; background-color:#ff4b4b; color:white; border:none; padding:12px; border-radius:5px; cursor:pointer; font-weight:bold;">1. Click to Login with Fyers</button></a>''', unsafe_allow_html=True)
        st.sidebar.write("---")
        full_url = st.sidebar.text_input("2. Pura Google URL yahan paste karein:")
        
        if st.sidebar.button("3. Generate Access Token 🚀"):
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

# --- 3. OPTIONS & SCANNER LOGIC ---
def get_opt_sym(stock, ltp, type="CE"):
    expiry = "16APR26" # Upcoming Expiry
    step = 100 if "NIFTY" in stock else 100 if "BANK" in stock else 10
    strike = round(ltp / step) * step
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{int(strike)}{type}"

# --- 4. PRO UI LAYOUT ---
st.set_page_config(layout="wide", page_title="Pro OHL Scanner")
st.markdown("""<style> .main { background-color: #0e1117; } .stTable { font-size: 20px; } </style>""", unsafe_allow_html=True)

st.title("🔥 Pro Intraday OHL & Gainer Scanner")

fyers = get_fyers_instance()

if fyers:
    # Top FNO Stocks + Index
    watch_list = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX", "NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:HDFCBANK-EQ", "NSE:ICICIBANK-EQ", "NSE:TATASTEEL-EQ"]
    
    results = []
    today = datetime.date.today().strftime('%Y-%m-%d')

    with st.spinner("🚀 Market Data Scan Jari Hai..."):
        for s in watch_list:
            try:
                q_res = fyers.quotes({"symbols": s})
                ltp = q_res['d'][0]['v']['lp']
                
                # Check Stock, ATM Call, ATM Put
                syms = [s, get_opt_sym(s, ltp, "CE"), get_opt_sym(s, ltp, "PE")]
                
                for sym in syms:
                    res = fyers.history(data={"symbol": sym, "resolution": "15", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
                    if res['s'] == 'ok' and len(res['candles']) > 0:
                        df = pd.DataFrame(res['candles'], columns=['T','O','H','L','C','V'])
                        o, h, l, c = df.iloc[0]['O'], df['H'].max(), df['L'].min(), df.iloc[-1]['C']
                        change = round(((c - o) / o) * 100, 2)
                        
                        signal = "Neutral"
                        if o == l: signal = "🟩 BUY (O=L)"
                        elif o == h: signal = "🟥 SELL (O=H)"
                        
                        if change > 2.5: signal += " | 🚀 GAINER"
                        
                        results.append({"SYMBOL": sym, "SIGNAL": signal, "LTP": c, "% CHG": change, "DAY HIGH": h, "DAY LOW": l})
            except: continue

    # Grid Display
    col1, col2 = st.columns([1.2, 1.8])
    
    with col1:
        st.subheader("📊 Scanner Results")
        if results:
            df_res = pd.DataFrame(results).sort_values(by="% CHG", ascending=False)
            # Highlighting Signal Column
            def color_sig(val):
                if 'BUY' in val: return 'background-color: #004d00'
                if 'SELL' in val: return 'background-color: #4d0000'
                return ''
            
            selected = st.selectbox("Select Stock for Chart:", df_res['SYMBOL'].tolist())
            st.dataframe(df_res.style.applymap(color_sig, subset=['SIGNAL']), height=600)
            if st.button("🔄 Refresh Market Data"): st.rerun()
        else:
            st.info("9:30 AM ke baad data milna shuru hoga.")

    with col2:
        if 'selected' in locals():
            st.subheader(f"📈 Live 5-Min Chart: {selected}")
            c_res = fyers.history(data={"symbol": selected, "resolution": "5", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
            if c_res['s'] == 'ok' and len(c_res['candles']) > 0:
                c_df = pd.DataFrame(c_res['candles'], columns=['T', 'O', 'H', 'L', 'C', 'V'])
                fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(c_df['T'], unit='s'), open=c_df['O'], high=c_df['H'], low=c_df['L'], close=c_df['C'])])
                fig.update_layout(template="plotly_dark", height=600, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("👈 Sidebar se Login karke start karein.")
