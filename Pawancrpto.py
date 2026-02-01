import streamlit as st
import pandas as pd
import numpy as np
import datetime
import ccxt
import pandas_ta as ta

# --- 1. SETTINGS & THEME ---
st.set_page_config(page_title="PAWAN ALGO SYSTEM V5", layout="wide", initial_sidebar_state="expanded")

# CSS Styling - Premium Dark Mode
st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #00FBFF; margin-bottom: 20px; }
    .m-table { width: 100%; border-collapse: collapse; background: #0B1629; color: white; }
    .m-table th { background-color: #1E293B; color: #94A3B8; padding: 12px; text-align: left; border-bottom: 2px solid #00FBFF; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1E293B; font-size: 14px; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.3; } }
    .audit-card { background: #0B1629; padding: 15px; border-radius: 8px; border: 1px solid #1E293B; margin-bottom: 10px; }
    .stButton>button { width: 100%; background-color: #00FBFF; color: black; font-weight: bold; border-radius: 8px; border: none; }
    .stButton>button:hover { background-color: #00d1d4; color: black; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE (NO KEYS REQUIRED) ---
def get_market_data():
    # Public connection - No API Key needed for data fetching
    ex = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
    results = []
    # Targeted high-volatility pairs
    pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", "AVAX/USDT"]
    
    try:
        for s in pairs:
            ohlcv = ex.fetch_ohlcv(s, timeframe='5m', limit=100)
            if not ohlcv: continue
            
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            # Technical Indicators
            st_data = ta.supertrend(df['h'], df['l'], df['c'], length=10, multiplier=3.0)
            bb_data = ta.bbands(df['c'], length=20, std=2)
            macd_data = ta.macd(df['c'])
            rsi_data = ta.rsi(df['c'], length=14)
            df = pd.concat([df, st_data, bb_data, macd_data, rsi_data], axis=1)
            
            # Column mapping
            st_col = [c for c in df.columns if "SUPERT_" in c and "d" not in c.lower()][0]
            bbm_col = [c for c in df.columns if "BBM_" in c][0]
            bbu_col = [c for c in df.columns if "BBU_" in c][0]
            bbl_col = [c for c in df.columns if "BBL_" in c][0]
            macdh_col = [c for c in df.columns if "MACDh_" in c][0]
            macd_col = [c for c in df.columns if c.startswith("MACD_")][0]
            rsi_col = [c for c in df.columns if "RSI_" in c][0]

            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # --- TITAN GHOST RESISTANCE ---
            # Finding the max high of the previous Red Supertrend segment
            red_mask = df[st_col] > df['c']
            titan_res = 0.0
            if any(red_mask):
                # We look back at the most recent red segment
                titan_res = df.loc[red_mask, 'h'].max()

            # --- THE PRECIOUS FORMULA CHECK ---
            c1 = last[st_col] < last['c']                   # ST is Green
            c2 = last[macdh_col] > prev[macdh_col]          # MACD Histogram rising
            c3 = last[macd_col] > 0                         # MACD Line > 0
            c4 = last['c'] > last[bbm_col]                  # Price > Middle BB
            c5 = last[bbu_col] > prev[bbu_col]              # Upper BB sloping up
            c6 = last[st_col] > titan_res if (c1 and titan_res > 0) else False # Ghost Breakout
            c7 = last[rsi_col] >= 70                        # RSI 70+
            
            # CALL SHIELD (No Trade Zone)
            # Logic: If Supertrend Green is BELOW Lower BB
            call_shield = last[st_col] < last[bbl_col]
            
            is_pink = (c1 and c2 and c3 and c4 and c5 and c6 and c7) and not call_shield
            
            results.append({
                "Symbol": s, 
                "LTP": last['c'], 
                "ST": last[st_col],
                "Prev_Red_High": titan_res, 
                "Pink": is_pink, 
                "Shield": call_shield,
                "Points": [c1, c2, c3, c4, c5, c6, c7], 
                "Target": s.replace("/", ""), 
                "Time": datetime.datetime.fromtimestamp(last['t']/1000).strftime('%H:%M')
            })
        return results, None
    except Exception as e:
        return [], str(e)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color:#00FBFF;'>🏹 TITAN V5</h1>", unsafe_allow_html=True)
    page = st.radio("MENU", ["Live Scanner", "7-Point Audit", "Charts"])
    st.divider()
    
    # MANUAL REFRESH ONLY
    if st.button("🚀 SCAN MARKETS NOW"):
        st.cache_data.clear()
        st.rerun()
        
    st.info("Manual Mode: Background processes are disabled to conserve resources.")

# Status Bar
st.markdown(f"""
<div class="status-strip">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span><b>MODE:</b> <span style="color:#00FBFF">PRECIOUS 2026</span></span>
        <span><b>GHOST RESISTANCE:</b> ENABLED</span>
        <span><b>API:</b> PUBLIC (NO KEY)</span>
        <span><b>LAST SCAN:</b> {datetime.datetime.now().strftime("%H:%M:%S")}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Execution
data, err = get_market_data()

if err:
    st.error(f"API Error: {err}")

if page == "Live Scanner":
    if data:
        html = """<table class="m-table">
        <tr><th>Symbol</th><th>LTP</th><th>ST Green</th><th>Prev Red High</th><th>Pink Alert</th><th>Trigger</th></tr>"""
        for d in data:
            status = '<span class="pink-alert">💎 BREAKOUT</span>' if d['Pink'] else '<span style="color:#475569">WAIT</span>'
            trigger = '<b style="color:lime">ON</b>' if d['Pink'] else '<span style="color:grey">OFF</span>'
            
            # Apply Shield Warning if active
            symbol_display = d['Symbol']
            if d['Shield']:
                symbol_display = f"⚠️ {d['Symbol']} (SHIELDED)"

            html += f"""<tr>
                <td style="color:#00FBFF"><b>{symbol_display}</b></td>
                <td>{d['LTP']:.4f}</td>
                <td>{d['ST']:.4f}</td>
                <td>{d['Prev_Red_High']:.4f}</td>
                <td>{status}</td>
                <td>{trigger}</td>
            </tr>"""
        st.markdown(html + "</table>", unsafe_allow_html=True)
    else:
        st.warning("No data found. Please trigger a manual scan.")

elif page == "7-Point Audit":
    st.subheader("Titan V5 Formula Verification")
    if data:
        for d in data:
            p = d['Points']
            st.markdown(f"""
            <div class="audit-card">
                <b>{d['Symbol']} Audit Trace:</b><br>
                {'✅' if p[0] else '❌'} Supertrend Green | 
                {'✅' if p[1] else '❌'} MACD Hist Rising | 
                {'✅' if p[2] else '❌'} MACD Line > 0<br>
                {'✅' if p[3] else '❌'} Price > Mid BB | 
                {'✅' if p[4] else '❌'} Upper BB Rising | 
                {'✅' if p[5] else '❌'} GHOST BREAKOUT (ST > {d['Prev_Red_High']:.2f}) | 
                {'✅' if p[6] else '❌'} RSI 70+
                <br><small style='color:{"#FF69B4" if d["Shield"] else "#00FF00"}'>
                Shield Protection: {'🛡️ CALL SHIELD ACTIVE (NO TRADE)' if d['Shield'] else '🟢 CLEAR TO TRADE'}
                </small>
            </div>
            """, unsafe_allow_html=True)

elif page == "Charts":
    if data:
        sel = st.selectbox("Select Asset", [x['Symbol'] for x in data])
        target = [x['Target'] for x in data if x['Symbol'] == sel][0]
        st.components.v1.html(f"""
            <iframe src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:{target}&interval=5&theme=dark" width="100%" height="550" frameborder="0"></iframe>
        """, height=560)

st.caption("TITAN ALGO SYSTEM V5 | GHOST RESISTANCE PROTOCOL | NO-KEY VERSION")
