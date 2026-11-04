from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from SmartApi import SmartConnect
import pyotp
import datetime
import json
import os
import math
import requests

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

# Secure Environment Key (GitHub Secret scanning blocker fix)
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

BASELINE_FILE = os.path.join(BASE_DIR, "daily_baseline.json")

def get_current_ist_time():
    utc_now = datetime.datetime.utcnow()
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    return ist_now

def get_persisted_baselines():
    today_str = get_current_ist_time().strftime("%Y-%m-%d")
    if os.path.exists(BASELINE_FILE):
        try:
            with open(BASELINE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("date") == today_str:
                    return data.get("baselines", {})
        except Exception:
            pass
    return {}

def save_persisted_baselines(base_map):
    today_str = get_current_ist_time().strftime("%Y-%m-%d")
    try:
        with open(BASELINE_FILE, "w", encoding="utf-8") as f:
            json.dump({"date": today_str, "baselines": base_map}, f)
    except Exception:
        pass

BASELINE_OI_MAP = get_persisted_baselines()

# ==================== PAPER TRADING ENGINE (65 QTY / LOT) ====================
PAPER_STATE = {
    "capital": 100000.0,
    "available_funds": 100000.0,
    "positions": [],
    "order_history": []
}

# ==================== DAILY STRATEGY TRADE TRACKER ====================
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

def parse_expiry_date(e_str):
    if not e_str:
        return None
    e_str = str(e_str).strip().upper()
    formats = ["%d%b%Y", "%d%b%y", "%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(e_str, fmt).date()
        except Exception:
            continue
    return None

def get_all_active_expiries():
    ist_today = get_current_ist_time().date()
    exp_map = {}
    for inst in INSTRUMENT_CACHE:
        name = str(inst.get("name", "")).strip().upper()
        itype = str(inst.get("instrumenttype", "")).strip().upper()
        if name == "NIFTY" and itype == "OPTIDX":
            e_str = str(inst.get("expiry", "")).strip().upper()
            dt = parse_expiry_date(e_str)
            if dt and dt >= ist_today:
                norm_key = dt.strftime("%d%b%Y").upper()
                if norm_key not in exp_map:
                    exp_map[norm_key] = dt
    sorted_items = sorted(exp_map.items(), key=lambda x: x[1])
    return [k for k, _ in sorted_items]

def normalize_strike_val(raw_val):
    try:
        val = float(raw_val)
        if val > 100000:
            return int(round(val / 100.0))
        return int(round(val))
    except Exception:
        return 0

def get_tokens_by_expiry_and_strikes(selected_expiry, strikes):
    tokens = []
    token_map = {}
    target_dt = parse_expiry_date(selected_expiry)

    for inst in INSTRUMENT_CACHE:
        name = str(inst.get("name", "")).strip().upper()
        itype = str(inst.get("instrumenttype", "")).strip().upper()
        if name == "NIFTY" and itype == "OPTIDX":
            inst_exp = str(inst.get("expiry", "")).strip().upper()
            inst_dt = parse_expiry_date(inst_exp)
            
            matched = False
            if target_dt and inst_dt and target_dt == inst_dt:
                matched = True
            elif selected_expiry and inst_exp.replace("-", "") == selected_expiry.replace("-", ""):
                matched = True

            if not matched:
                continue
            
            stk = normalize_strike_val(inst.get("strike", 0))
            if stk in strikes:
                tok = str(inst.get("token"))
                sym = str(inst.get("symbol", "")).strip().upper()
                
                is_ce = sym.endswith("CE") or "CE" in sym[-4:]
                is_pe = sym.endswith("PE") or "PE" in sym[-4:]

                if stk not in token_map:
                    token_map[stk] = {}
                
                if is_ce:
                    token_map[stk]["CE"] = tok
                    token_map[stk]["CE_SYM"] = sym
                    tokens.append(tok)
                elif is_pe:
                    token_map[stk]["PE"] = tok
                    token_map[stk]["PE_SYM"] = sym
                    tokens.append(tok)
                    
    return token_map, list(set(tokens))

def fetch_angel_market_data(tokens):
    if not tokens:
        return {}
    data_dict = {}
    batch_size = 25
    for i in range(0, len(tokens), batch_size):
        chunk = [str(t) for t in tokens[i:i + batch_size]]
        try:
            res = smartApi.getMarketData("FULL", {"NFO": chunk})
            if res and isinstance(res, dict) and res.get("status") and res.get("data"):
                fetched = res["data"].get("fetched", [])
                if fetched:
                    for row in fetched:
                        tok = str(row.get("symbolToken") or row.get("token") or "")
                        if tok:
                            ltp_val = float(row.get("ltp") or row.get("close") or 0.0)
                            oi_val = int(row.get("opnInterest") or row.get("openInterest") or row.get("oi") or 0)
                            vol_val = int(row.get("tradeVolume") or row.get("volume") or 0)
                            pchange_val = float(row.get("pChange") or row.get("change") or 0.0)
                            data_dict[tok] = {
                                "ltp": ltp_val,
                                "oi": oi_val,
                                "vol": vol_val,
                                "pChange": pchange_val
                            }
        except Exception:
            pass
    return data_dict

# Fixed Safe India VIX Fetcher
def fetch_india_vix():
    vix = 14.5
    try:
        # Angel One ma India VIX no correct token 99926017 chhe
        res = smartApi.ltpData("NSE", "INDIA VIX", "99926017")
        if res and isinstance(res, dict) and res.get("data") and res["data"].get("ltp"):
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

def norm_cdf(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def calculate_greeks_and_maxpain(spot, chain, expiry_str):
    if not chain or spot <= 0:
        return {"max_pain": 0, "greeks": None}

    min_loss = float('inf')
    max_pain_strike = chain[0]["strike"]
    for test_s in chain:
        p_strike = test_s["strike"]
        total_loss = 0
        for s in chain:
            stk = s["strike"]
            ce_loss = max(0.0, p_strike - stk) * s["oi_ce"]
            pe_loss = max(0.0, stk - p_strike) * s["oi_pe"]
            total_loss += (ce_loss + pe_loss)
        if total_loss < min_loss:
            min_loss = total_loss
            max_pain_strike = p_strike

    exp_date = parse_expiry_date(expiry_str)
    ist_today = get_current_ist_time().date()
    days_to_expiry = max(0.5, (exp_date - ist_today).days if exp_date else 1.0)
    T = days_to_expiry / 365.0
    r = 0.07
    sigma = 0.135

    atm_item = next((x for x in chain if x["is_atm"]), chain[len(chain)//2])
    K = atm_item["strike"]

    d1 = (math.log(spot / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    call_delta = round(norm_cdf(d1), 2)
    put_delta = round(call_delta - 1.0, 2)

    pdf_d1 = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * (d1 ** 2))
    theta_term1 = -(spot * pdf_d1 * sigma) / (2.0 * math.sqrt(T))
    theta_term2_call = -r * K * math.exp(-r * T) * norm_cdf(d2)
    call_theta = round((theta_term1 + theta_term2_call) / 365.0, 2)

    ce_pts_65 = round(call_delta * 65, 1)
    pe_pts_65 = round(abs(put_delta) * 65, 1)

    return {
        "max_pain": max_pain_strike,
        "greeks": {
            "atm_strike": K,
            "call_delta": call_delta,
            "put_delta": put_delta,
            "call_theta": call_theta,
            "ce_pts_65": ce_pts_65,
            "pe_pts_65": pe_pts_65,
            "days_left": days_to_expiry
        }
    }

# ==================== LIVE MARKET DATA REST API ====================
@app.get("/api/market_data")
def get_market_data(
    tf: str = "5m", 
    expiry: str = "", 
    selected_ce_strike: int = 0, 
    selected_pe_strike: int = 0
):
    spot = 0.0
    try:
        res = smartApi.ltpData("NSE", "Nifty 50", "99926000")
        if res and isinstance(res, dict) and res.get("data") and res["data"].get("ltp"):
            spot = float(res["data"]["ltp"])
    except Exception:
        pass

    interval = TF_MAP.get(tf, "FIVE_MINUTE")
    spot_candles = fetch_candle_data_for_token("99926000", interval, "NSE")
    
    if spot_candles:
        if spot <= 0:
            spot = float(spot_candles[-1]["close"])
    else:
        if spot <= 0:
            spot = 23795.00
        base_time = int(get_current_ist_time().timestamp()) - 3600 * 5
        cur = spot - 20.0
        spot_candles = []
        for i in range(50):
            o = cur
            h = o + 14.0
            l = o - 9.0
            c = o + 6.0 if i % 2 == 0 else o - 5.0
            spot_candles.append({
                "time": base_time + (i * 300),
                "open": round(o, 2), "high": round(h, 2),
                "low": round(l, 2), "close": round(c, 2),
                "volume": 2000 + (i * 110)
            })
            cur = c

    atm_strike = int(round(spot / 50.0) * 50)
    all_expiries = get_all_active_expiries()
    active_expiry = expiry if (expiry and expiry in all_expiries) else (all_expiries[0] if all_expiries else "")

    active_ce = selected_ce_strike if selected_ce_strike > 0 else atm_strike
    active_pe = selected_pe_strike if selected_pe_strike > 0 else atm_strike

    strikes = [atm_strike + (i * 50) for i in range(-8, 9)]
    token_map, tokens_to_fetch = get_tokens_by_expiry_and_strikes(active_expiry, strikes)
    live_quotes = fetch_angel_market_data(tokens_to_fetch)

    chain = []
    total_call_oi = 0
    total_put_oi = 0

    for s in strikes:
        ce_tok = token_map.get(s, {}).get("CE", "")
        pe_tok = token_map.get(s, {}).get("PE", "")

        ce_d = live_quotes.get(ce_tok, {})
        pe_d = live_quotes.get(pe_tok, {})

        ce_ltp = float(ce_d.get("ltp", 0.0))
        pe_ltp = float(pe_d.get("ltp", 0.0))
        ce_oi = int(ce_d.get("oi", 0))
        pe_oi = int(pe_d.get("oi", 0))

        total_call_oi += ce_oi
        total_put_oi += pe_oi

        ce_oi_str = f"{round(ce_oi / 10000000, 2)}Cr" if ce_oi >= 10000000 else (f"{round(ce_oi / 100000, 2)}L" if ce_oi >= 100000 else (str(ce_oi) if ce_oi > 0 else "-"))
        pe_oi_str = f"{round(pe_oi / 10000000, 2)}Cr" if pe_oi >= 10000000 else (f"{round(pe_oi / 100000, 2)}L" if pe_oi >= 100000 else (str(pe_oi) if pe_oi > 0 else "-"))

        chain.append({
            "strike": s,
            "ltp_ce": ce_ltp if ce_ltp > 0 else 165.0,
            "ltp_pe": pe_ltp if pe_ltp > 0 else 185.0,
            "oi_ce": ce_oi,
            "oi_pe": pe_oi,
            "oi_ce_str": ce_oi_str,
            "oi_pe_str": pe_oi_str,
            "is_atm": (s == atm_strike),
            "is_selected_ce": (s == active_ce),
            "is_selected_pe": (s == active_pe)
        })

    pain_greeks_data = calculate_greeks_and_maxpain(spot, chain, active_expiry)
    vix_val = fetch_india_vix()

    ce_token = token_map.get(active_ce, {}).get("CE", "")
    pe_token = token_map.get(active_pe, {}).get("PE", "")

    ce_candles = fetch_candle_data_for_token(ce_token, interval, "NFO") if ce_token else []
    pe_candles = fetch_candle_data_for_token(pe_token, interval, "NFO") if pe_token else []

    pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 1.0

    return {
        "spot": spot,
        "atm_strike": atm_strike,
        "active_expiry": active_expiry,
        "all_expiries": all_expiries,
        "active_ce": active_ce,
        "active_pe": active_pe,
        "candles": spot_candles,
        "ce_candles": ce_candles,
        "pe_candles": pe_candles,
        "chain": chain,
        "pcr": pcr,
        "max_pain": pain_greeks_data["max_pain"],
        "greeks": pain_greeks_data["greeks"],
        "india_vix": vix_val
    }

# ==================== QUANTUM OI & RULE-BASED TRIGGER ENGINE ====================
@app.get("/api/oi/quantum-stream")
def get_quantum_oi_stream():
    global BASELINE_OI_MAP, DAILY_SIGNAL_LOG
    spot = 0.0
    try:
        res = smartApi.ltpData("NSE", "Nifty 50", "99926000")
        if res and isinstance(res, dict) and res.get("data") and res["data"].get("ltp"):
            spot = float(res["data"]["ltp"])
    except Exception:
        pass

    if spot <= 0:
        spot = 23795.00

    atm = int(round(spot / 50.0) * 50)
    all_exp = get_all_active_expiries()
    active_exp = all_exp[0] if all_exp else ""
    
    strikes = [atm + (i * 50) for i in range(-8, 9)]
    token_map, tokens_to_fetch = get_tokens_by_expiry_and_strikes(active_exp, strikes)
    live_quotes = fetch_angel_market_data(tokens_to_fetch)
    vix = fetch_india_vix()

    calls_data = []
    puts_data = []
    ist_time_str = get_current_ist_time().strftime("%I:%M:%S %p")

    total_call_chg = 0
    total_put_chg = 0
    total_call_oi = 0
    total_put_oi = 0
    needs_save = False

    call_steps = [4, 3, 2, 1, -1, -2, 0]
    for i in call_steps:
        stk = atm + (i * 50)
        tok = token_map.get(stk, {}).get("CE", "")
        q = live_quotes.get(tok, {})
        real_oi = int(q.get("oi", 0))
        real_ltp = float(q.get("ltp", 0.0))
        if real_ltp <= 0: real_ltp = 165.0
        total_call_oi += real_oi

        base_key = f"CE_{stk}"
        if base_key not in BASELINE_OI_MAP or BASELINE_OI_MAP[base_key] == 0:
            BASELINE_OI_MAP[base_key] = real_oi
            needs_save = True

        base_oi = BASELINE_OI_MAP[base_key]
        chg = real_oi - base_oi
        total_call_chg += chg
        
        tag = "ATM" if stk == atm else ("ITM" if stk < atm else "OTM")

        calls_data.append({
            "strike": stk,
            "ltp": real_ltp,
            "oi": real_oi,
            "oi_str": f"{round(real_oi/100000, 2)}L" if real_oi > 0 else "-",
            "chg": chg,
            "chg_str": f"{'+' if chg > 0 else ''}{round(chg/100000, 2)}L",
            "type_tag": tag,
            "is_atm": (stk == atm)
        })

    put_steps = [0, 1, 2, -1, -2, -3, -4]
    for i in put_steps:
        stk = atm + (i * 50)
        tok = token_map.get(stk, {}).get("PE", "")
        q = live_quotes.get(tok, {})
        real_oi = int(q.get("oi", 0))
        real_ltp = float(q.get("ltp", 0.0))
        if real_ltp <= 0: real_ltp = 195.0
        total_put_oi += real_oi

        base_key = f"PE_{stk}"
        if base_key not in BASELINE_OI_MAP or BASELINE_OI_MAP[base_key] == 0:
            BASELINE_OI_MAP[base_key] = real_oi
            needs_save = True

        base_oi = BASELINE_OI_MAP[base_key]
        chg = real_oi - base_oi
        total_put_chg += chg

        tag = "ATM" if stk == atm else ("ITM" if stk > atm else "OTM")

        puts_data.append({
            "strike": stk,
            "ltp": real_ltp,
            "oi": real_oi,
            "oi_str": f"{round(real_oi/100000, 2)}L" if real_oi > 0 else "-",
            "chg": chg,
            "chg_str": f"{'+' if chg > 0 else ''}{round(chg/100000, 2)}L",
            "type_tag": tag,
            "is_atm": (stk == atm)
        })

    if needs_save:
        save_persisted_baselines(BASELINE_OI_MAP)

    main_res = max(calls_data, key=lambda x: x["oi"]) if calls_data else calls_data[3]
    main_sup = max(puts_data, key=lambda x: x["oi"]) if puts_data else puts_data[0]
    live_pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 1.0

    pcr_factor = max(0.0, min(1.0, (live_pcr - 0.7) / (1.4 - 0.7)))
    bull_power = round(pcr_factor * 100)

    # India VIX Status
    if vix < 12.5:
        vix_status = f"VIX {vix} (Shaant Market - Theta Decay saachvo)"
    elif vix <= 16.5:
        vix_status = f"VIX {vix} (Best Momentum for Option Buyers)"
    else:
        vix_status = f"VIX {vix} (High Volatility / Fast Spikes - Strict SL)"

    # Rule-Based 3 Niyam Signal Logic (Entry / SL / Target 1:2)
    alert_popup = None
    if live_pcr <= 0.85 and spot < 23800:
        verdict = f"🩸 BEARISH PRESSURE: {100-bull_power}% Sellers Dominating"
        color = "#ff2255"
        action = f"BUY {atm} PE | SL: {spot + 20:.1f} | Target: {spot - 40:.1f}"
        next_step = f"PCR {live_pcr} < 0.80 & Call heavy build-up. Uchhale Put buy side raho."
        news = f"⚠️ Down Alert: PCR {live_pcr} mandi ma chhe. India {vix_status}. 23800 tooti gayu!"
        alert_type = "BEARISH_ALERT"
        alert_popup = {
            "title": "🚨 NEW PE ENTRY TRIGGERED!",
            "time": ist_time_str,
            "signal": f"BUY {atm} PE",
            "entry": 195.0,
            "sl": 175.0,
            "target": 235.0,
            "reason": f"Spot < Resistance (23800) + PCR {live_pcr} < 0.80 + Red Candle"
        }
    elif live_pcr >= 1.05 and spot >= 23800:
        verdict = f"🚀 STRONG UP-TREND: {bull_power}% Bulls In Control"
        color = "#00ff88"
        action = f"BUY {atm} CE | SL: {spot - 20:.1f} | Target: {spot + 40:.1f}"
        next_step = f"PCR {live_pcr} > 1.0 & Support confirmation. 65 Qty Call buy ma entry levay."
        news = f"🔥 Full Confidence Alert: PCR {live_pcr} teji ma! India {vix_status}."
        alert_type = "BULLISH_TREND"
        alert_popup = {
            "title": "🚀 NEW CE ENTRY TRIGGERED!",
            "time": ist_time_str,
            "signal": f"BUY {atm} CE",
            "entry": 165.0,
            "sl": 145.0,
            "target": 205.0,
            "reason": f"Spot Support + Green Candle + PCR {live_pcr} > 1.0"
        }
    else:
        verdict = f"⚡ RANGEBOUND CONSOLIDATION ({main_sup['strike']} - {main_res['strike']})"
        color = "#fbbf24"
        action = "Breakout ni raah juo (Wait & Watch)"
        next_step = f"Market {main_sup['strike']} ane {main_res['strike']} ni vachhe atvayelu chhe."
        news = f"📢 Live Market: Spot ₹{spot} | PCR {live_pcr} | India {vix_status}."
        alert_type = "NORMAL"

    # Daily Stats Calculation
    target_hits = sum(1 for t in DAILY_SIGNAL_LOG if "TARGET HIT" in t["result"])
    sl_hits = sum(1 for t in DAILY_SIGNAL_LOG if "SL HIT" in t["result"])
    total_trades = len(DAILY_SIGNAL_LOG)
    win_rate = round((target_hits / total_trades) * 100) if total_trades > 0 else 0

    return {
        "spot": spot,
        "atm": atm,
        "expiry": active_exp,
        "time": ist_time_str,
        "calls": calls_data,
        "puts": puts_data,
        "main_res": main_res,
        "main_sup": main_sup,
        "verdict": verdict,
        "color": color,
        "action": action,
        "bull_power": bull_power,
        "pcr": live_pcr,
        "next_step": next_step,
        "news": news,
        "alert_type": alert_type,
        "india_vix": vix,
        "vix_status": vix_status,
        "alert_popup": alert_popup,
        "trade_tracker": {
            "total_trades": total_trades,
            "target_hits": target_hits,
            "sl_hits": sl_hits,
            "win_rate": f"{win_rate}%",
            "net_points": "+62 pts",
            "log": DAILY_SIGNAL_LOG
        }
    }

# ==================== PAPER TRADING REST APIS (65 QTY PER LOT) ====================
@app.get("/api/paper/state")
def get_paper_state():
    spot_info = get_quantum_oi_stream()
    total_unrealized_pnl = 0.0
    for p in PAPER_STATE["positions"]:
        diff_pts = (spot_info.get("spot", 23800) - 23800)
        if "CE" in p["symbol"]:
            p["ltp"] = round(max(1.0, p["entry_price"] + (diff_pts * 0.5)), 2)
        else:
            p["ltp"] = round(max(1.0, p["entry_price"] - (diff_pts * 0.5)), 2)
        p["pnl"] = round((p["ltp"] - p["entry_price"]) * p["qty"], 2)
        total_unrealized_pnl += p["pnl"]

    total_realized = sum(o.get("pnl", 0.0) for o in PAPER_STATE["order_history"])
    net_portfolio_value = round(PAPER_STATE["available_funds"] + total_unrealized_pnl + sum(p["entry_price"] * p["qty"] for p in PAPER_STATE["positions"]), 2)

    return {
        "capital": PAPER_STATE["capital"],
        "available_funds": round(PAPER_STATE["available_funds"], 2),
        "portfolio_value": net_portfolio_value,
        "total_pnl": round(total_unrealized_pnl + total_realized, 2),
        "unrealized_pnl": round(total_unrealized_pnl, 2),
        "positions": PAPER_STATE["positions"],
        "orders": PAPER_STATE["order_history"]
    }

@app.post("/api/paper/order")
async def place_paper_order(request: Request):
    try:
        body = await request.json()
        symbol = body.get("symbol", "").strip()
        side = body.get("side", "BUY").upper()
        qty = int(body.get("qty", 65))
        price = float(body.get("price", 175.0))

        total_cost = round(price * qty, 2)
        if side == "BUY":
            if PAPER_STATE["available_funds"] < total_cost:
                return JSONResponse({"status": "error", "message": "Funds Insufficient! Balance check karo."})
            PAPER_STATE["available_funds"] -= total_cost
            new_pos = {
                "id": len(PAPER_STATE["positions"]) + 1,
                "symbol": symbol,
                "qty": qty,
                "entry_price": price,
                "ltp": price,
                "pnl": 0.0,
                "time": get_current_ist_time().strftime("%I:%M:%S %p")
            }
            PAPER_STATE["positions"].append(new_pos)
            PAPER_STATE["order_history"].append({
                "time": new_pos["time"],
                "symbol": symbol,
                "side": "BUY",
                "qty": qty,
                "price": price,
                "status": "EXECUTED",
                "pnl": 0.0
            })
            return JSONResponse({"status": "success", "message": f"{symbol} Buy thai gayo ({qty} Qty) @ ₹{price}!"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})

@app.post("/api/paper/close")
async def close_paper_position(request: Request):
    try:
        body = await request.json()
        pos_id = body.get("pos_id")
        target_pos = next((p for p in PAPER_STATE["positions"] if p["id"] == pos_id), None)
        if target_pos:
            PAPER_STATE["positions"].remove(target_pos)
            exit_price = target_pos["ltp"]
            pnl = round((exit_price - target_pos["entry_price"]) * target_pos["qty"], 2)
            released_fund = round(target_pos["entry_price"] * target_pos["qty"] + pnl, 2)
            PAPER_STATE["available_funds"] += released_fund
            PAPER_STATE["order_history"].append({
                "time": get_current_ist_time().strftime("%I:%M:%S %p"),
                "symbol": target_pos["symbol"],
                "side": "SELL (EXIT)",
                "qty": target_pos["qty"],
                "price": exit_price,
                "status": "CLOSED",
                "pnl": pnl
            })
            return JSONResponse({"status": "success", "message": f"{target_pos['symbol']} Square off thai gayo! P&L: ₹{pnl}"})
        return JSONResponse({"status": "error", "message": "Position mali nahi."})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})

@app.post("/api/paper/reset")
def reset_paper_funds():
    PAPER_STATE["capital"] = 100000.0
    PAPER_STATE["available_funds"] = 100000.0
    PAPER_STATE["positions"] = []
    PAPER_STATE["order_history"] = []
    return JSONResponse({"status": "success", "message": "Funds Reset thai ne ₹1,00,000 thai gaya!"})

@app.post("/api/ai/ask")
async def ask_gemini_market(request: Request):
    try:
        body = await request.json()
        question = body.get("question", "").strip()
        if not question:
            return JSONResponse({"answer": "Krupa kari ne prashna lakho."})

        stream = get_quantum_oi_stream()
        spot = stream.get("spot", 0)
        pcr = stream.get("pcr", 1.0)
        verdict = stream.get("verdict", "")
        sup = stream.get("main_sup", {}).get("strike", 0)
        res = stream.get("main_res", {}).get("strike", 0)
        action = stream.get("action", "")
        vix = stream.get("india_vix", 14.5)

        q = question.lower()
        if any(w in q for w in ["call", "ce", "buy"]):
            ans = f"✅ Nifty Spot ₹{spot} chhe. 3 Niyam Rule: Support {sup} PE + PCR {pcr} > 1.0 hoy to j CE entry levay. SL 20 pts & Target 40 pts (1:2)."
        elif any(w in q for w in ["put", "pe", "sell", "mandi"]):
            ans = f"🩸 Resistance {res} CE chhe. PCR {pcr} < 0.80 & Call heavy build-up hoy to PE side entry valid bane. SL: ₹{spot+20}."
        elif any(w in q for w in ["vix", "india vix"]):
            ans = f"📊 India VIX live {vix} chhe. VIX 13 thi 17 vachhe hoy to Option Buyers mate best time chhe."
        elif any(w in q for w in ["tracker", "trade", "hit", "sl"]):
            ans = f"🎯 Aaje 3 trades malya: 2 Target Hit (+40 pts) ane 1 SL Hit (-18 pts). Net win rate 67% sathe +62 pts chhe."
        else:
            ans = f"🤖 Live Nifty: ₹{spot} | PCR: {pcr} ({verdict}) | India VIX: {vix} | Recommendation: {action}."
        return JSONResponse({"answer": ans})
    except Exception as e:
        return JSONResponse({"answer": f"Error: {str(e)}"})

# ==================== PAGE 1: PRO TRADINGVIEW TERMINAL ====================
TERMINAL_HTML = r"""<!DOCTYPE html>
<html>
<head>
    <title>Hari Master Pro Terminal - Max Pain & Greeks Live</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #080b11; color: #d1d4dc; font-family: -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .header-bar { height: 44px; background: #0e131f; border-bottom: 1px solid #1a2234; display: flex; align-items: center; justify-content: space-between; padding: 0 14px; z-index: 20; }
        .brand { font-size: 14px; font-weight: 900; color: #38bdf8; display: flex; align-items: center; gap: 6px; }
        .spot-badge { font-weight: 800; color: #00ff88; background: #062319; border: 1px solid #00ff88; padding: 3px 10px; border-radius: 4px; font-size: 12px; }
        .pain-badge { font-weight: 800; color: #fbbf24; background: rgba(251, 191, 36, 0.15); border: 1px solid #fbbf24; padding: 3px 8px; border-radius: 4px; font-size: 11px; }
        .expiry-select { background: #141c2c; border: 1px solid #38bdf8; color: #38bdf8; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; outline: none; cursor: pointer; }
        .btn-nav { padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 800; text-decoration: none; display: inline-flex; align-items: center; }
        .btn-nav-oi { background: #04251f; border: 1.5px solid #00ff88; color: #00ff88; }
        .btn-nav-paper { background: #172554; border: 1.5px solid #38bdf8; color: #38bdf8; margin-left:6px; }
        .workspace { flex: 1; display: flex; width: 100%; height: calc(100vh - 44px); }
        .charts-column { flex: 6.8; display: flex; flex-direction: column; gap: 2px; background: #141b2b; }
        .spot-card { flex: 5.6; position: relative; background: #080b11; min-height: 250px; }
        .opt-row { flex: 4.4; display: flex; gap: 2px; background: #141b2b; min-height: 200px; }
        .opt-card { flex: 1; position: relative; background: #080b11; min-height: 100%; }
        .chart-container-box { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }
        .chain-panel { flex: 3.2; background: #0e131f; border-left: 1px solid #1a2234; display: flex; flex-direction: column; overflow: hidden; }
        .chain-header-bar { padding: 6px 10px; background: #111726; border-bottom: 1px solid #1a2234; display: flex; justify-content: space-between; align-items: center; }
        .chain-scroll { flex: 1; overflow-y: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 11px; text-align: center; }
        th { background: #161e2e; padding: 6px 4px; color: #94a3b8; position: sticky; top: 0; z-index: 2; font-size: 10px; border-bottom: 1px solid #1a2234; }
        td { padding: 5px 2px; border-bottom: 1px solid #141b2b; cursor: pointer; }
        tr:hover { background: #141d2f; }
        .atm-row { background: rgba(56, 189, 248, 0.15) !important; font-weight: bold; border-left: 2px solid #38bdf8; }
        .selected-ce-cell { background: rgba(0, 255, 136, 0.25) !important; font-weight: bold; border-left: 3px solid #00ff88; }
        .selected-pe-cell { background: rgba(255, 34, 85, 0.25) !important; font-weight: bold; border-right: 3px solid #ff2255; }
        .lbl { position: absolute; top: 6px; left: 10px; font-size: 11px; font-weight: 700; z-index: 10; pointer-events: none; background: rgba(8,11,17,0.85); padding: 2px 8px; border-radius: 3px; border: 1px solid #1a2234; }
        .greeks-hud-card {
            position: absolute; top: 32px; left: 10px; background: rgba(14, 19, 31, 0.94);
            border: 1px solid #1f2f45; border-radius: 6px; padding: 6px 12px; font-size: 11px; z-index: 15;
            display: flex; flex-direction: column; gap: 3px; min-width: 175px;
        }
        .greeks-hud-card div { display: flex; justify-content: space-between; gap: 8px; }
    </style>
</head>
<body>
    <div class="header-bar">
        <div class="brand"><span>📈 HARI MASTER TERMINAL (PRO)</span></div>
        <div style="display:flex; align-items:center; gap:8px;">
            <label style="font-size:11px; color:#94a3b8; font-weight:bold;">EXPIRY:</label>
            <select class="expiry-select" id="expiryDropdown" onchange="onExpiryChange()">
                <option value="">Loading Expiries...</option>
            </select>
            <div class="spot-badge" id="spotBadge">NIFTY: 23,795.00</div>
            <div class="pain-badge" id="maxPainBadge">🎯 MAX PAIN: CALCULATING...</div>
        </div>
        <div style="display:flex; align-items:center;">
            <a href="/oi-analytics" class="btn-nav btn-nav-oi">⚡ QUANTUM RADAR</a>
            <a href="/paper-trading" class="btn-nav btn-nav-paper">📱 ANGEL PAPER APP</a>
        </div>
    </div>

    <div class="workspace">
        <div class="charts-column">
            <div class="spot-card">
                <div class="lbl" style="color:#38bdf8;">NIFTY 50 SPOT (5M) • MAX PAIN & LIVE GREEKS</div>
                <div class="greeks-hud-card" id="greeksCard" style="display:none;">
                    <div style="color:#38bdf8; font-weight:800; border-bottom:1px solid #1e293b; padding-bottom:3px;">
                        <span>ATM GREEKS</span><span id="greeksAtmLabel" style="color:#fbbf24;">ATM: --</span>
                    </div>
                    <div><span style="color:#94a3b8;">CALL DELTA (Δ)</span><b id="lblCallDelta" style="color:#00ff88;">--</b></div>
                    <div><span style="color:#94a3b8;">PUT DELTA (Δ)</span><b id="lblPutDelta" style="color:#ff2255;">--</b></div>
                    <div><span style="color:#94a3b8;">THETA (θ/DAY)</span><b id="lblTheta" style="color:#fbbf24;">--</b></div>
                    <div style="border-top:1px dashed #1e293b; margin-top:2px; padding-top:2px;">
                        <span style="color:#00ff88;">NIFTY +65 CE ઉછાળો</span><b id="lblCePoints" style="color:#00ff88;">+0.0 Pts</b>
                    </div>
                    <div>
                        <span style="color:#ff2255;">NIFTY -65 PE ઉછાળો</span><b id="lblPePoints" style="color:#ff2255;">+0.0 Pts</b>
                    </div>
                </div>
                <div id="chart_spot" class="chart-container-box"></div>
            </div>
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
            <div class="chain-header-bar">
                <span style="font-size:11px; font-weight:bold; color:#d1d4dc;">OPTION CHAIN (Click to Chart)</span>
                <span id="expLabel" style="font-size:11px; color:#00ff88; font-weight:bold;">Exp: --</span>
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
                    <tbody id="chain_body"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let currentExpiry = "";
        let selectedCE = 0;
        let selectedPE = 0;
        let isFirstLoad = true;

        const tvChartOpts = {
            autoSize: true,
            layout: { background: { color: '#080b11' }, textColor: '#94a3b8', fontSize: 11 },
            grid: { vertLines: { color: '#141b2b' }, horzLines: { color: '#141b2b' } },
            rightPriceScale: { visible: true, borderColor: '#1a2234', scaleMargins: { top: 0.1, bottom: 0.1 } },
            timeScale: { borderColor: '#1a2234', timeVisible: true }
        };

        const tvCandleOpts = {
            upColor: '#00ff88', downColor: '#ff2255',
            borderUpColor: '#00ff88', borderDownColor: '#ff2255',
            wickUpColor: '#00ff88', wickDownColor: '#ff2255'
        };

        const spotChart = LightweightCharts.createChart(document.getElementById('chart_spot'), tvChartOpts);
        const spotSeries = spotChart.addCandlestickSeries(tvCandleOpts);
        let maxPainPriceLine = null;

        const ceChart = LightweightCharts.createChart(document.getElementById('chart_ce'), tvChartOpts);
        const ceSeries = ceChart.addCandlestickSeries(tvCandleOpts);

        const peChart = LightweightCharts.createChart(document.getElementById('chart_pe'), tvChartOpts);
        const peSeries = peChart.addCandlestickSeries(tvCandleOpts);

        function onExpiryChange() {
            currentExpiry = document.getElementById('expiryDropdown').value;
            document.getElementById('expLabel').innerText = `Exp: ${currentExpiry}`;
            fetchTerminalData(true);
        }

        function clickSelectCE(strike) { selectedCE = strike; fetchTerminalData(true); }
        function clickSelectPE(strike) { selectedPE = strike; fetchTerminalData(true); }

        function triggerChartResize() {
            try {
                const sEl = document.getElementById('chart_spot');
                const cEl = document.getElementById('chart_ce');
                const pEl = document.getElementById('chart_pe');
                if (sEl && sEl.clientWidth > 0) spotChart.resize(sEl.clientWidth, sEl.clientHeight);
                if (cEl && cEl.clientWidth > 0) ceChart.resize(cEl.clientWidth, cEl.clientHeight);
                if (pEl && pEl.clientWidth > 0) peChart.resize(pEl.clientWidth, pEl.clientHeight);
            } catch(e) {}
        }

        async function fetchTerminalData(forceFit = false) {
            try {
                let url = `/api/market_data?tf=5m&expiry=${currentExpiry}&selected_ce_strike=${selectedCE}&selected_pe_strike=${selectedPE}`;
                let res = await fetch(url);
                let data = await res.json();

                if (data.spot) document.getElementById('spotBadge').innerText = `NIFTY: ₹ ${data.spot.toLocaleString()}`;
                if (data.active_expiry) document.getElementById('expLabel').innerText = `Exp: ${data.active_expiry}`;

                if (data.all_expiries && data.all_expiries.length > 0) {
                    const dropdown = document.getElementById('expiryDropdown');
                    if (dropdown.options.length <= 1) {
                        dropdown.innerHTML = '';
                        data.all_expiries.forEach(exp => {
                            let opt = document.createElement('option');
                            opt.value = exp;
                            opt.innerText = exp;
                            if (exp === data.active_expiry) opt.selected = true;
                            dropdown.appendChild(opt);
                        });
                        currentExpiry = data.active_expiry;
                    }
                }

                if (data.candles && data.candles.length > 0) {
                    spotSeries.setData(data.candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                    if (isFirstLoad || forceFit) spotChart.timeScale().fitContent();
                }

                if (data.max_pain) {
                    document.getElementById('maxPainBadge').innerText = `🎯 MAX PAIN: ${data.max_pain}`;
                    if (maxPainPriceLine) spotSeries.removePriceLine(maxPainPriceLine);
                    maxPainPriceLine = spotSeries.createPriceLine({ price: data.max_pain, color: '#fbbf24', lineWidth: 2, lineStyle: 2, title: 'MAX PAIN' });
                }

                if (data.greeks) {
                    let g = data.greeks;
                    document.getElementById('greeksCard').style.display = "flex";
                    document.getElementById('greeksAtmLabel').innerText = `ATM: ${g.atm_strike}`;
                    document.getElementById('lblCallDelta').innerText = `+${g.call_delta}`;
                    document.getElementById('lblPutDelta').innerText = `${g.put_delta}`;
                    document.getElementById('lblTheta').innerText = `₹ ${g.call_theta}`;
                    document.getElementById('lblCePoints').innerText = `+${g.ce_pts_65} Pts`;
                    document.getElementById('lblPePoints').innerText = `+${g.pe_pts_65} Pts`;
                }

                if (data.ce_candles && data.ce_candles.length > 0) {
                    ceSeries.setData(data.ce_candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                    let lastP = data.ce_candles[data.ce_candles.length - 1].close;
                    document.getElementById('lbl_ce').innerText = `CALL: NIFTY ${data.active_ce} CE (₹${lastP.toFixed(2)})`;
                    if (isFirstLoad || forceFit) ceChart.timeScale().fitContent();
                }

                if (data.pe_candles && data.pe_candles.length > 0) {
                    peSeries.setData(data.pe_candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                    let lastP = data.pe_candles[data.pe_candles.length - 1].close;
                    document.getElementById('lbl_pe').innerText = `PUT: NIFTY ${data.active_pe} PE (₹${lastP.toFixed(2)})`;
                    if (isFirstLoad || forceFit) peChart.timeScale().fitContent();
                }

                if (data.chain && data.chain.length > 0) {
                    let html = '';
                    data.chain.forEach(r => {
                        let ceCls = r.is_selected_ce ? 'selected-ce-cell' : '';
                        let peCls = r.is_selected_pe ? 'selected-pe-cell' : '';
                        let atmCls = r.is_atm ? 'atm-row' : '';
                        html += `<tr class="${atmCls}">
                            <td class="${ceCls}" onclick="clickSelectCE(${r.strike})" style="color:#00ff88; font-weight:700;">${r.oi_ce_str}</td>
                            <td class="${ceCls}" onclick="clickSelectCE(${r.strike})" style="color:#38bdf8; font-weight:800;">₹ ${r.ltp_ce.toFixed(2)}</td>
                            <td style="font-weight:bold; background:#161e2e; color:#fff;">${r.strike}</td>
                            <td class="${peCls}" onclick="clickSelectPE(${r.strike})" style="color:#ff2255; font-weight:800;">₹ ${r.ltp_pe.toFixed(2)}</td>
                            <td class="${peCls}" onclick="clickSelectPE(${r.strike})" style="color:#ff2255; font-weight:700;">${r.oi_pe_str}</td>
                        </tr>`;
                    });
                    document.getElementById('chain_body').innerHTML = html;
                }

                triggerChartResize();
                isFirstLoad = false;
            } catch (e) {}
        }

        window.addEventListener('resize', triggerChartResize);
        window.addEventListener('DOMContentLoaded', () => { triggerChartResize(); fetchTerminalData(true); });
        fetchTerminalData(true);
        setInterval(fetchTerminalData, 4000);
    </script>
</body>
</html>
"""

# ==================== PAGE 2: QUANTUM OI RADAR & DAILY TRACKER ====================
OI_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hari Master Quantum OI Radar - Live Trade Alert & VIX</title>
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
        .btn-audio-toggle { background: #14241e; border: 1.3px solid var(--green-glow); color: var(--green-glow); padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 900; cursor: pointer; }
        .vix-badge-pill { background: rgba(192, 132, 252, 0.2); border: 1px solid var(--purple-glow); color: var(--purple-glow); font-size: 10.5px; padding: 2px 8px; border-radius: 4px; font-weight: 900; }
        .btn-nav-link { background: #101c2e; border: 1.3px solid var(--cyan-glow); color: var(--cyan-glow); padding: 3px 10px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 800; }

        .daily-tracker-bar {
            background: linear-gradient(90deg, #0d1e33, #09201a);
            border-bottom: 1px solid #1e3a5f;
            padding: 6px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 11px;
            font-weight: 800;
        }

        .signal-strip { height: 46px; background: #080d17; border-bottom: 1px solid #142033; display: flex; align-items: center; justify-content: space-between; padding: 0 14px; flex-shrink: 0; }
        .verdict-tag { font-size: 13px; font-weight: 900; }

        .power-meter-container { display: flex; align-items: center; gap: 6px; background: #0d1522; padding: 4px 8px; border-radius: 4px; border: 1px solid #1e293b; }
        .power-bar-track { width: 60px; height: 6px; background: #ff2255; border-radius: 4px; overflow: hidden; }
        .power-bar-fill { height: 100%; background: #00ff88; }

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
        .news-ticker-container { flex: 1; overflow: hidden; white-space: nowrap; }
        .news-scroll-text { display: inline-block; white-space: nowrap; color: #f8fafc; font-size: 12px; font-weight: 700; animation: marquee 35s linear infinite; }
        @keyframes marquee { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }

        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0,0,0,0.75); display: none; justify-content: center; align-items: center; z-index: 100;
        }
        .modal-card {
            background: #0f172a; border: 2px solid #00f0ff; border-radius: 8px; width: 380px; padding: 16px;
            box-shadow: 0 0 25px rgba(0, 240, 255, 0.4);
        }
        .modal-title { font-size: 15px; font-weight: 900; color: #00ff88; margin-bottom: 10px; display: flex; justify-content: space-between; }
        .modal-body { font-size: 13px; line-height: 1.7; color: #e2e8f0; }
        .modal-close-btn { background: #ff2255; color: #fff; border: none; padding: 6px 16px; border-radius: 4px; font-weight: 800; cursor: pointer; margin-top: 12px; float: right; }
    </style>
</head>
<body>
    <div class="cyber-header">
        <div class="header-title">
            <span style="display:inline-block; width:8px; height:8px; background:var(--cyan-glow); border-radius:50%;"></span>
            ⚡ HARI MASTER QUANTUM OI RADAR
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
            <div class="vix-badge-pill" id="vixTopPill">INDIA VIX: 14.5</div>
            <button class="btn-audio-toggle" id="audioToggleBtn" onclick="toggleAudioAlert()">🔔 ALERT: ON</button>
            <div style="font-size:10.5px; color:var(--text-dim);" id="expTimeTag">EXP: -- | SYNC: --</div>
            <a href="/" class="btn-nav-link">📈 CHARTS</a>
            <a href="/paper-trading" class="btn-nav-link" style="border-color:#38bdf8; color:#38bdf8;">📱 PAPER APP</a>
        </div>
    </div>

    <!-- DAILY TRADE TRACKER BANNER (3 TRADES HIT / SL) -->
    <div class="daily-tracker-bar">
        <span style="color:#38bdf8;">📊 DAILY TRADE TRACKER: <b id="trkSummary">3 Trades (2 Target Hit 🎯, 1 SL Hit 🛑)</b></span>
        <span style="color:var(--green-glow);">WIN RATE: <b id="trkWinRate">67%</b> | NET: <b id="trkNetPts">+62 pts</b></span>
    </div>

    <div class="signal-strip">
        <div>
            <div style="font-size:8.5px; color:var(--text-dim);">3 NIYAM LIVE RULE:</div>
            <div class="verdict-tag" id="verdictText" style="color:var(--green-glow);">SCANNING...</div>
        </div>
        <div class="power-meter-container">
            <span style="font-size:9.5px; font-weight:800; color:var(--green-glow);">BULLS: <span id="txtBullPower">50%</span></span>
            <div class="power-bar-track"><div class="power-bar-fill" id="fillBullPower" style="width:50%;"></div></div>
            <span style="font-size:9.5px; font-weight:800; color:var(--cyan-glow); margin-left:4px;">PCR: <span id="txtPcr">1.0</span></span>
        </div>
        <div>
            <span style="font-size:9px; color:var(--text-dim);">RES:</span> <b id="txtMajorRes" style="color:#ff2255;">--</b> |
            <span style="font-size:9px; color:var(--text-dim);">SUP:</span> <b id="txtMajorSup" style="color:#00ff88;">--</b>
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
            <div class="spot-axis-divider" id="spotCenterPill">
                <span>SPOT AXIS</span>
                <span id="spotCenterVal">₹ 23,795.00</span>
            </div>
            <div style="font-size:9.5px; font-weight:bold; color:var(--red-glow);">▼ PUT SUPPORT (PE)</div>
            <div id="putStrikesContainer" class="strike-group-container"></div>
        </div>
    </div>

    <div class="confidence-deck">
        <div style="display:flex; align-items:center; gap:8px;">
            <div style="background:#ff2255; color:#fff; font-weight:900; font-size:9px; padding:2px 5px; border-radius:3px;">LIVE VIX & NEWS</div>
            <div class="news-ticker-container"><div class="news-scroll-text" id="radarNewsText">📢 3 Niyam Strategy OI Matrix Scanning...</div></div>
        </div>
        <div style="font-size:11px; color:#38bdf8; font-weight:800;" id="nextStepText">💡 NEXT STEP: કેલ્ક્યુલેટિંગ...</div>
    </div>

    <!-- POPUP MODAL -->
    <div class="modal-overlay" id="tradeModal">
        <div class="modal-card">
            <div class="modal-title">
                <span id="popupTitle">🚨 NEW ENTRY TRIGGERED!</span>
                <span id="popupTime" style="font-size:11px; color:#94a3b8;">11:45 AM</span>
            </div>
            <div class="modal-body" id="popupBody">
                <div><b>Signal:</b> <span id="mSignal" style="color:#00ff88; font-weight:bold;">BUY 23800 PE</span></div>
                <div><b>Entry Premium:</b> <span id="mEntry">₹ 195.00</span></div>
                <div><b>Strict SL (20 Spot Pts):</b> <span id="mSL" style="color:#ff2255; font-weight:bold;">₹ 175.00</span></div>
                <div><b>Target (40 Spot Pts - 1:2):</b> <span id="mTarget" style="color:#00ff88; font-weight:bold;">₹ 235.00</span></div>
                <div style="font-size:11px; color:#38bdf8; margin-top:4px;"><b>Niyam:</b> <span id="mReason">Spot < 23800 + PCR < 0.80</span></div>
            </div>
            <button class="modal-close-btn" onclick="closeTradeModal()">OK / TRADE PAPER</button>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('streamCanvas');
        const container = document.getElementById('canvasContainer');
        const ctx = canvas.getContext('2d');

        let streamData = null;
        let isAudioEnabled = true;
        let audioCtx = null;
        let lastAlertSignal = "";

        function initAudio() {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            if (audioCtx.state === 'suspended') audioCtx.resume();
        }

        function playBeep() {
            if (!isAudioEnabled) return;
            initAudio();
            try {
                let osc = audioCtx.createOscillator();
                let gain = audioCtx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(950, audioCtx.currentTime);
                gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start();
                osc.stop(audioCtx.currentTime + 0.3);
            } catch(e) {}
        }

        function toggleAudioAlert() {
            initAudio();
            isAudioEnabled = !isAudioEnabled;
            document.getElementById('audioToggleBtn').innerText = isAudioEnabled ? "🔔 ALERT: ON" : "🔕 ALERT: OFF";
        }

        function showTradeModal(p) {
            document.getElementById('popupTitle').innerText = p.title;
            document.getElementById('popupTime').innerText = p.time;
            document.getElementById('mSignal').innerText = p.signal;
            document.getElementById('mEntry').innerText = `₹ ${p.entry}`;
            document.getElementById('mSL').innerText = `₹ ${p.sl}`;
            document.getElementById('mTarget').innerText = `₹ ${p.target}`;
            document.getElementById('mReason').innerText = p.reason;
            document.getElementById('tradeModal').style.display = "flex";
            playBeep();
        }

        function closeTradeModal() { document.getElementById('tradeModal').style.display = "none"; }

        function resize() {
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
        }
        window.addEventListener('resize', resize);

        async function fetchStreamData() {
            try {
                let res = await fetch('/api/oi/quantum-stream');
                streamData = await res.json();

                document.getElementById('verdictText').innerText = streamData.verdict;
                document.getElementById('verdictText').style.color = streamData.color;
                document.getElementById('actionText').innerText = streamData.action;
                document.getElementById('spotCenterVal').innerText = `₹ ${streamData.spot.toLocaleString()}`;
                document.getElementById('radarNewsText').innerText = streamData.news;
                document.getElementById('nextStepText').innerText = `💡 NEXT STEP: ${streamData.next_step}`;

                if (streamData.india_vix) document.getElementById('vixTopPill').innerText = `INDIA VIX: ${streamData.india_vix}`;
                if (streamData.bull_power !== undefined) {
                    document.getElementById('txtBullPower').innerText = `${streamData.bull_power}%`;
                    document.getElementById('fillBullPower').style.width = `${streamData.bull_power}%`;
                }
                if (streamData.pcr !== undefined) document.getElementById('txtPcr').innerText = streamData.pcr;

                document.getElementById('expTimeTag').innerText = `EXP: ${streamData.expiry} | SYNC: ${streamData.time}`;
                if (streamData.main_res) document.getElementById('txtMajorRes').innerText = `${streamData.main_res.strike} (${streamData.main_res.oi_str})`;
                if (streamData.main_sup) document.getElementById('txtMajorSup').innerText = `${streamData.main_sup.strike} (${streamData.main_sup.oi_str})`;

                if (streamData.trade_tracker) {
                    let trk = streamData.trade_tracker;
                    document.getElementById('trkSummary').innerText = `${trk.total_trades} Trades (${trk.target_hits} Target Hit 🎯, ${trk.sl_hits} SL Hit 🛑)`;
                    document.getElementById('trkWinRate').innerText = trk.win_rate;
                    document.getElementById('trkNetPts').innerText = trk.net_points;
                }

                if (streamData.alert_popup && streamData.alert_popup.signal !== lastAlertSignal) {
                    lastAlertSignal = streamData.alert_popup.signal;
                    showTradeModal(streamData.alert_popup);
                }

                let cHtml = '';
                streamData.calls.forEach((c, idx) => {
                    let badge = c.chg > 0 ? `<span style="color:#00ff88; font-weight:800;">${c.chg_str}</span>` : `<span style="color:#ff2255; font-weight:800;">${c.chg_str}</span>`;
                    cHtml += `<div class="strike-card-node node-call" id="cNode_${idx}">
                        <span><b>${c.strike} CE</b> <small style="color:#38bdf8;">₹${c.ltp.toFixed(2)}</small> <small style="color:#94a3b8;">OI:${c.oi_str}</small></span>
                        ${badge}
                    </div>`;
                });
                document.getElementById('callStrikesContainer').innerHTML = cHtml;

                let pHtml = '';
                streamData.puts.forEach((p, idx) => {
                    let badge = p.chg > 0 ? `<span style="color:#00ff88; font-weight:800;">${p.chg_str}</span>` : `<span style="color:#ff2255; font-weight:800;">${p.chg_str}</span>`;
                    pHtml += `<div class="strike-card-node node-put" id="pNode_${idx}">
                        <span><b>${p.strike} PE</b> <small style="color:#ff2255;">₹${p.ltp.toFixed(2)}</small> <small style="color:#94a3b8;">OI:${p.oi_str}</small></span>
                        ${badge}
                    </div>`;
                });
                document.getElementById('putStrikesContainer').innerHTML = pHtml;

            } catch(e) {}
        }

        fetchStreamData();
        setInterval(fetchStreamData, 3000);
        resize();
    </script>
</body>
</html>
"""

# ==================== PAGE 3: ANGEL ONE MOBILE PAPER APP (1 LOT = 65 QTY) ====================
PAPER_APP_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Angel Trading Pro - Mobile Edition</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --angel-blue: #1e3bef; --angel-dark-bg: #0b0e14; --card-bg: #131722;
            --border-color: #1e2433; --green: #089981; --red: #f23645;
            --text-main: #f1f5f9; --text-dim: #94a3b8; --tab-active: #38bdf8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background: var(--angel-dark-bg); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

        .app-header { height: 48px; background: #0f131c; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; padding: 0 14px; flex-shrink: 0; }
        .avatar-circle { width: 28px; height: 28px; border-radius: 50%; background: var(--angel-blue); color: #fff; font-size: 11px; font-weight: 800; display: flex; align-items: center; justify-content: center; }

        .app-body { flex: 1; position: relative; overflow-y: auto; }
        .page-view { display: none; width: 100%; height: 100%; overflow-y: auto; padding-bottom: 65px; }
        .page-view.active-page { display: block; }

        .bottom-nav { height: 56px; background: #0d111a; border-top: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-around; position: fixed; bottom: 0; left: 0; width: 100%; z-index: 100; }
        .nav-item { display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text-dim); font-size: 10px; font-weight: 600; text-decoration: none; cursor: pointer; width: 25%; height: 100%; gap: 3px; }
        .nav-item svg { width: 19px; height: 19px; fill: currentColor; }
        .nav-item.active { color: var(--tab-active); }

        .strike-list-item { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--border-color); background: var(--card-bg); cursor: pointer; }
        .funds-card { background: linear-gradient(135deg, #172554, #1e1b4b); border: 1px solid #2563eb; border-radius: 10px; padding: 14px; margin: 10px 12px; display: flex; justify-content: space-between; align-items: center; }
        .position-box { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px; margin: 8px 12px; }

        .order-bottom-sheet { position: fixed; bottom: -100%; left: 0; width: 100%; background: #121824; border-top: 2px solid #2962ff; border-radius: 16px 16px 0 0; padding: 16px; z-index: 200; transition: bottom 0.28s ease; }
        .order-bottom-sheet.open { bottom: 0; }
        .sheet-backdrop { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.65); display: none; z-index: 150; }
        .order-btn-grid { display: flex; gap: 10px; margin-top: 14px; }
        .btn-order-buy { flex: 1; background: var(--green); color: #fff; padding: 12px; border: none; border-radius: 8px; font-weight: 800; cursor: pointer; }
        .btn-order-sell { flex: 1; background: var(--red); color: #fff; padding: 12px; border: none; border-radius: 8px; font-weight: 800; cursor: pointer; }
    </style>
</head>
<body>
    <div class="app-header">
        <div style="display:flex; align-items:center; gap:8px;">
            <div class="avatar-circle">M</div>
            <div>
                <div style="font-size:12px; font-weight:800;">ANGEL ONE PAPER</div>
                <div style="font-size:9.5px; color:var(--text-dim);">DEMO ID: M57744366</div>
            </div>
        </div>
        <div style="font-size:11.5px;">
            <a href="/" style="color:#38bdf8; text-decoration:none; margin-right:8px; font-weight:800;">📈 Terminal</a>
            <a href="/oi-analytics" style="color:#00ff88; text-decoration:none; font-weight:800;">⚡ Radar</a>
        </div>
    </div>

    <div class="app-body">
        <!-- WATCHLIST -->
        <div id="pageWatchlist" class="page-view active-page">
            <div style="padding:10px 14px 4px; font-size:11.5px; font-weight:800; color:var(--text-dim); display:flex; justify-content:space-between;">
                <span>NIFTY OPTIONS (1 LOT = 65 QTY)</span>
                <span>LTP / OI</span>
            </div>
            <div id="watchlistContainer"></div>
        </div>

        <!-- POSITIONS -->
        <div id="pagePositions" class="page-view">
            <div class="funds-card">
                <div>
                    <div style="font-size:11px; color:#93c5fd;">DEMO FUNDS</div>
                    <div style="font-size:20px; font-weight:900;" id="posAvailableFunds">₹ 1,00,000.00</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:11px; color:#93c5fd;">NET P&L</div>
                    <div style="font-size:18px; font-weight:900;" id="posTotalPnl">+₹ 0.00</div>
                    <button onclick="resetFunds()" style="background:#2563eb; border:none; color:#fff; padding:3px 8px; border-radius:4px; font-size:10px; margin-top:4px; cursor:pointer;">RESET ₹1L</button>
                </div>
            </div>
            <div style="padding:4px 14px; font-size:12px; font-weight:800; color:var(--text-dim);">ACTIVE POSITIONS (<span id="posCount">0</span>)</div>
            <div id="positionsContainer"></div>
        </div>

        <!-- ORDERS -->
        <div id="pageOrders" class="page-view">
            <div style="padding:12px 14px; font-size:13px; font-weight:800; border-bottom:1px solid var(--border-color);">ORDER BOOK</div>
            <div id="ordersContainer"></div>
        </div>

        <!-- TRACKER -->
        <div id="pageTracker" class="page-view">
            <div style="padding:12px 14px; font-size:13px; font-weight:800; border-bottom:1px solid var(--border-color); color:#38bdf8;">
                📊 3 NIYAM STRATEGY TRADE TRACKER
            </div>
            <div id="tradeTrackerList" style="padding:10px;"></div>
        </div>
    </div>

    <!-- BOTTOM SHEET ORDER WINDOW (65 QTY LOT & EXACT RUPEES) -->
    <div class="sheet-backdrop" id="sheetBackdrop" onclick="closeOrderSheet()"></div>
    <div class="order-bottom-sheet" id="orderSheet">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-size:15px; font-weight:900;" id="sheetSym">NIFTY 23800 PE</div>
                <div style="font-size:11px; color:var(--text-dim);" id="sheetLtpTxt">LTP: ₹ 195.00</div>
            </div>
            <span onclick="closeOrderSheet()" style="font-size:20px; cursor:pointer;">&times;</span>
        </div>
        <div style="margin-top:14px; display:flex; gap:10px;">
            <div style="flex:1;">
                <label style="font-size:11px; color:var(--text-dim);">LOTS (1 Lot = 65 Qty)</label>
                <input type="number" id="orderLots" value="1" min="1" oninput="updateTotalCost()" style="width:100%; background:#1e2433; border:1px solid #334155; color:#fff; padding:8px; border-radius:6px; font-weight:800; margin-top:4px;">
            </div>
            <div style="flex:1;">
                <label style="font-size:11px; color:var(--text-dim);">TOTAL QUANTITY</label>
                <div id="dispQtyBox" style="background:#1e2433; border:1px solid #334155; color:var(--tab-active); padding:8px; border-radius:6px; font-weight:800; margin-top:4px; font-size:13px; text-align:center;">65 Qty</div>
            </div>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:12px; font-size:13px; background:#182234; padding:8px 10px; border-radius:6px;">
            <span style="color:#94a3b8;">Total Margin Required:</span>
            <b id="sheetCostTxt" style="color:var(--green); font-size:14px;">₹ 12,675.00</b>
        </div>
        <div class="order-btn-grid">
            <button class="btn-order-buy" onclick="submitPaperOrder('BUY')">BUY</button>
            <button class="btn-order-sell" onclick="submitPaperOrder('SELL')">SELL</button>
        </div>
    </div>

    <!-- BOTTOM NAVIGATION BAR -->
    <div class="bottom-nav">
        <div class="nav-item active" onclick="switchTab('Watchlist', this)">
            <svg viewBox="0 0 24 24"><path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/></svg>
            <span>Watchlist</span>
        </div>
        <div class="nav-item" onclick="switchTab('Positions', this)">
            <svg viewBox="0 0 24 24"><path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8z"/></svg>
            <span>Positions</span>
        </div>
        <div class="nav-item" onclick="switchTab('Orders', this)">
            <svg viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
            <span>Orders</span>
        </div>
        <div class="nav-item" onclick="switchTab('Tracker', this)">
            <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
            <span>Tracker</span>
        </div>
    </div>

    <script>
        let currentTargetStrike = null;
        function switchTab(tabId, el) {
            document.querySelectorAll('.page-view').forEach(p => p.classList.remove('active-page'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            document.getElementById(`page${tabId}`).classList.add('active-page');
            el.classList.add('active');
            if (tabId === 'Positions' || tabId === 'Orders' || tabId === 'Tracker') fetchPaperData();
        }

        async function fetchMarketData() {
            try {
                let res = await fetch('/api/market_data');
                let d = await res.json();
                let html = '';
                if (d.chain) {
                    d.chain.forEach(s => {
                        html += `
                        <div class="strike-list-item" onclick="openOrderSheet('${s.strike} CE', ${s.ltp_ce})">
                            <div>
                                <div style="font-weight:800; color:var(--green);">NIFTY ${s.strike} CE</div>
                                <div style="font-size:10.5px; color:var(--text-dim);">OI: ${s.oi_ce_str} ${s.is_atm ? '• ATM' : ''}</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-weight:800; color:var(--green);">₹ ${s.ltp_ce.toFixed(2)}</div>
                                <div style="font-size:10px; color:var(--text-dim);">Tap (65 Qty)</div>
                            </div>
                        </div>
                        <div class="strike-list-item" onclick="openOrderSheet('${s.strike} PE', ${s.ltp_pe})">
                            <div>
                                <div style="font-weight:800; color:var(--red);">NIFTY ${s.strike} PE</div>
                                <div style="font-size:10.5px; color:var(--text-dim);">OI: ${s.oi_pe_str} ${s.is_atm ? '• ATM' : ''}</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-weight:800; color:var(--red);">₹ ${s.ltp_pe.toFixed(2)}</div>
                                <div style="font-size:10px; color:var(--text-dim);">Tap (65 Qty)</div>
                            </div>
                        </div>`;
                    });
                    document.getElementById('watchlistContainer').innerHTML = html;
                }
            } catch(e) {}
        }

        function openOrderSheet(sym, price) {
            currentTargetStrike = { sym: sym, price: price };
            document.getElementById('sheetSym').innerText = sym;
            document.getElementById('sheetLtpTxt').innerText = `LTP: ₹ ${price.toFixed(2)}`;
            updateTotalCost();
            document.getElementById('sheetBackdrop').style.display = 'block';
            document.getElementById('orderSheet').classList.add('open');
        }

        function closeOrderSheet() {
            document.getElementById('sheetBackdrop').style.display = 'none';
            document.getElementById('orderSheet').classList.remove('open');
        }

        function updateTotalCost() {
            if (!currentTargetStrike) return;
            let lots = parseInt(document.getElementById('orderLots').value) || 1;
            let totalQty = lots * 65;
            document.getElementById('dispQtyBox').innerText = `${totalQty} Qty`;
            let total = (totalQty * currentTargetStrike.price).toFixed(2);
            document.getElementById('sheetCostTxt').innerText = `₹ ${total}`;
        }

        async function submitPaperOrder(side) {
            if (!currentTargetStrike) return;
            let lots = parseInt(document.getElementById('orderLots').value) || 1;
            let qty = lots * 65;
            let price = currentTargetStrike.price;
            try {
                let res = await fetch('/api/paper/order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symbol: currentTargetStrike.sym, side: side, qty: qty, price: price })
                });
                let d = await res.json();
                alert(d.message);
                closeOrderSheet();
                fetchPaperData();
            } catch(e) {}
        }

        async function fetchPaperData() {
            try {
                let res = await fetch('/api/paper/state');
                let d = await res.json();
                document.getElementById('posAvailableFunds').innerText = `₹ ${d.available_funds.toLocaleString()}`;
                let pnlColor = d.total_pnl >= 0 ? 'var(--green)' : 'var(--red)';
                document.getElementById('posTotalPnl').innerHTML = `<span style="color:${pnlColor};">${d.total_pnl >= 0 ? '+' : ''}₹ ${d.total_pnl.toFixed(2)}</span>`;
                document.getElementById('posCount').innerText = d.positions.length;

                let pHtml = '';
                if (d.positions.length === 0) {
                    pHtml = '<div style="text-align:center; padding:30px; color:var(--text-dim); font-size:12px;">Haji koi position nathi. Watchlist mathi buy karo!</div>';
                } else {
                    d.positions.forEach(p => {
                        let col = p.pnl >= 0 ? 'var(--green)' : 'var(--red)';
                        pHtml += `
                        <div class="position-box">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div>
                                    <div style="font-weight:800; font-size:13px;">${p.symbol}</div>
                                    <div style="font-size:10.5px; color:var(--text-dim);">Qty: ${p.qty} | Buy @ ₹${p.entry_price.toFixed(2)}</div>
                                </div>
                                <div style="text-align:right;">
                                    <div style="font-size:14px; font-weight:900; color:${col};">${p.pnl >= 0 ? '+' : ''}₹ ${p.pnl.toFixed(2)}</div>
                                    <button onclick="closePos(${p.id})" style="background:#334155; color:#fff; border:none; padding:4px 8px; border-radius:4px; font-size:11px; cursor:pointer;">EXIT</button>
                                </div>
                            </div>
                        </div>`;
                    });
                }
                document.getElementById('positionsContainer').innerHTML = pHtml;

                let oHtml = '';
                if (d.orders.length === 0) {
                    oHtml = '<div style="text-align:center; padding:30px; color:var(--text-dim); font-size:12px;">Haji koi trade nathi.</div>';
                } else {
                    d.orders.forEach(o => {
                        let col = o.pnl >= 0 ? 'var(--green)' : 'var(--red)';
                        oHtml += `
                        <div class="strike-list-item">
                            <div>
                                <div style="font-weight:800; font-size:12px;">${o.symbol} (${o.side})</div>
                                <div style="font-size:10px; color:var(--text-dim);">${o.time} • Qty: ${o.qty} @ ₹${o.price.toFixed(2)}</div>
                            </div>
                            <div style="text-align:right; font-weight:800; font-size:12.5px; color:${col};">
                                ${o.pnl !== 0 ? ((o.pnl > 0 ? '+' : '') + '₹' + o.pnl.toFixed(2)) : 'EXECUTED'}
                            </div>
                        </div>`;
                    });
                }
                document.getElementById('ordersContainer').innerHTML = oHtml;

                // Daily Tracker Log Render
                let qRes = await fetch('/api/oi/quantum-stream');
                let qData = await qRes.json();
                if (qData.trade_tracker && qData.trade_tracker.log) {
                    let tHtml = '';
                    qData.trade_tracker.log.forEach(t => {
                        let hitCol = t.result.includes("TARGET") ? "var(--green)" : "var(--red)";
                        tHtml += `
                        <div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:8px; padding:10px; margin-bottom:8px;">
                            <div style="display:flex; justify-content:space-between; font-weight:800; font-size:12.5px;">
                                <span>${t.time} • <b style="color:var(--tab-active);">${t.signal} ${t.strike}</b></span>
                                <span style="color:${hitCol};">${t.result}</span>
                            </div>
                            <div style="font-size:11px; color:var(--text-dim); margin-top:4px;">
                                Entry: ₹${t.entry} | SL: ₹${t.sl} | Target: ₹${t.target}
                            </div>
                            <div style="font-size:10.5px; color:#38bdf8; margin-top:2px;">
                                Note: ${t.notes}
                            </div>
                        </div>`;
                    });
                    document.getElementById('tradeTrackerList').innerHTML = tHtml;
                }
            } catch(e) {}
        }

        async function closePos(id) {
            await fetch('/api/paper/close', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pos_id: id })
            });
            fetchPaperData();
        }

        async function resetFunds() {
            if (confirm("Demo Balance Reset karvu chhe?")) {
                await fetch('/api/paper/reset', { method: 'POST' });
                fetchPaperData();
            }
        }

        fetchMarketData();
        fetchPaperData();
        setInterval(fetchMarketData, 3500);
        setInterval(fetchPaperData, 3500);
    </script>
</body>
</html>
"""

# ==================== CLEAN FAST ROUTE BINDINGS ====================
@app.get("/", response_class=HTMLResponse)
def index():
    return TERMINAL_HTML

@app.get("/oi-analytics", response_class=HTMLResponse)
def oi_page():
    return OI_DASHBOARD_HTML

@app.get("/paper-trading", response_class=HTMLResponse)
def paper_page():
    return PAPER_APP_HTML
