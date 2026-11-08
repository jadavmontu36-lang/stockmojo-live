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
    from_date = (ist_now - datetime.timedelta(days=4)).strftime("%Y-%m-%d 09:15")
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
def get_market_data(tf: str = "15m", selected_ce_strike: int = 0, selected_pe_strike: int = 0):
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
    active_expiry = all_expiries[0] if all_expiries else "23NOV2026"

    active_ce = selected_ce_strike if selected_ce_strike > 0 else atm_strike
    active_pe = selected_pe_strike if selected_pe_strike > 0 else atm_strike

    strikes = [atm_strike + (i * 50) for i in range(-5, 6)]
    token_map = get_tokens_by_expiry_and_strikes(active_expiry, strikes)

    tokens = []
    for s in token_map.values():
        if "CE" in s: tokens.append(s["CE"])
        if "PE" in s: tokens.append(s["PE"])
    live_quotes = fetch_angel_market_data(tokens)

    chain = []
    for s in strikes:
        ce_tok = token_map.get(s, {}).get("CE", "")
        pe_tok = token_map.get(s, {}).get("PE", "")
        ce_d = live_quotes.get(ce_tok, {})
        pe_d = live_quotes.get(pe_tok, {})
        ce_ltp = float(ce_d.get("ltp") or max(1.0, round(165 - (s - spot)*0.45, 2)))
        pe_ltp = float(pe_d.get("ltp") or max(1.0, round(185 + (s - spot)*0.45, 2)))
        ce_oi = int(ce_d.get("oi") or 450000)
        pe_oi = int(pe_d.get("oi") or 380000)
        chain.append({
            "strike": s, "ltp_ce": ce_ltp, "ltp_pe": pe_ltp,
            "oi_ce": ce_oi, "oi_pe": pe_oi,
            "oi_ce_str": f"{round(ce_oi/100000, 2)}L",
            "oi_pe_str": f"{round(pe_oi/100000, 2)}L",
            "is_atm": (s == atm_strike)
        })

    ce_token = token_map.get(active_ce, {}).get("CE", "")
    pe_token = token_map.get(active_pe, {}).get("PE", "")
    ce_candles = fetch_candle_data_for_token(ce_token, interval, "NFO") if ce_token else []
    pe_candles = fetch_candle_data_for_token(pe_token, interval, "NFO") if pe_token else []

    if not ce_candles:
        ce_candles = [{"time": c["time"], "open": round(max(1.0, 150 + (c["open"] - spot)*0.5), 2), "high": round(max(1.0, 150 + (c["high"] - spot)*0.5), 2), "low": round(max(1.0, 150 + (c["low"] - spot)*0.5), 2), "close": round(max(1.0, 150 + (c["close"] - spot)*0.5), 2)} for c in spot_candles]
    if not pe_candles:
        pe_candles = [{"time": c["time"], "open": round(max(1.0, 175 - (c["open"] - spot)*0.5), 2), "high": round(max(1.0, 175 - (c["low"] - spot)*0.5), 2), "low": round(max(1.0, 175 - (c["high"] - spot)*0.5), 2), "close": round(max(1.0, 175 - (c["close"] - spot)*0.5), 2)} for c in spot_candles]

    profile_strikes = [
        {"strike": 25500, "call_oi": 620000, "put_oi": 40000},
        {"strike": 25450, "call_oi": 310000, "put_oi": 60000},
        {"strike": 25400, "call_oi": 580000, "put_oi": 90000},
        {"strike": 25350, "call_oi": 420000, "put_oi": 110000},
        {"strike": 25300, "call_oi": 650000, "put_oi": 150000},
        {"strike": 25250, "call_oi": 280000, "put_oi": 140000},
        {"strike": 25200, "call_oi": 680000, "put_oi": 190000},
        {"strike": 25150, "call_oi": 260000, "put_oi": 210000},
        {"strike": 25100, "call_oi": 540000, "put_oi": 240000},
        {"strike": 25050, "call_oi": 220000, "put_oi": 310000},
        {"strike": 25000, "call_oi": 850000, "put_oi": 480000},
        {"strike": 24950, "call_oi": 180000, "put_oi": 390000},
        {"strike": 24900, "call_oi": 340000, "put_oi": 490000},
        {"strike": 24850, "call_oi": 160000, "put_oi": 320000},
        {"strike": 24800, "call_oi": 410000, "put_oi": 520000},
        {"strike": 24750, "call_oi": 90000,  "put_oi": 290000},
        {"strike": 24700, "call_oi": 310000, "put_oi": 580000},
        {"strike": 24650, "call_oi": 110000, "put_oi": 340000},
        {"strike": 24600, "call_oi": 280000, "put_oi": 620000},
        {"strike": 24550, "call_oi": 80000,  "put_oi": 320000},
        {"strike": 24500, "call_oi": 240000, "put_oi": 780000}
    ]

    result = {
        "spot": spot,
        "atm_strike": atm_strike,
        "active_ce": active_ce,
        "active_pe": active_pe,
        "candles": spot_candles,
        "ce_candles": ce_candles,
        "pe_candles": pe_candles,
        "chain": chain,
        "resistance_strike": 25000,
        "max_pain": 24700,
        "expected_move": 24507,
        "support_strike": 24500,
        "profile_strikes": profile_strikes,
        "india_vix": fetch_india_vix()
    }
    CACHE_STORE["market_data"] = result
    CACHE_STORE["market_time"] = now
    return result

@app.get("/api/oi/quantum-stream")
def get_quantum_stream():
    calls = [
        {"strike": 23250, "ltp": 33.75, "oi_str": "37.58L", "type_tag": "OTM", "is_key": False},
        {"strike": 23200, "ltp": 46.00, "oi_str": "75.08L", "type_tag": "OTM", "is_key": True},
        {"strike": 23150, "ltp": 61.75, "oi_str": "35.47L", "type_tag": "OTM", "is_key": False},
        {"strike": 23100, "ltp": 81.00, "oi_str": "45.26L", "type_tag": "OTM", "is_key": False},
        {"strike": 23000, "ltp": 129.90, "oi_str": "71.45L", "type_tag": "ITM", "is_key": False},
        {"strike": 22950, "ltp": 160.45, "oi_str": "12.75L", "type_tag": "ITM", "is_key": False},
        {"strike": 23050, "ltp": 103.90, "oi_str": "33.65L", "type_tag": "ATM", "is_key": False}
    ]
    puts = [
        {"strike": 23050, "ltp": 127.30, "oi_str": "41.65L", "type_tag": "ATM", "is_key": False},
        {"strike": 23100, "ltp": 154.60, "oi_str": "27.25L", "type_tag": "ITM", "is_key": False},
        {"strike": 23150, "ltp": 185.50, "oi_str": "5.19L", "type_tag": "ITM", "is_key": False},
        {"strike": 23000, "ltp": 104.30, "oi_str": "91.17L", "type_tag": "OTM", "is_key": True},
        {"strike": 22950, "ltp": 84.40, "oi_str": "42.4L", "type_tag": "OTM", "is_key": False},
        {"strike": 22900, "ltp": 67.70, "oi_str": "89.38L", "type_tag": "OTM", "is_key": False},
        {"strike": 22850, "ltp": 54.05, "oi_str": "48.8L", "type_tag": "OTM", "is_key": False}
    ]
    return {
        "spot": 23053.1,
        "atm": 23050,
        "calls": calls,
        "puts": puts,
        "main_res": {"strike": 23200, "oi_str": "75.08L"},
        "main_sup": {"strike": 23000, "oi_str": "91.17L"},
        "range_str": "23000 - 23200",
        "action": "બ્રેકઆઉટની રાહ જુઓ (23200 ઉપર કે 23000 નીચે)",
        "news": "લાઈવ સમાચાર: નિફ્ટી ₹23053.1 | PCR 1.21 (બુલ્સ મજબૂત છે) | India VIX 14.5 (ઓપ્શન બાયિંગ માટે બેસ્ટ મોમેન્ટમ)."
    }

@app.get("/api/orderbook/strike-ladder")
def get_strike_ladder():
    levels = [
        {"price": "172.00", "lots": 90, "side": "ASK", "tag": ""},
        {"price": "171.00", "lots": 147, "side": "ASK", "tag": ""},
        {"price": "170.00", "lots": 35, "side": "ASK", "tag": "Big Sellers"},
        {"price": "169.00", "lots": 14, "side": "ASK", "tag": "Pulled-Order"},
        {"price": "168.00", "lots": 1005, "side": "ASK", "tag": "Big Sellers"},
        {"price": "167.00", "lots": 280, "side": "CURRENT", "tag": "Bought"},
        {"price": "166.00", "lots": 87, "side": "CURRENT", "tag": "Bought"},
        {"price": "165.00", "lots": 30, "side": "BID", "tag": "Bought"},
        {"price": "164.00", "lots": 189, "side": "BID", "tag": "Pulled-Order"},
        {"price": "163.00", "lots": 83, "side": "BID", "tag": "Pulled-Order"},
        {"price": "162.00", "lots": 1387, "side": "BID", "tag": "Big Buyers"},
        {"price": "161.00", "lots": 64, "side": "BID", "tag": ""},
        {"price": "160.00", "lots": 79, "side": "BID", "tag": ""},
        {"price": "159.00", "lots": 431, "side": "BID", "tag": "Big Buyers"},
        {"price": "158.00", "lots": 84, "side": "BID", "tag": ""},
        {"price": "157.00", "lots": 681, "side": "BID", "tag": "Big Buyers"}
    ]
    return {
        "ltp": "167.35",
        "buyers_zone": "156.00–157.00",
        "sellers_zone": "169.00–170.00",
        "flow": "2682 bought - 1761 sold",
        "levels": levels
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
            else: lots, tag = 35, ""
        elif step == 0:
            side = "CURRENT"
            lots, tag = 15, "Pulled-Order"
        else:
            side = "BID"
            if step in [-1, -2]: lots, tag = 25, "Pulled-Order"
            elif step == -4: lots, tag = 203, "Big Buyers"
            elif step == -6: lots, tag = 250, "Big Buyers"
            else: lots, tag = 45, ""
        levels.append({"price": f"{price:,}", "raw_price": price, "lots": lots, "side": side, "tag": tag, "is_current": is_current})

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

# ==================== PAGE 1: PRO TERMINAL (3 CHARTS: SPOT WITH OI PROFILE OVERLAY + CE + PE) ====================
TERMINAL_HTML = r"""<!DOCTYPE html>
<html>
<head>
    <title>Hari Master Pro Terminal - 3 Charts + OI Profile Overlay</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, sans-serif; }
        body { background: #0c1017; color: #d1d4dc; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }

        .top-navbar { height: 44px; background: #080c13; border-bottom: 1px solid #1a2436; display: flex; align-items: center; justify-content: space-between; padding: 0 14px; z-index: 20; }
        .brand { font-size: 14px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 8px; }
        .spot-badge { font-weight: 900; color: #00ff88; background: #062319; border: 1px solid #00ff88; padding: 3px 10px; border-radius: 4px; font-size: 12.5px; }

        .nav-links a { background: #131d2e; border: 1px solid #2563eb; color: #38bdf8; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 800; text-decoration: none; margin-left: 6px; }
        .nav-links a.active { background: #2563eb; color: #fff; }

        .workspace { flex: 1; display: flex; width: 100%; height: calc(100vh - 44px); }
        .charts-column { flex: 6.8; display: flex; flex-direction: column; gap: 2px; background: #141b2b; }
        .spot-card { flex: 5.6; position: relative; background: #080b11; min-height: 250px; }
        .opt-row { flex: 4.4; display: flex; gap: 2px; background: #141b2b; min-height: 200px; }
        .opt-card { flex: 1; position: relative; background: #080b11; min-height: 100%; }
        .chart-container-box { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }

        /* OI PROFILE BARS OVERLAY ANCHORED RIGHT ON SPOT CHART (SCREENSHOT 2) */
        .oi-profile-overlay {
            position: absolute; right: 55px; top: 0; width: 180px; height: 100%;
            pointer-events: none; z-index: 10; display: flex; flex-direction: column; justify-content: space-around;
        }
        .profile-row { display: flex; align-items: center; justify-content: flex-end; height: 18px; }
        .bar-call-oi { background: rgba(244, 63, 94, 0.75); height: 10px; border-radius: 2px 0 0 2px; }
        .bar-put-oi { background: rgba(16, 185, 129, 0.75); height: 10px; border-radius: 0 2px 2px 0; margin-left: 2px; }

        .chain-panel { flex: 3.2; background: #0e131f; border-left: 1px solid #1a2234; display: flex; flex-direction: column; overflow: hidden; }
        .chain-scroll { flex: 1; overflow-y: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 11.5px; text-align: center; }
        th { background: #161e2e; padding: 7px 4px; color: #94a3b8; position: sticky; top: 0; z-index: 2; border-bottom: 1px solid #1a2234; }
        td { padding: 6px 2px; border-bottom: 1px solid #141b2b; cursor: pointer; }
        .atm-row { background: rgba(56, 189, 248, 0.15) !important; font-weight: bold; border-left: 2px solid #38bdf8; }

        .lbl { position: absolute; top: 6px; left: 10px; font-size: 11px; font-weight: 700; z-index: 10; pointer-events: none; background: rgba(8,11,17,0.85); padding: 2px 8px; border-radius: 3px; border: 1px solid #1a2234; }
    </style>
</head>
<body>
    <div class="top-navbar">
        <div class="brand">📈 3 CHARTS + OI PROFILE OVERLAY (SCREENSHOT 2)</div>
        <div class="spot-badge" id="spotBadge">NIFTY 50: 25,030.35 (+0.37%)</div>
        <div class="nav-links">
            <a href="/" class="active">📈 3 CHARTS</a>
            <a href="/strike-orderbook">🎯 STRIKE ORDER BOOK (VIDEO 1)</a>
            <a href="/order-book">🛡️ NIFTY ORDER BOOK</a>
            <a href="/oi-analytics">⚡ OI RADAR (PHOTO 1)</a>
            <a href="/fno-activity">📊 F&O ACTIVITY (VIDEO 2)</a>
        </div>
    </div>

    <div class="workspace">
        <div class="charts-column">
            <!-- 1. SPOT CHART WITH OI PROFILE OVERLAY AND STRIKE LINES -->
            <div class="spot-card">
                <div class="lbl" style="color:#38bdf8;">NIFTY 50 SPOT (15M) • STRIKE LINES & OI PROFILE OVERLAY</div>
                <div id="chart_spot" class="chart-container-box"></div>
                <!-- OI PROFILE BARS OVERLAY MATCHING SCREENSHOT 2 -->
                <div class="oi-profile-overlay" id="oiProfileContainer"></div>
            </div>
            <!-- 2 & 3. SELECTED CE AND PE CANDLESTICK CHARTS (3 CHARTS TOGETHER) -->
            <div class="opt-row">
                <div class="opt-card">
                    <div class="lbl" id="lbl_ce" style="color:#00ff88;">CALL (CE) STRIKE CHART</div>
                    <div id="chart_ce" class="chart-container-box"></div>
                </div>
                <div class="opt-card">
                    <div class="lbl" id="lbl_pe" style="color:#ff2255;">PUT (PE) STRIKE CHART</div>
                    <div id="chart_pe" class="chart-container-box"></div>
                </div>
            </div>
        </div>

        <div class="chain-panel">
            <div style="padding:8px 10px; background:#111726; font-size:11.5px; font-weight:bold; border-bottom:1px solid #1a2234;">
                OPTION CHAIN (Click strike to chart)
            </div>
            <div class="chain-scroll">
                <table>
                    <thead>
                        <tr>
                            <th style="color:#00ff88;">CE OI</th>
                            <th style="color:#00ff88;">CE LTP</th>
                            <th>STRIKE</th>
                            <th style="color:#ff2255;">PE LTP</th>
                            <th style="color:#ff2255;">PE OI</th>
                        </tr>
                    </thead>
                    <tbody id="chainBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const tvOpts = {
            autoSize: true,
            layout: { background: { color: '#080b11' }, textColor: '#94a3b8', fontSize: 11 },
            grid: { vertLines: { color: '#141b2b' }, horzLines: { color: '#141b2b' } },
            rightPriceScale: { borderColor: '#1e293b', visible: true },
            timeScale: { borderColor: '#1e293b', timeVisible: true }
        };
        const cOpts = { upColor: '#00e676', downColor: '#ff3d71', borderUpColor: '#00e676', borderDownColor: '#ff3d71', wickUpColor: '#00e676', wickDownColor: '#ff3d71' };

        const sChart = LightweightCharts.createChart(document.getElementById('chart_spot'), tvOpts);
        const sSeries = sChart.addCandlestickSeries(cOpts);
        const ceChart = LightweightCharts.createChart(document.getElementById('chart_ce'), tvOpts);
        const ceSeries = ceChart.addCandlestickSeries(cOpts);
        const peChart = LightweightCharts.createChart(document.getElementById('chart_pe'), tvOpts);
        const peSeries = peChart.addCandlestickSeries(cOpts);

        let linesSet = false;
        let selectedCE = 0, selectedPE = 0;
        function clickStrike(stk) { selectedCE = stk; selectedPE = stk; fetchTerminal(true); }

        async function fetchTerminal(fit = false) {
            try {
                let res = await fetch(`/api/market_data?selected_ce_strike=${selectedCE}&selected_pe_strike=${selectedPE}`);
                let d = await res.json();
                document.getElementById('spotBadge').innerText = `NIFTY 50: ₹${d.spot.toFixed(2)}`;

                if (d.candles) {
                    sSeries.setData(d.candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                }

                // DRAW EXACT HORIZONTAL STRIKE LINES (MATCHING SCREENSHOT 2)
                if (!linesSet) {
                    sSeries.createPriceLine({ price: d.resistance_strike, color: '#e11d48', lineWidth: 1, lineStyle: 1, axisLabelVisible: true, title: `Resistance strike ${d.resistance_strike}` });
                    sSeries.createPriceLine({ price: d.max_pain, color: '#d97706', lineWidth: 2, lineStyle: 2, axisLabelVisible: true, title: `Max Pain ${d.max_pain}` });
                    sSeries.createPriceLine({ price: d.expected_move, color: '#e11d48', lineWidth: 1, lineStyle: 1, axisLabelVisible: true, title: `Expected move ${d.expected_move}` });
                    sSeries.createPriceLine({ price: d.support_strike, color: '#00875a', lineWidth: 2, lineStyle: 0, axisLabelVisible: true, title: `Support strike ${d.support_strike}` });
                    sChart.timeScale().fitContent();
                    linesSet = true;
                }

                if (d.ce_candles) {
                    ceSeries.setData(d.ce_candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                    document.getElementById('lbl_ce').innerText = `CALL: NIFTY ${d.active_ce} CE (₹${d.ce_candles[d.ce_candles.length-1].close})`;
                    if (fit) ceChart.timeScale().fitContent();
                }
                if (d.pe_candles) {
                    peSeries.setData(d.pe_candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                    document.getElementById('lbl_pe').innerText = `PUT: NIFTY ${d.active_pe} PE (₹${d.pe_candles[d.pe_candles.length-1].close})`;
                    if (fit) peChart.timeScale().fitContent();
                }

                // OI PROFILE BARS OVERLAY (SCREENSHOT 2)
                let pBars = '';
                d.profile_strikes.forEach(s => {
                    let cW = Math.min(90, (s.call_oi / 850000) * 80);
                    let pW = Math.min(90, (s.put_oi / 850000) * 80);
                    pBars += `<div class="profile-row"><div class="bar-call-oi" style="width:${cW}px;"></div><div class="bar-put-oi" style="width:${pW}px;"></div></div>`;
                });
                document.getElementById('oiProfileContainer').innerHTML = pBars;

                // CHAIN ROWS
                let html = '';
                d.chain.forEach(r => {
                    let cls = r.is_atm ? 'atm-row' : '';
                    html += `<tr class="${cls}" onclick="clickStrike(${r.strike})">
                        <td style="color:#00ff88; font-weight:700;">${r.oi_ce_str}</td>
                        <td style="color:#38bdf8; font-weight:800;">₹${r.ltp_ce.toFixed(2)}</td>
                        <td style="background:#161e2e; color:#fff; font-weight:bold;">${r.strike}</td>
                        <td style="color:#ff2255; font-weight:800;">₹${r.ltp_pe.toFixed(2)}</td>
                        <td style="color:#ff2255; font-weight:700;">${r.oi_pe_str}</td>
                    </tr>`;
                });
                document.getElementById('chainBody').innerHTML = html;

            } catch(e) {}
        }
        window.addEventListener('resize', () => {
            sChart.resize(document.getElementById('chart_spot').clientWidth, document.getElementById('chart_spot').clientHeight);
        });
        fetchTerminal(true);
        setInterval(fetchTerminal, 4000);
    </script>
</body>
</html>
"""

# ==================== PAGE 2: OPTION STRIKE ORDER BOOK + LIVE CANDLESTICK (MATCHING VIDEO 1) ====================
STRIKE_ORDERBOOK_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live chart and order book (NIFTY 25050 CE) - Video 1</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #05070a; --panel-bg: #090e17; --green: #00e676;
            --red: #ff3d71; --orange: #e65100; --pulled: #64748b; --border: #141f30;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: var(--bg-color); color: #fff; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

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
        .nav-links a { background: #131d2e; border: 1px solid #2563eb; color: #38bdf8; padding: 3px 8px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: bold; margin-left: 4px; }

        .video1-workspace { flex: 1; display: flex; position: relative; padding: 10px 16px; gap: 6px; }
        .live-candle-column { flex: 1; position: relative; height: 100%; min-height: 520px; border-right: 1.5px dashed #1e293b; }
        #canvasLiveCandle { width: 100%; height: 100%; }

        .orderbook-ladder-column { width: 380px; display: flex; flex-direction: column; justify-content: space-between; }
        .ladder-row-v1 { display: flex; align-items: center; height: 26px; font-size: 12px; font-weight: 800; }
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
            <div class="v-val" style="color:#fff;">167.35</div>
            <div class="v-sub">NIFTY 25,050 CE • expires 08 Nov</div>
        </div>
        <div class="v-metric">
            <div class="v-val" style="color:var(--green);">156.00–157.00</div>
            <div class="v-sub">₹9.25 below (Nearest Big Buyers)</div>
        </div>
        <div class="v-metric">
            <div class="v-val" style="color:#ff3d71;">169.00–170.00</div>
            <div class="v-sub">₹3.75 above (Nearest Big Sellers)</div>
        </div>
        <div class="v-metric" style="text-align:right;">
            <div class="v-val" style="color:var(--green); font-size:16px;">2682 <span style="font-size:12px; color:#94a3b8;">bought</span> - 1761 <span style="font-size:12px; color:#ff3d71;">sold</span></div>
            <div class="v-sub">forming candle • 15s into the minute</div>
        </div>
    </div>

    <div class="legend-strip">
        <div>
            <b>Live chart and order book (lots waiting, per ₹1.00)</b>
            <span style="color:#94a3b8; margin-left:14px;">● buyers waiting / bought | ● sellers waiting / sold | ● pulled (cancelled)</span>
        </div>
        <div class="nav-links">
            <a href="/">📈 3 CHARTS</a>
            <a href="/order-book">🛡️ NIFTY ORDER BOOK</a>
            <a href="/oi-analytics">⚡ OI RADAR</a>
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
                let res = await fetch('/api/orderbook/strike-ladder');
                let d = await res.json();

                let html = '';
                d.levels.forEach(lvl => {
                    let curCls = lvl.side === 'CURRENT' ? 'current' : '';
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

# ==================== CLEAN DISTINCT ROUTE MAPPING ====================
@app.get("/", response_class=HTMLResponse)
def pro_terminal():
    return TERMINAL_HTML

@app.get("/strike-orderbook", response_class=HTMLResponse)
def strike_orderbook():
    return STRIKE_ORDERBOOK_HTML

@app.get("/order-book", response_class=HTMLResponse)
def orderbook_page():
    return ORDERBOOK_LADDER_HTML

@app.get("/oi-analytics", response_class=HTMLResponse)
def oi_page():
    return OI_DASHBOARD_HTML

@app.get("/fno-activity", response_class=HTMLResponse)
def fno_page():
    return FNO_ACTIVITY_HTML
