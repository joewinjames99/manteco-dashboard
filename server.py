"""
Manteco Price Resilience — Server v4
=====================================
- Products in Google Sheets (public "anyone with link can edit")
- Pairs + resale in Railway Postgres
- Single GOOGLE_API_KEY — no OAuth needed

Environment variables (Railway):
  SECRET_KEY        — team password for dashboard login
  ANTHROPIC_API_KEY — for scraping
  DATABASE_URL      — Railway Postgres (pairs + resale)
  GOOGLE_API_KEY    — Google Cloud API key (Sheets API enabled)
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

SECRET_KEY        = os.environ.get("SECRET_KEY", "manteco2026")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DATABASE_URL      = os.environ.get("DATABASE_URL", "")
GOOGLE_API_KEY    = os.environ.get("GOOGLE_API_KEY", "")
MODEL             = "claude-haiku-4-5-20251001"
MAX_TEXT_CHARS    = 6000
REQUEST_TIMEOUT   = 25

SCRAPE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

DOMAIN_BRAND_MAP = {
    "woolrich.com":"Woolrich","naadam.co":"NAADAM","zara.com":"Zara",
    "mango.com":"Mango","cos.com":"COS","loropiana.com":"Loro Piana",
    "zegna.com":"Ermenegildo Zegna","brunellocucinelli.com":"Brunello Cucinelli",
    "mrporter.com":"Mr Porter","farfetch.com":"Farfetch","ssense.com":"SSENSE",
    "grailed.com":"Grailed","ebay.com":"eBay",
    "vestiairecollective.com":"Vestiaire Collective","24s.com":"24S",
    "karenmillen.com":"Karen Millen","samsoe.com":"Samsoe Samsoe",
    "macys.com":"Macy's","nordstrom.com":"Nordstrom",
    "revolve.com":"Revolve","fwrd.com":"FWRD",
}

SHEET_COLUMNS = [
    "id","type","brand","name","category",
    "price_retail","price_sale","fabric",
    "manteco","url","scraped_at","notes"
]

EXTRACT_PROMPT = """\
You are a product data analyst for a wool fabric market research project about Manteco \
(Italian wool manufacturer based in Prato).

URL: {url}
Brand hint: {brand_hint}
Page title: {title}

Page text:
---
{text}
---

Extract product data. If text is sparse, infer from URL slug.
Manteco = true if "Manteco" or "MWool" appears in URL, title, or text.

Return ONLY JSON, no markdown:
{{
  "brand": "Brand name",
  "name": "Product name",
  "category": "coat|jacket|blazer|trousers|suit|knitwear|other",
  "price_retail": "$X,XXX or null",
  "price_sale": "$XXX or null",
  "fabric": "e.g. 75% Wool 25% Polyamide or null",
  "manteco": true or false
}}"""

# ── Postgres (pairs + resale only) ────────────────────────────────────────────
_mem = {"pairs": [], "resale_listings": [], "version": 0}

def get_db():
    import psycopg2
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    if not DATABASE_URL: return
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS manteco_pairs (
            key TEXT PRIMARY KEY, value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW())""")
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"DB init: {e}")

def load_pairs_data():
    if not DATABASE_URL: return dict(_mem)
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT value FROM manteco_pairs WHERE key='main'")
        row = cur.fetchone(); cur.close(); conn.close()
        if row: return json.loads(row[0])
    except Exception as e:
        print(f"DB load: {e}")
    return dict(_mem)

def save_pairs_data(data):
    global _mem
    data["version"]      = data.get("version", 0) + 1
    data["last_updated"] = datetime.utcnow().isoformat()
    _mem = data
    if not DATABASE_URL: return
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""INSERT INTO manteco_pairs (key,value,updated_at)
            VALUES ('main',%s,NOW())
            ON CONFLICT (key) DO UPDATE
            SET value=EXCLUDED.value, updated_at=NOW()""",
            (json.dumps(data, default=str),))
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"DB save: {e}")

# ── Google Sheets (API key — no OAuth) ───────────────────────────────────────
def sheet_id_from_url(url):
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return m.group(1) if m else url  # accept raw ID too

def sheets_read(sheet_id):
    """Read all rows from Products tab."""
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
           f"/values/Products!A:L?key={GOOGLE_API_KEY}")
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    return res.json().get("values", [])

def sheets_append(sheet_id, row):
    """Append one row to Products tab."""
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
           f"/values/Products!A:L:append?key={GOOGLE_API_KEY}"
           f"&valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS")
    res = requests.post(url, json={"values": [row]}, timeout=10)
    res.raise_for_status()
    return res.json()

def sheets_update_row(sheet_id, row_num, row):
    """Update a specific row (1-indexed, row 1 = header)."""
    range_ = f"Products!A{row_num}:L{row_num}"
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
           f"/values/{range_}?key={GOOGLE_API_KEY}"
           f"&valueInputOption=USER_ENTERED")
    res = requests.put(url, json={"values": [row]}, timeout=10)
    res.raise_for_status()
    return res.json()

def ensure_header(sheet_id):
    try:
        rows = sheets_read(sheet_id)
        if not rows or (rows[0] and rows[0][0] != "id"):
            url = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
                   f"/values/Products!A1:L1?key={GOOGLE_API_KEY}"
                   f"&valueInputOption=USER_ENTERED")
            requests.put(url, json={"values": [SHEET_COLUMNS]}, timeout=10)
    except Exception as e:
        print(f"Header: {e}")

def rows_to_products(rows):
    if not rows or len(rows) < 2: return []
    headers = rows[0]
    out = []
    for row in rows[1:]:
        if not row or not any(row): continue
        p = {col: (row[i] if i < len(row) else "") for i, col in enumerate(headers)}
        p["manteco"] = str(p.get("manteco","")).lower() in ("true","yes","1","true")
        out.append(p)
    return out

def product_to_row(p):
    return [str(p.get(col,"") or "") for col in SHEET_COLUMNS]

# ── Auth ──────────────────────────────────────────────────────────────────────
def check_auth():
    key = request.headers.get("X-Secret-Key","") or request.args.get("key","")
    return key == SECRET_KEY

# ── Scraping ──────────────────────────────────────────────────────────────────
def brand_hint(url):
    domain = urlparse(url).netloc.lower()
    for k, v in DOMAIN_BRAND_MAP.items():
        if k in domain: return v
    return domain.replace("www.","").replace("shop.","").split(".")[0].title()

def fetch_page(url):
    resp = requests.get(url, headers=SCRAPE_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script","style","nav","footer","header","aside","iframe","noscript"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title else ""
    main  = soup.find("main") or soup.find(id=re.compile(r"main|content|product",re.I)) or soup
    text  = re.sub(r"\s{2,}"," ", main.get_text(separator=" ", strip=True)).strip()
    return title, text[:MAX_TEXT_CHARS]

def analyze_with_claude(url, title, text):
    import anthropic as ant
    client = ant.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = EXTRACT_PROMPT.format(
        url=url, brand_hint=brand_hint(url),
        title=title, text=text or "(unavailable)"
    )
    msg = client.messages.create(model=MODEL, max_tokens=800,
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
    try:
        d = load_pairs_data(); db_ok = True; v = d.get("version",0)
    except Exception:
        db_ok = False; v = 0
    return jsonify({
        "status":           "ok",
        "db_connected":     db_ok,
        "api_key_set":      bool(ANTHROPIC_API_KEY),
        "sheets_api_set":   bool(GOOGLE_API_KEY),
        "version":          v,
    })

# ── Sheet proxy endpoints ──────────────────────────────────────────────────────
@app.route("/sheet/read")
def sheet_read():
    """Read all products from the Sheet."""
    sid = request.args.get("sheet_id","")
    if not sid:
        return jsonify({"error":"Missing sheet_id"}), 400
    if not GOOGLE_API_KEY:
        return jsonify({"error":"GOOGLE_API_KEY not set on server"}), 500
    try:
        sid  = sheet_id_from_url(sid)
        rows = sheets_read(sid)
        return jsonify({"products": rows_to_products(rows), "raw_rows": len(rows)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sheet/append", methods=["POST"])
def sheet_append():
    """Append a product to the Sheet."""
    if not check_auth():
        return jsonify({"error":"Unauthorized"}), 401
    body = request.get_json(force=True)
    sid  = body.get("sheet_id","")
    prod = body.get("product",{})
    if not sid:
        return jsonify({"error":"Missing sheet_id"}), 400
    if not GOOGLE_API_KEY:
        return jsonify({"error":"GOOGLE_API_KEY not set on server"}), 500
    try:
        sid = sheet_id_from_url(sid)
        ensure_header(sid)
        row = product_to_row(prod)
        sheets_append(sid, row)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sheet/update", methods=["POST"])
def sheet_update():
    """Update a specific product row by ID."""
    if not check_auth():
        return jsonify({"error":"Unauthorized"}), 401
    body = request.get_json(force=True)
    sid  = body.get("sheet_id","")
    prod = body.get("product",{})
    if not sid or not prod.get("id"):
        return jsonify({"error":"Missing sheet_id or product.id"}), 400
    if not GOOGLE_API_KEY:
        return jsonify({"error":"GOOGLE_API_KEY not set"}), 500
    try:
        sid  = sheet_id_from_url(sid)
        rows = sheets_read(sid)
        # Find row by ID (skip header = row 1)
        for i, r in enumerate(rows[1:], start=2):
            if r and r[0] == prod["id"]:
                row = product_to_row(prod)
                sheets_update_row(sid, i, row)
                return jsonify({"ok": True, "row": i})
        # Not found — append instead
        ensure_header(sid)
        sheets_append(sid, product_to_row(prod))
        return jsonify({"ok": True, "appended": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sheet/delete", methods=["POST"])
def sheet_delete():
    """Delete a product row by marking it blank (soft delete)."""
    if not check_auth():
        return jsonify({"error":"Unauthorized"}), 401
    body = request.get_json(force=True)
    sid  = body.get("sheet_id","")
    pid  = body.get("product_id","")
    if not sid or not pid:
        return jsonify({"error":"Missing sheet_id or product_id"}), 400
    if not GOOGLE_API_KEY:
        return jsonify({"error":"GOOGLE_API_KEY not set"}), 500
    try:
        sid  = sheet_id_from_url(sid)
        rows = sheets_read(sid)
        for i, r in enumerate(rows[1:], start=2):
            if r and r[0] == pid:
                sheets_update_row(sid, i, [""] * len(SHEET_COLUMNS))
                return jsonify({"ok": True})
        return jsonify({"ok": True, "not_found": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Pairs (Postgres) ──────────────────────────────────────────────────────────
@app.route("/pairs/data")
def pairs_data():
    since = request.args.get("since_version")
    data  = load_pairs_data()
    if since:
        try:
            if int(since) >= data.get("version",0):
                return jsonify({"up_to_date":True,"version":data.get("version",0)})
        except ValueError: pass
    return jsonify(data)

@app.route("/pairs", methods=["POST"])
def create_pair():
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_pairs_data()
    pair = request.get_json(force=True)
    pair["created_at"] = datetime.utcnow().isoformat()
    data.setdefault("pairs",[]).append(pair)
    save_pairs_data(data)
    return jsonify({"ok":True,"version":data["version"]})

@app.route("/pairs/<pair_id>", methods=["PATCH"])
def patch_pair(pair_id):
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_pairs_data()
    upd  = request.get_json(force=True)
    for p in data.get("pairs",[]):
        if p["id"] == pair_id: p.update(upd); break
    save_pairs_data(data)
    return jsonify({"ok":True,"version":data["version"]})

@app.route("/pairs/<pair_id>", methods=["DELETE"])
def delete_pair(pair_id):
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_pairs_data()
    data["pairs"] = [p for p in data.get("pairs",[]) if p["id"] != pair_id]
    save_pairs_data(data)
    return jsonify({"ok":True,"version":data["version"]})

@app.route("/resale", methods=["POST"])
def add_resale():
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_pairs_data()
    lst  = request.get_json(force=True)
    lst["added_at"] = datetime.utcnow().isoformat()
    data.setdefault("resale_listings",[]).append(lst)
    save_pairs_data(data)
    return jsonify({"ok":True,"version":data["version"]})

@app.route("/resale/<int:idx>", methods=["DELETE"])
def delete_resale(idx):
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_pairs_data()
    ls   = data.get("resale_listings",[])
    if 0 <= idx < len(ls): ls.pop(idx)
    save_pairs_data(data)
    return jsonify({"ok":True,"version":data["version"]})

# ── Scraper ───────────────────────────────────────────────────────────────────
@app.route("/scrape", methods=["POST"])
def scrape():
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    body     = request.get_json(force=True)
    urls     = [u.strip() for u in (body.get("urls") or []) if u.strip().startswith("http")]
    sheet_id = sheet_id_from_url(body.get("sheet_id","")) if body.get("sheet_id") else ""
    if not urls: return jsonify({"error":"No valid URLs"}), 400

    def generate():
        if sheet_id and GOOGLE_API_KEY:
            try: ensure_header(sheet_id)
            except: pass

        for i, url in enumerate(urls, 1):
            yield f"data: {json.dumps({'type':'progress','index':i,'total':len(urls),'message':f'Fetching {i}/{len(urls)}...'})}\n\n"
            try:
                title, text = fetch_page(url)
            except Exception:
                title, text = "", ""
                yield f"data: {json.dumps({'type':'progress','index':i,'total':len(urls),'message':'Fetch failed — using URL only'})}\n\n"

            yield f"data: {json.dumps({'type':'progress','index':i,'total':len(urls),'message':'Analyzing with Claude...'})}\n\n"
            try:
                product              = analyze_with_claude(url, title, text)
                product["id"]        = f"prod_{int(time.time()*1000)}_{i}"
                product["scraped_at"]= datetime.utcnow().strftime("%Y-%m-%d %H:%M")
                product["type"]      = "manteco" if product.get("manteco") else "control"
                product["url"]       = url
                product["notes"]     = ""

                saved_to_sheet = False
                if sheet_id and GOOGLE_API_KEY:
                    try:
                        sheets_append(sheet_id, product_to_row(product))
                        saved_to_sheet = True
                    except Exception as e:
                        product["_sheet_error"] = str(e)

                product["_saved_to_sheet"] = saved_to_sheet
                yield f"data: {json.dumps({'type':'product','data':product})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type':'error','url':url,'message':str(e)})}\n\n"
            time.sleep(1)

        yield f"data: {json.dumps({'type':'done','total':len(urls)})}\n\n"

    return Response(stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\nManteco Server v4 | Port:{port} | Sheets:{'yes' if GOOGLE_API_KEY else 'NO — set GOOGLE_API_KEY'}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
