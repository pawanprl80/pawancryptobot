import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, threading
import ccxt
import pandas_ta as ta
from streamlit_autorefresh import st_autorefresh

# --- 1. SETTINGS & THEME ---
st.set_page_config(page_title="PAWAN ALGO SYSTEM V5", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=5000, key="pawan_algo_refresh")

# Enhanced CSS for visibility
st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #00FBFF; margin-bottom: 20px; }
    .m-table { width: 100%; border-collapse: collapse; background: #0B1629; }
    .m-table th { background-color: #1E293B; color: #94A3B8; padding: 10px; text-align: left; }
    .m-table td { padding: 10px; border-bottom: 1px solid #1E293B; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.3; } }
    .audit-box { background: #0B1629; padding: 20px; border-radius: 10px; border: 1px solid #1E293B; line-height: 1.8; }
</style>
""", unsafe_allow_html=True)

# --- 2. THE ENGINE ---
if "master_cache" not in st.session_state:
    st.session_state.master_cache = {"data": [], "sync": "Initializing...", "error": None}

def run_pawan_engine():
    # Using a simple exchange initialization to prevent blocking
    ex = ccxt.binance({'options': {'defaultType': 'future'}})
    while True:
        try:
            results = []
            # Focusing on the most active pairs first
            pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
            
            for s in pairs:
                # Fetch 100 candles (5m timeframe)
                ohlcv = ex.fetch_ohlcv(s, timeframe='5m', limit=100)
                if not ohlcv: continue
                
                df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
                
                # --- Indicators ---
                # Supertrend (10, 3)
                st_df = ta.supertrend(df['h'], df['l'], df['c'], length=10, multiplier=3.0)
                # Bollinger Bands (20, 2)
                bb = ta.bbands(df['c'], length=20, std=2)
                # MACD
                macd = ta.macd(df['c'])
                # RSI
                rsi = ta.rsi(df['c'], length=14)
                
                df = pd.concat([df, st_df, bb, macd, rsi], axis=1)
                
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                # --- TITAN RESISTANCE (The 2026 Rule) ---
                # Find all rows where ST was Red (ST > Price)
                red_segments = df[df['SUPERT_10_3.0'] > df['c']]
                # The Resistance is the High of that Red segment
                titan_res = red_segments['h'].max() if not red_segments.empty else 0
                
                # --- THE 7-POINT PRECIOUS AUDIT ---
                p1 = last['SUPERT_10_3.0'] < last['c']               # ST Green
                p2 = last['MACDh_12_26_9'] > prev['MACDh_12_26_9']   # MACD Hist Rising
                p3 = last['MACD_12_26_9'] > 0                        # MACD Line Above 0
                p4 = last['c'] > last['BBM_20_2.0']                  # Precious Cross (Price > Mid)
                p5 = last['BBU_20_2.0'] > prev['BBU_20_2.0']         # BB Upper Rising
                p6 = last['SUPERT_10_3.0'] > titan_res if (p1 and titan_res > 0) else False # TITAN BREAKOUT
                p7 = last['RSI_14'] >= 70                            # RSI 70+
                
                # SHIELD (Out of Bounds Protection)
                call_shield = last['SUPERT_10_3.0'] < last['BBL_20_2.0']
                
                is_pink = (p1 and p2 and p3 and p4 and p5 and p6 and p7) and not call_shield
                
                results.append({
                    "Symbol": s, "LTP": last['c'], "ST": last['SUPERT_10_3.0'],
                    "TitanRes": titan_res, "Pink": is_pink, "Shield": call_shield,
                    "Points": [p1, p2, p3, p4, p5, p6, p7], "Mid": last['BBM_20_2.0'],
                    "df": df
                })
            
            st.session_state.master_cache["data"] = results
            st.session_state.master_cache["sync"] = datetime.datetime.now().strftime("%H:%M:%S")
            st.session_state.master_cache["error"] = None
        except Exception as e:
            st.session_state.master_cache["error"] = str(e)
        time.sleep(5)

# Start Thread
if "bg_loop" not in st.session_state:
    thread = threading.Thread(target=run_pawan_engine, daemon=True)
    thread.start()
    st.session_state.bg_loop = True

# --- 3. UI ---
with st.sidebar:
    st.title("🏹 PAWAN ALGO")
    page = st.radio("NAV", ["Dashboard", "Signal Validator", "Visual Validator"])
    st.divider()
    if st.session_state.master_cache["error"]:
        st.error(f"Engine Error: {st.session_state.master_cache['error']}")
    st.write(f"**Last Sync:** {st.session_state.master_cache['sync']}")

# Status Bar
st.markdown(f"""
<div class="status-strip">
    <div style="display:flex; justify-content:space-between;">
        <span><b>DMA:</b> 🟢 ACTIVE</span>
        <span><b>TITAN PROTOCOL:</b> READY</span>
        <span><b>SHIELDS:</b> {"<span style='color:lime'>ENABLED</span>"}</span>
        <span><b>CAPITAL:</b> ₹2,00,000</span>
    </div>
</div>
""", unsafe_allow_html=True)

data = st.session_state.master_cache["data"]

if not data:
    st.warning("Waiting for Engine to fetch Binance data... (Make sure you have internet)")
    st.spinner("Connecting to Pulse...")

elif page == "Dashboard":
    html = """<table class="m-table">
    <tr><th>Symbol</th><th>LTP</th><th>ST Green</th><th>Titan Res</th><th>Pink Alert</th><th>Action</th></tr>"""
    for d in data:
        alert = '<span class="pink-alert">💎 BREAKOUT</span>' if d['Pink'] else "WAITING"
        action = '<b style="color:lime">BUY 10X</b>' if d['Pink'] else "-"
        html += f"""<tr>
            <td style="color:#00FBFF"><b>{d['Symbol']}</b></td>
            <td>{d['LTP']:.2f}</td>
            <td>{d['ST']:.2f}</td>
            <td>{d['TitanRes']:.2f}</td>
            <td>{alert}</td>
            <td>{action}</td>
        </tr>"""
    st.markdown(html + "</table>", unsafe_allow_html=True)

elif page == "Signal Validator":
    for d in data[:2]: # Show first two pairs
        p = d['Points']
        st.markdown(f"#### 🎯 Audit: {d['Symbol']}")
        cols = st.columns(2)
        with cols[0]:
            st.write(f"{'✅' if p[0] else '⭕'} 1. ST Green")
            st.write(f"{'✅' if p[1] else '⭕'} 2. MACD Hist Rising")
            st.write(f"{'✅' if p[2] else '⭕'} 3. MACD > 0")
            st.write(f"{'✅' if p[3] else '⭕'} 4. ST > Midband ({d['Mid']:.2f})")
        with cols[1]:
            st.write(f"{'✅' if p[4] else '⭕'} 5. BB Upper Rising")
            st.write(f"{'✅' if p[5] else '⭕'} 6. Titan Breakout (ST > {d['TitanRes']:.2f})")
            st.write(f"{'✅' if p[6] else '⭕'} 7. RSI 70+")
        if d['Pink']: st.success(f"💎 {d['Symbol']} PINK ALERT ACTIVE")
        st.divider()

elif page == "Visual Validator":
    if data:
        target = data[0]['Symbol'].replace("/", "")
        st.components.v1.html(f"""
            <iframe src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:{target}&interval=5&theme=dark" width="100%" height="500" frameborder="0"></iframe>
        """, height=500)

st.caption("PAWAN ALGO V5 | 2026 PRECIOUS RULES | NO GHOST MODE")
