"""
Manteco Pricing Intelligence — Dashboard Server
================================================
Serves the dashboard HTML and proxies Google Sheets CSV requests,
or reads directly from the local Excel workbook.

Requirements:
    pip install flask flask-cors requests openpyxl

Usage:
    python app.py
    Then open http://127.0.0.1:5000
"""

import csv
import io
import os

import openpyxl
import requests
from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

HERE = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(HERE, "Manteco Workbook.xlsx")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

# Sheet name → (Excel tab name, first data row, 1-indexed)
# Row 1 = title, Row 2 = column headers, Row 3+ = data
# Markdown has an ArrayFormula placeholder at row 3, so data starts at row 4.
SHEET_META = {
    "products": ("Products",     3),
    "pairs":    ("Matched Pairs", 3),
    "markdown": ("Markdown",     4),
    "resale":   ("Resale",       3),
}

# Products sheet column indices (0-based)
PROD_ID_COL      = 0   # ID
PROD_RETAIL_COL  = 6   # Retail Price ($)

# Matched Pairs sheet column indices (0-based)
PAIR_ID_COL      = 0   # Pair ID
PAIR_MANTECO_COL = 5   # Manteco Prod. ID
PAIR_CONTROL_COL = 6   # Control Prod. ID
PAIR_M_RETAIL    = 7   # M: Retail ($)
PAIR_C_RETAIL    = 8   # C: Retail ($)
PAIR_PREM_DOLLAR = 9   # Premium $
PAIR_PREM_PCT    = 10  # Premium % — sent as decimal fraction (0.769 = 76.9%) so JS normPct() works

# Resale sheet column indices (0-based)
RES_PAIR_ID      = 0   # Pair ID
RES_SIDE         = 1   # Side (M/C)
RES_ORIG_RETAIL  = 3   # Original Retail ($)
RES_RESALE_PRICE = 4   # Resale Price ($)
RES_RESIDUAL_PCT = 5   # Residual % — sent as decimal fraction


def _build_product_lookup(wb):
    """
    Read the Products sheet and return:
      retail_by_id  — {productId: retailPrice (float)}
      aug_rows      — list of augmented product rows (with auto-assigned IDs)

    IDs missing in the sheet are auto-assigned as P{row_idx+1:02d}
    where row_idx is 0-based from the first data row (row 3 in Excel).
    This preserves the original ID-to-row mapping even after new rows
    are appended at the end of the sheet.
    """
    ws = wb["Products"]
    all_rows = list(ws.iter_rows(values_only=True))
    retail_by_id = {}
    aug_rows = []

    for i, row in enumerate(all_rows[2:]):   # i=0 → Excel row 3 → P01
        if not any(v is not None and str(v).strip() for v in row):
            continue
        row = list(row)
        prod_id = row[PROD_ID_COL]
        if prod_id is None:
            prod_id = f"P{i + 1:02d}"
            row[PROD_ID_COL] = prod_id
        else:
            prod_id = str(prod_id).strip()
            row[PROD_ID_COL] = prod_id

        retail = row[PROD_RETAIL_COL]
        if retail is not None:
            try:
                retail_by_id[prod_id] = float(retail)
            except (ValueError, TypeError):
                pass

        aug_rows.append(row)

    return retail_by_id, aug_rows


def _build_pair_product_map(wb):
    """
    Read the Matched Pairs sheet and return {pairId: {'m': mantecoId, 'c': controlId}}.
    Missing pairIds are auto-assigned by row position (same logic as _augment_pairs).
    """
    ws = wb["Matched Pairs"]
    all_rows = list(ws.iter_rows(values_only=True))
    result = {}
    for i, row in enumerate(all_rows[2:]):
        if not any(v is not None and str(v).strip() for v in row):
            continue
        pair_id = row[PAIR_ID_COL]
        if pair_id is None:
            pair_id = f"PA{i + 1:02d}"
        else:
            pair_id = str(pair_id).strip()
        m_id = str(row[PAIR_MANTECO_COL]).strip() if row[PAIR_MANTECO_COL] else ""
        c_id = str(row[PAIR_CONTROL_COL]).strip() if row[PAIR_CONTROL_COL] else ""
        result[pair_id] = {"m": m_id, "c": c_id}
    return result


def _augment_pairs(wb, retail_by_id):
    """
    Read the Matched Pairs sheet and return augmented rows where:
      - Missing pairId is auto-assigned by row position (PA01, PA02, …).
      - Missing mRetail/cRetail filled from Products retail lookup.
      - Missing Premium$ and Premium% computed from filled prices.
      - Premium% is stored as decimal fraction (e.g. 0.769) so JS normPct() scales it correctly.
    """
    ws = wb["Matched Pairs"]
    all_rows = list(ws.iter_rows(values_only=True))
    augmented = []

    for i, row in enumerate(all_rows[2:]):
        if not any(v is not None and str(v).strip() for v in row):
            continue
        row = list(row)

        # Auto-assign pairId when blank
        if row[PAIR_ID_COL] is None:
            row[PAIR_ID_COL] = f"PA{i + 1:02d}"

        m_id = str(row[PAIR_MANTECO_COL]).strip() if row[PAIR_MANTECO_COL] else ""
        c_id = str(row[PAIR_CONTROL_COL]).strip() if row[PAIR_CONTROL_COL] else ""

        # Fill mRetail/cRetail from Products when formula cache is empty
        if row[PAIR_M_RETAIL] is None and m_id in retail_by_id:
            row[PAIR_M_RETAIL] = retail_by_id[m_id]
        if row[PAIR_C_RETAIL] is None and c_id in retail_by_id:
            row[PAIR_C_RETAIL] = retail_by_id[c_id]

        m_r, c_r = row[PAIR_M_RETAIL], row[PAIR_C_RETAIL]
        if m_r is not None and c_r is not None:
            try:
                m_f, c_f = float(m_r), float(c_r)
                if row[PAIR_PREM_DOLLAR] is None:
                    row[PAIR_PREM_DOLLAR] = round(m_f - c_f, 2)
                if row[PAIR_PREM_PCT] is None and c_f != 0:
                    # Store as decimal fraction — JS normPct() multiplies ≤5 by 100
                    row[PAIR_PREM_PCT] = round(m_f / c_f - 1, 4)
            except (ValueError, TypeError):
                pass

        augmented.append(row)

    return augmented


def _augment_resale(wb, retail_by_id):
    """
    Read the Resale sheet and fix:
      - Skip placeholder rows (side is blank).
      - Fill Original Retail from Products lookup when blank.
      - Compute Residual % from raw prices when formula cache is empty.
      - Residual % is stored as decimal fraction so JS normPct() scales it correctly.
    """
    pair_product_map = _build_pair_product_map(wb)

    ws = wb["Resale"]
    all_rows = list(ws.iter_rows(values_only=True))
    result = []

    for row in all_rows[2:]:
        if not any(v is not None and str(v).strip() for v in row):
            continue
        row = list(row)

        pair_id = str(row[RES_PAIR_ID]).strip() if row[RES_PAIR_ID] else ""
        side    = str(row[RES_SIDE]).strip()    if row[RES_SIDE]    else ""

        # Skip placeholder/empty rows
        if not pair_id or not side:
            continue

        # Fill originalRetail from Products lookup when blank
        if row[RES_ORIG_RETAIL] is None:
            side_key = "m" if side.lower() == "manteco" else "c"
            prod_id = pair_product_map.get(pair_id, {}).get(side_key, "")
            if prod_id and prod_id in retail_by_id:
                row[RES_ORIG_RETAIL] = retail_by_id[prod_id]

        # Compute residual % as decimal fraction when formula cache is empty
        if row[RES_RESIDUAL_PCT] is None:
            orig   = row[RES_ORIG_RETAIL]
            resale = row[RES_RESALE_PRICE]
            if orig is not None and resale is not None:
                try:
                    row[RES_RESIDUAL_PCT] = round(float(resale) / float(orig), 4)
                except (ValueError, TypeError, ZeroDivisionError):
                    pass

        result.append(row)

    return result


def _v(v):
    return "" if v is None else str(v)


@app.route("/")
def index():
    return send_file(os.path.join(HERE, "manteco_dashboard.html"))


@app.route("/sheet/<name>")
def serve_sheet(name):
    meta = SHEET_META.get(name.lower())
    if not meta:
        return jsonify({"error": "Unknown sheet"}), 404

    if not os.path.exists(EXCEL_FILE):
        return jsonify({"error": "Manteco Workbook.xlsx not found in server directory"}), 404

    try:
        wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
        ws = wb[meta[0]]
        all_rows = list(ws.iter_rows(values_only=True))

        title_row  = all_rows[0]
        header_row = all_rows[1]

        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([_v(v) for v in title_row])
        w.writerow([_v(v) for v in header_row])

        if name.lower() == "products":
            _, aug_rows = _build_product_lookup(wb)
            for row in aug_rows:
                w.writerow([_v(v) for v in row])

        elif name.lower() == "pairs":
            retail_by_id, _ = _build_product_lookup(wb)
            for row in _augment_pairs(wb, retail_by_id):
                w.writerow([_v(v) for v in row])

        elif name.lower() == "resale":
            retail_by_id, _ = _build_product_lookup(wb)
            for row in _augment_resale(wb, retail_by_id):
                w.writerow([_v(v) for v in row])

        else:
            # Markdown — emit as-is, skipping empty rows
            data_rows = all_rows[meta[1] - 1:]
            for row in data_rows:
                if any(v is not None and str(v).strip() for v in row):
                    w.writerow([_v(v) for v in row])

        return Response(
            out.getvalue(),
            mimetype="text/csv",
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/csv-proxy")
def csv_proxy():
    url = request.args.get("url", "")
    if not url.startswith("https://docs.google.com/spreadsheets"):
        return jsonify({"error": "Only Google Sheets URLs allowed"}), 400
    try:
        r = requests.get(
            url,
            headers={**HEADERS, "Cache-Control": "no-cache", "Pragma": "no-cache"},
            timeout=15,
            allow_redirects=True,
        )
        r.raise_for_status()
        return Response(
            r.content,
            mimetype="text/csv",
            headers={"Access-Control-Allow-Origin": "*"},
        )
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
