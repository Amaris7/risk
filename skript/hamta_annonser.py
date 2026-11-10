#!/usr/bin/env python3
"""Hämtar jobbannonser som matchar masterprogrammet Riskhantering i samhället (KAU).

Källa: Arbetsförmedlingens öppna API:er (JobTech), ingen API-nyckel behövs.
  - JobSearch:      aktuella annonser
  - Historical Ads: arkiverade annonser senaste DAGAR_BAKAT dagarna

Resultat: data/annonser.json och data/annonser.csv

Kör:  python3 skript/hamta_annonser.py
Ändra gärna sökord (TERMS), filter (CORE/EXCLUDE), områden (AREAS) och kurskoppling (COURSES) nedan.
"""
import csv, datetime, json, os, re, sys, time, urllib.parse, urllib.request

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROT, "data")
DAGAR_BAKAT = 365          # hur långt bak arkiverade annonser hämtas
MIN_ANTAL = 200            # färre annonser än så tolkas som API-fel; då skrivs inget över
FROM = (datetime.date.today() - datetime.timedelta(days=DAGAR_BAKAT)).isoformat() + "T00:00:00"

TERMS = [
    "beredskapssamordnare", "krisberedskapssamordnare", "beredskapsplanerare", "beredskapshandläggare",
    "krisberedskap", "civilt försvar", "totalförsvar", "höjd beredskap", "beredskapsstrateg",
    "säkerhetssamordnare", "säkerhetsstrateg", "säkerhetschef", "trygghetssamordnare",
    "brottsförebyggande", "riskanalytiker", "riskanalys", "riskhantering", "riskkonsult",
    "risk- och sårbarhetsanalys", "kontinuitetshantering", "kontinuitetsplanering",
    "klimatanpassning", "klimatanpassningsstrateg", "skadeförebyggande", "olycksförebyggande",
    "trafiksäkerhet", "säkerhetsfrämjande", "riskkommunikation", "krisledning", "krisstöd samordnare",
    "säkerhetsskyddschef", "verksamhetsskydd", "räddningstjänst förebyggande", "olycksutredare",
    "säkerhetsanalytiker", "risk manager", "riskingenjör", "försörjningsberedskap",
]

AREAS = [
    ("Krisberedskap & civilt försvar", r"beredskap|civil[at]? försvar|totalförsvar|krisledning|krishantering|krisstöd|försörjningsberedskap|krigsorganisation"),
    ("Säkerhet & trygghet", r"säkerhetssamordn|säkerhetsstrateg|säkerhetschef|säkerhetsskydd|trygghet|brottsförebygg|verksamhetsskydd|säkerhetsanalytiker"),
    ("Riskanalys & riskkonsult", r"riskanaly|riskkonsult|riskhanter|risk manager|riskingenjör|riskbedömning|sårbarhetsanaly|risk"),
    ("Kontinuitetshantering", r"kontinuitet"),
    ("Klimatanpassning & naturolyckor", r"klimatanpass|översvämning|naturolyck|skred|klimat"),
    ("Skadeförebyggande & personsäkerhet", r"skadeförebygg|olycksförebygg|trafiksäkerhet|säkerhetsfrämj|räddningstjänst|olycksutred|brandskydd|förebyggande"),
    ("Riskkommunikation", r"riskkommunikation|kriskommunikation"),
]
# Rubriken måste innehålla något av detta för att räknas (minskar brus)
CORE = re.compile(r"beredskap|kris|civil[at]? försvar|totalförsvar|säkerhet(?!s?vakt)|trygghet|risk|kontinuitet|klimat|skadeförebygg|olycks|brottsförebygg|förebyggande|verksamhetsskydd|räddning", re.I)
EXCLUDE = re.compile(r"citrix|kundservice|fritidsvägledare|fritidsledare|\bvd\b|brandman|brandmän|deltidsbrand|larmoperatör|systemsäkerhet|it[- ]säkerhet|\bit\b|jurist|ekonom|controller|elektriker|montör|tekniker|ingenjör inom ce|väktare|ordningsvakt|it-säkerhet|cyber|informationssäkerhet|livsmedelssäkerhet|patientsäkerhet|elsäkerhet|kreditrisk|underwriter|aktuarie|säkerhetstekniker|lokalvård|undersköterska|sjuksköterska|läkare|kock|lager|säkerhetsvakt|kassa|försäljning|säljare|systemutvecklare|developer|devops|penetration|soc[- ]analytiker|nätverkstekniker|risk(?:-| )?(?:and|&) compliance analyst", re.I)

COURSES = [
    ("RHAD01/RHAD02", "Riskhantering, teori & lagstiftning", r"riskhantering|riskanalys|riskbedömning|sårbarhet|riskbild|hotbild|lagen om extraordinära|\bLEH\b|\bLSO\b|skydd mot olyckor"),
    ("RHAD12/RHAD22", "Personsäkerhet & skadeförebyggande", r"skadeförebygg|olycksförebygg|trafiksäkerhet|säkerhetsfrämj|suicidprevent|våldsprevent|brandskydd|äldresäkerhet|skadestatistik|personsäkerhet|trygghetsskapande|brottsförebygg"),
    ("RHAD21/RHAD31", "Naturkatastrofer & krisberedskap", r"naturolyck|översvämning|skred|extremväder|katastrof|krisberedskap|höjd beredskap|civilt försvar|totalförsvar|krisledning|stab|risk- och sårbarhetsanalys|\bRSA\b|beredskapsplan|varningssystem"),
    ("RHAD14", "Riskperception & riskkommunikation", r"riskkommunikation|kriskommunikation|information till allmänheten|befolkningens beredskap|riskperception"),
    ("RHAD03", "Klimatanpassning & riskreducering", r"klimatanpass|klimatförändring|klimat- och sårbarhet"),
    ("MVAE34", "Hållbarhet & säkerhet (SHM)", r"hållbar utveckling|hållbarhet|miljö och säkerhet|arbetsmiljö"),
    ("RHAD38", "Implementering & utvärdering av åtgärder", r"utvärder|uppfölj|implementer|åtgärdsplan|handlingsplan|styrdokument"),
    ("RHAD39", "Olycksutredning & organisatoriskt lärande", r"olycksutredning|händelseanalys|erfarenhetsåterföring|säkerhetskultur|avvikelse|lärande|övning"),
    ("RHAD35", "Vetenskaplig metod & analys", r"\banalys|utredning|statistik|omvärldsbevakning|kvalitativ|kvantitativ|lägesbild"),
    ("Kontinuitet", "Kontinuitetshantering", r"kontinuitet"),
]
STRONG = re.compile(r"beredskap|sårbarhet|riskanalytiker|riskhantering|säkerhetssamordn|säkerhetsstrateg|kris|klimatanpass|kontinuitet|skadeförebygg|olycksförebygg|trygghetssamordn|trafiksäkerhet|civil[at]? försvar|totalförsvar|riskkonsult|brottsförebygg|säkerhetsfrämj|risk ?manager|olycksutred", re.I)
FIN = re.compile(r"\bbank|finans|kreditrisk|marknadsrisk|försäkring|aktuari|quantitative|fintech|AML|penningtvätt", re.I)

KEYWORDS = ["risk- och sårbarhetsanalys", "RSA", "kontinuitetsplanering", "krisberedskap", "civilt försvar", "höjd beredskap",
            "totalförsvar", "krisledning", "riskanalys", "riskbedömning", "klimatanpassning", "skadeförebyggande",
            "säkerhetsskydd", "riskkommunikation", "omvärldsbevakning", "övningar", "utbildning", "samverkan",
            "lagen om extraordinära händelser", "LEH", "LSO", "projektledning", "säkerhetskultur", "trygghetsskapande",
            "systematiskt säkerhetsarbete", "brottsförebyggande", "masterexamen", "magisterexamen", "säkerhetsprövning", "körkort", "kandidatexamen", "högskoleexamen", "samhällsvetenskap", "krisstöd", "säkerhetsskyddsanalys", "styrdokument", "omvärldsanalys"]

def get(base, params):
    url = base + "?" + urllib.parse.urlencode(params)
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"accept": "application/json"}), timeout=30) as r:
                return json.load(r)
        except Exception as e:
            print("försöker igen:", e, file=sys.stderr); time.sleep(2)
    return {"hits": []}

ads = {}
for src, base, extra in [("aktuell", "https://jobsearch.api.jobtechdev.se/search", {}),
                         ("historisk", "https://historical.api.jobtechdev.se/search", {"historical-from": FROM})]:
    for t in TERMS:
        for off in (0, 100):
            d = get(base, {"q": t, "limit": 100, "offset": off, **extra})
            hits = d.get("hits", [])
            for h in hits:
                head = h.get("headline") or ""
                if not CORE.search(head) or EXCLUDE.search(head):
                    continue
                pub = (h.get("publication_date") or "")[:10]
                if pub < FROM[:10]:
                    continue
                emp = (h.get("employer") or {})
                wa = h.get("workplace_address") or {}
                key = (head.lower().strip(), (emp.get("name") or "").lower(), (wa.get("municipality") or ""))
                text = (h.get("description") or {}).get("text") or ""
                full = head + " " + text
                areas = [a for a, rx in AREAS if re.search(rx, head, re.I)] or \
                        [a for a, rx in AREAS if re.search(rx, full, re.I)][:1]
                if not areas:
                    continue
                kws = [k for k in KEYWORDS if re.search(r"\b" + re.escape(k) + r"\b", full, re.I if not k.isupper() else 0)]
                kurser = [c for c, n, rx in COURSES if re.search(rx, full, re.I)]
                score = len(kurser) + (2 if STRONG.search(head) else 0)
                if score < 3:
                    continue
                if (FIN.search(head) or len(FIN.findall(text)) >= 3) and re.search(r"risk", head, re.I):
                    areas = ["Finansiell & operativ risk (angränsande)"]
                match = "Hög" if score >= 7 else ("Medel" if score >= 5 else "Grundläggande")
                status = "aktuell" if src == "aktuell" else "arkiverad"
                rec = {
                    "id": h["id"], "rubrik": head.strip(), "arbetsgivare": emp.get("workplace") or emp.get("name"),
                    "kommun": wa.get("municipality") or wa.get("city") or "Ospecificerad", "lan": wa.get("region") or "Ospecificerat",
                    "publicerad": pub, "sista": (h.get("application_deadline") or "")[:10],
                    "yrke": (h.get("occupation") or {}).get("label"), "omraden": areas, "nyckelord": kws,
                    "utdrag": re.sub(r"\s+", " ", text)[:320].strip(), "url": h.get("webpage_url"), "status": status,
                    "omfattning": (h.get("working_hours_type") or {}).get("label"),
                    "anstallning": (h.get("employment_type") or {}).get("label"),
                    "kallterm": t, "kurser": kurser, "match": match, "poang": score,
                }
                if key in ads:
                    if status == "aktuell": ads[key].update(status="aktuell", url=rec["url"], sista=rec["sista"])
                    continue
                ads[key] = rec
            if len(hits) < 100:
                break
    print(src, "klart, totalt", len(ads), "annonser", file=sys.stderr)

out = sorted(ads.values(), key=lambda r: r["publicerad"], reverse=True)
out.sort(key=lambda r: r["status"] != "aktuell")

if len(out) < MIN_ANTAL:
    sys.exit(f"Bara {len(out)} annonser hämtades, troligen fel hos API:et. Behåller befintlig data.")

# Spara bara fälten som sidan använder
KEEP = ["rubrik", "arbetsgivare", "kommun", "lan", "publicerad", "sista", "omraden", "nyckelord", "utdrag",
        "url", "status", "omfattning", "kurser", "match", "poang"]
for a in out:
    a["utdrag"] = a["utdrag"][:200]
    a["arbetsgivare"] = a["arbetsgivare"] or "Okänd arbetsgivare"
    for k in list(a):
        if k not in KEEP:
            del a[k]

os.makedirs(DATA_DIR, exist_ok=True)
data = {"hamtad": datetime.date.today().isoformat(), "fran": FROM[:10], "kurser": [[c, n] for c, n, _ in COURSES], "annonser": out}
with open(os.path.join(DATA_DIR, "annonser.json"), "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
with open(os.path.join(DATA_DIR, "annonser.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(KEEP)
    for a in out:
        w.writerow([";".join(a[k]) if isinstance(a[k], list) else a[k] for k in KEEP])
print("Klart:", len(out), "annonser, varav", sum(r["status"] == "aktuell" for r in out), "aktuella", file=sys.stderr)
