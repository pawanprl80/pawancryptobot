import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, requests
from urllib.parse import urlencode
from cryptography.hazmat.primitives.asymmetric import ed25519
import pandas_ta as ta
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. SETUP & THEME
st.set_page_config(page_title="TITAN V5 PRO", layout="wide")
st_autorefresh(interval=10000, key="titan_v5_indicator_sync")

# API CREDENTIALS
API_KEY = "d4a0b5668e86d5256ca1b8387dbea87fc64a1c2e82e405d41c256c459c8f338d"
API_SECRET = "a5576f4da0ae455b616755a8340aef2b0eff4d05a775f82bc00352f079303511"

st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #1E293B; margin-bottom: 20px; border-left: 5px solid #00FBFF; }
    .m-table { width: 100%; border-collapse: collapse; background: #0B1629; }
    .m-table th { background-color: #1E293B; color: #00FBFF; padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1E293B; font-size: 14px; font-family: 'monospace'; }
    .ltp-val { color: #00FF00; font-weight: bold; }
    .st-val { color: #00FBFF; }
    .rsi-val { color: #FFFF00; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; text-shadow: 0 0 10px #FF69B4; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)

class CoinSwitchEngine:
    def __init__(self):
        self.base_url = "https://dma.coinswitch.co"

    def _auth_request(self, method, endpoint, params=None):
        epoch = str(int(time.time() * 1000))
        path = endpoint
        if method == "GET" and params:
            sorted_query = urlencode(sorted(params.items()))
            path = f"{endpoint}?{sorted_query}"
        
        message = method + path + epoch
        pk = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(API_SECRET))
        sig = pk.sign(message.encode()).hex()
        
        headers = {'X-AUTH-SIGNATURE': sig, 'X-AUTH-APIKEY': API_KEY, 'X-AUTH-EPOCH': epoch, 'Content-Type': 'application/json'}
        try:
            res = requests.get(f"{self.base_url}{endpoint}", headers=headers, params=params, timeout=10)
            return res.json()
        except: return {"retCode": -1}

    def get_market_data(self):
        res = self._auth_request("GET", "/v5/market/tickers", {"category": "linear"})
        if res.get('retCode') == 0:
            df = pd.DataFrame(res['result']['list'])
            df['change'] = (pd.to_numeric(df['lastPrice']) / pd.to_numeric(df['prevPrice24h']) - 1) * 100
            return df.sort_values(by='change', ascending=False).head(10)
        return pd.DataFrame()

    def get_indicators(self, symbol):
        res = self._auth_request("GET", "/v5/market/kline", {"symbol": symbol, "interval": "5", "limit": "100", "category": "linear"})
        if not res or res.get('retCode') != 0: return None
        
        df = pd.DataFrame(res['result']['list'], columns=['ts', 'o', 'h', 'l', 'c', 'v', 't'])
        df[['o', 'h', 'l', 'c']] = df[['o', 'h', 'l', 'c']].apply(pd.to_numeric)
        df = df.iloc[::-1].reset_index(drop=True)

        # Indicator Calculations
        st_data = ta.supertrend(df['h'], df['l'], df['c'], 10, 3)
        bb = ta.bbands(df['c'], 20, 2)
        macd = ta.macd(df['c'])
        rsi = ta.rsi(df['c'], 14)
        df = pd.concat([df, st_data, bb, macd, rsi], axis=1)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]

        # Audit Points
        p1 = last['c'] > last['SUPERT_10_3.0']
        p2 = last['SUPERT_10_3.0'] > last['BBM_20_2.0']
        p3 = last['MACDh_12_26_9'] > prev['MACDh_12_26_9']
        p4 = last['MACD_12_26_9'] > 0
        p5 = last['BBU_20_2.0'] > prev['BBU_20_2.0']
        p6 = last['RSI_14'] >= 70
        
        score = sum([p1, p2, p3, p4, p5, p6])
        return {
            "df": df, "ltp": last['c'], "st": last['SUPERT_10_3.0'], "mid": last['BBM_20_2.0'],
            "rsi": last['RSI_14'], "macd": last['MACDh_12_26_9'], "score": score
        }

# --- APP RENDER ---
engine = CoinSwitchEngine()
st.markdown(f"""
<div class="status-strip">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:18px;">🏹 <b>TITAN V5 PRO</b> | INDICATOR AUDIT</span>
        <span style="color:#00FBFF;"><b>SYNC:</b> {datetime.datetime.now().strftime("%H:%M:%S")}</span>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🚀 GAINER SCANNER", "📊 VISUAL VALIDATOR"])

movers = engine.get_market_data()

with tab1:
    if not movers.empty:
        html = """<table class="m-table">
        <tr><th>Symbol</th><th>24h %</th><th>LTP</th><th>Supertrend</th><th>Midband</th><th>RSI</th><th>Audit</th></tr>"""
        for _, row in movers.iterrows():
            audit = engine.get_indicators(row['symbol'])
            if audit:
                alert = '<span class="pink-alert">💎 PINK</span>' if audit['score'] >= 6 else f"{audit['score']}/6"
                html += f"""<tr>
                    <td style="color:#00FBFF"><b>{row['symbol']}</b></td>
                    <td style="color:{'#00FF00' if float(row['change']) > 0 else '#FF4B4B'}">{float(row['change']):.2f}%</td>
                    <td class="ltp-val">{audit['ltp']:.4f}</td>
                    <td class="st-val">{audit['st']:.4f}</td>
                    <td>{audit['mid']:.4f}</td>
                    <td class="rsi-val">{audit['rsi']:.1f}</td>
                    <td>{alert}</td>
                </tr>"""
        st.markdown(html + "</table>", unsafe_allow_html=True)
    else:
        st.error("Credential Error: Please check API Key/Secret.")

with tab2:
    if not movers.empty:
        sel = st.selectbox("Select Asset to Visualize", movers['symbol'].tolist())
        v = engine.get_indicators(sel)
        if v:
            df = v['df']
            # TradingView Style Chart
            fig = go.Figure()
            # Candlesticks
            fig.add_trace(go.Candlestick(x=df.index, open=df['o'], high=df['h'], low=df['l'], close=df['c'], name="Price"))
            # Supertrend
            fig.add_trace(go.Scatter(x=df.index, y=df['SUPERT_10_3.0'], line=dict(color='#00FBFF', width=2), name="Supertrend"))
            # Midband
            fig.add_trace(go.Scatter(x=df.index, y=df['BBM_20_2.0'], line=dict(color='orange', dash='dot'), name="Midband"))
            
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
            
            # Indicator Panel
            c1, c2, c3 = st.columns(3)
            c1.metric("MACD Hist", f"{v['macd']:.5f}")
            c2.metric("RSI (14)", f"{v['rsi']:.2f}")
            c3.metric("Audit Score", f"{v['score']}/6")

st.caption("TITAN V5 | PURE INDICATOR ENGINE | COINSWITCH DMA")
