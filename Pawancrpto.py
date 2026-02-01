import sys
import subprocess

# --- AUTOMATIC LIBRARY INSTALLER ---
def install_missing_libraries():
    required_libraries = ["ccxt", "pandas-ta", "plotly", "streamlit-autorefresh"]
    for lib in required_libraries:
        try:
            if lib == "pandas-ta":
                import pandas_ta
            else:
                __import__(lib.replace("-", "_"))
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

# Run installer before anything else
install_missing_libraries()

import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, threading
import ccxt
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

# 1. SETUP & THEME (AngelOne Dark Navy)
st.set_page_config(page_title="TITAN V5 PRO", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=5000, key="v5_visual_verify")

st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    [data-testid="stSidebar"] { background-color: #0B1629; border-right: 1px solid #1E293B; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #2D3748; margin-bottom: 20px; }
    
    .m-table { width: 100%; border-collapse: collapse; }
    .m-table th { background-color: #1E293B; color: #94A3B8; padding: 12px; text-align: left; text-transform: uppercase; font-size: 11px; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1E293B; font-size: 13px; }
    
    .pair-name { color: #00FBFF !important; font-weight: 900; }
    .ltp-green { color: #00FF00 !important; font-weight: bold; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; animation: blinker 1.5s linear infinite; }
    
    .logic-card { background: #1A263E; padding: 20px; border-radius: 8px; border-left: 5px solid #00FBFF; margin-bottom: 15px; }
    .step-ok { color: #00FF00; font-weight: bold; }
    .step-wait { color: #64748B; }
    @keyframes blinker { 50% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)

# 2. BACKGROUND ENGINE (5m VERIFICATION)
if "master_cache" not in st.session_state:
    st.session_state.master_cache = {"data": [], "sync": "Never"}

def engine_loop():
    ex = ccxt.binance()
    while True:
        try:
            results = []
            pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "MATIC/USDT"]
            for s in pairs:
                ohlcv = ex.fetch_ohlcv(s, timeframe='5m', limit=100)
                df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
                
                # Indicators Calculation
                st_df = ta.supertrend(df['h'], df['l'], df['c'], length=10, multiplier=3)
                bb = ta.bbands(df['c'], length=20, std=2)
                macd = ta.macd(df['c'])
                rsi = ta.rsi(df['c'], length=14)
                
                df = pd.concat([df, st_df, bb, macd, rsi], axis=1)
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                # GHOST RESISTANCE: Max high of last RED Supertrend segment
                red_highs = df[df['SUPERT_10_3.0'] > df['c']]['h']
                ghost_res = red_highs.max() if not red_highs.empty else 0
                
                # THE 6 PRECIOUS STEPS VERIFICATION
                s1 = last['SUPERT_10_3.0'] < last['c'] # ST Green
                s2 = last['MACDh_12_26_9'] > prev['MACDh_12_26_9'] # MACD Rising
                s3 = last['MACD_12_26_9'] > 0 # MACD > 0
                s4 = last['c'] > last['BBM_20_2.0'] # Price > Midband
                s5 = last['BBU_20_2.0'] > prev['BBU_20_2.0'] # Upper Band Rising
                s6 = last['SUPERT_10_3.0'] > ghost_res if s1 else False # Ghost Breakout
                s7 = last['RSI_14'] >= 70 # RSI Verification

                is_pink = (s1 and s2 and s3 and s4 and s5 and s6 and s7)

                results.append({
                    "Symbol": s, "LTP": last['c'], "ST": last['SUPERT_10_3.0'],
                    "Mid": last['BBM_20_2.0'], "Upper": last['BBU_20_2.0'],
                    "Ghost": ghost_res, "RSI": last['RSI_14'], "MACD": last['MACD_12_26_9'],
                    "Pink": is_pink, "Steps": [s1, s2, s3, s4, s5, s6, s7], "df": df
                })
            st.session_state.master_cache["data"] = results
            st.session_state.master_cache["sync"] = datetime.datetime.now().strftime("%H:%M:%S")
            time.sleep(10)
        except:
            time.sleep(5)

if "bg_loop" not in st.session_state:
    threading.Thread(target=engine_loop, daemon=True).start()
    st.session_state.bg_loop = True

# 3. SIDEBAR
with st.sidebar:
    st.markdown("<h2 style='color:#00FBFF;'>🏹 TITAN V5 PRO</h2>", unsafe_allow_html=True)
    page = st.radio("MENU", ["Dashboard", "Signal Validator", "Visual Validator", "Indicator Values"])

# 4. TOP STATUS
st.markdown(f"""
<div class="status-strip">
    <table style="width:100%; text-align:center; color:white; font-size:12px;">
        <tr>
            <td><b>DMA</b><br><span style="color:#00FF00">🟢 Active</span></td>
            <td><b>Sync</b><br>{st.session_state.master_cache['sync']}</td>
            <td><b>Formula</b><br>PRECIOUS 6-STEP</td>
            <td><b>Shields</b><br><span style="color:#94A3B8">OFF</span></td>
        </tr>
    </table>
</div>
""", unsafe_allow_html=True)

# 5. PAGES
data = st.session_state.master_cache["data"]

if page == "Dashboard":
    if data:
        html = '<table class="m-table"><tr><th>Symbol</th><th>LTP</th><th>ST Green</th><th>Ghost High</th><th>RSI</th><th>Pink Alert</th></tr>'
        for d in data:
            p_text = '<span class="pink-alert">{PINK} BREAKOUT</span>' if d['Pink'] else "-"
            html += f"<tr><td class='pair-name'>{d['Symbol']}</td><td class='ltp-green'>₹ {d['LTP']:.2f}</td><td>{d['ST']:.2f}</td><td>{d['Ghost']:.2f}</td><td>{d['RSI']:.1f}</td><td>{p_text}</td></tr>"
        st.markdown(html + "</table>", unsafe_allow_html=True)

elif page == "Signal Validator":
    if data:
        target = data[0]
        s = target['Steps']
        st.markdown(f"""
        <div class="logic-card">
            <p class="{'step-ok' if s[0] else 'step-wait'}">{'✅' if s[0] else '⭕'} 1. Supertrend: GREEN</p>
            <p class="{'step-ok' if s[1] else 'step-wait'}">{'✅' if s[1] else '⭕'} 2. MACD Histogram: RISING</p>
            <p class="{'step-ok' if s[2] else 'step-wait'}">{'✅' if s[2] else '⭕'} 3. MACD Line: ABOVE 0</p>
            <p class="{'step-ok' if s[3] else 'step-wait'}">{'✅' if s[3] else '⭕'} 4. Price Position: ABOVE BB MID</p>
            <p class="{'step-ok' if s[4] else 'step-wait'}">{'✅' if s[4] else '⭕'} 5. Volatility: UPPER BAND RISING</p>
            <p class="{'step-ok' if s[5] else 'step-wait'}">{'✅' if s[5] else '⭕'} 6. Ghost Resistance: ST > PREV RED HIGH</p>
            <p class="{'step-ok' if s[6] else 'step-wait'}">{'✅' if s[6] else '⭕'} 7. RSI Check: >= 70</p>
            <hr>
            <h3 style="color:#00FBFF">DIAMOND TRIGGER: {'READY 💎' if target['Pink'] else 'SEARCHING...'}</h3>
        </div>
        """, unsafe_allow_html=True)

elif page == "Visual Validator":
    if data:
        target = data[0]
        df = target['df']
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.25, 0.25])
        fig.add_trace(go.Candlestick(x=df.index, open=df['o'], high=df['h'], low=df['l'], close=df['c'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBM_20_2.0'], line=dict(color='orange', dash='dot'), name="Midband"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SUPERT_10_3.0'], line=dict(color='#00FBFF', width=2), name="Supertrend"), row=1, col=1)
        fig.add_hline(y=target['Ghost'], line_dash="dash", line_color="pink", annotation_text="GHOST RES", row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], line=dict(color='yellow'), name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'], line=dict(color='blue'), name="MACD"), row=3, col=1)
        fig.add_hline(y=0, line_color="white", row=3, col=1)
        fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("<center><small>TITAN V5 PRO | 6-STEP PRECIOUS | 2026 MASTER</small></center>", unsafe_allow_html=True)
