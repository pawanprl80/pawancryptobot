import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, requests
from urllib.parse import urlencode
import pandas_ta as ta
from streamlit_autorefresh import st_autorefresh

# Secure Import for Signatures
try:
    from nacl.signing import SigningKey
    HAS_NACL = True
except ImportError:
    HAS_NACL = False

# 1. PAGE CONFIG & SYNC
st.set_page_config(page_title="TITAN V5 PRO", layout="wide")
st_autorefresh(interval=10000, key="titan_v5_live")

# API CREDENTIALS
API_KEY = "d4a0b5668e86d5256ca1b8387dbea87fc64a1c2e82e405d41c256c459c8f338d"
API_SECRET = "a5576f4da0ae455b616755a8340aef2b0eff4d05a775f82bc00352f079303511"

# UI STYLING
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

class TitanDMA:
    def __init__(self, key, secret):
        self.key = key
        self.secret = secret
        self.base = "https://dma.coinswitch.co"

    def _sign(self, method, endpoint, params=None):
        epoch = str(int(time.time()))
        path = endpoint
        if method == "GET" and params:
            path = f"{endpoint}?{urlencode(sorted(params.items()))}"
        
        msg = method + path + epoch
        if HAS_NACL:
            sk = SigningKey(bytes.fromhex(self.secret))
            sig = sk.sign(msg.encode()).signature.hex()
        else:
            sig = "NACL_MISSING"
        return sig, epoch

    def get_audit(self, symbol):
        endpoint = "/v5/market/kline"
        params = {"symbol": symbol, "interval": "5", "limit": "100", "category": "linear"}
        sig, epoch = self._sign("GET", endpoint, params)
        headers = {'X-AUTH-SIGNATURE': sig, 'X-AUTH-APIKEY': self.key, 'X-AUTH-EPOCH': epoch}
        
        try:
            r = requests.get(f"{self.base}{endpoint}", headers=headers, params=params, timeout=10).json()
            if r.get('retCode') != 0: return None
            
            df = pd.DataFrame(r['result']['list'], columns=['ts', 'o', 'h', 'l', 'c', 'v', 't'])
            df[['o','h','l','c']] = df[['o','h','l','c']].apply(pd.to_numeric)
            df = df.iloc[::-1].reset_index(drop=True)

            # Indicators
            st_ind = ta.supertrend(df['h'], df['l'], df['c'], 10, 3)
            bb = ta.bbands(df['c'], 20, 2)
            rsi = ta.rsi(df['c'], 14)
            df = pd.concat([df, st_ind, bb, rsi], axis=1)
            
            curr = df.iloc[-1]
            
            # GHOST LOGIC: Max high of last Red segment
            red_zone = df[df['SUPERT_10_3.0'] > df['c']]
            ghost_high = red_zone['h'].max() if not red_zone.empty else 0

            # 2026 GHOST RULES
            c1 = curr['c'] > curr['SUPERT_10_3.0'] # ST Green
            c2 = curr['SUPERT_10_3.0'] > ghost_high if c1 else False # Breakout
            c3 = curr['RSI_14'] >= 70
            
            # CALL SHIELD
            shield = curr['SUPERT_10_3.0'] < curr['BBL_20_2.0']
            
            pink = (c1 and c2 and c3) and not shield
            
            return {"ltp": curr['c'], "st": curr['SUPERT_10_3.0'], "ghost": ghost_high, "pink": pink, "shield": shield}
        except: return None

# UI
engine = TitanDMA(API_KEY, API_SECRET)
st.markdown(f"""
<div class="status-strip">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span>🏹 <b>TITAN V5 PRO</b> | GHOST BREAKOUT AUDIT</span>
        <span style="color:#00FBFF;"><b>{datetime.datetime.now().strftime("%H:%M:%S")}</b></span>
    </div>
</div>
""", unsafe_allow_html=True)

# Fetch Tickers
t_res = requests.get("https://dma.coinswitch.co/v5/market/tickers?category=linear").json()
if t_res.get('retCode') == 0:
    movers = pd.DataFrame(t_res['result']['list']).head(10)
    
    html = """<table class="m-table">
    <tr><th>Symbol</th><th>LTP</th><th>ST Green</th><th>Prev Red High</th><th>Pink Alert</th><th>Trigger</th></tr>"""
    
    for _, row in movers.iterrows():
        v = engine.get_audit(row['symbol'])
        if v:
            pink_lbl = '<span class="pink-alert">BREAKOUT</span>' if v['pink'] else "No"
            trigger = '<span style="color:lime">ON</span>' if v['pink'] else ("<span class='shield-gate'>SHIELD</span>" if v['shield'] else "WAIT")
            html += f"<tr><td>{row['symbol']}</td><td>{v['ltp']:.4f}</td><td>{v['st']:.4f}</td><td>{v['ghost']:.4f}</td><td>{pink_lbl}</td><td>{trigger}</td></tr>"
    st.markdown(html + "</table>", unsafe_allow_html=True)

    st.subheader("📊 VISUAL VALIDATOR")
    sel = st.selectbox("Validate", movers['symbol'].tolist())
    st.components.v1.html(f"""
        <div style="height:500px; border-radius: 8px; overflow: hidden;">
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({{"width": "100%", "height": 500, "symbol": "BYBIT:{sel.replace('.P','')}", "interval": "5", "theme": "dark", "style": "1", "container_id": "tv_chart"}});
          </script><div id="tv_chart"></div>
        </div>
    """, height=520)
