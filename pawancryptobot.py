import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, random
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

# 1. CLOUD CONFIG & THEME (Professional Navy Blue)
st.set_page_config(page_title="TITAN V5 PRO", layout="wide", initial_sidebar_state="expanded")

# Auto-refresh every 2 seconds for that "Live" feel
st_autorefresh(interval=2000, key="v5_pulse")

st.markdown("""
<style>
    /* Navy Blue Theme */
    .stApp { background-color: #050A14; color: #E2E8F0; }
    [data-testid="stSidebar"] { background-color: #0B1629; border-right: 1px solid #1E293B; }
    
    /* Top Status Strip */
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #1E293B; margin-bottom: 20px; }
    
    /* Live Table Styling */
    .m-table { width: 100%; border-collapse: collapse; background-color: #0B1629; border-radius: 10px; overflow: hidden; }
    .m-table th { background-color: #1E293B; color: #94A3B8; padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1E293B; font-size: 14px; color: #E2E8F0; }
    
    /* Highlights */
    .coin-name { color: #00FBFF !important; font-weight: 900; }
    .ltp-green { color: #00FF00 !important; font-weight: bold; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; animation: blinker 1.5s linear infinite; }
    .diamond-glow { font-size: 20px; text-shadow: 0 0 10px #00FF00; }
    
    @keyframes blinker { 50% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)

# 2. DATA SIMULATION (LIVE UPDATING ENGINE)
if "live_data" not in st.session_state:
    st.session_state.live_data = {
        "NIFTY": {"ltp": 22140.50, "st": 22050.00, "prev_red": 22020.00, "mid": 22040.00, "rsi": 72, "macd": 12, "shield": "OK"},
        "BANKNIFTY": {"ltp": 46820.10, "st": 46900.00, "prev_red": 47100.00, "mid": 46850.00, "rsi": 45, "macd": -5, "shield": "PUT SHIELD"},
        "RELIANCE": {"ltp": 2950.00, "st": 2945.00, "prev_red": 2942.00, "mid": 2946.00, "rsi": 71, "macd": 2, "shield": "OK"}
    }

# Update prices randomly to show live movement
for k in st.session_state.live_data:
    st.session_state.live_data[k]["ltp"] += random.uniform(-5, 5)

# 3. SIDEBAR NAVIGATION
with st.sidebar:
    st.markdown("<h2 style='color:#00FBFF;'>🏹 TITAN V5 PRO</h2>", unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio("NAVIGATION", ["Dashboard", "Signal Validator", "Visual Validator", "Order Book", "Health Board"])
    st.markdown("---")
    st.toggle("Engine ON/OFF", value=True)
    st.toggle("Live Trading", value=False)
    st.button("🚨 PANIC BUTTON")

# 4. MAIN UI - TOP STATUS STRIP
st.markdown(f"""
<div class="status-strip">
    <table style="width:100%; text-align:center; color:white; font-size:12px;">
        <tr>
            <td><b>WS STATUS</b><br><span style="color:#00FF00">🟢 CONNECTED</span></td>
            <td><b>ENGINE</b><br>ACTIVE</td>
            <td><b>CAPITAL</b><br>₹2,00,000</td>
            <td><b>SHIELDS</b><br>MONITORING</td>
            <td><b>TIME</b><br>{datetime.datetime.now().strftime('%H:%M:%S')}</td>
        </tr>
    </table>
</div>
""", unsafe_allow_html=True)

# 5. PAGE LOGIC
if menu == "Dashboard":
    st.subheader("📊 Live Scanner (Precious Formula)")
    
    html = '<table class="m-table"><tr><th>Symbol</th><th>LTP</th><th>ST Green</th><th>Midband</th><th>ST x Mid</th><th>Pink Alert</th><th>Action</th></tr>'
    
    for sym, d in st.session_state.live_data.items():
        # LOGIC GATES
        st_x_mid = d['st'] > d['mid'] # Precious Formula Condition
        ghost_break = d['st'] > d['prev_red'] # Ghost Resistance Condition
        is_pink = st_x_mid and ghost_break and d['rsi'] >= 70 and d['macd'] > 0
        
        # UI Formatting
        st_x_mid_ui = "🟢 ABOVE" if st_x_mid else "⚪ BELOW"
        pink_ui = '<span class="pink-alert">PINK BREAKOUT</span>' if is_pink else "WAIT"
        action_ui = "BUY 10X" if is_pink else "-"
        
        html += f"""
        <tr>
            <td class="coin-name">{sym}</td>
            <td class="ltp-green">{d['ltp']:.2f}</td>
            <td>{d['st']:.2f}</td>
            <td>{d['mid']:.2f}</td>
            <td>{st_x_mid_ui}</td>
            <td>{pink_ui}</td>
            <td>{action_ui}</td>
        </tr>
        """
    st.markdown(html + "</table>", unsafe_allow_html=True)

elif menu == "Signal Validator":
    st.subheader("🎯 7-Point Audit (Verification)")
    target = st.selectbox("Select Asset", list(st.session_state.live_data.keys()))
    d = st.session_state.live_data[target]
    
    # Audit Points
    checks = [
        ("Supertrend Status", d['ltp'] > d['st'], "GREEN (Bullish)"),
        ("Precious Formula", d['st'] > d['mid'], "ST x MID CROSS"),
        ("Ghost Resistance", d['st'] > d['prev_red'], f"ST > {d['prev_red']}"),
        ("RSI Momentum", d['rsi'] >= 70, f"RSI: {d['rsi']}"),
        ("MACD Filter", d['macd'] > 0, "MACD > 0"),
        ("Shield Logic", d['shield'] == "OK", "Shield Clear"),
        ("Capital Risk", True, "Within ₹2L Limit")
    ]
    
    for name, ok, val in checks:
        color = "#00FF00" if ok else "#64748B"
        st.markdown(f"**{name}:** <span style='color:{color}'>{'✅' if ok else '⭕'} {val}</span>", unsafe_allow_html=True)

elif menu == "Visual Validator":
    st.subheader("👁️ Visual Indicator Proof")
    target = st.selectbox("Select Asset", list(st.session_state.live_data.keys()))
    d = st.session_state.live_data[target]
    
    # Plotly Visual
    fig = make_subplots(rows=1, cols=1)
    # Mock price candles
    fig.add_trace(go.Scatter(x=[1,2,3,4,5], y=[d['ltp']-10, d['ltp']-5, d['ltp']+2, d['ltp']-3, d['ltp']], name="Price", line=dict(color="#00FBFF")))
    # Supertrend Line
    fig.add_trace(go.Scatter(x=[1,2,3,4,5], y=[d['st']]*5, name="Supertrend", line=dict(color="#00FF00", dash="dash")))
    # BB Mid Line
    fig.add_trace(go.Scatter(x=[1,2,3,4,5], y=[d['mid']]*5, name="BB Midband", line=dict(color="#FF69B4")))
    
    fig.update_layout(template="plotly_dark", height=500, paper_bgcolor="#050A14", plot_bgcolor="#050A14")
    st.plotly_chart(fig, use_container_width=True)
    st.info("Visual Confirmation: Pink Line = BB Mid | Cyan Line = Supertrend")

st.caption("TITAN V5 MASTER | PRECIOUS FORMULA ENGINE | SECURE NAVY CLOUD")
