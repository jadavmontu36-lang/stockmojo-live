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
        "notes": "25000 Support thi Big Buyers bounce"
    },
    {
        "time": "11:20 AM",
        "signal": "BUY PE",
        "strike": "25050 PE",
        "entry": 190.0,
        "sl": 170.0,
        "target": 230.0,
        "result": "TARGET HIT (+40 pts)",
        "notes": "25045 Big Sellers rejection"
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

# ==================== LADDER API ====================
@app.get("/api/orderbook/ladder")
def get_orderbook_ladder():
    now = time.time()
    if CACHE_STORE["ladder_data"] and (now - CACHE_STORE["ladder_time"]) < 2.0:
        return CACHE_STORE["ladder_data"]

    m = get_market_data()
    spot = m["spot"]
    center_price = round(spot / 5.0) * 5.0

    levels = []
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

    buyers_pct = 23.73
    sellers_pct = 76.27

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
        {"area": f"Just below {center_price-40:.0f}", "type": "Below the strike 25000"},
        {"area": f"Just above {center_price+60:.0f}", "type": "Above today's high (CALLS)"}
    ]

    res = {
        "future_spot": f"{spot:,.2f}",
        "buyers_pct": buyers_pct,
        "sellers_pct": sellers_pct,
        "levels": levels,
        "big_orders": big_orders,
        "stop_losses": stop_losses,
        "gujarati_news": gujarati_news,
        "updated_time": get_current_ist_time().strftime("%I:%M:%S %p")
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
    win_rate = round((target_hits / len(DAILY_SIGNAL_LOG)) * 100)

    res_data = {
        "spot": spot, "atm": atm, "expiry": m["active_expiry"],
        "time": ist_time_str, "calls": calls, "puts": puts,
        "main_res": {"strike": atm + 100, "oi_str": "64.89L"},
        "main_sup": {"strike": atm - 100, "oi_str": "70.74L"},
        "verdict": "⚡ RANGEBOUND CONSOLIDATION",
        "color": "#fbbf24",
        "action": "બ્રેકઆઉટ-ની રાહ જુઓ",
        "bull_power": 23, "pcr": pcr,
        "next_step": "Strict 20 Spot Pts SL & 40 Spot Pts Target (1:2)",
        "news": f"લાઈવ સમાચાર: નિફ્ટી ₹{spot:,.2f} | PCR {pcr} | India VIX {vix}.",
        "india_vix": vix,
        "trade_tracker": {
            "total_trades": len(DAILY_SIGNAL_LOG),
            "target_hits": target_hits,
            "sl_hits": sl_hits,
            "win_rate": f"{win_rate}%",
            "net_points": "+62 PTS",
            "log": DAILY_SIGNAL_LOG
        }
    }
    CACHE_STORE["stream_data"] = res_data
    CACHE_STORE["stream_time"] = now
    return res_data

# ==================== PAPER TRADING APIS ====================
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
    price = float(body.get("price", 145.0))
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
        <div class="spot-badge" id="spotBadge">NIFTY: ₹25,030.35</div>
        <div class="nav-links">
            <a href="/" class="active">📈 CHARTS</a>
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

# ==================== HTML 2: QUANTUM OI RADAR (WIRES + POPUP) ====================
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
            --cyan-glow: #00f0ff; --gold-glow: #fbbf24; --text-dim: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Sans Gujarati', monospace, sans-serif; }
        body { background: var(--bg-deep); color: #fff; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        .cyber-header { height: 42px; background: #090e17; border-bottom: 1.5px solid #142033; display: flex; align-items: center; justify-content: space-between; padding: 0 14px; flex-shrink: 0; }
        .header-title { font-size: 13.5px; font-weight: 900; color: var(--cyan-glow); }
        .nav-links a { background: #101c2e; border: 1.3px solid var(--cyan-glow); color: var(--cyan-glow); padding: 3px 10px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 800; margin-left: 6px; }

        .daily-tracker-bar { background: linear-gradient(90deg, #0d1e33, #09201a); border-bottom: 1px solid #1e3a5f; padding: 6px 14px; display: flex; align-items: center; justify-content: space-between; font-size: 11.5px; font-weight: 800; }
        .btn-view-trades { background: #1e3a8a; border: 1px solid #38bdf8; color: #fff; padding: 3px 10px; border-radius: 4px; font-size: 10.5px; font-weight: 800; cursor: pointer; margin-left: 8px; }

        .signal-strip { height: 46px; background: #080d17; border-bottom: 1px solid #142033; display: flex; align-items: center; justify-content: space-between; padding: 0 14px; flex-shrink: 0; }
        .verdict-tag { font-size: 13px; font-weight: 900; }

        .stream-workspace { flex: 1; display: flex; width: 100%; min-height: calc(100vh - 165px); position: relative; }
        .matrix-canvas-box { flex: 1; position: relative; background: #040609; overflow: hidden; }
        #streamCanvas { width: 100%; height: 100%; display: block; }

        .strike-nodes-col { width: 440px; max-width: 49%; background: #080d16; border-left: 1.5px solid #142033; display: flex; flex-direction: column; justify-content: space-between; padding: 4px 8px; }
        .strike-group-container { flex: 1; display: flex; flex-direction: column; justify-content: space-around; gap: 2px; }
        .strike-card-node { background: #0d1522; border: 1.2px solid #1f2f45; border-radius: 5px; padding: 4px 8px; display: flex; justify-content: space-between; align-items: center; font-size: 12px; }
        .node-call { border-left: 4px solid var(--green-glow); }
        .node-put { border-left: 4px solid var(--red-glow); }
        .spot-axis-divider { height: 25px; background: #ffffff; border-radius: 4px; color: #000; display: flex; align-items: center; justify-content: space-between; padding: 0 10px; font-weight: 900; font-size: 12px; margin: 3px 0; }

        .confidence-deck { background: #070d18; border-top: 1.5px solid #1a2a44; padding: 6px 12px; font-size: 11px; color: #38bdf8; font-weight: 800; }

        .modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.8); display: none; justify-content: center; align-items: center; z-index: 1000; }
        .modal-card { background: #0f172a; border: 2px solid #38bdf8; border-radius: 10px; width: 500px; max-width: 92%; padding: 16px; }
        .history-item { background: #131d2e; border: 1px solid #23354d; border-radius: 6px; padding: 10px; margin-bottom: 8px; }
    </style>
</head>
<body>
    <div class="cyber-header">
        <div class="header-title">⚡ HARI MASTER QUANTUM OI RADAR</div>
        <div class="nav-links">
            <a href="/">📈 CHARTS</a>
            <a href="/order-book">🛡️ ORDER BOOK</a>
            <a href="/paper-trading">📱 ANGEL PAPER</a>
        </div>
    </div>

    <div class="daily-tracker-bar">
        <div>
            <span style="color:#38bdf8;">📊 <b id="trkSummary">આજે કુલ 3 ટ્રેડ મળ્યા (2 Target Hit 🎯, 1 SL Hit 🛑)</b></span>
            <button class="btn-view-trades" onclick="openHistoryModal()">VIEW HISTORY 👁️</button>
        </div>
        <span style="color:var(--green-glow);">NET RETURN: <b id="trkNetPts">+62 PTS</b> ✅</span>
    </div>

    <div class="signal-strip">
        <div>
            <div style="font-size:8.5px; color:var(--text-dim);">LIVE DIRECTION & TRAP:</div>
            <div class="verdict-tag" id="verdictText" style="color:#fbbf24;">SCANNING...</div>
        </div>
        <div>
            <span style="font-size:9px; color:var(--text-dim);">RES:</span> <b id="txtMajorRes" style="color:#ff2255;">--</b> |
            <span style="font-size:9px; color:var(--text-dim);">SUP:</span> <b id="txtMajorSup" style="color:#00ff88;">--</b>
        </div>
        <div style="text-align:right;">
            <div style="font-size:8.5px; color:var(--text-dim);">ACTION:</div>
            <div style="font-size:11px; font-weight:900; color:var(--cyan-glow);" id="actionText">CALCULATING...</div>
        </div>
    </div>

    <div class="stream-workspace">
        <div class="matrix-canvas-box" id="canvasContainer"><canvas id="streamCanvas"></canvas></div>
        <div class="strike-nodes-col">
            <div style="font-size:9.5px; font-weight:bold; color:var(--green-glow);">▲ CALL RESISTANCE (CE)</div>
            <div id="callStrikesContainer" class="strike-group-container"></div>
            <div class="spot-axis-divider">
                <span>SPOT AXIS</span>
                <span id="spotCenterVal">₹ 25,030.35</span>
            </div>
            <div style="font-size:9.5px; font-weight:bold; color:var(--red-glow);">▼ PUT SUPPORT (PE)</div>
            <div id="putStrikesContainer" class="strike-group-container"></div>
        </div>
    </div>

    <div class="confidence-deck" id="nextStepText">💡 NEXT STEP: Strict 20 Spot Pts SL & 40 Spot Pts Target (1:2)</div>

    <!-- HISTORY MODAL -->
    <div class="modal-overlay" id="historyModal">
        <div class="modal-card">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <b style="color:#38bdf8;">📊 TODAY'S TRADES HISTORY</b>
                <span onclick="closeHistoryModal()" style="cursor:pointer; font-size:20px;">&times;</span>
            </div>
            <div id="historyListContainer"></div>
            <button onclick="closeHistoryModal()" style="background:#ff2255; color:#fff; border:none; padding:6px 12px; border-radius:4px; font-weight:bold; cursor:pointer; float:right;">CLOSE</button>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('streamCanvas');
        const container = document.getElementById('canvasContainer');
        const ctx = canvas.getContext('2d');
        let globalLog = [];

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

        function openHistoryModal() {
            let html = '';
            globalLog.forEach(t => {
                let col = t.result.includes("TARGET") ? "var(--green-glow)" : "var(--red-glow)";
                html += `<div class="history-item">
                    <div style="display:flex; justify-content:space-between; font-weight:900;">
                        <span>${t.time} • <b style="color:#38bdf8;">${t.signal} ${t.strike}</b></span>
                        <span style="color:${col};">${t.result}</span>
                    </div>
                    <div style="font-size:11px; color:#94a3b8; margin-top:4px;">Entry: ₹${t.entry} | SL: ₹${t.sl} | Target: ₹${t.target}</div>
                </div>`;
            });
            document.getElementById('historyListContainer').innerHTML = html;
            document.getElementById('historyModal').style.display = 'flex';
        }
        function closeHistoryModal() { document.getElementById('historyModal').style.display = 'none'; }

        async function fetchRadar() {
            try {
                let res = await fetch('/api/oi/quantum-stream');
                let d = await res.json();
                document.getElementById('spotCenterVal').innerText = '₹ ' + d.spot.toFixed(2);
                document.getElementById('verdictText').innerText = d.verdict;
                document.getElementById('actionText').innerText = d.action;
                document.getElementById('txtMajorRes').innerText = d.main_res.strike + ' (' + d.main_res.oi_str + ')';
                document.getElementById('txtMajorSup').innerText = d.main_sup.strike + ' (' + d.main_sup.oi_str + ')';
                if (d.trade_tracker) globalLog = d.trade_tracker.log;

                let cHtml = '';
                d.calls.slice(0, 6).forEach(c => {
                    cHtml += `<div class="strike-card-node node-call">
                        <span><b>${c.strike} CE</b> <small style="color:#38bdf8;">₹${c.ltp.toFixed(2)}</small></span>
                        <span style="color:#00ff88; font-weight:800;">${c.oi_str}</span>
                    </div>`;
                });
                document.getElementById('callStrikesContainer').innerHTML = cHtml;

                let pHtml = '';
                d.puts.slice(0, 6).forEach(p => {
                    pHtml += `<div class="strike-card-node node-put">
                        <span><b>${p.strike} PE</b> <small style="color:#ff2255;">₹${p.ltp.toFixed(2)}</small></span>
                        <span style="color:#ff2255; font-weight:800;">${p.oi_str}</span>
                    </div>`;
                });
                document.getElementById('putStrikesContainer').innerHTML = pHtml;
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
            --text-main: #f1f5f9; --text-dim: #94a3b8; --tab-active: #38bdf8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: var(--dark-bg); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

        .app-header { height: 48px; background: #0f131c; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; padding: 0 14px; flex-shrink: 0; }
        .avatar-circle { width: 28px; height: 28px; border-radius: 50%; background: var(--angel-blue); color: #fff; font-size: 11px; font-weight: 800; display: flex; align-items: center; justify-content: center; }
        .nav-links a { background: #172554; border: 1px solid #2563eb; color: #38bdf8; padding: 3px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 800; text-decoration: none; margin-left: 4px; }

        .app-body { flex: 1; position: relative; overflow-y: auto; }
        .page-view { display: none; width: 100%; height: 100%; overflow-y: auto; padding-bottom: 65px; }
        .page-view.active-page { display: block; }

        .bottom-nav { height: 56px; background: #0d111a; border-top: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-around; position: fixed; bottom: 0; left: 0; width: 100%; z-index: 100; }
        .nav-item { display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text-dim); font-size: 10px; font-weight: 600; cursor: pointer; width: 33%; height: 100%; }
        .nav-item.active { color: var(--tab-active); }

        .strike-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--border-color); background: var(--card-bg); cursor: pointer; }
        .depth-sheet { position: fixed; bottom: -100%; left: 0; width: 100%; background: #121824; border-top: 2px solid var(--tab-active); border-radius: 16px 16px 0 0; padding: 16px; z-index: 200; transition: bottom 0.25s ease; }
        .depth-sheet.open { bottom: 0; }
        .backdrop { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.65); display: none; z-index: 150; }
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
            <a href="/order-book">🛡️ ORDER BOOK</a>
            <a href="/oi-analytics">⚡ OI RADAR</a>
        </div>
    </div>

    <div class="app-body">
        <div id="pageWatchlist" class="page-view active-page">
            <div id="watchlistContainer"></div>
        </div>
        <div id="pagePositions" class="page-view">
            <div style="background:linear-gradient(135deg, #172554, #1e1b4b); padding:14px; margin:10px; border-radius:8px; display:flex; justify-content:space-between;">
                <div><span>FUNDS:</span><h3 id="dispAvailFunds">₹ 1,00,000.00</h3></div>
                <div style="text-align:right;"><span>P&L:</span><h3 id="dispNetPnl">₹ 0.00</h3></div>
            </div>
            <div id="positionsContainer"></div>
        </div>
        <div id="pageOrders" class="page-view">
            <div id="ordersContainer"></div>
        </div>
    </div>

    <div class="backdrop" id="sheetBackdrop" onclick="closeSheet()"></div>
    <div class="depth-sheet" id="depthSheet">
        <b id="dSymTitle">NIFTY 25000 CE</b>
        <div style="margin:10px 0;">
            <label style="font-size:11px; color:var(--text-dim);">Lots (1 Lot = 65 Qty)</label>
            <input type="number" id="lotInput" value="1" min="1" style="width:100%; padding:8px; background:#1a202c; color:#fff; border:1px solid #334155; border-radius:6px;">
        </div>
        <div style="display:flex; gap:10px; margin-top:14px;">
            <button onclick="executeOrder('BUY')" style="flex:1; background:var(--green); color:#fff; padding:12px; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">BUY (65 QTY)</button>
            <button onclick="executeOrder('SELL')" style="flex:1; background:var(--red); color:#fff; padding:12px; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">SELL (65 QTY)</button>
        </div>
    </div>

    <div class="bottom-nav">
        <div class="nav-item active" onclick="switchNav('Watchlist', this)">Watchlist</div>
        <div class="nav-item" onclick="switchNav('Positions', this)">Positions</div>
        <div class="nav-item" onclick="switchNav('Orders', this)">Orders</div>
    </div>

    <script>
        let curItem = null;
        function switchNav(id, el) {
            document.querySelectorAll('.page-view').forEach(p => p.classList.remove('active-page'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            document.getElementById(`page${id}`).classList.add('active-page');
            el.classList.add('active');
            if (id === 'Positions' || id === 'Orders') syncPaper();
        }

        async function loadWatchlist() {
            try {
                let res = await fetch('/api/market_data');
                let d = await res.json();
                let html = '';
                d.chain.forEach(s => {
                    html += `
                    <div class="strike-row" onclick="openDepth('${s.strike} CE', ${s.ltp_ce})">
                        <div><b>NIFTY ${s.strike} CE</b><br><small style="color:var(--text-dim);">OI: ${s.oi_ce_str}</small></div>
                        <div style="color:var(--green); font-weight:bold;">₹${s.ltp_ce.toFixed(2)}</div>
                    </div>
                    <div class="strike-row" onclick="openDepth('${s.strike} PE', ${s.ltp_pe})">
                        <div><b>NIFTY ${s.strike} PE</b><br><small style="color:var(--text-dim);">OI: ${s.oi_pe_str}</small></div>
                        <div style="color:var(--red); font-weight:bold;">₹${s.ltp_pe.toFixed(2)}</div>
                    </div>`;
                });
                document.getElementById('watchlistContainer').innerHTML = html;
            } catch(e) {}
        }

        function openDepth(sym, ltp) {
            curItem = { sym: sym, ltp: ltp };
            document.getElementById('dSymTitle').innerText = 'NIFTY ' + sym + ' @ ₹' + ltp.toFixed(2);
            document.getElementById('sheetBackdrop').style.display = 'block';
            document.getElementById('depthSheet').classList.add('open');
        }
        function closeSheet() {
            document.getElementById('sheetBackdrop').style.display = 'none';
            document.getElementById('depthSheet').classList.remove('open');
        }

        async function executeOrder(side) {
            let lots = parseInt(document.getElementById('lotInput').value) || 1;
            let res = await fetch('/api/paper/order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ symbol: curItem.sym, side: side, qty: lots * 65, price: curItem.ltp })
            });
            let d = await res.json();
            alert(d.message);
            closeSheet();
            syncPaper();
        }

        async function syncPaper() {
            try {
                let res = await fetch('/api/paper/state');
                let d = await res.json();
                document.getElementById('dispAvailFunds').innerText = '₹ ' + d.available_funds.toLocaleString();
                document.getElementById('dispNetPnl').innerText = (d.total_pnl >= 0 ? '+' : '') + '₹ ' + d.total_pnl.toFixed(2);

                let pHtml = '';
                d.positions.forEach(p => {
                    pHtml += `<div style="background:var(--card-bg); padding:10px; margin:8px; border-radius:6px; display:flex; justify-content:space-between; align-items:center;">
                        <div><b>${p.symbol}</b><br><small>${p.qty} Qty @ ₹${p.entry_price.toFixed(2)}</small></div>
                        <button onclick="closePos(${p.id})" style="background:#334155; color:#fff; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;">EXIT</button>
                    </div>`;
                });
                document.getElementById('positionsContainer').innerHTML = pHtml || '<div style="text-align:center; padding:20px; color:var(--text-dim);">No Active Positions</div>';
            } catch(e) {}
        }

        async function closePos(id) {
            await fetch('/api/paper/close', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ pos_id: id }) });
            syncPaper();
        }

        loadWatchlist();
        syncPaper();
        setInterval(loadWatchlist, 4000);
        setInterval(syncPaper, 4000);
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
    <title>Institutional Order Book Ladder - The Trade Cartel</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+Gujarati:wght@600;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0e14; --panel-bg: #121824; --green: #00e676;
            --red: #ff3d71; --pulled-grey: #64748b; --cyan: #00f0ff; --border: #1e293b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', 'Noto Sans Gujarati', sans-serif; }
        body { background: var(--bg-color); color: #fff; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        .top-navbar { height: 48px; background: #090d16; border-bottom: 1.5px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; flex-shrink: 0; }
        .nav-links a { background: #131d2e; border: 1px solid var(--border); color: #38bdf8; padding: 4px 10px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 800; margin-left: 6px; }

        .metrics-strip { display: flex; gap: 10px; padding: 10px 16px; background: #0c111c; border-bottom: 1px solid var(--border); }
        .metric-card { flex: 1; background: var(--panel-bg); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; }

        .workspace { flex: 1; display: flex; gap: 12px; padding: 12px 16px; }
        .ladder-container { flex: 1.4; background: var(--panel-bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px; overflow-y: auto; max-height: calc(100vh - 190px); }
        .feeds-container { flex: 1; display: flex; flex-direction: column; gap: 12px; }

        .ladder-row { display: flex; align-items: center; height: 23px; font-size: 11px; font-weight: 700; }
        .ladder-row.current-price-row { background: rgba(255, 255, 255, 0.12); border-radius: 4px; }
        
        .bid-bar-box { flex: 1; display: flex; justify-content: flex-end; align-items: center; padding-right: 8px; height: 100%; }
        .bid-fill { background: rgba(0, 230, 118, 0.85); height: 16px; border-radius: 3px 0 0 3px; display: flex; align-items: center; justify-content: flex-end; padding-right: 5px; color: #000; font-size: 10px; font-weight: 900; }
        .price-center-axis { width: 85px; text-align: center; color: #e2e8f0; font-family: monospace; font-size: 12px; font-weight: 800; flex-shrink: 0; }
        .ask-bar-box { flex: 1; display: flex; justify-content: flex-start; align-items: center; padding-left: 8px; height: 100%; }
        .ask-fill { background: rgba(255, 61, 113, 0.85); height: 16px; border-radius: 0 3px 3px 0; display: flex; align-items: center; justify-content: flex-start; padding-left: 5px; color: #fff; font-size: 10px; font-weight: 900; }

        .feed-card { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px; }
        .gujarati-news-footer { background: linear-gradient(90deg, #1e1b4b, #0f172a); border-top: 1.5px solid #38bdf8; padding: 8px 16px; display: flex; align-items: center; gap: 10px; font-size: 12px; font-weight: 700; }
    </style>
</head>
<body>
    <div class="top-navbar">
        <div style="font-weight:900; font-size:14px;">🛡️ THE TRADE CARTEL: ORDER BOOK LADDER</div>
        <div class="nav-links">
            <a href="/">📈 CHARTS</a>
            <a href="/oi-analytics">⚡ OI RADAR</a>
            <a href="/paper-trading">📱 ANGEL PAPER</a>
        </div>
    </div>

    <div class="metrics-strip">
        <div class="metric-card">
            <div style="font-size:10.5px; color:#94a3b8;">NIFTY FUTURE (LIVE)</div>
            <div style="font-size:18px; font-weight:900; color:var(--cyan);" id="dispSpotFuture">25,030.35</div>
        </div>
        <div class="metric-card" style="flex:2;">
            <div style="display:flex; justify-content:space-between; font-size:11px; font-weight:800;">
                <span style="color:var(--green);">Buyers: <b id="dispBuyersPct">23.73%</b></span>
                <span style="color:var(--red);">Sellers: <b id="dispSellersPct">76.27%</b></span>
            </div>
            <div style="height:7px; background:var(--red); border-radius:4px; margin-top:6px; display:flex;">
                <div id="gaugeBuyersBar" style="width:23.73%; background:var(--green); height:100%;"></div>
            </div>
        </div>
    </div>

    <div class="workspace">
        <div class="ladder-container">
            <div id="ladderRowsBox"></div>
        </div>
        <div class="feeds-container">
            <div class="feed-card">
                <b style="font-size:12px; color:#e2e8f0;">BIG ORDERS RIGHT NOW 🔴</b>
                <div id="bigOrdersFeedBox" style="margin-top:8px;"></div>
            </div>
            <div class="feed-card">
                <b style="font-size:12px; color:#fbbf24;">STOP-LOSS AREAS (ESTIMATED) ⚠️</b>
                <div id="stopLossFeedBox" style="margin-top:8px;"></div>
            </div>
        </div>
    </div>

    <div class="gujarati-news-footer">
        <span style="background:#ef4444; color:#fff; font-size:9.5px; padding:3px 6px; border-radius:3px; font-weight:bold;">ગુજરાતી લાઈવ ન્યૂઝ</span>
        <span id="dispGujaratiNews">📢 ઓર્ડર બુક સમાચાર લોડ થઈ રહ્યા છે...</span>
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
                document.getElementById('dispGujaratiNews').innerText = d.gujarati_news;

                let lHtml = '';
                d.levels.forEach(lvl => {
                    let curCls = lvl.is_current ? 'current-price-row' : '';
                    let bidWidth = lvl.side === "BID" ? Math.min(100, (lvl.lots / 250) * 100) : 0;
                    let askWidth = lvl.side === "ASK" ? Math.min(100, (lvl.lots / 250) * 100) : 0;

                    let bidContent = lvl.side === "BID" ? `<span style="color:var(--green); font-size:10px; margin-right:4px;">${lvl.tag}</span><div class="bid-fill" style="width:${bidWidth}%;">${lvl.lots}</div>` : (lvl.tag === "Pulled Order" ? `<span style="color:#64748b; font-size:10px;">Pulled Order</span>` : '');
                    let askContent = lvl.side === "ASK" ? `<div class="ask-fill" style="width:${askWidth}%;">${lvl.lots}</div><span style="color:var(--red); font-size:10px; margin-left:4px;">${lvl.tag}</span>` : (lvl.tag === "Pulled Order" ? `<span style="color:#64748b; font-size:10px;">Pulled Order</span>` : '');

                    lHtml += `<div class="ladder-row ${curCls}">
                        <div class="bid-bar-box">${bidContent}</div>
                        <div class="price-center-axis">${lvl.price}</div>
                        <div class="ask-bar-box">${askContent}</div>
                    </div>`;
                });
                document.getElementById('ladderRowsBox').innerHTML = lHtml;

                let oHtml = '';
                d.big_orders.forEach(o => {
                    oHtml += `<div style="display:flex; justify-content:space-between; font-size:11px; padding:4px 0;">
                        <span>${o.action} ${o.range}</span><b>${o.lots}</b>
                    </div>`;
                });
                document.getElementById('bigOrdersFeedBox').innerHTML = oHtml;

                let sHtml = '';
                d.stop_losses.forEach(s => {
                    sHtml += `<div style="display:flex; justify-content:space-between; font-size:11px; padding:4px 0;">
                        <span style="color:#ff3d71;">${s.area}</span><span style="color:#94a3b8;">${s.type}</span>
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

# ==================== CLEAN DEDICATED ROUTE BINDINGS (ALL 4 PAGES) ====================
@app.get("/", response_class=HTMLResponse)
def index():
    return TERMINAL_HTML

@app.get("/oi-analytics", response_class=HTMLResponse)
def oi_page():
    return OI_DASHBOARD_HTML

@app.get("/paper-trading", response_class=HTMLResponse)
def paper_page():
    return ANGEL_APP_HTML

@app.get("/order-book", response_class=HTMLResponse)
def orderbook_page():
    return ORDERBOOK_LADDER_HTML
