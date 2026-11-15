"""AgriShift AI assistant (mounted by the dashboard server at /assistant).

- Gemini API key stays on the server (read from .env in the project root, or an environment variable).
- Stage 1: source reading with Gemini (Google Search / URL reading when the key allows it).
- Stage 2: answer with live NASA POWER data + FAO-56/CROPWAT calculations as tools.
"""
import asyncio
import os
import math
import time
import datetime as dt
import collections
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

BASE = Path(__file__).parent


def load_env(p=None):
    p = p or (BASE.parent / ".env")
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
load_env(BASE / ".env")
KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
GURL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SOURCES = [
    ("Space Apps – Adapting Farms with NASA Data", "https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources"),
    ("FAO CROPWAT", "https://www.fao.org/land-water/resources/tools/software/cropwat/en"),
    ("NASA AppEEARS", "https://appeears.earthdatacloud.nasa.gov/"),
    ("NASA POWER", "https://power.larc.nasa.gov/data-access-viewer/"),
    ("FAO EcoCrop", "https://www.fao.org/geospatial/data-and-tools/data-portals/ecocrop/en"),
]

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
# Same-origin by default. Add your deployed domain(s) here if the page is hosted elsewhere.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",") if o],
    allow_methods=["POST", "GET"],
    allow_headers=["content-type"],
)

# ---------------------------------------------------------------- NASA POWER + FAO-56 tools
CROPS = {
    "قمح": ("Poaceae", 0, 150, [.3, 1.15, .3], [15, 23], [5, 27]),
    "ذرة": ("Poaceae", 0, 120, [.3, 1.2, .6], [20, 30], [10, 38]),
    "أرز": ("Poaceae", 0, 135, [1.05, 1.2, .9], [22, 30], [15, 38]),
    "برسيم": ("Fabaceae", 1, 150, [.4, 1.15, 1.1], [15, 25], [5, 35]),
    "فول": ("Fabaceae", 1, 140, [.5, 1.15, .3], [12, 22], [3, 30]),
    "عدس": ("Fabaceae", 1, 110, [.4, 1.1, .3], [15, 24], [5, 32]),
    "فول سوداني": ("Fabaceae", 1, 120, [.4, 1.15, .6], [22, 30], [15, 38]),
    "طماطم": ("Solanaceae", 0, 130, [.6, 1.15, .8], [18, 26], [10, 35]),
    "بطاطس": ("Solanaceae", 0, 110, [.5, 1.15, .75], [15, 22], [7, 30]),
    "بصل": ("Amaryllidaceae", 0, 150, [.7, 1.05, .75], [12, 24], [5, 32]),
    "قطن": ("Malvaceae", 0, 180, [.35, 1.15, .7], [22, 32], [15, 40]),
    "بنجر سكر": ("Amaranthaceae", 0, 180, [.35, 1.2, .7], [15, 24], [5, 32]),
}
CN = list(CROPS)
MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MD = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
PW = "https://power.larc.nasa.gov/api/temporal/"
_clim = {}
ALIAS = {"wheat": "قمح", "maize": "ذرة", "corn": "ذرة", "rice": "أرز", "berseem": "برسيم", "clover": "برسيم",
         "faba": "فول", "fava": "فول", "broad bean": "فول", "lentil": "عدس", "peanut": "فول سوداني", "groundnut": "فول سوداني",
         "tomato": "طماطم", "potato": "بطاطس", "بطاطا": "بطاطس", "onion": "بصل", "cotton": "قطن", "sugar beet": "بنجر سكر", "beet": "بنجر سكر"}
NOT_BUILTIN = {"error": "crop is not in the built-in table; call custom_crop_plan with the parameters you found in the research notes (FAO EcoCrop / FAO-56 Kc)"}


def resolve(name):
    n = str(name).strip().lower()
    if n in CROPS:
        return n
    return ALIAS.get(n)


async def pw(client, path, params):
    q = {"community": "AG", "format": "JSON", **params}
    r = await client.get(PW + path, params=q, timeout=40)
    r.raise_for_status()
    return r.json()["properties"]["parameter"]


async def clim(client, lat, lon):
    k = f"{lat:.2f},{lon:.2f}"
    if k not in _clim:
        p = await pw(client, "climatology/point", {
            "parameters": "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR",
            "latitude": f"{lat:.2f}", "longitude": f"{lon:.2f}"})
        _clim[k] = {x: [p[x][m] for m in MON] for x in p}
    return _clim[k]


def ra(lat, n):
    ph = lat * math.pi / 180
    dr = 1 + .033 * math.cos(2 * math.pi * n / 365)
    d = .409 * math.sin(2 * math.pi * n / 365 - 1.39)
    ws = math.acos(max(-1, min(1, -math.tan(ph) * math.tan(d))))
    return 24 * 60 / math.pi * .082 * dr * (ws * math.sin(ph) * math.sin(d) + math.cos(ph) * math.cos(d) * math.sin(ws))


def eto(tn, tx, lat, n):  # Hargreaves
    return max(0, .0023 * ((tn + tx) / 2 + 17.8) * math.sqrt(max(tx - tn, 0)) * .408 * ra(lat, n))


def eff_r(p):
    return p * (125 - .2 * p) / 125 if p <= 250 else 125 + .1 * p


def score(t, o, a):
    if o[0] <= t <= o[1]:
        return 1
    if a[0] <= t < o[0]:
        return (t - a[0]) / (o[0] - a[0])
    if o[1] < t <= a[1]:
        return (a[1] - t) / (a[1] - o[1])
    return 0


def plan(crop, lat, c, sm, spec=None):
    fam, fx, days, kc, to, ta = spec or CROPS[crop]
    etc = pe = ts = 0.0
    for i in range(days):
        d = dt.date(2001, sm, 15) + dt.timedelta(days=i)
        m = d.month - 1
        fr = i / days
        if fr < .2:
            k = kc[0]
        elif fr < .45:
            k = kc[0] + (kc[1] - kc[0]) * (fr - .2) / .25
        elif fr < .8:
            k = kc[1]
        else:
            k = kc[1] + (kc[2] - kc[1]) * (fr - .8) / .2
        etc += k * eto(c["T2M_MIN"][m], c["T2M_MAX"][m], lat, d.timetuple().tm_yday)
        pe += eff_r(c["PRECTOTCORR"][m] * MD[m]) / MD[m]
        ts += c["T2M"][m]
    irr = max(0, etc - pe)
    tm = ts / days
    return {"crop": crop, "start_month": sm, "season_days": days, "mean_temp_c": round(tm, 1),
            "temp_suitability_0to1": round(score(tm, to, ta), 2), "crop_water_need_mm": round(etc),
            "effective_rain_mm": round(pe), "net_irrigation_mm": round(irr),
            "net_irrigation_m3_per_feddan": round(irr * 4.2),
            "note": "net before irrigation efficiency (flood irrigation ~55-60%); FAO-56 Kc x ETo (Hargreaves), CROPWAT logic"}


def _rank(crop, lat, c, spec=None):
    return sorted((plan(crop, lat, c, m, spec) for m in range(1, 13)),
                  key=lambda x: (-x["temp_suitability_0to1"], x["net_irrigation_mm"]))


async def t_crop_plan(client, a):
    k = resolve(a["crop"])
    if not k:
        return NOT_BUILTIN
    return plan(k, a["lat"], await clim(client, a["lat"], a["lon"]), int(a["start_month"]))


async def t_best_planting(client, a):
    k = resolve(a["crop"])
    if not k:
        return NOT_BUILTIN
    c = await clim(client, a["lat"], a["lon"])
    return {"crop": k, "top3_start_months": _rank(k, a["lat"], c)[:3]}


async def t_custom_crop_plan(client, a):
    """Any plant: the model passes agronomic parameters it found in EcoCrop / FAO-56 research."""
    try:
        spec = (str(a.get("family", "unknown")), 1 if a.get("is_legume") else 0, int(a["season_days"]),
                [float(a["kc_ini"]), float(a["kc_mid"]), float(a["kc_end"])],
                [float(a["t_opt_min"]), float(a["t_opt_max"])], [float(a["t_abs_min"]), float(a["t_abs_max"])])
    except (KeyError, ValueError, TypeError) as e:
        return {"error": f"missing or invalid parameter: {e}"}
    if not (20 <= spec[2] <= 400):
        return {"error": "season_days must be between 20 and 400"}
    c = await clim(client, a["lat"], a["lon"])
    name = str(a.get("crop", "custom"))[:40]
    if a.get("start_month"):
        return plan(name, a["lat"], c, int(a["start_month"]), spec)
    return {"crop": name, "top3_start_months": _rank(name, a["lat"], c, spec)[:3]}


async def t_rotation_advice(client, a):
    c = await clim(client, a["lat"], a["lon"])
    k = resolve(a["previous_crop"])
    if k:
        pv = CROPS[k]
    elif a.get("previous_family") is not None:
        pv = (str(a["previous_family"]), 1 if a.get("previous_is_legume") else 0)
    else:
        return {"error": "previous crop is not in the built-in table; pass previous_family (botanical family) and previous_is_legume"}
    out = []
    for n in CN:
        x = CROPS[n]
        if x[0] == pv[0]:
            continue
        b = _rank(n, a["lat"], c)[0]
        bonus = .25 if (x[1] and not pv[1]) else 0
        out.append({"next_crop": n,
                    "score": round(b["temp_suitability_0to1"] + bonus - b["net_irrigation_mm"] / 20000, 2),
                    "best_start_month": b["start_month"], "suitability": b["temp_suitability_0to1"],
                    "net_irrigation_m3_per_feddan": b["net_irrigation_m3_per_feddan"],
                    "why": ["different plant family (breaks pest/disease cycle)"] + (["legume fixes nitrogen"] if bonus else [])})
    return {"previous_crop": a["previous_crop"], "top3": sorted(out, key=lambda x: -x["score"])[:3]}


async def t_nasa_conditions(client, a):
    days = int(a.get("days", 30))
    e = dt.datetime.utcnow() - dt.timedelta(days=3)
    s = e - dt.timedelta(days=days - 1)
    f = lambda d: d.strftime("%Y%m%d")
    p = await pw(client, "daily/point", {
        "parameters": "T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,GWETROOT",
        "latitude": a["lat"], "longitude": a["lon"], "start": f(s), "end": f(e)})
    v = lambda k: [x for x in p[k].values() if x > -900]
    av = lambda arr: round(sum(arr) / len(arr), 1) if arr else None
    tx, tn, rain, rh = v("T2M_MAX"), v("T2M_MIN"), v("PRECTOTCORR"), v("RH2M")
    et = 0.0
    for d, mx in p["T2M_MAX"].items():
        mn = p["T2M_MIN"].get(d, -999)
        if mx > -900 and mn > -900:
            dd = dt.datetime.strptime(d, "%Y%m%d")
            et += eto(mn, mx, a["lat"], dd.timetuple().tm_yday)
    al = []
    if tx and max(tx) >= 38:
        al.append("heat wave: Tmax reached 38+ C")
    if tn and min(tn) <= 3:
        al.append("frost/cold risk")
    if av(rh) and av(tx) and av(rh) > 70 and 15 <= av(tx) <= 28:
        al.append("humid + mild: favorable for fungal diseases (indicator only)")
    if av(tx) and av(rh) and av(tx) > 33 and av(rh) < 40:
        al.append("hot and dry: favors spider mites / sucking insects (indicator only)")
    rs = sum(rain)
    return {"source": "NASA POWER (AG)", "period": f"{f(s)}-{f(e)}", "avg_tmax_c": av(tx), "avg_tmin_c": av(tn),
            "rain_total_mm": round(rs, 1), "avg_rh_pct": av(rh), "root_zone_soil_wetness_0to1": av(v("GWETROOT")),
            "eto_total_mm": round(et, 1), "water_balance_mm": round(rs - et, 1), "alerts": al}


FN = {"nasa_conditions": t_nasa_conditions, "crop_plan": t_crop_plan,
      "best_planting": t_best_planting, "rotation_advice": t_rotation_advice,
      "custom_crop_plan": t_custom_crop_plan}
LL = {"lat": {"type": "number"}, "lon": {"type": "number"}}
CR = {"type": "string", "description": "crop name, Arabic or English. Built-in: " + ", ".join(CN)}
DECL = [
    {"name": "nasa_conditions", "description": "Recent weather and soil moisture for the farm from NASA POWER, with heat/frost/disease alerts",
     "parameters": {"type": "object", "properties": {**LL, "days": {"type": "integer"}}, "required": ["lat", "lon"]}},
    {"name": "crop_plan", "description": "Water need and temperature suitability of a crop planted in a given month (FAO-56 / CROPWAT logic)",
     "parameters": {"type": "object", "properties": {"crop": CR, **LL, "start_month": {"type": "integer"}}, "required": ["crop", "lat", "lon", "start_month"]}},
    {"name": "best_planting", "description": "Best 3 planting months for a crop at the farm location",
     "parameters": {"type": "object", "properties": {"crop": CR, **LL}, "required": ["crop", "lat", "lon"]}},
    {"name": "rotation_advice", "description": "Best crops (among the built-in ones) to plant after the previous crop. For a previous crop outside the built-in list pass previous_family and previous_is_legume",
     "parameters": {"type": "object", "properties": {"previous_crop": CR, "previous_family": {"type": "string"}, "previous_is_legume": {"type": "boolean"}, **LL}, "required": ["previous_crop", "lat", "lon"]}},
    {"name": "custom_crop_plan", "description": "Planting-month ranking or water need for ANY plant (not only built-in crops), using its parameters from the research notes: season length, FAO-56 Kc (initial/mid/end), optimal and absolute temperature range from EcoCrop. Give start_month for one month, omit it for the best 3 months",
     "parameters": {"type": "object", "properties": {"crop": {"type": "string"}, "family": {"type": "string"}, "is_legume": {"type": "boolean"}, "season_days": {"type": "integer"},
                    "kc_ini": {"type": "number"}, "kc_mid": {"type": "number"}, "kc_end": {"type": "number"},
                    "t_opt_min": {"type": "number"}, "t_opt_max": {"type": "number"}, "t_abs_min": {"type": "number"}, "t_abs_max": {"type": "number"},
                    "start_month": {"type": "integer"}, **LL},
                    "required": ["crop", "season_days", "kc_ini", "kc_mid", "kc_end", "t_opt_min", "t_opt_max", "t_abs_min", "t_abs_max", "lat", "lon"]}},
]

# ---------------------------------------------------------------- prompts
RESEARCH_SYS = """You are the research stage of AgriShift, an agricultural assistant for farmers (mostly Egyptian).
First work out EXACTLY what the farmer asked: which plant(s) (any plant on Earth, not only common crops; use its scientific name too), and what they want (planting time, soil, water, fertilizer, pests, rotation, comparison, a decision, a how-to, general info...).
Then do DEEP research focused on THAT request:
1. Open the relevant seed pages with the URL tool: FAO EcoCrop (search the plant there: temperature, rainfall, pH, soil texture, salinity, cycle length, altitude, photoperiod), FAO CROPWAT (Kc values, growth stages, crop coefficients, irrigation logic), NASA POWER (parameters/variables relevant to the question), NASA AppEEARS (satellite products such as MODIS NDVI/ET/LAI or SMAP soil moisture that could monitor this crop), and the Space Apps "Adapting Farms with NASA Data" resources page.
2. Run several different Google searches (Arabic AND English, common + scientific names), with site: operators for fao.org, power.larc.nasa.gov, appeears.earthdatacloud.nasa.gov, earthdata.nasa.gov, spaceappschallenge.org; then reliable local sources (Egypt Ministry of Agriculture, Agricultural Research Center, universities, journals).
3. Output concise factual notes ONLY about what was asked: specific numbers and ranges, the source of each, where sources disagree. If the plant is not a standard crop, also give these model parameters when you can find them: botanical family, legume yes/no, season length in days, Kc initial/mid/end, optimal temperature range, absolute temperature range. Say "not found" for anything you could not find. Never invent values.
If the message is not about agriculture, plants, soil, water, weather for farming or farm decisions, write only: OFF_TOPIC."""

ANSWER_SYS = """أنت "أجري شيفت" (AgriShift)، مستشار زراعي ذكي من فريق NASA Space Apps 2026. بتتكلم مع فلاح أو باحث زي ما خبير بيتكلم مع واحد قدامه: بتفهم هو عايز إيه بالظبط وتجاوب عليه.
أنت عارف أي نبات (محاصيل، خضار، فاكهة، أشجار، نباتات زينة وطبية)، لأن عندك "ملاحظات بحث" من مصادر FAO EcoCrop وCROPWAT وNASA POWER وAppEEARS والويب في آخر رسالة للمستخدم.
طريقة الرد:
1. جاوب على سؤال المستخدم نفسه. لو سأل "أزرع إيه؟" ادّيه قرار وسبب. لو سأل عن آفة ادّيه التشخيص والعلاج. لو طلب مقارنة قارن. لو سلّم عليك أو سأل سؤال عام رد عادي وبسيط. ممنوع تعرض الداتا كأنها تقرير ثابت أو قالب واحد لكل الأسئلة.
2. الداتا (أرقام NASA وFAO) تتذكر بس لما بتدعم الإجابة، وتتقال بلغة بسيطة: "الشهر الأنسب نوفمبر لأن الحرارة في طنطا 17 درجة والري المطلوب حوالي 700 م³/فدان"، مش جدول أرقام.
3. استخدم الأدوات لما السؤال يخص مكان الفلاح: nasa_conditions للجو والرطوبة الحالية، best_planting وcrop_plan للمحاصيل الأساسية، وcustom_crop_plan لأي نبات تاني بمعاملاته من ملاحظات البحث، وrotation_advice للدورة. متخمّنش أرقام جو أو ري من دماغك.
4. خلي الإجابة على قد السؤال: سؤال بسيط = رد قصير ومباشر، سؤال معقد = تفصيل بعناوين قصيرة ونقاط. أول سطرين فيهم الخلاصة.
5. اتفاعل مع المحادثة: افتكر اللي اتقال قبل كده، وابني عليه. لو ناقص معلومة تغيّر الإجابة فعلًا (نوع التربة، مصدر المياه، المساحة) اسأل سؤال واحد بس في الآخر بعد ما تدّي أحسن إجابة ممكنة بافتراض معقول.
6. ممنوع "استشر مهندس زراعي" كإجابة. معلومات السلامة (مبيدات، جرعات) بتتقال جوه الإجابة. لو المصادر اختلفت اذكر النطاق وسبب الاختلاف، ولو معلومة مش مؤكدة قول كده.
7. نفس لغة المستخدم ولهجته (مصري لو كتب مصري). لو السؤال برة الزراعة قوله بلطف إنك متخصص في الزراعة وارجع للموضوع.
8. متكتبش سطر "المصادر" بنفسك، السيرفر بيضيفه.
9. لو مفيش "ملاحظات بحث" في آخر رسالة، جاوب من معرفتك الزراعية بالتفصيل وبأرقام ونطاقات محددة (حرارة مثلى ودنيا وعليا، pH، قوام التربة، الملوحة، المياه، المواعيد بالشهور، الآفات وطرق مكافحتها) بنفس منهج بيانات FAO EcoCrop وCROPWAT. متعتذرش إنك مقدرتش تبحث، وقول بس لو رقم معين مش مؤكد.
10. اضبط مستوى الشرح على اللي قدامك: فلاح بيسأل بكلام بسيط يتجاوب بكلام بسيط وأمثلة من الحقل ووحدات مألوفة (فدان، م³، شهر)، وباحث أو سؤال أكاديمي يتجاوب بدقة ومصطلحات علمية. ولو السؤال رسمي أو بالفصحى جاوب بفصحى مبسطة.
11. عن المشروع: AgriShift بيدعم تحدي Space Apps 2026 "Adapting Farms with NASA Data". بيربط بيانات NASA POWER (حرارة ومطر وإشعاع ورطوبة تربة) ومنهج FAO CROPWAT (الاحتياج المائي) وقاعدة FAO EcoCrop (متطلبات النبات) ومنتجات AppEEARS (زي NDVI من MODIS لمتابعة صحة المحصول من القمر الصناعي) لقرارات الدورة الزراعية والري. اشرح ده لو حد سأل.
12. لا تذكر أبدًا كلمات زي "ملاحظات البحث" أو "الأدوات" أو أسماء الدوال في ردك للمستخدم."""


# ---------------------------------------------------------------- Gemini helpers
class GeminiError(Exception):
    pass


MODELS = [MODEL] + [m.strip() for m in os.environ.get("GEMINI_FALLBACKS", "gemini-3.5-flash-lite").split(",")
                    if m.strip() and m.strip() != MODEL]
BAD = {}  # model -> unix time until which it is skipped (timed out or not available)
BLOCKED = {}  # tool name -> unix time until which it is skipped (google_search needs billing)


def uses(body, tool):
    return any(tool in t for t in body.get("tools", []))


async def gemini(client, body):
    """Main model first, then fallbacks. Retry once on 503. Fail fast if the tool itself is not allowed (429 + google_search)."""
    err = "no model available"
    now = time.time()
    order = [m for m in MODELS if BAD.get(m, 0) < now] or MODELS
    for model in order:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(2):
            try:
                r = await client.post(url, headers={"x-goog-api-key": KEY, "content-type": "application/json"}, json=body, timeout=45)
            except httpx.TimeoutException:
                err = f"timeout ({model})"
                BAD[model] = time.time() + 300
                break
            if r.status_code < 400:
                print("[gemini] served by", model)
                return r.json()
            try:
                msg = r.json().get("error", {}).get("message", "")
            except Exception:
                msg = ""
            err = f"{r.status_code}: {msg[:200]}"  # never includes the key
            if r.status_code == 503 and attempt == 0:
                await asyncio.sleep(2)
                continue
            if r.status_code == 429 and uses(body, "google_search"):
                raise GeminiError(err)
            if r.status_code in (404, 503):
                BAD[model] = time.time() + 300
            elif r.status_code == 429 and not uses(body, "url_context"):  # tool-specific 429s must not demote the model
                BAD[model] = time.time() + 90  # per-minute or daily limit reached: use the next model for a while
            break
    raise GeminiError(err)


def text_of(resp):
    parts = (resp.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))


def links_of(resp):
    out = []
    c = (resp.get("candidates") or [{}])[0]
    for ch in (c.get("groundingMetadata") or {}).get("groundingChunks", []):
        w = ch.get("web") or {}
        if w.get("uri"):
            out.append((w.get("title") or w["uri"], w["uri"]))
    for u in (c.get("urlContextMetadata") or {}).get("urlMetadata", []):
        if u.get("retrievedUrl") and "SUCCESS" in str(u.get("urlRetrievalStatus", "")):
            out.append((u["retrievedUrl"].split("/")[2], u["retrievedUrl"]))
    return out


async def research(client, question, history_text, place):
    prompt = (f"Farmer location: {place}\nToday: {dt.date.today().isoformat()}\n\nRecent conversation:\n{history_text}\n\n"
              f"Farmer's question: {question}\n\nSeed pages:\n" + "\n".join(u for _, u in SOURCES))
    base = {"systemInstruction": {"parts": [{"text": RESEARCH_SYS}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    now = time.time()
    combos = []
    if BLOCKED.get("google_search", 0) < now:
        combos.append(([{"google_search": {}}, {"url_context": {}}], "google_search"))
    if BLOCKED.get("url_context", 0) < now:
        combos.append(([{"url_context": {}}], "url_context"))
    for tools, name in combos:  # no combos left = skip research, the answer stage uses its own knowledge + NASA tools
        try:
            r = await gemini(client, dict(base, tools=tools))
            return text_of(r), links_of(r)
        except GeminiError as e:
            print("research attempt failed:", e)
            hard = any(c in str(e) for c in ("429", "400", "403", "404"))
            BLOCKED[name] = time.time() + (1800 if hard else 120)
    return "", []


async def answer(client, contents, lang, notes, place, lat, lon):
    sys = ANSWER_SYS + f"\nمكان الفلاح: {place} (lat={lat}, lon={lon}). النهاردة: {dt.date.today().isoformat()}."
    if lang == "en":
        sys += "\nThe user chose English: write the whole answer in English."
    used = set()
    for _ in range(6):
        r = await gemini(client, {"systemInstruction": {"parts": [{"text": sys}]}, "contents": contents,
                                  "tools": [{"functionDeclarations": DECL}],
                                  "generationConfig": {"maxOutputTokens": 4000}})
        cand = (r.get("candidates") or [{}])[0]
        content = cand.get("content") or {"role": "model", "parts": []}
        calls = [p["functionCall"] for p in content.get("parts", []) if "functionCall" in p]
        if not calls:
            return text_of(r), used
        contents.append(content)  # keep the model turn untouched (thought signatures)
        res = []
        for c in calls:
            used.add(c["name"])
            try:
                o = await FN[c["name"]](client, c.get("args", {}))
            except Exception as e:
                o = {"error": str(e)[:200]}
            res.append({"functionResponse": {"name": c["name"], "response": {"result": o}}})
        contents.append({"role": "user", "parts": res})
    raise GeminiError("too many tool steps")


# ---------------------------------------------------------------- API
HITS = collections.defaultdict(collections.deque)


def limited(ip, n=15, per=60):
    q = HITS[ip]
    now = time.time()
    while q and now - q[0] > per:
        q.popleft()
    if len(q) >= n:
        return True
    q.append(now)
    return False




@app.get("/api/health")
async def health():
    return {"ok": bool(KEY), "models_in_order": MODELS}


@app.post("/api/chat")
async def chat(req: Request):
    ip = req.client.host if req.client else "?"
    if limited(ip):
        return JSONResponse({"error": "too many requests, slow down"}, status_code=429)
    if not KEY:
        return JSONResponse({"error": "server is not configured"}, status_code=503)
    try:
        j = await req.json()
        msgs = [m for m in j["messages"] if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)][-12:]
        lat, lon = float(j["lat"]), float(j["lon"])
        place = str(j.get("place", ""))[:80]
        lang = "en" if j.get("lang") == "en" else "ar"
        if not msgs or msgs[-1]["role"] != "user" or not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError
        msgs = [{"role": m["role"], "content": m["content"][:2000]} for m in msgs]
        if not msgs[-1]["content"].strip():
            raise ValueError("empty message")
    except Exception:
        return JSONResponse({"error": "bad request"}, status_code=400)

    question = msgs[-1]["content"]
    hist_txt = "\n".join(f'{m["role"]}: {m["content"][:400]}' for m in msgs[:-1][-4:])
    try:
        async with httpx.AsyncClient() as client:
            notes, links = await research(client, question, hist_txt, place)
            contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in msgs[:-1]]
            if notes.strip() == "OFF_TOPIC":
                last = question
            else:
                last = f"{question}\n\n--- ملاحظات بحث (من مصادر NASA وFAO والويب) ---\n{notes}"
            contents.append({"role": "user", "parts": [{"text": last}]})
            reply, used = await answer(client, contents, lang, notes, place, lat, lon)
    except Exception as e:  # GeminiError, network errors...
        print("chat error:", repr(e)[:300])
        low = str(e).lower()
        detail = ("الحد المجاني من جوجل اتعدى، استنى دقيقة وجرّب تاني" if "429" in low else
                  "جوجل بطيئة دلوقتي، جرّب تاني بعد شوية" if ("timeout" in low or "503" in low) else str(e)[:160])
        return JSONResponse({"error": "ai backend error", "detail": detail}, status_code=502)

    want = []
    if used & {"nasa_conditions", "crop_plan", "best_planting", "custom_crop_plan", "rotation_advice"}:
        want.append("POWER")
    if used & {"crop_plan", "best_planting", "custom_crop_plan", "rotation_advice"}:
        want.append("CROPWAT")
    seen, src = set(), []
    for title, url in [(t, u) for t, u in SOURCES if any(w in t for w in want)] + links:
        if url not in seen and len(src) < 10:
            seen.add(url)
            src.append(f"[{title}]({url})")
    if src:
        reply = reply.strip() + "\n\n" + ("Sources: " if lang == "en" else "المصادر: ") + " · ".join(src)
    return {"reply": reply.strip()}
