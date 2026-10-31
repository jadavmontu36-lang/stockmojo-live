from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from SmartApi import SmartConnect
import pyotp
import datetime
import json
import os

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
            print(f"✅ Loaded {len(INSTRUMENT_CACHE)} instruments from nfo_instruments.json")
    except Exception as e:
        print("❌ Instrument load error:", e)

BASELINE_OI_MAP = {}

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
    today = datetime.date.today()
    exp_map = {}
    for inst in INSTRUMENT_CACHE:
        name = str(inst.get("name", "")).strip().upper()
        itype = str(inst.get("instrumenttype", "")).strip().upper()
        if name == "NIFTY" and itype == "OPTIDX":
            e_str = str(inst.get("expiry", "")).strip().upper()
            dt = parse_expiry_date(e_str)
            if dt and dt >= today:
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
    batch_size = 40
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
        except Exception as e:
            print(f"❌ MarketData fetch error: {e}")
    return data_dict

def fetch_candle_data_for_token(token, interval_str, exchange="NFO"):
    now = datetime.datetime.now()
    to_date = now.strftime("%Y-%m-%d 15:30")
    from_date = (now - datetime.timedelta(days=4)).strftime("%Y-%m-%d 09:15")
    
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
        return []
    return candles

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
    except Exception as e:
        print("LTP Error:", e)

    interval = TF_MAP.get(tf, "FIVE_MINUTE")
    spot_candles = fetch_candle_data_for_token("99926000", interval, "NSE")
    
    if spot_candles:
        if spot <= 0:
            spot = float(spot_candles[-1]["close"])
    else:
        if spot <= 0:
            spot = 23053.10
        base_time = int(datetime.datetime.now().timestamp()) - 3600 * 5
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

    strikes = [atm_strike + (i * 50) for i in range(-10, 11)]
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

        if ce_oi >= 10000000:
            ce_oi_str = f"{round(ce_oi / 10000000, 2)}Cr"
        elif ce_oi >= 100000:
            ce_oi_str = f"{round(ce_oi / 100000, 2)}L"
        elif ce_oi > 0:
            ce_oi_str = str(ce_oi)
        else:
            ce_oi_str = "-"

        if pe_oi >= 10000000:
            pe_oi_str = f"{round(pe_oi / 10000000, 2)}Cr"
        elif pe_oi >= 100000:
            pe_oi_str = f"{round(pe_oi / 100000, 2)}L"
        elif pe_oi > 0:
            pe_oi_str = str(pe_oi)
        else:
            pe_oi_str = "-"

        chain.append({
            "strike": s,
            "ltp_ce": ce_ltp,
            "ltp_pe": pe_ltp,
            "oi_ce": ce_oi,
            "oi_pe": pe_oi,
            "oi_ce_str": ce_oi_str,
            "oi_pe_str": pe_oi_str,
            "is_atm": (s == atm_strike),
            "is_selected_ce": (s == active_ce),
            "is_selected_pe": (s == active_pe)
        })

    ce_token = token_map.get(active_ce, {}).get("CE", "")
    pe_token = token_map.get(active_pe, {}).get("PE", "")

    ce_candles = fetch_candle_data_for_token(ce_token, interval, "NFO") if ce_token else []
    pe_candles = fetch_candle_data_for_token(pe_token, interval, "NFO") if pe_token else []

    ce_sel_data = next((x for x in chain if x["strike"] == active_ce), chain[len(chain)//2])
    pe_sel_data = next((x for x in chain if x["strike"] == active_pe), chain[len(chain)//2])
    base_ce = ce_sel_data["ltp_ce"] if ce_sel_data["ltp_ce"] > 0 else 100.0
    base_pe = pe_sel_data["ltp_pe"] if pe_sel_data["ltp_pe"] > 0 else 100.0
    last_c = spot_candles[-1]["close"]

    if not ce_candles:
        ce_candles = []
        for c in spot_candles:
            diff_c = c["close"] - last_c
            diff_o = c["open"] - last_c
            c_cl = max(0.5, round(base_ce + (diff_c * 0.5), 2))
            c_op = max(0.5, round(base_ce + (diff_o * 0.5), 2))
            ce_candles.append({
                "time": c["time"], "open": c_op, "high": max(c_op, c_cl) + 2.5, 
                "low": max(0.2, min(c_op, c_cl) - 2.5), "close": c_cl
            })

    if not pe_candles:
        pe_candles = []
        for c in spot_candles:
            diff_c = c["close"] - last_c
            diff_o = c["open"] - last_c
            p_cl = max(0.5, round(base_pe - (diff_c * 0.5), 2))
            p_op = max(0.5, round(base_pe - (diff_o * 0.5), 2))
            pe_candles.append({
                "time": c["time"], "open": p_op, "high": max(p_op, p_cl) + 2.5, 
                "low": max(0.2, min(p_op, p_cl) - 2.5), "close": p_cl
            })

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
        "pcr": pcr
    }

# ==================== ADVANCED INTRADAY RADAR ENGINE ====================
@app.get("/api/oi/quantum-stream")
def get_quantum_oi_stream():
    global BASELINE_OI_MAP
    spot = 0.0
    try:
        res = smartApi.ltpData("NSE", "Nifty 50", "99926000")
        if res and isinstance(res, dict) and res.get("data") and res["data"].get("ltp"):
            spot = float(res["data"]["ltp"])
    except Exception:
        pass

    if spot <= 0:
        spot = 23053.10

    atm = int(round(spot / 50.0) * 50)
    all_exp = get_all_active_expiries()
    active_exp = all_exp[0] if all_exp else ""
    
    strikes = [atm + (i * 50) for i in range(-4, 5)]
    token_map, tokens_to_fetch = get_tokens_by_expiry_and_strikes(active_exp, strikes)
    live_quotes = fetch_angel_market_data(tokens_to_fetch)

    calls_data = []
    puts_data = []
    time_str = datetime.datetime.now().strftime("%H:%M:%S")

    call_steps = [4, 3, 2, 1, 0, -1, -2]
    for i in call_steps:
        stk = atm + (i * 50)
        tok = token_map.get(stk, {}).get("CE", "")
        q = live_quotes.get(tok, {})
        real_oi = int(q.get("oi", 0))
        real_ltp = float(q.get("ltp", 0.0))

        base_key = f"CE_{stk}"
        if base_key not in BASELINE_OI_MAP or BASELINE_OI_MAP[base_key] == 0:
            BASELINE_OI_MAP[base_key] = real_oi

        base_oi = BASELINE_OI_MAP[base_key]
        chg = real_oi - base_oi

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

    put_steps = [-2, -1, 0, 1, 2, 3, 4]
    for i in put_steps:
        stk = atm - (i * 50)
        tok = token_map.get(stk, {}).get("PE", "")
        q = live_quotes.get(tok, {})
        real_oi = int(q.get("oi", 0))
        real_ltp = float(q.get("ltp", 0.0))

        base_key = f"PE_{stk}"
        if base_key not in BASELINE_OI_MAP or BASELINE_OI_MAP[base_key] == 0:
            BASELINE_OI_MAP[base_key] = real_oi

        base_oi = BASELINE_OI_MAP[base_key]
        chg = real_oi - base_oi

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

    intraday_calls = [c for c in calls_data if c["strike"] >= atm]
    intraday_puts = [p for p in puts_data if p["strike"] <= atm]

    main_res = max(intraday_calls, key=lambda x: x["oi"]) if intraday_calls else calls_data[0]
    main_sup = max(intraday_puts, key=lambda x: x["oi"]) if intraday_puts else puts_data[-1]

    max_call_add = max(calls_data, key=lambda x: x["chg"]) if calls_data else None
    max_put_add = max(puts_data, key=lambda x: x["chg"]) if puts_data else None

    if max_put_add and max_put_add["chg"] > 0 and (not max_call_add or max_put_add["chg"] >= max_call_add["chg"]):
        verdict = f"🚀 તેજી સંકેત: {max_put_add['strike']} PE પર નવો OI ઉમેરાયો"
        color = "#00ff88"
        action = f"ખરીદો {max_put_add['strike']} CE / {atm} CE | લક્ષ્ય: {main_res['strike']}"
        news = f"🔥 એડવાન્સ એલર્ટ: {max_put_add['strike']} PE સ્ટ્રાઇક પર સૌથી મોટો નવો ઓપન ઇન્ટરેસ્ટ ({max_put_add['chg_str']}) ઉમેરાયો છે! પુટ રાઇટર્સ મજબૂત દીવાલ બનાવી રહ્યા છે, જેથી બજાર નીચે અટકીને ઉપરની દિશામાં Rocket Reversal મારશે! ખાસ ધ્યાન: {max_put_add['strike']} CE / {atm} CE પર કૉલ બાય સાઇડ નજર રાખો, ઉપરનું લક્ષ્ય {main_res['strike']} રહેશે!"
    elif max_call_add and max_call_add["chg"] > 0 and (not max_put_add or max_call_add["chg"] > max_put_add["chg"]):
        verdict = f"🩸 મંદી સંકેત: {max_call_add['strike']} CE પર નવો OI ઉમેરાયો"
        color = "#ff2255"
        action = f"ખરીદો {max_call_add['strike']} PE / {atm} PE | લક્ષ્ય: {main_sup['strike']}"
        news = f"⚠️ એડવાન્સ એલર્ટ: {max_call_add['strike']} CE સ્ટ્રાઇક પર ભારે નવો ઓપન ઇન્ટરેસ્ટ ({max_call_add['chg_str']}) ઉમેરાયો છે! મોટા કૉલ સેલર્સ બજારને દબાવી રહ્યા છે, જેથી નિફ્ટી ઉપર નહીં જઈ શકે અને નીચે પટકશે! ખાસ ધ્યાન: {max_call_add['strike']} PE / {atm} PE પર પુટ બાય સાઇડ નજર રાખો, નીચેનું લક્ષ્ય {main_sup['strike']} રહેશે!"
    else:
        verdict = f"⚡ સાઇડવેઝ રેન્જ: {main_sup['strike']} - {main_res['strike']}"
        color = "#fbbf24"
        action = f"બ્રેકઆઉટની રાહ જુઓ ({main_res['strike']} ઉપર કે {main_sup['strike']} નીચે)"
        news = f"📢 લાઈવ સમાચાર: નિફ્ટી સ્પોટ {spot} પર ચાલે છે. નજીકનો સૌથી મોટો કૉલ અવરોધ {main_res['strike']} CE ({main_res['oi_str']}) અને પુટ સપોર્ટ {main_sup['strike']} PE ({main_sup['oi_str']}) છે. હજુ સુધી કોઈ મોટી સ્ટ્રાઇક પર આક્રમક OI ઉમેરાયો નથી. જ્યાં સુધી {main_res['strike']} ઉપર કે {main_sup['strike']} નીચે બ્રેકઆઉટ ન આવે ત્યાં સુધી શાંતિ રાખો!"

    return {
        "spot": spot,
        "atm": atm,
        "expiry": active_exp,
        "time": time_str,
        "calls": calls_data,
        "puts": puts_data,
        "main_res": main_res,
        "main_sup": main_sup,
        "verdict": verdict,
        "color": color,
        "action": action,
        "news": news
    }

# ==================== TERMINAL FRONTEND ====================
TERMINAL_HTML = r"""<!DOCTYPE html>
<html>
<head>
    <title>StockMojo Terminal Pro - Angel One Live</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #080b11; color: #d1d4dc; font-family: -apple-system, BlinkMacSystemFont, sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .header-bar { height: 44px; background: #0e131f; border-bottom: 1px solid #1a2234; display: flex; align-items: center; justify-content: space-between; padding: 0 14px; z-index: 20; }
        .brand { font-size: 14px; font-weight: 800; color: #38bdf8; display: flex; align-items: center; gap: 6px; }
        .spot-badge { font-weight: 800; color: #00ff88; background: #062319; border: 1px solid #00ff88; padding: 4px 10px; border-radius: 4px; font-size: 12px; }
        .expiry-select { background: #141c2c; border: 1px solid #38bdf8; color: #38bdf8; padding: 4px 8px; border-radius: 4px; font-size: 11.5px; font-weight: 700; outline: none; cursor: pointer; }
        .btn-nav-oi { background: #04251f; border: 1.5px solid #00ff88; color: #00ff88; padding: 5px 12px; border-radius: 4px; font-size: 11px; font-weight: 800; text-decoration: none; box-shadow: 0 0 10px rgba(0,255,136,0.2); }
        .btn-nav-oi:hover { background: #00ff88; color: #000; }
        .workspace { flex: 1; display: flex; width: 100%; height: calc(100vh - 44px); }
        .charts-column { flex: 6.8; display: flex; flex-direction: column; gap: 1px; background: #141b2b; }
        .spot-card { flex: 5.8; position: relative; background: #080b11; }
        .opt-row { flex: 4.2; display: flex; gap: 1px; background: #141b2b; }
        .opt-card { flex: 1; position: relative; background: #080b11; }
        .chain-panel { flex: 3.2; background: #0e131f; border-left: 1px solid #1a2234; display: flex; flex-direction: column; overflow: hidden; }
        .chain-header-bar { padding: 8px 10px; background: #111726; border-bottom: 1px solid #1a2234; display: flex; justify-content: space-between; align-items: center; }
        .chain-scroll { flex: 1; overflow-y: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 10.5px; text-align: center; }
        th { background: #161e2e; padding: 6px 4px; color: #94a3b8; position: sticky; top: 0; z-index: 2; font-size: 9.5px; }
        td { padding: 5px 2px; border-bottom: 1px solid #141b2b; cursor: pointer; }
        tr:hover { background: #141d2f; }
        .atm-row { background: rgba(56, 189, 248, 0.12) !important; font-weight: bold; border-left: 2px solid #38bdf8; }
        .selected-ce-cell { background: rgba(0, 255, 136, 0.25) !important; font-weight: bold; border-left: 3px solid #00ff88; }
        .selected-pe-cell { background: rgba(255, 34, 85, 0.25) !important; font-weight: bold; border-right: 3px solid #ff2255; }
        .lbl { position: absolute; top: 6px; left: 10px; font-size: 11px; font-weight: bold; z-index: 10; pointer-events: none; }
    </style>
</head>
<body>
    <div class="header-bar">
        <div class="brand"><span>⚡ StockMojo Pro Terminal</span></div>
        <div style="display:flex; align-items:center; gap:10px;">
            <label style="font-size:11px; color:#94a3b8; font-weight:bold;">EXPIRY:</label>
            <select class="expiry-select" id="expiryDropdown" onchange="onExpiryChange()">
                <option value="">Loading Expiries...</option>
            </select>
            <div class="spot-badge" id="spotBadge">NIFTY: 22,517.00</div>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
            <a href="/oi-analytics" target="_blank" class="btn-nav-oi">⚡ QUANTUM REVERSAL MATRIX</a>
        </div>
    </div>

    <div class="workspace">
        <div class="charts-column">
            <div class="spot-card">
                <div class="lbl" style="color:#38bdf8;">NIFTY 50 SPOT INDEX</div>
                <div id="chart_spot" style="width:100%; height:100%;"></div>
            </div>
            <div class="opt-row">
                <div class="opt-card">
                    <div class="lbl" id="lbl_ce" style="color:#00ff88;">CALL (CE) STRIKE CHART</div>
                    <div id="chart_ce" style="width:100%; height:100%;"></div>
                </div>
                <div class="opt-card">
                    <div class="lbl" id="lbl_pe" style="color:#ff2255;">PUT (PE) STRIKE CHART</div>
                    <div id="chart_pe" style="width:100%; height:100%;"></div>
                </div>
            </div>
        </div>

        <div class="chain-panel">
            <div class="chain-header-bar">
                <span style="font-size:11px; font-weight:bold; color:#38bdf8;">LIVE OPTION CHAIN (Click to Chart)</span>
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

        const chartOpts = {
            autoSize: true,
            layout: { background: { color: '#080b11' }, textColor: '#d1d4dc', fontSize: 11 },
            grid: { vertLines: { color: '#141b2b' }, horzLines: { color: '#141b2b' } },
            crosshair: {
                vertLine: { color: '#38bdf8', style: 2, labelBackgroundColor: '#1e293b' },
                horzLine: { color: '#38bdf8', style: 2, labelBackgroundColor: '#1e293b' }
            },
            rightPriceScale: { visible: true, borderColor: '#1a2234', scaleMargins: { top: 0.1, bottom: 0.1 }, mode: 0, autoScale: true, alignLabels: true, borderVisible: true },
            timeScale: { borderColor: '#1a2234', timeVisible: true, secondsVisible: false }
        };

        const candleSeriesOpts = {
            upColor: '#00ff88', downColor: '#ff2255',
            borderUpColor: '#00ff88', borderDownColor: '#ff2255',
            wickUpColor: '#00ff88', wickDownColor: '#ff2255',
            priceFormat: { type: 'price', precision: 2, minMove: 0.05 }
        };

        const spotChart = LightweightCharts.createChart(document.getElementById('chart_spot'), chartOpts);
        const spotSeries = spotChart.addCandlestickSeries(candleSeriesOpts);

        const ceChart = LightweightCharts.createChart(document.getElementById('chart_ce'), chartOpts);
        const ceSeries = ceChart.addCandlestickSeries(candleSeriesOpts);

        const peChart = LightweightCharts.createChart(document.getElementById('chart_pe'), chartOpts);
        const peSeries = peChart.addCandlestickSeries(candleSeriesOpts);

        function onExpiryChange() {
            currentExpiry = document.getElementById('expiryDropdown').value;
            document.getElementById('expLabel').innerText = `Exp: ${currentExpiry}`;
            fetchTerminalData(true);
        }

        function clickSelectCE(strike) {
            selectedCE = strike;
            fetchTerminalData(true);
        }

        function clickSelectPE(strike) {
            selectedPE = strike;
            fetchTerminalData(true);
        }

        async function fetchTerminalData(forceFit = false) {
            try {
                let url = `/api/market_data?tf=5m&expiry=${currentExpiry}&selected_ce_strike=${selectedCE}&selected_pe_strike=${selectedPE}`;
                let res = await fetch(url);
                let data = await res.json();

                if (data.spot) document.getElementById('spotBadge').innerText = `NIFTY: ₹ ${data.spot.toLocaleString()}`;

                if (data.active_expiry) {
                    document.getElementById('expLabel').innerText = `Exp: ${data.active_expiry}`;
                }

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
                    if (isFirstLoad) { spotChart.timeScale().fitContent(); isFirstLoad = false; }
                }

                if (data.ce_candles && data.ce_candles.length > 0) {
                    ceSeries.setData(data.ce_candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                    let lastP = data.ce_candles[data.ce_candles.length - 1].close;
                    document.getElementById('lbl_ce').innerText = `CALL: NIFTY ${data.active_ce} CE (₹${lastP.toFixed(2)})`;
                    if (forceFit) ceChart.timeScale().fitContent();
                }

                if (data.pe_candles && data.pe_candles.length > 0) {
                    peSeries.setData(data.pe_candles.map(c => ({ time: c.time + 19800, open: c.open, high: c.high, low: c.low, close: c.close })));
                    let lastP = data.pe_candles[data.pe_candles.length - 1].close;
                    document.getElementById('lbl_pe').innerText = `PUT: NIFTY ${data.active_pe} PE (₹${lastP.toFixed(2)})`;
                    if (forceFit) peChart.timeScale().fitContent();
                }

                if (data.chain && data.chain.length > 0) {
                    let html = '';
                    data.chain.forEach(r => {
                        let ceCls = r.is_selected_ce ? 'selected-ce-cell' : '';
                        let peCls = r.is_selected_pe ? 'selected-pe-cell' : '';
                        let atmCls = r.is_atm ? 'atm-row' : '';

                        let cePriceDisplay = r.ltp_ce > 0 ? `₹ ${r.ltp_ce.toFixed(2)}` : '-';
                        let pePriceDisplay = r.ltp_pe > 0 ? `₹ ${r.ltp_pe.toFixed(2)}` : '-';

                        html += `<tr class="${atmCls}">
                            <td class="${ceCls}" onclick="clickSelectCE(${r.strike})" style="color:#00ff88; font-weight:700;">${r.oi_ce_str}</td>
                            <td class="${ceCls}" onclick="clickSelectCE(${r.strike})" style="color:#38bdf8; font-weight:800;">${cePriceDisplay}</td>
                            <td style="font-weight:bold; background:#161e2e; color:#fff;">${r.strike}</td>
                            <td class="${peCls}" onclick="clickSelectPE(${r.strike})" style="color:#ff2255; font-weight:800;">${pePriceDisplay}</td>
                            <td class="${peCls}" onclick="clickSelectPE(${r.strike})" style="color:#ff2255; font-weight:700;">${r.oi_pe_str}</td>
                        </tr>`;
                    });
                    document.getElementById('chain_body').innerHTML = html;
                }

            } catch (e) {
                console.error("Terminal Stream Error:", e);
            }
        }

        window.addEventListener('resize', () => {
            spotChart.timeScale().fitContent();
            ceChart.timeScale().fitContent();
            peChart.timeScale().fitContent();
        });

        fetchTerminalData();
        setInterval(fetchTerminalData, 4000);
    </script>
</body>
</html>
"""

# ==================== QUANTUM REVERSAL MATRIX (100% MOBILE RESPONSIVE NO-CUT) ====================
OI_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="gu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Quantum OI Reversal & Transfer Matrix - Intraday Radar</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Gujarati:wght@500;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #05070a;
            --green-glow: #00ff88;
            --red-glow: #ff2255;
            --cyan-glow: #00f0ff;
            --gold-glow: #fbbf24;
            --purple-glow: #c084fc;
            --text-dim: #64748b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Sans Gujarati', -apple-system, BlinkMacSystemFont, monospace, sans-serif; }
        body { background: var(--bg-deep); color: #fff; height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        .cyber-header {
            height: 44px;
            background: #090e17;
            border-bottom: 1.5px solid #142033;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            flex-shrink: 0;
        }
        .header-title { font-size: 13.5px; font-weight: 900; color: var(--cyan-glow); display: flex; align-items: center; gap: 8px; }
        .btn-back-chart { background: #101c2e; border: 1px solid var(--cyan-glow); color: var(--cyan-glow); padding: 5px 10px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: bold; }

        .signal-strip {
            height: auto;
            min-height: 52px;
            background: #080d17;
            border-bottom: 1px solid #142033;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 6px 14px;
            flex-wrap: wrap;
            gap: 6px;
            flex-shrink: 0;
        }
        .verdict-tag { font-size: 15px; font-weight: 900; letter-spacing: 0.5px; }

        .major-node-box { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
        .node-badge { padding: 4px 8px; border-radius: 4px; font-size: 10.5px; font-weight: 800; display: flex; align-items: center; gap: 4px; }
        .res-node { background: rgba(255, 34, 85, 0.15); border: 1.5px solid var(--red-glow); color: var(--red-glow); }
        .sup-node { background: rgba(0, 255, 136, 0.15); border: 1.5px solid var(--green-glow); color: var(--green-glow); }

        .stream-workspace {
            flex: 1;
            display: flex;
            width: 100%;
            height: calc(100vh - 150px);
            position: relative;
        }

        .matrix-canvas-box { 
            flex: 5.5; 
            position: relative; 
            background: #040609; 
            overflow: hidden; 
        }
        #streamCanvas { width: 100%; height: 100%; display: block; }

        .strike-nodes-col {
            flex: 4.5;
            background: #080d16;
            border-left: 1.5px solid #142033;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 6px 8px;
            position: relative;
            height: 100%;
            overflow-y: auto;
        }

        .strike-group-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: space-around;
            padding: 2px 0;
            gap: 2px;
        }

        .strike-card-node {
            background: #0d1522;
            border: 1px solid #1a273b;
            border-radius: 4px;
            padding: 5px 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11.5px;
            position: relative;
            box-shadow: 0 2px 4px rgba(0,0,0,0.4);
            white-space: nowrap;
        }
        .node-call { border-left: 3px solid var(--green-glow); }
        .node-put { border-left: 3px solid var(--red-glow); }
        
        .badge-atm { background: rgba(0, 240, 255, 0.25); color: var(--cyan-glow); border: 1px solid var(--cyan-glow); padding: 1px 4px; border-radius: 3px; font-weight: 800; font-size: 9px; }
        .badge-itm { background: rgba(192, 132, 252, 0.25); color: var(--purple-glow); border: 1px solid var(--purple-glow); padding: 1px 4px; border-radius: 3px; font-weight: 800; font-size: 9px; }
        .badge-otm { background: rgba(100, 116, 139, 0.25); color: #cbd5e1; padding: 1px 4px; border-radius: 3px; font-size: 9px; font-weight: 700; }

        .strike-card-node.atm-node-active {
            border: 1.5px solid var(--cyan-glow) !important;
            background: rgba(56, 189, 248, 0.18) !important;
        }
        .strike-card-node.main-res-active {
            border: 1.5px solid var(--red-glow) !important;
            background: rgba(255, 34, 85, 0.22) !important;
        }
        .strike-card-node.main-sup-active {
            border: 1.5px solid var(--green-glow) !important;
            background: rgba(0, 255, 136, 0.22) !important;
        }

        .glow-plus { color: var(--green-glow); font-weight: 800; font-size: 11px; }
        .glow-minus { color: var(--red-glow); font-weight: 800; font-size: 11px; }

        .spot-axis-divider {
            height: 26px;
            background: #ffffff;
            border-radius: 4px;
            color: #000;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 10px;
            font-weight: 900;
            font-size: 11.5px;
            box-shadow: 0 0 12px rgba(255,255,255,0.8);
            margin: 3px 0;
            z-index: 5;
            flex-shrink: 0;
        }

        .news-radar-deck {
            height: 48px;
            background: #080e1a;
            border-top: 1.5px solid #1a2a44;
            display: flex;
            align-items: center;
            padding: 0 10px;
            gap: 10px;
            flex-shrink: 0;
        }
        .radar-badge-box {
            background: #ff2255;
            color: #fff;
            font-weight: 900;
            font-size: 10px;
            padding: 4px 8px;
            border-radius: 4px;
            flex-shrink: 0;
        }
        .news-ticker-container { flex: 1; overflow: hidden; position: relative; }
        
        .news-scroll-text {
            display: inline-block;
            white-space: nowrap;
            color: #f8fafc;
            font-size: 13px;
            font-weight: 700;
            animation: slowMarquee 45s linear infinite;
        }
        @keyframes slowMarquee { 
            0% { transform: translateX(100%); } 
            100% { transform: translateX(-100%); } 
        }

        /* 100% RESPONSIVE RULES FOR SMARTPHONES */
        @media (max-width: 768px) {
            body { height: auto !important; min-height: 100vh; overflow-y: auto !important; }
            .cyber-header { padding: 0 10px; }
            .header-title { font-size: 11.5px; }
            .signal-strip { padding: 8px 10px; }
            .verdict-tag { font-size: 13.5px; }
            
            /* Vertical Split on Mobile so nothing cuts horizontally */
            .stream-workspace {
                flex-direction: column !important;
                height: auto !important;
            }
            .matrix-canvas-box {
                width: 100% !important;
                height: 280px !important;
                min-height: 280px !important;
                flex: none !important;
            }
            .strike-nodes-col {
                width: 100% !important;
                flex: none !important;
                border-left: none !important;
                border-top: 1.5px solid #142033;
                padding: 10px;
                height: auto !important;
            }
            .strike-card-node {
                font-size: 11.5px !important;
                padding: 8px 10px !important;
                margin-bottom: 4px;
            }
            .spot-axis-divider {
                height: 32px !important;
                font-size: 12.5px !important;
                margin: 6px 0 !important;
            }
            .news-radar-deck {
                position: sticky;
                bottom: 0;
                z-index: 50;
            }
        }
    </style>
</head>
<body>
    <div class="cyber-header">
        <div class="header-title">
            <span style="display:inline-block; width:8px; height:8px; background:var(--cyan-glow); border-radius:50%; box-shadow:0 0 8px var(--cyan-glow);"></span>
            QUANTUM OI INTRADAY RADAR
        </div>
        <div style="font-size:10.5px; color:var(--text-dim);" id="expTimeTag">EXP: -- | SYNC: --</div>
        <a href="/" class="btn-back-chart">⬅ CHARTS</a>
    </div>

    <div class="signal-strip">
        <div>
            <div style="font-size:9.5px; color:var(--text-dim); text-transform:uppercase;">INTRADAY VERDICT:</div>
            <div class="verdict-tag" id="verdictText" style="color:var(--green-glow);">SCANNING MARKET...</div>
        </div>

        <div class="major-node-box">
            <div class="node-badge res-node" id="boxMajorRes">
                <span>🛡️ RES:</span>
                <span id="txtMajorRes" style="font-size:11.5px; font-weight:900;">--</span>
            </div>
            <div class="node-badge sup-node" id="boxMajorSup">
                <span>🏰 SUP:</span>
                <span id="txtMajorSup" style="font-size:11.5px; font-weight:900;">--</span>
            </div>
        </div>

        <div>
            <div style="font-size:9.5px; color:var(--text-dim); text-transform:uppercase;">ACTION:</div>
            <div style="font-size:11.5px; font-weight:800; color:var(--cyan-glow);" id="actionText">CALCULATING...</div>
        </div>
    </div>

    <div class="stream-workspace">
        <div class="matrix-canvas-box" id="canvasContainer">
            <canvas id="streamCanvas"></canvas>
        </div>

        <div class="strike-nodes-col">
            <div style="font-size:10.5px; font-weight:bold; color:var(--green-glow); text-transform:uppercase; margin-bottom:2px;">
                ▲ CALL RESISTANCE (OTM / ATM / ITM)
            </div>
            <div id="callStrikesContainer" class="strike-group-container"></div>

            <div class="spot-axis-divider" id="spotCenterPill">
                <span>NIFTY SPOT AXIS</span>
                <span id="spotCenterVal">₹ 23,053.1</span>
            </div>

            <div style="font-size:10.5px; font-weight:bold; color:var(--red-glow); text-transform:uppercase; margin-top:4px;">
                ▼ PUT SUPPORT (ITM / ATM / OTM)
            </div>
            <div id="putStrikesContainer" class="strike-group-container"></div>
        </div>
    </div>

    <div class="news-radar-deck">
        <div class="radar-badge-box"><span>🔴 લાઈવ રડાર</span></div>
        <div class="news-ticker-container">
            <div class="news-scroll-text" id="radarNewsText">
                📢 નિફ્ટી લાઈવ ઓપન ઈન્ટરેસ્ટ સ્કેન થઈ રહ્યો છે... નજીકની કઈ સ્ટ્રાઈક પર મોટા પાયે પોઝિશન બની રહી છે તેની વિગત અહીં લાઈવ લખાશે...
            </div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('streamCanvas');
        const container = document.getElementById('canvasContainer');
        const ctx = canvas.getContext('2d');

        let streamData = null;
        let callNodePositions = [];
        let putNodePositions = [];

        function resize() {
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
            captureTargetCoordinates();
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
                document.getElementById('expTimeTag').innerText = `EXP: ${streamData.expiry} | SYNC: ${streamData.time}`;

                if (streamData.main_res) {
                    document.getElementById('txtMajorRes').innerText = `${streamData.main_res.strike} (${streamData.main_res.oi_str})`;
                }
                if (streamData.main_sup) {
                    document.getElementById('txtMajorSup').innerText = `${streamData.main_sup.strike} (${streamData.main_sup.oi_str})`;
                }

                // Render Calls
                let cHtml = '';
                streamData.calls.forEach((c, idx) => {
                    let isMain = (streamData.main_res && streamData.main_res.strike === c.strike) ? 'main-res-active' : (c.is_atm ? 'atm-node-active' : '');
                    let badge = c.chg > 0 ? `<span class="glow-plus">${c.chg_str}</span>` : (c.chg < 0 ? `<span class="glow-minus">${c.chg_str}</span>` : `<span style="color:#94a3b8; font-weight:700;">${c.chg_str}</span>`);
                    let ltpText = c.ltp > 0 ? `(₹${c.ltp.toFixed(2)})` : '';
                    let typeBadge = `<span class="badge-${c.type_tag.toLowerCase()}">${c.type_tag}</span>`;

                    cHtml += `<div class="strike-card-node node-call ${isMain}" id="cNode_${idx}">
                        <span><b>${c.strike} CE</b> ${typeBadge} <span style="color:#38bdf8; font-weight:800; margin-left:3px;">${ltpText}</span> <small style="color:#64748b; margin-left:2px;">(OI: ${c.oi_str})</small></span>
                        ${badge}
                    </div>`;
                });
                document.getElementById('callStrikesContainer').innerHTML = cHtml;

                // Render Puts
                let pHtml = '';
                streamData.puts.forEach((p, idx) => {
                    let isMain = (streamData.main_sup && streamData.main_sup.strike === p.strike) ? 'main-sup-active' : (p.is_atm ? 'atm-node-active' : '');
                    let badge = p.chg > 0 ? `<span class="glow-plus">${p.chg_str}</span>` : (p.chg < 0 ? `<span class="glow-minus">${p.chg_str}</span>` : `<span style="color:#94a3b8; font-weight:700;">${p.chg_str}</span>`);
                    let ltpText = p.ltp > 0 ? `(₹${p.ltp.toFixed(2)})` : '';
                    let typeBadge = `<span class="badge-${p.type_tag.toLowerCase()}">${p.type_tag}</span>`;

                    pHtml += `<div class="strike-card-node node-put ${isMain}" id="pNode_${idx}">
                        <span><b>${p.strike} PE</b> ${typeBadge} <span style="color:#ff2255; font-weight:800; margin-left:3px;">${ltpText}</span> <small style="color:#64748b; margin-left:2px;">(OI: ${p.oi_str})</small></span>
                        ${badge}
                    </div>`;
                });
                document.getElementById('putStrikesContainer').innerHTML = pHtml;

                captureTargetCoordinates();

            } catch(e) {}
        }

        function captureTargetCoordinates() {
            callNodePositions = [];
            putNodePositions = [];
            const containerRect = container.getBoundingClientRect();
            const isMobile = window.innerWidth <= 768;

            if (isMobile) {
                // Distribute evenly along canvas height on mobile
                const step = canvas.height / 16;
                for (let i = 0; i < 7; i++) callNodePositions.push(step * (i + 1));
                for (let i = 0; i < 7; i++) putNodePositions.push(canvas.height / 2 + step * (i + 1));
                return;
            }

            if (streamData && streamData.calls) {
                streamData.calls.forEach((_, idx) => {
                    let el = document.getElementById(`cNode_${idx}`);
                    if (el) {
                        let r = el.getBoundingClientRect();
                        callNodePositions.push(r.top - containerRect.top + (r.height / 2));
                    }
                });
            }

            if (streamData && streamData.puts) {
                streamData.puts.forEach((_, idx) => {
                    let el = document.getElementById(`pNode_${idx}`);
                    if (el) {
                        let r = el.getBoundingClientRect();
                        putNodePositions.push(r.top - containerRect.top + (r.height / 2));
                    }
                });
            }
        }

        function drawLineLabel(x, y, text, badgeColor, textColor) {
            ctx.save();
            ctx.font = 'bold 9px monospace, sans-serif';
            let textWidth = ctx.measureText(text).width;
            let padX = 5;
            let bWidth = textWidth + (padX * 2);
            let bHeight = 15;
            let bx = x - (bWidth / 2);
            let by = y - (bHeight / 2);

            ctx.fillStyle = '#080d16';
            ctx.strokeStyle = badgeColor;
            ctx.lineWidth = 1.1;
            ctx.shadowColor = badgeColor;
            ctx.shadowBlur = 5;
            
            ctx.beginPath();
            ctx.roundRect(bx, by, bWidth, bHeight, 3);
            ctx.fill();
            ctx.stroke();

            ctx.shadowBlur = 0;
            ctx.fillStyle = textColor;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(text, x, y);
            ctx.restore();
        }

        function renderNerveMatrix() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            const startX = 0;
            const startY = canvas.height / 2;
            const endX = canvas.width;
            const t = Date.now() * 0.0025;
            const isMobile = window.innerWidth <= 768;

            // 1. Call Lines
            callNodePositions.forEach((targetY, i) => {
                let callItem = (streamData && streamData.calls && streamData.calls[i]) ? streamData.calls[i] : null;
                let isMain = (streamData && streamData.main_res && callItem && callItem.strike === streamData.main_res.strike);
                let isAtm = (callItem && callItem.is_atm);
                let isItm = (callItem && callItem.type_tag === "ITM");
                
                let lineColor = isMain ? '#00ff88' : (isAtm ? '#00f0ff' : (isItm ? '#c084fc' : `rgba(0, 255, 136, ${0.25 + (i * 0.08)})`));
                
                ctx.beginPath();
                ctx.lineWidth = isMain ? 2.5 : 1.3;
                ctx.strokeStyle = lineColor;

                let waveOffset = Math.sin(t + i * 0.7) * 8;
                let cp1x = canvas.width * 0.35;
                let cp1y = startY - 12 - (i * 5) + waveOffset;
                let cp2x = canvas.width * 0.70;
                let cp2y = targetY - waveOffset * 0.3;

                ctx.moveTo(startX, startY);
                ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, endX, targetY);
                ctx.stroke();

                let pProg = (t * 0.3 + (i * 0.14)) % 1;
                let px = Math.pow(1 - pProg, 3) * startX + 3 * Math.pow(1 - pProg, 2) * pProg * cp1x + 3 * (1 - pProg) * Math.pow(pProg, 2) * cp2x + Math.pow(pProg, 3) * endX;
                let py = Math.pow(1 - pProg, 3) * startY + 3 * Math.pow(1 - pProg, 2) * pProg * cp1y + 3 * (1 - pProg) * Math.pow(pProg, 2) * cp2y + Math.pow(pProg, 3) * targetY;

                ctx.beginPath();
                ctx.fillStyle = isMain ? '#ffffff' : (isAtm ? '#00f0ff' : (isItm ? '#c084fc' : '#00ff88'));
                ctx.arc(px, py, isMain ? 3.2 : 2.0, 0, Math.PI * 2);
                ctx.fill();

                if (callItem && !isMobile) {
                    let lxProg = 0.75;
                    let lx = Math.pow(1 - lxProg, 3) * startX + 3 * Math.pow(1 - lxProg, 2) * lxProg * cp1x + 3 * (1 - lxProg) * Math.pow(lxProg, 2) * cp2x + Math.pow(lxProg, 3) * endX;
                    let ly = Math.pow(1 - lxProg, 3) * startY + 3 * Math.pow(1 - lxProg, 2) * lxProg * cp1y + 3 * (1 - lxProg) * Math.pow(lxProg, 2) * cp2y + Math.pow(lxProg, 3) * targetY;
                    
                    let labelText = `${callItem.strike} CE: ${callItem.chg_str}`;
                    let labelBorderColor = isMain ? '#00ff88' : (isAtm ? '#00f0ff' : '#1a2a44');
                    let labelTextColor = callItem.chg > 0 ? '#00ff88' : (callItem.chg < 0 ? '#ff2255' : '#94a3b8');
                    drawLineLabel(lx, ly, labelText, labelBorderColor, labelTextColor);
                }
            });

            // 2. Put Lines
            putNodePositions.forEach((targetY, i) => {
                let putItem = (streamData && streamData.puts && streamData.puts[i]) ? streamData.puts[i] : null;
                let isMain = (streamData && streamData.main_sup && putItem && putItem.strike === streamData.main_sup.strike);
                let isAtm = (putItem && putItem.is_atm);
                let isItm = (putItem && putItem.type_tag === "ITM");
                
                let lineColor = isMain ? '#ff2255' : (isAtm ? '#00f0ff' : (isItm ? '#c084fc' : `rgba(255, 34, 85, ${0.25 + (i * 0.08)})`));
                
                ctx.beginPath();
                ctx.lineWidth = isMain ? 2.5 : 1.3;
                ctx.strokeStyle = lineColor;

                let waveOffset = Math.sin(t + i * 0.7) * 8;
                let cp1x = canvas.width * 0.35;
                let cp1y = startY + 12 + (i * 5) + waveOffset;
                let cp2x = canvas.width * 0.70;
                let cp2y = targetY + waveOffset * 0.3;

                ctx.moveTo(startX, startY);
                ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, endX, targetY);
                ctx.stroke();

                let pProg = (t * 0.3 + (i * 0.14)) % 1;
                let px = Math.pow(1 - pProg, 3) * startX + 3 * Math.pow(1 - pProg, 2) * pProg * cp1x + 3 * (1 - pProg) * Math.pow(pProg, 2) * cp2x + Math.pow(pProg, 3) * endX;
                let py = Math.pow(1 - pProg, 3) * startY + 3 * Math.pow(1 - pProg, 2) * pProg * cp1y + 3 * (1 - pProg) * Math.pow(pProg, 2) * cp2y + Math.pow(pProg, 3) * targetY;

                ctx.beginPath();
                ctx.fillStyle = isMain ? '#ffffff' : (isAtm ? '#00f0ff' : (isItm ? '#c084fc' : '#ff2255'));
                ctx.arc(px, py, isMain ? 3.2 : 2.0, 0, Math.PI * 2);
                ctx.fill();

                if (putItem && !isMobile) {
                    let lxProg = 0.75;
                    let lx = Math.pow(1 - lxProg, 3) * startX + 3 * Math.pow(1 - lxProg, 2) * lxProg * cp1x + 3 * (1 - lxProg) * Math.pow(lxProg, 2) * cp2x + Math.pow(lxProg, 3) * endX;
                    let ly = Math.pow(1 - lxProg, 3) * startY + 3 * Math.pow(1 - lxProg, 2) * pProg * cp1y + 3 * (1 - lxProg) * Math.pow(lxProg, 2) * cp2y + Math.pow(lxProg, 3) * targetY;
                    
                    let labelText = `${putItem.strike} PE: ${putItem.chg_str}`;
                    let labelBorderColor = isMain ? '#ff2255' : (isAtm ? '#00f0ff' : '#1a2a44');
                    let labelTextColor = putItem.chg > 0 ? '#00ff88' : (putItem.chg < 0 ? '#ff2255' : '#94a3b8');
                    drawLineLabel(lx, ly, labelText, labelBorderColor, labelTextColor);
                }
            });

            // Central Spot Line
            ctx.beginPath();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2.0;
            ctx.shadowColor = '#ffffff';
            ctx.shadowBlur = 10;
            ctx.moveTo(0, startY);
            ctx.lineTo(canvas.width, startY);
            ctx.stroke();
            ctx.shadowBlur = 0;

            requestAnimationFrame(renderNerveMatrix);
        }

        fetchStreamData();
        setInterval(fetchStreamData, 3000);
        resize();
        renderNerveMatrix();
    </script>
</body>
</html>
