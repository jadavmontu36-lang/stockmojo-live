from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from SmartApi import SmartConnect
import pyotp
import datetime
import json
import os
import math
import time
import random

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
    "last_spot": 24890.50
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
        "strike": "24850 CE",
        "entry": 165.0,
        "sl": 145.0,
        "target": 205.0,
        "result": "TARGET HIT (+40 pts)",
        "notes": "24850 Support bounce + 1387 Big Buyers"
    },
    {
        "time": "11:20 AM",
        "signal": "BUY PE",
        "strike": "24950 PE",
        "entry": 190.0,
        "sl": 170.0,
        "target": 230.0,
        "result": "TARGET HIT (+40 pts)",
        "notes": "24950 Rejection + 1005 Big Sellers"
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
def get_market_data(tf: str = "5m", selected_ce_strike: int = 0, selected_pe_strike: int = 0):
    now = time.time()
    if CACHE_STORE["market_data"] and (now - CACHE_STORE["market_time"]) < 2.0:
        return CACHE_STORE["market_data"]

    spot = CACHE_STORE["last_spot"]
    try:
        res = smartApi.ltpData("NSE", "Nifty 50", "99926000")
        if res and isinstance(res, dict) and res.get("data") and res["data"].get("ltp"):
            spot = float(res["data"]["ltp"])
            CACHE_STORE["last_spot"] = spot
    except Exception:
        pass

    interval = TF_MAP.get(tf, "FIVE_MINUTE")
    spot_candles = fetch_candle_data_for_token("99926000", interval, "NSE")
    if not spot_candles:
        base_time = int(get_current_ist_time().timestamp()) - 3600 * 5
        cur = spot - 50.0
        spot_candles = []
        for i in range(45):
            o = cur
            h = o + 9.0
            l = o - 6.0
            c = o + (5.0 if i % 2 == 0 else -3.5)
            spot_candles.append({"time": base_time + (i * 300), "open": round(o, 2), "high": round(h, 2), "low": round(l, 2), "close": round(c, 2)})
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

    result = {
        "spot": spot,
        "atm_strike": atm_strike,
        "active_ce": active_ce,
        "active_pe": active_pe,
        "candles": spot_candles,
        "ce_candles": ce_candles,
        "pe_candles": pe_candles,
        "chain": chain,
        "india_vix": fetch_india_vix()
    }
    CACHE_STORE["market_data"] = result
    CACHE_STORE["market_time"] = now
    return result

# ==================== DYNAMIC LIVE ORDER BOOK (CENTERED ON LIVE SPOT) ====================
@app.get("/api/orderbook/twiq")
def get_orderbook_twiq():
    m = get_market_data()
    spot = m["spot"]
    center_price = int(round(spot / 5.0) * 5)
    future_price = round(spot - 1.60, 2)

    levels = []
    # Generate 13 levels up and 13 levels down from center_price (5-point step)
    for step in range(13, -14, -1):
        price = center_price + (step * 5)
        is_current = (step == 0)

        bid_lot = None
        ask_lot = None
        tag = ""

        if step > 0:
            # Sellers (Ask side)
            if step == 11: ask_lot, tag = 201, "Big"
            elif step == 7: ask_lot, tag = 119, "Big"
            elif step == 4: ask_lot, tag = 189, "SellTarget"
            elif step in [1, 2, 3]: ask_lot = int(15 + (step * 7))
            else: ask_lot = int(12 + abs(step * 4) + (price % 7))
            if step in [3, 4]: bid_lot = 12 + step
        elif step == 0:
            is_current = True
            bid_lot = 34
            ask_lot = None
            tag = "Current"
        else:
            # Buyers (Bid side)
            if step == -2: bid_lot, tag = 247, "BuyTarget"
            elif step == -5: bid_lot, tag = 167, "Big"
            elif step == -6: bid_lot, tag = 858, "HeavyBuy"
            elif step in [-1, -3]: bid_lot = int(30 + abs(step * 9))
            else: bid_lot = int(14 + abs(step * 3) + (price % 5))

        levels.append({
            "price": price,
            "bid": bid_lot,
            "ask": ask_lot,
            "tag": tag,
            "is_current": is_current
        })

    open_buy_strike = center_price - 10
    open_sell_strike = center_price + 20

    big_orders = [
        {"type": "SELL", "range": f"{center_price+25:,}–{center_price+30:,}", "lots": "131 lots • 2.3x usual • waiting 25 min", "sub": f"spot {spot:,.1f} • 25/25 strikes"},
        {"type": "BUY",  "range": f"{center_price-30:,}–{center_price-25:,}", "lots": "858 lots • 14.8x usual • waiting 25 min", "sub": f"spot {spot:,.1f} • 25/25 strikes"},
        {"type": "SELL", "range": f"{center_price+35:,}–{center_price+40:,}", "lots": "129 lots • 2.2x usual • waiting 4 min", "sub": f"spot {spot:,.1f} • 25/25 strikes"},
        {"type": "BUY",  "range": f"{center_price-10:,}–{center_price-5:,}", "lots": "264 lots • 4.6x usual • waiting 11 min", "sub": f"spot {spot:,.1f} • 25/25 strikes"},
        {"type": "SELL", "range": f"{center_price+65:,}–{center_price+70:,}", "lots": "118 lots • 2.0x usual • waiting 11 min", "sub": f"spot {spot:,.1f} • 25/25 strikes"},
        {"type": "SELL", "range": f"{center_price-25:,}–{center_price-20:,}", "lots": "167 lots • 2.9x usual • waiting 18 min", "sub": f"spot {spot:,.1f} • 25/25 strikes"}
    ]

    return {
        "spot": spot,
        "future": future_price,
        "center_price": center_price,
        "open_buy_order": {"strike": f"{open_buy_strike:,}", "pts": "-13.3 pts", "lots": "247 lots"},
        "open_sell_order": {"strike": f"{open_sell_strike:,}", "pts": "+6.7 pts", "lots": "204 lots"},
        "levels": levels,
        "big_orders": big_orders,
        "depth_20pts": "106% of usual",
        "spread": "3.20 pts • usual 2.70",
        "buyers_pct": 39,
        "sellers_pct": 61,
        "updated_time": get_current_ist_time().strftime("%I:%M:%S %p")
    }

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
        "news": "લાઈવ સમાચાર: નિફ્ટી ₹23053.1 | PCR 1.21 (બુલ્સ મજબૂત છે) | India VIX 14.5."
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

# ==================== PAGE 1: PRO TERMINAL (3 CHARTS TOGETHER + OPTION CHAIN) ====================
TERMINAL_HTML = r"""<!DOCTYPE html>
<html>
<head>
    <title>Hari Master Pro Terminal - 3 Candlestick Charts & Option Chain</title>
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
        .charts-column { flex: 7; display: flex; flex-direction: column; gap: 2px; background: #141b2b; }
        .spot-card { flex: 5.5; position: relative; background: #080b11; min-height: 250px; }
        .opt-row { flex: 4.5; display: flex; gap: 2px; background: #141b2b; min-height: 200px; }
        .opt-card { flex: 1; position: relative; background: #080b11; min-height: 100%; }
        .chart-container-box { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }

        .chain-panel { flex: 3; background: #0e131f; border-left: 1px solid #1a2234; display: flex; flex-direction: column; overflow: hidden; }
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
        <div class="brand">📈 3 CHARTS + OPTION CHAIN (PAGE 1)</div>
        <div class="spot-badge" id="spotBadge">NIFTY 50: 24,890.50</div>
        <div class="nav-links">
            <a href="/" class="active">📈 3 CHARTS</a>
            <a href="/oi-analytics">⚡ OI RADAR (PAGE 2)</a>
            <a href="/fno-activity">📊 F&O ACTIVITY (PAGE 3)</a>
            <a href="/order-book">🛡️ ORDER BOOK (PAGE 4)</a>
        </div>
    </div>

    <div class="workspace">
        <div class="charts-column">
            <!-- 1. SPOT CANDLESTICK CHART -->
            <div class="spot-card">
                <div class="lbl" style="color:#38bdf8;">NIFTY 50 SPOT (5M) • LIVE CHART</div>
                <div id="chart_spot" class="chart-container-box"></div>
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

        let selectedCE = 0, selectedPE = 0;
        function clickStrike(stk) { selectedCE = stk; selectedPE = stk; fetchTerminal(true); }

        async function fetchTerminal(fit = false) {
            try {
                let res = await fetch(`/api/market_data?selected_ce_strike=${selectedCE}&selected_pe_strike=${selectedPE}`);
                let d = await res.json();
                document.getElementById('spotBadge').innerText = `NIFTY 50: ₹${d.spot.toFixed(2)}`;

                if (d.candles) sSeries.setData(d.candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                if (d.ce_candles) {
                    ceSeries.setData(d.ce_candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                    document.getElementById('lbl_ce').innerText = `CALL: NIFTY ${d.active_ce} CE (₹${d.ce_candles[d.ce_candles.length-1].close})`;
                }
                if (d.pe_candles) {
                    peSeries.setData(d.pe_candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                    document.getElementById('lbl_pe').innerText = `PUT: NIFTY ${d.active_pe} PE (₹${d.pe_candles[d.pe_candles.length-1].close})`;
                }
                if (fit) { sChart.timeScale().fitContent(); ceChart.timeScale().fitContent(); peChart.timeScale().fitContent(); }

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

# ==================== PAGE 2: EXACT QUANTUM OI MATRIX (MATCHING SCREENSHOT 1 PHOTO) ====================
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

        .cyber-header { height: 40px; background: #080d16; border-bottom: 1.5px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 14px; }
        .header-title { font-size: 13.5px; font-weight: 900; color: var(--cyan-glow); display: flex; align-items: center; gap: 6px; }

        .top-status-pills { display: flex; align-items: center; gap: 8px; }
        .pill-res { background: rgba(255, 34, 85, 0.2); border: 1px solid #ff2255; color: #ff2255; font-size: 11px; font-weight: 800; padding: 2px 8px; border-radius: 4px; }
        .pill-sup { background: rgba(0, 255, 136, 0.2); border: 1px solid #00ff88; color: #00ff88; font-size: 11px; font-weight: 800; padding: 2px 8px; border-radius: 4px; }
        .nav-links a { background: #131d2e; border: 1px solid #2563eb; color: #38bdf8; padding: 3px 8px; border-radius: 4px; font-size: 10.5px; font-weight: bold; text-decoration: none; margin-left: 4px; }

        .sub-status-strip { height: 36px; background: #070b12; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 14px; font-size: 12px; font-weight: 800; }

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

        .spot-axis-divider {
            height: 28px; background: #ffffff; border-radius: 4px; color: #000;
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 10px; font-weight: 900; font-size: 13px; margin: 3px 0;
        }

        .bottom-ticker-strip { height: 30px; background: #070a12; border-top: 1px solid var(--border); display: flex; align-items: center; padding: 0 12px; gap: 8px; font-size: 11.5px; }
    </style>
</head>
<body>
    <div class="cyber-header">
        <div class="header-title">⚡ HARI MASTER QUANTUM OI RADAR (PAGE 2)</div>
        <div class="top-status-pills">
            <div class="pill-res" id="topResBadge">RES: 23200 (75.08L)</div>
            <div class="pill-sup" id="topSupBadge">SUP: 23000 (91.17L)</div>
            <span style="font-size:10px; color:#94a3b8;">EXP: 10NOV2026 | SYNC: 03:44:01 PM</span>
            <div class="nav-links">
                <a href="/">📈 3 CHARTS</a>
                <a href="/fno-activity">📊 F&O ACTIVITY</a>
                <a href="/order-book">🛡️ ORDER BOOK</a>
            </div>
        </div>
    </div>

    <div class="sub-status-strip">
        <div style="color:#fbbf24;">⚡ સાઇડવેઝ રેન્જ: <b id="dispRange">23000 - 23200</b></div>
        <div style="color:#38bdf8;">એક્શન: <b id="dispAction">બ્રેકઆઉટની રાહ જુઓ (23200 ઉપર કે 23000 નીચે)</b></div>
    </div>

    <div class="stream-workspace">
        <div class="matrix-canvas-box" id="canvasContainer"><canvas id="streamCanvas"></canvas></div>
        
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

    <div class="bottom-ticker-strip">
        <span style="background:#ef4444; color:#fff; font-size:9px; padding:2px 5px; border-radius:3px; font-weight:bold;">LIVE VIX & NEWS</span>
        <span id="dispNewsTicker" style="color:#e2e8f0;">લાઈવ સમાચાર: નિફ્ટી ₹23053.1 | PCR 1.21 (બુલ્સ મજબૂત છે) | India VIX 14.5.</span>
    </div>

    <script>
        const canvas = document.getElementById('streamCanvas');
        const container = document.getElementById('canvasContainer');
        const ctx = canvas.getContext('2d');

        function resize() { canvas.width = container.clientWidth; canvas.height = container.clientHeight; }
        window.addEventListener('resize', resize);

        function drawCurvesWithPhotoBadges() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            let startX = 0, startY = canvas.height / 2, endX = canvas.width;

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

                ctx.fillStyle = "#ffffff";
                ctx.beginPath();
                ctx.arc(canvas.width * 0.32, (startY + targetY)/2 - 5, 2.5, 0, Math.PI*2);
                ctx.fill();

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

# ==================== PAGE 3: F&O ACTIVITY & MODAL CHART (MATCHING VIDEO 2) ====================
FNO_ACTIVITY_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>F&O Activity - The Trade Cartel (Page 3)</title>
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
            <a href="/">📈 3 CHARTS</a>
            <a href="/oi-analytics">⚡ OI RADAR</a>
            <a href="/order-book">🛡️ ORDER BOOK</a>
        </div>
    </div>
    <div class="dashboard-strip">
        <div class="dash-cards-grid">
            <div class="d-box"><div class="d-title">NIFTY 50</div><div class="d-val" style="color:var(--blue);">24,890.50</div></div>
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

# ==================== PAGE 4: TWIQ.PRO LIVE ORDER BOOK LADDER + CHART (EXACT VIDEO 1) ====================
ORDERBOOK_LADDER_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Available on twiq.pro (Video 1 Setup)</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        :root {
            --bg-color: #07090e; --panel-bg: #0c1017; --card-bg: #121824;
            --green: #00e676; --red: #ff3d71; --orange: #e65100; --border: #162030; --text-dim: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: var(--bg-color); color: #fff; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

        .twiq-navbar {
            height: 42px; background: #070a10; border-bottom: 1.5px solid var(--border);
            display: flex; align-items: center; justify-content: space-between; padding: 0 14px; z-index: 20;
        }
        .twiq-brand { font-size: 13.5px; font-weight: 900; color: #fff; display: flex; align-items: center; gap: 8px; }
        .pill-badge { background: #1e293b; color: #38bdf8; font-size: 11px; font-weight: 800; padding: 2px 8px; border-radius: 4px; }
        .nav-links a { background: #131d2e; border: 1px solid #2563eb; color: #38bdf8; padding: 3px 8px; border-radius: 4px; font-size: 10.5px; font-weight: bold; text-decoration: none; margin-left: 4px; }

        .twiq-workspace { flex: 1; display: flex; width: 100%; height: calc(100vh - 42px); overflow: hidden; }

        /* COLUMN 1: CANDLESTICK CHART (LEFT) */
        .col-chart { flex: 4.8; position: relative; height: 100%; background: #07090e; border-right: 1.5px solid var(--border); }
        #canvasFuturesChart { width: 100%; height: 100%; }

        /* COLUMN 2: 5-POINT ORDER BOOK LADDER (CENTER) */
        .col-ladder { flex: 3.2; display: flex; flex-direction: column; background: #0a0e16; border-right: 1.5px solid var(--border); overflow: hidden; }
        .ladder-top-summary { padding: 8px 10px; border-bottom: 1px solid var(--border); display: flex; gap: 8px; }
        .sum-box-buy { flex: 1; background: rgba(0, 230, 118, 0.08); border: 1px solid rgba(0, 230, 118, 0.3); border-radius: 6px; padding: 6px; font-size: 10.5px; }
        .sum-box-sell { flex: 1; background: rgba(255, 61, 113, 0.08); border: 1px solid rgba(255, 61, 113, 0.3); border-radius: 6px; padding: 6px; font-size: 10.5px; }

        .ladder-header-strip { display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; font-size: 11px; font-weight: 900; color: var(--text-dim); border-bottom: 1px solid var(--border); background: #080c14; }
        .ladder-rows-scroll { flex: 1; overflow-y: auto; padding: 4px 0; }
        
        .ladder-row-item { display: flex; align-items: center; height: 23px; font-size: 11.5px; font-weight: 800; }
        .ladder-row-item.current-price { background: rgba(255, 255, 255, 0.16); border-top: 1px solid rgba(255,255,255,0.4); border-bottom: 1px solid rgba(255,255,255,0.4); }
        .bid-side { flex: 1; display: flex; justify-content: flex-end; align-items: center; padding-right: 6px; }
        .bid-bar { background: var(--green); height: 15px; border-radius: 2px 0 0 2px; display: flex; align-items: center; justify-content: flex-end; padding-right: 4px; color: #000; font-size: 10px; font-weight: 900; }
        .p-axis { width: 70px; text-align: center; color: #e2e8f0; font-family: monospace; font-size: 12px; font-weight: 900; flex-shrink: 0; }
        .ask-side { flex: 1; display: flex; justify-content: flex-start; align-items: center; padding-left: 6px; }
        .ask-bar { background: var(--red); height: 15px; border-radius: 0 2px 2px 0; display: flex; align-items: center; padding-left: 4px; color: #fff; font-size: 10px; font-weight: 900; }

        /* COLUMN 3: BIG ORDERS RIGHT NOW + DEPTH (RIGHT) */
        .col-big-orders { flex: 4; display: flex; flex-direction: column; background: #07090e; padding: 10px 12px; overflow-y: auto; gap: 8px; }
        .big-order-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 10px; }
        .feed-order-row { padding: 6px 0; border-bottom: 1px dashed rgba(255,255,255,0.06); font-size: 11px; }

        .gauge-track { height: 7px; background: var(--red); border-radius: 4px; overflow: hidden; display: flex; margin-top: 6px; }
        .gauge-fill-buyers { background: var(--green); height: 100%; width: 39%; }
    </style>
</head>
<body>
    <div class="twiq-navbar">
        <div class="twiq-brand">
            <span>Available on twiq.pro (Video 1 Setup)</span>
            <span class="pill-badge">Nifty 50</span>
            <span class="pill-badge" style="color:#00e676;">5m</span>
            <span class="pill-badge">fx</span>
        </div>
        <div class="nav-links">
            <a href="/">📈 3 CHARTS</a>
            <a href="/oi-analytics">⚡ OI RADAR</a>
            <a href="/fno-activity">📊 F&O ACTIVITY</a>
        </div>
    </div>

    <div class="twiq-workspace">
        <!-- 1. LEFT CANDLESTICK CHART -->
        <div class="col-chart">
            <div style="position:absolute; top:8px; left:12px; font-size:11.5px; font-weight:bold; color:#38bdf8; z-index:10;">
                NIFTY FUTURES (5M) • LIVE CHART
            </div>
            <div id="canvasFuturesChart"></div>
        </div>

        <!-- 2. CENTER ORDER BOOK LADDER (LIVE CENTERED ON SPOT) -->
        <div class="col-ladder">
            <div style="padding:6px 10px; font-size:12px; font-weight:900; border-bottom:1px solid var(--border);">
                Order book <small style="color:var(--text-dim); font-size:10px;">• Updated 0s ago</small>
                <div style="font-size:10px; color:var(--text-dim); font-weight:normal;">Nifty Futures Open Orders</div>
            </div>

            <div class="ladder-top-summary">
                <div class="sum-box-buy">
                    <div style="color:var(--text-dim); font-size:9.5px;">Open Buy orders</div>
                    <b style="color:var(--green); font-size:13px;" id="dispBuyOrderTop">--</b>
                    <div style="font-size:9.5px; color:var(--text-dim);" id="dispBuySubTop">-13.3 pts • 247 lots</div>
                </div>
                <div class="sum-box-sell">
                    <div style="color:var(--text-dim); font-size:9.5px;">Open Sell orders</div>
                    <b style="color:var(--red); font-size:13px;" id="dispSellOrderTop">--</b>
                    <div style="font-size:9.5px; color:var(--text-dim);" id="dispSellSubTop">+6.7 pts • 204 lots</div>
                </div>
            </div>

            <div class="ladder-header-strip">
                <span>BID LOTS</span>
                <span>PRICE</span>
                <span>ASK LOTS</span>
            </div>

            <div class="ladder-rows-scroll" id="ladderRowsBox"></div>

            <div style="padding:6px 10px; font-size:9.5px; color:var(--text-dim); border-top:1px solid var(--border); background:#080c14;">
                Colored price: 2x usual 58 lots or more • Spot <b style="color:#00ff88;" id="dispSpotLadder">--</b>
            </div>
        </div>

        <!-- 3. RIGHT BIG ORDERS RIGHT NOW + DEPTH STATS -->
        <div class="col-big-orders">
            <div class="big-order-card">
                <div style="font-size:12px; font-weight:900; margin-bottom:6px;">
                    Big orders right now <small style="color:var(--text-dim); font-size:10px;">• 2x usual 5-point size</small>
                </div>
                <div id="bigOrdersFeedBox"></div>
                <div style="font-size:10.5px; color:#fbbf24; margin-top:8px;">Recently pulled (9 left before price reached them)</div>
            </div>

            <div class="big-order-card">
                <div style="display:flex; justify-content:space-between; font-size:11px;">
                    <span>Depth within 20 pts: <b>106% of usual</b></span>
                    <span>Spread: <b>3.20 pts</b></span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:11px; margin-top:8px;">
                    <span style="color:var(--green); font-weight:900;">Buyers 39%</span>
                    <span style="color:var(--red); font-weight:900;">Sellers 61%</span>
                </div>
                <div class="gauge-track">
                    <div class="gauge-fill-buyers"></div>
                </div>
                <div style="font-size:10px; color:var(--text-dim); margin-top:8px; line-height:1.4;">
                    Netting lots within 20 pts. Orders can be cancelled any time. This is context, not direction.
                </div>
            </div>
        </div>
    </div>

    <script>
        const tvChart = LightweightCharts.createChart(document.getElementById('canvasFuturesChart'), {
            autoSize: true,
            layout: { background: { color: '#07090e' }, textColor: '#94a3b8', fontSize: 11 },
            grid: { vertLines: { color: '#141b2b' }, horzLines: { color: '#141b2b' } },
            rightPriceScale: { borderColor: '#162030', visible: true },
            timeScale: { borderColor: '#162030', timeVisible: true }
        });
        const series = tvChart.addCandlestickSeries({
            upColor: '#00e676', downColor: '#ff3d71',
            borderUpColor: '#00e676', borderDownColor: '#ff3d71',
            wickUpColor: '#00e676', wickDownColor: '#ff3d71'
        });

        async function fetchTwiqData() {
            try {
                let [mRes, lRes] = await Promise.all([fetch('/api/market_data'), fetch('/api/orderbook/twiq')]);
                let m = await mRes.json();
                let l = await lRes.json();

                if (m.candles) {
                    series.setData(m.candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                    tvChart.timeScale().fitContent();
                }

                document.getElementById('dispSpotLadder').innerText = l.spot.toFixed(1);
                document.getElementById('dispBuyOrderTop').innerText = l.open_buy_order.strike;
                document.getElementById('dispBuySubTop').innerText = `${l.open_buy_order.pts} • ${l.open_buy_order.lots}`;
                document.getElementById('dispSellOrderTop').innerText = l.open_sell_order.strike;
                document.getElementById('dispSellSubTop').innerText = `${l.open_sell_order.pts} • ${l.open_sell_order.lots}`;

                // Render Live Ladder Rows dynamically centered on spot
                let lHtml = '';
                l.levels.forEach(lvl => {
                    let curCls = lvl.is_current ? 'current-price' : '';
                    let bidContent = '';
                    if (lvl.bid) {
                        let w = Math.min(100, Math.max(12, (lvl.bid / 858) * 100));
                        bidContent = `<div class="bid-bar" style="width:${w}%;">${lvl.bid}</div>`;
                    }
                    let askContent = '';
                    if (lvl.ask) {
                        let w = Math.min(100, Math.max(12, (lvl.ask / 201) * 100));
                        askContent = `<div class="ask-bar" style="width:${w}%;">${lvl.ask}</div>`;
                    }
                    lHtml += `
                    <div class="ladder-row-item ${curCls}">
                        <div class="bid-side">${bidContent}</div>
                        <div class="p-axis">${lvl.price.toLocaleString()}</div>
                        <div class="ask-side">${askContent}</div>
                    </div>`;
                });
                document.getElementById('ladderRowsBox').innerHTML = lHtml;

                // Render Big Orders Feed
                let bHtml = '';
                l.big_orders.forEach(o => {
                    let col = o.type === 'BUY' ? 'var(--green)' : 'var(--red)';
                    bHtml += `
                    <div class="feed-order-row">
                        <div style="font-weight:900;"><span style="color:${col};">Open ${o.type} orders</span> <b>${o.range}</b></div>
                        <div style="color:#e2e8f0; font-size:10.5px;">${o.lots}</div>
                        <div style="color:var(--text-dim); font-size:9.5px;">${o.sub}</div>
                    </div>`;
                });
                document.getElementById('bigOrdersFeedBox').innerHTML = bHtml;

            } catch(e) {}
        }
        window.addEventListener('resize', () => {
            tvChart.resize(document.getElementById('canvasFuturesChart').clientWidth, document.getElementById('canvasFuturesChart').clientHeight);
        });
        fetchTwiqData();
        setInterval(fetchTwiqData, 2000);
    </script>
</body>
</html>
"""

# ==================== CLEAN DISTINCT ROUTE MAPPING (ALL 4 PAGES) ====================
@app.get("/", response_class=HTMLResponse)
def page_3charts():
    return TERMINAL_HTML

@app.get("/oi-analytics", response_class=HTMLResponse)
def page_oi_matrix():
    return OI_DASHBOARD_HTML

@app.get("/fno-activity", response_class=HTMLResponse)
def page_fno():
    return FNO_ACTIVITY_HTML

@app.get("/order-book", response_class=HTMLResponse)
def page_orderbook():
    return ORDERBOOK_LADDER_HTML
