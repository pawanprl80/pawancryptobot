import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, requests
from urllib.parse import urlencode, urlparse
from nacl.signing import SigningKey
import pandas_ta as ta
from streamlit_autorefresh import st_autorefresh

# 1. CLOUD INITIALIZATION
st.set_page_config(page_title="TITAN V5 PRO", layout="wide")
st_autorefresh(interval=10000, key="titan_v5_ghost_pulse")

# API CREDENTIALS
API_KEY = "d4a0b5668e86d5256ca1b8387dbea87fc64a1c2e82e405d41c256c459c8f338d"
API_SECRET = "a5576f4da0ae455b616755a8340aef2b0eff4d05a775f82bc00352f079303511"

st.markdown("""
<style>
    .stApp { background-color: #020617; color: #E2E8F0; }
    .status-strip { background: linear-gradient(90deg, #1e293b, #0f172a); padding: 15px; border-radius: 12px; border: 1px solid #00fbff; margin-bottom: 20px; }
    .m-table { width: 100%; border-collapse: collapse; background: #0b1629; border-radius: 10px; overflow: hidden; margin-bottom: 20px;}
    .m-table th { background-color: #1e293b; color: #00fbff; padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1e293b; font-size: 14px; font-family: 'monospace'; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; text-shadow: 0 0 10px #FF69B4; animation: blinker 1.5s linear infinite; }
    .shield-gate { color: #f87171; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)

class TitanDMAEngine:
    def __init__(self, key, secret):
        self.api_key = key
        self.api_secret = secret
        self.base_url = "https://dma.coinswitch.co"

    def _generate_signature(self, method, endpoint, params=None):
        epoch_time = str(int(time.time()))
        params = params or {}
        if method == "GET" and params:
            query_string = urlencode(sorted(params.items()))
            full_path = f"{endpoint}?{query_string}"
        else:
            full_path = endpoint

        message = method + full_path + epoch_time
        signing_key = SigningKey(bytes.fromhex(self.api_secret))
        signature = signing_key.sign(message.encode()).signature.hex()
        return signature, epoch_time

    def get_market(self):
        endpoint = "/v5/market/tickers"
        params = {"category": "linear"}
        sig, epoch = self._generate_signature("GET", endpoint, params)
        headers = {'X-AUTH-SIGNATURE': sig, 'X-AUTH-APIKEY': self.api_key, 'X-AUTH-EPOCH': epoch}
        try:
            res = requests.get(f"{self.base_url}{endpoint}", headers=headers, params=params, timeout=10)
            data = res.json()
            if data.get('retCode') == 0:
                df = pd.DataFrame(data['result']['list'])
                df['change'] = (pd.to_numeric(df['lastPrice']) / pd.to_numeric(df['prevPrice24h']) - 1) * 100
                return df.sort_values(by='change', ascending=False).head(10)
        except: pass
        return pd.DataFrame()

    def get_audit(self, symbol):
        endpoint = "/v5/market/kline"
        params = {"symbol": symbol, "interval": "5", "limit": "100", "category": "linear"}
        sig, epoch = self._generate_signature("GET", endpoint, params)
        headers = {'X-AUTH-SIGNATURE': sig, 'X-AUTH-APIKEY': self.api_key, 'X-AUTH-EPOCH': epoch}
        try:
            res = requests.get(f"{self.base_url}{endpoint}", headers=headers, params=params, timeout=10)
            data = res.json()
            if data.get('retCode') != 0: return None
            
            df = pd.DataFrame(data['result']['list'], columns=['ts', 'o', 'h', 'l', 'c', 'v', 't'])
            df[['o', 'h', 'l', 'c']] = df[['o', 'h', 'l', 'c']].apply(pd.to_numeric)
            df = df.iloc[::-1].reset_index(drop=True)

            # Indicator Logic
            st = ta.supertrend(df['h'], df['l'], df['c'], 10, 3)
            bb = ta.bbands(df['c'], 20, 2)
            macd = ta.macd(df['c'])
            rsi = ta.rsi(df['c'], 14)
            df = pd.concat([df, st, bb, macd, rsi], axis=1)
            
            curr, prev = df.iloc[-1], df.iloc[-2]

            # GHOST LOGIC: Find max high of last RED segment
            red_mask = df['SUPERT_10_3.0'] > df['c']
            ghost_high = df[red_mask]['h'].max() if not df[red_mask].empty else 0

            # SHIELD GATE
            call_shield = curr['SUPERT_10_3.0'] < curr['BBL_20_2.0']
            
            # PRECIOUS FORMULA
            c1 = curr['c'] > curr['SUPERT_10_3.0']          # ST Green
            c2 = curr['SUPERT_10_3.0'] > ghost_high if c1 else False # GHOST BREAKOUT
            c3 = curr['MACDh_12_26_9'] > prev['MACDh_12_26_9'] # MACD Rising
            c4 = curr['RSI_14'] >= 70                       # RSI 70+
            c5 = curr['BBU_20_2.0'] > prev['BBU_20_2.0']    # BB Upper Rising
            
            score = sum([c1, c2, c3, c4, c5])
            pink = (score >= 5) and not call_shield

            return {
                "ltp": curr['c'], "st": curr['SUPERT_10_3.0'], "ghost": ghost_high,
                "score": score, "pink": pink, "shield": call_shield, "rsi": curr['RSI_14']
            }
        except: return None

# UI
engine = TitanDMAEngine(API_KEY, API_SECRET)
st.markdown(f"""
<div class="status-strip">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span>🏹 <b>TITAN V5 PRO</b> | GHOST BREAKOUT AUDIT</span>
        <span style="color:#00FBFF;">{datetime.datetime.now().strftime("%H:%M:%S")}</span>
    </div>
</div>
""", unsafe_allow_html=True)

movers = engine.get_market()
if not movers.empty:
    html = """<table class="m-table">
    <tr><th>Symbol</th><th>LTP</th><th>ST Green</th><th>Prev Red High</th><th>Pink Alert</th><th>Trigger</th></tr>"""
    for _, row in movers.iterrows():
        v = engine.get_audit(row['symbol'])
        if v:
            pink_label = '<span class="pink-alert">BREAKOUT</span>' if v['pink'] else "No"
            trigger = '<span style="color:lime">ON</span>' if v['pink'] else ("<span class='shield-gate'>SHIELD</span>" if v['shield'] else "WAIT")
            html += f"""<tr>
                <td style="color:#00FBFF"><b>{row['symbol']}</b></td>
                <td>{v['ltp']:.4f}</td>
                <td style="color:#4ade80">{v['st']:.4f}</td>
                <td style="color:#94a3b8">{v['ghost']:.4f}</td>
                <td>{pink_label}</td>
                <td>{trigger}</td>
            </tr>"""
    st.markdown(html + "</table>", unsafe_allow_html=True)

    st.subheader("📊 VISUAL VALIDATOR")
    sel = st.selectbox("Validate Asset", movers['symbol'].tolist())
    tv_symbol = sel.replace(".P", "")
    st.components.v1.html(f"""
        <div style="height:500px; border: 1px solid #1E293B; border-radius: 8px; overflow: hidden;">
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({{"width": "100%", "height": 500, "symbol": "BYBIT:{tv_symbol}", "interval": "5", "theme": "dark", "style": "1", "locale": "en", "enable_publishing": false, "container_id": "tv_chart"}});
          </script>
          <div id="tv_chart"></div>
        </div>
    """, height=520)
