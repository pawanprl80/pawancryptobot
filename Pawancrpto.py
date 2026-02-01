import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, requests
from urllib.parse import urlencode, unquote_plus
from cryptography.hazmat.primitives.asymmetric import ed25519
import pandas_ta as ta
from streamlit_autorefresh import st_autorefresh

# 1. INITIALIZATION & THEME
st.set_page_config(page_title="TITAN V5 VALIDATOR", layout="wide")
st_autorefresh(interval=5000, key="v5_validator_pulse")

# Credentials
API_KEY = "d4a0b5668e86d5256ca1b8387dbea87fc64a1c2e82e405d41c256c459c8f338d"
API_SECRET = "a5576f4da0ae455b616755a8340aef2b0eff4d05a775f82bc00352f079303511"

st.markdown("""
<style>
    .stApp { background-color: #020617; color: #f8fafc; }
    .val-card { background: #1e293b; border-radius: 12px; padding: 15px; border-left: 5px solid #00fbff; margin-bottom: 10px; }
    .metric-box { padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; font-family: 'Courier New'; }
    .bg-green { background-color: #064e3b; color: #4ade80; border: 1px solid #4ade80; }
    .bg-red { background-color: #450a0a; color: #f87171; border: 1px solid #f87171; }
    .bg-neutral { background-color: #0f172a; color: #94a3b8; border: 1px solid #334155; }
    .indicator-name { font-size: 12px; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px; }
    .indicator-value { font-size: 20px; font-weight: 800; }
    .pink-glow { color: #ff69b4; text-shadow: 0 0 15px #ff69b4; font-size: 24px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

class CoinSwitchEngine:
    def __init__(self):
        self.base_url = "https://dma.coinswitch.co"

    def _gen_headers(self, method, endpoint, params=None):
        epoch = str(int(time.time()))
        path = endpoint
        if method == "GET" and params:
            path = unquote_plus(f"{endpoint}?{urlencode(params)}")
        msg = method + path + epoch
        pk = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(API_SECRET))
        sig = pk.sign(msg.encode()).hex()
        return {'X-AUTH-SIGNATURE': sig, 'X-AUTH-APIKEY': API_KEY, 'X-AUTH-EPOCH': epoch, 'Content-Type': 'application/json'}

    def get_data(self, symbol):
        endpoint = "/v5/market/kline"
        params = {"symbol": symbol, "interval": "5", "limit": 100, "category": "linear"}
        try:
            res = requests.get(f"{self.base_url}{endpoint}", headers=self._gen_headers("GET", endpoint, params), params=params)
            df = pd.DataFrame(res.json()['result']['list'], columns=['ts', 'o', 'h', 'l', 'c', 'v', 't'])
            df[['h', 'l', 'c', 'o']] = df[['h', 'l', 'c', 'o']].apply(pd.to_numeric)
            df = df.iloc[::-1].reset_index(drop=True)
            
            st_df = ta.supertrend(df['h'], df['l'], df['c'], 10, 3)
            bb = ta.bbands(df['c'], 20, 2)
            macd = ta.macd(df['c'])
            rsi = ta.rsi(df['c'], 14)
            df = pd.concat([df, st_df, bb, macd, rsi], axis=1)
            
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Logic calculation
            st_val = last['SUPERT_10_3.0']
            mid_val = last['BBM_20_2.0']
            prev_st = prev['SUPERT_10_3.0']
            prev_mid = prev['BBM_20_2.0']
            
            data = {
                "symbol": symbol,
                "price": last['c'],
                "st_val": st_val,
                "mid_val": mid_val,
                "rsi": last['RSI_14'],
                "macd_h": last['MACDh_12_26_9'],
                "upper_bb": last['BBU_20_2.0'],
                "is_st_green": last['c'] > st_val,
                "is_st_cross_mid": (st_val > mid_val) and (prev_st <= prev_mid),
                "is_rsi_70": last['RSI_14'] >= 70,
                "is_macd_rising": last['MACDh_12_26_9'] > prev['MACDh_12_26_9']
            }
            return data
        except: return None

engine = CoinSwitchEngine()

st.title("🏹 TITAN V5 | SIGNAL VALIDATOR")

# 1. Selector
col_top1, col_top2 = st.columns([2, 1])
with col_top1:
    symbol = st.selectbox("CHOOSE ASSET TO VALIDATE", ["BTCUSDT.P", "ETHUSDT.P", "SOLUSDT.P", "DOGEUSDT.P", "PEPEUSDT.P"])

# 2. Fetch Data
d = engine.get_data(symbol)

if d:
    # 3. Indicator Value Dashboard
    st.markdown("### 📊 REAL-TIME INDICATOR VALUES")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        color = "bg-green" if d['is_st_green'] else "bg-red"
        st.markdown(f"""<div class="metric-box {color}"><div class="indicator-name">Supertrend Line</div><div class="indicator-value">{d['st_val']:.4f}</div></div>""", unsafe_allow_html=True)
    
    with c2:
        st.markdown(f"""<div class="metric-box bg-neutral"><div class="indicator-name">Midband (20)</div><div class="indicator-value">{d['mid_val']:.4f}</div></div>""", unsafe_allow_html=True)
        
    with c3:
        color = "bg-green" if d['is_rsi_70'] else "bg-neutral"
        st.markdown(f"""<div class="metric-box {color}"><div class="indicator-name">RSI (14)</div><div class="indicator-value">{d['rsi']:.2f}</div></div>""", unsafe_allow_html=True)

    with c4:
        color = "bg-green" if d['is_macd_rising'] else "bg-red"
        st.markdown(f"""<div class="metric-box {color}"><div class="indicator-name">MACD Hist</div><div class="indicator-value">{d['macd_h']:.6f}</div></div>""", unsafe_allow_html=True)

    # 4. Critical Signal Validator
    st.markdown("### ⚡ SIGNAL STATUS")
    s1, s2, s3 = st.columns(3)
    
    with s1:
        status = "✅ ST IS GREEN" if d['is_st_green'] else "❌ ST IS RED"
        cls = "bg-green" if d['is_st_green'] else "bg-red"
        st.markdown(f'<div class="metric-box {cls}">{status}</div>', unsafe_allow_html=True)
        
    with s2:
        status = "🔥 MID CROSSOVER" if d['is_st_cross_mid'] else "⏳ NO CROSSOVER"
        cls = "bg-green" if d['is_st_cross_mid'] else "bg-neutral"
        st.markdown(f'<div class="metric-box {cls}">{status}</div>', unsafe_allow_html=True)

    with s3:
        if d['is_st_green'] and d['is_st_cross_mid'] and d['is_rsi_70'] and d['is_macd_rising']:
            st.markdown('<div class="pink-glow">💎 PINK ALERT ACTIVE</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="metric-box bg-neutral">WAITING FOR CONFLUENCE</div>', unsafe_allow_html=True)

    # 5. TradingView Context
    st.divider()
    tv_s = symbol.replace(".P", "")
    st.components.v1.html(f"""
        <iframe src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:{tv_s}&interval=5&theme=dark" width="100%" height="400" frameborder="0"></iframe>
    """, height=410)

else:
    st.error("Error fetching data from CoinSwitch API. Please check credentials.")

st.caption(f"Last API Pulse: {datetime.datetime.now().strftime('%H:%M:%S')}")
