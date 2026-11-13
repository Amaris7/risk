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
TEXT_MAX = 5000            # max antal tecken per annonstext i sökfilen data/annonstext.json
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
    # klimatrisker och naturolyckor
    "klimatstrateg", "klimatrisk", "klimatsamordnare", "naturolyckor", "översvämning", "skred", "skyfall", "naturkatastrof",
]

AREAS = [
    ("Krisberedskap & civilt försvar", r"beredskap|civil[at]? försvar|totalförsvar|krisledning|krishantering|krisstöd|försörjningsberedskap|krigsorganisation"),
    ("Säkerhet & trygghet", r"säkerhetssamordn|säkerhetsstrateg|säkerhetschef|säkerhetsskydd|trygghet|brottsförebygg|verksamhetsskydd|säkerhetsanalytiker"),
    ("Riskanalys & riskkonsult", r"riskanaly|riskkonsult|riskhanter|risk manager|riskingenjör|riskbedömning|sårbarhetsanaly|risk"),
    ("Kontinuitetshantering", r"kontinuitet"),
    ("Klimatanpassning & naturolyckor", r"klimatanpass|översvämning|naturolyck|\bskred|klimat"),
    ("Skadeförebyggande & personsäkerhet", r"skadeförebygg|olycksförebygg|trafiksäkerhet|säkerhetsfrämj|räddningstjänst|olycksutred|brandskydd|förebyggande"),
    ("Riskkommunikation", r"riskkommunikation|kriskommunikation"),
]
# Rubriken måste innehålla något av detta för att räknas (minskar brus)
CORE = re.compile(r"beredskap|kris(?!tianstad|tinehamn|tina|tian|tin\b)|civil[at]? försvar|totalförsvar|säkerhet(?!s?vakt)|trygghet|risk|kontinuitet|klimat|skadeförebygg|olycks|brottsförebygg|förebyggande|verksamhetsskydd|räddning", re.I)
EXCLUDE = re.compile(r"citrix|kundservice|fritidsvägledare|fritidsledare|\bvd\b|brandman|brandmän|deltidsbrand|larmoperatör|systemsäkerhet|it[- ]säkerhet|\bit\b|jurist|ekonom|controller|elektriker|montör|tekniker|ingenjör inom ce|väktare|ordningsvakt|it-säkerhet|cyber|informationssäkerhet|livsmedelssäkerhet|patientsäkerhet|elsäkerhet|kreditrisk|underwriter|aktuarie|säkerhetstekniker|lokalvård|undersköterska|sjuksköterska|läkare|kock|lager|säkerhetsvakt|kassa|försäljning|säljare|systemutvecklare|developer|devops|penetration|soc[- ]analytiker|nätverkstekniker|säkerhetsarkitekt|risk(?:-| )?(?:and|&) compliance analyst", re.I)

COURSES = [
    ("RHAD01/RHAD02", "Riskhantering, teori & lagstiftning", r"riskhantering|riskanalys|riskbedömning|sårbarhet|riskbild|hotbild|lagen om extraordinära|\bLEH\b|\bLSO\b|skydd mot olyckor"),
    ("RHAD12/RHAD22", "Personsäkerhet & skadeförebyggande", r"skadeförebygg|olycksförebygg|trafiksäkerhet|säkerhetsfrämj|suicidprevent|våldsprevent|brandskydd|äldresäkerhet|skadestatistik|personsäkerhet|trygghetsskapande|brottsförebygg"),
    ("RHAD21/RHAD31", "Naturkatastrofer & krisberedskap", r"naturolyck|översvämning|\bskred|extremväder|katastrof|krisberedskap|höjd beredskap|civilt försvar|totalförsvar|krisledning|stab|risk- och sårbarhetsanalys|\bRSA\b|beredskapsplan|varningssystem"),
    ("RHAD14", "Riskperception & riskkommunikation", r"riskkommunikation|kriskommunikation|krisinformation|information till allmänheten|befolkningens beredskap|riskperception"),
    ("RHAD03", "Klimatanpassning & riskreducering", r"klimatanpass|klimatförändring|klimat- och sårbarhet|risk- och sårbarhetsanalys|\bRSA\b|kontinuitet"),
    ("MVAE34", "Hållbarhet & säkerhet (SHM)", r"hållbar utveckling|hållbarhet|miljö och säkerhet|arbetsmiljö"),
    ("RHAD38", "Implementering & utvärdering av åtgärder", r"utvärder|uppfölj|följa upp|implementer|åtgärdsplan|handlingsplan|styrdokument"),
    ("RHAD39", "Olycksutredning & organisatoriskt lärande", r"olycksutred|händelseanalys|incidenthantering|avvikelsehantering|tillbud|erfarenhetsåterföring|säkerhetskultur|organisatoriskt lärande|övning"),
    ("RHAD35", "Vetenskaplig metod & analys", r"\banalys|utredning|statistik|omvärldsbevakning|kvalitativ|kvantitativ|lägesbild"),
]
STRONG = re.compile(r"beredskap|sårbarhet|riskanalytiker|riskhantering|säkerhetssamordn|säkerhetsstrateg|kris|klimatanpass|kontinuitet|skadeförebygg|olycksförebygg|trygghetssamordn|trafiksäkerhet|civil[at]? försvar|totalförsvar|riskkonsult|brottsförebygg|säkerhetsfrämj|risk ?manager|olycksutred", re.I)
FIN = re.compile(r"\bbank|finans|kreditrisk|marknadsrisk|försäkring|aktuari|quantitative|fintech|AML|penningtvätt", re.I)

KEYWORDS = ["risk- och sårbarhetsanalys", "RSA", "kontinuitetsplanering", "krisberedskap", "civilt försvar", "höjd beredskap",
            "totalförsvar", "krisledning", "riskanalys", "riskbedömning", "klimatanpassning", "skadeförebyggande",
            "säkerhetsskydd", "riskkommunikation", "omvärldsbevakning", "övningar", "utbildning", "samverkan",
            "lagen om extraordinära händelser", "LEH", "LSO", "projektledning", "säkerhetskultur", "trygghetsskapande",
            "systematiskt säkerhetsarbete", "brottsförebyggande", "masterexamen", "magisterexamen", "säkerhetsprövning", "körkort", "kandidatexamen", "högskoleexamen", "samhällsvetenskap", "krisstöd", "säkerhetsskyddsanalys", "styrdokument", "omvärldsanalys"]

# Krav som plockas ur annonstexten. En mening räknas bara som krav om den inte säger att något är meriterande.
KRAV = [
    ("Akademisk examen", r"högskoleexamen|universitetsexamen|akademisk examen|kandidatexamen|masterexamen|magisterexamen|"
                         r"examen från (universitet|högskola)|eftergymnasial utbildning|högskoleutbildning|universitetsutbildning|akademisk utbildning"),
    ("Säkerhetsprövning", r"säkerhetsprövning|säkerhetsklass|säkerhetsprövas|registerkontroll"),
    ("Svenskt medborgarskap", r"svenskt medborgarskap|svensk medborgare"),
    ("Körkort", r"körkort"),
    ("Erfarenhet av beredskap/kris", r"erfarenhet (av|från|inom) [^.]{0,60}(krisberedskap|beredskap|krishantering|krisledning|civilt försvar|totalförsvar)"),
    ("Erfarenhet av säkerhet/risk", r"erfarenhet (av|från|inom) [^.]{0,60}(säkerhetsarbete|säkerhetsskydd|säkerhetsfrågor|riskhantering|riskanalys|riskbedömning)"),
    ("Flera års erfarenhet", r"\d+\s*(–|-|till)?\s*\d*\s*års (yrkes|arbets|relevant )?erfarenhet|flerårig|flera års|några års erfarenhet"),
    ("Projektledning", r"projektledning|leda projekt|projektledar"),
    ("Svenska i tal och skrift", r"svenska (språket )?i tal och skrift|svenska och engelska i tal och skrift|god(a)? kunskaper i svenska|behärska(r)? svenska"),
    ("Engelska i tal och skrift", r"engelska (språket )?i tal och skrift|svenska och engelska|god(a)? kunskaper i engelska|behärska(r)? engelska"),
]
# Annonser som uttryckligen vänder sig till nyexaminerade eller juniora
NYEXAD = re.compile(r"nyexaminerad|nyutexaminerad|nyligen examinerad|ingen tidigare erfarenhet|inget krav på tidigare erfarenhet|trainee|"
                    r"i början av din karriär|tidigt i din karriär|första jobb efter|söker (vi )?(nu )?(en |två |flera )?juniora?\b|(rollen|tjänsten) som junior", re.I)


def passar_nyexad(rubrik, text):
    return bool(NYEXAD.search(text or "") or re.search(r"junior|trainee", rubrik or "", re.I))


# Mjuka formuleringar räknas som meriterande, inte som krav
MERIT = re.compile(r"meriter|fördel|önskvärt|plus|bonus|uppskattas|\bgärna\b|är bra om|är bra att|\bvälkommen\b|"
                   r"från (dina )?studier|under (dina )?studier|genom praktik|från praktik|praktik eller|examensarbete|"
                   r"ser vi (det )?som (värdefullt|positivt)", re.I)
# Rubrik för en lista med meriterande saker. Snävare än MERIT: "välkommen" eller "gärna" i en vanlig mening är ingen rubrik.
MERITRUBRIK = re.compile(r"meriter|önskvärt|ser (vi )?gärna|vi uppskattar|är ett plus|är en fördel|fördel om", re.I)
ERFARENHETSKRAV = {"Erfarenhet av beredskap/kris", "Erfarenhet av säkerhet/risk", "Flera års erfarenhet", "Tidigare erfarenhet"}
KRAV_NAMN = [n for n, _ in KRAV] + ["Tidigare erfarenhet"]


ARBETSGIVAREN = re.compile(r"\bdu får\b|du kommer att få|\berbjuder\b|möjlighet att|\bvi har\b|\bvår |\bvåra |\bvi är\b", re.I)


def krav_meningar(text):
    """Meningar som kan innehålla krav. Hoppar över meriterande meningar och listor under en rubrik som
    "Meriterande:" eller "Det är meriterande om du har" (fram till nästa tomma rad eller rubrik).
    Bara radens sista mening kan vara en rubrik: i Platsbankens text står rubriken ofta sist på en lång rad
    ("… B-körkort. Det är meriterande om du har")."""
    def meningar(s):
        return [m for m in re.split(r"[.!?•]+|\s[–-]\s", s) if m.strip() and not MERIT.search(m)]
    ut, merit_lista = [], False
    for rad in (text or "").split("\n"):
        r = rad.strip()
        if not r:
            merit_lista = False
            continue
        sista = re.split(r"(?<=[.!?])\s+", r)[-1]
        fore = r[:len(r) - len(sista)]
        ar_meritrubrik = MERITRUBRIK.search(sista) and (sista.endswith(":") or len(sista) < 60)
        if ar_meritrubrik or (sista.endswith(":") and len(sista) < 80):
            if not merit_lista:
                ut += meningar(fore)
            merit_lista = bool(ar_meritrubrik)
            continue
        if not merit_lista:
            ut += meningar(r)
    return ut


def hitta_krav(text, korkort_kravs=False, erfarenhet_kravs=False, nyexad=False):
    """Krav i annonsen, i fast ordning. Meningar som säger meriterande/önskvärt räknas inte.
    Annonser som uttryckligen vänder sig till nyexaminerade får inga erfarenhetskrav."""
    meningar = krav_meningar(text)
    hittade = {n for n, rx in KRAV if any(re.search(rx, m, re.I) for m in meningar)}
    if korkort_kravs:
        hittade.add("Körkort")
    # erfarenhet_kravs: texten ställer erfarenhetskrav (se hitta_erfarenheter) som inte passar de specifika kraven
    if erfarenhet_kravs and not hittade & {"Erfarenhet av beredskap/kris", "Erfarenhet av säkerhet/risk", "Flera års erfarenhet"}:
        hittade.add("Tidigare erfarenhet")
    if nyexad:
        hittade -= ERFARENHETSKRAV
    return [n for n in KRAV_NAMN if n in hittade]


# Vilken erfarenhet annonsen kräver, som korta fraser ur texten: "minst 3 års erfarenhet av riskhantering"
ERF_FRAS = re.compile(r"((?:(?:minst|gedigen|god|goda|dokumenterad|flerårig|relevant|tidigare|längre|några års)\s+)*"
                      r"(?:\d+\s*(?:[–-]\s*\d+\s*)?års?\s+(?:arbetslivs|yrkes|relevant\s+)?)?"
                      r"erfarenhet (?:av|från|inom|med) [^.;:!?•·\n]{3,160})", re.I)
ERF_SLUT = re.compile(r"\s(?:samt|och du|eller du|då du|vilket|som du|för att|eftersom|är ett krav|krävs|är meriterande)\b.*$", re.I)


def hitta_erfarenheter(text, nyexad=False, max_antal=4, max_tecken=110):
    """Erfarenhetskrav som korta fraser ur annonstexten. Meriterande och mjuka formuleringar räknas inte.
    Nyexaminerade: inga krav. Arbetsförmedlingens ruta "erfarenhet krävs" påverkar inte: texten avgör."""
    if nyexad:
        return []
    ut = []
    for mening in krav_meningar(text):
        if ARBETSGIVAREN.search(mening):
            continue
        for m in ERF_FRAS.finditer(mening):
            fras = re.sub(r"\s+", " ", ERF_SLUT.sub("", m.group(1))).strip(" ,")
            ar = re.match(r"(?:över )?(\d+)\s*års", fras, re.I)
            if ar and int(ar.group(1)) >= 20:  # "Studsvik har över 75 års erfarenhet" handlar om arbetsgivaren
                continue
            if len(fras) > max_tecken:
                fras = fras[:max_tecken].rsplit(" ", 1)[0].rstrip(" ,") + " …"
            fras = fras[:1].upper() + fras[1:]
            if fras.lower() not in (f.lower() for f in ut):
                ut.append(fras)
    return ut[:max_antal]


# Tjänster som en master i riskhantering inte leder till
FORSKARTJANST = re.compile(r"postdoktor|postdoc|lektor", re.I)          # kräver alltid doktorsexamen (högskoleförordningen)
FORSKARE = re.compile(r"\bforskare\b|forskningssekreterare|professor", re.I)  # utesluts om texten kräver doktorsexamen
FORSKARKRAV = re.compile(r"doktorsexamen|forskarutbildning|disputera", re.I)
DOKTORAND = re.compile(r"doktorand", re.I)
DOKTORAND_AMNE = re.compile(r"risk|säkerhet|kris|beredskap|civil[at]? försvar|totalförsvar|samhällsskydd", re.I)


def kraver_annan_utbildning(rubrik, text):
    """True om tjänsten kräver doktorsexamen, eller är en doktorandtjänst i ett ämne utanför programmet.
    "Doktorsexamen är meriterande" räknas inte som krav."""
    if FORSKARTJANST.search(rubrik):
        return True
    if FORSKARE.search(rubrik) and any(FORSKARKRAV.search(m) for m in krav_meningar(text)):
        return True
    return bool(DOKTORAND.search(rubrik)) and not DOKTORAND_AMNE.search(rubrik)


def get(base, params):
    url = base + "?" + urllib.parse.urlencode(params)
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"accept": "application/json"}), timeout=30) as r:
                return json.load(r)
        except Exception as e:
            print("försöker igen:", e, file=sys.stderr); time.sleep(2)
    return {"hits": []}

PLATSBANKEN = "https://arbetsformedlingen.se/platsbanken/annonser/"


def annonsnyckel(h):
    """Annonser med samma rubrik, arbetsgivare och kommun räknas som dubbletter."""
    emp = h.get("employer") or {}
    wa = h.get("workplace_address") or {}
    return ((h.get("headline") or "").lower().strip(), (emp.get("name") or "").lower(), (wa.get("municipality") or ""))


def bearbeta(h, src, sokterm, fran=FROM):
    """Gör om en annons från API:et till en post för sidan, eller None om den inte är relevant."""
    head = h.get("headline") or ""
    if not CORE.search(head) or EXCLUDE.search(head):
        return None
    pub = (h.get("publication_date") or "")[:10]
    if pub < fran[:10]:
        return None
    emp = h.get("employer") or {}
    wa = h.get("workplace_address") or {}
    text = (h.get("description") or {}).get("text") or ""
    if kraver_annan_utbildning(head, text):
        return None
    full = head + " " + text
    areas = [a for a, rx in AREAS if re.search(rx, head, re.I)] or \
            [a for a, rx in AREAS if re.search(rx, full, re.I)][:1]
    if not areas:
        return None
    kws = [k for k in KEYWORDS if re.search(r"\b" + re.escape(k) + r"\b", full, re.I if not k.isupper() else 0)]
    kurser = [c for c, n, rx in COURSES if re.search(rx, full, re.I)]
    score = len(kurser) + (2 if STRONG.search(head) else 0)
    if score < 3:
        return None
    if (FIN.search(head) or len(FIN.findall(text)) >= 3) and re.search(r"risk", head, re.I):
        areas = ["Finansiell & operativ risk (angränsande)"]
    match = "Hög" if score >= 7 else ("Medel" if score >= 5 else "Grundläggande")
    nyexad = passar_nyexad(head, text)
    erfarenheter = hitta_erfarenheter(text, nyexad)
    # Säkerhet: länka bara till Platsbanken, aldrig till en adress som kommer okontrollerad från datan
    url = h.get("webpage_url") or ""
    if not url.startswith(PLATSBANKEN):
        url = PLATSBANKEN + urllib.parse.quote(str(h.get("id", "")), safe="")
    return {
        "id": str(h["id"]), "rubrik": head.strip(), "arbetsgivare": emp.get("workplace") or emp.get("name") or "Okänd arbetsgivare",
        "kommun": wa.get("municipality") or wa.get("city") or "Ospecificerad", "lan": wa.get("region") or "Ospecificerat",
        "publicerad": pub, "sista": (h.get("application_deadline") or "")[:10],
        "omraden": areas, "nyckelord": kws,
        "utdrag": re.sub(r"\s+", " ", text).strip()[:200], "url": url,
        "status": "aktuell" if src == "aktuell" else "arkiverad",
        "omfattning": (h.get("working_hours_type") or {}).get("label"),
        "kurser": kurser, "match": match, "poang": score,
        "junior": nyexad,
        "erfarenheter": erfarenheter,
        # Arbetsförmedlingens ruta "erfarenhet krävs" är ikryssad men texten ställer inget erfarenhetskrav
        "erf_ruta": bool(h.get("experience_required")) and not erfarenheter and not nyexad,
        "krav": hitta_krav(text, bool(h.get("driving_license_required")), bool(erfarenheter), nyexad=nyexad),
        "text": re.sub(r"\s+", " ", text).strip()[:TEXT_MAX],
    }


def lagg_till(ads, h, rec):
    """Lägger till en post. Finns dubbletten redan och den nya är aktuell, uppdateras status och länk."""
    key = annonsnyckel(h)
    if key in ads:
        if rec["status"] == "aktuell":
            ads[key].update(status="aktuell", url=rec["url"], sista=rec["sista"])
        return
    ads[key] = rec


def hamta():
    ads = {}
    for src, base, extra in [("aktuell", "https://jobsearch.api.jobtechdev.se/search", {}),
                             ("historisk", "https://historical.api.jobtechdev.se/search", {"historical-from": FROM})]:
        for t in TERMS:
            for off in (0, 100):
                hits = get(base, {"q": t, "limit": 100, "offset": off, **extra}).get("hits", [])
                for h in hits:
                    rec = bearbeta(h, src, t)
                    if rec:
                        lagg_till(ads, h, rec)
                if len(hits) < 100:
                    break
        print(src, "klart, totalt", len(ads), "annonser", file=sys.stderr)
    out = sorted(ads.values(), key=lambda r: r["publicerad"], reverse=True)
    out.sort(key=lambda r: r["status"] != "aktuell")
    return out


# Fälten som sidan använder (texten sparas separat i annonstext.json)
KEEP = ["id", "rubrik", "arbetsgivare", "kommun", "lan", "publicerad", "sista", "omraden", "nyckelord", "utdrag",
        "url", "status", "omfattning", "kurser", "match", "poang", "krav", "junior", "erfarenheter", "erf_ruta"]


def spara(out, data_dir=DATA_DIR):
    texter = {a["id"]: a["text"].lower() for a in out}
    poster = [{k: a.get(k) for k in KEEP} for a in out]
    os.makedirs(data_dir, exist_ok=True)
    data = {"hamtad": datetime.date.today().isoformat(), "fran": FROM[:10], "kurser": [[c, n] for c, n, _ in COURSES], "annonser": poster}
    with open(os.path.join(data_dir, "annonser.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    with open(os.path.join(data_dir, "annonstext.json"), "w", encoding="utf-8") as f:
        json.dump(texter, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(data_dir, "annonser.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(KEEP)
        for a in poster:
            w.writerow([";".join(a[k]) if isinstance(a[k], list) else a[k] for k in KEEP])


def main():
    out = hamta()
    if len(out) < MIN_ANTAL:
        sys.exit(f"Bara {len(out)} annonser hämtades, troligen fel hos API:et. Behåller befintlig data.")
    spara(out)
    print("Klart:", len(out), "annonser, varav", sum(r["status"] == "aktuell" for r in out), "aktuella", file=sys.stderr)


if __name__ == "__main__":
    main()
