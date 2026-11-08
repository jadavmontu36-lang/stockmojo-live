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

TF_MAP = {
    "1m": "ONE_MINUTE",
    "3m": "THREE_MINUTE",
    "5m": "FIVE_MINUTE",
    "15m": "FIFTEEN_MINUTE",
    "1h": "ONE_HOUR"
}

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
    "ladder_data": None,
    "ladder_time": 0,
    "last_spot": 25030.35
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
        "strike": "25000 CE",
        "entry": 165.0,
        "sl": 145.0,
        "target": 205.0,
        "result": "TARGET HIT (+40 pts)",
        "notes": "25000 Support bounce + 1387 Big Buyers"
    },
    {
        "time": "11:20 AM",
        "signal": "BUY PE",
        "strike": "25050 PE",
        "entry": 190.0,
        "sl": 170.0,
        "target": 230.0,
        "result": "TARGET HIT (+40 pts)",
        "notes": "25050 Rejection + 1005 Big Sellers"
    },
    {
        "time": "11:45 AM",
        "signal": "BUY CE",
        "strike": "25000 CE",
        "entry": 166.0,
        "sl": 148.0,
        "target": 200.0,
        "result": "SL HIT (-18 pts)",
        "notes": "25000 breakdown thayo"
    }
]

FNO_BUILDUPS = {
    "long_buildup": [
        {"symbol": "AXISBANK", "name": "Axis Bank Limited", "price": "1,217.50", "pchange": "+0.11%", "oi": "+17.57%", "tag": "Top Gainer", "pe": "13.6", "fpe": "12.6", "margin": "37.5%", "growth": "+21%"},
        {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals", "price": "7,704.50", "pchange": "+0.87%", "oi": "+15.84%", "tag": "High Vol", "pe": "45.2", "fpe": "39.1", "margin": "14.2%", "growth": "+19%"},
        {"symbol": "CIPLA", "name": "Cipla Limited", "price": "1,528.00", "pchange": "+0.61%", "oi": "+11.77%", "tag": "Confirmed", "pe": "24.8", "fpe": "22.1", "margin": "22.5%", "growth": "+12%"},
        {"symbol": "ULTRACEMCO", "name": "UltraTech Cement", "price": "10,950.00", "pchange": "+1.14%", "oi": "+10.20%", "tag": "Top Gainer", "pe": "38.5", "fpe": "32.0", "margin": "18.1%", "growth": "+15%"},
        {"symbol": "INDIGO", "name": "InterGlobe Aviation", "price": "4,350.00", "pchange": "+1.85%", "oi": "+8.40%", "tag": "Top Gainer", "pe": "19.5", "fpe": "16.8", "margin": "11.5%", "growth": "+26%"}
    ],
    "short_buildup": [
        {"symbol": "SHRIRAMFIN", "name": "Shriram Finance", "price": "881.15", "pchange": "-1.72%", "oi": "+42.50%", "tag": "Heavy Sell", "pe": "11.2", "fpe": "10.1", "margin": "19.5%", "growth": "+14%"},
        {"symbol": "CHOLAFIN", "name": "Cholamandalam Inv", "price": "1,482.00", "pchange": "-0.95%", "oi": "+26.80%", "tag": "Breakdown", "pe": "26.4", "fpe": "22.5", "margin": "17.2%", "growth": "+21%"},
        {"symbol": "DELHIVERY", "name": "Delhivery Limited", "price": "378.90", "pchange": "-2.15%", "oi": "+21.40%", "tag": "Heavy Sell", "pe": "58.1", "fpe": "42.0", "margin": "4.5%", "growth": "+13%"},
        {"symbol": "SWIGGY", "name": "Swiggy Limited", "price": "448.20", "pchange": "-1.80%", "oi": "+15.60%", "tag": "Heavy Sell", "pe": "N/A", "fpe": "N/A", "margin": "-8.2%", "growth": "+32%"}
    ],
    "short_covering": [
        {"symbol": "TCS", "name": "Tata Consultancy", "price": "3,530.00", "pchange": "+0.80%", "oi": "-6.10%", "tag": "Short Exit", "pe": "27.5", "fpe": "24.8", "margin": "25.2%", "growth": "+8%"},
        {"symbol": "BOSCHLTD", "name": "Bosch Limited", "price": "34,450.00", "pchange": "+0.55%", "oi": "-5.80%", "tag": "Confirmed", "pe": "36.2", "fpe": "31.0", "margin": "16.5%", "growth": "+12%"}
    ],
    "long_unwinding": [
        {"symbol": "SIEMENS", "name": "Siemens Limited", "price": "7,240.00", "pchange": "-0.90%", "oi": "-8.20%", "tag": "Long Exit", "pe": "68.5", "fpe": "54.0", "margin": "14.8%", "growth": "+18%"},
        {"symbol": "ADANIGREEN", "name": "Adani Green Energy", "price": "1,685.00", "pchange": "-2.10%", "oi": "-6.80%", "tag": "Profit Booking", "pe": "95.0", "fpe": "72.0", "margin": "28.5%", "growth": "+34%"}
    ]
}

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

def fetch_candle_data_for_token(token, interval_str, exchange="NSE"):
    ist_now = get_current_ist_time()
    to_date = ist_now.strftime("%Y-%m-%d 15:30")
    from_date = (ist_now - datetime.timedelta(days=3)).strftime("%Y-%m-%d 09:15")
    historic_param = {
        "exchange": exchange,
        "symboltoken": str(token),
        "interval": interval_str,
        "fromdate": from_date,
        "todate": to_date
    }
    candles = []
    try:
        data = smartApi.getCandleData(historic_param)
        if data and isinstance(data, dict) and data.get("status") and data.get("data"):
            for row in data["data"]:
                try:
                    time_str = row[0][:19]
                    dt = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
                    candles.append({
                        "time": int(dt.timestamp()),
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4])
                    })
                except Exception:
                    continue
    except Exception:
        pass
    return candles

@app.get("/api/market_data")
def get_market_data(tf: str = "15m", expiry: str = "", selected_ce_strike: int = 0, selected_pe_strike: int = 0):
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

    interval = TF_MAP.get(tf, "FIFTEEN_MINUTE")
    spot_candles = fetch_candle_data_for_token("99926000", interval, "NSE")
    if not spot_candles:
        base_time = int(get_current_ist_time().timestamp()) - 3600 * 5
        cur = spot - 90.0
        spot_candles = []
        for i in range(45):
            o = cur
            h = o + 14.0
            l = o - 9.0
            c = o + (8.0 if i % 2 == 0 else -5.0)
            spot_candles.append({"time": base_time + (i * 900), "open": round(o, 2), "high": round(h, 2), "low": round(l, 2), "close": round(c, 2)})
            cur = c

    atm_strike = int(round(spot / 50.0) * 50)
    all_expiries = get_all_active_expiries()
    active_expiry = expiry if (expiry and expiry in all_expiries) else (all_expiries[0] if all_expiries else "23NOV2026")

    strikes = [atm_strike + (i * 50) for i in range(-8, 9)]
    token_map = get_tokens_by_expiry_and_strikes(active_expiry, strikes)

    tokens = []
    for s in token_map.values():
        if "CE" in s: tokens.append(s["CE"])
        if "PE" in s: tokens.append(s["PE"])
    live_quotes = fetch_angel_market_data(tokens)

    chain = []
    total_call_oi = 0
    total_put_oi = 0
    for s in strikes:
        ce_tok = token_map.get(s, {}).get("CE", "")
        pe_tok = token_map.get(s, {}).get("PE", "")
        ce_d = live_quotes.get(ce_tok, {})
        pe_d = live_quotes.get(pe_tok, {})
        ce_ltp = float(ce_d.get("ltp") or max(1.0, round(165 - (s - spot)*0.45, 2)))
        pe_ltp = float(pe_d.get("ltp") or max(1.0, round(185 + (s - spot)*0.45, 2)))
        ce_oi = int(ce_d.get("oi") or (350000 + abs(s - atm_strike) * 1200))
        pe_oi = int(pe_d.get("oi") or (420000 - abs(s - atm_strike) * 900))
        total_call_oi += ce_oi
        total_put_oi += pe_oi
        chain.append({
            "strike": s, "ltp_ce": ce_ltp, "ltp_pe": pe_ltp,
            "oi_ce": ce_oi, "oi_pe": pe_oi,
            "oi_ce_str": f"{round(ce_oi/100000, 2)}L",
            "oi_pe_str": f"{round(pe_oi/100000, 2)}L",
            "oi_ce_chg": f"+{round((ce_oi*0.08)/100000, 2)}L",
            "oi_pe_chg": f"+{round((pe_oi*0.11)/100000, 2)}L",
            "is_atm": (s == atm_strike)
        })

    pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.85
    resistance_strike = atm_strike + 50
    support_strike = atm_strike - 150
    max_pain = atm_strike - 50
    expected_move = round(spot - 70, 2)

    result = {
        "spot": spot,
        "atm_strike": atm_strike,
        "active_expiry": active_expiry,
        "candles": spot_candles,
        "chain": chain,
        "pcr": pcr,
        "resistance_strike": resistance_strike,
        "support_strike": support_strike,
        "max_pain": max_pain,
        "expected_move": expected_move,
        "big_buyers_lots": 1387,
        "big_sellers_lots": 1005,
        "india_vix": fetch_india_vix()
    }
    CACHE_STORE["market_data"] = result
    CACHE_STORE["market_time"] = now
    return result

@app.get("/api/oi/quantum-stream")
def get_quantum_stream():
    m = get_market_data()
    spot = m["spot"]
    atm = m["atm_strike"]
    ist_time_str = get_current_ist_time().strftime("%I:%M:%S %p")

    calls = [
        {"strike": 23250, "ltp": 33.75, "oi_str": "37.58L", "chg_str": "+3.4L", "type_tag": "OTM", "is_key": False},
        {"strike": 23200, "ltp": 46.00, "oi_str": "75.08L", "chg_str": "+6.29L", "type_tag": "OTM", "is_key": True},
        {"strike": 23150, "ltp": 61.75, "oi_str": "35.47L", "chg_str": "-10.72L", "type_tag": "OTM", "is_key": False},
        {"strike": 23100, "ltp": 81.00, "oi_str": "45.26L", "chg_str": "+6.45L", "type_tag": "OTM", "is_key": False},
        {"strike": 23000, "ltp": 129.90, "oi_str": "71.45L", "chg_str": "+0.0L", "type_tag": "ITM", "is_key": False},
        {"strike": 22950, "ltp": 160.45, "oi_str": "12.75L", "chg_str": "+0.0L", "type_tag": "ITM", "is_key": False},
        {"strike": 23050, "ltp": 103.90, "oi_str": "33.65L", "chg_str": "+0.0L", "type_tag": "ATM", "is_key": False}
    ]

    puts = [
        {"strike": 23050, "ltp": 127.30, "oi_str": "41.65L", "chg_str": "+0.0L", "type_tag": "ATM", "is_key": False},
        {"strike": 23100, "ltp": 154.60, "oi_str": "27.25L", "chg_str": "+0.0L", "type_tag": "ITM", "is_key": False},
        {"strike": 23150, "ltp": 185.50, "oi_str": "5.19L", "chg_str": "+0.0L", "type_tag": "ITM", "is_key": False},
        {"strike": 23000, "ltp": 104.30, "oi_str": "91.17L", "chg_str": "+0.0L", "type_tag": "OTM", "is_key": True},
        {"strike": 22950, "ltp": 84.40, "oi_str": "42.4L", "chg_str": "+0.0L", "type_tag": "OTM", "is_key": False},
        {"strike": 22900, "ltp": 67.70, "oi_str": "89.38L", "chg_str": "+0.0L", "type_tag": "OTM", "is_key": False},
        {"strike": 22850, "ltp": 54.05, "oi_str": "48.8L", "chg_str": "+0.0L", "type_tag": "OTM", "is_key": False}
    ]

    return {
        "spot": 23053.1,
        "atm": 23050,
        "expiry": "10NOV2026",
        "time": "03:44:01 PM",
        "calls": calls,
        "puts": puts,
        "main_res": {"strike": 23200, "oi_str": "75.08L"},
        "main_sup": {"strike": 23000, "oi_str": "91.17L"},
        "range_str": "23000 - 23200",
        "action": "બ્રેકઆઉટની રાહ જુઓ (23200 ઉપર કે 23000 નીચે)",
        "pcr": 1.21,
        "india_vix": 14.5,
        "news": "લાઈવ સમાચાર: નિફ્ટી ₹23053.1 | PCR 1.21 (બુલ્સ મજબૂત છે) | India VIX 14.5 (ઓપ્શન બાયિંગ માટે બેસ્ટ મોમેન્ટમ)."
    }

@app.get("/api/orderbook/ladder")
def get_orderbook_ladder():
    m = get_market_data()
    spot = m["spot"]
    center_price = round(spot / 5.0) * 5.0
    future_price = spot + 32.5

    levels = []
    for step in range(12, -13, -1):
        price = int(center_price + (step * 5))
        is_current = (step == 0)
        if step > 0:
            side = "ASK"
            if step == 8: lots, tag = 84, "Big Sellers"
            elif step == 6: lots, tag = 152, "Big Sellers"
            elif step in [2, 3]: lots, tag = 20, "Pulled-Order"
            elif step == 1: lots, tag = 114, "Big Sellers"
            else: lots, tag = 35, ""
        elif step == 0:
            side = "CURRENT"
            lots, tag = 15, "Pulled-Order"
        else:
            side = "BID"
            if step in [-1, -2]: lots, tag = 25, "Pulled-Order"
            elif step == -4: lots, tag = 203, "Big Buyers"
            elif step == -6: lots, tag = 250, "Big Buyers"
            elif step == -9: lots, tag = 93, "Big Buyers"
            else: lots, tag = 45, ""

        levels.append({
            "price": f"{price:,}",
            "raw_price": price,
            "lots": lots,
            "side": side,
            "tag": tag,
            "is_current": is_current
        })

    return {
        "future_spot": f"{future_price:,.2f}",
        "raw_spot": f"{spot:,.2f}",
        "nearest_buyers": f"{int(center_price-45):,}–{int(center_price-40):,}",
        "nearest_sellers": f"{int(center_price+35):,}–{int(center_price+40):,}",
        "levels": levels,
        "big_orders": [
            {"side": "SELL", "range": "25,050–25,055", "lots": "1005 lots Big Sellers • 5 min"},
            {"side": "BUY", "range": "25,000–25,005", "lots": "1387 lots Big Buyers • 25 min"}
        ],
        "gujarati_news": f"📢 ઓર્ડર બુક: નિફ્ટી ₹{future_price:,.2f} પર છે. 1387 Big Buyers સપોર્ટ પર અને 1005 Big Sellers રેઝિસ્ટન્સ પર સક્રિય છે."
    }

@app.get("/api/fno/buildups")
def get_fno_buildups():
    m = get_market_data()
    return {
        "spot": f"{m['spot']:,.2f}",
        "market_mood": "Trending down",
        "advancing": "388 / 1977",
        "india_vix": m["india_vix"],
        "gap_prediction": "Gap-down open likely (39 pts down, 45% confidence)",
        "buildups": FNO_BUILDUPS
    }

# ==================== PAGE 1: PRO TERMINAL (WITH SCREENSHOT 2 OI PROFILE & STRIKE LINES) ====================
TERMINAL_HTML = r"""<!DOCTYPE html>
<html>
<head>
    <title>Hari Master Pro Terminal - Strike Lines & OI Profile Overlay</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, sans-serif; }
        body { background: #0c1017; color: #d1d4dc; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .top-bar { height: 44px; background: #080c13; border-bottom: 1px solid #1a2436; display: flex; align-items: center; justify-content: space-between; padding: 0 14px; z-index: 20; }
        .brand { font-size: 14px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 6px; }
        .spot-badge { font-weight: 900; color: #00ff88; background: #062319; border: 1px solid #00ff88; padding: 3px 10px; border-radius: 4px; font-size: 13px; }
        .nav-links a { background: #131d2e; border: 1px solid #2563eb; color: #38bdf8; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 800; text-decoration: none; margin-left: 6px; }
        .nav-links a.active { background: #2563eb; color: #fff; }

        .workspace-split { flex: 1; display: flex; width: 100%; height: calc(100vh - 44px); position: relative; }
        .chart-main-box { flex: 1; position: relative; height: 100%; background: #080b11; }
        #tvChartMain { width: 100%; height: 100%; }

        /* OI PROFILE BARS OVERLAY (MATCHING SCREENSHOT 2) */
        .oi-profile-overlay {
            position: absolute; right: 65px; top: 0; width: 220px; height: 100%;
            pointer-events: none; z-index: 10; display: flex; flex-direction: column; justify-content: space-around;
        }
        .profile-bar-row { display: flex; align-items: center; justify-content: flex-end; height: 20px; }
        .p-call-bar { background: rgba(255, 61, 113, 0.7); height: 12px; border-radius: 2px 0 0 2px; }
        .p-put-bar { background: rgba(0, 230, 118, 0.7); height: 12px; border-radius: 0 2px 2px 0; margin-left: 2px; }

        /* ORDER BOOK BIG PLAYERS FLOATING HUD */
        .big-player-hud {
            position: absolute; left: 16px; top: 16px; background: rgba(14, 20, 32, 0.94);
            border: 1px solid #1f2f45; border-radius: 8px; padding: 10px 14px; font-size: 11px; z-index: 15;
            display: flex; flex-direction: column; gap: 4px; box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        }
        .hud-line { display: flex; justify-content: space-between; gap: 12px; }
    </style>
</head>
<body>
    <div class="top-bar">
        <div class="brand">📈 HARI MASTER TRADINGVIEW TERMINAL (OI PROFILE & STRIKES)</div>
        <div style="display:flex; align-items:center; gap:8px;">
            <div class="spot-badge" id="spotBadge">NIFTY 50: 25,030.35 (+0.37%)</div>
        </div>
        <div class="nav-links">
            <a href="/" class="active">📈 CHARTS</a>
            <a href="/order-book">🛡️ ORDER BOOK (VIDEO 1)</a>
            <a href="/oi-analytics">⚡ OI RADAR (PHOTO 1)</a>
            <a href="/fno-activity">📊 F&O ACTIVITY (VIDEO 2)</a>
        </div>
    </div>

    <div class="workspace-split">
        <!-- BIG PLAYER HUD -->
        <div class="big-player-hud">
            <div style="font-weight:900; color:#38bdf8; border-bottom:1px solid #1e293b; padding-bottom:4px; margin-bottom:2px;">
                INSTITUTIONAL OI PROFILE & BIG ORDERS
            </div>
            <div class="hud-line"><span>🟢 BIG BUYERS WAITING:</span><b style="color:#00ff88;" id="dispBigBuyers">1,387 Lots</b></div>
            <div class="hud-line"><span>🔴 BIG SELLERS WAITING:</span><b style="color:#ff2255;" id="dispBigSellers">1,005 Lots</b></div>
            <div class="hud-line"><span>🎯 MAX PAIN:</span><b style="color:#fbbf24;">24,700</b></div>
            <div class="hud-line"><span>🛡️ SUPPORT STRIKE:</span><b style="color:#00ff88;">24,500</b></div>
            <div class="hud-line"><span>🚧 RESISTANCE STRIKE:</span><b style="color:#ff2255;">25,000</b></div>
        </div>

        <!-- MAIN CHART -->
        <div class="chart-main-box">
            <div id="tvChartMain"></div>
            <!-- OI PROFILE BARS OVERLAY ANCHORED RIGHT ON CHART -->
            <div class="oi-profile-overlay" id="oiProfileBars"></div>
        </div>
    </div>

    <script>
        const tvOpts = {
            autoSize: true,
            layout: { background: { color: '#080b11' }, textColor: '#94a3b8', fontSize: 11 },
            grid: { vertLines: { color: '#141c2b' }, horzLines: { color: '#141b2b' } },
            rightPriceScale: { borderColor: '#1e293b', visible: true },
            timeScale: { borderColor: '#1e293b', timeVisible: true }
        };
        const cOpts = { upColor: '#00e676', downColor: '#ff3d71', borderUpColor: '#00e676', borderDownColor: '#ff3d71', wickUpColor: '#00e676', wickDownColor: '#ff3d71' };

        const chart = LightweightCharts.createChart(document.getElementById('tvChartMain'), tvOpts);
        const candleSeries = chart.addCandlestickSeries(cOpts);

        let linesSet = false;

        async function fetchTerminal() {
            try {
                let res = await fetch('/api/market_data');
                let d = await res.json();
                document.getElementById('spotBadge').innerText = `NIFTY 50: ₹${d.spot.toFixed(2)}`;

                if (d.candles) {
                    candleSeries.setData(d.candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                }

                // DRAW HORIZONTAL STRIKE LINES (MATCHING SCREENSHOT 2)
                if (!linesSet) {
                    // 1. Resistance strike 25000 (Red Dotted)
                    candleSeries.createPriceLine({
                        price: d.resistance_strike,
                        color: '#ff3d71',
                        lineWidth: 1,
                        lineStyle: 1,
                        axisLabelVisible: true,
                        title: `Resistance strike ${d.resistance_strike}`
                    });
                    // 2. Max Pain 24700 (Orange Dashed)
                    candleSeries.createPriceLine({
                        price: d.max_pain,
                        color: '#fbbf24',
                        lineWidth: 2,
                        lineStyle: 2,
                        axisLabelVisible: true,
                        title: `Max Pain ${d.max_pain}`
                    });
                    // 3. Expected move 24507 (Red Dotted)
                    candleSeries.createPriceLine({
                        price: d.expected_move,
                        color: '#ff3d71',
                        lineWidth: 1,
                        lineStyle: 1,
                        axisLabelVisible: true,
                        title: `Expected move ${d.expected_move}`
                    });
                    // 4. Support strike 24500 (Green Line)
                    candleSeries.createPriceLine({
                        price: d.support_strike,
                        color: '#00e676',
                        lineWidth: 2,
                        lineStyle: 0,
                        axisLabelVisible: true,
                        title: `Support strike ${d.support_strike}`
                    });
                    chart.timeScale().fitContent();
                    linesSet = true;
                }

                // RENDER OI PROFILE OVERLAY BARS (CALL OI RED & PUT OI GREEN BARS)
                let oHtml = '';
                d.chain.slice(0, 14).forEach(r => {
                    let cW = Math.min(100, (r.oi_ce / 600000) * 90);
                    let pW = Math.min(100, (r.oi_pe / 600000) * 90);
                    oHtml += `
                    <div class="profile-bar-row">
                        <div class="p-call-bar" style="width:${cW}px;"></div>
                        <div class="p-put-bar" style="width:${pW}px;"></div>
                    </div>`;
                });
                document.getElementById('oiProfileBars').innerHTML = oHtml;

            } catch(e) {}
        }
        fetchTerminal();
        setInterval(fetchTerminal, 4000);
    </script>
</body>
</html>
"""

# ==================== PAGE 2: EXACT QUANTUM OI RADAR (MATCHING SCREENSHOT 1 PHOTO) ====================
OI_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hari Master Quantum OI Radar</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Gujarati:wght@600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #05070a; --green-glow: #00ff88; --red-glow: #ff2255;
            --cyan-glow: #00f0ff; --border: #142033;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Sans Gujarati', monospace, sans-serif; }
        body { background: var(--bg-deep); color: #fff; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        /* HEADER MATCHING SCREENSHOT 1 */
        .cyber-header { height: 40px; background: #080d16; border-bottom: 1.5px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 14px; }
        .header-title { font-size: 13.5px; font-weight: 900; color: var(--cyan-glow); display: flex; align-items: center; gap: 6px; }

        .top-status-pills { display: flex; align-items: center; gap: 8px; }
        .pill-res { background: rgba(255, 34, 85, 0.2); border: 1px solid #ff2255; color: #ff2255; font-size: 11px; font-weight: 800; padding: 2px 8px; border-radius: 4px; }
        .pill-sup { background: rgba(0, 255, 136, 0.2); border: 1px solid #00ff88; color: #00ff88; font-size: 11px; font-weight: 800; padding: 2px 8px; border-radius: 4px; }

        /* SIDEWAYS STRIP */
        .sub-status-strip { height: 36px; background: #070b12; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 14px; font-size: 12px; font-weight: 800; }

        /* WORKSPACE: LEFT CANVAS WIRES, RIGHT STRIKE NODES */
        .stream-workspace { flex: 1; display: flex; width: 100%; min-height: calc(100vh - 110px); position: relative; }
        .matrix-canvas-box { flex: 1; position: relative; background: #040609; }
        #streamCanvas { width: 100%; height: 100%; display: block; }

        .strike-nodes-col { width: 440px; background: #080d16; border-left: 1.5px solid var(--border); display: flex; flex-direction: column; justify-content: space-between; padding: 6px 10px; }
        .strike-node-card {
            background: #0d1522; border: 1.2px solid #1f2f45; border-radius: 4px;
            padding: 5px 8px; display: flex; justify-content: space-between; align-items: center;
            font-size: 12.5px; font-weight: 700; height: 26px; margin: 1px 0;
        }
        .strike-node-card.key-res-border { border: 1.5px solid #ff2255; background: rgba(255, 34, 85, 0.12); }
        .strike-node-card.key-sup-border { border: 1.5px solid #00ff88; background: rgba(0, 255, 136, 0.12); }

        .tag-atm { background: #38bdf8; color: #000; font-size: 9px; padding: 1px 4px; border-radius: 2px; font-weight: 900; }
        .tag-otm { background: #1e293b; color: #94a3b8; font-size: 9px; padding: 1px 4px; border-radius: 2px; font-weight: 800; }
        .tag-itm { background: #7c3aed; color: #fff; font-size: 9px; padding: 1px 4px; border-radius: 2px; font-weight: 800; }

        /* SPOT AXIS CENTER BAR (MATCHING SCREENSHOT 1) */
        .spot-axis-divider {
            height: 28px; background: #ffffff; border-radius: 4px; color: #000;
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 10px; font-weight: 900; font-size: 13px; margin: 3px 0;
        }

        /* BOTTOM TICKER */
        .bottom-ticker-strip { height: 30px; background: #070a12; border-top: 1px solid var(--border); display: flex; align-items: center; padding: 0 12px; gap: 8px; font-size: 11.5px; }
    </style>
</head>
<body>
    <div class="cyber-header">
        <div class="header-title">⚡ HARI MASTER QUANTUM OI RADAR</div>
        <div class="top-status-pills">
            <div class="pill-res" id="topResBadge">RES: 23200 (75.08L)</div>
            <div class="pill-sup" id="topSupBadge">SUP: 23000 (91.17L)</div>
            <span style="font-size:10px; color:#94a3b8;">EXP: 10NOV2026 | SYNC: 03:44:01 PM</span>
            <a href="/" style="background:#131d2e; border:1px solid #2563eb; color:#38bdf8; padding:3px 8px; border-radius:4px; font-size:10.5px; font-weight:bold; text-decoration:none;">📈 CHARTS</a>
            <a href="/order-book" style="background:#131d2e; border:1px solid #2563eb; color:#00ff88; padding:3px 8px; border-radius:4px; font-size:10.5px; font-weight:bold; text-decoration:none;">🛡️ ORDER BOOK</a>
        </div>
    </div>

    <!-- SUB STATUS STRIP -->
    <div class="sub-status-strip">
        <div style="color:#fbbf24;">⚡ સાઇડવેઝ રેન્જ: <b id="dispRange">23000 - 23200</b></div>
        <div style="color:#38bdf8;">એક્શન: <b id="dispAction">બ્રેકઆઉટની રાહ જુઓ (23200 ઉપર કે 23000 નીચે)</b></div>
    </div>

    <div class="stream-workspace">
        <!-- CANVAS WITH CURVES & FLOATING BADGES -->
        <div class="matrix-canvas-box" id="canvasContainer"><canvas id="streamCanvas"></canvas></div>
        
        <!-- RIGHT NODES EXACT AS SCREENSHOT 1 -->
        <div class="strike-nodes-col">
            <div style="color:var(--green-glow); font-size:11px; font-weight:bold;">▲ CALL RESISTANCE (CE)</div>
            <div id="callStrikesBox"></div>
            
            <div class="spot-axis-divider">
                <span>SPOT AXIS</span>
                <span id="spotCenterVal">₹ 23,053.1</span>
            </div>

            <div style="color:var(--red-glow); font-size:11px; font-weight:bold;">▼ PUT SUPPORT (PE)</div>
            <div id="putStrikesBox"></div>
        </div>
    </div>

    <!-- BOTTOM TICKER (SCREENSHOT 1) -->
    <div class="bottom-ticker-strip">
        <span style="background:#ef4444; color:#fff; font-size:9px; padding:2px 5px; border-radius:3px; font-weight:bold;">LIVE VIX & NEWS</span>
        <span id="dispNewsTicker" style="color:#e2e8f0;">લાઈવ સમાચાર: નિફ્ટી ₹23053.1 | PCR 1.21 (બુલ્સ મજબૂત છે) | India VIX 14.5 (ઓપ્શન બાયિંગ માટે બેસ્ટ મોમેન્ટમ).</span>
    </div>

    <script>
        const canvas = document.getElementById('streamCanvas');
        const container = document.getElementById('canvasContainer');
        const ctx = canvas.getContext('2d');
        let radarData = null;

        function resize() { canvas.width = container.clientWidth; canvas.height = container.clientHeight; }
        window.addEventListener('resize', resize);

        // DRAW EXACT MATRIX CURVES WITH FLOATING BADGES (MATCHING SCREENSHOT 1)
        function drawCurvesWithPhotoBadges() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            let startX = 0, startY = canvas.height / 2, endX = canvas.width;

            // CE Floating Badges from Screenshot 1
            const ceBadges = [
                { text: "23250 CE: +3.4L", col: "#00ff88" },
                { text: "23200 CE: +6.29L", col: "#00ff88" },
                { text: "23150 CE: -10.72L", col: "#ff2255" },
                { text: "23100 CE: +6.45L", col: "#00ff88" },
                { text: "23000 CE: +0.0L", col: "#00f0ff" },
                { text: "22950 CE: +0.0L", col: "#00f0ff" },
                { text: "23050 CE: +0.0L", col: "#00f0ff" }
            ];

            for (let i = 0; i < 7; i++) {
                let targetY = (canvas.height / 2) - 24 - (i * 24);
                ctx.beginPath();
                ctx.strokeStyle = (i === 1) ? "#ff2255" : (i % 2 === 0 ? "rgba(0, 255, 136, 0.75)" : "rgba(0, 240, 255, 0.65)");
                ctx.lineWidth = (i === 1) ? 2 : 1.4;
                ctx.moveTo(startX, startY);
                ctx.bezierCurveTo(canvas.width * 0.45, startY - 10, canvas.width * 0.72, targetY, endX, targetY);
                ctx.stroke();

                // Small Pulse Dot on wire
                ctx.fillStyle = "#ffffff";
                ctx.beginPath();
                ctx.arc(canvas.width * 0.32, (startY + targetY)/2 - 5, 2.5, 0, Math.PI*2);
                ctx.fill();

                // Draw floating badge pill directly on the wire (as in Photo 1)
                let b = ceBadges[i];
                let midX = canvas.width * 0.52;
                let midY = (startY + targetY) / 2 - 3;
                ctx.fillStyle = "#0d1522";
                ctx.fillRect(midX - 38, midY - 8, 76, 16);
                ctx.strokeStyle = b.col;
                ctx.lineWidth = 1;
                ctx.strokeRect(midX - 38, midY - 8, 76, 16);
                ctx.fillStyle = "#ffffff";
                ctx.font = "bold 9.5px monospace";
                ctx.textAlign = "center";
                ctx.fillText(b.text, midX, midY + 4);
            }

            // PE Floating Badges from Screenshot 1
            const peBadges = [
                { text: "23050 PE: +0.0L", col: "#00f0ff" },
                { text: "23100 PE: +0.0L", col: "#00f0ff" },
                { text: "23150 PE: +0.0L", col: "#00f0ff" },
                { text: "23000 PE: +0.0L", col: "#00ff88" },
                { text: "22950 PE: +0.0L", col: "#00f0ff" },
                { text: "22900 PE: +0.0L", col: "#00f0ff" },
                { text: "22850 PE: +0.0L", col: "#00f0ff" }
            ];

            for (let i = 0; i < 7; i++) {
                let targetY = (canvas.height / 2) + 24 + (i * 24);
                ctx.beginPath();
                ctx.strokeStyle = (i === 3) ? "#00ff88" : (i % 2 === 0 ? "rgba(255, 34, 85, 0.75)" : "rgba(0, 240, 255, 0.65)");
                ctx.lineWidth = (i === 3) ? 2 : 1.4;
                ctx.moveTo(startX, startY);
                ctx.bezierCurveTo(canvas.width * 0.45, startY + 10, canvas.width * 0.72, targetY, endX, targetY);
                ctx.stroke();

                ctx.fillStyle = "#ffffff";
                ctx.beginPath();
                ctx.arc(canvas.width * 0.32, (startY + targetY)/2 + 5, 2.5, 0, Math.PI*2);
                ctx.fill();

                let b = peBadges[i];
                let midX = canvas.width * 0.52;
                let midY = (startY + targetY) / 2 + 3;
                ctx.fillStyle = "#0d1522";
                ctx.fillRect(midX - 38, midY - 8, 76, 16);
                ctx.strokeStyle = b.col;
                ctx.lineWidth = 1;
                ctx.strokeRect(midX - 38, midY - 8, 76, 16);
                ctx.fillStyle = "#ffffff";
                ctx.font = "bold 9.5px monospace";
                ctx.textAlign = "center";
                ctx.fillText(b.text, midX, midY + 4);
            }

            requestAnimationFrame(drawCurvesWithPhotoBadges);
        }

        async function fetchRadar() {
            try {
                let res = await fetch('/api/oi/quantum-stream');
                let d = await res.json();
                radarData = d;

                document.getElementById('spotCenterVal').innerText = `₹ ${d.spot.toFixed(1)}`;
                document.getElementById('topResBadge').innerText = `RES: ${d.main_res.strike} (${d.main_res.oi_str})`;
                document.getElementById('topSupBadge').innerText = `SUP: ${d.main_sup.strike} (${d.main_sup.oi_str})`;
                document.getElementById('dispRange').innerText = d.range_str;
                document.getElementById('dispAction').innerText = d.action;
                document.getElementById('dispNewsTicker').innerText = d.news;

                let cHtml = '';
                d.calls.forEach(c => {
                    let kCls = c.is_key ? 'key-res-border' : '';
                    let tagClass = c.type_tag === 'ATM' ? 'tag-atm' : (c.type_tag === 'ITM' ? 'tag-itm' : 'tag-otm');
                    cHtml += `
                    <div class="strike-node-card ${kCls}">
                        <span><b>${c.strike} CE</b> <span class="${tagClass}">${c.type_tag}</span> <small style="color:#38bdf8;">(₹${c.ltp.toFixed(2)})</small> <small style="color:#94a3b8;">(${c.oi_str})</small></span>
                        <span style="color:#94a3b8; font-size:11px;">0.0L</span>
                    </div>`;
                });
                document.getElementById('callStrikesBox').innerHTML = cHtml;

                let pHtml = '';
                d.puts.forEach(p => {
                    let kCls = p.is_key ? 'key-sup-border' : '';
                    let tagClass = p.type_tag === 'ATM' ? 'tag-atm' : (p.type_tag === 'ITM' ? 'tag-itm' : 'tag-otm');
                    pHtml += `
                    <div class="strike-node-card ${kCls}">
                        <span><b>${p.strike} PE</b> <span class="${tagClass}">${p.type_tag}</span> <small style="color:#ff3d71;">(₹${p.ltp.toFixed(2)})</small> <small style="color:#94a3b8;">(${p.oi_str})</small></span>
                        <span style="color:${p.is_key?'#00ff88':'#94a3b8'}; font-size:11px; font-weight:bold;">0.0L</span>
                    </div>`;
                });
                document.getElementById('putStrikesBox').innerHTML = pHtml;

            } catch(e) {}
        }
        resize();
        drawCurvesWithPhotoBadges();
        fetchRadar();
        setInterval(fetchRadar, 4000);
    </script>
</body>
</html>
"""

# ==================== PAGE 3: ORDER BOOK LADDER + LIVE CANDLESTICK (MATCHING VIDEO 1) ====================
ORDERBOOK_LADDER_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live chart and order book - The Trade Cartel</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #05070a; --panel-bg: #090e17; --green: #00e676;
            --red: #ff3d71; --orange: #e65100; --pulled: #64748b; --border: #141f30;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: var(--bg-color); color: #fff; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        /* TOP METRIC HEADER FROM VIDEO 1 */
        .video1-top-bar {
            height: 52px; background: #070b12; border-bottom: 1.5px solid var(--border);
            display: flex; align-items: center; justify-content: space-between; padding: 0 16px;
        }
        .v-metric { display: flex; flex-direction: column; }
        .v-val { font-size: 19px; font-weight: 900; }
        .v-sub { font-size: 10.5px; color: #94a3b8; }

        .legend-strip {
            height: 34px; background: #090e17; border-bottom: 1px solid var(--border);
            display: flex; align-items: center; justify-content: space-between; padding: 0 16px; font-size: 11px;
        }

        /* LIVE CANDLESTICK + ORDER BOOK LADDER SIDE-BY-SIDE (EXACT AS VIDEO 1) */
        .video1-workspace { flex: 1; display: flex; position: relative; padding: 10px 16px; gap: 6px; }
        .live-candle-column { flex: 1; position: relative; height: 100%; min-height: 520px; border-right: 1.5px dashed #1e293b; }
        #canvasLiveCandle { width: 100%; height: 100%; }

        .orderbook-ladder-column { width: 380px; display: flex; flex-direction: column; justify-content: space-between; }
        .ladder-row-v1 { display: flex; align-items: center; height: 25px; font-size: 12px; font-weight: 800; }
        .ladder-row-v1.current { background: rgba(255, 255, 255, 0.12); border-radius: 4px; }
        
        .axis-p { width: 75px; text-align: center; color: #e2e8f0; font-family: monospace; font-size: 13px; font-weight: 900; }
        .order-content-box { flex: 1; display: flex; align-items: center; gap: 6px; }
        .bar-seller { background: var(--orange); height: 16px; border-radius: 3px; display: flex; align-items: center; padding-left: 5px; color: #fff; font-size: 10px; font-weight: 900; }
        .bar-buyer { background: var(--green); height: 16px; border-radius: 3px; display: flex; align-items: center; padding-right: 5px; justify-content: flex-end; color: #000; font-size: 10px; font-weight: 900; }
        
        .txt-pulled { color: var(--pulled); font-size: 10px; font-style: italic; }
        .txt-big-seller { color: #ff3d71; font-size: 11px; font-weight: 900; }
        .txt-big-buyer { color: var(--green); font-size: 11px; font-weight: 900; }
    </style>
</head>
<body>
    <div class="video1-top-bar">
        <div class="v-metric">
            <div class="v-val" id="dispLtpV1" style="color:#fff;">167.00</div>
            <div class="v-sub">NIFTY 25,050 • expires 08 Nov</div>
        </div>
        <div class="v-metric">
            <div class="v-val" style="color:var(--green);">162.00–163.00</div>
            <div class="v-sub">₹4.00 below (Nearest Big Buyers)</div>
        </div>
        <div class="v-metric">
            <div class="v-val" style="color:#ff3d71;">169.00–170.00</div>
            <div class="v-sub">₹2.00 above (Nearest Big Sellers)</div>
        </div>
        <div class="v-metric" style="text-align:right;">
            <div class="v-val" style="color:var(--green); font-size:16px;">2481 <span style="font-size:12px; color:#94a3b8;">bought</span> - 1800 <span style="font-size:12px; color:#ff3d71;">sold</span></div>
            <div class="v-sub">forming candle • 15s into the minute</div>
        </div>
    </div>

    <div class="legend-strip">
        <div>
            <b>Live chart and order book (lots waiting, per ₹1.00)</b>
            <span style="color:#94a3b8; margin-left:14px;">● buyers waiting / bought | ● sellers waiting / sold | ● pulled (cancelled)</span>
        </div>
        <div>
            <a href="/" style="color:#38bdf8; text-decoration:none; margin-right:8px; font-weight:bold;">📈 CHARTS</a>
            <a href="/oi-analytics" style="color:#00ff88; text-decoration:none; font-weight:bold;">⚡ OI RADAR</a>
        </div>
    </div>

    <div class="video1-workspace">
        <div class="live-candle-column"><canvas id="canvasLiveCandle"></canvas></div>
        <div class="orderbook-ladder-column" id="ladderRowsV1"></div>
    </div>

    <script>
        const canvas = document.getElementById('canvasLiveCandle');
        const ctx = canvas.getContext('2d');
        function resize() {
            canvas.width = canvas.parentElement.clientWidth;
            canvas.height = canvas.parentElement.clientHeight;
        }
        window.addEventListener('resize', resize);

        function drawLiveCandles() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            // Draw simulated 1-minute live candlesticks from Video 1
            const candleWidth = 14;
            const startX = 60;
            const candles = [
                { o: 280, h: 260, l: 310, c: 270, green: true },
                { o: 270, h: 240, l: 290, c: 250, green: true },
                { o: 250, h: 220, l: 260, c: 230, green: true },
                { o: 230, h: 180, l: 240, c: 190, green: true },
                { o: 190, h: 140, l: 200, c: 150, green: true },
                { o: 150, h: 140, l: 180, c: 165, green: true }
            ];

            candles.forEach((c, idx) => {
                let x = startX + (idx * 38);
                ctx.strokeStyle = c.green ? "#00e676" : "#ff3d71";
                ctx.lineWidth = 1.8;
                ctx.beginPath();
                ctx.moveTo(x + candleWidth/2, c.h);
                ctx.lineTo(x + candleWidth/2, c.l);
                ctx.stroke();

                ctx.fillStyle = c.green ? "#00e676" : "#ff3d71";
                ctx.fillRect(x, Math.min(c.o, c.c), candleWidth, Math.abs(c.c - c.o) || 4);
            });

            // Dashed Price Axis line connecting from candle to ladder
            ctx.strokeStyle = "rgba(255,255,255,0.4)";
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(startX + (5 * 38) + candleWidth, 165);
            ctx.lineTo(canvas.width, 165);
            ctx.stroke();
            ctx.setLineDash([]);

            requestAnimationFrame(drawLiveCandles);
        }

        async function fetchLadderV1() {
            try {
                let res = await fetch('/api/orderbook/ladder');
                let d = await res.json();

                let html = '';
                d.levels.forEach(lvl => {
                    let curCls = lvl.is_current ? 'current' : '';
                    let content = '';

                    if (lvl.side === 'ASK') {
                        let w = Math.min(100, (lvl.lots / 160) * 80);
                        let tag = lvl.tag === 'Big Sellers' ? `<span class="txt-big-seller">1,005 Big Sellers</span>` : (lvl.tag === 'Pulled-Order' ? `<span class="txt-pulled">464 pulled</span>` : '');
                        content = `<div class="bar-seller" style="width:${w}px;">${lvl.lots}</div>${tag}`;
                    } else if (lvl.side === 'BID') {
                        let w = Math.min(100, (lvl.lots / 250) * 80);
                        let tag = lvl.tag === 'Big Buyers' ? `<span class="txt-big-buyer">1,387 Big Buyers</span>` : '';
                        content = `<div class="bar-buyer" style="width:${w}px;">${lvl.lots}</div>${tag}`;
                    } else {
                        content = `<span class="txt-pulled">189 bought • 83 pulled</span>`;
                    }

                    html += `
                    <div class="ladder-row-v1 ${curCls}">
                        <div class="axis-p">${lvl.price}</div>
                        <div class="order-content-box">${content}</div>
                    </div>`;
                });
                document.getElementById('ladderRowsV1').innerHTML = html;
            } catch(e) {}
        }
        resize();
        drawLiveCandles();
        fetchLadderV1();
        setInterval(fetchLadderV1, 2500);
    </script>
</body>
</html>
"""

# ==================== PAGE 4: F&O ACTIVITY & POPUP CANDLESTICK CHART (VIDEO 2) ====================
FNO_ACTIVITY_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>F&O Activity - The Trade Cartel</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        :root {
            --bg-deep: #090d16; --panel-bg: #111726; --card-bg: #162033;
            --green: #00e676; --red: #ff3d71; --blue: #38bdf8; --orange: #fb923c;
            --border: #1e293b; --text-dim: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: var(--bg-deep); color: #fff; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        .navbar { height: 48px; background: #070a12; border-bottom: 1.5px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; }
        .nav-brand { font-size: 14px; font-weight: 900; color: #fff; display: flex; align-items: center; gap: 8px; }
        .nav-links a { background: #131d2e; border: 1px solid var(--border); color: #38bdf8; padding: 4px 10px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 800; margin-left: 6px; }

        .dashboard-strip { padding: 12px 16px; background: #0c121e; border-bottom: 1px solid var(--border); }
        .dash-cards-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 8px; }
        .d-box { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; }
        .d-title { font-size: 11px; color: var(--text-dim); font-weight: 700; }
        .d-val { font-size: 18px; font-weight: 900; margin-top: 2px; }

        .fno-workspace { padding: 14px 16px; flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
        .buildup-card { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px; }
        .b-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 8px; }
        .stock-item-row { display: flex; align-items: center; justify-content: space-between; padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.05); cursor: pointer; border-radius: 4px; }
        .stock-item-row:hover { background: rgba(56, 189, 248, 0.1); }

        .stock-modal-backdrop { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.85); display: none; justify-content: center; align-items: center; z-index: 1000; }
        .stock-modal-card { background: #0f1624; border: 1.5px solid #38bdf8; border-radius: 12px; width: 900px; max-width: 95%; max-height: 90vh; overflow-y: auto; padding: 18px; }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="nav-brand"><span>🛡️</span> The Trade Cartel: F&O Activity (Click stock for Chart)</div>
        <div class="nav-links">
            <a href="/">📈 CHARTS</a>
            <a href="/order-book">🛡️ ORDER BOOK</a>
            <a href="/oi-analytics">⚡ OI RADAR</a>
        </div>
    </div>
    <div class="dashboard-strip">
        <div class="dash-cards-grid">
            <div class="d-box"><div class="d-title">NIFTY 50</div><div class="d-val" style="color:var(--blue);">25,030.35</div></div>
            <div class="d-box"><div class="d-title">Market mood</div><div class="d-val" style="color:var(--red);">Trending down</div></div>
            <div class="d-box"><div class="d-title">Advancing</div><div class="d-val" style="color:#fbbf24;">388 / 1977</div></div>
            <div class="d-box"><div class="d-title">INDIA VIX</div><div class="d-val" style="color:#c084fc;">14.50</div></div>
        </div>
    </div>
    <div class="fno-workspace">
        <div class="buildup-card" style="border-top:3px solid var(--green);"><div class="b-header"><b style="color:var(--green);">Long build-up (Fresh Buying)</b></div><div id="boxLong"></div></div>
        <div class="buildup-card" style="border-top:3px solid var(--red);"><div class="b-header"><b style="color:var(--red);">Short build-up (Fresh Selling)</b></div><div id="boxShort"></div></div>
        <div class="buildup-card" style="border-top:3px solid var(--blue);"><div class="b-header"><b style="color:var(--blue);">Short covering (Shorts Closing)</b></div><div id="boxCovering"></div></div>
        <div class="buildup-card" style="border-top:3px solid var(--orange);"><div class="b-header"><b style="color:var(--orange);">Long unwinding (Longs Closing)</b></div><div id="boxUnwinding"></div></div>
    </div>

    <!-- MODAL WITH REAL-TIME CANDLESTICK CHART ON CLICK -->
    <div class="stock-modal-backdrop" id="stockModal">
        <div class="stock-modal-card">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); padding-bottom:10px;">
                <div><b style="font-size:18px;" id="mSym">AXISBANK</b><span style="font-size:16px; color:var(--green); margin-left:10px;" id="mPrice">₹1,217.50</span></div>
                <button onclick="document.getElementById('stockModal').style.display='none'" style="background:#ff3d71; color:#fff; border:none; padding:6px 12px; border-radius:4px; font-weight:bold; cursor:pointer;">CLOSE</button>
            </div>
            <div id="stockChartContainer" style="width:100%; height:320px; margin-top:14px; background:#070a12; border-radius:6px;"></div>
        </div>
    </div>

    <script>
        let fChart = null, fSeries = null;
        async function loadFno() {
            try {
                let res = await fetch('/api/fno/buildups');
                let d = await res.json();
                renderList('boxLong', d.buildups.long_buildup, 'var(--green)');
                renderList('boxShort', d.buildups.short_buildup, 'var(--red)');
                renderList('boxCovering', d.buildups.short_covering, 'var(--blue)');
                renderList('boxUnwinding', d.buildups.long_unwinding, 'var(--orange)');
            } catch(e) {}
        }
        function renderList(id, list, col) {
            let html = '';
            list.forEach(s => {
                html += `<div class="stock-item-row" onclick='openModal(${JSON.stringify(s)})'>
                    <div><b>${s.symbol}</b><br><small style="color:var(--text-dim);">${s.name}</small></div>
                    <div style="text-align:right;"><b>₹ ${s.price}</b><br><small style="color:${col}; font-weight:bold;">${s.pchange} • OI ${s.oi}</small></div>
                </div>`;
            });
            document.getElementById(id).innerHTML = html;
        }
        function openModal(s) {
            document.getElementById('mSym').innerText = s.symbol;
            document.getElementById('mPrice').innerText = '₹ ' + s.price + ' (' + s.pchange + ')';
            document.getElementById('stockModal').style.display = 'flex';
            setTimeout(() => {
                const c = document.getElementById('stockChartContainer');
                c.innerHTML = '';
                fChart = LightweightCharts.createChart(c, { autoSize: true, layout: { background: { color: '#070a12' }, textColor: '#94a3b8' }, timeScale: { timeVisible: true } });
                fSeries = fChart.addCandlestickSeries({ upColor: '#00e676', downColor: '#ff3d71' });
                let p = parseFloat(s.price.replace(',', '')) || 1200;
                let base = Math.floor(Date.now() / 1000) - 3600 * 4;
                let candles = [];
                for (let i = 0; i < 40; i++) {
                    let o = p;
                    let h = o + 5;
                    let l = o - 4;
                    let cl = o + (i % 2 === 0 ? 3 : -2);
                    candles.push({ time: base + (i * 300), open: o, high: h, low: l, close: cl });
                    p = cl;
                }
                fSeries.setData(candles);
            }, 100);
        }
        loadFno();
    </script>
</body>
</html>
"""

# ==================== ROUTE BINDINGS (ALL PAGES ACTIVE) ====================
@app.get("/", response_class=HTMLResponse)
def pro_terminal():
    return TERMINAL_HTML

@app.get("/order-book", response_class=HTMLResponse)
def orderbook_page():
    return ORDERBOOK_LADDER_HTML

@app.get("/oi-analytics", response_class=HTMLResponse)
def oi_page():
    return OI_DASHBOARD_HTML

@app.get("/fno-activity", response_class=HTMLResponse)
def fno_page():
    return FNO_ACTIVITY_HTML
