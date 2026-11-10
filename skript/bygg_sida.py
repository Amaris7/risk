#!/usr/bin/env python3
"""Bygger index.html av mallen skript/mall.html, annonsdatan i data/annonser.json
och kurskalendern i data/kurskalender.ics (om den finns).

Kör:  python3 skript/bygg_sida.py
Utseende och texter ändrar du i skript/mall.html. Platshållaren __DATA__ ersätts med datan.
"""
import datetime, json, os, re

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MALL = os.path.join(ROT, "skript", "mall.html")
DATA = os.path.join(ROT, "data", "annonser.json")
KALENDER = os.path.join(ROT, "data", "kurskalender.ics")
UT = os.path.join(ROT, "index.html")

# Personliga Zoom-rum ska inte ligga på en publik sida. Sätt till False om sidan bara är för dig.
DOLJ_ZOOMLANKAR = True


def las_ics(sokvag):
    """Enkel ICS-läsare: räcker för kalendrar med VEVENT, heldagar och lokal tid (TZID)."""
    with open(sokvag, encoding="utf-8") as f:
        rader = f.read().replace("\r\n", "\n").replace("\n ", "").replace("\n\t", "").split("\n")
    def avkoda(v):
        return v.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")
    def tid(nyckel, v):
        if "VALUE=DATE" in nyckel or len(v) == 8:
            return datetime.date(int(v[:4]), int(v[4:6]), int(v[6:8])).isoformat(), True
        return f"{v[:4]}-{v[4:6]}-{v[6:8]}T{v[9:11]}:{v[11:13]}", False
    handelser, h, namn = [], None, ""
    for rad in rader:
        if rad == "BEGIN:VEVENT":
            h = {}
        elif rad == "END:VEVENT" and h is not None:
            handelser.append(h); h = None
        elif ":" in rad:
            nyckel, v = rad.split(":", 1)
            bas = nyckel.split(";")[0]
            if h is None:
                if bas == "X-WR-CALNAME": namn = avkoda(v)
                continue
            if bas in ("DTSTART", "DTEND"):
                h[bas], h["heldag"] = tid(nyckel, v)
            elif bas in ("SUMMARY", "LOCATION", "DESCRIPTION", "URL"):
                h[bas] = avkoda(v)
    ut = []
    for h in handelser:
        titel = h.get("SUMMARY", "")
        m = re.match(r"([A-ZÅÄÖ]{2,6}\d{2,3})\s*:\s*(.*)", titel)
        kod, titel = (m.group(1), m.group(2)) if m else ("", titel)
        info, url = h.get("DESCRIPTION", ""), h.get("URL", "")
        if DOLJ_ZOOMLANKAR:
            info = re.sub(r"\n?Anslut via Zoom:\s*https?://\S*zoom\S*", "", info)
            info = re.sub(r"https?://\S*zoom\.us\S*", "(länk i Canvas)", info)
            if "zoom" in url: url = ""
        ut.append({"kod": kod, "titel": titel.strip(), "start": h.get("DTSTART", ""), "slut": h.get("DTEND", ""),
                   "heldag": h.get("heldag", False), "plats": h.get("LOCATION", ""), "info": info.strip(), "url": url})
    ut.sort(key=lambda e: e["start"])
    andrad = datetime.date.fromtimestamp(os.path.getmtime(sokvag)).isoformat()
    return {"namn": namn, "andrad": andrad, "handelser": ut}


with open(DATA, encoding="utf-8") as f:
    data = json.load(f)
data["kalender"] = las_ics(KALENDER) if os.path.exists(KALENDER) else None
with open(MALL, encoding="utf-8") as f:
    mall = f.read()

js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = mall.replace("__DATA__", js)

# Mallen saknar <!doctype>/<head>, så lägg på ett skal som gör filen fristående
if not html.lstrip().lower().startswith("<!doctype"):
    html = ('<!doctype html>\n<html lang="sv">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<style>html{color-scheme:light dark}body{margin:0}[hidden]{display:none!important}img{max-width:100%}</style>\n'
            '</head>\n<body>\n' + html + '\n</body>\n</html>\n')

with open(UT, "w", encoding="utf-8") as f:
    f.write(html)
kal = data["kalender"]
print(f"Skrev {UT} ({len(html) // 1024} KB, {len(data['annonser'])} annonser, hämtade {data['hamtad']}, "
      f"{len(kal['handelser']) if kal else 0} kalenderhändelser)")
