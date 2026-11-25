#!/usr/bin/env python3
"""Merge the reviewed batches in work/ into data/vessels.csv, give each vessel a stable ID, and refuse anything that
breaks the dataset's rules. Standard library only.

  python3 tools/build.py            # check and write data/vessels.csv
  python3 tools/build.py --check    # check only

Rules checked for every row (a row that fails is reported and left out):
  - a known category, a name, at least one source URL, a last_checked date
  - militia rows name who identified them (label_source) and carry a tier: confirmed / assessed / possible
  - MMSI, if present, is 9 digits; IMO, if present, is 7 digits with a valid check digit
  - no vessel appears twice (same MMSI, IMO or name)
  - no value is taken from a vessel-tracking site whose terms forbid building datasets
"""
import argparse
import csv
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLS = ["id", "name_en", "name_zh", "former_names", "category", "hull_number", "imo", "mmsi", "call_sign", "flag",
        "operator", "home_port", "type_or_class", "built_year", "notable_activity", "label_source", "label_tier",
        "confidence", "confidence_reason", "registry_check", "sources", "identifier_sources", "last_checked"]
CATEGORIES = ["research", "survey", "space_tracking", "intelligence", "navy_survey", "coast_guard", "militia"]
PREFIX = {"research": "R", "survey": "R", "space_tracking": "N", "intelligence": "N", "navy_survey": "N", "coast_guard": "C", "militia": "M"}
BANNED = re.compile(r"marinetraffic\.com|vesselfinder\.com|myshiptracking\.com|vesseltracker\.com", re.I)


def imo_ok(imo):
    if not re.fullmatch(r"\d{7}", imo): return False
    d = [int(c) for c in imo]
    return sum(d[i] * (7 - i) for i in range(6)) % 10 == d[6]


def problems(r):
    out = []
    if r.get("category") not in CATEGORIES: out.append(f"category {r.get('category')!r}")
    if not (r.get("name_en") or "").strip(): out.append("no name")
    if not re.search(r"https?://", r.get("sources") or ""): out.append("no source URL")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.get("last_checked") or ""): out.append("no last_checked date")
    if r.get("category") == "militia":
        if not (r.get("label_source") or "").strip(): out.append("militia row without label_source")
        if not re.match(r"(confirmed|assessed|possible)\b", r.get("label_tier") or ""): out.append("militia row without a valid label_tier")
    if r.get("mmsi") and not re.fullmatch(r"\d{9}", r["mmsi"]): out.append(f"MMSI {r['mmsi']!r} is not 9 digits")
    if r.get("imo") and not imo_ok(r["imo"]): out.append(f"IMO {r['imo']!r} fails its check digit")
    for k in ("sources", "identifier_sources"):
        v = r.get(k) or ""
        if BANNED.search(v) and "lead only" not in v.lower(): out.append(f"{k} cites a tracking site whose terms forbid datasets")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0]); ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    rows, bad = [], 0
    for path in sorted(glob.glob(os.path.join(ROOT, "work", "*.json"))):
        for r in json.load(open(path, encoding="utf-8")):
            if not isinstance(r, dict) or "category" not in r: continue
            if (r.get("review_status") or "").startswith(("researched, not yet", "rejected")): continue    # only reviewed rows go in
            r = {c: str(r.get(c, "") or "").strip() for c in COLS}
            p = problems(r)
            if p: bad += 1; print(f"LEFT OUT {os.path.basename(path)} {r['name_en'] or '?'}: " + "; ".join(p)); continue
            rows.append(r)
    seen, keep = {}, []
    for r in rows:
        keys = [("mmsi", r["mmsi"]), ("imo", r["imo"]), ("name", re.sub(r"\W", "", r["name_en"].lower()))]
        dup = next((seen[k] for k in keys if k[1] and k in seen), None)
        if dup: print(f"DUPLICATE {r['name_en']} (same as {dup['name_en']}), left out"); bad += 1; continue
        for k in keys:
            if k[1]: seen[k] = r
        keep.append(r)
    keep.sort(key=lambda r: (CATEGORIES.index(r["category"]), r["name_en"].lower()))
    counters = {}
    for r in keep:                                   # stable IDs: CNV-R001, CNV-N001, CNV-C001, CNV-M001
        p = PREFIX[r["category"]]; counters[p] = counters.get(p, 0) + 1; r["id"] = f"CNV-{p}{counters[p]:03d}"
    by = {c: sum(1 for r in keep if r["category"] == c) for c in CATEGORIES}
    print(f"{len(keep)} vessels ok, {bad} left out: " + ", ".join(f"{v} {k}" for k, v in by.items() if v))
    itu_ok = lambda r: r["mmsi"] and re.search(r"ITU MARS: (MMSI|.*MMSI)[^;.]*confirmed", r["registry_check"]) and not re.search(r"not confirmed|unconfirmed", r["registry_check"])
    print(f"MMSI given: {sum(1 for r in keep if r['mmsi'])}; MMSI confirmed in ITU MARS: {sum(1 for r in keep if itu_ok(r))}")
    if a.check: return 1 if bad else 0
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "vessels.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(keep)
    print("wrote data/vessels.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
