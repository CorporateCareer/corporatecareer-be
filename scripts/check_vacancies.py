#!/usr/bin/env python3
"""Dagelijkse vacaturecontrole.

Leest het jobs-data JSON-blok in jobs.html, controleert per vacature of de
officiele bronpagina nog bestaat en de functietitel er nog op staat, en zet
de vacature op inactief na twee opeenvolgende mislukte controles. Herstelt
automatisch zodra de bron weer klopt. Status per vacature staat in
scripts/vacancy_state.json.
"""
import json, re, sys, urllib.request

JOBS_HTML = "jobs.html"
STATE = "scripts/vacancy_state.json"
FAIL_LIMIT = 2

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (vacaturecheck corporatecareer.be)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return None, str(e)

def main():
    html = open(JOBS_HTML, encoding="utf-8").read()
    m = re.search(r'(<script id="jobs-data" type="application/json">)([\s\S]*?)(</script>)', html)
    if not m:
        print("jobs-data blok niet gevonden"); sys.exit(1)
    jobs = json.loads(m.group(2))

    try:
        state = json.load(open(STATE, encoding="utf-8"))
    except Exception:
        state = {}

    cache = {}
    changed = False
    for job in jobs:
        url, key = job.get("url"), str(job["id"])
        check = (job.get("checkText") or job["title"]).lower()
        if url not in cache:
            cache[url] = fetch(url)
        status, body = cache[url]
        ok = status == 200 and check in body.lower()
        fails = 0 if ok else state.get(key, 0) + 1
        state[key] = fails
        should_be_active = fails < FAIL_LIMIT
        if job.get("active", True) != should_be_active:
            job["active"] = should_be_active
            changed = True
            print(f"[{job['company']}] {job['title']}: actief -> {should_be_active} (fails={fails})")
        else:
            print(f"[{job['company']}] {job['title']}: ok={ok} fails={fails}")

    if changed:
        new = m.group(1) + "\n" + json.dumps(jobs, ensure_ascii=False, indent=2) + "\n" + m.group(3)
        open(JOBS_HTML, "w", encoding="utf-8").write(html[:m.start()] + new + html[m.end():])
    json.dump(state, open(STATE, "w", encoding="utf-8"), indent=2)
    print("klaar; wijzigingen:", changed)

if __name__ == "__main__":
    main()
