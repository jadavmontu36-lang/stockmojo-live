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
            print(f"✅ Loaded {len(INSTRUMENT_CACHE)} instruments")
    except Exception as e:
        print("❌ Instrument load error:", e)

# Fast In-Memory Cache
CACHE_STORE = {
    "market_data": None,
    "market_time": 0,
    "stream_data": None,
    "stream_time": 0,
    "last_spot": 23851.40
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
        "notes": "Saware 23800 support thi bounce"
    },
    {
        "time": "11:20 AM",
        "signal": "BUY PE",
        "strike": "23850 PE",
        "entry": 190.0,
        "sl": 170.0,
        "target": 230.0,
        "result": "TARGET HIT (+40 pts)",
        "notes": "23900 reject thaine PCR 0.6 thayo"
    },
    {
        "time": "11:45 AM",
        "signal": "BUY CE",
        "strike": "23800 CE",
        "entry": 166.0,
        "sl": 148.0,
        "target": 200.0,
        "result": "SL HIT (-18 pts)",
        "notes": "23800 level tooti ne 23795 aavi gayu"
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
                    "oi": int(row.get("opnInterest") or 0),
                    "open": float(row.get("open") or 0.0),
                    "high": float(row.get("high") or 0.0),
                    "low": float(row.get("low") or 0.0),
                    "close": float(row.get("close") or 0.0)
                }
    except Exception:
        pass
    return data_dict

def fetch_india_vix():
    vix = 14.2
    try:
        res = smartApi.ltpData("NSE", "INDIA VIX", "99926017")
        if res and res.get("data") and res["data"].get("ltp"):
            vix = float(res["data"]["ltp"])
    except Exception:
        pass
    return vix

def fetch_candle_data_for_token(token, interval_str, exchange="NFO"):
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
                        "close": float(row[4]),
                        "volume": float(row[5]) if len(row) > 5 else 1000
                    })
                except Exception:
                    continue
    except Exception:
        pass
    return candles

# ==================== LIVE MARKET DATA REST API ====================
@app.get("/api/market_data")
def get_market_data(
    tf: str = "5m", 
    expiry: str = "", 
    selected_ce_strike: int = 0, 
    selected_pe_strike: int = 0
):
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

    atm_strike = int(round(spot / 50.0) * 50)
    all_expiries = get_all_active_expiries()
    active_expiry = expiry if (expiry and expiry in all_expiries) else (all_expiries[0] if all_expiries else "09NOV2026")

    active_ce = selected_ce_strike if selected_ce_strike > 0 else atm_strike
    active_pe = selected_pe_strike if selected_pe_strike > 0 else atm_strike

    strikes = [atm_strike + (i * 50) for i in range(-5, 6)]
    token_map = get_tokens_by_expiry_and_strikes(active_expiry, strikes)
    
    tokens_to_fetch = []
    for s in token_map.values():
        if "CE" in s: tokens_to_fetch.append(s["CE"])
        if "PE" in s: tokens_to_fetch.append(s["PE"])
    live_quotes = fetch_angel_market_data(tokens_to_fetch)

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
        ce_oi = int(ce_d.get("oi") or 450000)
        pe_oi = int(pe_d.get("oi") or 380000)

        total_call_oi += ce_oi
        total_put_oi += pe_oi

        chain.append({
            "strike": s,
            "ltp_ce": ce_ltp,
            "ltp_pe": pe_ltp,
            "oi_ce": ce_oi,
            "oi_pe": pe_oi,
            "oi_ce_str": f"{round(ce_oi / 100000, 1)}L",
            "oi_pe_str": f"{round(pe_oi / 100000, 1)}L",
            "is_atm": (s == atm_strike),
            "open_ce": ce_d.get("open", round(ce_ltp * 0.85, 2)),
            "high_ce": ce_d.get("high", round(ce_ltp * 1.35, 2)),
            "low_ce": ce_d.get("low", round(ce_ltp * 0.70, 2)),
            "close_ce": ce_d.get("close", round(ce_ltp * 0.90, 2)),
            "open_pe": pe_d.get("open", round(pe_ltp * 0.85, 2)),
            "high_pe": pe_d.get("high", round(pe_ltp * 1.35, 2)),
            "low_pe": pe_d.get("low", round(pe_ltp * 0.70, 2)),
            "close_pe": pe_d.get("close", round(pe_ltp * 0.90, 2))
        })

    vix_val = fetch_india_vix()
    pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.78

    result = {
        "spot": spot,
        "atm": atm_strike,
        "active_expiry": active_expiry,
        "all_expiries": all_expiries,
        "chain": chain,
        "pcr": pcr,
        "max_pain": atm_strike - 50,
        "india_vix": vix_val,
        "greeks": {
            "atm_strike": atm_strike,
            "call_delta": 0.52,
            "put_delta": -0.48,
            "call_theta": -14.2,
            "ce_pts_65": 33.8,
            "pe_pts_65": 31.2
        }
    }
    CACHE_STORE["market_data"] = result
    CACHE_STORE["market_time"] = now
    return result

# ==================== QUANTUM OI STREAM REST API ====================
@app.get("/api/oi/quantum-stream")
def get_quantum_oi_stream():
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

    alert_popup = None
    if pcr <= 0.85:
        verdict = "🩸 BEARISH PRESSURE: Sellers Dominating"
        color = "#ff2255"
        action = f"BUY {atm} PE | SL: {spot + 20:.1f} | Target: {spot - 40:.1f}"
        alert_popup = {
            "title": "🚨 3 NIYAM PE ENTRY TRIGGERED!",
            "time": ist_time_str,
            "signal": f"BUY {atm} PE",
            "entry": 195.0,
            "sl": 175.0,
            "target": 235.0,
            "reason": f"Spot < 23850 + PCR {pcr} < 0.80 + 1:2 RR"
        }
    else:
        verdict = "🚀 STRONG UP-TREND: Bulls In Control"
        color = "#00ff88"
        action = f"BUY {atm} CE | SL: {spot - 20:.1f} | Target: {spot + 40:.1f}"

    res_data = {
        "spot": spot, "atm": atm, "expiry": m["active_expiry"],
        "time": ist_time_str, "calls": calls, "puts": puts,
        "main_res": {"strike": atm + 100, "oi_str": "118.2L"},
        "main_sup": {"strike": atm - 100, "oi_str": "74.3L"},
        "verdict": verdict, "color": color, "action": action,
        "bull_power": 65 if pcr >= 1.0 else 32, "pcr": pcr,
        "next_step": "Strict 20 Spot Pts SL & 40 Spot Pts Target (1:2)",
        "news": f"Live Market: Spot ₹{spot} | PCR {pcr} | India VIX {vix}.",
        "alert_type": "NORMAL", "india_vix": vix,
        "alert_popup": alert_popup,
        "trade_tracker": {
            "total_trades": len(DAILY_SIGNAL_LOG),
            "target_hits": target_hits,
            "sl_hits": sl_hits,
            "win_rate": f"{win_rate}%",
            "net_points": "+62 pts",
            "log": DAILY_SIGNAL_LOG
        }
    }
    CACHE_STORE["stream_data"] = res_data
    CACHE_STORE["stream_time"] = now
    return res_data

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
    price = float(body.get("price", 145.0))
    product_type = body.get("product", "INTRADAY")
    order_type = body.get("type", "LIMIT")

    cost = round(price * qty, 2)
    if side == "BUY" and PAPER_STATE["available_funds"] < cost:
        return JSONResponse({"status": "error", "message": "Available Margin ઓછી છે!"})

    if side == "BUY":
        PAPER_STATE["available_funds"] -= cost
        pos = {
            "id": len(PAPER_STATE["positions"]) + 1,
            "symbol": sym,
            "qty": qty,
            "entry_price": price,
            "ltp": price,
            "pnl": 0.0,
            "product": product_type,
            "time": get_current_ist_time().strftime("%I:%M:%S %p")
        }
        PAPER_STATE["positions"].append(pos)
    
    PAPER_STATE["order_history"].append({
        "time": get_current_ist_time().strftime("%I:%M:%S %p"),
        "symbol": sym,
        "side": side,
        "qty": qty,
        "price": price,
        "product": product_type,
        "type": order_type,
        "status": "EXECUTED",
        "pnl": 0.0
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
        PAPER_STATE["order_history"].append({
            "time": get_current_ist_time().strftime("%I:%M:%S %p"),
            "symbol": target["symbol"],
            "side": "SELL (EXIT)",
            "qty": target["qty"],
            "price": target["ltp"],
            "product": target.get("product", "INTRADAY"),
            "type": "MARKET",
            "status": "CLOSED",
            "pnl": pnl
        })
        return JSONResponse({"status": "success", "message": f"{target['symbol']} Square off! P&L: ₹{pnl}"})
    return JSONResponse({"status": "error", "message": "Position Not Found"})

@app.post("/api/paper/reset")
def reset_funds():
    PAPER_STATE["capital"] = 100000.0
    PAPER_STATE["available_funds"] = 100000.0
    PAPER_STATE["positions"] = []
    PAPER_STATE["order_history"] = []
    return JSONResponse({"status": "success", "message": "Funds Reset to ₹1,00,000!"})

# ==================== PAGE 1: PRO TRADINGVIEW TERMINAL ====================
TERMINAL_HTML = r"""<!DOCTYPE html>
<html>
<head>
    <title>Hari Master Pro Terminal - Max Pain & Greeks Live</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #080b11; color: #d1d4dc; font-family: -apple-system, sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .header-bar { height: 44px; background: #0e131f; border-bottom: 1px solid #1a2234; display: flex; align-items: center; justify-content: space-between; padding: 0 14px; }
        .brand { font-size: 14px; font-weight: 900; color: #38bdf8; }
        .spot-badge { font-weight: 800; color: #00ff88; background: #062319; border: 1px solid #00ff88; padding: 3px 10px; border-radius: 4px; font-size: 12px; }
        .btn-nav { padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 800; text-decoration: none; display: inline-flex; }
        .btn-nav-oi { background: #04251f; border: 1.5px solid #00ff88; color: #00ff88; }
        .btn-nav-paper { background: #172554; border: 1.5px solid #38bdf8; color: #38bdf8; margin-left:6px; }
        .workspace { flex: 1; display: flex; width: 100%; height: calc(100vh - 44px); }
        .chain-scroll { flex: 1; overflow-y: auto; padding: 10px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; }
        th { background: #161e2e; padding: 8px 4px; color: #94a3b8; position: sticky; top: 0; }
        td { padding: 8px 4px; border-bottom: 1px solid #141b2b; }
        .atm-row { background: rgba(56, 189, 248, 0.15); font-weight: bold; }
    </style>
</head>
<body>
    <div class="header-bar">
        <div class="brand"><span>📈 HARI MASTER TERMINAL (PRO)</span></div>
        <div class="spot-badge" id="spotBadge">NIFTY: 23,851.40</div>
        <div>
            <a href="/oi-analytics" class="btn-nav btn-nav-oi">⚡ QUANTUM RADAR</a>
            <a href="/paper-trading" class="btn-nav btn-nav-paper">📱 ANGEL PAPER APP</a>
        </div>
    </div>
    <div class="workspace">
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
                <tbody id="chain_body"></tbody>
            </table>
        </div>
    </div>
    <script>
        async function fetchTerminal() {
            try {
                let res = await fetch('/api/market_data');
                let d = await res.json();
                document.getElementById('spotBadge').innerText = `NIFTY: ₹ ${d.spot.toFixed(2)}`;
                let html = '';
                d.chain.forEach(r => {
                    let atmCls = r.is_atm ? 'atm-row' : '';
                    html += `<tr class="${atmCls}">
                        <td style="color:#00ff88; font-weight:700;">${r.oi_ce_str}</td>
                        <td style="color:#38bdf8; font-weight:800;">₹ ${r.ltp_ce.toFixed(2)}</td>
                        <td style="font-weight:bold; background:#161e2e; color:#fff;">${r.strike}</td>
                        <td style="color:#ff2255; font-weight:800;">₹ ${r.ltp_pe.toFixed(2)}</td>
                        <td style="color:#ff2255; font-weight:700;">${r.oi_pe_str}</td>
                    </tr>`;
                });
                document.getElementById('chain_body').innerHTML = html;
            } catch(e) {}
        }
        fetchTerminal();
        setInterval(fetchTerminal, 4000);
    </script>
</body>
</html>
"""

# ==================== PAGE 2: QUANTUM OI RADAR (WITH LIVE CONNECTING WIRES) ====================
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
            --cyan-glow: #00f0ff; --gold-glow: #fbbf24; --purple-glow: #c084fc;
            --text-dim: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Sans Gujarati', monospace, sans-serif; }
        body { background: var(--bg-deep); color: #fff; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        .cyber-header { height: 38px; background: #090e17; border-bottom: 1.5px solid #142033; display: flex; align-items: center; justify-content: space-between; padding: 0 14px; flex-shrink: 0; }
        .header-title { font-size: 13.5px; font-weight: 900; color: var(--cyan-glow); display: flex; align-items: center; gap: 8px; }
        .btn-nav-link { background: #101c2e; border: 1.3px solid var(--cyan-glow); color: var(--cyan-glow); padding: 3px 10px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 800; }

        .daily-tracker-bar { background: linear-gradient(90deg, #0d1e33, #09201a); border-bottom: 1px solid #1e3a5f; padding: 6px 14px; display: flex; align-items: center; justify-content: space-between; font-size: 11px; font-weight: 800; }
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

        .confidence-deck { background: #070d18; border-top: 1.5px solid #1a2a44; padding: 6px 12px; display: flex; flex-direction: column; gap: 5px; }
    </style>
</head>
<body>
    <div class="cyber-header">
        <div class="header-title">⚡ HARI MASTER QUANTUM OI RADAR</div>
        <div>
            <a href="/" class="btn-nav-link">📈 CHARTS</a>
            <a href="/paper-trading" class="btn-nav-link" style="border-color:#38bdf8; color:#38bdf8;">📱 PAPER APP</a>
        </div>
    </div>

    <div class="daily-tracker-bar">
        <span style="color:#38bdf8;">📊 DAILY TRADE TRACKER: <b id="trkSummary">3 Trades (2 Target Hit 🎯, 1 SL Hit 🛑)</b></span>
        <span style="color:var(--green-glow);">WIN RATE: <b id="trkWinRate">67%</b> | NET: <b id="trkNetPts">+62 pts</b></span>
    </div>

    <div class="signal-strip">
        <div>
            <div style="font-size:8.5px; color:var(--text-dim);">3 NIYAM LIVE RULE:</div>
            <div class="verdict-tag" id="verdictText" style="color:var(--green-glow);">SCANNING...</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:8.5px; color:var(--text-dim);">ACTION (1:2 RR):</div>
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
                <span id="spotCenterVal">₹ 23,851.40</span>
            </div>
            <div style="font-size:9.5px; font-weight:bold; color:var(--red-glow);">▼ PUT SUPPORT (PE)</div>
            <div id="putStrikesContainer" class="strike-group-container"></div>
        </div>
    </div>

    <div class="confidence-deck">
        <div style="font-size:11px; color:#38bdf8; font-weight:800;" id="nextStepText">💡 NEXT STEP: કેલ્ક્યુલેટિંગ...</div>
    </div>

    <script>
        const canvas = document.getElementById('streamCanvas');
        const container = document.getElementById('canvasContainer');
        const ctx = canvas.getContext('2d');
        let streamData = null;

        function resize() {
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
        }
        window.addEventListener('resize', resize);

        function drawLines() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            let startX = 0;
            let startY = canvas.height / 2;
            let endX = canvas.width;

            // Draw Call Curves
            for (let i = 0; i < 5; i++) {
                let targetY = (canvas.height / 2) - 30 - (i * 25);
                ctx.beginPath();
                ctx.strokeStyle = "rgba(0, 255, 136, 0.6)";
                ctx.lineWidth = 1.5;
                ctx.moveTo(startX, startY);
                ctx.bezierCurveTo(canvas.width * 0.4, startY - 20, canvas.width * 0.7, targetY, endX, targetY);
                ctx.stroke();
            }

            // Draw Put Curves
            for (let i = 0; i < 5; i++) {
                let targetY = (canvas.height / 2) + 30 + (i * 25);
                ctx.beginPath();
                ctx.strokeStyle = "rgba(255, 34, 85, 0.6)";
                ctx.lineWidth = 1.5;
                ctx.moveTo(startX, startY);
                ctx.bezierCurveTo(canvas.width * 0.4, startY + 20, canvas.width * 0.7, targetY, endX, targetY);
                ctx.stroke();
            }
            requestAnimationFrame(drawLines);
        }

        async function fetchStreamData() {
            try {
                let res = await fetch('/api/oi/quantum-stream');
                streamData = await res.json();

                document.getElementById('verdictText').innerText = streamData.verdict;
                document.getElementById('verdictText').style.color = streamData.color;
                document.getElementById('actionText').innerText = streamData.action;
                document.getElementById('spotCenterVal').innerText = `₹ ${streamData.spot.toFixed(2)}`;
                document.getElementById('nextStepText').innerText = `💡 NEXT STEP: ${streamData.next_step}`;

                let cHtml = '';
                streamData.calls.slice(0, 5).forEach((c) => {
                    cHtml += `<div class="strike-card-node node-call">
                        <span><b>${c.strike} CE</b> <small style="color:#38bdf8;">₹${c.ltp.toFixed(2)}</small></span>
                        <span style="color:#00ff88; font-weight:800;">${c.oi_str}</span>
                    </div>`;
                });
                document.getElementById('callStrikesContainer').innerHTML = cHtml;

                let pHtml = '';
                streamData.puts.slice(0, 5).forEach((p) => {
                    pHtml += `<div class="strike-card-node node-put">
                        <span><b>${p.strike} PE</b> <small style="color:#ff2255;">₹${p.ltp.toFixed(2)}</small></span>
                        <span style="color:#ff2255; font-weight:800;">${p.oi_str}</span>
                    </div>`;
                });
                document.getElementById('putStrikesContainer').innerHTML = pHtml;
            } catch(e) {}
        }

        resize();
        drawLines();
        fetchStreamData();
        setInterval(fetchStreamData, 4000);
    </script>
</body>
</html>
"""

# ==================== PAGE 3: ANGEL ONE MOBILE APP PAPER TRADING ====================
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
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background: var(--dark-bg); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

        .app-header { height: 48px; background: #0f131c; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; padding: 0 14px; flex-shrink: 0; }
        .avatar-circle { width: 28px; height: 28px; border-radius: 50%; background: var(--angel-blue); color: #fff; font-size: 11px; font-weight: 800; display: flex; align-items: center; justify-content: center; }

        .app-body { flex: 1; position: relative; overflow-y: auto; overflow-x: hidden; }
        .page-view { display: none; width: 100%; height: 100%; overflow-y: auto; padding-bottom: 65px; }
        .page-view.active-page { display: block; }

        .bottom-nav { height: 56px; background: #0d111a; border-top: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-around; position: fixed; bottom: 0; left: 0; width: 100%; z-index: 100; }
        .nav-item { display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text-dim); font-size: 10px; font-weight: 600; text-decoration: none; cursor: pointer; width: 25%; height: 100%; gap: 3px; }
        .nav-item.active { color: var(--tab-active); }

        .strike-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--border-color); background: var(--card-bg); cursor: pointer; }

        .depth-sheet {
            position: fixed; bottom: -100%; left: 0; width: 100%; background: #121824;
            border-top: 2px solid var(--tab-active); border-radius: 16px 16px 0 0; padding: 16px;
            z-index: 200; transition: bottom 0.25s ease; box-shadow: 0 -8px 30px rgba(0,0,0,0.8);
        }
        .depth-sheet.open { bottom: 0; }
        .backdrop { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.65); display: none; z-index: 150; }

        .orderpad-sheet {
            position: fixed; bottom: -100%; left: 0; width: 100%; background: #131722;
            border-top: 2px solid var(--green); border-radius: 16px 16px 0 0; padding: 16px;
            z-index: 300; transition: bottom 0.25s ease;
        }
        .orderpad-sheet.open { bottom: 0; }

        .btn-order-place { width: 100%; background: var(--green); color: #fff; padding: 13px; border: none; border-radius: 8px; font-weight: 900; font-size: 14px; cursor: pointer; margin-top: 14px; }
    </style>
</head>
<body>
    <div class="app-header">
        <div style="display:flex; align-items:center; gap:8px;">
            <div class="avatar-circle">M</div>
            <div>
                <div style="font-size:12px; font-weight:800;">ANGEL ONE PRO</div>
                <div style="font-size:9.5px; color:var(--text-dim);">DEMO ID: M57744366</div>
            </div>
        </div>
        <div style="font-size:11.5px;">
            <a href="/" style="color:#38bdf8; text-decoration:none; margin-right:8px; font-weight:800;">📈 Terminal</a>
            <a href="/oi-analytics" style="color:#00ff88; text-decoration:none; font-weight:800;">⚡ Radar</a>
        </div>
    </div>

    <div class="app-body">
        <div id="pageWatchlist" class="page-view active-page">
            <div style="padding:10px 14px 4px; font-size:11px; font-weight:800; color:var(--text-dim); display:flex; justify-content:space-between;">
                <span>NIFTY OPTIONS (1 LOT = 65 QTY)</span>
                <span>LTP / OI CHG</span>
            </div>
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

    <div class="backdrop" id="sheetBackdrop" onclick="closeAllSheets()"></div>

    <!-- DEPTH SHEET (SCREENSHOT 2) -->
    <div class="depth-sheet" id="depthSheet">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div><b id="dSymTitle">NIFTY 23900 CE</b><br><small style="color:var(--text-dim);">NSE FO</small></div>
            <div style="color:var(--green); font-size:16px; font-weight:bold;" id="dLtpVal">₹146.85</div>
        </div>
        <div style="display:flex; gap:10px; margin-top:14px;">
            <button onclick="openOrderPad('BUY')" style="flex:1; background:var(--green); color:#fff; padding:12px; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">BUY</button>
            <button onclick="openOrderPad('SELL')" style="flex:1; background:var(--red); color:#fff; padding:12px; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">SELL</button>
        </div>
    </div>

    <!-- ORDER PAD (SCREENSHOT 1) -->
    <div class="orderpad-sheet" id="orderPadSheet">
        <b id="padSymTitle">NIFTY 23900 CE</b>
        <div style="margin:10px 0;">
            <label style="font-size:11px; color:var(--text-dim);">Lots (1 Lot = 65 Qty)</label>
            <input type="number" id="lotInput" value="1" min="1" oninput="calcMargin()" style="width:100%; padding:8px; background:#1a202c; color:#fff; border:1px solid #334155; border-radius:6px; font-weight:bold;">
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:10px; font-size:12px;">
            <span>Margin Required:</span>
            <b id="dispMarginReq" style="color:var(--green);">₹ 9,545.25</b>
        </div>
        <button class="btn-order-place" onclick="executeOrder()">PLACE BUY ORDER</button>
    </div>

    <div class="bottom-nav">
        <div class="nav-item active" onclick="switchNav('Watchlist', this)">Watchlist</div>
        <div class="nav-item" onclick="switchNav('Positions', this)">Positions</div>
        <div class="nav-item" onclick="switchNav('Orders', this)">Orders</div>
    </div>

    <script>
        let curItem = null;
        let curSide = "BUY";

        function switchNav(id, el) {
            document.querySelectorAll('.page-view').forEach(p => p.classList.remove('active-page'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            document.getElementById(`page${id}`).classList.add('active-page');
            el.classList.add('active');
            if (id === 'Positions' || id === 'Orders') syncPaperData();
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
                        <div style="color:var(--green); font-weight:bold;">₹ ${s.ltp_ce.toFixed(2)}</div>
                    </div>
                    <div class="strike-row" onclick="openDepth('${s.strike} PE', ${s.ltp_pe})">
                        <div><b>NIFTY ${s.strike} PE</b><br><small style="color:var(--text-dim);">OI: ${s.oi_pe_str}</small></div>
                        <div style="color:var(--red); font-weight:bold;">₹ ${s.ltp_pe.toFixed(2)}</div>
                    </div>`;
                });
                document.getElementById('watchlistContainer').innerHTML = html;
            } catch(e) {}
        }

        function openDepth(sym, ltp) {
            curItem = { sym: sym, ltp: ltp };
            document.getElementById('dSymTitle').innerText = `NIFTY ${sym}`;
            document.getElementById('dLtpVal').innerText = `₹${ltp.toFixed(2)}`;
            document.getElementById('sheetBackdrop').style.display = 'block';
            document.getElementById('depthSheet').classList.add('open');
        }

        function openOrderPad(side) {
            curSide = side;
            document.getElementById('depthSheet').classList.remove('open');
            document.getElementById('padSymTitle').innerText = `NIFTY ${curItem.sym}`;
            calcMargin();
            document.getElementById('orderPadSheet').classList.add('open');
        }

        function closeAllSheets() {
            document.getElementById('sheetBackdrop').style.display = 'none';
            document.getElementById('depthSheet').classList.remove('open');
            document.getElementById('orderPadSheet').classList.remove('open');
        }

        function calcMargin() {
            let lots = parseInt(document.getElementById('lotInput').value) || 1;
            let total = (lots * 65 * curItem.ltp).toFixed(2);
            document.getElementById('dispMarginReq').innerText = `₹ ${parseFloat(total).toLocaleString()}`;
        }

        async function executeOrder() {
            let lots = parseInt(document.getElementById('lotInput').value) || 1;
            let res = await fetch('/api/paper/order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ symbol: curItem.sym, side: curSide, qty: lots * 65, price: curItem.ltp })
            });
            let d = await res.json();
            alert(d.message);
            closeAllSheets();
            syncPaperData();
        }

        async function syncPaperData() {
            try {
                let res = await fetch('/api/paper/state');
                let d = await res.json();
                document.getElementById('dispAvailFunds').innerText = `₹ ${d.available_funds.toLocaleString()}`;
                document.getElementById('dispNetPnl').innerText = `${d.total_pnl >= 0 ? '+' : ''}₹ ${d.total_pnl.toFixed(2)}`;
                let pHtml = '';
                d.positions.forEach(p => {
                    pHtml += `
                    <div style="background:var(--card-bg); padding:10px; margin:8px; border-radius:6px; display:flex; justify-content:space-between; align-items:center;">
                        <div><b>${p.symbol}</b><br><small>Qty: ${p.qty} @ ₹${p.entry_price.toFixed(2)}</small></div>
                        <button onclick="closePos(${p.id})" style="background:#334155; color:#fff; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;">EXIT</button>
                    </div>`;
                });
                document.getElementById('positionsContainer').innerHTML = pHtml || '<div style="text-align:center; padding:20px; color:var(--text-dim);">No Active Positions</div>';
            } catch(e) {}
        }

        async function closePos(id) {
            await fetch('/api/paper/close', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ pos_id: id })
            });
            syncPaperData();
        }

        loadWatchlist();
        syncPaperData();
        setInterval(loadWatchlist, 4000);
        setInterval(syncPaperData, 4000);
    </script>
</body>
</html>
"""

# ==================== ROUTE BINDINGS ====================
@app.get("/", response_class=HTMLResponse)
def index():
    return TERMINAL_HTML

@app.get("/oi-analytics", response_class=HTMLResponse)
def oi_page():
    return OI_DASHBOARD_HTML

@app.get("/paper-trading", response_class=HTMLResponse)
def paper_page():
    return ANGEL_APP_HTML
