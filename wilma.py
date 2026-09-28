"""Hakee Wilmasta lasten tulevat kokeet ja viimeaikaiset läksyt.

Tunnukset luetaan ympäristömuuttujista (GitHub Secrets):
  WILMA_URL       esim. https://jyvaskyla.inschool.fi
  WILMA_USER      huoltajan käyttäjätunnus
  WILMA_PASSWORD  huoltajan salasana

HUOM: repo voi olla julkinen, joten tämä skripti EI tulosta lokiin
lasten nimiä, läksyjä tai kokeita – vain lukumääriä.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)


class WilmaError(Exception):
    pass


def parse_date(raw: str | None) -> str | None:
    """'4.9.2026' / '2026-09-04' / '2026-09-04T00:00' -> '2026-09-04'."""
    if not raw:
        return None
    s = str(raw).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m[1]}-{m[2]}-{m[3]}"
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)
    if m:
        return f"{m[3]}-{int(m[2]):02d}-{int(m[1]):02d}"
    return None


def clean(text: str | None) -> str:
    if not text:
        return ""
    text = BeautifulSoup(str(text), "html.parser").get_text("\n")
    text = text.replace("\r\n", "\n")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln).strip()


class Wilma:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Referer": self.base + "/"})

    # ---------- kirjautuminen ----------
    def login(self, username: str, password: str) -> None:
        fields: dict[str, str] = {}
        r = self.s.get(self.base + "/login", timeout=30)
        if r.ok:
            soup = BeautifulSoup(r.text, "html.parser")
            for inp in soup.find_all("input"):
                name = inp.get("name")
                typ = (inp.get("type") or "text").lower()
                if name and name not in ("Login", "Password") and typ in ("hidden", "submit"):
                    fields[name] = inp.get("value", "")
        if not fields.get("SESSIONID"):
            t = self.s.get(self.base + "/token", timeout=30)
            m = re.search(r'"Wilma2LoginID"\s*:\s*"([^"\s]+)"', t.text)
            if not m:
                title = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
                raise WilmaError(
                    "Kirjautumistunnistetta (SESSIONID) ei saatu – "
                    f"/login HTTP {r.status_code} ({r.headers.get('server', '?')}, "
                    f"otsikko: {title[1].strip()[:60] if title else '-'}), /token HTTP {t.status_code}"
                )
            fields["SESSIONID"] = m[1]

        fields.update({"Login": username, "Password": password})
        r = self.s.post(self.base + "/login", data=fields, allow_redirects=False, timeout=30)
        location = r.headers.get("location", "")
        if "loginfailed" in location.lower() or "loginfailed" in r.text.lower():
            raise WilmaError("Kirjautuminen epäonnistui – tarkista tunnus ja salasana")
        if "Wilma2SID" not in self.s.cookies.get_dict():
            raise WilmaError("Kirjautuminen epäonnistui (ei istuntoevästettä)")
        if location:
            follow = self.s.get(requests.compat.urljoin(self.base + "/", location), timeout=30)
            if 'id="mfa-formkey"' in follow.text:
                raise WilmaError("Wilma pyytää kaksivaiheista tunnistautumista – automaatio ei toimi")

    # ---------- lapset ----------
    def students(self) -> list[dict]:
        out: dict[str, dict] = {}
        try:
            r = self.s.get(self.base + "/api/v1/accounts/me/roles", timeout=30)
            data = r.json()
            roles = data.get("payload", data) if isinstance(data, dict) else data
            for role in roles or []:
                typ = role.get("type", role.get("Type"))
                if typ in ("passwd", 7, "7"):
                    continue
                m = re.search(r"!?(\d+)", str(role.get("slug", role.get("Slug", ""))))
                if m:
                    out.setdefault(m[1], {"id": m[1], "name": role.get("name") or role.get("Name") or m[1]})
        except (ValueError, requests.RequestException, AttributeError):
            pass
        if not out:  # vanhempi Wilma: etsitään linkit etusivulta
            r = self.s.get(self.base + "/", timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                m = re.search(r"/!(\d+)(?:/|$)", a["href"])
                if m and m[1] not in out:
                    txt = a.get_text(" ", strip=True)
                    out[m[1]] = {"id": m[1], "name": txt or m[1]}
        return list(out.values())

    # ---------- data ----------
    def overview(self, sid: str) -> dict:
        r = self.s.get(f"{self.base}/!{sid}/overview", timeout=30)
        r.raise_for_status()
        try:
            return r.json()
        except ValueError:
            raise WilmaError("/overview ei palauttanut JSONia")

    def exam_calendar(self, sid: str) -> list[dict]:
        r = self.s.get(f"{self.base}/!{sid}/exams/calendar", timeout=30)
        if not r.ok:
            return []
        return parse_exam_calendar(r.text)


def parse_exam_calendar(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    exams = []
    for block in soup.select("div.table-responsive.margin-bottom"):
        table = block.select_one("table.table-grey")
        if not table:
            continue
        rows = table.find_all("tr")
        if not rows:
            continue
        cells = rows[0].find_all("td")
        if len(cells) < 2:
            continue
        d = parse_date(cells[0].get_text(" ", strip=True))
        if not d:
            continue
        head = re.sub(r"\s+", " ", cells[1].get_text(" ", strip=True))
        subject, title = head, ""
        if ":" in head:
            title, subject = head.split(":", 1)
        teacher, notes = "", ""
        for row in rows[1:]:
            th, td = row.find("th"), row.find("td")
            if not th or not td:
                continue
            h = th.get_text(strip=True).lower()
            if "opettaja" in h:
                teacher = ", ".join(a.get_text(strip=True) for a in td.select("a.profile-link")) or td.get_text(" ", strip=True)
            elif "lisätiedot" in h or "notes" in h:
                notes = clean(td.decode_contents())
        exams.append({
            "date": d,
            "subject": subject.strip(),
            "title": title.strip(),
            "topic": notes,
            "teacher": teacher,
        })
    return exams


def extract(ov: dict, cal: list[dict]) -> tuple[list[dict], list[dict]]:
    homework, exams = [], []
    for g in ov.get("Groups") or []:
        subject = g.get("CourseName") or g.get("Caption") or g.get("CourseCode") or ""
        teachers = ", ".join(t.get("TeacherName", "") for t in g.get("Teachers") or [] if t.get("TeacherName"))
        for hw in g.get("Homework") or []:
            text = clean(hw.get("Homework"))
            d = parse_date(hw.get("Date"))
            if text and d:
                homework.append({"date": d, "subject": subject, "text": text, "teacher": teachers})
        for ex in g.get("Exams") or []:
            if str(ex.get("Grade") or "").strip():
                continue  # jo arvioitu = mennyt koe
            d = parse_date(ex.get("Date"))
            if d:
                exams.append({
                    "date": d,
                    "subject": subject,
                    "title": clean(ex.get("Caption") or ex.get("Name")),
                    "topic": clean(ex.get("Topic") or ex.get("Info")),
                    "teacher": teachers,
                })
    # Yhdistetään koekalenterin kokeet (voi sisältää kokeita, joita overview ei näytä).
    # Sama koe voi tulla molemmista eri muodossa: "ENA01 : Englanti, A1" vs "Englanti, A1".
    for e in cal:
        dup = next((x for x in exams if same_exam(x, e)), None)
        if dup:
            if not dup["topic"] and e["topic"]:
                dup["topic"] = e["topic"]
            continue
        e = dict(e, subject=strip_code(e["subject"]))
        exams.append(e)
    return homework, exams


def strip_code(subject: str) -> str:
    """'ENA01 : Englanti, A1' -> 'Englanti, A1'."""
    return re.sub(r"^\s*[\wÅÄÖåäö.\-]+\s*:\s*", "", subject or "").strip() or (subject or "")


def same_exam(a: dict, b: dict) -> bool:
    if a["date"] != b["date"]:
        return False
    sa, sb = strip_code(a["subject"]).lower(), strip_code(b["subject"]).lower()
    if sa and sb and (sa in sb or sb in sa):
        return True
    ta, tb = (a.get("title") or "").lower(), (b.get("title") or "").lower()
    return bool(ta) and ta == tb and (a.get("topic") or "") == (b.get("topic") or "")


def fetch_all() -> dict:
    url = os.environ.get("WILMA_URL", "https://jyvaskyla.inschool.fi")
    user = os.environ["WILMA_USER"]
    pw = os.environ["WILMA_PASSWORD"]
    w = Wilma(url)
    w.login(user, pw)
    studs = w.students()
    if not studs:
        raise WilmaError("Tililtä ei löytynyt yhtään oppilasta")
    children = []
    for i, st in enumerate(studs, 1):
        ov = w.overview(st["id"])
        cal = w.exam_calendar(st["id"])
        hw, ex = extract(ov, cal)
        print(f"Oppilas {i}: {len(hw)} läksyä, {len(ex)} koetta (overview-avaimet: {sorted(ov.keys())})")
        children.append({"name": st["name"], "homework": hw, "exams": ex})
    return {"children": children}


if __name__ == "__main__":
    try:
        data = fetch_all()
    except (WilmaError, requests.RequestException, KeyError) as e:
        print(f"VIRHE: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1] if len(sys.argv) > 1 else "data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
"""Hakee Wilmasta lasten tulevat kokeet ja viimeaikaiset läksyt.

Tunnukset luetaan ympäristömuuttujista (GitHub Secrets):
  WILMA_URL       esim. https://jyvaskyla.inschool.fi
  WILMA_USER      huoltajan käyttäjätunnus
  WILMA_PASSWORD  huoltajan salasana

HUOM: repo voi olla julkinen, joten tämä skripti EI tulosta lokiin
lasten nimiä, läksyjä tai kokeita – vain lukumääriä.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)


class WilmaError(Exception):
    pass


def parse_date(raw: str | None) -> str | None:
    """'4.9.2026' / '2026-09-04' / '2026-09-04T00:00' -> '2026-09-04'."""
    if not raw:
        return None
    s = str(raw).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m[1]}-{m[2]}-{m[3]}"
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)
    if m:
        return f"{m[3]}-{int(m[2]):02d}-{int(m[1]):02d}"
    return None


def clean(text: str | None) -> str:
    if not text:
        return ""
    text = BeautifulSoup(str(text), "html.parser").get_text("\n")
    text = text.replace("\r\n", "\n")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln).strip()


class Wilma:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Referer": self.base + "/"})

    # ---------- kirjautuminen ----------
    def login(self, username: str, password: str) -> None:
        fields: dict[str, str] = {}
        r = self.s.get(self.base + "/login", timeout=30)
        if r.ok:
            soup = BeautifulSoup(r.text, "html.parser")
            for inp in soup.find_all("input"):
                name = inp.get("name")
                typ = (inp.get("type") or "text").lower()
                if name and name not in ("Login", "Password") and typ in ("hidden", "submit"):
                    fields[name] = inp.get("value", "")
        if not fields.get("SESSIONID"):
            t = self.s.get(self.base + "/token", timeout=30)
            m = re.search(r'"Wilma2LoginID"\s*:\s*"([^"\s]+)"', t.text)
            if not m:
                title = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
                raise WilmaError(
                    "Kirjautumistunnistetta (SESSIONID) ei saatu – "
                    f"/login HTTP {r.status_code} ({r.headers.get('server', '?')}, "
                    f"otsikko: {title[1].strip()[:60] if title else '-'}), /token HTTP {t.status_code}"
                )
            fields["SESSIONID"] = m[1]

        fields.update({"Login": username, "Password": password})
        r = self.s.post(self.base + "/login", data=fields, allow_redirects=False, timeout=30)
        location = r.headers.get("location", "")
        if "loginfailed" in location.lower() or "loginfailed" in r.text.lower():
            raise WilmaError("Kirjautuminen epäonnistui – tarkista tunnus ja salasana")
        if "Wilma2SID" not in self.s.cookies.get_dict():
            raise WilmaError("Kirjautuminen epäonnistui (ei istuntoevästettä)")
        if location:
            follow = self.s.get(requests.compat.urljoin(self.base + "/", location), timeout=30)
            if 'id="mfa-formkey"' in follow.text:
                raise WilmaError("Wilma pyytää kaksivaiheista tunnistautumista – automaatio ei toimi")

    # ---------- lapset ----------
    def students(self) -> list[dict]:
        out: dict[str, dict] = {}
        try:
            r = self.s.get(self.base + "/api/v1/accounts/me/roles", timeout=30)
            data = r.json()
            roles = data.get("payload", data) if isinstance(data, dict) else data
            for role in roles or []:
                typ = role.get("type", role.get("Type"))
                if typ in ("passwd", 7, "7"):
                    continue
                m = re.search(r"!?(\d+)", str(role.get("slug", role.get("Slug", ""))))
                if m:
                    out.setdefault(m[1], {"id": m[1], "name": role.get("name") or role.get("Name") or m[1]})
        except (ValueError, requests.RequestException, AttributeError):
            pass
        if not out:  # vanhempi Wilma: etsitään linkit etusivulta
            r = self.s.get(self.base + "/", timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                m = re.search(r"/!(\d+)(?:/|$)", a["href"])
                if m and m[1] not in out:
                    txt = a.get_text(" ", strip=True)
                    out[m[1]] = {"id": m[1], "name": txt or m[1]}
        return list(out.values())

    # ---------- data ----------
    def overview(self, sid: str) -> dict:
        r = self.s.get(f"{self.base}/!{sid}/overview", timeout=30)
        r.raise_for_status()
        try:
            return r.json()
        except ValueError:
            raise WilmaError("/overview ei palauttanut JSONia")

    def exam_calendar(self, sid: str) -> list[dict]:
        r = self.s.get(f"{self.base}/!{sid}/exams/calendar", timeout=30)
        if not r.ok:
            return []
        return parse_exam_calendar(r.text)


def parse_exam_calendar(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    exams = []
    for block in soup.select("div.table-responsive.margin-bottom"):
        table = block.select_one("table.table-grey")
        if not table:
            continue
        rows = table.find_all("tr")
        if not rows:
            continue
        cells = rows[0].find_all("td")
        if len(cells) < 2:
            continue
        d = parse_date(cells[0].get_text(" ", strip=True))
        if not d:
            continue
        head = re.sub(r"\s+", " ", cells[1].get_text(" ", strip=True))
        subject, title = head, ""
        if ":" in head:
            title, subject = head.split(":", 1)
        teacher, notes = "", ""
        for row in rows[1:]:
            th, td = row.find("th"), row.find("td")
            if not th or not td:
                continue
            h = th.get_text(strip=True).lower()
            if "opettaja" in h:
                teacher = ", ".join(a.get_text(strip=True) for a in td.select("a.profile-link")) or td.get_text(" ", strip=True)
            elif "lisätiedot" in h or "notes" in h:
                notes = clean(td.decode_contents())
        exams.append({
            "date": d,
            "subject": subject.strip(),
            "title": title.strip(),
            "topic": notes,
            "teacher": teacher,
        })
    return exams


def extract(ov: dict, cal: list[dict]) -> tuple[list[dict], list[dict]]:
    homework, exams = [], []
    for g in ov.get("Groups") or []:
        subject = g.get("CourseName") or g.get("Caption") or g.get("CourseCode") or ""
        teachers = ", ".join(t.get("TeacherName", "") for t in g.get("Teachers") or [] if t.get("TeacherName"))
        for hw in g.get("Homework") or []:
            text = clean(hw.get("Homework"))
            d = parse_date(hw.get("Date"))
            if text and d:
                homework.append({"date": d, "subject": subject, "text": text, "teacher": teachers})
        for ex in g.get("Exams") or []:
            if str(ex.get("Grade") or "").strip():
                continue  # jo arvioitu = mennyt koe
            d = parse_date(ex.get("Date"))
            if d:
                exams.append({
                    "date": d,
                    "subject": subject,
                    "title": clean(ex.get("Caption") or ex.get("Name")),
                    "topic": clean(ex.get("Topic") or ex.get("Info")),
                    "teacher": teachers,
                })
    # Yhdistetään koekalenterin kokeet (voi sisältää kokeita, joita overview ei näytä)
    seen = {(e["date"], e["subject"].lower()[:12]) for e in exams}
    for e in cal:
        key = (e["date"], e["subject"].lower()[:12])
        if key in seen:
            for x in exams:  # täydennetään puuttuva aihe
                if (x["date"], x["subject"].lower()[:12]) == key and not x["topic"] and e["topic"]:
                    x["topic"] = e["topic"]
            continue
        exams.append(e)
        seen.add(key)
    return homework, exams


def fetch_all() -> dict:
    url = os.environ.get("WILMA_URL", "https://jyvaskyla.inschool.fi")
    user = os.environ["WILMA_USER"]
    pw = os.environ["WILMA_PASSWORD"]
    w = Wilma(url)
    w.login(user, pw)
    studs = w.students()
    if not studs:
        raise WilmaError("Tililtä ei löytynyt yhtään oppilasta")
    children = []
    for i, st in enumerate(studs, 1):
        ov = w.overview(st["id"])
        cal = w.exam_calendar(st["id"])
        hw, ex = extract(ov, cal)
        print(f"Oppilas {i}: {len(hw)} läksyä, {len(ex)} koetta (overview-avaimet: {sorted(ov.keys())})")
        children.append({"name": st["name"], "homework": hw, "exams": ex})
    return {"children": children}


if __name__ == "__main__":
    try:
        data = fetch_all()
    except (WilmaError, requests.RequestException, KeyError) as e:
        print(f"VIRHE: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1] if len(sys.argv) > 1 else "data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
