import streamlit as st
import pandas as pd
import numpy as np
import datetime
import ccxt
import pandas_ta as ta

# --- 1. SETTINGS & THEME ---
st.set_page_config(page_title="PAWAN ALGO V5", layout="wide", initial_sidebar_state="expanded")

# Clean, High-Visibility CSS
st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #00FBFF; margin-bottom: 20px; }
    .m-table { width: 100%; border-collapse: collapse; background: #0B1629; color: white; }
    .m-table th { background-color: #1E293B; color: #94A3B8; padding: 12px; text-align: left; border-bottom: 2px solid #00FBFF; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1E293B; font-size: 14px; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; }
    .stButton>button { width: 100%; background-color: #00FBFF; color: black; font-weight: bold; border-radius: 8px; border: none; height: 3em; }
</style>
""", unsafe_allow_html=True)

# --- 2. THE PURE 7-POINT ENGINE ---
def get_market_data():
    # Public connection - No keys
    ex = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
    results = []
    pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", "AVAX/USDT"]
    
    try:
        for s in pairs:
            ohlcv = ex.fetch_ohlcv(s, timeframe='5m', limit=100)
            if not ohlcv: continue
            
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            # Indicators
            st_data = ta.supertrend(df['h'], df['l'], df['c'], length=10, multiplier=3.0)
            bb_data = ta.bbands(df['c'], length=20, std=2)
            macd_data = ta.macd(df['c'])
            rsi_data = ta.rsi(df['c'], length=14)
            df = pd.concat([df, st_data, bb_data, macd_data, rsi_data], axis=1)
            
            # Dynamic Column Fetching
            st_col = [c for c in df.columns if "SUPERT_" in c and "d" not in c.lower()][0]
            bbm_col = [c for c in df.columns if "BBM_" in c][0]
            bbu_col = [c for c in df.columns if "BBU_" in c][0]
            macdh_col = [c for c in df.columns if "MACDh_" in c][0]
            macd_col = [c for c in df.columns if c.startswith("MACD_")][0]
            rsi_col = [c for c in df.columns if "RSI_" in c][0]

            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # --- THE 7 POINTS ---
            p1 = last[st_col] < last['c']                 # 1. Supertrend Green
            p2 = last[macdh_col] > prev[macdh_col]        # 2. MACD Hist Rising
            p3 = last[macd_col] > 0                       # 3. MACD Line Above 0
            p4 = last['c'] > last[bbm_col]                # 4. Price > Mid BB
            p5 = last[bbu_col] > prev[bbu_col]            # 5. Upper BB Rising
            p6 = last['c'] > last[bbu_col]                # 6. Upper BB Breakout (Classic)
            p7 = last[rsi_col] >= 70                      # 7. RSI 70+
            
            is_pink = all([p1, p2, p3, p4, p5, p6, p7])
            
            results.append({
                "Symbol": s, 
                "LTP": last['c'], 
                "Points": [p1, p2, p3, p4, p5, p6, p7],
                "Pink": is_pink,
                "Target": s.replace("/", "")
            })
        return results, None
    except Exception as e:
        return [], str(e)

# --- 3. UI ---
with st.sidebar:
    st.markdown("<h1 style='color:#00FBFF;'>🏹 PAWAN V5</h1>", unsafe_allow_html=True)
    if st.button("🚀 SCAN MARKETS"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.write("Mode: **Pure 7 Formula**")
    st.write("Refresh: **Manual**")

st.markdown(f"""
<div class="status-strip">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span><b>SYSTEM:</b> ONLINE</span>
        <span><b>FORMULA:</b> 7-POINT PRECIOUS</span>
        <span><b>SCAN TIME:</b> {datetime.datetime.now().strftime("%H:%M:%S")}</span>
    </div>
</div>
""", unsafe_allow_html=True)

data, err = get_market_data()
if err: st.error(err)

if data:
    # Dashboard Table
    html = """<table class="m-table">
    <tr><th>Symbol</th><th>LTP</th><th>Audit Score</th><th>Pink Alert</th><th>Action</th></tr>"""
    for d in data:
        score = sum(d['Points'])
        alert = '<span class="pink-alert">💎 BUY NOW</span>' if d['Pink'] else f"{score}/7"
        action = "<b>ENTER 10X</b>" if d['Pink'] else "-"
        
        html += f"""<tr>
            <td style="color:#00FBFF"><b>{d['Symbol']}</b></td>
            <td>{d['LTP']:.4f}</td>
            <td>{score} Points Match</td>
            <td>{alert}</td>
            <td>{action}</td>
        </tr>"""
    st.markdown(html + "</table>", unsafe_allow_html=True)

    # Detailed Audit Section
    st.divider()
    cols = st.columns(2)
    for i, d in enumerate(data[:4]):
        with cols[i % 2]:
            st.markdown(f"**{d['Symbol']} Audit**")
            p = d['Points']
            st.write(f"{'✅' if p[0] else '❌'} 1. ST Green | {'✅' if p[1] else '❌'} 2. MACD Hist | {'✅' if p[2] else '❌'} 3. MACD > 0")
            st.write(f"{'✅' if p[3] else '❌'} 4. Price > Mid | {'✅' if p[4] else '❌'} 5. BB Up | {'✅' if p[5] else '❌'} 6. BB Break | {'✅' if p[6] else '❌'} 7. RSI 70")
            st.divider()

st.caption("PAWAN ALGO | PURE 7-POINT PRECIOUS FORMULA | NO GHOST | NO SHIELD")
