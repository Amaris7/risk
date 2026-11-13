"""All statistik som sidan visar: antal, andelar och topplistor. Räknas här i Python vid bygget, så att varje siffra
går att granska och testa. Sidans JavaScript visar bara de färdiga siffrorna (utom det som beror på vad besökaren
själv skriver eller väljer, som sökordsräknaren och filtren).

Kör fristående för att se rapporten:  python3 skript/statistik.py
Resultatet sparas också vid varje bygge i data/statistik.json och data/statistik.md."""
import json
import math
import os
import re
from collections import Counter

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Yrkesroller: den första rollen vars mönster matchar rubriken gäller. Ordningen spelar alltså roll.
# Rubriker som nämner både säkerhets- och beredskapssamordnare får en egen grupp först, så att de rena rollerna hålls isär.
SAK_RX = r"säkerhetssamordn|säkerhetskoordinator"
BER_RX = r"beredskapssamordn|beredskapskoordinator|samordnare.*beredskap|beredskaps.*samordn"
ROLLER = [
    ("Säkerhets- och beredskapssamordnare", rf"^(?=.*(?:{SAK_RX}))(?=.*(?:{BER_RX}))",
     "Kombinerade roller där säkerhetsarbete och krisberedskap ligger på samma person, vanligt i mindre kommuner, bolag och förvaltningar."),
    ("Beredskapssamordnare", BER_RX,
     "Samordnar kommunens, regionens eller myndighetens krisberedskap och civila försvar: RSA, beredskapsplaner, krisledningsorganisation, övningar och utbildning."),
    ("Beredskapshandläggare & -planerare", r"beredskapshandl|beredskapsplaner|handläggare.*beredskap|beredskapsspecialist|beredskapsexpert|beredskapsstrateg|beredskapsansvarig|beredskapschef",
     "Handlägger och utvecklar beredskapsplanering på länsstyrelser, civilområden och statliga myndigheter, ofta med fokus på höjd beredskap."),
    ("Civilt försvar & totalförsvar", r"civil[at]? försvar|totalförsvar|civilområde|försörjningsberedskap",
     "Roller som bygger upp det civila försvaret: planering för höjd beredskap, krigsorganisation, försörjningsberedskap och samverkan med Försvarsmakten."),
    ("Säkerhetssamordnare", SAK_RX,
     "Samordnar en organisations säkerhetsarbete: riskbedömningar, incidenthantering, säkerhetsrutiner och ofta även krisberedskap."),
    ("Säkerhetsstrateg & säkerhetschef", r"säkerhetsstrateg|säkerhetschef|säkerhetsspecialist|säkerhetsansvarig|chef.*säkerhet",
     "Strategiskt ansvar för säkerhet, beredskap och kontinuitet. Ofta krav på erfarenhet och ledningsförmåga."),
    ("Säkerhetsskydd", r"säkerhetsskydd",
     "Säkerhetsskyddschefer och handläggare som skyddar säkerhetskänslig verksamhet. Kräver oftast kompletterande kunskap om säkerhetsskyddslagen."),
    ("Trygghet & brottsförebyggande", r"trygghet|brottsförebygg",
     "Arbetar lokalt med trygghetsskapande och brottsförebyggande åtgärder, ofta i kommuner och bostadsbolag."),
    ("Kontinuitetshantering", r"kontinuitet",
     "Ser till att verksamheten fungerar vid störningar: kontinuitetsplaner, beroendeanalyser och övningar."),
    ("Riskanalytiker & riskkonsult", r"riskanaly|riskkonsult|risk ?manager|riskhanter|riskingenjör|riskspecialist|riskstrateg",
     "Analyserar och bedömer risker, på myndighet, i industri eller som konsult. Inkluderar även finansiella riskroller, som är mer angränsande."),
    ("Klimatanpassning", r"klimat",
     "Strateger och projektledare som arbetar med klimatanpassning, översvämnings- och skredrisker i fysisk planering."),
    ("Klimatomställning & energi", r"energistrateg|energisamordn|energiutveckl|energiexpert|utsläpp|fossilfri|koldioxid",
     "Klimat-, miljö- och energistrateger som arbetar med att minska utsläpp och energianvändning. Angränsande till programmet: klimatfrågan är gemensam, men fokus är omställning snarare än risk."),
    ("Skadeförebyggande & räddningstjänst", r"skadeförebygg|olycksförebygg|förebyggande|trafiksäkerhet|räddning|brandskydd|säkerhetsfrämj|olycksutred",
     "Förebyggande arbete mot olyckor och skador: trafiksäkerhet, räddningstjänstens förebyggande verksamhet och olycksutredning."),
    ("Krisledning & krisstöd", r"kris",
     "Krishantering, krisledning och krisstöd, ofta i regioner, myndigheter och företag."),
    ("Analytiker & utredare", r"analytiker|utredare|handläggare|strateg|samordnare|specialist|expert|projektledare",
     "Andra analytiker-, utredar- och samordnarroller med koppling till risk, beredskap eller säkerhet."),
]
KLIMATROLLER = ("Klimatanpassning", "Klimatomställning & energi")
OVRIGT = ("Övrigt", "", "Annonser som inte passade in i någon av grupperna ovan.")


def procent(del_, hel):
    """Heltalsprocent, avrundad uppåt vid .5 (som Math.round i webbläsaren). 0 om helheten är 0."""
    return math.floor(del_ / hel * 100 + 0.5) if hel else 0


def procent_dec(del_, hel):
    """Procent med en decimal för små andelar (under 10 %), annars heltal."""
    if not hel:
        return 0
    p = del_ / hel * 100
    return math.floor(p * 10 + 0.5) / 10 if p < 10 else math.floor(p + 0.5)


ERF_OSPEC = "Tidigare erfarenhet krävs (anges inte vilken)"


def kraver_erfarenhet(a):
    """Samma regel som filtret på sidan (kraverErfarenhet i logik.js): annonsen har minst ett erfarenhetskrav."""
    return bool(a.get("erfarenheter"))


def roll(rubrik):
    for namn, rx, _ in ROLLER:
        if re.search(rx, rubrik or "", re.I):
            return namn
    return OVRIGT[0]


def kort_titel(rubrik):
    """Kort yrkestitel ur en rubrik: "Säkerhetssamordnare till Heby kommun" blir "Säkerhetssamordnare"."""
    t = re.sub(r"[!.:]+$", "", (rubrik or "").strip())
    t = re.sub(r"\s+[–—|]\s.*$", "", t)
    t = re.sub(r"\s+-\s.*$", "", t)
    t = re.sub(r",\s.*$", "", t)
    t = re.sub(r"\s+(till|sökes|söks|på|vid|hos)(\s.*)?$", "", t, flags=re.I)
    t = re.sub(r"\s+i\s+[A-ZÅÄÖ].*$", "", t)
    t = t.strip()
    return t[:1].upper() + t[1:]


def rakna(poster, f):
    """Som sidans count(): räknar värden (eller listor av värden), flest först, vid lika i första förekomstens ordning."""
    c = Counter()
    for p in poster:
        v = f(p)
        for k in (v if isinstance(v, list) else [v]):
            if k:
                c[k] += 1
    return [[k, n] for k, n in c.most_common()]


def med_andel(rader, hel):
    return [[k, n, procent(n, hel)] for k, n in rader]


# Samma sökning som sidans sökord: varje ord måste stå i början av ett ord i texten (OCH mellan orden).
def sok_matcher(q):
    ord_ = [w for w in (q or "").lower().split() if w]
    res = [re.compile(r"(?:^|[\W_])" + re.escape(w)) for w in ord_]  # som [^\p{L}\p{N}] i webbläsaren
    return lambda text: all(r.search(text) for r in res)


def sokbar_text(a, texter):
    s = " ".join([a["rubrik"], a["arbetsgivare"], a["kommun"], a["lan"], a.get("utdrag", "")]).lower()
    return s + (" " + texter[a["id"]] if a["id"] in texter else "")


def berakna(annonser, kurskoder, texter=None):
    """All statistik för sidan. Lägger också till fälten "roll" och "klimat" på varje annons.
    "klimat" är "risk" (klimatrisker och naturolyckor), "omst" (klimatomställning, energi och utsläpp) eller "",
    se kompetenser.klimattyp(). Det kräver annonstexterna."""
    import kompetenser  # här, eftersom kompetenser importerar statistik
    texter = texter or {}
    for a in annonser:
        a["klimat"] = kompetenser.klimattyp(a, texter.get(a["id"], ""))
        a["roll"] = roll(a["rubrik"])
        # Klimatrubrikerna fördelas på anpassning eller omställning efter vad annonsen faktiskt handlar om
        if a["roll"] in KLIMATROLLER and a["klimat"]:
            a["roll"] = KLIMATROLLER[a["klimat"] == "omst"]
    n = len(annonser)
    kurs = lambda a: [k for k in a["kurser"] if k in kurskoder]

    def med_typ(urval, typ):
        """[antal, procent av urvalet] för annonser med klimattypen."""
        k = sum(a["klimat"] == typ for a in urval)
        return [k, procent(k, len(urval))]

    roller = []
    for namn, _, beskr in ROLLER + [OVRIGT]:
        urval = [a for a in annonser if a["roll"] == namn]
        if not urval:
            continue
        roller.append({
            "namn": namn, "beskrivning": beskr, "antal": len(urval),
            "aktuella": sum(a["status"] == "aktuell" for a in urval),
            "klimat": med_typ(urval, "risk"),
            "omst": med_typ(urval, "omst"),
            "titlar": [k for k, _ in rakna(urval, lambda a: kort_titel(a["rubrik"]))[:4]],
            "arbetsgivare": [k for k, _ in rakna(urval, lambda a: a["arbetsgivare"])[:3]],
            "kurser": [k for k, _ in rakna(urval, kurs)[:3]],
            "krav": med_andel(rakna(urval, lambda a: a["krav"])[:4], len(urval)),
        })

    alfabetiskt = lambda rader: sorted(rader, key=lambda r: r[0].lower())
    return {
        "antal": n,
        "fakta": {
            "annonser": n,
            "aktuella": sum(a["status"] == "aktuell" for a in annonser),
            "hog_matchning": sum(a["match"] == "Hög" for a in annonser),
            "orter": len({a["kommun"] for a in annonser}),
            "arbetsgivare": len({a["arbetsgivare"] for a in annonser}),
            "nyexaminerade": sum(bool(a.get("junior")) for a in annonser),
            "klimat": sum(a["klimat"] == "risk" for a in annonser),
            "klimat_procent": procent(sum(a["klimat"] == "risk" for a in annonser), n),
            "klimat_omst": sum(a["klimat"] == "omst" for a in annonser),
            "klimat_omst_procent": procent(sum(a["klimat"] == "omst" for a in annonser), n),
            "kraver_erfarenhet": sum(kraver_erfarenhet(a) for a in annonser),
            "kraver_inte_erfarenhet": sum(not kraver_erfarenhet(a) for a in annonser),
            "erfarenhet_ospecificerad": sum(a.get("erfarenheter", [""])[:1] == [ERF_OSPEC] for a in annonser),
        },
        "roller": roller,
        "omraden": rakna(annonser, lambda a: a["omraden"]),
        "nyckelord": rakna(annonser, lambda a: a["nyckelord"])[:12],
        "kurser": rakna(annonser, kurs),
        "arbetsgivare": rakna(annonser, lambda a: a["arbetsgivare"])[:12],
        "lan": rakna(annonser, lambda a: a["lan"]),
        "krav": med_andel(rakna(annonser, lambda a: a["krav"]), n),
        "filter": {
            "kommuner": {lan: alfabetiskt(rakna([a for a in annonser if not lan or a["lan"] == lan], lambda a: a["kommun"]))
                         for lan in [""] + sorted({a["lan"] for a in annonser})},
            "lan": alfabetiskt(rakna(annonser, lambda a: a["lan"])),
            "omraden": rakna(annonser, lambda a: a["omraden"]),
            "roller": rakna(annonser, lambda a: a["roll"]),
        },
    }


def rapport(stat, kompetens=None):
    """Granskningsbar sammanställning i Markdown: varje siffra med täljare och nämnare."""
    r = ["# Statistik för sidan", "", f"Totalt **{stat['antal']}** annonser. Andel = antal / totalt, avrundat till heltal (0,5 uppåt).", ""]
    f = stat["fakta"]
    namn = {"annonser": "Annonser", "aktuella": "Aktuella just nu", "hog_matchning": "Hög matchning", "orter": "Orter",
            "arbetsgivare": "Arbetsgivare", "nyexaminerade": "Passar nyexaminerade", "kraver_erfarenhet": "Kräver erfarenhet",
            "kraver_inte_erfarenhet": "Kräver inte erfarenhet", "erfarenhet_ospecificerad": "Kräver erfarenhet, men anger inte vilken",
            "klimat": "Handlar om klimatrisker och naturolyckor",
            "klimat_procent": "Andel klimatriskannonser (%)",
            "klimat_omst": "Handlar om klimatomställning, energi och utsläpp",
            "klimat_omst_procent": "Andel omställningsannonser (%)"}
    r += ["## Nyckeltal", "", "| Mått | Antal |", "|---|---|"] + [f"| {namn.get(k, k)} | {v} |" for k, v in f.items()] + [""]
    def tabell(rubrik, rader, hel=None):
        out = [f"## {rubrik}", "", "| | Antal | Andel |", "|---|---|---|"]
        for rad in rader:
            k, nn = rad[0], rad[1]
            out.append(f"| {k} | {nn} | {procent(nn, hel or stat['antal'])} % |")
        return out + [""]
    r += tabell("Arbetsområden (en annons kan ha flera)", stat["omraden"])
    r += tabell("Krav", stat["krav"])
    r += tabell("Kurser som annonserna anknyter till", stat["kurser"])
    r += tabell("Begrepp i annonstexten (topp 12)", stat["nyckelord"])
    r += tabell("Län", stat["lan"])
    r += ["## Yrkesroller", "", "| Roll | Antal | Aktuella | Klimatrisker (antal av rollens annonser, andel) | Klimatomställning | Vanligaste krav (antal av rollens annonser, andel) |", "|---|---|---|---|---|---|"]
    for ro in stat["roller"]:
        krav = "; ".join(f"{k} {nn}/{ro['antal']} = {p} %" for k, nn, p in ro["krav"])
        r.append(f"| {ro['namn']} | {ro['antal']} | {ro['aktuella']} | {ro['klimat'][0]}/{ro['antal']} = {ro['klimat'][1]} % | {ro['omst'][0]}/{ro['antal']} = {ro['omst'][1]} % | {krav} |")
    r.append("")
    if kompetens:
        r += ["## Kompetenser per grupp (Valbara kurser)", ""]
        for g in kompetens["grupper"].values():
            r += [f"### {g['namn']} ({g['antal']} annonser)", "", "| Kompetens | Antal | Andel i gruppen | Andel av alla annonser |", "|---|---|---|---|"]
            for k in kompetens["kompetenser"]:
                t = g["traff"][k["id"]]
                r.append(f"| {k['namn']} | {t} av {g['antal']} | {g['procent'][k['id']]} % | {g['procent_av_alla'][k['id']]} % |")
            r.append("")
    return "\n".join(r)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import hamta_annonser as H
    import kompetenser as K
    with open(os.path.join(ROT, "data", "annonser.json"), encoding="utf-8") as fh:
        ads = json.load(fh)["annonser"]
    with open(os.path.join(ROT, "data", "annonstext.json"), encoding="utf-8") as fh:
        tx = json.load(fh)
    print(rapport(berakna(ads, {c for c, _, _ in H.COURSES}, tx), K.statistik(ads, tx)))
