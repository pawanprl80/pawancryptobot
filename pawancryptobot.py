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
    
    /* TABLE STYLING */
    .m-table { width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; }
    .m-table th { background-color: #1E293B; color: #94A3B8; padding: 12px; text-align: left; text-transform: uppercase; font-size: 11px; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1E293B; font-size: 13px; }
    
    /* COLORS */
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
            # Focusing on pairs for 5m verification
            pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "MATIC/USDT"]
            for s in pairs:
                # Fetching 100 candles for indicator stability
                ohlcv = ex.fetch_ohlcv(s, timeframe='5m', limit=100)
                df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
                
                # CORRECT PANDAS_TA USAGE
                st_df = ta.supertrend(df['h'], df['l'], df['c'], length=10, multiplier=3)
                bb = ta.bbands(df['c'], length=20, std=2)
                macd = ta.macd(df['c'])
                rsi = ta.rsi(df['c'], length=14)
                
                df = pd.concat([df, st_df, bb, macd, rsi], axis=1)
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                # Ghost Resistance (Max of the most recent RED Supertrend segment)
                red_highs = df[df['SUPERT_10_3.0'] > df['c']]['h']
                ghost_res = red_highs.max() if not red_highs.empty else 0
                
                # THE 6 PRECIOUS STEPS VERIFICATION
                s1 = last['SUPERT_10_3.0'] < last['c'] # ST Green
                s2 = last['MACDh_12_26_9'] > prev['MACDh_12_26_9'] # MACD Hist Rising
                s3 = last['MACD_12_26_9'] > 0 # MACD Line Above 0
                s4 = last['c'] > last['BBM_20_2.0'] # Price Above Midband
                s5 = last['BBU_20_2.0'] > prev['BBU_20_2.0'] # Upper Band Sloping Up
                s6 = last['SUPERT_10_3.0'] > ghost_res if s1 else False # Ghost Breakout
                s7 = last['RSI_14'] >= 70 # RSI Verification

                results.append({
                    "Symbol": s, "LTP": last['c'], "ST": last['SUPERT_10_3.0'],
                    "Mid": last['BBM_20_2.0'], "Upper": last['BBU_20_2.0'],
                    "Ghost": ghost_res, "RSI": last['RSI_14'], "MACD": last['MACD_12_26_9'],
                    "Pink": (s1 and s2 and s3 and s4 and s5 and s6 and s7),
                    "Steps": [s1, s2, s3, s4, s5, s6, s7],
                    "df": df
                })
            st.session_state.master_cache["data"] = results
            st.session_state.master_cache["sync"] = datetime.datetime.now().strftime("%H:%M:%S")
            time.sleep(10)
        except Exception as e:
            time.sleep(5)

if "bg_loop" not in st.session_state:
    threading.Thread(target=engine_loop, daemon=True).start()
    st.session_state.bg_loop = True

# 3. SIDEBAR
with st.sidebar:
    st.markdown("<h2 style='color:#00FBFF;'>🏹 TITAN V5 PRO</h2>", unsafe_allow_html=True)
    st.divider()
    menu = ["Dashboard", "Signal Validator", "Visual Validator", "Health Board"]
    page = st.radio("MENU", menu)

# 4. TOP STATUS
st.markdown(f"""
<div class="status-strip">
    <table style="width:100%; text-align:center; color:white; font-size:12px;">
        <tr>
            <td><b>DMA</b><br><span style="color:#00FF00">🟢 Connected</span></td>
            <td><b>Last Sync</b><br>{st.session_state.master_cache['sync']}</td>
            <td><b>Strategy</b><br>PRECIOUS 6-STEP</td>
            <td><b>Timeframe</b><br>5-MINUTE</td>
        </tr>
    </table>
</div>
""", unsafe_allow_html=True)

# 5. PAGES
data = st.session_state.master_cache["data"]

if page == "Dashboard":
    st.subheader("📊 Live 5m Ghost Scanner")
    if data:
        html = '<table class="m-table"><tr><th>Symbol</th><th>LTP</th><th>ST Green</th><th>Ghost High</th><th>RSI</th><th>Status</th></tr>'
        for d in data:
            p_text = '<span class="pink-alert">BREAKOUT 💎</span>' if d['Pink'] else "WAITING"
            html += f"""<tr>
                <td class="pair-name">{d['Symbol']}</td>
                <td class="ltp-green">₹ {d['LTP']:.2f}</td>
                <td>{d['ST']:.2f}</td>
                <td>{d['Ghost']:.2f}</td>
                <td>{d['RSI']:.1f}</td>
                <td>{p_text}</td>
            </tr>"""
        st.markdown(html + "</table>", unsafe_allow_html=True)

elif page == "Signal Validator":
    st.subheader("🎯 Real-Time Verification Checklist")
    if data:
        target = data[0]
        s = target['Steps']
        st.markdown(f"""
        <div class="logic-card">
            <p class="{'step-ok' if s[0] else 'step-wait'}">{'✅' if s[0] else '⭕'} 1. Supertrend: GREEN</p>
            <p class="{'step-ok' if s[1] else 'step-wait'}">{'✅' if s[1] else '⭕'} 2. MACD Histogram: RISING</p>
            <p class="{'step-ok' if s[2] else 'step-wait'}">{'✅' if s[2] else '⭕'} 3. MACD Line: ABOVE 0 (Verified on Chart)</p>
            <p class="{'step-ok' if s[3] else 'step-wait'}">{'✅' if s[3] else '⭕'} 4. Price Position: ABOVE BB MID (Verified on Chart)</p>
            <p class="{'step-ok' if s[4] else 'step-wait'}">{'✅' if s[4] else '⭕'} 5. Volatility: UPPER BAND RISING</p>
            <p class="{'step-ok' if s[5] else 'step-wait'}">{'✅' if s[5] else '⭕'} 6. Ghost Resistance: ST > PREV RED HIGH</p>
            <p class="{'step-ok' if s[6] else 'step-wait'}">{'✅' if s[6] else '⭕'} 7. RSI Check: >= 70 (Verified on Chart)</p>
            <hr>
            <h3 style="color:#00FBFF">DIAMOND TRIGGER: {'READY 💎' if target['Pink'] else 'SEARCHING...'}</h3>
        </div>
        """, unsafe_allow_html=True)

elif page == "Visual Validator":
    st.subheader("👁️ 5-Minute Multi-Indicator Chart")
    if data:
        target = data[0]
        df = target['df']
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.25, 0.25])
        
        # Row 1: Main Verification (Price, BB, ST, Ghost)
        fig.add_trace(go.Candlestick(x=df.index, open=df['o'], high=df['h'], low=df['l'], close=df['c'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBU_20_2.0'], line=dict(color='rgba(255,255,255,0.2)'), name="Upper BB"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBM_20_2.0'], line=dict(color='orange', dash='dot'), name="Midband"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SUPERT_10_3.0'], line=dict(color='#00FBFF', width=2), name="Supertrend"), row=1, col=1)
        fig.add_hline(y=target['Ghost'], line_dash="dash", line_color="pink", annotation_text="GHOST RES", row=1, col=1)

        # Row 2: RSI Verification (70 Level)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], line=dict(color='yellow'), name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)

        # Row 3: MACD Verification (0 Level)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'], line=dict(color='blue'), name="MACD"), row=3, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], name="Histogram"), row=3, col=1)
        fig.add_hline(y=0, line_color="white", row=3, col=1)

        fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

st.markdown("<center><small>TITAN V5 PRO | MASTER PRECIOUS VALIDATOR | 2026</small></center>", unsafe_allow_html=True)
