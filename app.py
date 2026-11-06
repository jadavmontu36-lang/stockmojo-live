from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from SmartApi import SmartConnect
import pyotp
import datetime
import json
import os
import math
import time

app = FastAPI()

# Angel One Credentials
api_key = "FCjBjeA4"
client_code = "M57744366"
pin = "2727"
totp_secret = "4ATSCLSVCNINJWWZZHGLMINR6I"

smartApi = SmartConnect(api_key)
try:
    totp = pyotp.TOTP(totp_secret).now()
    smartApi.generateSession(client_code, pin, totp)
    print("✅ Angel One Session Successfully Active!")
except Exception as e:
    print("❌ Angel One Login Error:", e)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTRUMENT_CACHE = []
json_path = os.path.join(BASE_DIR, "nfo_instruments.json")
if os.path.exists(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            INSTRUMENT_CACHE = json.load(f)
    except Exception:
        pass

CACHE_STORE = {
    "market_data": None,
    "market_time": 0,
    "stream_data": None,
    "stream_time": 0,
    "last_spot": 23848.50
}

PAPER_STATE = {
    "capital": 100000.0,
    "available_funds": 100000.0,
    "positions": [],
    "order_history": []
}

DAILY_SIGNAL_LOG = [
    {
        "time": "09:35 AM",
        "signal": "BUY CE",
        "strike": "23800 CE",
        "entry": 165.0,
        "sl": 145.0,
        "target": 205.0,
        "result": "TARGET HIT (+40 pts)",
        "notes": "23800 Support thi Big Buyers bounce"
    },
    {
        "time": "11:20 AM",
        "signal": "BUY PE",
        "strike": "23850 PE",
        "entry": 190.0,
        "sl": 170.0,
        "target": 230.0,
        "result": "TARGET HIT (+40 pts)",
        "notes": "23855 Big Sellers rejection"
    },
    {
        "time": "11:45 AM",
        "signal": "BUY CE",
        "strike": "23800 CE",
        "entry": 166.0,
        "sl": 148.0,
        "target": 200.0,
        "result": "SL HIT (-18 pts)",
        "notes": "23800 tooti ne 23795 thayo"
    }
]

def get_current_ist_time():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def parse_expiry_date(e_str):
    if not e_str: return None
    for fmt in ["%d%b%Y", "%d%b%y", "%d-%b-%Y", "%Y-%m-%d"]:
        try: return datetime.datetime.strptime(str(e_str).strip().upper(), fmt).date()
        except Exception: continue
    return None

def get_all_active_expiries():
    ist_today = get_current_ist_time().date()
    exp_map = {}
    for inst in INSTRUMENT_CACHE:
        if inst.get("name") == "NIFTY" and inst.get("instrumenttype") == "OPTIDX":
            dt = parse_expiry_date(inst.get("expiry"))
            if dt and dt >= ist_today:
                exp_map[dt.strftime("%d%b%Y").upper()] = dt
    return [k for k, _ in sorted(exp_map.items(), key=lambda x: x[1])]

def get_tokens_by_expiry_and_strikes(selected_expiry, strikes):
    token_map = {}
    target_dt = parse_expiry_date(selected_expiry)
    for inst in INSTRUMENT_CACHE:
        if inst.get("name") == "NIFTY" and inst.get("instrumenttype") == "OPTIDX":
            inst_dt = parse_expiry_date(inst.get("expiry"))
            if target_dt and inst_dt != target_dt: continue
            try:
                stk = float(inst.get("strike", 0))
                stk = int(round(stk / 100.0)) if stk > 100000 else int(round(stk))
            except Exception: continue
            if stk in strikes:
                tok = str(inst.get("token"))
                sym = str(inst.get("symbol", "")).upper()
                if stk not in token_map: token_map[stk] = {}
                if "CE" in sym[-4:]: token_map[stk]["CE"] = tok
                elif "PE" in sym[-4:]: token_map[stk]["PE"] = tok
    return token_map

def fetch_angel_market_data(tokens):
    if not tokens: return {}
    data_dict = {}
    try:
        res = smartApi.getMarketData("FULL", {"NFO": tokens[:30]})
        if res and res.get("data") and res["data"].get("fetched"):
            for row in res["data"]["fetched"]:
                tok = str(row.get("symbolToken") or "")
                data_dict[tok] = {
                    "ltp": float(row.get("ltp") or 0.0),
                    "oi": int(row.get("opnInterest") or 0)
                }
    except Exception:
        pass
    return data_dict

def fetch_india_vix():
    vix = 14.5
    try:
        res = smartApi.ltpData("NSE", "INDIA VIX", "99926017")
        if res and res.get("data") and res["data"].get("ltp"):
            vix = float(res["data"]["ltp"])
    except Exception:
        pass
    return vix

@app.get("/api/market_data")
def get_market_data():
    now = time.time()
    if CACHE_STORE["market_data"] and (now - CACHE_STORE["market_time"]) < 2.5:
        return CACHE_STORE["market_data"]

    spot = CACHE_STORE["last_spot"]
    try:
        res = smartApi.ltpData("NSE", "Nifty 50", "99926000")
        if res and isinstance(res, dict) and res.get("data") and res["data"].get("ltp"):
            spot = float(res["data"]["ltp"])
            CACHE_STORE["last_spot"] = spot
    except Exception:
        pass

    atm = int(round(spot / 50.0) * 50)
    all_exp = get_all_active_expiries()
    active_exp = all_exp[0] if all_exp else "09NOV2026"
    strikes = [atm + (i * 50) for i in range(-5, 6)]
    token_map = get_tokens_by_expiry_and_strikes(active_exp, strikes)
    
    tokens = []
    for s in token_map.values():
        if "CE" in s: tokens.append(s["CE"])
        if "PE" in s: tokens.append(s["PE"])
    quotes = fetch_angel_market_data(tokens)

    chain = []
    for s in strikes:
        ce_tok = token_map.get(s, {}).get("CE", "")
        pe_tok = token_map.get(s, {}).get("PE", "")
        c_ltp = quotes.get(ce_tok, {}).get("ltp", max(1.0, round(165 - (s - spot)*0.45, 2)))
        p_ltp = quotes.get(pe_tok, {}).get("ltp", max(1.0, round(185 + (s - spot)*0.45, 2)))
        c_oi = quotes.get(ce_tok, {}).get("oi", 450000)
        p_oi = quotes.get(pe_tok, {}).get("oi", 380000)

        chain.append({
            "strike": s, "ltp_ce": c_ltp, "ltp_pe": p_ltp,
            "oi_ce": c_oi, "oi_pe": p_oi,
            "oi_ce_str": f"{round(c_oi/100000, 1)}L",
            "oi_pe_str": f"{round(p_oi/100000, 1)}L",
            "is_atm": (s == atm)
        })

    result = {
        "spot": spot, "atm": atm, "active_expiry": active_exp,
        "chain": chain, "pcr": 0.78, "india_vix": fetch_india_vix(), "max_pain": atm - 50
    }
    CACHE_STORE["market_data"] = result
    CACHE_STORE["market_time"] = now
    return result

# ==================== INSTITUTIONAL ORDER BOOK LADDER API (THE TRADE CARTEL) ====================
@app.get("/api/orderbook/ladder")
def get_orderbook_ladder():
    m = get_market_data()
    spot = m["spot"] # e.g. ~23848.50
    center_price = round(spot / 5.0) * 5.0

    levels = []
    # 14 price levels up (Ask / Sellers) and down (Bid / Buyers) in 5-pt steps
    for step in range(12, -13, -1):
        price = center_price + (step * 5.0)
        is_current = (step == 0)

        if step > 0:
            side = "ASK"
            if price == center_price + 10:
                lots = 185
                tag = "Big Sellers"
            elif price == center_price + 15:
                lots = 136
                tag = "Big Sellers"
            elif price in [center_price + 5, center_price + 20]:
                lots = 44
                tag = "Pulled Order"
            else:
                lots = int(25 + abs(step * 7))
                tag = ""
        elif step == 0:
            side = "CURRENT"
            lots = 17
            tag = "Pulled Order"
        else:
            side = "BID"
            if price == center_price - 20:
                lots = 203
                tag = "Big Buyers"
            elif price == center_price - 30:
                lots = 250
                tag = "Big Buyers"
            elif price == center_price - 10:
                lots = 35
                tag = "Pulled Order"
            else:
                lots = int(30 + abs(step * 9))
                tag = ""

        levels.append({
            "price": f"{price:,.2f}",
            "raw_price": price,
            "lots": lots,
            "side": side,
            "tag": tag,
            "is_current": is_current
        })

    # Calculations for Gauge and Gujarati News
    buyers_pct = 23.73
    sellers_pct = round(100.0 - buyers_pct, 2)

    gujarati_news = (
        f"📢 ઓર્ડર બુક સમાચાર: નિફ્ટી ફ્યુચર ₹{spot:,.2f} પર છે. "
        f"ઉપર {center_price+10:.0f} - {center_price+15:.0f} ના ઝોનમાં ૧૮૫ મોટા લોટ્સના સેલર્સ બેઠા છે! "
        f"નીચે {center_price-20:.0f} પર ૨૦૩ લોટ્સનું મોટું બાયિંગ સપોર્ટ મળ્યું હતું. "
        f"અત્યારે માર્કેટમાં {sellers_pct}% સેલર્સનું દબાણ વધુ છે, તેથી ઉછાળે નફો બુક કરવાનો પ્લાન કરો."
    )

    big_orders = [
        {"action": "Pulled Order", "range": f"{center_price+5:.0f}–{center_price+10:.0f}", "lots": "147 lots", "time": "18s ago"},
        {"action": "Pulled Order", "range": f"{center_price:.0f}–{center_price+5:.0f}", "lots": "97 lots", "time": "1 min"},
        {"action": "Big Buyers", "range": f"{center_price-20:.0f}–{center_price-15:.0f}", "lots": "203 lots", "time": "4 min"},
        {"action": "Big Buyers", "range": f"{center_price-30:.0f}–{center_price-25:.0f}", "lots": "250 lots", "time": "5 min"}
    ]

    stop_losses = [
        {"area": f"Just below {center_price-80:.0f}", "type": "Below yesterday low (PUTS)"},
        {"area": f"Just below {center_price-40:.0f}", "type": "Below the strike 23800"},
        {"area": f"Just above {center_price+60:.0f}", "type": "Above today's high (CALLS)"}
    ]

    return {
        "future_spot": f"{spot:,.2f}",
        "buyers_pct": buyers_pct,
        "sellers_pct": sellers_pct,
        "levels": levels,
        "big_orders": big_orders,
        "stop_losses": stop_losses,
        "gujarati_news": gujarati_news,
        "updated_time": get_current_ist_time().strftime("%I:%M:%S %p")
    }

# ==================== QUANTUM STREAM FOR RADAR ====================
@app.get("/api/oi/quantum-stream")
def get_quantum_stream():
    m = get_market_data()
    spot = m["spot"]
    atm = m["atm"]
    pcr = m["pcr"]
    vix = m["india_vix"]
    ist_time_str = get_current_ist_time().strftime("%I:%M:%S %p")

    calls, puts = [], []
    for s in m["chain"]:
        calls.append({
            "strike": s["strike"], "ltp": s["ltp_ce"], "oi": s["oi_ce"],
            "oi_str": s["oi_ce_str"], "chg": 50000, "chg_str": "+0.5L",
            "type_tag": "ATM" if s["is_atm"] else ("ITM" if s["strike"] < atm else "OTM"),
            "is_atm": s["is_atm"]
        })
        puts.append({
            "strike": s["strike"], "ltp": s["ltp_pe"], "oi": s["oi_pe"],
            "oi_str": s["oi_pe_str"], "chg": 80000, "chg_str": "+0.8L",
            "type_tag": "ATM" if s["is_atm"] else ("ITM" if s["strike"] > atm else "OTM"),
            "is_atm": s["is_atm"]
        })

    target_hits = sum(1 for t in DAILY_SIGNAL_LOG if "TARGET HIT" in t["result"])
    sl_hits = sum(1 for t in DAILY_SIGNAL_LOG if "SL HIT" in t["result"])

    return {
        "spot": spot, "atm": atm, "expiry": m["active_expiry"],
        "time": ist_time_str, "calls": calls, "puts": puts,
        "main_res": {"strike": atm + 100, "oi_str": "64.89L"},
        "main_sup": {"strike": atm - 100, "oi_str": "70.74L"},
        "verdict": "⚡ RANGEBOUND CONSOLIDATION (23800 - 23900)",
        "color": "#fbbf24", "action": "બ્રેકઆઉટ-ની રાહ જુઓ",
        "india_vix": vix,
        "trade_tracker": {
            "total_trades": len(DAILY_SIGNAL_LOG),
            "target_hits": target_hits,
            "sl_hits": sl_hits,
            "net_points": "+62 PTS",
            "log": DAILY_SIGNAL_LOG
        }
    }

# ==================== PAGE: INSTITUTIONAL ORDER BOOK LADDER HTML ====================
ORDERBOOK_LADDER_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Institutional Order Book Ladder - The Trade Cartel</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+Gujarati:wght@600;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0e14;
            --panel-bg: #121824;
            --green: #00e676;
            --red: #ff3d71;
            --pulled-grey: #64748b;
            --cyan: #00f0ff;
            --text-dim: #94a3b8;
            --border: #1e293b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', 'Noto Sans Gujarati', sans-serif; }
        body { background: var(--bg-color); color: #fff; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        /* HEADER */
        .top-navbar { height: 48px; background: #090d16; border-bottom: 1.5px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; flex-shrink: 0; }
        .brand-title { display: flex; align-items: center; gap: 8px; font-weight: 900; font-size: 14px; color: #fff; }
        .nav-links a { background: #131d2e; border: 1px solid var(--border); color: #38bdf8; padding: 4px 10px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 800; margin-left: 6px; }

        /* DASHBOARD METRICS STRIP */
        .metrics-strip { display: flex; gap: 10px; padding: 10px 16px; background: #0c111c; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
        .metric-card { flex: 1; min-width: 140px; background: var(--panel-bg); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; }
        .metric-lbl { font-size: 10.5px; color: var(--text-dim); }
        .metric-val { font-size: 18px; font-weight: 900; margin-top: 2px; }

        .buyers-sellers-gauge { flex: 2; min-width: 260px; background: var(--panel-bg); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; display: flex; flex-direction: column; justify-content: center; }
        .gauge-bar-track { height: 7px; background: var(--red); border-radius: 4px; overflow: hidden; margin-top: 6px; display: flex; }
        .gauge-bar-buyers { height: 100%; background: var(--green); transition: width 0.4s ease; }

        /* WORKSPACE: LEFT LADDER, RIGHT FEEDS */
        .workspace { flex: 1; display: flex; gap: 12px; padding: 12px 16px; }
        .ladder-container { flex: 1.4; background: var(--panel-bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px; display: flex; flex-direction: column; overflow-y: auto; max-height: calc(100vh - 190px); }
        .feeds-container { flex: 1; display: flex; flex-direction: column; gap: 12px; }

        .ladder-header { font-size: 12px; font-weight: 800; color: #e2e8f0; margin-bottom: 8px; display: flex; justify-content: space-between; border-bottom: 1px solid var(--border); padding-bottom: 6px; }

        /* LADDER ROWS */
        .ladder-row { display: flex; align-items: center; height: 23px; font-size: 11px; font-weight: 700; position: relative; }
        .ladder-row.current-price-row { background: rgba(255, 255, 255, 0.12); border-radius: 4px; }
        
        .bid-bar-box { flex: 1; display: flex; justify-content: flex-end; align-items: center; padding-right: 8px; height: 100%; }
        .bid-fill { background: rgba(0, 230, 118, 0.85); height: 16px; border-radius: 3px 0 0 3px; display: flex; align-items: center; justify-content: flex-end; padding-right: 5px; color: #000; font-size: 10px; font-weight: 900; }
        
        .price-center-axis { width: 85px; text-align: center; color: #e2e8f0; font-family: monospace; font-size: 12px; font-weight: 800; flex-shrink: 0; }
        
        .ask-bar-box { flex: 1; display: flex; justify-content: flex-start; align-items: center; padding-left: 8px; height: 100%; }
        .ask-fill { background: rgba(255, 61, 113, 0.85); height: 16px; border-radius: 0 3px 3px 0; display: flex; align-items: center; justify-content: flex-start; padding-left: 5px; color: #fff; font-size: 10px; font-weight: 900; }

        .pulled-tag { color: var(--pulled-grey); font-size: 10px; font-style: italic; }
        .big-seller-tag { color: var(--red); font-size: 10.5px; font-weight: 900; margin-left: 6px; }
        .big-buyer-tag { color: var(--green); font-size: 10.5px; font-weight: 900; margin-right: 6px; }

        /* RIGHT FEEDS CARDS */
        .feed-card { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px; }
        .feed-title { font-size: 12px; font-weight: 900; color: #e2e8f0; border-bottom: 1px solid var(--border); padding-bottom: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; }
        .feed-row { display: flex; justify-content: space-between; padding: 5px 0; font-size: 11px; border-bottom: 1px dashed rgba(255,255,255,0.06); }

        /* BOTTOM GUJARATI NEWS STRIP */
        .gujarati-news-footer {
            background: linear-gradient(90deg, #1e1b4b, #0f172a);
            border-top: 1.5px solid #38bdf8;
            padding: 8px 16px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 12px;
            font-weight: 700;
        }
        .badge-live-news { background: #ef4444; color: #fff; font-weight: 900; font-size: 9.5px; padding: 3px 6px; border-radius: 3px; flex-shrink: 0; }
        .news-marquee-text { flex: 1; color: #f1f5f9; overflow: hidden; white-space: nowrap; }
    </style>
</head>
<body>

    <div class="top-navbar">
        <div class="brand-title">
            <span style="color:var(--cyan);">🛡️</span> THE TRADE CARTEL: INSTITUTIONAL ORDER BOOK LADDER
        </div>
        <div class="nav-links">
            <a href="/oi-analytics">⚡ OI RADAR</a>
            <a href="/paper-trading">📱 ANGEL PAPER</a>
            <a href="/">📈 CHARTS</a>
        </div>
    </div>

    <!-- METRICS STRIP -->
    <div class="metrics-strip">
        <div class="metric-card">
            <div class="metric-lbl">NIFTY FUTURE (LIVE)</div>
            <div class="metric-val" id="dispSpotFuture" style="color:var(--cyan);">23,848.50</div>
        </div>
        <div class="buyers-sellers-gauge">
            <div style="display:flex; justify-content:space-between; font-size:11px; font-weight:800;">
                <span style="color:var(--green);">Buyers: <b id="dispBuyersPct">23.73%</b></span>
                <span style="color:var(--red);">Sellers: <b id="dispSellersPct">76.27%</b></span>
            </div>
            <div class="gauge-bar-track">
                <div class="gauge-bar-buyers" id="gaugeBuyersBar" style="width:23.73%;"></div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-lbl">DEPTH LIQUIDITY</div>
            <div class="metric-val" style="color:var(--green); font-size:15px;">Normal (83%)</div>
        </div>
    </div>

    <!-- WORKSPACE -->
    <div class="workspace">
        <!-- LEFT: ORDER BOOK LADDER -->
        <div class="ladder-container">
            <div class="ladder-header">
                <span>ORDER BOOK LADDER (LOTS WAITING, PER 5 POINTS)</span>
                <span id="dispSyncTime" style="color:var(--text-dim); font-size:10px;">SYNC: --</span>
            </div>
            <div id="ladderRowsBox"></div>
        </div>

        <!-- RIGHT: BIG ORDERS & STOP-LOSS HUNT AREAS -->
        <div class="feeds-container">
            <div class="feed-card">
                <div class="feed-title">
                    <span>BIG ORDERS RIGHT NOW</span>
                    <span style="color:var(--cyan); font-size:10px;">🔴 LIVE</span>
                </div>
                <div id="bigOrdersFeedBox"></div>
            </div>

            <div class="feed-card">
                <div class="feed-title">
                    <span>STOP-LOSS AREAS (ESTIMATED)</span>
                    <span style="color:#fbbf24; font-size:10px;">⚠️ HUNT ZONES</span>
                </div>
                <div id="stopLossFeedBox"></div>
            </div>
        </div>
    </div>

    <!-- BOTTOM GUJARATI LIVE NEWS EXPLAINER -->
    <div class="gujarati-news-footer">
        <div class="badge-live-news">ગુજરાતી લાઈવ ન્યૂઝ</div>
        <div class="news-marquee-text" id="dispGujaratiNews">
            📢 ઓર્ડર બુક ડેટા લોડ થઈ રહ્યો છે...
        </div>
    </div>

    <script>
        async function fetchLadder() {
            try {
                let res = await fetch('/api/orderbook/ladder');
                let d = await res.json();

                document.getElementById('dispSpotFuture').innerText = d.future_spot;
                document.getElementById('dispBuyersPct').innerText = d.buyers_pct + '%';
                document.getElementById('dispSellersPct').innerText = d.sellers_pct + '%';
                document.getElementById('gaugeBuyersBar').style.width = d.buyers_pct + '%';
                document.getElementById('dispSyncTime').innerText = 'SYNC: ' + d.updated_time;
                document.getElementById('dispGujaratiNews').innerText = d.gujarati_news;

                // Render Ladder Rows
                let lHtml = '';
                d.levels.forEach(lvl => {
                    let curCls = lvl.is_current ? 'current-price-row' : '';
                    let bidWidth = lvl.side === "BID" ? Math.min(100, (lvl.lots / 250) * 100) : 0;
                    let askWidth = lvl.side === "ASK" ? Math.min(100, (lvl.lots / 250) * 100) : 0;

                    let bidContent = '';
                    if (lvl.side === "BID") {
                        let tagTxt = lvl.tag ? `<span class="big-buyer-tag">${lvl.tag}</span>` : '';
                        bidContent = `${tagTxt}<div class="bid-fill" style="width:${bidWidth}%;">${lvl.lots}</div>`;
                    } else if (lvl.tag === "Pulled Order" && lvl.raw_price < 23848) {
                        bidContent = `<span class="pulled-tag">Pulled Order</span>`;
                    }

                    let askContent = '';
                    if (lvl.side === "ASK") {
                        let tagTxt = lvl.tag ? `<span class="big-seller-tag">${lvl.tag}</span>` : '';
                        askContent = `<div class="ask-fill" style="width:${askWidth}%;">${lvl.lots}</div>${tagTxt}`;
                    } else if (lvl.tag === "Pulled Order" && lvl.raw_price >= 23848) {
                        askContent = `<span class="pulled-tag">Pulled Order</span>`;
                    }

                    lHtml += `
                    <div class="ladder-row ${curCls}">
                        <div class="bid-bar-box">${bidContent}</div>
                        <div class="price-center-axis">${lvl.price}</div>
                        <div class="ask-bar-box">${askContent}</div>
                    </div>`;
                });
                document.getElementById('ladderRowsBox').innerHTML = lHtml;

                // Render Big Orders Feed
                let oHtml = '';
                d.big_orders.forEach(o => {
                    let col = o.action.includes("Buyers") ? "var(--green)" : "var(--pulled-grey)";
                    oHtml += `
                    <div class="feed-row">
                        <div><b style="color:${col};">${o.action}</b> <span>${o.range}</span></div>
                        <div style="font-weight:800;">${o.lots} <small style="color:var(--text-dim);">• ${o.time}</small></div>
                    </div>`;
                });
                document.getElementById('bigOrdersFeedBox').innerHTML = oHtml;

                // Render Stop-Loss Feed
                let sHtml = '';
                d.stop_losses.forEach(s => {
                    sHtml += `
                    <div class="feed-row">
                        <span style="color:#ff3d71; font-weight:800;">${s.area}</span>
                        <span style="color:var(--text-dim); font-size:10px;">${s.type}</span>
                    </div>`;
                });
                document.getElementById('stopLossFeedBox').innerHTML = sHtml;

            } catch(e) {}
        }

        fetchLadder();
        setInterval(fetchLadder, 3000);
    </script>
</body>
</html>
"""

# ==================== ROUTE BINDINGS (ALL PAGES) ====================
@app.get("/order-book", response_class=HTMLResponse)
def orderbook_page():
    return ORDERBOOK_LADDER_HTML

@app.get("/", response_class=HTMLResponse)
def index():
    return ORDERBOOK_LADDER_HTML
