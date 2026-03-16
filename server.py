"""
Manteco Price Resilience — Cloud Server v2 (Postgres)
======================================================
Uses Railway's free Postgres for persistent storage.

Environment variables (set in Railway):
  DATABASE_URL       — auto-set by Railway when you add Postgres
  ANTHROPIC_API_KEY  — for scraping (optional)
  SECRET_KEY         — team password
"""

import os, re, json, time
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, Response, stream_with_context, send_file
from flask_cors import CORS

app = Flask(__name__, static_folder=None)
CORS(app)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SECRET_KEY        = os.environ.get("SECRET_KEY", "manteco2026")
DATABASE_URL      = os.environ.get("DATABASE_URL", "")
MODEL             = "claude-haiku-4-5-20251001"
MAX_TEXT_CHARS    = 6000
REQUEST_TIMEOUT   = 25

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
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
    "grailed.com":"Grailed","ebay.com":"eBay","vestiairecollective.com":"Vestiaire Collective",
    "24s.com":"24S","karenmillen.com":"Karen Millen","samsoe.com":"Samsoe Samsoe",
    "macys.com":"Macy's","nordstrom.com":"Nordstrom","revolve.com":"Revolve","fwrd.com":"FWRD",
}

DEFAULT_DATA = {
    "products": [],
    "pairs": [],
    "resale_listings": [],
    "version": 0,
    "last_updated": datetime.utcnow().isoformat(),
}

EXTRACT_PROMPT = """\
You are a product data analyst for a wool fabric market research project about Manteco, \
an Italian wool manufacturer.

URL: {url}
Brand hint: {brand_hint}
Channel: {channel}
Page title: {title}

Page text:
---
{text}
---

Extract product data. If page text is sparse, infer from URL slug. \
Manteco = true if "Manteco" or "MWool" appears in URL, title, or text.

Return ONLY a JSON object, no markdown:
{{
  "brand": "Brand name",
  "name": "Product name",
  "category": "coat|jacket|blazer|trousers|suit|knitwear|other",
  "price_retail": "$X,XXX or null",
  "price_sale": "$XXX or null",
  "currency": "USD|EUR|GBP",
  "fabric": "composition string or null",
  "manteco": true or false,
  "manteco_quote": "short quote or null",
  "channel": "{channel}",
  "url": "{url}"
}}"""

# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def init_db():
    """Create the data table if it doesn't exist."""
    if not DATABASE_URL:
        return
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS manteco_data (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB init error: {e}")

_memory_store = None  # in-memory fallback when DB unavailable

def load_data():
    global _memory_store
    if not DATABASE_URL:
        if _memory_store is None:
            _memory_store = dict(DEFAULT_DATA)
        return _memory_store
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT value FROM manteco_data WHERE key = 'main'")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return json.loads(row[0])
        return dict(DEFAULT_DATA)
    except Exception as e:
        print(f"DB load error (using memory): {e}")
        if _memory_store is None:
            _memory_store = dict(DEFAULT_DATA)
        return _memory_store

def save_data(data):
    global _memory_store
    data["last_updated"] = datetime.utcnow().isoformat()
    data["version"] = data.get("version", 0) + 1
    _memory_store = data  # always update memory
    if not DATABASE_URL:
        return
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO manteco_data (key, value, updated_at)
            VALUES ('main', %s, NOW())
            ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value, updated_at = NOW()
        """, (json.dumps(data, default=str),))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB save error (saved to memory only): {e}")

# ── Auth ──────────────────────────────────────────────────────────────────────
def check_auth():
    key = request.headers.get("X-Secret-Key","") or request.args.get("key","")
    return key == SECRET_KEY

# ── Scraping ──────────────────────────────────────────────────────────────────
def detect_channel(url):
    domain = urlparse(url).netloc.lower()
    for ch, kws in CHANNEL_MAP.items():
        if any(k in domain for k in kws): return ch
    return "retail"

def brand_hint(url):
    domain = urlparse(url).netloc.lower()
    for k, v in DOMAIN_BRAND_MAP.items():
        if k in domain: return v
    return domain.replace("www.","").replace("shop.","").split(".")[0].title()

def fetch_page(url):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script","style","nav","footer","header","aside","iframe","noscript","svg"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title else ""
    main  = soup.find("main") or soup.find(id=re.compile(r"main|content|product",re.I)) or soup
    text  = re.sub(r"\s{2,}"," ", main.get_text(separator=" ", strip=True)).strip()
    return title, text[:MAX_TEXT_CHARS]

def analyze_with_claude(url, title, text, channel):
    import anthropic as ant
    client = ant.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = EXTRACT_PROMPT.format(
        url=url, brand_hint=brand_hint(url), channel=channel,
        title=title, text=text or "(unavailable)"
    )
    msg = client.messages.create(model=MODEL, max_tokens=1000,
        messages=[{"role":"user","content":prompt}])
    raw = re.sub(r"^```json|^```|```$","",msg.content[0].text.strip(),flags=re.MULTILINE).strip()
    return json.loads(raw)

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    from pathlib import Path
    return send_file(Path(__file__).parent / "dashboard.html")

@app.route("/health")
def health():
    db_ok = False
    version = 0
    num_products = 0
    num_pairs = 0
    last_updated = "—"
    try:
        d = load_data()
        db_ok = True
        version = d.get("version", 0)
        num_products = len(d.get("products",[]))
        num_pairs = len(d.get("pairs",[]))
        last_updated = d.get("last_updated","—")
    except Exception as e:
        print(f"Health check load error: {e}")
    return jsonify({
        "status": "ok",
        "api_key_set": bool(ANTHROPIC_API_KEY),
        "db_connected": db_ok,
        "version": version,
        "products": num_products,
        "pairs": num_pairs,
        "last_updated": last_updated,
    })

@app.route("/data", methods=["GET"])
def get_data():
    client_version = request.args.get("since_version", None)
    data = load_data()
    if client_version is not None:
        try:
            if int(client_version) >= data.get("version", 0):
                return jsonify({"up_to_date": True, "version": data.get("version",0)})
        except ValueError:
            pass
    return jsonify(data)

@app.route("/data/products/<pid>", methods=["PATCH"])
def patch_product(pid):
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_data()
    updates = request.get_json(force=True)
    for p in data.get("products", []):
        if p["id"] == pid:
            p.update(updates)
            break
    save_data(data)
    return jsonify({"ok": True})

@app.route("/data/products/<pid>", methods=["DELETE"])
def delete_product(pid):
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_data()
    data["products"] = [p for p in data.get("products",[]) if p["id"] != pid]
    for pair in data.get("pairs",[]):
        if pair.get("manteco_id") == pid:
            pair["manteco_id"] = None
        if pid in pair.get("control_ids",[]):
            pair["control_ids"].remove(pid)
    data["pairs"] = [p for p in data.get("pairs",[]) if p.get("manteco_id")]
    save_data(data)
    return jsonify({"ok": True})

@app.route("/data/pairs", methods=["POST"])
def create_pair():
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_data()
    pair = request.get_json(force=True)
    pair["created_at"] = datetime.utcnow().isoformat()
    data.setdefault("pairs",[]).append(pair)
    save_data(data)
    return jsonify({"ok": True})

@app.route("/data/pairs/<pair_id>", methods=["PATCH"])
def patch_pair(pair_id):
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_data()
    updates = request.get_json(force=True)
    for p in data.get("pairs",[]):
        if p["id"] == pair_id:
            p.update(updates)
            break
    save_data(data)
    return jsonify({"ok": True})

@app.route("/data/pairs/<pair_id>", methods=["DELETE"])
def delete_pair(pair_id):
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_data()
    data["pairs"] = [p for p in data.get("pairs",[]) if p["id"] != pair_id]
    save_data(data)
    return jsonify({"ok": True})

@app.route("/data/resale", methods=["POST"])
def add_resale():
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_data()
    listing = request.get_json(force=True)
    listing["added_at"] = datetime.utcnow().isoformat()
    data.setdefault("resale_listings",[]).append(listing)
    save_data(data)
    return jsonify({"ok": True})

@app.route("/data/resale/<int:idx>", methods=["DELETE"])
def delete_resale(idx):
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_data()
    listings = data.get("resale_listings",[])
    if 0 <= idx < len(listings):
        listings.pop(idx)
    save_data(data)
    return jsonify({"ok": True})

@app.route("/scrape", methods=["POST"])
def scrape():
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    body = request.get_json(force=True)
    urls = [u.strip() for u in (body.get("urls") or []) if u.strip().startswith("http")]
    if not urls: return jsonify({"error":"No valid URLs"}), 400

    def generate():
        total = len(urls)
        for i, url in enumerate(urls, 1):
            yield f"data: {json.dumps({'type':'progress','url':url,'index':i,'total':total,'message':f'Fetching {i}/{total}...'})}\n\n"
            channel = detect_channel(url)
            try:
                title, text = fetch_page(url)
            except Exception:
                title, text = "", ""
                yield f"data: {json.dumps({'type':'progress','url':url,'index':i,'total':total,'message':'Fetch failed, using URL only'})}\n\n"

            yield f"data: {json.dumps({'type':'progress','url':url,'index':i,'total':total,'message':'Analyzing...'})}\n\n"
            try:
                product = analyze_with_claude(url, title, text, channel)
                product["id"] = "prod_" + str(int(time.time()*1000)) + "_" + str(i)
                product["scraped_at"] = datetime.utcnow().isoformat()
                product["type"] = "manteco" if product.get("manteco") else "control"
                data = load_data()
                data.setdefault("products",[]).append(product)
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
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"\nManteco Price Resilience Server")
    print(f"Port: {port} | DB: {'connected' if DATABASE_URL else 'not set'}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

# Run init_db on startup
init_db()
