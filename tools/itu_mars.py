#!/usr/bin/env python3
"""Look up a ship in the ITU's MARS ship station list (the official register of MMSIs and call signs notified by
national administrations). Standard library only. One request per lookup, results cached; please keep it light.

  itu_mars.py --mmsi 413255690
  itu_mars.py --name "SHI YAN 6"
  itu_mars.py --callsign BIPK          (call-sign search is unreliable on the ITU side: a miss is not proof)

Prints one line per record: name | call sign | MMSI | administration | last updated.
"""
import argparse
import hashlib
import html
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

URL = "https://mmsapp.itu.int/mmsapp/ShipStation/list"
UA = "china-state-vessels/0.1 (open dataset research; https://github.com/Ghongha007/china-state-vessels)"
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "china-state-vessels", "itu")


def search(mmsi="", name="", callsign=""):
    os.makedirs(CACHE, exist_ok=True)
    key = os.path.join(CACHE, hashlib.sha1(f"{mmsi}|{name}|{callsign}".encode()).hexdigest()[:16] + ".json")
    if os.path.exists(key):
        return json.load(open(key))
    stamp = os.path.join(CACHE, ".last")              # at most one search every 8 seconds, even across runs
    if os.path.exists(stamp):
        wait = 8 - (time.time() - os.path.getmtime(stamp))
        if wait > 0: time.sleep(wait)
    open(stamp, "w").close()
    jar = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", UA)]
    page = op.open(URL, timeout=60).read().decode("utf-8", "replace")
    form = {m.group(1): html.unescape(m.group(2)) for m in re.finditer(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', page)}
    form = {k: v for k, v in form.items() if not k.startswith("Search.")}
    form.update({"Search.MaritimeMobileServiceIdentity": mmsi, "Search.Name": name, "Search.CallSign": callsign, "viewCommand": "Search"})
    time.sleep(1)
    res = op.open(URL, data=urllib.parse.urlencode(form).encode(), timeout=60).read().decode("utf-8", "replace")
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", res, re.S):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) >= 4 and any(re.fullmatch(r"\d{9}", c) for c in cells):
            rows.append(cells)
    json.dump(rows, open(key, "w"))
    time.sleep(1)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mmsi", default=""); ap.add_argument("--name", default=""); ap.add_argument("--callsign", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not (a.mmsi or a.name or a.callsign): sys.exit("give --mmsi, --name or --callsign")
    try:
        rows = search(a.mmsi, a.name, a.callsign)
    except urllib.error.HTTPError as ex:
        sys.exit(f"ITU refused the request (HTTP {ex.code}); it limits how often you can search. Wait a while and try again.")
    if a.json: print(json.dumps(rows, ensure_ascii=False)); return 0
    if not rows: print("no record found"); return 1
    for r in rows: print(" | ".join(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
