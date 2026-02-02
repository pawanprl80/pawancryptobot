import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, requests
from urllib.parse import urlencode
from cryptography.hazmat.primitives.asymmetric import ed25519
import pandas_ta as ta
from streamlit_autorefresh import st_autorefresh

# 1. SETUP & THEME
st.set_page_config(page_title="TITAN V5 PRO", layout="wide")
st_autorefresh(interval=10000, key="titan_v5_v2_pulse")

# API CREDENTIALS
API_KEY = "d4a0b5668e86d5256ca1b8387dbea87fc64a1c2e82e405d41c256c459c8f338d"
API_SECRET = "a5576f4da0ae455b616755a8340aef2b0eff4d05a775f82bc00352f079303511"

st.markdown("""
<style>
    .stApp { background-color: #020617; color: #E2E8F0; }
    .status-strip { background-color: #0F172A; padding: 15px; border-radius: 12px; border: 1px solid #00FBFF; margin-bottom: 20px; }
    .m-table { width: 100%; border-collapse: collapse; background: #0B1629; border-radius: 10px; overflow: hidden; }
    .m-table th { background-color: #1E293B; color: #00FBFF; padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1E293B; font-size: 14px; font-family: 'monospace'; }
    .ltp-val { color: #22C55E; font-weight: bold; }
    .st-val { color: #00FBFF; }
    .rsi-val { color: #EAB308; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; text-shadow: 0 0 10px #FF69B4; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)

class TitanV5Engine:
    def __init__(self):
        self.base_url = "https://dma.coinswitch.co"

    def _auth_request(self, method, endpoint, params=None):
        epoch = str(int(time.time() * 1000))
        path = endpoint
        if method == "GET" and params:
            # Sorted parameters for signature stability
            sorted_query = urlencode(sorted(params.items()))
            path = f"{endpoint}?{sorted_query}"
        
        message = method + path + epoch
        try:
            pk = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(API_SECRET))
            sig = pk.sign(message.encode()).hex()
            headers = {'X-AUTH-SIGNATURE': sig, 'X-AUTH-APIKEY': API_KEY, 'X-AUTH-EPOCH': epoch, 'Content-Type': 'application/json'}
            res = requests.get(f"{self.base_url}{endpoint}", headers=headers, params=params, timeout=5)
            return res.json()
        except:
            return {"retCode": -1}

    def get_market(self):
        res = self._auth_request("GET", "/v5/market/tickers", {"category": "linear"})
        if res.get('retCode') == 0:
            df = pd.DataFrame(res['result']['list'])
            df['change'] = (pd.to_numeric(df['lastPrice']) / pd.to_numeric(df['prevPrice24h']) - 1) * 100
            return df.sort_values(by='change', ascending=False).head(10)
        return pd.DataFrame()

    def get_audit(self, symbol):
        res = self._auth_request("GET", "/v5/market/kline", {"symbol": symbol, "interval": "5", "limit": "100", "category": "linear"})
        if not res or res.get('retCode') != 0:
            return None
        
        try:
            klines = res['result']['list']
            df = pd.DataFrame(klines, columns=['ts', 'o', 'h', 'l', 'c', 'v', 't'])
            df[['o', 'h', 'l', 'c']] = df[['o', 'h', 'l', 'c']].apply(pd.to_numeric)
            df = df.iloc[::-1].reset_index(drop=True)

            # Calculations
            st_df = ta.supertrend(df['h'], df['l'], df['c'], 10, 3)
            bb = ta.bbands(df['c'], 20, 2)
            rsi = ta.rsi(df['c'], 14)
            df = pd.concat([df, st_df, bb, rsi], axis=1)
            
            last = df.iloc[-1]
            
            # Audit Logic
            p1 = last['c'] > last['SUPERT_10_3.0']
            p2 = last['SUPERT_10_3.0'] > last['BBM_20_2.0']
            p3 = last['RSI_14'] >= 70
            
            score = sum([p1, p2, p3])
            return {
                "ltp": last['c'], "st": last['SUPERT_10_3.0'], 
                "mid": last['BBM_20_2.0'], "rsi": last['RSI_14'], "score": score
            }
        except:
            return None

# --- UI RENDER ---
engine = TitanV5Engine()
st.markdown(f"""
<div class="status-strip">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:18px;">🏹 <b>TITAN V5 PRO</b> | INDICATOR AUDIT</span>
        <span style="color:#00FBFF;"><b>{datetime.datetime.now().strftime("%H:%M:%S")}</b></span>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🚀 GAINER SCANNER", "📊 VISUAL VALIDATOR"])

movers = engine.get_market()

with tab1:
    if not movers.empty:
        html = """<table class="m-table">
        <tr><th>Symbol</th><th>24h %</th><th>LTP</th><th>Supertrend</th><th>Midband</th><th>RSI</th><th>Audit</th></tr>"""
        for _, row in movers.iterrows():
            audit = engine.get_audit(row['symbol'])
            if audit:
                score_display = '<span class="pink-alert">💎 PINK</span>' if audit['score'] == 3 else f"{audit['score']}/3"
                html += f"""<tr>
                    <td style="color:#00FBFF"><b>{row['symbol']}</b></td>
                    <td style="color:{'#22C55E' if float(row['change']) > 0 else '#EF4444'}">{float(row['change']):.2f}%</td>
                    <td class="ltp-val">{audit['ltp']:.4f}</td>
                    <td class="st-val">{audit['st']:.2f}</td>
                    <td>{audit['mid']:.2f}</td>
                    <td class="rsi-val">{audit['rsi']:.1f}</td>
                    <td>{score_display}</td>
                </tr>"""
        st.markdown(html + "</table>", unsafe_allow_html=True)
    else:
        st.warning("No Market Data. Please verify API Credentials.")

with tab2:
    if not movers.empty:
        sel = st.selectbox("Validate Asset", movers['symbol'].tolist())
        tv_symbol = sel.replace(".P", "").replace("USDT", "USDT")
        st.components.v1.html(f"""
            <div class="tradingview-widget-container">
              <div id="tradingview_df358"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
              <script type="text/javascript">
              new TradingView.widget({{
                "width": "100%", "height": 500, "symbol": "BINANCE:{tv_symbol}",
                "interval": "5", "timezone": "Etc/UTC", "theme": "dark", "style": "1",
                "locale": "en", "toolbar_bg": "#f1f3f6", "enable_publishing": false,
                "allow_symbol_change": true, "container_id": "tradingview_df358"
              }});
              </script>
            </div>
        """, height=520)

st.caption("TITAN V5 | 2026 INDICATOR ENGINE | COINSWITCH DMA")
