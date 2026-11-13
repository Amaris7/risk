"""Kompetenser som skiljer studievägarna åt: vad de obligatoriska kurserna ger, vad de valbara lägger till,
och hur ofta annonserna efterfrågar kompetensen. Används av bygg_sida.py (statistik) och illustrationer.py (diagram).

Nivåerna (0–3) är en förenklad bedömning utifrån kursbeskrivningarna på kau.se och synpunkter från en lärare
på programmet: 0 = berörs inte, 1 = berörs, 2 = grund, 3 = fördjupning."""
import re

from statistik import procent, procent_dec

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

# Klimat delas i två grupper:
#  "risk": klimatrisker och naturolyckor (klimatanpassning, översvämning, skred, skyfall …), det programmet utbildar för
#  "omst": klimatomställning, det vill säga att minska utsläpp och energianvändning (klimat- och energistrateger m.fl.)
# Mönstren matchar i början av ord (\b) så att t.ex. "skred" inte träffar i "riskreducerande".
KLIMATRISK_TITEL = r"\b(?:klimatanpass|klimatrisk|klimatförändr|klimathändelse|klimateffekt|översvämning|naturolyck|skred|skyfall|" \
                   r"naturkatastrof|naturrisk|extremväder|dagvatten|klimatsäkr)"
KLIMATRISK_TEXT = r"\b(?:klimatanpass|klimatrisk|klimatförändring|klimatsäkr|översvämning|skyfall|skred|naturolyck|naturkatastrof|" \
                  r"extremväder|höga flöden|havsnivå|ras och skred|värmebölj)"
# Samma utan "klimatförändring": den nämns också i annonser om att minska utsläpp ("minska klimatförändringarna")
KLIMATRISK_TEXT_SNAV = r"\b(?:klimatanpass|klimatrisk|klimatsäkr|översvämning|skyfall|skred|naturolyck|naturkatastrof|" \
                       r"extremväder|höga flöden|havsnivå|värmebölj)"
# Rubriker om klimat i allmänhet, energi eller utsläpp (t.ex. "Klimat- och energistrateg").
# "Kallt klimat", "arbetsklimat" och "inomhusklimat" handlar inte om klimatarbete.
KLIMAT_TITEL = r"(?<!kallt )(?<!arbets)(?<!inomhus)klimat|energistrateg|energisamordn|energiutveckl|energiexpert|utsläpp|fossilfri|koldioxid"
OMSTALLNING_NAMN = "Klimatomställning, energi och utsläpp"


def klimattyp(a, text):
    """"risk", "omst" eller "".
    risk: rubriken nämner klimatrisker/naturolyckor, eller texten nämner klimatrisker minst två gånger.
          Har rubriken bara ordet klimat (eller energi/utsläpp) räknas inte "klimatförändring" i texten,
          eftersom den också står i annonser om att minska utsläpp.
    omst: rubriken nämner klimat, energi eller utsläpp men annonsen handlar inte om klimatrisker."""
    rubrik = a["rubrik"]
    if re.search(KLIMATRISK_TITEL, rubrik, re.I):
        return "risk"
    klimat_i_rubrik = bool(re.search(KLIMAT_TITEL, rubrik, re.I))
    if len(re.findall(KLIMATRISK_TEXT_SNAV if klimat_i_rubrik else KLIMATRISK_TEXT, text, re.I)) >= 2:
        return "risk"
    return "omst" if klimat_i_rubrik else ""


# id, namn, mönster i rubriken. Klimatgruppen avgörs av klimattyp() ovan.
ROLLGRUPPER = [
    ("alla", "Alla annonser", r""),
    ("sak", "Säkerhetssamordnare", r"säkerhetssamordn|säkerhetskoordinator"),
    ("ber", "Beredskapssamordnare", r"beredskapssamordn|beredskapskoordinator|samordnare.*beredskap|beredskaps.*samordn"),
    ("klim", "Klimatrisker och naturolyckor", None),
]


def i_grupp(a, text, gid, titel_rx):
    if gid == "klim":
        return klimattyp(a, text) == "risk"
    return not titel_rx or bool(re.search(titel_rx, a["rubrik"], re.I))


def statistik(annonser, texter):
    """Andel annonser per kompetens, totalt och för säkerhets- respektive beredskapssamordnare."""
    grupper = {}
    for g, namn, rx in ROLLGRUPPER:
        urval = [a for a in annonser if i_grupp(a, texter.get(a["id"], ""), g, rx)]
        grupper[g] = {"namn": namn, "antal": len(urval), "aktuella": sum(1 for a in urval if a.get("status") == "aktuell"), "andel": {}}
        for k, _, mrx, *_ in KOMPETENSER:
            traff = sum(1 for a in urval if re.search(mrx, texter.get(a["id"], "") + " " + a["rubrik"].lower()))
            grupper[g]["andel"][k] = round(traff / len(urval), 3) if urval else 0
            grupper[g].setdefault("traff", {})[k] = traff
            grupper[g].setdefault("procent", {})[k] = procent(traff, len(urval))
            grupper[g].setdefault("procent_av_alla", {})[k] = procent_dec(traff, len(annonser))
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
