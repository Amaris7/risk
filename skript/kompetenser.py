"""Kompetenser som skiljer studievägarna åt: vad de obligatoriska kurserna ger, vad de valbara lägger till,
och hur ofta annonserna efterfrågar kompetensen. Används av bygg_sida.py (statistik) och illustrationer.py (diagram).

Nivåerna (0–3) är en förenklad bedömning utifrån kursbeskrivningarna på kau.se och synpunkter från en lärare
på programmet: 0 = berörs inte, 1 = berörs, 2 = grund, 3 = fördjupning."""
import re

# nyckel, namn, sökmönster i annonstext, nivå med bara obligatoriska kurser, nivå med valbar kurs, valbar kurs, viktigast för
KOMPETENSER = [
    ("rsa", "Risk- och sårbarhetsanalys (RSA)", r"risk- och sårbarhetsanalys|\brsa\b", 2, 3, "RHAD03",
     "Säkerhetssamordnare"),
    ("kontinuitet", "Kontinuitetshantering", r"kontinuitet", 1, 3, "RHAD03",
     "Beredskapssamordnare"),
    ("utredning", "Olycksutredning och incidenthantering", r"olycksutred|händelseanalys|incidentutred|haveriutred|utreda (olyckor|händelser|incidenter|tillbud)|incidenthantering|avvikelsehantering|tillbud", 1, 3, "RHAD39",
     "Säkerhets- och beredskapssamordnare"),
    ("larande", "Organisatoriskt lärande och säkerhetskultur", r"erfarenhetsåterföring|organisatoriskt lärande|säkerhetskultur|lärande organisation|utvärdera övning|utvärdering av övning|lära av", 0, 3, "RHAD39",
     "Säkerhets- och beredskapssamordnare"),
    ("implementering", "Implementering och uppföljning av åtgärder", r"implementer|åtgärdsplan|handlingsplan|uppföljning|följa upp|utvärder", 1, 3, "RHAD38",
     "Säkerhets- och beredskapssamordnare"),
    ("kommunikation", "Riskkommunikation", r"riskkommunikation|kriskommunikation|krisinformation|information till allmänheten|befolkningsinformation|kommunicera risker", 1, 3, "RHAD14",
     "Kommunikativa roller i kris och beredskap"),
    ("klimat", "Klimatanpassning", r"klimatanpass|klimatförändring", 2, 3, "RHAD03",
     "Klimatstrateger och klimatanpassningssamordnare"),
    ("hallbarhet", "Hållbarhet, säkerhet, hälsa och miljö", r"hållbar utveckling|systematiskt arbetsmiljöarbete|arbetsmiljöarbete|säkerhet, hälsa och miljö|miljö- och säkerhet", 1, 3, "MVAE34",
     "Klimat- och hållbarhetsroller, säkerhets- och miljösamordnare"),
]

VALBARA = {
    "RHAD03": ("Klimatanpassning och riskreducering", ["rsa", "kontinuitet", "klimat"],
               "Kopplar risk- och sårbarhetsanalys till klimat- och sårbarhetsanalys och ger verktyg för kontinuitetshantering. "
               "RSA är centralt för säkerhetssamordnare och kontinuitetshantering för beredskapssamordnare."),
    "RHAD39": ("Olycksutredning och organisatoriskt lärande", ["utredning", "larande"],
               "Ger verktyg för att utreda olyckor och tillbud och för att leda det organisatoriska lärandet efteråt. "
               "Viktigt för både säkerhets- och beredskapssamordnare."),
    "RHAD38": ("Implementering och utvärdering av riskhanteringsåtgärder", ["implementering"],
               "Ger verktyg för att genomföra, följa upp och utvärdera åtgärder i praktiken. "
               "Viktigt för både säkerhets- och beredskapssamordnare."),
    "RHAD14": ("Riskperception och riskkommunikation", ["kommunikation"],
               "Hur människor uppfattar risker och hur man når fram med information före och under en kris."),
    "MVAE34": ("Hållbar utveckling ur ett säkerhetsperspektiv", ["hallbarhet"],
               "Hållbarhet i säkerhetsarbetet och sambandet mellan säkerhet, hälsa och miljö."),
}

# id, namn, mönster i rubriken, mönster i texten (räcker om det förekommer minst två gånger)
ROLLGRUPPER = [
    ("alla", "Alla annonser", r"", None),
    ("sak", "Säkerhetssamordnare", r"säkerhetssamordn|säkerhetskoordinator", None),
    ("ber", "Beredskapssamordnare", r"beredskapssamordn|beredskapskoordinator|samordnare.*beredskap|beredskaps.*samordn", None),
    ("klim", "Klimatrisker och naturolyckor", r"klimat|översvämning|naturolyck|skred|skyfall|naturkatastrof|naturrisk",
     r"klimatanpass|klimatrisk|klimatförändring|översvämning|skyfall|skred|naturolyck|naturkatastrof|extremväder|höga flöden|havsnivå"),
]


def i_grupp(a, text, titel_rx, text_rx):
    if not titel_rx:
        return True
    if re.search(titel_rx, a["rubrik"], re.I):
        return True
    return bool(text_rx) and len(re.findall(text_rx, text)) >= 2


def statistik(annonser, texter):
    """Andel annonser per kompetens, totalt och för säkerhets- respektive beredskapssamordnare."""
    grupper = {}
    for g, namn, rx, trx in ROLLGRUPPER:
        urval = [a for a in annonser if i_grupp(a, texter.get(a["id"], ""), rx, trx)]
        grupper[g] = {"namn": namn, "antal": len(urval), "aktuella": sum(1 for a in urval if a.get("status") == "aktuell"), "andel": {}}
        for k, _, mrx, *_ in KOMPETENSER:
            traff = sum(1 for a in urval if re.search(mrx, texter.get(a["id"], "") + " " + a["rubrik"].lower()))
            grupper[g]["andel"][k] = round(traff / len(urval), 3) if urval else 0
            grupper[g].setdefault("traff", {})[k] = traff
    return {
        "kompetenser": [{"id": k, "namn": n, "sok": sok_ord(k), "obl": o, "val": v, "kurs": c, "viktig": vik} for k, n, _, o, v, c, vik in KOMPETENSER],
        "valbara": [{"kod": c, "namn": n, "ger": ger, "text": t} for c, (n, ger, t) in VALBARA.items()],
        "grupper": grupper,
    }


def sok_ord(k):
    """Sökord som sidans sökning använder för att visa annonserna för kompetensen."""
    return {"rsa": "risk- och sårbarhetsanalys", "kontinuitet": "kontinuitet", "utredning": "incidenthantering",
            "larande": "erfarenhetsåterföring", "implementering": "implementering", "kommunikation": "kriskommunikation",
            "klimat": "klimatanpassning", "hallbarhet": "arbetsmiljöarbete"}[k]
