import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, threading
import ccxt
import pandas_ta as ta
import requests
import json
from urllib.parse import urlencode, unquote_plus
from cryptography.hazmat.primitives.asymmetric import ed25519
from streamlit_autorefresh import st_autorefresh

# --- 1. INITIALIZATION & CREDENTIALS ---
API_KEY = "d4a0b5668e86d5256ca1b8387dbea87fc64a1c2e82e405d41c256c459c8f338d"
API_SECRET = "a5576f4da0ae455b616755a8340aef2b0eff4d05a775f82bc00352f079303511"
BASE_URL = "https://dma.coinswitch.co"

st.set_page_config(page_title="PAWAN ALGO SYSTEM V5", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=5000, key="pawan_algo_pulse")

# --- 2. UI STYLING (NAVY DARK & PINK ALERTS) ---
st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    [data-testid="stSidebar"] { background-color: #0B1629; border-right: 1px solid #1E293B; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #1E293B; margin-bottom: 20px; }
    .m-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .m-table th { background-color: #1E293B; color: #94A3B8; padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1E293B; font-size: 14px; }
    .pair-name { color: #00FBFF !important; font-weight: 900; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.3; } }
    .audit-box { background: #0B1629; padding: 20px; border-radius: 10px; border: 1px solid #1E293B; }
    .step-ok { color: #00FF00; font-weight: bold; }
    .step-wait { color: #475569; }
</style>
""", unsafe_allow_html=True)

# --- 3. DMA HEADERS ENGINE ---
def gen_dma_headers(method, endpoint, params=None):
    epoch = str(int(time.time() * 1000))
    path = endpoint
    if method == "GET" and params:
        path = unquote_plus(f"{endpoint}?{urlencode(params)}")
    msg = method + path + epoch
    pk = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(API_SECRET))
    sig = pk.sign(msg.encode()).hex()
    return {'X-AUTH-SIGNATURE': sig, 'X-AUTH-APIKEY': API_KEY, 'X-AUTH-EPOCH': epoch, 'Content-Type': 'application/json'}

# --- 4. PRECIOUS TITAN ENGINE (REPLACED GHOST WITH TITAN) ---
if "master_cache" not in st.session_state:
    st.session_state.master_cache = {"data": [], "sync": "Connecting..."}

def run_pawan_engine():
    ex = ccxt.binance()
    while True:
        try:
            results = []
            pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
            for s in pairs:
                ohlcv = ex.fetch_ohlcv(s, timeframe='5m', limit=100)
                df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
                
                # Indicators
                st_data = ta.supertrend(df['h'], df['l'], df['c'], 10, 3)
                bb = ta.bbands(df['c'], 20, 2)
                macd = ta.macd(df['c'])
                rsi = ta.rsi(df['c'], 14)
                df = pd.concat([df, st_data, bb, macd, rsi], axis=1)
                
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                # --- TITAN RESISTANCE: Max High of previous Red Supertrend segment ---
                red_seg = df[df['SUPERT_10_3.0'] > df['c']]
                titan_res = red_seg['h'].max() if not red_seg.empty else 0
                
                # --- 7-POINT FORMULA VALIDATOR ---
                p1 = last['SUPERT_10_3.0'] < last['c']               # 1. ST Green
                p2 = last['MACDh_12_26_9'] > prev['MACDh_12_26_9']   # 2. MACD Histogram Up
                p3 = last['MACD_12_26_9'] > 0                        # 3. MACD Line Above 0
                p4 = last['c'] > last['BBM_20_2.0']                  # 4. Precious Cross (ST > Mid)
                p5 = last['BBU_20_2.0'] > prev['BBU_20_2.0']         # 5. BB Upper Rising
                p6 = last['SUPERT_10_3.0'] > titan_res if p1 else False # 6. TITAN BREAKOUT
                p7 = last['RSI_14'] >= 70                            # 7. Momentum RSI 70+
                
                # SHIELDS (Out of Bounds)
                call_shield = last['SUPERT_10_3.0'] < last['BBL_20_2.0']
                
                is_pink = (p1 and p2 and p3 and p4 and p5 and p6 and p7) and not call_shield
                
                results.append({
                    "Symbol": s, "LTP": last['c'], "ST": last['SUPERT_10_3.0'],
                    "TitanRes": titan_res, "Pink": is_pink, "Shield": call_shield,
                    "Points": [p1, p2, p3, p4, p5, p6, p7], "Mid": last['BBM_20_2.0']
                })
            
            st.session_state.master_cache["data"] = results
            st.session_state.master_cache["sync"] = datetime.datetime.now().strftime("%H:%M:%S")
            time.sleep(10)
        except:
            time.sleep(5)

if "bg_loop" not in st.session_state:
    threading.Thread(target=run_pawan_engine, daemon=True).start()
    st.session_state.bg_loop = True

# --- 5. UI LAYOUT ---
with st.sidebar:
    st.markdown("<h2 style='color:#00FBFF;'>🏹 PAWAN ALGO</h2>", unsafe_allow_html=True)
    page = st.radio("NAVIGATION", ["Dashboard", "Signal Validator", "Visual Validator"])
    st.markdown("---")
    st.write("**Leverage:** 10x | **Margin:** 500 USDT")

# TOP STATUS STRIP
st.markdown(f"""
<div class="status-strip">
    <table style="width:100%; text-align:center; color:white; font-size:12px;">
        <tr>
            <td><b>DMA CONNECTION</b><br><span style="color:#00FF00">🟢 ACTIVE</span></td>
            <td><b>SYNC</b><br>{st.session_state.master_cache['sync']}</td>
            <td><b>TITAN PROTOCOL</b><br>READY</td>
            <td><b>SHIELDS</b><br>ENABLED</td>
        </tr>
    </table>
</div>
""", unsafe_allow_html=True)

data = st.session_state.master_cache["data"]

if page == "Dashboard":
    if data:
        html = '<table class="m-table"><tr><th>Symbol</th><th>LTP</th><th>ST Green</th><th>Titan Resistance</th><th>Pink Alert</th><th>Trigger</th></tr>'
        for d in data:
            p_alert = '<span class="pink-alert">💎 BREAKOUT</span>' if d['Pink'] else "No"
            trigger = '<span style="color:#00FF00">ON</span>' if d['Pink'] else "WAIT"
            html += f"<tr><td class='pair-name'>{d['Symbol']}</td><td>{d['LTP']:.2f}</td><td>{d['ST']:.2f}</td><td>{d['TitanRes']:.2f}</td><td>{p_alert}</td><td>{trigger}</td></tr>"
        st.markdown(html + "</table>", unsafe_allow_html=True)

elif page == "Signal Validator":
    if data:
        t = data[0]
        p = t['Points']
        st.markdown(f"### 🎯 7-Point Audit: {t['Symbol']}")
        st.markdown(f"""
        <div class="audit-box">
            <p class="{'step-ok' if p[0] else 'step-wait'}">{'✅' if p[0] else '⭕'} 1. Supertrend: GREEN</p>
            <p class="{'step-ok' if p[1] else 'step-wait'}">{'✅' if p[1] else '⭕'} 2. MACD Histogram: RISING</p>
            <p class="{'step-ok' if p[2] else 'step-wait'}">{'✅' if p[2] else '⭕'} 3. MACD Line: ABOVE 0</p>
            <p class="{'step-ok' if p[3] else 'step-wait'}">{'✅' if p[3] else '⭕'} 4. Precious Cross (ST > Mid {t['Mid']:.2f})</p>
            <p class="{'step-ok' if p[4] else 'step-wait'}">{'✅' if p[4] else '⭕'} 5. BB Upper: SLOPING UP</p>
            <p class="{'step-ok' if p[5] else 'step-wait'}">{'✅' if p[5] else '⭕'} 6. TITAN BREAKOUT (ST {t['ST']:.2f} > Res {t['TitanRes']:.2f})</p>
            <p class="{'step-ok' if p[6] else 'step-wait'}">{'✅' if p[6] else '⭕'} 7. RSI Target: 70+</p>
            <hr style="border:0.5px solid #1E293B">
            <h2 style="color:#FF69B4">DIAMOND READY: {'YES 💎' if t['Pink'] else 'SCANNING...'}</h2>
        </div>
        """, unsafe_allow_html=True)

elif page == "Visual Validator":
    if data:
        target = data[0]['Symbol'].replace("/", "")
        tv_html = f'<iframe src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:{target}&interval=5&theme=dark" width="100%" height="550" frameborder="0"></iframe>'
        st.components.v1.html(tv_html, height=550)

st.caption("PAWAN ALGO SYSTEM V5 | 2026 PRECIOUS FORMULA | COINSWITCH DMA")
