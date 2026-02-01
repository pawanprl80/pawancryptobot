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

# Enhanced CSS for high-contrast visibility
st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #00FBFF; margin-bottom: 20px; }
    .m-table { width: 100%; border-collapse: collapse; background: #0B1629; color: white; }
    .m-table th { background-color: #1E293B; color: #94A3B8; padding: 10px; text-align: left; border-bottom: 2px solid #00FBFF; }
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
    # Use public binance for scanning to avoid API blocks
    ex = ccxt.binance({'options': {'defaultType': 'future'}})
    while True:
        try:
            results = []
            pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
            
            for s in pairs:
                ohlcv = ex.fetch_ohlcv(s, timeframe='5m', limit=200) # Increased limit for better resistance finding
                if not ohlcv: continue
                
                df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
                
                # --- Robust Indicator Calculation ---
                # Supertrend (10, 3)
                st_data = ta.supertrend(df['h'], df['l'], df['c'], length=10, multiplier=3.0)
                # Bollinger Bands (20, 2)
                bb_data = ta.bbands(df['c'], length=20, std=2)
                # MACD
                macd_data = ta.macd(df['c'])
                # RSI
                rsi_data = ta.rsi(df['c'], length=14)
                
                df = pd.concat([df, st_data, bb_data, macd_data, rsi_data], axis=1)
                
                # Safe column mapping to prevent KeyError
                # Supertrend columns often vary between SUPERT_10_3.0 and SUPERT_10_3
                st_col = [c for c in df.columns if "SUPERT_" in c][0]
                bbm_col = [c for c in df.columns if "BBM_" in c][0]
                bbu_col = [c for c in df.columns if "BBU_" in c][0]
                bbl_col = [c for c in df.columns if "BBL_" in c][0]
                macdh_col = [c for c in df.columns if "MACDh_" in c][0]
                macd_col = [c for c in df.columns if c.startswith("MACD_")][0]
                rsi_col = [c for c in df.columns if "RSI_" in c][0]

                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                # --- TITAN RESISTANCE (Formula: Max High of previous Red Supertrend) ---
                red_segments = df[df[st_col] > df['c']]
                titan_res = red_segments['h'].max() if not red_segments.empty else 0
                
                # --- THE 7-POINT PRECIOUS AUDIT ---
                p1 = last[st_col] < last['c']                 # ST Green
                p2 = last[macdh_col] > prev[macdh_col]        # MACD Hist Rising
                p3 = last[macd_col] > 0                       # MACD Line Above 0
                p4 = last['c'] > last[bbm_col]                # Precious Cross (Price > Mid)
                p5 = last[bbu_col] > prev[bbu_col]            # BB Upper Rising
                p6 = last[st_col] > titan_res if (p1 and titan_res > 0) else False # TITAN BREAKOUT
                p7 = last[rsi_col] >= 70                      # RSI 70+
                
                # SHIELD (Out of Bounds Protection)
                call_shield = last[st_col] < last[bbl_col]
                
                is_pink = (p1 and p2 and p3 and p4 and p5 and p6 and p7) and not call_shield
                
                results.append({
                    "Symbol": s, "LTP": last['c'], "ST": last[st_col],
                    "TitanRes": titan_res, "Pink": is_pink, "Shield": call_shield,
                    "Points": [p1, p2, p3, p4, p5, p6, p7], "Mid": last[bbm_col]
                })
            
            st.session_state.master_cache["data"] = results
            st.session_state.master_cache["sync"] = datetime.datetime.now().strftime("%H:%M:%S")
            st.session_state.master_cache["error"] = None
        except Exception as e:
            st.session_state.master_cache["error"] = f"KeyError/Logic: {str(e)}"
        time.sleep(5)

# Start Thread
if "bg_loop" not in st.session_state:
    thread = threading.Thread(target=run_pawan_engine, daemon=True)
    thread.start()
    st.session_state.bg_loop = True

# --- 3. UI LAYOUT ---
with st.sidebar:
    st.markdown("<h1 style='color:#00FBFF;'>🏹 PAWAN ALGO</h1>", unsafe_allow_html=True)
    page = st.radio("NAVIGATE", ["Dashboard", "Signal Validator", "Visual Validator"])
    st.divider()
    if st.session_state.master_cache["error"]:
        st.error(st.session_state.master_cache["error"])
    st.write(f"**Last Data Refresh:** {st.session_state.master_cache['sync']}")

# Status Bar
st.markdown(f"""
<div class="status-strip">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span><b>DMA:</b> <span style="color:lime">🟢 LIVE</span></span>
        <span><b>TITAN PROTOCOL:</b> READY</span>
        <span><b>MODE:</b> 2026 PRECIOUS</span>
        <span><b>CAPITAL:</b> ₹2,00,000</span>
    </div>
</div>
""", unsafe_allow_html=True)

data = st.session_state.master_cache["data"]

if not data:
    st.info("🔄 Connecting to Binance Future Streams... Please wait 5-10 seconds.")
    st.spinner("Parsing indicators...")

elif page == "Dashboard":
    html = """<table class="m-table">
    <tr><th>Symbol</th><th>LTP</th><th>ST Green</th><th>Titan Resistance</th><th>Pink Alert</th><th>Signal</th></tr>"""
    for d in data:
        alert = '<span class="pink-alert">💎 PINK ALERT</span>' if d['Pink'] else "SCANNING"
        signal = '<b style="color:lime">BUY 10X</b>' if d['Pink'] else "<span style='color:#475569'>WAIT</span>"
        html += f"""<tr>
            <td style="color:#00FBFF"><b>{d['Symbol']}</b></td>
            <td>{d['LTP']:.2f}</td>
            <td>{d['ST']:.2f}</td>
            <td>{d['TitanRes']:.2f}</td>
            <td>{alert}</td>
            <td>{signal}</td>
        </tr>"""
    st.markdown(html + "</table>", unsafe_allow_html=True)

elif page == "Signal Validator":
    st.subheader("Pawan 7-Point Indicator Signal Check")
    for d in data[:2]:
        p = d['Points']
        with st.expander(f"Audit Log: {d['Symbol']}", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"{'✅' if p[0] else '⭕'} 1. ST Trend: Green")
                st.write(f"{'✅' if p[1] else '⭕'} 2. MACD Hist: Rising")
                st.write(f"{'✅' if p[2] else '⭕'} 3. MACD Line: > 0")
                st.write(f"{'✅' if p[3] else '⭕'} 4. ST > Mid ({d['Mid']:.2f})")
            with c2:
                st.write(f"{'✅' if p[4] else '⭕'} 5. BB Upper: Upward")
                st.write(f"{'✅' if p[5] else '⭕'} 6. Titan Breakout (ST > {d['TitanRes']:.2f})")
                st.write(f"{'✅' if p[6] else '⭕'} 7. RSI: 70+")
            if d['Pink']: st.markdown("<h3 style='color:#FF69B4; text-align:center;'>💎 PINK SIGNAL VALIDATED 💎</h3>", unsafe_allow_html=True)

elif page == "Visual Validator":
    if data:
        pair_to_show = st.selectbox("Select Pair", [d['Symbol'] for d in data])
        target = pair_to_show.replace("/", "")
        st.components.v1.html(f"""
            <iframe src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:{target}&interval=5&theme=dark" width="100%" height="550" frameborder="0"></iframe>
        """, height=560)

st.caption("PAWAN ALGO SYSTEM V5 | 2026 PRECIOUS FORMULA | UPDATED TITAN RULES")
