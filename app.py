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
    "ladder_data": None,
    "ladder_time": 0,
    "last_spot": 24646.20
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
        "strike": "24600 CE",
        "entry": 165.0,
        "sl": 145.0,
        "target": 205.0,
        "result": "TARGET HIT (+40 pts)",
        "notes": "24600 Support bounce + Big Buyers 125 lots"
    },
    {
        "time": "11:20 AM",
        "signal": "BUY PE",
        "strike": "24680 PE",
        "entry": 190.0,
        "sl": 170.0,
        "target": 230.0,
        "result": "TARGET HIT (+40 pts)",
        "notes": "24680 Rejection + Nearest Big Sellers 134k"
    },
    {
        "time": "11:45 AM",
        "signal": "BUY CE",
        "strike": "24650 CE",
        "entry": 166.0,
        "sl": 148.0,
        "target": 200.0,
        "result": "SL HIT (-18 pts)",
        "notes": "24650 Pulled order break thayo"
    }
]

# F&O 4-Quadrant Stocks Data (Video Reference)
FNO_BUILDUPS = {
    "long_buildup": [
        {"symbol": "AXISBANK", "name": "Axis Bank Limited", "price": "1,217.50", "pchange": "+0.11%", "oi": "+17.57%", "tag": "Top Gainer", "pe": "13.6", "fpe": "12.6", "margin": "37.5%", "growth": "+21%"},
        {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals", "price": "7,704.50", "pchange": "+0.87%", "oi": "+15.84%", "tag": "High Vol", "pe": "45.2", "fpe": "39.1", "margin": "14.2%", "growth": "+19%"},
        {"symbol": "CIPLA", "name": "Cipla Limited", "price": "1,528.00", "pchange": "+0.61%", "oi": "+11.77%", "tag": "Confirmed", "pe": "24.8", "fpe": "22.1", "margin": "22.5%", "growth": "+12%"},
        {"symbol": "ULTRACEMCO", "name": "UltraTech Cement", "price": "10,950.00", "pchange": "+1.14%", "oi": "+10.20%", "tag": "Top Gainer", "pe": "38.5", "fpe": "32.0", "margin": "18.1%", "growth": "+15%"},
        {"symbol": "PIIND", "name": "PI Industries", "price": "4,180.00", "pchange": "+0.45%", "oi": "+9.15%", "tag": "Confirmed", "pe": "31.2", "fpe": "27.4", "margin": "24.0%", "growth": "+18%"},
        {"symbol": "INDIGO", "name": "InterGlobe Aviation", "price": "4,350.00", "pchange": "+1.85%", "oi": "+8.40%", "tag": "Top Gainer", "pe": "19.5", "fpe": "16.8", "margin": "11.5%", "growth": "+26%"},
        {"symbol": "MARUTI", "name": "Maruti Suzuki", "price": "11,352.00", "pchange": "+0.97%", "oi": "+7.12%", "tag": "Confirmed", "pe": "23.4", "fpe": "20.1", "margin": "12.8%", "growth": "+16%"}
    ],
    "short_buildup": [
        {"symbol": "SHRIRAMFIN", "name": "Shriram Finance", "price": "881.15", "pchange": "-1.72%", "oi": "+42.50%", "tag": "Heavy Sell", "pe": "11.2", "fpe": "10.1", "margin": "19.5%", "growth": "+14%"},
        {"symbol": "CHOLAFIN", "name": "Cholamandalam Inv", "price": "1,482.00", "pchange": "-0.95%", "oi": "+26.80%", "tag": "Breakdown", "pe": "26.4", "fpe": "22.5", "margin": "17.2%", "growth": "+21%"},
        {"symbol": "DELHIVERY", "name": "Delhivery Limited", "price": "378.90", "pchange": "-2.15%", "oi": "+21.40%", "tag": "Heavy Sell", "pe": "58.1", "fpe": "42.0", "margin": "4.5%", "growth": "+13%"},
        {"symbol": "MANAPPURAM", "name": "Manappuram Finance", "price": "178.50", "pchange": "-3.40%", "oi": "+18.90%", "tag": "Breakdown", "pe": "8.4", "fpe": "7.6", "margin": "22.1%", "growth": "+9%"},
        {"symbol": "SWIGGY", "name": "Swiggy Limited", "price": "448.20", "pchange": "-1.80%", "oi": "+15.60%", "tag": "Heavy Sell", "pe": "N/A", "fpe": "N/A", "margin": "-8.2%", "growth": "+32%"},
        {"symbol": "GODREJPROP", "name": "Godrej Properties", "price": "2,780.00", "pchange": "-1.60%", "oi": "+14.20%", "tag": "Breakdown", "pe": "48.2", "fpe": "39.0", "margin": "15.0%", "growth": "+25%"},
        {"symbol": "CANBK", "name": "Canara Bank", "price": "101.40", "pchange": "-1.10%", "oi": "+12.80%", "tag": "Confirmed", "pe": "6.2", "fpe": "5.8", "margin": "16.4%", "growth": "+11%"},
        {"symbol": "VOLTAS", "name": "Voltas Limited", "price": "1,680.00", "pchange": "-2.25%", "oi": "+11.50%", "tag": "Heavy Sell", "pe": "62.4", "fpe": "48.1", "margin": "5.8%", "growth": "+14%"}
    ],
    "short_covering": [
        {"symbol": "TCS", "name": "Tata Consultancy", "price": "3,530.00", "pchange": "+0.80%", "oi": "-6.10%", "tag": "Short Exit", "pe": "27.5", "fpe": "24.8", "margin": "25.2%", "growth": "+8%"},
        {"symbol": "AMARARAJA", "name": "Amara Raja Energy", "price": "1,140.00", "pchange": "+1.95%", "oi": "-7.40%", "tag": "Short Exit", "pe": "21.0", "fpe": "18.5", "margin": "13.8%", "growth": "+17%"},
        {"symbol": "BOSCHLTD", "name": "Bosch Limited", "price": "34,450.00", "pchange": "+0.55%", "oi": "-5.80%", "tag": "Confirmed", "pe": "36.2", "fpe": "31.0", "margin": "16.5%", "growth": "+12%"},
        {"symbol": "GRASIM", "name": "Grasim Industries", "price": "2,610.00", "pchange": "+1.10%", "oi": "-4.90%", "tag": "Short Exit", "pe": "28.4", "fpe": "24.2", "margin": "14.1%", "growth": "+11%"}
    ],
    "long_unwinding": [
        {"symbol": "SIEMENS", "name": "Siemens Limited", "price": "7,240.00", "pchange": "-0.90%", "oi": "-8.20%", "tag": "Long Exit", "pe": "68.5", "fpe": "54.0", "margin": "14.8%", "growth": "+18%"},
        {"symbol": "KPITTECH", "name": "KPIT Technologies", "price": "1,520.00", "pchange": "-1.45%", "oi": "-7.10%", "tag": "Long Exit", "pe": "52.1", "fpe": "41.2", "margin": "19.2%", "growth": "+28%"},
        {"symbol": "ADANIGREEN", "name": "Adani Green Energy", "price": "1,685.00", "pchange": "-2.10%", "oi": "-6.80%", "tag": "Profit Booking", "pe": "95.0", "fpe": "72.0", "margin": "28.5%", "growth": "+34%"},
        {"symbol": "HINDALCO", "name": "Hindalco Industries", "price": "645.00", "pchange": "-1.30%", "oi": "-5.90%", "tag": "Long Exit", "pe": "14.2", "fpe": "12.8", "margin": "11.2%", "growth": "+9%"}
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
    active_exp = all_exp[0] if all_exp else "23NOV2026"
    strikes = [atm + (i * 50) for i in range(-5, 6)]
    token_map = get_tokens_by_expiry_and_strikes(active_exp, strikes)
    
    tokens = []
    for s in token_map.values():
        if "CE" in s: tokens.append(s["CE"])
        if "PE" in s: tokens.append(s["PE"])
    quotes = fetch_angel_market_data(tokens)

    chain = []
    total_c_oi, total_p_oi = 0, 0
    for s in strikes:
        ce_tok = token_map.get(s, {}).get("CE", "")
        pe_tok = token_map.get(s, {}).get("PE", "")
        c_ltp = quotes.get(ce_tok, {}).get("ltp", max(1.0, round(165 - (s - spot)*0.45, 2)))
        p_ltp = quotes.get(pe_tok, {}).get("ltp", max(1.0, round(185 + (s - spot)*0.45, 2)))
        c_oi = quotes.get(ce_tok, {}).get("oi", 450000)
        p_oi = quotes.get(pe_tok, {}).get("oi", 380000)
        total_c_oi += c_oi
        total_p_oi += p_oi

        chain.append({
            "strike": s, "ltp_ce": c_ltp, "ltp_pe": p_ltp,
            "oi_ce": c_oi, "oi_pe": p_oi,
            "oi_ce_str": f"{round(c_oi/100000, 1)}L",
            "oi_pe_str": f"{round(p_oi/100000, 1)}L",
            "is_atm": (s == atm)
        })

    pcr = round(total_p_oi / total_c_oi, 2) if total_c_oi > 0 else 0.78
    result = {
        "spot": spot, "atm": atm, "active_expiry": active_exp,
        "chain": chain, "pcr": pcr, "india_vix": fetch_india_vix(), "max_pain": atm - 50
    }
    CACHE_STORE["market_data"] = result
    CACHE_STORE["market_time"] = now
    return result

# ==================== F&O BUILDUPS REST API ====================
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

# ==================== LADDER API ====================
@app.get("/api/orderbook/ladder")
def get_orderbook_ladder():
    now = time.time()
    if CACHE_STORE["ladder_data"] and (now - CACHE_STORE["ladder_time"]) < 2.0:
        return CACHE_STORE["ladder_data"]

    m = get_market_data()
    spot = m["spot"]
    if spot < 1000: spot = 24646.20
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

    nearest_buyers_low = int(center_price - 30)
    nearest_buyers_high = int(center_price - 20)
    nearest_sellers_low = int(center_price + 10)
    nearest_sellers_high = int(center_price + 15)

    big_orders_list = [
        {"side": "SELL", "range": f"{nearest_sellers_high+30:,}–{nearest_sellers_high+35:,}", "lots": "147 lots • 18s ago"},
        {"side": "SELL", "range": f"{nearest_sellers_low:,}–{nearest_sellers_high:,}", "lots": "185 lots • 1 min ago"},
        {"side": "BUY", "range": f"{nearest_buyers_low:,}–{nearest_buyers_high:,}", "lots": "203 lots • 4 min ago"},
        {"side": "BUY", "range": f"{center_price-35:,}–{center_price-30:,}", "lots": "250 lots • 5 min ago"}
    ]

    stop_losses_list = [
        {"level": f"Just below {center_price-80:,}", "desc": "Below yesterday low (PUTS)"},
        {"level": f"Just below {center_price-40:,}", "desc": "Below the strike 25000"},
        {"level": f"Just above {center_price+60:,}", "desc": "Above today's high (CALLS)"}
    ]

    gujarati_news = (
        f"📢 ઓર્ડર બુક સમાચાર: નિફ્ટી ફ્યુચર ₹{future_price:,.2f} પર છે. "
        f"ઉપર {nearest_sellers_low:,}–{nearest_sellers_high:,} ના ઝોનમાં ૧૮૫ મોટા લોટ્સના સેલર્સ બેઠા છે. "
        f"નીચે {nearest_buyers_low:,}–{nearest_buyers_high:,} પર ૨૦૩ લોટ્સનું મોટું બાયિંગ સપોર્ટ મળ્યું હતું. "
        f"અત્યારે સેલર્સનું દબાણ વધુ છે, તેથી ઉછાળે પ્રોફિટ બુક કરવાનો પ્લાન કરો."
    )

    res = {
        "future_spot": f"{future_price:,.2f}",
        "raw_spot": f"{spot:,.2f}",
        "basis": "+32.5",
        "expiry": "23 Nov",
        "nearest_buyers": f"{nearest_buyers_low:,}–{nearest_buyers_high:,}",
        "buyers_sub": f"24.5 pts below • spot {spot-24.5:,.0f}",
        "nearest_sellers": f"{nearest_sellers_low:,}–{nearest_sellers_high:,}",
        "sellers_sub": f"18.2 pts above • spot {spot+18.2:,.0f}",
        "levels": levels,
        "big_orders": big_orders_list,
        "stop_losses": stop_losses_list,
        "gujarati_news": gujarati_news
    }
    CACHE_STORE["ladder_data"] = res
    CACHE_STORE["ladder_time"] = now
    return res

# ==================== QUANTUM STREAM ====================
@app.get("/api/oi/quantum-stream")
def get_quantum_stream():
    now = time.time()
    if CACHE_STORE["stream_data"] and (now - CACHE_STORE["stream_time"]) < 2.5:
        return CACHE_STORE["stream_data"]

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
        "verdict": "⚡ RANGEBOUND CONSOLIDATION (24600 - 24700)",
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

# ==================== PAPER TRADING REST APIS ====================
@app.get("/api/paper/state")
def get_paper_state():
    total_unrealized = sum(p.get("pnl", 0) for p in PAPER_STATE["positions"])
    total_realized = sum(o.get("pnl", 0) for o in PAPER_STATE["order_history"])
    return {
        "capital": PAPER_STATE["capital"],
        "available_funds": round(PAPER_STATE["available_funds"], 2),
        "total_pnl": round(total_unrealized + total_realized, 2),
        "positions": PAPER_STATE["positions"],
        "orders": PAPER_STATE["order_history"]
    }

@app.post("/api/paper/order")
async def place_order(req: Request):
    body = await req.json()
    sym = body.get("symbol")
    side = body.get("side", "BUY")
    qty = int(body.get("qty", 65))
    price = float(body.get("price", 165.0))
    cost = round(price * qty, 2)
    if side == "BUY" and PAPER_STATE["available_funds"] < cost:
        return JSONResponse({"status": "error", "message": "Available Margin ઓછી છે!"})

    if side == "BUY":
        PAPER_STATE["available_funds"] -= cost
        pos = {
            "id": len(PAPER_STATE["positions"]) + 1, "symbol": sym, "qty": qty,
            "entry_price": price, "ltp": price, "pnl": 0.0,
            "product": body.get("product", "INTRADAY"),
            "time": get_current_ist_time().strftime("%I:%M:%S %p")
        }
        PAPER_STATE["positions"].append(pos)
    
    PAPER_STATE["order_history"].append({
        "time": get_current_ist_time().strftime("%I:%M:%S %p"),
        "symbol": sym, "side": side, "qty": qty, "price": price,
        "product": body.get("product", "INTRADAY"),
        "type": body.get("type", "LIMIT"),
        "status": "EXECUTED", "pnl": 0.0
    })
    return JSONResponse({"status": "success", "message": f"{sym} ({qty} Qty) {side} Order Executed!"})

@app.post("/api/paper/close")
async def close_order(req: Request):
    body = await req.json()
    pos_id = body.get("pos_id")
    target = next((p for p in PAPER_STATE["positions"] if p["id"] == pos_id), None)
    if target:
        PAPER_STATE["positions"].remove(target)
        pnl = round((target["ltp"] - target["entry_price"]) * target["qty"], 2)
        PAPER_STATE["available_funds"] += (target["entry_price"] * target["qty"] + pnl)
        return JSONResponse({"status": "success", "message": f"{target['symbol']} Closed! P&L: ₹{pnl}"})
    return JSONResponse({"status": "error", "message": "Position Not Found"})

# ==================== NEW PAGE: F&O ACTIVITY & BUILD-UP SCREENER HTML ====================
FNO_ACTIVITY_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>F&O Activity - The Trade Cartel</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+Gujarati:wght@600;800;900&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        :root {
            --bg-deep: #090d16; --panel-bg: #111726; --card-bg: #162033;
            --green: #00e676; --red: #ff3d71; --blue: #38bdf8; --orange: #fb923c;
            --border: #1e293b; --text-dim: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', 'Noto Sans Gujarati', sans-serif; }
        body { background: var(--bg-deep); color: #fff; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        .navbar { height: 48px; background: #070a12; border-bottom: 1.5px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; flex-shrink: 0; }
        .nav-brand { font-size: 14px; font-weight: 900; color: #fff; display: flex; align-items: center; gap: 8px; }
        .nav-links a { background: #131d2e; border: 1px solid var(--border); color: #38bdf8; padding: 4px 10px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 800; margin-left: 6px; }

        /* DASHBOARD SUMMARY */
        .dashboard-strip { padding: 12px 16px; background: #0c121e; border-bottom: 1px solid var(--border); }
        .dash-cards-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 8px; }
        .d-box { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; }
        .d-title { font-size: 11px; color: var(--text-dim); font-weight: 700; }
        .d-val { font-size: 18px; font-weight: 900; margin-top: 2px; }

        /* PREDICTION BANNER */
        .prediction-box { background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; padding: 8px 14px; margin-top: 10px; font-size: 11.5px; display: flex; justify-content: space-between; align-items: center; }

        /* FNO 4 QUADRANT GRID */
        .fno-workspace { padding: 14px 16px; flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
        .buildup-card { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px; }
        .b-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 8px; }
        .b-title { font-size: 13px; font-weight: 900; }
        .b-sub { font-size: 10.5px; color: var(--text-dim); }

        .stock-item-row { display: flex; align-items: center; justify-content: space-between; padding: 9px 8px; border-bottom: 1px solid rgba(255,255,255,0.05); cursor: pointer; border-radius: 4px; transition: background 0.15s ease; }
        .stock-item-row:hover { background: rgba(56, 189, 248, 0.1); }
        .stock-tag-badge { font-size: 9px; padding: 2px 6px; border-radius: 3px; font-weight: 800; margin-left: 6px; }

        /* POPUP STOCK DETAILS MODAL (AS SEEN IN VIDEO) */
        .stock-modal-backdrop { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.85); display: none; justify-content: center; align-items: center; z-index: 1000; }
        .stock-modal-card { background: #0f1624; border: 1.5px solid #38bdf8; border-radius: 12px; width: 950px; max-width: 95%; max-height: 90vh; overflow-y: auto; padding: 18px; box-shadow: 0 0 35px rgba(56, 189, 248, 0.3); }

        .btn-modal-close { background: #ff3d71; color: #fff; border: none; padding: 6px 14px; border-radius: 4px; font-weight: 800; cursor: pointer; }
    </style>
</head>
<body>

    <div class="navbar">
        <div class="nav-brand"><span>🛡️</span> The Trade Cartel: F&O Activity</div>
        <div class="nav-links">
            <a href="/">📈 CHARTS</a>
            <a href="/order-book">🛡️ ORDER BOOK</a>
            <a href="/oi-analytics">⚡ OI RADAR</a>
            <a href="/paper-trading">📱 ANGEL PAPER</a>
        </div>
    </div>

    <!-- TOP DASHBOARD -->
    <div class="dashboard-strip">
        <div style="font-size:16px; font-weight:900;">Dashboard</div>
        <div class="dash-cards-grid">
            <div class="d-box">
                <div class="d-title">NIFTY 50</div>
                <div class="d-val" id="dispSpot" style="color:var(--blue);">24,646.20</div>
                <div style="font-size:10px; color:#ef4444;">-0.93% • Today</div>
            </div>
            <div class="d-box">
                <div class="d-title">Market mood</div>
                <div class="d-val" style="color:var(--red);">Trending down</div>
                <div style="font-size:10px; color:var(--text-dim);">Score: 12 of 48</div>
            </div>
            <div class="d-box">
                <div class="d-title">Advancing</div>
                <div class="d-val" style="color:#fbbf24;">388 / 1977</div>
                <div style="font-size:10px; color:var(--text-dim);">Stocks in green</div>
            </div>
            <div class="d-box">
                <div class="d-title">INDIA VIX</div>
                <div class="d-val" style="color:#c084fc;">14.50</div>
                <div style="font-size:10px; color:var(--text-dim);">Normal range</div>
            </div>
        </div>

        <div class="prediction-box">
            <span><b>Nifty Opening Expectation:</b> <span id="dispPrediction">Gap-down open likely (39 pts down, 45% confidence)</span></span>
            <span style="color:#ef4444; font-weight:800;">🔻 Gap-down open likely</span>
        </div>
    </div>

    <!-- FNO 4 QUADRANT LISTS -->
    <div style="padding:12px 16px 0; font-size:14px; font-weight:900;">
        Price and OI together
        <div style="font-size:11px; color:var(--text-dim); font-weight:normal; margin-top:2px;">Stock futures sorted by which way price and open interest moved today. Click any stock to view chart & drivers.</div>
    </div>

    <div class="fno-workspace">
        <!-- 1. LONG BUILD-UP -->
        <div class="buildup-card" style="border-top:3px solid var(--green);">
            <div class="b-header">
                <div>
                    <div class="b-title" style="color:var(--green);">Long build-up</div>
                    <div class="b-sub">Price up, OI up: fresh buying</div>
                </div>
                <b style="color:var(--green);" id="countLong">7 stocks</b>
            </div>
            <div id="boxLongBuildup"></div>
        </div>

        <!-- 2. SHORT BUILD-UP -->
        <div class="buildup-card" style="border-top:3px solid var(--red);">
            <div class="b-header">
                <div>
                    <div class="b-title" style="color:var(--red);">Short build-up</div>
                    <div class="b-sub">Price down, OI up: fresh selling</div>
                </div>
                <b style="color:var(--red);" id="countShort">8 stocks</b>
            </div>
            <div id="boxShortBuildup"></div>
        </div>

        <!-- 3. SHORT COVERING -->
        <div class="buildup-card" style="border-top:3px solid var(--blue);">
            <div class="b-header">
                <div>
                    <div class="b-title" style="color:var(--blue);">Short covering</div>
                    <div class="b-sub">Price up, OI down: shorts closing</div>
                </div>
                <b style="color:var(--blue);" id="countCovering">4 stocks</b>
            </div>
            <div id="boxShortCovering"></div>
        </div>

        <!-- 4. LONG UNWINDING -->
        <div class="buildup-card" style="border-top:3px solid var(--orange);">
            <div class="b-header">
                <div>
                    <div class="b-title" style="color:var(--orange);">Long unwinding</div>
                    <div class="b-sub">Price down, OI down: longs closing</div>
                </div>
                <b style="color:var(--orange);" id="countUnwinding">4 stocks</b>
            </div>
            <div id="boxLongUnwinding"></div>
        </div>
    </div>

    <!-- STOCK ANALYSIS MODAL (AS IN VIDEO) -->
    <div class="stock-modal-backdrop" id="stockModal">
        <div class="stock-modal-card">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); padding-bottom:10px;">
                <div>
                    <span style="font-size:18px; font-weight:900;" id="mStockSym">AXISBANK</span>
                    <span style="font-size:12px; color:var(--text-dim); margin-left:8px;" id="mStockName">Axis Bank Limited</span>
                    <div style="font-size:16px; font-weight:900; color:var(--green); margin-top:2px;" id="mStockPrice">₹ 1,217.50 (+0.11%)</div>
                </div>
                <button class="btn-modal-close" onclick="closeStockModal()">CLOSE</button>
            </div>

            <!-- KEY DRIVERS & METRICS -->
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; margin:14px 0;">
                <div style="background:var(--card-bg); padding:10px; border-radius:6px; border:1px solid var(--border);">
                    <div style="font-size:10.5px; color:var(--text-dim);">P/E Ratio</div>
                    <b style="font-size:16px;" id="mPE">13.6</b>
                </div>
                <div style="background:var(--card-bg); padding:10px; border-radius:6px; border:1px solid var(--border);">
                    <div style="font-size:10.5px; color:var(--text-dim);">Forward P/E</div>
                    <b style="font-size:16px;" id="mFPE">12.6</b>
                </div>
                <div style="background:var(--card-bg); padding:10px; border-radius:6px; border:1px solid var(--border);">
                    <div style="font-size:10.5px; color:var(--text-dim);">Profit Margin</div>
                    <b style="font-size:16px; color:var(--green);" id="mMargin">37.5%</b>
                </div>
                <div style="background:var(--card-bg); padding:10px; border-radius:6px; border:1px solid var(--border);">
                    <div style="font-size:10.5px; color:var(--text-dim);">Revenue Growth</div>
                    <b style="font-size:16px; color:var(--blue);" id="mGrowth">+21% YoY</b>
                </div>
            </div>

            <!-- CHART CANVAS -->
            <div style="font-size:12px; font-weight:bold; margin-bottom:6px; color:#38bdf8;">Candlestick Price Chart & EMA Stack (10 / 20 / 50 / 200 EMA)</div>
            <div id="stockCandleChart" style="width:100%; height:320px; background:#070a12; border-radius:8px; border:1px solid var(--border);"></div>

            <!-- BULL & BEAR CASE -->
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-top:14px;">
                <div style="background:rgba(0,230,118,0.06); border:1px solid rgba(0,230,118,0.25); border-radius:8px; padding:12px;">
                    <b style="color:var(--green); font-size:13px;">Bull Case: Strong Fundamentals</b>
                    <ul style="font-size:11px; color:#e2e8f0; margin-left:16px; margin-top:6px; line-height:1.6;">
                        <li>P/E 13.6 represents solid value against sector average.</li>
                        <li>High operating profit growth of 25%+ year-on-year.</li>
                        <li>Fresh long build-up confirms buyer accumulation.</li>
                    </ul>
                </div>
                <div style="background:rgba(255,61,113,0.06); border:1px solid rgba(255,61,113,0.25); border-radius:8px; padding:12px;">
                    <b style="color:var(--red); font-size:13px;">Bear Case: Technical Resistance</b>
                    <ul style="font-size:11px; color:#e2e8f0; margin-left:16px; margin-top:6px; line-height:1.6;">
                        <li>Price trades near short-term 50-EMA resistance band.</li>
                        <li>Overall banking sector mood remains cautious.</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <script>
        let fnoData = null;
        let stockChartInstance = null;
        let stockSeriesInstance = null;

        async function loadFnoData() {
            try {
                let res = await fetch('/api/fno/buildups');
                fnoData = await res.json();

                document.getElementById('dispSpot').innerText = fnoData.spot;
                document.getElementById('dispPrediction').innerText = fnoData.gap_prediction;

                let b = fnoData.buildups;
                renderList('boxLongBuildup', b.long_buildup, 'var(--green)', '#00e67622');
                renderList('boxShortBuildup', b.short_buildup, 'var(--red)', '#ff3d7122');
                renderList('boxShortCovering', b.short_covering, 'var(--blue)', '#38bdf822');
                renderList('boxLongUnwinding', b.long_unwinding, 'var(--orange)', '#fb923c22');

            } catch(e) {}
        }

        function renderList(containerId, list, col, bgBadge) {
            let html = '';
            list.forEach(s => {
                html += `
                <div class="stock-item-row" onclick='openStockModal(${JSON.stringify(s)})'>
                    <div>
                        <b style="font-size:12.5px;">${s.symbol}</b>
                        <span class="stock-tag-badge" style="background:${bgBadge}; color:${col};">${s.tag}</span>
                        <div style="font-size:10px; color:var(--text-dim);">${s.name}</div>
                    </div>
                    <div style="text-align:right;">
                        <b style="font-size:12.5px;">₹ ${s.price}</b>
                        <div style="font-size:10.5px; font-weight:800; color:${col};">${s.pchange} • OI ${s.oi}</div>
                    </div>
                </div>`;
            });
            document.getElementById(containerId).innerHTML = html;
        }

        function openStockModal(s) {
            document.getElementById('mStockSym').innerText = s.symbol;
            document.getElementById('mStockName').innerText = s.name;
            document.getElementById('mStockPrice').innerText = `₹ ${s.price} (${s.pchange})`;
            document.getElementById('mPE').innerText = s.pe;
            document.getElementById('mFPE').innerText = s.fpe;
            document.getElementById('mMargin').innerText = s.margin;
            document.getElementById('mGrowth').innerText = s.growth;

            document.getElementById('stockModal').style.display = 'flex';
            setTimeout(() => initStockChart(s), 100);
        }

        function closeStockModal() {
            document.getElementById('stockModal').style.display = 'none';
        }

        function initStockChart(s) {
            const container = document.getElementById('stockCandleChart');
            container.innerHTML = '';
            stockChartInstance = LightweightCharts.createChart(container, {
                autoSize: true,
                layout: { background: { color: '#070a12' }, textColor: '#94a3b8' },
                grid: { vertLines: { color: '#162033' }, horzLines: { color: '#162033' } },
                timeScale: { timeVisible: true }
            });
            stockSeriesInstance = stockChartInstance.addCandlestickSeries({
                upColor: '#00e676', downColor: '#ff3d71',
                borderUpColor: '#00e676', borderDownColor: '#ff3d71',
                wickUpColor: '#00e676', wickDownColor: '#ff3d71'
            });

            let baseTime = Math.floor(Date.now() / 1000) - 3600 * 5;
            let p = parseFloat(s.price.replace(',', '')) || 1200;
            let candles = [];
            for (let i = 0; i < 45; i++) {
                let o = p;
                let h = o + 6;
                let l = o - 4;
                let c = o + (i % 2 === 0 ? 3 : -2);
                candles.push({ time: baseTime + (i * 300), open: o, high: h, low: l, close: c });
                p = c;
            }
            stockSeriesInstance.setData(candles);
        }

        loadFnoData();
        setInterval(loadFnoData, 5000);
    </script>
</body>
</html>
"""

# ==================== HTML 1: PRO TERMINAL (CHARTS & CHAIN) ====================
TERMINAL_HTML = r"""<!DOCTYPE html>
<html>
<head>
    <title>Hari Master Pro Terminal - Charts & Option Chain</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, sans-serif; }
        body { background: #080b11; color: #d1d4dc; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .header-bar { height: 46px; background: #0e131f; border-bottom: 1px solid #1a2234; display: flex; align-items: center; justify-content: space-between; padding: 0 14px; flex-shrink: 0; }
        .brand { font-size: 14px; font-weight: 900; color: #38bdf8; }
        .spot-badge { font-weight: 800; color: #00ff88; background: #062319; border: 1px solid #00ff88; padding: 3px 10px; border-radius: 4px; font-size: 12px; }
        .nav-links a { background: #172554; border: 1px solid #2563eb; color: #38bdf8; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 800; text-decoration: none; margin-left: 6px; }
        .nav-links a.active { background: #2563eb; color: #fff; }
        .workspace { flex: 1; overflow-y: auto; padding: 12px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; }
        th { background: #161e2e; padding: 10px 6px; color: #94a3b8; position: sticky; top: 0; border-bottom: 1px solid #1e293b; }
        td { padding: 8px 4px; border-bottom: 1px solid #141b2b; }
        .atm-row { background: rgba(56, 189, 248, 0.15); font-weight: bold; border-left: 3px solid #38bdf8; }
    </style>
</head>
<body>
    <div class="header-bar">
        <div class="brand">📈 HARI MASTER PRO TERMINAL</div>
        <div class="spot-badge" id="spotBadge">NIFTY: ₹24,646.20</div>
        <div class="nav-links">
            <a href="/" class="active">📈 CHARTS</a>
            <a href="/fno-activity">📊 F&O ACTIVITY</a>
            <a href="/order-book">🛡️ ORDER BOOK</a>
            <a href="/oi-analytics">⚡ OI RADAR</a>
            <a href="/paper-trading">📱 ANGEL PAPER</a>
        </div>
    </div>
    <div class="workspace">
        <table>
            <thead>
                <tr>
                    <th style="color:#00ff88;">CALL OI</th>
                    <th style="color:#00ff88;">CALL LTP</th>
                    <th>STRIKE</th>
                    <th style="color:#ff2255;">PUT LTP</th>
                    <th style="color:#ff2255;">PUT OI</th>
                </tr>
            </thead>
            <tbody id="chainBody"></tbody>
        </table>
    </div>
    <script>
        async function loadTerminal() {
            try {
                let res = await fetch('/api/market_data');
                let d = await res.json();
                document.getElementById('spotBadge').innerText = 'NIFTY: ₹' + d.spot.toFixed(2);
                let html = '';
                d.chain.forEach(r => {
                    let cls = r.is_atm ? 'atm-row' : '';
                    html += `<tr class="${cls}">
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
        loadTerminal();
        setInterval(loadTerminal, 4000);
    </script>
</body>
</html>
"""

# ==================== HTML 2: QUANTUM OI RADAR ====================
OI_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hari Master Quantum OI Radar</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Gujarati:wght@500;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #05070a; --green-glow: #00ff88; --red-glow: #ff2255;
            --cyan-glow: #00f0ff; --border: #142033;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Sans Gujarati', monospace, sans-serif; }
        body { background: var(--bg-deep); color: #fff; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        .cyber-header { height: 42px; background: #090e17; border-bottom: 1.5px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 14px; }
        .header-title { font-size: 13.5px; font-weight: 900; color: var(--cyan-glow); }
        .nav-links a { background: #101c2e; border: 1.3px solid var(--cyan-glow); color: var(--cyan-glow); padding: 3px 10px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 800; margin-left: 6px; }

        .stream-workspace { flex: 1; display: flex; width: 100%; min-height: calc(100vh - 120px); }
        .matrix-canvas-box { flex: 1; position: relative; background: #040609; }
        #streamCanvas { width: 100%; height: 100%; }

        .strike-nodes-col { width: 420px; background: #080d16; border-left: 1.5px solid var(--border); display: flex; flex-direction: column; justify-content: space-around; padding: 6px; }
        .strike-card-node { background: #0d1522; border: 1.2px solid #1f2f45; border-radius: 5px; padding: 5px 8px; display: flex; justify-content: space-between; font-size: 12px; }
        .node-call { border-left: 4px solid var(--green-glow); }
        .node-put { border-left: 4px solid var(--red-glow); }
    </style>
</head>
<body>
    <div class="cyber-header">
        <div class="header-title">⚡ HARI MASTER QUANTUM OI RADAR</div>
        <div class="nav-links">
            <a href="/">📈 CHARTS</a>
            <a href="/fno-activity">📊 F&O ACTIVITY</a>
            <a href="/order-book">🛡️ ORDER BOOK</a>
            <a href="/paper-trading">📱 ANGEL PAPER</a>
        </div>
    </div>
    <div class="stream-workspace">
        <div class="matrix-canvas-box" id="canvasContainer"><canvas id="streamCanvas"></canvas></div>
        <div class="strike-nodes-col">
            <div style="color:var(--green-glow); font-size:11px; font-weight:bold;">▲ CALL RESISTANCE (CE)</div>
            <div id="callStrikes"></div>
            <div style="background:#fff; color:#000; padding:6px; border-radius:4px; font-weight:900; text-align:center;">SPOT: ₹ 24,646.20</div>
            <div style="color:var(--red-glow); font-size:11px; font-weight:bold;">▼ PUT SUPPORT (PE)</div>
            <div id="putStrikes"></div>
        </div>
    </div>
    <script>
        const canvas = document.getElementById('streamCanvas');
        const container = document.getElementById('canvasContainer');
        const ctx = canvas.getContext('2d');
        function resize() { canvas.width = container.clientWidth; canvas.height = container.clientHeight; }
        window.addEventListener('resize', resize);

        function drawCurves() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            let startX = 0, startY = canvas.height / 2, endX = canvas.width;
            for (let i = 0; i < 6; i++) {
                let targetY = (canvas.height / 2) - 25 - (i * 24);
                ctx.beginPath();
                ctx.strokeStyle = "rgba(0, 255, 136, 0.7)";
                ctx.lineWidth = 1.6;
                ctx.moveTo(startX, startY);
                ctx.bezierCurveTo(canvas.width * 0.45, startY - 15, canvas.width * 0.75, targetY, endX, targetY);
                ctx.stroke();
            }
            for (let i = 0; i < 6; i++) {
                let targetY = (canvas.height / 2) + 25 + (i * 24);
                ctx.beginPath();
                ctx.strokeStyle = "rgba(255, 34, 85, 0.7)";
                ctx.lineWidth = 1.6;
                ctx.moveTo(startX, startY);
                ctx.bezierCurveTo(canvas.width * 0.45, startY + 15, canvas.width * 0.75, targetY, endX, targetY);
                ctx.stroke();
            }
            requestAnimationFrame(drawCurves);
        }

        async function fetchRadar() {
            try {
                let res = await fetch('/api/oi/quantum-stream');
                let d = await res.json();
                let cHtml = '', pHtml = '';
                d.calls.slice(0, 5).forEach(c => {
                    cHtml += `<div class="strike-card-node node-call"><b>${c.strike} CE</b> <span style="color:#00ff88;">${c.oi_str}</span></div>`;
                });
                d.puts.slice(0, 5).forEach(p => {
                    pHtml += `<div class="strike-card-node node-put"><b>${p.strike} PE</b> <span style="color:#ff2255;">${p.oi_str}</span></div>`;
                });
                document.getElementById('callStrikes').innerHTML = cHtml;
                document.getElementById('putStrikes').innerHTML = pHtml;
            } catch(e) {}
        }
        resize();
        drawCurves();
        fetchRadar();
        setInterval(fetchRadar, 4000);
    </script>
</body>
</html>
"""

# ==================== HTML 3: ANGEL ONE MOBILE PAPER APP ====================
ANGEL_APP_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Angel Trading Pro - Mobile Edition</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --angel-blue: #1e3bef; --dark-bg: #0b0e14; --card-bg: #131722;
            --border-color: #1e2433; --green: #00c087; --red: #f23645;
            --text-main: #f1f5f9; --text-dim: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: var(--dark-bg); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

        .app-header { height: 48px; background: #0f131c; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; padding: 0 14px; }
        .avatar-circle { width: 28px; height: 28px; border-radius: 50%; background: var(--angel-blue); color: #fff; font-size: 11px; font-weight: 800; display: flex; align-items: center; justify-content: center; }
        .nav-links a { background: #172554; border: 1px solid #2563eb; color: #38bdf8; padding: 3px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 800; text-decoration: none; margin-left: 4px; }

        .app-body { flex: 1; overflow-y: auto; padding: 12px; }
        .strike-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--border-color); background: var(--card-bg); cursor: pointer; border-radius: 6px; margin-bottom: 6px; }
    </style>
</head>
<body>
    <div class="app-header">
        <div style="display:flex; align-items:center; gap:8px;">
            <div class="avatar-circle">M</div>
            <div><b style="font-size:12px;">ANGEL ONE PAPER</b><br><small style="color:var(--text-dim); font-size:9px;">1 LOT = 65 QTY</small></div>
        </div>
        <div class="nav-links">
            <a href="/">📈 CHARTS</a>
            <a href="/fno-activity">📊 F&O</a>
            <a href="/order-book">🛡️ LADDER</a>
            <a href="/oi-analytics">⚡ RADAR</a>
        </div>
    </div>
    <div class="app-body">
        <div style="background:linear-gradient(135deg, #172554, #1e1b4b); padding:14px; border-radius:8px; display:flex; justify-content:space-between; margin-bottom:12px;">
            <div><span>FUNDS:</span><h3 id="dispFunds">₹ 1,00,000.00</h3></div>
            <div style="text-align:right;"><span>P&L:</span><h3 id="dispPnl" style="color:var(--green);">+₹ 0.00</h3></div>
        </div>
        <div id="watchlistContainer"></div>
    </div>
    <script>
        async function loadWatchlist() {
            try {
                let res = await fetch('/api/market_data');
                let d = await res.json();
                let html = '';
                d.chain.forEach(s => {
                    html += `
                    <div class="strike-row" onclick="buyTrade('${s.strike} CE', ${s.ltp_ce})">
                        <div><b>NIFTY ${s.strike} CE</b><br><small style="color:var(--text-dim);">OI: ${s.oi_ce_str}</small></div>
                        <div style="color:var(--green); font-weight:bold;">₹${s.ltp_ce.toFixed(2)} (BUY)</div>
                    </div>
                    <div class="strike-row" onclick="buyTrade('${s.strike} PE', ${s.ltp_pe})">
                        <div><b>NIFTY ${s.strike} PE</b><br><small style="color:var(--text-dim);">OI: ${s.oi_pe_str}</small></div>
                        <div style="color:var(--red); font-weight:bold;">₹${s.ltp_pe.toFixed(2)} (BUY)</div>
                    </div>`;
                });
                document.getElementById('watchlistContainer').innerHTML = html;
            } catch(e) {}
        }

        async function buyTrade(sym, p) {
            let res = await fetch('/api/paper/order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ symbol: sym, side: 'BUY', qty: 65, price: p })
            });
            let d = await res.json();
            alert(d.message);
        }

        loadWatchlist();
        setInterval(loadWatchlist, 4000);
    </script>
</body>
</html>
"""

# ==================== HTML 4: ORDER BOOK LADDER ====================
ORDERBOOK_LADDER_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NIFTY Order Book - The Trade Cartel</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+Gujarati:wght@600;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0e14; --panel-bg: #121824; --green: #00e676;
            --red: #ff3d71; --orange-bar: #e65100; --pulled-grey: #64748b;
            --cyan: #00f0ff; --border: #1e293b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', 'Noto Sans Gujarati', sans-serif; }
        body { background: var(--bg-color); color: #fff; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        .top-navbar { height: 48px; background: #090d16; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; flex-shrink: 0; }
        .brand-title { display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 13.5px; color: #fff; }
        .nav-links a { background: #131d2e; border: 1px solid var(--border); color: #38bdf8; padding: 4px 10px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 800; margin-left: 6px; }

        .metrics-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 12px 16px; }
        .metric-box { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; }

        .workspace-grid { display: flex; gap: 14px; padding: 0 16px 16px; }
        .ladder-panel { flex: 1.5; background: var(--panel-bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px; overflow-y: auto; max-height: calc(100vh - 250px); }
        .right-feeds-panel { flex: 1; display: flex; flex-direction: column; gap: 12px; }

        .ladder-row { display: flex; align-items: center; height: 24px; font-size: 11px; font-weight: 700; margin-bottom: 1px; }
        .ladder-row.current-price-row { background: rgba(255, 255, 255, 0.14); border-radius: 4px; }
        .bid-box { flex: 1; display: flex; justify-content: flex-end; align-items: center; padding-right: 8px; }
        .bid-fill { background: rgba(0, 230, 118, 0.85); height: 16px; border-radius: 3px 0 0 3px; display: flex; align-items: center; justify-content: flex-end; padding-right: 6px; color: #000; font-size: 10px; font-weight: 900; }
        .axis-price { width: 90px; text-align: center; color: #e2e8f0; font-family: monospace; font-size: 12.5px; font-weight: 800; }
        .ask-box { flex: 1; display: flex; justify-content: flex-start; align-items: center; padding-left: 8px; }
        .ask-fill { background: rgba(230, 81, 0, 0.9); height: 16px; border-radius: 0 3px 3px 0; display: flex; align-items: center; justify-content: flex-start; padding-left: 6px; color: #fff; font-size: 10px; font-weight: 900; }

        .feed-card { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
        .gujarati-news-footer { background: linear-gradient(90deg, #1e1b4b, #0f172a); border-top: 1.5px solid #38bdf8; padding: 8px 16px; display: flex; align-items: center; gap: 10px; font-size: 12px; font-weight: 700; }
    </style>
</head>
<body>
    <div class="top-navbar">
        <div class="brand-title"><span>🛡️</span> The Trade Cartel: Order Book Ladder</div>
        <div class="nav-links">
            <a href="/">📈 CHARTS</a>
            <a href="/fno-activity">📊 F&O ACTIVITY</a>
            <a href="/oi-analytics">⚡ OI RADAR</a>
            <a href="/paper-trading">📱 ANGEL PAPER</a>
        </div>
    </div>

    <div class="metrics-row">
        <div class="metric-box">
            <div style="font-size:11px; color:#94a3b8;">NIFTY future</div>
            <div style="font-size:20px; font-weight:900;" id="dispFutureVal">24,646.20</div>
            <div style="font-size:10px; color:#94a3b8;" id="dispFutureSub">basis +32.5 • expires 23 Nov</div>
        </div>
        <div class="metric-box">
            <div style="font-size:11px; color:#94a3b8;">Nearest Big Buyers</div>
            <div style="font-size:20px; font-weight:900; color:var(--green);" id="dispBuyersVal">24,600–24,610</div>
            <div style="font-size:10px; color:#94a3b8;">125 lots • 2.3x normal</div>
        </div>
        <div class="metric-box">
            <div style="font-size:11px; color:#94a3b8;">Nearest Big Sellers</div>
            <div style="font-size:20px; font-weight:900; color:#ff3d71;" id="dispSellersVal">24,680–24,685</div>
            <div style="font-size:10px; color:#94a3b8;">152 lots • 4.1x normal</div>
        </div>
        <div class="metric-box">
            <div style="font-size:11px; color:#94a3b8;">Liquidity</div>
            <div style="font-size:20px; font-weight:900;">Normal (85%)</div>
            <div style="font-size:10px; color:#94a3b8;">spread 7.8 pts</div>
        </div>
    </div>

    <div class="workspace-grid">
        <div class="ladder-panel">
            <div style="font-size:11.5px; font-weight:bold; margin-bottom:8px; border-bottom:1px solid var(--border); padding-bottom:6px;">Order book ladder (lots waiting, per 5 points)</div>
            <div id="ladderRowsBox"></div>
        </div>
        <div class="right-feeds-panel">
            <div class="feed-card">
                <b style="font-size:12px;">Big orders right now 🔴</b>
                <div id="bigOrdersBox" style="margin-top:6px;"></div>
            </div>
            <div class="feed-card">
                <b style="font-size:12px; color:#fbbf24;">Stop-Loss Areas (estimated) ⚠️</b>
                <div id="stopLossBox" style="margin-top:6px;"></div>
            </div>
        </div>
    </div>

    <div class="gujarati-news-footer">
        <span style="background:#ef4444; color:#fff; font-size:9.5px; padding:3px 6px; border-radius:3px; font-weight:900;">ગુજરાતી લાઈવ ન્યૂઝ</span>
        <span id="dispGujaratiNews">📢 ઓર્ડર બુક સમાચાર લોડ થઈ રહ્યા છે...</span>
    </div>

    <script>
        async function fetchLadder() {
            try {
                let res = await fetch('/api/orderbook/ladder');
                let d = await res.json();
                document.getElementById('dispFutureVal').innerText = d.future_spot;
                document.getElementById('dispFutureSub').innerText = `spot ${d.raw_spot} • basis ${d.basis} • expires ${d.expiry}`;
                document.getElementById('dispBuyersVal').innerText = d.nearest_buyers;
                document.getElementById('dispSellersVal').innerText = d.nearest_sellers;
                document.getElementById('dispGujaratiNews').innerText = d.gujarati_news;

                let lHtml = '';
                d.levels.forEach(lvl => {
                    let curCls = lvl.is_current ? 'current-price-row' : '';
                    let bidWidth = lvl.side === "BID" ? Math.min(100, (lvl.lots / 250) * 100) : 0;
                    let askWidth = lvl.side === "ASK" ? Math.min(100, (lvl.lots / 250) * 100) : 0;

                    let bidContent = lvl.side === "BID" ? `<span style="color:var(--green); font-size:10px; margin-right:4px;">${lvl.tag}</span><div class="bid-fill" style="width:${bidWidth}%;">${lvl.lots}</div>` : (lvl.tag === "Pulled-Order" ? `<span style="color:#64748b; font-size:10px;">Pulled-Order</span>` : '');
                    let askContent = lvl.side === "ASK" ? `<div class="ask-fill" style="width:${askWidth}%;">${lvl.lots}</div><span style="color:#ff3d71; font-size:10px; margin-left:4px;">${lvl.tag}</span>` : (lvl.tag === "Pulled-Order" ? `<span style="color:#64748b; font-size:10px;">Pulled-Order</span>` : '');

                    lHtml += `<div class="ladder-row ${curCls}">
                        <div class="bid-box">${bidContent}</div>
                        <div class="axis-price">${lvl.price}</div>
                        <div class="ask-box">${askContent}</div>
                    </div>`;
                });
                document.getElementById('ladderRowsBox').innerHTML = lHtml;

                let bHtml = '';
                d.big_orders.forEach(b => {
                    bHtml += `<div style="display:flex; justify-content:space-between; font-size:11px; padding:4px 0;">
                        <span style="color:${b.side==='BUY'?'var(--green)':'#ff3d71'}; font-weight:bold;">${b.side==='BUY'?'Big Buyers':'Big Sellers'} ${b.range}</span>
                        <span style="color:#94a3b8;">${b.lots}</span>
                    </div>`;
                });
                document.getElementById('bigOrdersBox').innerHTML = bHtml;

                let sHtml = '';
                d.stop_losses.forEach(s => {
                    sHtml += `<div style="display:flex; justify-content:space-between; font-size:11px; padding:4px 0;">
                        <span style="color:#ff3d71; font-weight:bold;">${s.level}</span>
                        <span style="color:#94a3b8;">${s.desc}</span>
                    </div>`;
                });
                document.getElementById('stopLossBox').innerHTML = sHtml;
            } catch(e) {}
        }
        fetchLadder();
        setInterval(fetchLadder, 3000);
    </script>
</body>
</html>
"""

# ==================== CLEAN DEDICATED ROUTE BINDINGS (ALL 5 PAGES) ====================
@app.get("/fno-activity", response_class=HTMLResponse)
def fno_page():
    return FNO_ACTIVITY_HTML

@app.get("/order-book", response_class=HTMLResponse)
def orderbook_page():
    return ORDERBOOK_LADDER_HTML

@app.get("/", response_class=HTMLResponse)
def index():
    return TERMINAL_HTML

@app.get("/oi-analytics", response_class=HTMLResponse)
def oi_page():
    return OI_DASHBOARD_HTML

@app.get("/paper-trading", response_class=HTMLResponse)
def paper_page():
    return ANGEL_APP_HTML
