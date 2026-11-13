"""Browser dashboard for the lead agent — no API keys needed.

Run from the repo root:
    pip install -r requirements.txt
    python webapp/app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template, request

from lead_agent.audit import audit_website
from lead_agent.yellowpages import scrape_yellowpages

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def run():
    data = request.get_json(force=True, silent=True) or {}
    niche = (data.get("niche") or "").strip()
    city = (data.get("city") or "").strip()
    try:
        max_results = min(int(data.get("max_results") or 60), 150)
    except (TypeError, ValueError):
        max_results = 60
    include_missing = bool(data.get("include_missing"))

    if not niche or not city:
        return jsonify({"error": "Please enter both a niche and a city."}), 400

    leads = scrape_yellowpages(niche, city, max_results=max_results)
    if not leads:
        return jsonify({"leads": [], "count": 0,
                        "error": "No businesses found — try a broader niche "
                                 "or check the city spelling."})

    with_website = [lead for lead in leads if lead["website"]]
    without_website = [lead for lead in leads if not lead["website"]]

    audits = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(audit_website, lead["website"]): lead
                   for lead in with_website}
        for future in as_completed(futures):
            lead = futures[future]
            try:
                audits[id(lead)] = future.result()
            except Exception as exc:
                audits[id(lead)] = {
                    "score": 0, "signals": ["unreachable"],
                    "notes": [f"audit error: {exc}"],
                }

    results = []
    for lead in leads:
        row = dict(lead)
        if lead["website"]:
            row.update(audits.get(id(lead), {"score": 0, "signals": [],
                                             "notes": []}))
        else:
            row.update({
                "score": 50 if include_missing else 0,
                "signals": ["no_website"] if include_missing else [],
                "notes": ["no website found at all"] if include_missing else [],
            })
        results.append(row)

    results.sort(key=lambda row: row.get("score", 0), reverse=True)
    return jsonify({
        "leads": results,
        "count": len(results),
        "audited": len(with_website),
        "no_website": len(without_website),
    })


if __name__ == "__main__":
    print("Lead Agent dashboard running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
