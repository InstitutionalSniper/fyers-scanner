import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
from fyers_apiv3 import fyersModel
from fyers_apiv3.fyersModel import SessionModel

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="ALPHA LIVE TERMINAL")
CLIENT_ID = "7PHDU5GN1H-100"  
SECRET_KEY = "8JXSML4ARB"
REDIRECT_URI = "https://google.com" 

# --- 2. THE STABLE LOGIN (FULL GOOGLE URL LOGIC) ---
def get_fyers_instance():
    if 'access_token' not in st.session_state:
        with st.sidebar:
            st.header("🔑 SECURE ACCESS")
            session = SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, 
                                  redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
            auth_url = session.generate_authcode()
            
            st.markdown(f'''<a href="{auth_url}" target="_blank"><button style="width:100%; height:50px; background: #ED1C24; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold;">1. LOGIN WITH FYERS</button></a>''', unsafe_allow_html=True)
            st.write("---")
            
            # Yahan pura URL paste hoga
            full_google_url = st.text_area("2. PASTE FULL GOOGLE URL HERE", height=100, placeholder="https://google.com...")
            
            if st.button("3. GENERATE TERMINAL TOKEN 🚀"):
                if "auth_code=" in full_google_url:
                    try:
                        # URL se auth_code nikalne ka fix
                        auth_code = full_google_url.split("auth_code=")[1].split("&")[0]
                        session.set_token(auth_code)
                        response = session.generate_token()
                        if 'access_token' in response:
                            st.session_state.access_token = response["access_token"]
                            st.success("TERMINAL ONLINE!")
                            st.rerun()
                        else:
                            st.error(f"Token Error: {response}")
                    except Exception as e:
                        st.error(f"URL Error: Sahi se copy karein.")
                else:
                    st.warning("Pura URL paste karein jisme 'auth_code=' ho.")
        return None
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=st.session_state.access_token, log_path="")

# --- 3. OPTIONS SYMBOL GENERATOR ---
def get_opt_sym(stock, ltp, type="CE"):
    expiry = "16APR26" # Current Expiry
    step = 100 if "NIFTY" in stock else 100 if "BANK" in stock else 10
    strike = round(ltp / step) * step
    base = stock.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", "")
    return f"NSE:{base}{expiry}{int(strike)}{type}"

# --- 4. MAIN TERMINAL ---
st.title("⚡ TERMINAL ALPHA: LIVE STOCKS & OPTIONS OHL")
fyers = get_fyers_instance()

if fyers:
    # Top Stocks List
    watch_stocks = ["NSE:NIFTY50-INDEX", "NSE:ADANIENT-EQ", "NSE:SBIN-EQ", "NSE:TATAMOTORS-EQ"]
    today = datetime.date.today().strftime('%Y-%m-%d')
    results = []

    with st.spinner("FETCHING LIVE OHL DATA..."):
        for s in watch_stocks:
            try:
                # 1. Get Live Price for Strike Selection
                q_res = fyers.quotes({"symbols": s})['d'][0]['v']
                ltp = q_res['lp']
                
                # 2. Check Stock + Call + Put
                syms = [s, get_opt_sym(s, ltp, "CE"), get_opt_sym(s, ltp, "PE")]
                
                for sym in syms:
                    res = fyers.history(data={"symbol": sym, "resolution": "15", "date_format": "1", 
                                              "range_from": today, "range_to": today, "cont_flag": "1"})
                    if res['s'] == 'ok' and len(res['candles']) > 0:
                        df = pd.DataFrame(res['candles'], columns=['T','O','H','L','C','V'])
                        # Day's First Candle Data
                        o, h_max, l_min, curr_ltp = df.iloc[0]['O'], df['H'].max(), df['L'].min(), df.iloc[-1]['C']
                        
                        sig = "WAIT"
                        if o == l_min: sig = "🚀 BUY (O=L)"
                        elif o == h_max: sig = "🔻 SELL (O=H)"
                        
                        chg = round(((curr_ltp - o) / o) * 100, 2)
                        results.append({"SYMBOL": sym, "SIGNAL": sig, "LTP": curr_ltp, "% CHG": chg, "OPEN": o, "HIGH": h_max, "LOW": l_min})
            except: continue

    # --- UI RENDERING ---
    if results:
        df_final = pd.DataFrame(results).sort_values(by="% CHG", ascending=False)
        
        # Ticker (Fix for live movers)
        ticker_text = " | ".join([f"{r['SYMBOL']} ({r['% CHG']}%)" for idx, r in df_final.iterrows()])
        st.markdown(f'<marquee style="color: #00ff00; font-size: 20px; background: #000; padding: 10px;">🔥 LIVE TICKER: {ticker_text}</marquee>', unsafe_allow_html=True)

        col1, col2 = st.columns([1.2, 1.8])
        with col1:
            st.subheader("📡 SCANNER")
            selected = st.radio("SELECT ASSET:", df_final['SYMBOL'].tolist())
            def style_sig(val):
                if 'BUY' in val: return 'color: #00ff00; font-weight: bold'
                if 'SELL' in val: return 'color: #ff4b4b; font-weight: bold'
                return ''
            st.dataframe(df_final.style.map(style_sig, subset=['SIGNAL']), use_container_width=True, height=500)
            if st.button("⚡ FORCE REFRESH"): st.rerun()

        with col2:
            st.subheader(f"📊 LIVE CHART: {selected}")
            c_res = fyers.history(data={"symbol": selected, "resolution": "5", "date_format": "1", 
                                        "range_from": today, "range_to": today, "cont_flag": "1"})
            if c_res['s'] == 'ok' and len(c_res['candles']) > 0:
                c_df = pd.DataFrame(c_res['candles'], columns=['T', 'O', 'H', 'L', 'C', 'V'])
                fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(c_df['T'], unit='s'), 
                                                     open=c_df['O'], high=c_df['H'], 
                                                     low=c_df['L'], close=c_df['C'])])
                fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("👈 SIDEBAR SE GOOGLE URL PASTE KAREIN.")
