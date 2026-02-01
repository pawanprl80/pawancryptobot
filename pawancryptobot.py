import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, threading

# Error Handling for Imports
try:
    import ccxt
    import pandas_ta as ta
except ImportError:
    st.error("Missing Libraries! Please run: pip install ccxt pandas_ta")
    st.stop()

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

# 1. SETUP & THEME
st.set_page_config(page_title="TITAN V5 PRO", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=5000, key="v5_master_pulse")

# Custom UI Styling (AngelOne Dark Navy Theme)
st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    [data-testid="stSidebar"] { background-color: #0B1629; border-right: 1px solid #1E293B; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #2D3748; margin-bottom: 20px; }
    .m-table { width: 100%; border-collapse: collapse; }
    .m-table th { background-color: #1E293B; color: #94A3B8; padding: 12px; text-align: left; font-size: 11px; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1E293B; font-size: 13px; }
    .pair-name { color: #00FBFF !important; font-weight: 900; }
    .ltp-green { color: #00FF00 !important; font-weight: bold; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)

# 2. ENGINE (PRECIOUS 6-STEP + GHOST RESISTANCE)
if "master_cache" not in st.session_state:
    st.session_state.master_cache = {"data": [], "sync": "Never"}

def engine_loop():
    # Initialize Binance Exchange via CCXT
    ex = ccxt.binance()
    while True:
        try:
            results = []
            pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "MATIC/USDT"]
            for s in pairs:
                # Fetch 5m candles
                ohlcv = ex.fetch_ohlcv(s, timeframe='5m', limit=100)
                df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
                
                # Indicators via pandas_ta
                st_df = ta.supertrend(df['h'], df['l'], df['c'], length=10, multiplier=3)
                bb = ta.bbands(df['c'], length=20, std=2)
                macd = ta.macd(df['c'])
                rsi = ta.rsi(df['c'], length=14)
                
                df = pd.concat([df, st_df, bb, macd, rsi], axis=1)
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                # GHOST RESISTANCE LOGIC
                # Identify the max high of the most recent RED Supertrend segment
                red_zone = df[df['SUPERT_10_3.0'] > df['c']]
                ghost_res = red_zone['h'].max() if not red_zone.empty else 0
                
                # 6-STEP PRECIOUS VERIFICATION (YOUR 2026 RULES)
                s1 = last['SUPERT_10_3.0'] < last['c']        # ST is Green
                s2 = last['MACDh_12_26_9'] > prev['MACDh_12_26_9'] # MACD Hist Rising
                s3 = last['MACD_12_26_9'] > 0                 # MACD Line > 0
                s4 = last['c'] > last['BBM_20_2.0']           # Price > Midband
                s5 = last['BBU_20_2.0'] > prev['BBU_20_2.0']  # Upper Band Rising
                s6 = last['SUPERT_10_3.0'] > ghost_res if s1 else False # ST_Green > Prev_Red_High
                s7 = last['RSI_14'] >= 70                     # RSI 70 Breakout

                is_pink = (s1 and s2 and s3 and s4 and s5 and s6 and s7)

                results.append({
                    "Symbol": s, "LTP": last['c'], "ST": last['SUPERT_10_3.0'],
                    "Ghost": ghost_res, "RSI": last['RSI_14'], "MACD": last['MACD_12_26_9'],
                    "Pink": is_pink, "df": df
                })
            st.session_state.master_cache["data"] = results
            st.session_state.master_cache["sync"] = datetime.datetime.now().strftime("%H:%M:%S")
            time.sleep(10)
        except Exception as e:
            time.sleep(5)

if "bg_loop" not in st.session_state:
    threading.Thread(target=engine_loop, daemon=True).start()
    st.session_state.bg_loop = True

# 3. SIDEBAR (13 Sections Concept)
with st.sidebar:
    st.markdown("<h2 style='color:#00FBFF;'>🏹 TITAN V5 PRO</h2>", unsafe_allow_html=True)
    page = st.radio("NAVIGATION", ["Dashboard", "Signal Validator", "Visual Validator", "Health Board"])
    st.divider()
    st.toggle("DMA ENGINE", value=True)
    st.caption("2026 PRECIOUS FORMULA ACTIVE")

# 4. TOP STRIP
st.markdown(f"""
<div class="status-strip">
    <table style="width:100%; text-align:center; color:white; font-size:12px;">
        <tr>
            <td><b>CONNECTION</b><br><span style="color:#00FF00">🟢 CCXT Live</span></td>
            <td><b>SYNC</b><br>{st.session_state.master_cache['sync']}</td>
            <td><b>GHOST MODE</b><br><span style="color:#00FBFF">ACTIVE</span></td>
            <td><b>SHIELDS</b><br>OFF</td>
        </tr>
    </table>
</div>
""", unsafe_allow_html=True)

# 5. PAGE ROUTING
data = st.session_state.master_cache["data"]

if page == "Dashboard":
    if data:
        html = '<table class="m-table"><tr><th>Symbol</th><th>LTP</th><th>ST Green</th><th>Ghost High</th><th>Pink Alert</th><th>Trigger</th></tr>'
        for d in data:
            pink_status = '<span class="pink-alert">{PINK} BREAKOUT</span>' if d['Pink'] else "No"
            html += f"""<tr>
                <td class="pair-name">{d['Symbol']}</td>
                <td class="ltp-green">₹ {d['LTP']:.2f}</td>
                <td>{d['ST']:.2f}</td>
                <td>{d['Ghost']:.2f}</td>
                <td>{pink_status}</td>
                <td style="color:#00FBFF">{'ON' if d['Pink'] else 'WAIT'}</td>
            </tr>"""
        st.markdown(html + "</table>", unsafe_allow_html=True)

elif page == "Visual Validator":
    if data:
        target = data[0]
        df = target['df']
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=df.index, open=df['o'], high=df['h'], low=df['l'], close=df['c'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SUPERT_10_3.0'], line=dict(color='#00FBFF'), name="ST"), row=1, col=1)
        fig.add_hline(y=target['Ghost'], line_dash="dash", line_color="pink", row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("<center><small>TITAN V5 | CCXT DMA | GHOST BREAKOUT | 2026</small></center>", unsafe_allow_html=True)
