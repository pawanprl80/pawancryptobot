import streamlit as st
import pandas as pd
import numpy as np
import datetime
import ccxt
import pandas_ta as ta

# --- 1. SETTINGS & PREMIUM THEME ---
st.set_page_config(page_title="PAWAN ALGO V5", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #050A14; color: #E2E8F0; }
    .status-strip { background-color: #162031; padding: 15px; border-radius: 12px; border: 1px solid #00FBFF; margin-bottom: 20px; }
    .m-table { width: 100%; border-collapse: collapse; background: #0B1629; color: white; border-radius: 10px; overflow: hidden; }
    .m-table th { background-color: #1E293B; color: #00FBFF; padding: 12px; text-align: left; border-bottom: 2px solid #00FBFF; text-transform: uppercase; font-size: 11px; }
    .m-table td { padding: 12px; border-bottom: 1px solid #1E293B; font-size: 14px; font-family: 'monospace'; }
    .pink-alert { color: #FF69B4 !important; font-weight: bold; text-shadow: 0 0 8px #FF69B4; }
    .stButton>button { width: 100%; background: linear-gradient(90deg, #00FBFF, #0080FF); color: black; font-weight: bold; border-radius: 8px; border: none; height: 3.5em; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE: TOP 100 + PURE 7 FORMULA ---
def get_market_intelligence():
    # Public endpoint to bypass regional restrictions
    ex = ccxt.binance({
        'options': {'defaultType': 'future'},
        'enableRateLimit': True,
        'headers': {'User-Agent': 'Mozilla/5.0'}
    })
    ex.urls['api']['public'] = 'https://fapi.binance.com/fapi/v1'
    
    try:
        # Fetch Top 100 Gainers/Losers
        tickers = ex.fetch_tickers()
        sorted_tickers = sorted(tickers.values(), key=lambda x: x['percentage'] if x['percentage'] else 0, reverse=True)
        top_100 = [t['symbol'] for t in sorted_tickers if '/USDT' in t['symbol']][:100]
        
        results = []
        # Audit top performers (optimized loop)
        for s in top_100[:20]: 
            ohlcv = ex.fetch_ohlcv(s, timeframe='5m', limit=100)
            if not ohlcv: continue
            
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            # Pure 7 Indicators
            st_df = ta.supertrend(df['h'], df['l'], df['c'], length=10, multiplier=3.0)
            bb = ta.bbands(df['c'], length=20, std=2)
            macd = ta.macd(df['c'])
            rsi = ta.rsi(df['c'], length=14)
            df = pd.concat([df, st_df, bb, macd, rsi], axis=1)
            
            # Clean Column References
            st_col = [c for c in df.columns if "SUPERT_" in c and "d" not in c.lower()][0]
            bbm_col = [c for c in df.columns if "BBM_" in c][0]
            bbu_col = [c for c in df.columns if "BBU_" in c][0]
            macdh_col = [c for c in df.columns if "MACDh_" in c][0]
            macd_col = [c for c in df.columns if c.startswith("MACD_")][0]
            rsi_col = [c for c in df.columns if "RSI_" in c][0]

            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # --- PURE 7 POINT AUDIT ---
            p1 = last[st_col] < last['c']                 # 1. ST Green
            p2 = last[macdh_col] > prev[macdh_col]        # 2. MACD Hist Rising
            p3 = last[macd_col] > 0                       # 3. MACD Line > 0
            p4 = last['c'] > last[bbm_col]                # 4. Price > Mid BB
            p5 = last[bbu_col] > prev[bbu_col]            # 5. Upper BB Rising
            p6 = last['c'] > last[bbu_col]                # 6. Price > Upper BB
            p7 = last[rsi_col] >= 70                      # 7. RSI 70+
            
            points = [p1, p2, p3, p4, p5, p6, p7]
            is_pink = all(points)
            score = sum(points)
            
            results.append({
                "Symbol": s, "LTP": last['c'], "Change": tickers[s]['percentage'],
                "Score": score, "Pink": is_pink, "Audit": points,
                "Target": s.replace("/", "")
            })
        return results, None
    except Exception as e:
        return [], str(e)

# --- 3. UI LAYOUT ---
with st.sidebar:
    st.markdown("<h1 style='color:#00FBFF;'>🏹 PAWAN V5</h1>", unsafe_allow_html=True)
    mode = st.radio("MENU", ["Top 100 Audit", "Visual Validator"])
    st.divider()
    if st.button("🚀 SCAN TOP MOVERS"):
        st.cache_data.clear()
        st.rerun()
    st.info("Formula: Pure 7-Point\nBackground: Stopped")

st.markdown(f"""
<div class="status-strip">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span><b>MODE:</b> PURE 7 PRECIOUS</span>
        <span><b>SYMBOLS:</b> TOP 100</span>
        <span><b>LAST UPDATE:</b> {datetime.datetime.now().strftime("%H:%M:%S")}</span>
    </div>
</div>
""", unsafe_allow_html=True)

data, err = get_market_intelligence()

if err:
    st.error(f"Scanner Connection Error. Please retry.")

if mode == "Top 100 Audit":
    if data:
        html = """<table class="m-table">
        <tr><th>Symbol</th><th>24h %</th><th>LTP</th><th>Audit Score</th><th>Condition</th></tr>"""
        for d in data:
            status = '<span class="pink-alert">💎 PINK ALERT</span>' if d['Pink'] else f"{d['Score']}/7 Match"
            chg_color = "lime" if d['Change'] > 0 else "red"
            html += f"""<tr>
                <td style="color:#00FBFF"><b>{d['Symbol']}</b></td>
                <td style="color:{chg_color}">{d['Change']:.2f}%</td>
                <td>{d['LTP']:.4f}</td>
                <td>{"✅"*d['Score']}{"⚪"*(7-d['Score'])}</td>
                <td>{status}</td>
            </tr>"""
        st.markdown(html + "</table>", unsafe_allow_html=True)
    else:
        st.info("Click 'SCAN TOP MOVERS' to identify opportunities.")

elif mode == "Visual Validator":
    if data:
        sel = st.selectbox("Select Symbol for Visual Audit", [x['Symbol'] for x in data])
        s_data = [x for x in data if x['Symbol'] == sel][0]
        
        # --- SVG INDICATOR GRAPH ---
        st.subheader(f"7-Point Trace: {sel}")
        labels = ["ST Green", "MACD Hist", "MACD > 0", "Price > Mid", "BB Up", "BB Break", "RSI 70+"]
        
        svg_items = ""
        for i, val in enumerate(s_data['Audit']):
            color = "#FF69B4" if val else "#1E293B"
            stroke = "#00FBFF" if val else "#475569"
            txt_color = "black" if val else "#94A3B8"
            svg_items += f"""
            <g transform="translate({10 + i*112}, 50)">
                <rect width="105" height="70" rx="10" fill="{color}" stroke="{stroke}" stroke-width="2"/>
                <text x="52" y="30" text-anchor="middle" fill="{txt_color}" font-family="Arial" font-size="10" font-weight="bold">{labels[i]}</text>
                <text x="52" y="55" text-anchor="middle" fill="{txt_color}" font-family="Arial" font-size="16">{'✅' if val else '⚪'}</text>
            </g>
            """
            
        svg_html = f"""
        <svg width="100%" height="150" viewBox="0 0 800 150" style="background:#0B1629; border-radius:12px;">
            {svg_items}
        </svg>
        """
        st.markdown(svg_html, unsafe_allow_html=True)
        
        # --- TRADINGVIEW WITH INDICATORS ---
        st.components.v1.html(f"""
            <div style="height:600px;">
                <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                <script type="text/javascript">
                new TradingView.widget({{
                  "width": "100%",
                  "height": 600,
                  "symbol": "BINANCE:{s_data['Target']}",
                  "interval": "5",
                  "timezone": "Etc/UTC",
                  "theme": "dark",
                  "style": "1",
                  "locale": "en",
                  "toolbar_bg": "#f1f3f6",
                  "enable_publishing": false,
                  "hide_side_toolbar": false,
                  "allow_symbol_change": true,
                  "studies": [
                    "SuperTrend@tv-basicstudies",
                    "BollingerBands@tv-basicstudies",
                    "MACD@tv-basicstudies",
                    "RSI@tv-basicstudies"
                  ],
                  "container_id": "tv_chart"
                }});
                </script>
                <div id="tv_chart"></div>
            </div>
        """, height=620)

st.caption("PAWAN V5 | 100 MOVER SCANNER | PURE 7 FORMULA | VISUAL VALIDATOR")
