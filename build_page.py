"""Tekee data.json:sta sivun site/index.html.

Säännöt:
  - Kokeet: kaikki tästä päivästä eteenpäin.
  - Läksyt: 3 viimeisen koulupäivän (ma–pe) aikana annetut + mahdolliset tulevat.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Helsinki")
SCHOOL_DAYS = int(os.environ.get("LAKSYPAIVAT", "3"))


def homework_cutoff(today: date, n: int) -> date:
    d, count = today, 0
    while True:
        if d.weekday() < 5:
            count += 1
            if count == n:
                return d
        d -= timedelta(days=1)


def build(data: dict, now: datetime) -> str:
    today = now.date()
    cutoff = homework_cutoff(today, SCHOOL_DAYS).isoformat()
    t = today.isoformat()
    kids = []
    for c in data["children"]:
        exams = sorted((e for e in c["exams"] if e["date"] >= t), key=lambda e: (e["date"], e["subject"]))
        hw = sorted((h for h in c["homework"] if h["date"] >= cutoff), key=lambda h: (h["date"], h["subject"]), reverse=True)
        kids.append({"name": c["name"], "exams": exams, "homework": hw})
    payload = {"updated": now.isoformat(timespec="minutes"), "cutoff": cutoff, "kids": kids}
    tpl = open(os.path.join(os.path.dirname(__file__), "template.html"), encoding="utf-8").read()
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return tpl.replace("__DATA__", blob)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "site/index.html"
    now = datetime.now(TZ)
    if os.environ.get("NOW"):  # testausta varten
        now = datetime.fromisoformat(os.environ["NOW"]).replace(tzinfo=TZ)
    data = json.load(open(src, encoding="utf-8"))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8").write(build(data, now))
    print(f"Sivu kirjoitettu: {out}")
