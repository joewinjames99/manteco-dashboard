"""
Manteco Pricing Intelligence — Dashboard Server
================================================
Serves the dashboard HTML and proxies Google Sheets CSV requests.

Requirements:
    pip install flask flask-cors requests

Usage:
    python server.py
    Then open http://127.0.0.1:5000
"""

import os
import requests
from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


@app.route("/")
def index():
    here = os.path.dirname(os.path.abspath(__file__))
    return send_file(os.path.join(here, "manteco_dashboard.html"))


@app.route("/csv-proxy")
def csv_proxy():
    url = request.args.get("url", "")
    if not url.startswith("https://docs.google.com/spreadsheets"):
        return jsonify({"error": "Only Google Sheets URLs allowed"}), 400
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        r.raise_for_status()
        return Response(r.content, mimetype="text/csv",
                        headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\nManteco Dashboard Server")
    print(f"Running on http://127.0.0.1:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
