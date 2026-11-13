"""Bygger tester/webblasare/_xss.html: den riktiga mallen, men med påhittade annonser och kalenderhändelser
där varje textfält försöker köra skript. Webbläsartestet kontrollerar att inget av det körs."""
import os
import sys

HÄR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.dirname(os.path.dirname(HÄR))
sys.path.insert(0, os.path.join(ROT, "skript"))
import bygg_sida as B  # noqa: E402
import kompetenser  # noqa: E402
import statistik  # noqa: E402

ELAK = '"><img src=x onerror="window.__xss=1"><script>window.__xss=1</script>'
ELAK2 = "</script><script>window.__xss=1</script><!--"

annons = {
    "id": "999", "rubrik": "Beredskapssamordnare " + ELAK, "arbetsgivare": ELAK2, "kommun": ELAK, "lan": "Värmlands län",
    "publicerad": "2026-11-01", "sista": "2026-12-01", "omraden": ["Krisberedskap & civilt försvar", ELAK],
    "nyckelord": [ELAK], "utdrag": ELAK, "url": "javascript:window.__xss=1", "status": "aktuell",
    "omfattning": ELAK, "kurser": ["RHAD21/RHAD31", ELAK], "match": "Hög", "poang": 9,
    "krav": ["Körkort", ELAK], "junior": True,
}
data = {
    "hamtad": "2026-11-11", "fran": "2025-11-11", "kurser": [], "annonser": [annons],
    "kalender": {"andrad": "2026-11-11", "handelser": [{
        "kod": "RHAD12", "titel": "Seminarium " + ELAK, "start": "2099-01-01T10:00", "slut": "2099-01-01T12:00",
        "heldag": False, "plats": ELAK2, "info": ELAK, "url": "", "uppgift": False}]},
}

# Statistiken räknas med samma Python-kod som på riktigt, men på den elaka datan
data["statistik"] = statistik.berakna(data["annonser"], {"RHAD21/RHAD31", ELAK}, {"999": ELAK})
data["kompetens"] = kompetenser.statistik(data["annonser"], {"999": ELAK})

with open(os.path.join(ROT, "skript", "mall.html"), encoding="utf-8") as f:
    mall = f.read()
with open(os.path.join(ROT, "skript", "logik.js"), encoding="utf-8") as f:
    logik = f.read()
with open(os.path.join(HÄR, "_xss.html"), "w", encoding="utf-8") as f:
    f.write(B.bygg(mall, data, logik))
