#!/usr/bin/env python3
"""Bygger index.html av mallen skript/mall.html, annonsdatan i data/annonser.json
och kurskalendern i data/kurskalender.ics (om den finns).

Kör:  python3 skript/bygg_sida.py
Utseende och texter ändrar du i skript/mall.html. Platshållaren __DATA__ ersätts med datan.
"""
import datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import illustrationer  # noqa: E402
from zoneinfo import ZoneInfo

SVENSK_TID = ZoneInfo("Europe/Stockholm")

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
        if v.endswith("Z"):  # UTC (t.ex. Canvas-export) → svensk tid
            t = datetime.datetime.strptime(v, "%Y%m%dT%H%M%SZ").replace(tzinfo=datetime.timezone.utc)
            return t.astimezone(SVENSK_TID).strftime("%Y-%m-%dT%H:%M"), False
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
        # Canvas lägger kurskoden sist: "Inlämning PM [RHAD12, ht26]"
        mb = re.search(r"\s*\[([A-ZÅÄÖ]{2,6}\d{2,3})[^\]]*\]\s*$", titel)
        if mb:
            titel = titel[:mb.start()]
        # Egna händelser har koden först: "RHAD12: Campusträff". Den vinner över Canvas-koden.
        m = re.match(r"([A-ZÅÄÖ]{2,6}\d{2,3})\s*:\s*(.*)", titel)
        kod, titel = (m.group(1), m.group(2)) if m else ((mb.group(1) if mb else ""), titel)
        # Canvas-uppgifter: ingen egen kurskod först och ingen plats
        uppgift = not m and not h.get("LOCATION")
        titel = re.sub(r"^[^\wÅÄÖåäö(]+", "", titel)  # ta bort ikoner som 🔔 🎯
        info, url = h.get("DESCRIPTION", ""), h.get("URL", "")
        if DOLJ_ZOOMLANKAR:
            info = re.sub(r"\n?Anslut via Zoom:\s*https?://\S*zoom\S*", "", info)
            info = re.sub(r"https?://\S*zoom\.us\S*", "(länk i Canvas)", info)
            if "zoom" in url: url = ""
        ut.append({"kod": kod, "titel": titel.strip(), "start": h.get("DTSTART", ""), "slut": h.get("DTEND", ""),
                   "heldag": h.get("heldag", False), "plats": h.get("LOCATION", ""), "info": info.strip(), "url": url,
                   "uppgift": uppgift})
    ut.sort(key=lambda e: e["start"])
    andrad = datetime.date.fromtimestamp(os.path.getmtime(sokvag)).isoformat()
    # Kalenderns namn tas inte med: i Canvas-exporter innehåller det ditt namn
    return {"andrad": andrad, "handelser": ut}


LOGIK = os.path.join(ROT, "skript", "logik.js")

# Säkerhet: sidan får bara ladda skript/data från sig själv och typsnitt från Google Fonts
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'")


def data_som_js(data):
    """JSON som säkert kan bäddas in i <script>: alla < skrivs som \\u003c så att ingen text kan avsluta taggen."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def logik_som_js(kod):
    """logik.js inbäddad i sidan: exportraden för Node tas bort."""
    return re.sub(r"(?s)/\* node-export \*/.*$", "", kod)


def grafik(html, bilder):
    """Byter <!--GRAFIK:namn--> mot illustrationen med det namnet. Okända namn lämnas som tomma."""
    return re.sub(r"<!--GRAFIK:(\w+)-->", lambda m: bilder.get(m.group(1), ""), html)


def bygg(mall, data, logik, bilder=None):
    html = grafik(mall, bilder or {})
    html = html.replace("/*__LOGIK__*/", logik_som_js(logik)).replace("__DATA__", data_som_js(data))
    # Mallen saknar <!doctype>/<head>, så lägg på ett skal som gör filen fristående
    if not html.lstrip().lower().startswith("<!doctype"):
        html = ('<!doctype html>\n<html lang="sv">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                f'<meta http-equiv="Content-Security-Policy" content="{CSP}">\n'
                '<meta name="referrer" content="strict-origin-when-cross-origin">\n'
                '<style>html{color-scheme:light dark}body{margin:0}[hidden]{display:none!important}img{max-width:100%}</style>\n'
                '</head>\n<body>\n' + html + '\n</body>\n</html>\n')
    return html


def main():
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    data["kalender"] = las_ics(KALENDER) if os.path.exists(KALENDER) else None
    with open(MALL, encoding="utf-8") as f:
        mall = f.read()
    with open(LOGIK, encoding="utf-8") as f:
        logik = f.read()
    texter = {}
    sokvag = os.path.join(ROT, "data", "annonstext.json")
    if os.path.exists(sokvag):
        with open(sokvag, encoding="utf-8") as f:
            texter = json.load(f)
    html = bygg(mall, data, logik, illustrationer.alla(data, texter))
    with open(UT, "w", encoding="utf-8") as f:
        f.write(html)
    kal = data["kalender"]
    print(f"Skrev {UT} ({len(html) // 1024} KB, {len(data['annonser'])} annonser, hämtade {data['hamtad']}, "
          f"{len(kal['handelser']) if kal else 0} kalenderhändelser)")


if __name__ == "__main__":
    main()
