"""Testaa jäsennys ja sivun rakennus keksityllä datalla: python test/testaa.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wilma import extract, parse_exam_calendar

OV = {"Role":"guardian","Groups":[
 {"CourseName":"Matematiikka","CourseCode":"MA7","Teachers":[{"TeacherName":"Laine Pekka"}],
  "Homework":[{"Date":"2026-09-28","Homework":"s. 42 teht. 1–5"},{"Date":"2026-09-24","Homework":"s. 40 teht. 3, 4"},{"Date":"2026-09-17","Homework":"vanha läksy"}],
  "Exams":[{"Date":"6.10.2026","Caption":"Jakson 1 koe","Topic":"Kappaleet 1–8\r\nMuista laskin"},{"Date":"10.9.2026","Name":"Pistokoe","Grade":"9"}]},
 {"CourseName":"Englanti","Teachers":[],
  "Homework":[{"Date":"25.9.2026","Homework":"<p>Opettele sanat <b>Unit 3</b></p>"}],
  "Exams":[{"Date":"30.9.2026","Caption":"Sanakoe","Topic":"Unit 3"}]}]}
CAL = """<div class="table-responsive margin-bottom"><table class="table-grey">
<tr><td>Ma 6.10.2026</td><td>Jakson 1 koe: MAA07 : Matematiikka</td></tr>
<tr><th>Opettaja</th><td><a class="profile-link">Laine Pekka</a></td></tr></table></div>
<div class="table-responsive margin-bottom"><table class="table-grey">
<tr><td>To 15.10.2026</td><td>Esitelmä: Historia</td></tr>
<tr><th>Lisätiedot</th><td>Aiheena keskiaika</td></tr></table></div>
<div class="table-responsive margin-bottom"><table class="table-grey">
<tr><td>Ke 30.9.2026</td><td>Sanakoe: ENA01 : Englanti</td></tr>
<tr><th>Lisätiedot</th><td>Unit 3</td></tr></table></div>"""

cal = parse_exam_calendar(CAL)
assert len(cal) == 3 and cal[1] == {"date":"2026-10-15","subject":"Historia","title":"Esitelmä","topic":"Aiheena keskiaika","teacher":""}, cal
hw, ex = extract(OV, cal)
assert len(hw) == 4 and any(h["text"] == "Opettele sanat\nUnit 3" or "Unit 3" in h["text"] for h in hw)
assert len(ex) == 3 and {e["date"] for e in ex} == {"2026-10-06", "2026-09-30", "2026-10-15"}, ex
assert [e["subject"] for e in ex if e["date"] == "2026-10-15"] == ["Historia"]   # arvioitu koe pois, duplikaatti yhdistetty
kid2_hw, kid2_ex = extract({"Groups":[{"CourseName":"Ympäristöoppi","Homework":[{"Date":"2026-09-28","Homework":"Tuo syksyn lehti"}],"Exams":[]}]}, [])
data = {"children":[{"name":"Nieminen Aino","homework":hw,"exams":ex},{"name":"Nieminen Eetu","homework":kid2_hw,"exams":kid2_ex}]}
json.dump(data, open("test/data.json","w"), ensure_ascii=False, indent=1)
print("OK: jäsennys", len(hw), "läksyä,", len(ex), "koetta")
