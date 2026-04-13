import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from fyers_apiv3 import fyersModel
from fyers_apiv3.fyersModel import SessionModel

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="ALPHA LIVE TERMINAL")
CLIENT_ID = "7PHDU5GN1H-100"  
SECRET_KEY = "8JXSML4ARB"
REDIRECT_URI = "https://google.com" 

# --- 2. LOGIN (KEEP SAME) ---
def get_fyers_instance():
    if 'access_token' not in st.session_state:
        with st.sidebar:
            session = SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
            st.markdown(f'''<a href="{session.generate_authcode()}" target="_blank"><button style="width:100%; height:50px; background: #ED1C24; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold;">1. LOGIN FYERS</button></a>''', unsafe_allow_html=True)
            full_url = st.text_area("2. PASTE FULL URL")
            if st.button("3. START SCANNER"):
                try:
                    auth_code = full_url.split("auth_code=").split("&")
                    session.set_token(auth_code)
                    st.session_state.access_token = session.generate_token()["access_token"]
                    st.rerun()
                except: st.error("Login Error!")
        return None
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- 3. LIVE SCANNER ENGINE ---
st.title("⚡ LIVE TERMINAL: OHL & FNO GAINERS")
fyers = get_fyers_instance()

if fyers:
    # Top FNO Stocks (Adani Power included)
    master_list = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX", "NSE:ADANIPOWER-EQ", "NSE:TATAMOTORS-EQ", "NSE:RELIANCE-EQ", "NSE:SBIN-EQ", "NSE:HDFCBANK-EQ", "NSE:TATASTEEL-EQ", "NSE:ADANIENT-EQ"]
    
    today = datetime.date.today().strftime('%Y-%m-%d')
    results = []

    for s in master_list:
        try:
            # LIVE DATA FOR OHL
            res = fyers.history(data={"symbol": s, "resolution": "15", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
            if res['s'] == 'ok' and len(res['candles']) > 0:
                df = pd.DataFrame(res['candles'], columns=['T','O','H','L','C','V'])
                # First Candle Data
                first_o = df.iloc[0]['O']
                day_h = df['H'].max()
                day_l = df['L'].min()
                ltp = df.iloc[-1]['C']
                
                # Signal Logic
                sig = "NORMAL"
                if first_o == day_l: sig = "🚀 BUY (O=L)"
                elif first_o == day_h: sig = "🔻 SELL (O=H)"
                
                chg = round(((ltp - first_o) / first_o) * 100, 2)
                results.append({"SYMBOL": s, "SIGNAL": sig, "LTP": ltp, "% CHG": chg, "OPEN": first_o, "HIGH": day_h, "LOW": day_l})
        except: continue

    # UI Rendering
    if results:
        df_final = pd.DataFrame(results).sort_values(by="% CHG", ascending=False)
        
        # Live Ticker
        ticker_text = " | ".join([f"{r['SYMBOL']} ({r['% CHG']}%)" for idx, r in df_final.iterrows()])
        st.markdown(f'<marquee style="color: #00ff00; font-size: 20px; background: #000; padding: 10px;">🔥 LIVE MOVERS: {ticker_text}</marquee>', unsafe_allow_html=True)

        col1, col2 = st.columns([1.2, 1.8])
        with col1:
            st.subheader("📡 SCANNER")
            selected = st.radio("SELECT:", df_final['SYMBOL'].tolist())
            def style_sig(val):
                if 'BUY' in val: return 'color: #00ff00; font-weight: bold'
                if 'SELL' in val: return 'color: #ff4b4b; font-weight: bold'
                return ''
            st.dataframe(df_final.style.applymap(style_sig, subset=['SIGNAL']), use_container_width=True, height=500)
            if st.button("REFRESH"): st.rerun()

        with col2:
            st.subheader(f"📊 CHART: {selected}")
            c_res = fyers.history(data={"symbol": selected, "resolution": "5", "date_format": "1", "range_from": today, "range_to": today, "cont_flag": "1"})
            if c_res['s'] == 'ok':
                c_df = pd.DataFrame(c_res['candles'], columns=['T', 'O', 'H', 'L', 'C', 'V'])
                fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(c_df['T'], unit='s'), open=c_df['O'], high=c_df['H'], low=c_df['L'], close=c_df['C'])])
                fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
