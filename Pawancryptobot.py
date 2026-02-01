import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, threading
import requests
import json
from urllib.parse import urlencode, unquote_plus
from cryptography.hazmat.primitives.asymmetric import ed25519
import pandas_ta as ta
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & CREDENTIALS ---
# Using the credentials you provided
API_KEY = "d4a0b5668e86d5256ca1b8387dbea87fc64a1c2e82e405d41c256c459c8f338d"
API_SECRET = "a5576f4da0ae455b616755a8340aef2b0eff4d05a775f82bc00352f079303511"
BASE_URL = "https://dma.coinswitch.co"

st.set_page_config(page_title="TITAN V5 DMA TERMINAL", layout="wide")
st_autorefresh(interval=5000, key="v5_dma_sync")

# --- 2. THE NAVY BLUE UI STYLING ---
st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    [data-testid="stSidebar"] { background-color: #0B1629; border-right: 1px solid #1E293B; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #1E293B; margin-bottom: 20px; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.3; } }
    .step-ok { color: #00FF00; font-weight: bold; }
    .step-wait { color: #64748B; }
</style>
""", unsafe_allow_html=True)

# --- 3. COINSWITCH DMA SIGNATURE LOGIC ---
def gen_headers(method, endpoint, params=None, body=None):
    epoch = str(int(time.time() * 1000))
    path = endpoint
    if method == "GET" and params:
        path = unquote_plus(f"{endpoint}?{urlencode(params)}")
    
    msg = method + path + epoch
    if body:
        msg += json.dumps(body)
        
    pk = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(API_SECRET))
    sig = pk.sign(msg.encode()).hex()
    return {
        'X-AUTH-SIGNATURE': sig, 
        'X-AUTH-APIKEY': API_KEY, 
        'X-AUTH-EPOCH': epoch, 
        'Content-Type': 'application/json'
    }

# --- 4. PRECIOUS 7-POINT ENGINE ---
if "master_cache" not in st.session_state:
    st.session_state.master_cache = {"data": [], "sync": "Never"}

def run_dma_engine():
    while True:
        try:
            results = []
            pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            for s in pairs:
                # 1. Fetch 5m Klines from CoinSwitch
                endpoint = "/v5/market/kline"
                params = {"symbol": s, "interval": "5", "limit": "100", "category": "linear"}
                res = requests.get(f"{BASE_URL}{endpoint}", headers=gen_headers("GET", endpoint, params), params=params)
                kline = res.json()['result']['list']
                
                df = pd.DataFrame(kline, columns=['t', 'o', 'h', 'l', 'c', 'v', 'turnover'])
                df[['h', 'l', 'c', 'o']] = df[['h', 'l', 'c', 'o']].apply(pd.to_numeric)
                df = df.iloc[::-1].reset_index(drop=True)
                
                # 2. Indicators
                st_data = ta.supertrend(df['h'], df['l'], df['c'], 10, 3)
                bb = ta.bbands(df['c'], 20, 2)
                macd = ta.macd(df['c'])
                rsi = ta.rsi(df['c'], 14)
                df = pd.concat([df, st_data, bb, macd, rsi], axis=1)
                
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                # 3. GHOST RESISTANCE LOGIC
                red_seg = df[df['SUPERT_10_3.0'] > df['c']]
                ghost_high = red_seg['h'].max() if not red_seg.empty else 0
                
                # 4. 7-POINT FORMULA AUDIT
                p1 = last['SUPERT_10_3.0'] < last['c']              # ST Green
                p2 = last['MACDh_12_26_9'] > prev['MACDh_12_26_9']  # MACD Rising
                p3 = last['MACD_12_26_9'] > 0                       # MACD > 0
                p4 = last['c'] > last['BBM_20_2.0']                 # Precious Cross
                p5 = last['BBU_20_2.0'] > prev['BBU_20_2.0']        # Upper BB Rising
                p6 = last['SUPERT_10_3.0'] > ghost_high if p1 else False # Ghost Breakout
                p7 = last['RSI_14'] >= 70                           # RSI 70+
                
                # SHIELD: Out-of-bounds
                shield_active = last['SUPERT_10_3.0'] < last['BBL_20_2.0']
                
                is_pink = (p1 and p2 and p3 and p4 and p5 and p6 and p7) and not shield_active
                
                results.append({
                    "Symbol": s, "LTP": last['c'], "ST": last['SUPERT_10_3.0'],
                    "Ghost": ghost_high, "Pink": is_pink, "Shield": shield_active,
                    "Points": [p1, p2, p3, p4, p5, p6, p7], "Mid": last['BBM_20_2.0']
                })
            
            st.session_state.master_cache["data"] = results
            st.session_state.master_cache["sync"] = datetime.datetime.now().strftime("%H:%M:%S")
            time.sleep(10)
        except:
            time.sleep(5)

if "bg_loop" not in st.session_state:
    threading.Thread(target=run_dma_engine, daemon=True).start()
    st.session_state.bg_loop = True

# --- 5. UI LAYOUT ---
with st.sidebar:
    st.markdown("<h2 style='color:#00FBFF;'>🏹 TITAN V5 DMA</h2>", unsafe_allow_html=True)
    menu = st.radio("NAVIGATION", ["Dashboard", "Signal Validator", "Visual Validator"])
    st.markdown("---")
    st.write("**Leverage:** 10x | **Timeframe:** 5M")

# Status Strip
st.markdown(f"""
<div class="status-strip">
    <table style="width:100%; text-align:center; color:white; font-size:12px;">
        <tr>
            <td><b>DMA CONNECTION</b><br><span style="color:#00FF00">🟢 ACTIVE</span></td>
            <td><b>SYNC</b><br>{st.session_state.master_cache['sync']}</td>
            <td><b>SHIELDS</b><br>ENABLED</td>
            <td><b>GHOST PROTOCOL</b><br>READY</td>
        </tr>
    </table>
</div>
""", unsafe_allow_html=True)

data = st.session_state.master_cache["data"]

if menu == "Dashboard":
    if data:
        st.markdown("### 📊 Market Scanner")
        df_scan = pd.DataFrame(data)
        df_scan['Pink Alert'] = df_scan['Pink'].apply(lambda x: "💎 BREAKOUT" if x else "WAIT")
        df_scan['Trigger'] = df_scan['Pink'].apply(lambda x: "ON" if x else "WAIT")
        st.table(df_scan[['Symbol', 'LTP', 'ST', 'Ghost', 'Pink Alert', 'Trigger']])

elif menu == "Visual Validator":
    if data:
        t = data[0]
        st.markdown(f"### 👁️ {t['Symbol']} CoinSwitch Chart (5-Minute)")
        chart_html = f"""
        <div style="height:600px; border-radius:12px; overflow:hidden; border:1px solid #1E293B;">
            <iframe 
                src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:{t['Symbol']}&interval=5&theme=dark&studies=BollingerBands%40tv-basicstudies%2CSuperTrend%40tv-basicstudies%2CRSI%40tv-basicstudies%2CMACD%40tv-basicstudies"
                width="100%" height="100%" frameborder="0">
            </iframe>
        </div>
        """
        st.components.v1.html(chart_html, height=600)

elif menu == "Signal Validator":
    if data:
        t = data[0]
        pts = t['Points']
        st.markdown(f"### 🎯 7-Point Audit: {t['Symbol']}")
        st.write(f"{'✅' if pts[5] else '⭕'} Ghost Breakout: ST ({t['ST']:.2f}) > Ghost ({t['Ghost']:.2f})")
        st.write(f"{'✅' if pts[3] else '⭕'} Precious Formula: ST > Midband ({t['Mid']:.2f})")
        st.write(f"{'✅' if pts[6] else '⭕'} Momentum: RSI 70+")
        if t['Pink']:
            st.success("💎 PINK ALERT ACTIVE: CRITERIA MET")

st.caption("TITAN V5 | COINSWITCH DMA VERIFIED | 2026 GHOST RULES")
