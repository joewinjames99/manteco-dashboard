"""
Manteco Price Resilience — Server v3
=====================================
Products: Google Sheets (master, OAuth token from client)
Pairs + Resale: Railway Postgres

Env vars needed in Railway:
  SECRET_KEY          — dashboard team password
  ANTHROPIC_API_KEY   — for scraping
  DATABASE_URL        — auto-set by Railway Postgres addon
  GOOGLE_CLIENT_ID    — from Google Cloud Console
  GOOGLE_CLIENT_SECRET
"""

import os, re, json, time
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, Response, stream_with_context, send_file
from flask_cors import CORS
from pathlib import Path

app = Flask(__name__, static_folder=None)
CORS(app)

SECRET_KEY            = os.environ.get("SECRET_KEY", "manteco2026")
ANTHROPIC_API_KEY     = os.environ.get("ANTHROPIC_API_KEY", "")
DATABASE_URL          = os.environ.get("DATABASE_URL", "")
GOOGLE_CLIENT_ID      = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET  = os.environ.get("GOOGLE_CLIENT_SECRET", "")
MODEL                 = "claude-haiku-4-5-20251001"
MAX_TEXT_CHARS        = 6000

SCRAPE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

DOMAIN_BRAND_MAP = {
    "woolrich.com":"Woolrich","naadam.co":"NAADAM","zara.com":"Zara","mango.com":"Mango",
    "cos.com":"COS","loropiana.com":"Loro Piana","zegna.com":"Ermenegildo Zegna",
    "brunellocucinelli.com":"Brunello Cucinelli","mrporter.com":"Mr Porter",
    "farfetch.com":"Farfetch","ssense.com":"SSENSE","grailed.com":"Grailed",
    "ebay.com":"eBay","vestiairecollective.com":"Vestiaire Collective","24s.com":"24S",
    "karenmillen.com":"Karen Millen","samsoe.com":"Samsoe Samsoe",
    "macys.com":"Macy's","nordstrom.com":"Nordstrom","fwrd.com":"FWRD",
}

SHEET_COLS = ["id","type","brand","name","category","price_retail","price_sale",
              "fabric","manteco","manteco_quote","url","scraped_at","notes"]

EXTRACT_PROMPT = """\
You are a product analyst for a Manteco wool fabric research project.
URL: {url}  |  Brand: {brand}  |  Title: {title}

Page text:
---
{text}
---

Manteco = true if "Manteco" or "MWool" appears anywhere in URL, title, or text.
Return ONLY a JSON object:
{{"brand":"string","name":"string","category":"coat|jacket|blazer|trousers|suit|knitwear|other",
"price_retail":"$X or null","price_sale":"$X or null","fabric":"string or null",
"manteco":true/false,"manteco_quote":"short quote or null"}}"""

# ── Auth ──────────────────────────────────────────────────────────────────────
def check_auth():
    k = request.headers.get("X-Secret-Key","") or request.args.get("key","")
    return k == SECRET_KEY

def google_token():
    return request.headers.get("X-Google-Token","")

# ── Postgres (pairs + resale only) ────────────────────────────────────────────
_mem = {"pairs":[], "resale_listings":[], "version":0}

def init_db():
    if not DATABASE_URL: return
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur  = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS manteco_kv
            (key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP DEFAULT NOW())""")
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(f"DB init: {e}")

def load_kv():
    if not DATABASE_URL: return dict(_mem)
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur  = conn.cursor()
        cur.execute("SELECT value FROM manteco_kv WHERE key='main'")
        row  = cur.fetchone(); cur.close(); conn.close()
        if row: return json.loads(row[0])
    except Exception as e: print(f"DB load: {e}")
    return dict(_mem)

def save_kv(data):
    global _mem
    data["version"]      = data.get("version",0) + 1
    data["last_updated"] = datetime.utcnow().isoformat()
    _mem = data
    if not DATABASE_URL: return
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur  = conn.cursor()
        cur.execute("""INSERT INTO manteco_kv (key,value,updated_at) VALUES ('main',%s,NOW())
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW()""",
            (json.dumps(data, default=str),))
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(f"DB save: {e}")

# ── Google Sheets helpers (all using OAuth Bearer token) ──────────────────────
SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"

def sh_get(sheet_id, range_, token):
    r = requests.get(f"{SHEETS_BASE}/{sheet_id}/values/{range_}",
        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    r.raise_for_status()
    return r.json().get("values", [])

def sh_append(sheet_id, range_, rows, token):
    r = requests.post(
        f"{SHEETS_BASE}/{sheet_id}/values/{range_}:append",
        params={"valueInputOption":"USER_ENTERED","insertDataOption":"INSERT_ROWS"},
        headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
        json={"values": rows}, timeout=10)
    r.raise_for_status()
    return r.json()

def sh_update(sheet_id, range_, rows, token):
    r = requests.put(
        f"{SHEETS_BASE}/{sheet_id}/values/{range_}",
        params={"valueInputOption":"USER_ENTERED"},
        headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
        json={"values": rows}, timeout=10)
    r.raise_for_status()
    return r.json()

def ensure_header(sheet_id, token):
    try:
        rows = sh_get(sheet_id, "Products!A1:A1", token)
        if not rows or not rows[0] or rows[0][0] != "id":
            sh_update(sheet_id, "Products!A1", [SHEET_COLS], token)
    except Exception as e: print(f"Header: {e}")

def rows_to_products(rows):
    if not rows or len(rows) < 2: return []
    hdrs = rows[0]
    out  = []
    for row in rows[1:]:
        if not row or not row[0]: continue
        p = {hdrs[i]: (row[i] if i < len(row) else "") for i in range(len(hdrs))}
        p["manteco"] = str(p.get("manteco","")).lower() in ("true","yes","1")
        out.append(p)
    return out

def product_to_row(p):
    return [str(p.get(c,"") or "") for c in SHEET_COLS]

# ── Scraping ──────────────────────────────────────────────────────────────────
def brand_from_url(url):
    d = urlparse(url).netloc.lower()
    for k,v in DOMAIN_BRAND_MAP.items():
        if k in d: return v
    return d.replace("www.","").replace("shop.","").split(".")[0].title()

def fetch_page(url):
    r = requests.get(url, headers=SCRAPE_HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script","style","nav","footer","header","aside","iframe","noscript"]): t.decompose()
    title = soup.title.string.strip() if soup.title else ""
    main  = soup.find("main") or soup.find(id=re.compile(r"main|content|product",re.I)) or soup
    text  = re.sub(r"\s{2,}"," ", main.get_text(separator=" ", strip=True)).strip()
    return title, text[:MAX_TEXT_CHARS]

def analyze(url, title, text):
    import anthropic as ant
    client = ant.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(model=MODEL, max_tokens=800,
        messages=[{"role":"user","content":EXTRACT_PROMPT.format(
            url=url, brand=brand_from_url(url), title=title, text=text or "(unavailable)")}])
    raw = re.sub(r"^```json|^```|```$","",msg.content[0].text.strip(),flags=re.MULTILINE).strip()
    return json.loads(raw)

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_file(Path(__file__).parent / "dashboard.html")

@app.route("/health")
def health():
    db_ok = False
    try: load_kv(); db_ok = True
    except: pass
    return jsonify({
        "status": "ok",
        "db_connected": db_ok,
        "api_key_set": bool(ANTHROPIC_API_KEY),
        "oauth_configured": bool(GOOGLE_CLIENT_ID),
    })

# ── OAuth ─────────────────────────────────────────────────────────────────────
@app.route("/oauth/url")
def oauth_url():
    if not GOOGLE_CLIENT_ID:
        return jsonify({"error":"GOOGLE_CLIENT_ID not configured in Railway Variables"}), 400
    redirect_uri = request.args.get("redirect_uri","")
    scope = "https://www.googleapis.com/auth/spreadsheets"
    url = (f"https://accounts.google.com/o/oauth2/v2/auth"
           f"?client_id={GOOGLE_CLIENT_ID}&redirect_uri={redirect_uri}"
           f"&response_type=code&scope={scope}&access_type=offline&prompt=consent")
    return jsonify({"url": url})

@app.route("/oauth/token", methods=["POST"])
def oauth_token():
    b = request.get_json(force=True)
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "code": b.get("code"), "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": b.get("redirect_uri"), "grant_type": "authorization_code"})
    return jsonify(r.json()), r.status_code

@app.route("/oauth/refresh", methods=["POST"])
def oauth_refresh():
    b = request.get_json(force=True)
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "refresh_token": b.get("refresh_token"), "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET, "grant_type": "refresh_token"})
    return jsonify(r.json()), r.status_code

# ── Sheet endpoints ───────────────────────────────────────────────────────────
@app.route("/sheet/read")
def sheet_read():
    token    = google_token()
    sheet_id = request.args.get("sheet_id","")
    if not token:    return jsonify({"error":"Missing Google token — connect your Sheet first"}), 401
    if not sheet_id: return jsonify({"error":"Missing sheet_id"}), 400
    try:
        rows     = sh_get(sheet_id, "Products!A:M", token)
        products = rows_to_products(rows)
        return jsonify({"products": products})
    except Exception as e:
        code = 401 if "401" in str(e) else 500
        return jsonify({"error": str(e)}), code

@app.route("/sheet/append", methods=["POST"])
def sheet_append():
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    token    = google_token()
    b        = request.get_json(force=True)
    sheet_id = b.get("sheet_id","")
    product  = b.get("product",{})
    if not token:    return jsonify({"error":"Missing Google token"}), 401
    if not sheet_id: return jsonify({"error":"Missing sheet_id"}), 400
    try:
        ensure_header(sheet_id, token)
        sh_append(sheet_id, "Products!A:M", [product_to_row(product)], token)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Pairs (Railway DB) ────────────────────────────────────────────────────────
@app.route("/pairs/data")
def pairs_data():
    since = request.args.get("since_version")
    data  = load_kv()
    if since:
        try:
            if int(since) >= data.get("version",0):
                return jsonify({"up_to_date":True,"version":data.get("version",0)})
        except ValueError: pass
    return jsonify(data)

@app.route("/pairs", methods=["POST"])
def create_pair():
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_kv()
    pair = request.get_json(force=True)
    pair["created_at"] = datetime.utcnow().isoformat()
    data.setdefault("pairs",[]).append(pair)
    save_kv(data)
    return jsonify({"ok":True,"version":data["version"]})

@app.route("/pairs/<pid>", methods=["PATCH"])
def patch_pair(pid):
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_kv()
    for p in data.get("pairs",[]):
        if p["id"]==pid: p.update(request.get_json(force=True)); break
    save_kv(data)
    return jsonify({"ok":True,"version":data["version"]})

@app.route("/pairs/<pid>", methods=["DELETE"])
def delete_pair(pid):
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_kv()
    data["pairs"] = [p for p in data.get("pairs",[]) if p["id"]!=pid]
    save_kv(data)
    return jsonify({"ok":True,"version":data["version"]})

@app.route("/resale", methods=["POST"])
def add_resale():
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_kv()
    item = request.get_json(force=True)
    item["added_at"] = datetime.utcnow().isoformat()
    data.setdefault("resale_listings",[]).append(item)
    save_kv(data)
    return jsonify({"ok":True,"version":data["version"]})

@app.route("/resale/<int:idx>", methods=["DELETE"])
def del_resale(idx):
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    data = load_kv()
    lst  = data.get("resale_listings",[])
    if 0 <= idx < len(lst): lst.pop(idx)
    save_kv(data)
    return jsonify({"ok":True,"version":data["version"]})

# ── Scraper ───────────────────────────────────────────────────────────────────
@app.route("/scrape", methods=["POST"])
def scrape():
    if not check_auth(): return jsonify({"error":"Unauthorized"}), 401
    b        = request.get_json(force=True)
    urls     = [u.strip() for u in (b.get("urls") or []) if u.strip().startswith("http")]
    sheet_id = b.get("sheet_id","")
    token    = b.get("access_token","")
    if not urls: return jsonify({"error":"No valid URLs"}), 400

    def generate():
        if sheet_id and token:
            try: ensure_header(sheet_id, token)
            except: pass
        for i, url in enumerate(urls, 1):
            yield f"data: {json.dumps({'type':'progress','index':i,'total':len(urls),'message':f'Fetching {i}/{len(urls)}...'})}\n\n"
            try:    title, text = fetch_page(url)
            except: title, text = "", ""
            yield f"data: {json.dumps({'type':'progress','index':i,'total':len(urls),'message':'Analyzing...'})}\n\n"
            try:
                p = analyze(url, title, text)
                p.update({"id":f"prod_{int(time.time()*1000)}_{i}",
                          "scraped_at":datetime.utcnow().isoformat(),
                          "type":"manteco" if p.get("manteco") else "control",
                          "url":url, "notes":""})
                saved = False
                if sheet_id and token:
                    try:
                        sh_append(sheet_id, "Products!A:M", [product_to_row(p)], token)
                        saved = True
                    except Exception as se:
                        p["_sheet_error"] = str(se)
                p["_saved_to_sheet"] = saved
                yield f"data: {json.dumps({'type':'product','data':p})}\n\n"
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
    print(f"Manteco Server | port:{port} | db:{'yes' if DATABASE_URL else 'no'} | oauth:{'yes' if GOOGLE_CLIENT_ID else 'no'}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
