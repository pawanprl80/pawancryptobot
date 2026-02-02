import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, requests
from urllib.parse import urlencode, unquote_plus
from cryptography.hazmat.primitives.asymmetric import ed25519
import pandas_ta as ta
from streamlit_autorefresh import st_autorefresh

# 1. INITIALIZATION & THEME
st.set_page_config(page_title="TITAN V5 PRO", layout="wide")
st_autorefresh(interval=10000, key="titan_v5_heartbeat")

# CREDENTIALS
API_KEY = "d4a0b5668e86d5256ca1b8387dbea87fc64a1c2e82e405d41c256c459c8f338d"
API_SECRET = "a5576f4da0ae455b616755a8340aef2b0eff4d05a775f82bc00352f079303511"

st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #00FBFF; margin-bottom: 20px; }
    .m-table { width: 100%; border-collapse: collapse; background: #0B1629; border-radius: 10px; overflow: hidden; }
    .m-table th { background-color: #1E293B; color: #00FBFF; padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1E293B; font-size: 14px; font-family: 'monospace'; }
    .metric-box { padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; border: 1px solid #1E293B; }
    .bg-bull { background-color: #064E3B; color: #4ADE80; border-color: #4ADE80; }
    .bg-bear { background-color: #450A0A; color: #F87171; border-color: #F87171; }
    .bg-neutral { background-color: #0F172A; color: #94A3B8; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; text-shadow: 0 0 10px #FF69B4; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)

class CoinSwitchEngine:
    def __init__(self):
        self.base_url = "https://dma.coinswitch.co"

    def _gen_headers(self, method, endpoint, params=None):
        epoch = str(int(time.time() * 1000))
        path = endpoint
        if method == "GET" and params:
            sorted_params = urlencode(sorted(params.items()), quote_via=requests.utils.quote)
            path = f"{endpoint}?{sorted_params}"
        msg = method + path + epoch
        pk = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(API_SECRET))
        sig = pk.sign(msg.encode()).hex()
        return {'X-AUTH-SIGNATURE': sig, 'X-AUTH-APIKEY': API_KEY, 'X-AUTH-EPOCH': epoch, 'Content-Type': 'application/json'}

    def get_top_movers(self):
        endpoint = "/v5/market/tickers"
        params = {"category": "linear"}
        try:
            res = requests.get(f"{self.base_url}{endpoint}", headers=self._gen_headers("GET", endpoint, params), params=params)
            data = res.json()['result']['list']
            df = pd.DataFrame(data)
            df['change'] = (pd.to_numeric(df['lastPrice']) / pd.to_numeric(df['prevPrice24h']) - 1) * 100
            return df.sort_values(by='change', ascending=False)
        except: return pd.DataFrame()

    def get_audit(self, symbol):
        endpoint = "/v5/market/kline"
        params = {"symbol": symbol, "interval": "5", "limit": "100", "category": "linear"}
        try:
            res = requests.get(f"{self.base_url}{endpoint}", headers=self._gen_headers("GET", endpoint, params), params=params)
            kline = res.json()['result']['list']
            df = pd.DataFrame(kline, columns=['ts', 'o', 'h', 'l', 'c', 'v', 't'])
            df[['o', 'h', 'l', 'c']] = df[['o', 'h', 'l', 'c']].apply(pd.to_numeric)
            df = df.iloc[::-1].reset_index(drop=True)
            
            # Indicators
            st = ta.supertrend(df['h'], df['l'], df['c'], 10, 3)
            bb = ta.bbands(df['c'], 20, 2)
            macd = ta.macd(df['c'])
            rsi = ta.rsi(df['c'], 14)
            df = pd.concat([df, st, bb, macd, rsi], axis=1)
            
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # GHOST RESISTANCE LOGIC
            red_segments = df[df['SUPERT_10_3.0'] > df['c']]
            ghost_high = red_segments['h'].max() if not red_segments.empty else 0

            # AUDIT POINTS
            p1 = last['c'] > last['SUPERT_10_3.0']                # 1. ST Green
            p2 = (last['SUPERT_10_3.0'] > last['BBM_20_2.0']) and (prev['SUPERT_10_3.0'] <= prev['BBM_20_2.0']) # 2. CROSS MID
            p3 = last['MACDh_12_26_9'] > prev['MACDh_12_26_9']    # 3. MACD Rising
            p4 = last['MACD_12_26_9'] > 0                         # 4. MACD Line > 0
            p5 = last['BBU_20_2.0'] > prev['BBU_20_2.0']          # 5. Upper BB Rising
            p6 = last['SUPERT_10_3.0'] > ghost_high if p1 else False # 6. GHOST BREAKOUT
            p7 = last['RSI_14'] >= 70                             # 7. RSI 70+

            pts = [p1, p2, p3, p4, p5, p6, p7]
            return {
                "symbol": symbol, "ltp": last['c'], "st": last['SUPERT_10_3.0'], "mid": last['BBM_20_2.0'],
                "rsi": last['RSI_14'], "ghost": ghost_high, "score": sum(pts), "pts": pts, "chg": last['c']-prev['c']
            }
        except: return None

engine = CoinSwitchEngine()

# --- UI LAYOUT ---
st.markdown(f"""
<div class="status-strip">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:18px;">🏹 <b>TITAN V5 PRO</b></span>
        <span><b>MODE:</b> PURE 7 PRECIOUS</span>
        <span style="color:#00FBFF;"><b>SYNC:</b> {datetime.datetime.now().strftime("%H:%M:%S")}</span>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🚀 TOP 100 GAINER AUDIT", "🔍 SIGNAL VALIDATOR"])

with tab1:
    movers = engine.get_top_movers()
    if not movers.empty:
        html = """<table class="m-table">
        <tr><th>Symbol</th><th>24h Chg</th><th>LTP</th><th>Audit Score</th><th>Condition</th></tr>"""
        for _, row in movers.head(20).iterrows():
            res = engine.get_audit(row['symbol'])
            if res:
                p_alert = '<span class="pink-alert">💎 PINK ALERT</span>' if res['score'] == 7 else f"Audit: {res['score']}/7"
                color = "lime" if float(row['change']) > 0 else "red"
                html += f"""<tr>
                    <td style="color:#00FBFF"><b>{row['symbol']}</b></td>
                    <td style="color:{color}">{float(row['change']):.2f}%</td>
                    <td>{res['ltp']:.4f}</td>
                    <td>{"✅"*res['score']}{"⚪"*(7-res['score'])}</td>
                    <td>{p_alert}</td>
                </tr>"""
        st.markdown(html + "</table>", unsafe_allow_html=True)
    else:
        st.error("Credential Error or API Timeout. Checking Connection...")

with tab2:
    if not movers.empty:
        sel = st.selectbox("Validate Specific Asset", movers['symbol'].tolist())
        v = engine.get_audit(sel)
        if v:
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="metric-box {"bg-bull" if v["pts"][0] else "bg-bear"}"><small>SUPERTREND</small><br>{v["st"]:.4f}</div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box bg-neutral"><small>MIDBAND</small><br>{v["mid"]:.4f}</div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box {"bg-bull" if v["pts"][6] else "bg-neutral"}"><small>RSI (14)</small><br>{v["rsi"]:.2f}</div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-box bg-neutral"><small>GHOST RES</small><br>{v["ghost"]:.4f}</div>', unsafe_allow_html=True)
            
            st.divider()
            s1, s2, s3 = st.columns(3)
            s1.metric("ST Status", "GREEN" if v['pts'][0] else "RED", delta=v['chg'])
            s2.metric("Mid Crossover", "FIRE 🔥" if v['pts'][1] else "WAIT", delta_color="normal")
            s3.metric("Ghost Breakout", "YES" if v['pts'][5] else "NO")
            
            if v['score'] == 7:
                st.markdown('<div class="metric-box" style="border:2px solid #ff69b4; color:#ff69b4; font-size:24px;">💎 PINK ALERT ACTIVE</div>', unsafe_allow_html=True)
            
            tv_s = sel.replace(".P", "")
            st.components.v1.html(f'<iframe src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:{tv_s}&interval=5&theme=dark" width="100%" height="450" frameborder="0"></iframe>', height=460)

st.caption("TITAN V5 | 2026 PURE FORMULA | COINSWITCH DMA")
