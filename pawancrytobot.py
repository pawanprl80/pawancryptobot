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

# --- 1. CREDENTIALS & CONSTANTS ---
API_KEY = "d4a0b5668e86d5256ca1b8387dbea87fc64a1c2e82e405d41c256c459c8f338d"
API_SECRET = "a5576f4da0ae455b616755a8340aef2b0eff4d05a775f82bc00352f079303511"
BASE_URL = "https://dma.coinswitch.co"

st.set_page_config(page_title="TITAN V5 PRO DMA", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=5000, key="v5_heartbeat")

# --- 2. AUTHENTICATION (SIGNATURE GENERATOR) ---
def gen_dma_headers(method, endpoint, params=None, body=None):
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

# --- 3. PRECIOUS GHOST ENGINE ---
if "master_cache" not in st.session_state:
    st.session_state.master_cache = {"data": [], "sync": "Connecting...", "error": None}

def run_precious_sync():
    while True:
        try:
            results = []
            pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            for symbol in pairs:
                # Fetch 5M Klines
                endpoint = "/v5/market/kline"
                params = {"symbol": symbol, "interval": "5", "limit": "100", "category": "linear"}
                res = requests.get(f"{BASE_URL}{endpoint}", headers=gen_dma_headers("GET", endpoint, params), params=params, timeout=10)
                
                if res.status_code == 200:
                    kline_data = res.json()['result']['list']
                    df = pd.DataFrame(kline_data, columns=['t', 'o', 'h', 'l', 'c', 'v', 'turnover'])
                    df[['h', 'l', 'c', 'o']] = df[['h', 'l', 'c', 'o']].apply(pd.to_numeric)
                    df = df.iloc[::-1].reset_index(drop=True)
                    
                    # 2026 INDICATORS
                    st_df = ta.supertrend(df['h'], df['l'], df['c'], 10, 3)
                    bb = ta.bbands(df['c'], 20, 2)
                    macd = ta.macd(df['c'])
                    rsi = ta.rsi(df['c'], 14)
                    df = pd.concat([df, st_df, bb, macd, rsi], axis=1)
                    
                    last = df.iloc[-1]
                    prev = df.iloc[-2]
                    
                    # GHOST RESISTANCE: Max high of previous RED segment
                    red_line = df[df['SUPERT_10_3.0'] > df['c']]
                    ghost_high = red_line['h'].max() if not red_line.empty else 0
                    
                    # 7-POINT FORMULA
                    p1 = last['SUPERT_10_3.0'] < last['c']               # ST Green
                    p2 = last['MACDh_12_26_9'] > prev['MACDh_12_26_9']   # MACD Hist Up
                    p3 = last['MACD_12_26_9'] > 0                        # MACD > 0
                    p4 = last['c'] > last['BBM_20_2.0']                  # ST > Mid (Precious)
                    p5 = last['BBU_20_2.0'] > prev['BBU_20_2.0']         # BB Upper Up
                    p6 = last['SUPERT_10_3.0'] > ghost_high if p1 else False # GHOST BREAKOUT
                    p7 = last['RSI_14'] >= 70                            # RSI 70+
                    
                    # SHIELDS
                    call_shield = last['SUPERT_10_3.0'] < last['BBL_20_2.0']
                    
                    is_pink = (p1 and p2 and p3 and p4 and p5 and p6 and p7) and not call_shield
                    
                    results.append({
                        "Symbol": symbol, "LTP": last['c'], "ST": last['SUPERT_10_3.0'],
                        "Ghost": ghost_high, "Pink": is_pink, "Shield": call_shield,
                        "Points": [p1, p2, p3, p4, p5, p6, p7], "Mid": last['BBM_20_2.0']
                    })
            
            st.session_state.master_cache["data"] = results
            st.session_state.master_cache["sync"] = datetime.datetime.now().strftime("%H:%M:%S")
            st.session_state.master_cache["error"] = None
        except Exception as e:
            st.session_state.master_cache["error"] = str(e)
        time.sleep(10)

if "bg_thread" not in st.session_state:
    thread = threading.Thread(target=run_precious_sync, daemon=True)
    thread.start()
    st.session_state.bg_thread = True

# --- 4. UI STYLING ---
st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    [data-testid="stSidebar"] { background-color: #0B1629; border-right: 1px solid #1E293B; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #1E293B; margin-bottom: 20px; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR & NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color:#00FBFF;'>🏹 TITAN V5 DMA</h2>", unsafe_allow_html=True)
    page = st.radio("NAVIGATION", ["Dashboard", "Signal Validator", "Visual Validator"])
    st.markdown("---")
    st.write(f"**Leverage:** 10x")
    st.write(f"**Margin:** 500 USDT")
    if st.session_state.master_cache["error"]:
        st.error(f"API Error: {st.session_state.master_cache['error']}")

# Header Strip
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

if page == "Dashboard":
    if data:
        st.markdown("### 📊 Market Scanner")
        df_scan = pd.DataFrame(data)
        df_scan['Pink Alert'] = df_scan['Pink'].apply(lambda x: "💎 BREAKOUT" if x else "WAIT")
        df_scan['Shield'] = df_scan['Shield'].apply(lambda x: "⚠️ ACTIVE" if x else "CLEAN")
        st.table(df_scan[['Symbol', 'LTP', 'ST', 'Ghost', 'Pink Alert', 'Shield']])
    else:
        st.info("Waiting for first data sync from CoinSwitch DMA...")

elif page == "Visual Validator":
    if data:
        target = data[0]
        st.markdown(f"### 👁️ {target['Symbol']} 5-Minute Chart")
        # TradingView Widget forced to 5M with all indicators
        tv_html = f"""
        <div style="height:600px; border-radius:12px; overflow:hidden; border:1px solid #1E293B;">
            <iframe src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:{target['Symbol']}&interval=5&theme=dark&studies=BollingerBands%40tv-basicstudies%2CSuperTrend%40tv-basicstudies%2CRSI%40tv-basicstudies%2CMACD%40tv-basicstudies" width="100%" height="100%" frameborder="0"></iframe>
        </div>
        """
        st.components.v1.html(tv_html, height=600)
        st.write(f"**Verification:** ST Green ({target['ST']:.2f}) > Ghost Res ({target['Ghost']:.2f})")

elif page == "Signal Validator":
    if data:
        t = data[0]
        pts = t['Points']
        st.markdown(f"### 🎯 Signal Audit: {t['Symbol']}")
        st.markdown(f"""
        - {'✅' if pts[0] else '❌'} Supertrend is Green
        - {'✅' if pts[3] else '❌'} ST > Midband (Precious Formula)
        - {'✅' if pts[5] else '❌'} Ghost Breakout (ST > {t['Ghost']:.2f})
        - {'✅' if pts[6] else '❌'} RSI >= 70
        """)
        if t['Pink']: st.success("💎 PINK ALERT TRIGGERED")

st.caption("TITAN V5 | COINSWITCH DMA | 2026 GHOST RULES")
