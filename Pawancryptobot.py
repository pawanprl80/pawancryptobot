import streamlit as st
import pandas as pd
import numpy as np
import datetime, time, requests, json, urllib.parse
from urllib.parse import urlparse, urlencode, unquote_plus
import pandas_ta as ta
from streamlit_autorefresh import st_autorefresh

# --- 1. PHOTOCOPY: DMABybit WRAPPER CLASS (SIGNATURE LOGIC) ---
try:
    from nacl.signing import SigningKey
    HAS_NACL = True
except ImportError:
    HAS_NACL = False

class DMABybit:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.coinswitch_url = "https://dma.coinswitch.co"

    def _generate_coinswitch_signature(self, method, endpoint, params=None):
        if not HAS_NACL:
            return "NACL_MISSING", str(int(time.time()))
        
        params = params or {}
        epoch_time = str(int(time.time()))
        unquote_endpoint = endpoint
        if method == "GET" and params:
            endpoint += ('&', '?')[urlparse(endpoint).query == ''] + urlencode(params)
            unquote_endpoint = urllib.parse.unquote(endpoint)

        message = method + unquote_endpoint + epoch_time
        signing_key = SigningKey(bytes.fromhex(self.api_secret))
        signature = signing_key.sign(message.encode()).signature.hex()
        return signature, epoch_time

# --- 2. PHOTOCOPY: PAWAN MASTER ALGO SCANNER ---
class MasterAlgoScanner:
    def __init__(self, trader):
        self.trader = trader

    def get_audit(self, symbol):
        endpoint = "/v5/market/kline"
        params = {"symbol": symbol, "interval": "5", "limit": 100, "category": "linear"}
        sig, epoch = self.trader._generate_coinswitch_signature("GET", endpoint, params)
        headers = {'X-AUTH-SIGNATURE': sig, 'X-AUTH-APIKEY': self.trader.api_key, 'X-AUTH-EPOCH': epoch}
        
        try:
            res = requests.get(f"{self.trader.coinswitch_url}{endpoint}", headers=headers, params=params, timeout=5).json()
            if res.get('retCode') != 0: return None
            
            df = pd.DataFrame(res['result']['list'], columns=['ts', 'o', 'h', 'l', 'c', 'v', 't'])
            df[['o','h','l','c']] = df[['o','h','l','c']].apply(pd.to_numeric)
            df = df.iloc[::-1].reset_index(drop=True)

            # --- PRECIOUS 7-POINT FORMULA ---
            st_data = ta.supertrend(df['h'], df['l'], df['c'], 10, 3)
            bb = ta.bbands(df['c'], 20, 2)
            macd = ta.macd(df['c'])
            rsi = ta.rsi(df['c'], 14)
            df = pd.concat([df, st_data, bb, macd, rsi], axis=1)
            
            last = df.iloc[-1]
            prev = df.iloc[-2]

            # Logic Gates
            p1 = last['c'] > last['SUPERT_10_3.0']                  # ST Green
            p2 = last['MACDh_12_26_9'] > prev['MACDh_12_26_9']      # MACD Hist Rising
            p3 = last['MACD_12_26_9'] > 0                           # MACD Line > 0
            p4 = last['c'] > last['BBM_20_2.0']                     # ST Cross Mid
            p5 = last['BBU_20_2.0'] > prev['BBU_20_2.0']            # Upper BB Rising
            p6 = last['RSI_14'] >= 70                               # RSI Target 70+
            
            # SHIELD GATES (Out-of-Bounds Zones)
            call_shield = last['SUPERT_10_3.0'] < last['BBL_20_2.0']
            
            pink_alert = (p1 and p2 and p3 and p4 and p5 and p6) and not call_shield

            return {
                "ltp": last['c'], "st": last['SUPERT_10_3.0'], "mid": last['BBM_20_2.0'],
                "rsi": last['RSI_14'], "pink": pink_alert, "shield": call_shield
            }
        except: return None

# --- 3. PHOTOCOPY: STREAMLIT UI ---
st.set_page_config(page_title="PAWAN MASTER ALGO", layout="wide")
st_autorefresh(interval=10000, key="master_pulse")

API_KEY = "d4a0b5668e86d5256ca1b8387dbea87fc64a1c2e82e405d41c256c459c8f338d"
API_SECRET = "a5576f4da0ae455b616755a8340aef2b0eff4d05a775f82bc00352f079303511"

st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #1E293B; margin-bottom: 20px; }
    .m-table { width: 100%; border-collapse: collapse; background: #0B1629; border-radius: 10px; overflow: hidden; }
    .m-table th { background-color: #1E293B; color: #94A3B8; padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1E293B; font-family: monospace; font-size: 14px; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; animation: blinker 1.5s linear infinite; }
    .shield-gate { color: #f87171; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)

trader = DMABybit(API_KEY, API_SECRET)
scanner = MasterAlgoScanner(trader)

st.markdown(f"""
<div class="status-strip">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span>🏹 <b>PAWAN MASTER ALGO SYSTEM</b> | ACTIVE CLOUD SCAN</span>
        <span style="color:#00FBFF;">SYNC: {datetime.datetime.now().strftime("%H:%M:%S")}</span>
    </div>
</div>
""", unsafe_allow_html=True)

try:
    # Get Tickers for Top 100
    t_endpoint = "/v5/market/tickers"
    t_params = {"category": "linear"}
    t_sig, t_epoch = trader._generate_coinswitch_signature("GET", t_endpoint, t_params)
    t_headers = {'X-AUTH-SIGNATURE': t_sig, 'X-AUTH-APIKEY': API_KEY, 'X-AUTH-EPOCH': t_epoch}
    
    ticker_res = requests.get(f"https://dma.coinswitch.co{t_endpoint}", headers=t_headers, params=t_params).json()
    
    if ticker_res.get('retCode') == 0:
        all_movers = pd.DataFrame(ticker_res['result']['list'])
        all_movers['change'] = (pd.to_numeric(all_movers['lastPrice']) / pd.to_numeric(all_movers['prevPrice24h']) - 1) * 100
        
        tab1, tab2 = st.tabs(["🚀 TOP 100 GAINERS", "📉 TOP 100 LOSERS"])
        
        # Process Gainers then Losers
        for tab, data_group in zip([tab1, tab2], [all_movers.sort_values(by='change', ascending=False).head(100), all_movers.sort_values(by='change', ascending=True).head(100)]):
            with tab:
                html = """<table class="m-table">
                <tr><th>Symbol</th><th>24h Chg</th><th>LTP</th><th>ST Green</th><th>Midband</th><th>RSI</th><th>Trigger</th></tr>"""
                
                for _, row in data_group.iterrows():
                    v = scanner.get_audit(row['symbol'])
                    if v:
                        trigger = '<span class="pink-alert">PINK ALERT</span>' if v['pink'] else ("<span class='shield-gate'>SHIELD</span>" if v['shield'] else "WAIT")
                        html += f"""<tr>
                            <td style="color:#00FBFF"><b>{row['symbol']}</b></td>
                            <td style="color:{'#22c55e' if row['change'] > 0 else '#f87171'}">{row['change']:.2f}%</td>
                            <td>{v['ltp']:.4f}</td>
                            <td>{v['st']:.4f}</td>
                            <td>{v['mid']:.4f}</td>
                            <td>{v['rsi']:.1f}</td>
                            <td>{trigger}</td>
                        </tr>"""
                st.markdown(html + "</table>", unsafe_allow_html=True)
    else:
        st.error("DMA API Connection Failed. Check Credentials.")
except Exception as e:
    st.info("Scanner Warming Up... Connecting to DMA Endpoints.")
