"""Vie tulevat kokeet salattuna tiedostona Harjoittelu-sovellusta varten.

Käyttö: KOKEET_AVAIN=<sivun salasana> python vie_kokeet.py data.json site/kokeet.json
Salaus: AES-256-CBC, avain = sha256("harjoittelu-kokeet:" + salasana), satunnainen IV.
Harjoittelu-sovelluksen Worker purkaa tiedoston samalla salasanalla (secret KOULU_SALASANA).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from wilma import strip_code

TZ = ZoneInfo("Europe/Helsinki")


def payload(data: dict, now: datetime) -> dict:
    t = now.date().isoformat()
    kids = []
    for c in data["children"]:
        exams = sorted(
            ({"date": e["date"], "subject": strip_code(e.get("subject", "")), "title": e.get("title", ""), "topic": e.get("topic", "")}
             for e in c.get("exams", []) if e.get("date", "") >= t),
            key=lambda e: (e["date"], e["subject"]))
        kids.append({"name": c["name"], "exams": exams})
    return {"updated": now.isoformat(timespec="minutes"), "kids": kids}


def encrypt(plain: bytes, password: str) -> dict:
    key = hashlib.sha256(("harjoittelu-kokeet:" + password).encode()).hexdigest()
    iv = os.urandom(16).hex()
    out = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-K", key, "-iv", iv],
                         input=plain, capture_output=True, check=True).stdout
    return {"v": 1, "iv": iv, "data": base64.b64encode(out).decode()}


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    pw = os.environ.get("KOKEET_AVAIN", "")
    if not pw:
        sys.exit("KOKEET_AVAIN puuttuu")
    data = json.load(open(src, encoding="utf-8"))
    body = json.dumps(payload(data, datetime.now(TZ)), ensure_ascii=False).encode()
    json.dump(encrypt(body, pw), open(dst, "w"))
    print(f"Kokeet viety: {dst}")
