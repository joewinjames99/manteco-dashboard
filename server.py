"""
Manteco Price Resilience — Cloud Server
========================================
Flask backend with persistent JSON storage.
Serves the dashboard HTML and all API routes.
Deploy to Railway, Render, or any cloud host.

Environment variables to set in Railway dashboard:
  ANTHROPIC_API_KEY   — your Anthropic key (optional, for scraping)
  SECRET_KEY          — any random string e.g. "manteco2026abc"
"""

import os, re, json, time, hashlib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, Response, stream_with_context, send_file
from flask_cors import CORS

app = Flask(__name__, static_folder=None)
CORS(app)

# ── Config ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SECRET_KEY        = os.environ.get("SECRET_KEY", "manteco2026")
MODEL             = "claude-haiku-4-5-20251001"
MAX_TEXT_CHARS    = 6000
REQUEST_TIMEOUT   = 25
DATA_FILE         = Path(os.environ.get("DATA_PATH", "data/manteco_data.json"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

CHANNEL_MAP = {
    "luxury": ["loropiana","zegna","brunello","ermenegildo","brioni","kiton"],
    "resell": ["grailed","vestiaire","stockx","depop","therealreal","ebay","poshmark","thredup"],
}

DOMAIN_BRAND_MAP = {
    "woolrich.com":"Woolrich","naadam.co":"NAADAM","zara.com":"Zara",
    "mango.com":"Mango","cos.com":"COS","loropiana.com":"Loro Piana",
    "zegna.com":"Ermenegildo Zegna","brunellocucinelli.com":"Brunello Cucinelli",
    "mrporter.com":"Mr Porter","farfetch.com":"Farfetch","ssense.com":"SSENSE",
    "grailed.com":"Grailed","ebay.com":"eBay",
    "vestiairecollective.com":"Vestiaire Collective","24s.com":"24S",
    "karenmillen.com":"Karen Millen","samsoe.com":"Samsøe Samsøe",
    "macys.com":"Macy's","nordstrom.com":"Nordstrom",
}

# ── Default data ──────────────────────────────────────────────────────────────
DEFAULT_DATA = {
    "pairs": [
        {"id":"P01","brand":"Woolrich","tier":"Premium","cat":"Coat","season":"FW24",
         "m_name":"Coat in Manteco Recycled Wool Blend","m_retail":None,"m_sale":None,"m_resale":None,
         "m_url":"https://www.woolrich.com/us/en/coat-in-manteco-recycled-wool-blend-CFWOOU0821MRUT3518_734.html",
         "c_name":"Coat in Recycled Italian Wool Blend","c_retail":None,"c_sale":None,"c_resale":None,
         "c_url":"https://www.woolrich.com/us/en/coat-in-recycled-italian-wool-blend-CFWOOU0827MRUT3109_3989A.html"},
        {"id":"P02","brand":"Woolrich","tier":"Premium","cat":"Coat","season":"FW24",
         "m_name":"2-in-1 Sideline Coat in Manteco Recycled Wool Blend","m_retail":1320,"m_sale":925,"m_resale":None,
         "m_url":"https://www.woolrich.com/us/en/2-in-1-sideline-coat-in-manteco-recycled-wool-blend-CFWWOU0943FRUT3492_7391.html",
         "c_name":"Standard Wool Coat (control TBD)","c_retail":None,"c_sale":None,"c_resale":None,
         "c_url":"https://www.woolrich.com/us/en/women/outerwear/coats/"},
        {"id":"P03","brand":"Karen Millen","tier":"Contemporary Premium","cat":"Coat","season":"FW24",
         "m_name":"Italian Manteco Wool Blend High Neck Belted Midaxi Coat","m_retail":None,"m_sale":None,"m_resale":None,
         "m_url":"https://www.karenmillen.com/us/product/karen-millen-italian-manteco-wool-blend-high-neck-belted-midaxi-coat_bkk13810",
         "c_name":"Italian Wool Fitted Coat (non-Manteco)","c_retail":None,"c_sale":None,"c_resale":None,
         "c_url":"https://www.karenmillen.com/us/italian-wool-fitted-coat---/BKK06546.html"},
        {"id":"P04","brand":"Karen Millen","tier":"Contemporary Premium","cat":"Coat","season":"FW24",
         "m_name":"Premium Italian Manteco Wool Double Breasted Tailored Midi Coat","m_retail":None,"m_sale":None,"m_resale":None,
         "m_url":"https://www.karenmillen.com/us/product/karen-millen-premium-italian-manteco-wool-double-breasted-tailored-midi-coat_bkk21774",
         "c_name":"Italian Virgin Wool Hourglass Midi Coat","c_retail":None,"c_sale":None,"c_resale":None,
         "c_url":"https://www.karenmillen.com/us/italian-virgin-wool-hourglass-midi-coat-/BKK06905.html"},
        {"id":"P05","brand":"Mango","tier":"Contemporary","cat":"Coat","season":"FW24",
         "m_name":"Manteco Wool Coat with Lapels (Men)","m_retail":399.99,"m_sale":279.99,"m_resale":None,
         "m_url":"https://shop.mango.com/us/en/p/men/coats/coats/manteco-wool-coat-with-lapels_77097782",
         "c_name":"Herringbone Wool-Blend Coat Men (non-Manteco)","c_retail":None,"c_sale":None,"c_resale":None,
         "c_url":"https://shop.mango.com/us/men/coats-and-blazers/coats"},
        {"id":"P06","brand":"Mango","tier":"Contemporary","cat":"Coat","season":"FW24",
         "m_name":"Manteco Wool Coat with Belt (Women)","m_retail":None,"m_sale":None,"m_resale":None,
         "m_url":"https://shop.mango.com/us/en/p/women/coats/coats/manteco-wool-coat-with-belt_17066744",
         "c_name":"Belted Wool Coat Women (non-Manteco)","c_retail":None,"c_sale":None,"c_resale":None,
         "c_url":"https://shop.mango.com/us/women/clothing/coats"},
        {"id":"P07","brand":"Karen Millen","tier":"Contemporary Premium","cat":"Coat","season":"FW24",
         "m_name":"Premium Italian Manteco Wool Military Double Breasted Midaxi Coat","m_retail":None,"m_sale":None,"m_resale":None,
         "m_url":"https://www.karenmillen.com/us/product/karen-millen-premium-italian-manteco-wool-military-double-breasted-tailored-midi-coat_bkk21818",
         "c_name":"Italian Wool Fitted Coat (non-Manteco)","c_retail":None,"c_sale":None,"c_resale":None,
         "c_url":"https://www.karenmillen.com/us/italian-wool-fitted-coat---/BKK06546.html"},
        {"id":"P08","brand":"Karen Millen","tier":"Contemporary Premium","cat":"Coat","season":"FW24",
         "m_name":"Italian Manteco Wool Maxi Double Breasted Tailored Coat","m_retail":None,"m_sale":None,"m_resale":None,
         "m_url":"https://www.karenmillen.com/italian-manteco-wool-maxi-double-breasted-tailored-coat/BKK14749.html",
         "c_name":"Italian Virgin Wool Hourglass Midi Coat","c_retail":None,"c_sale":None,"c_resale":None,
         "c_url":"https://www.karenmillen.com/us/italian-virgin-wool-hourglass-midi-coat-/BKK06905.html"},
        {"id":"P09","brand":"Woolrich via 24S","tier":"Premium","cat":"Coat","season":"FW24",
         "m_name":"Men's Coat in Manteco Recycled Wool Blend","m_retail":None,"m_sale":None,"m_resale":None,
         "m_url":"https://www.24s.com/en-us/coat-in-manteco-recycled-wool-blend-woolrich_WOO4AB22",
         "c_name":"Control TBD — find comparable Woolrich coat on 24S","c_retail":None,"c_sale":None,"c_resale":None,
         "c_url":"https://www.24s.com/en-us/brand/woolrich"},
        {"id":"P10","brand":"Samsøe Samsøe","tier":"Contemporary Premium","cat":"Coat","season":"AW24",
         "m_name":"Alma Coat (Manteco MWool recycled wool blend)","m_retail":None,"m_sale":None,"m_resale":None,
         "m_url":"https://www.samsoe.com/en-US/product/alma-coat-14895-salute",
         "c_name":"Samolly Coat (non-Manteco wool blend)","c_retail":None,"c_sale":None,"c_resale":None,
         "c_url":"https://www.samsoe.com/en-US/product/samolly-coat-15343-black-mel"},
    ],
    "resale_listings": [],
    "scraped_products": [],
    "last_updated": datetime.utcnow().isoformat(),
    "version": 1,
}

# ── Persistence ───────────────────────────────────────────────────────────────
def load_data():
    try:
        if DATA_FILE.exists():
            return json.loads(DATA_FILE.read_text())
    except Exception:
        pass
    return dict(DEFAULT_DATA)

def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.utcnow().isoformat()
    DATA_FILE.write_text(json.dumps(data, indent=2, default=str))

# ── Auth helper ───────────────────────────────────────────────────────────────
def check_auth():
    key = request.headers.get("X-Secret-Key", "") or request.args.get("key", "")
    return key == SECRET_KEY

# ── Scraping helpers ──────────────────────────────────────────────────────────
def detect_channel(url):
    domain = urlparse(url).netloc.lower()
    for ch, kws in CHANNEL_MAP.items():
        if any(k in domain for k in kws): return ch
    return "retail"

def brand_hint(url):
    domain = urlparse(url).netloc.lower()
    for k, v in DOMAIN_BRAND_MAP.items():
        if k in domain: return v
    return domain.replace("www.","").split(".")[0].title()

def fetch_page(url):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script","style","nav","footer","header","aside","iframe","noscript","svg"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title else ""
    main = soup.find("main") or soup.find(id=re.compile(r"main|content|product",re.I)) or soup
    text = re.sub(r"\s{2,}"," ", main.get_text(separator=" ", strip=True)).strip()
    return title, text[:MAX_TEXT_CHARS]

EXTRACT_PROMPT = """\
You are a product data analyst for a wool fabric market research project about Manteco, \
an Italian wool manufacturer based in Prato, Italy.

URL: {url}
Brand hint: {brand_hint}
Channel: {channel}
Page title: {title}

Page text:
---
{text}
---

Instructions:
- Extract all available data from the page text.
- If page text is sparse (JS-rendered site), infer name from URL slug and use your knowledge \
of the brand's Manteco collection for fabric and approximate price (prefix with ~).
- manteco = true if "Manteco" or "MWool" appears in URL, title, or text.

Return ONLY a JSON object, no markdown:
{{
  "brand": "Brand name",
  "name": "Product name",
  "category": "coat|jacket|blazer|trousers|suit|knitwear|other",
  "price_retail": "$X,XXX or ~$X,XXX or null",
  "price_sale": "$XXX or ~$XXX or null",
  "currency": "USD|EUR|GBP",
  "fabric": "composition string or null",
  "manteco": true or false,
  "manteco_quote": "short quote or null",
  "channel": "{channel}",
  "url": "{url}",
  "scraped_at": "{timestamp}"
}}"""

def analyze_with_claude(url, title, text, channel):
    import anthropic as ant
    client = ant.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = EXTRACT_PROMPT.format(
        url=url, brand_hint=brand_hint(url), channel=channel,
        title=title, text=text or "(unavailable)",
        timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    msg = client.messages.create(model=MODEL, max_tokens=1000,
        messages=[{"role":"user","content":prompt}])
    raw = re.sub(r"^```json|^```|```$","",msg.content[0].text.strip(),flags=re.MULTILINE).strip()
    return json.loads(raw)

# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_file("dashboard.html")

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "api_key_set": bool(ANTHROPIC_API_KEY),
        "data_file": str(DATA_FILE),
        "last_updated": load_data().get("last_updated","—"),
    })

# ── Data CRUD ──────────────────────────────────────────────────────────────────

@app.route("/data", methods=["GET"])
def get_data():
    return jsonify(load_data())

@app.route("/data/pairs", methods=["PUT"])
def update_pairs():
    if not check_auth():
        return jsonify({"error":"Unauthorized"}), 401
    data = load_data()
    data["pairs"] = request.get_json(force=True)
    save_data(data)
    return jsonify({"ok": True, "pairs": len(data["pairs"])})

@app.route("/data/pairs", methods=["POST"])
def add_pair():
    if not check_auth():
        return jsonify({"error":"Unauthorized"}), 401
    data = load_data()
    pair = request.get_json(force=True)
    data["pairs"].append(pair)
    save_data(data)
    return jsonify({"ok": True, "id": pair.get("id")})

@app.route("/data/pairs/<pair_id>", methods=["PATCH"])
def patch_pair(pair_id):
    if not check_auth():
        return jsonify({"error":"Unauthorized"}), 401
    data = load_data()
    updates = request.get_json(force=True)
    for p in data["pairs"]:
        if p["id"] == pair_id:
            p.update(updates)
            break
    save_data(data)
    return jsonify({"ok": True})

@app.route("/data/resale", methods=["POST"])
def add_resale():
    if not check_auth():
        return jsonify({"error":"Unauthorized"}), 401
    data = load_data()
    listing = request.get_json(force=True)
    listing["added_at"] = datetime.utcnow().isoformat()
    data.setdefault("resale_listings",[]).append(listing)
    save_data(data)
    return jsonify({"ok": True})

@app.route("/data/resale/<int:idx>", methods=["DELETE"])
def delete_resale(idx):
    if not check_auth():
        return jsonify({"error":"Unauthorized"}), 401
    data = load_data()
    if 0 <= idx < len(data.get("resale_listings",[])):
        data["resale_listings"].pop(idx)
        save_data(data)
    return jsonify({"ok": True})

# ── Scraper ────────────────────────────────────────────────────────────────────

@app.route("/scrape", methods=["POST"])
def scrape():
    if not check_auth():
        return jsonify({"error":"Unauthorized"}), 401
    body = request.get_json(force=True)
    urls = [u.strip() for u in (body.get("urls") or []) if u.strip().startswith("http")]
    if not urls:
        return jsonify({"error":"No valid URLs"}), 400

    def generate():
        total = len(urls)
        for i, url in enumerate(urls, 1):
            yield f"data: {json.dumps({'type':'progress','url':url,'index':i,'total':total,'message':f'Fetching {i}/{total}...'})}\n\n"
            channel = detect_channel(url)
            try:
                title, text = fetch_page(url)
            except Exception as e:
                title, text = url.split("/")[-1].replace("-"," "), ""
                yield f"data: {json.dumps({'type':'progress','url':url,'index':i,'total':total,'message':'Fetch failed — using URL only'})}\n\n"

            yield f"data: {json.dumps({'type':'progress','url':url,'index':i,'total':total,'message':'Analyzing with Claude...'})}\n\n"
            try:
                product = analyze_with_claude(url, title, text, channel)
                # Persist scraped product
                data = load_data()
                data.setdefault("scraped_products",[]).append(product)
                save_data(data)
                yield f"data: {json.dumps({'type':'product','data':product})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type':'error','url':url,'message':str(e)})}\n\n"
            time.sleep(1)

        yield f"data: {json.dumps({'type':'done','total':total})}\n\n"

    return Response(stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\nManteco Price Resilience Server")
    print(f"Running on http://0.0.0.0:{port}")
    print(f"Data file: {DATA_FILE}")
    print(f"Secret key: {SECRET_KEY[:4]}***\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
