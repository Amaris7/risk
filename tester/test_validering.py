"""Validering och säkerhetskontroll av det som faktiskt publiceras:
data/annonser.json, data/annonstext.json, data/kurskalender.ics, skript/mall.html och index.html.
Körs efter bygget. Faller något här ska sidan inte publiceras."""
import datetime
import json
import os
import re
import unittest

import hjalp
import bygg_sida as B
import hamta_annonser as H

ROT = hjalp.ROT
DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TID = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?$")
PLATSBANKEN_URL = re.compile(r"^https://arbetsformedlingen\.se/platsbanken/annonser/[\w-]+$")
OMRADEN = {a for a, _ in H.AREAS} | {"Finansiell & operativ risk (angränsande)"}
KURSKODER = {c for c, _, _ in H.COURSES}
PROGRAMKURSER = {"RHAD01", "RHAD02", "RHAD03", "RHAD12", "RHAD14", "RHAD21", "RHAD22", "RHAD31", "RHAD35", "RHAD38", "RHAD39", "RHAE01", "MVAE34"}


def las(*delar):
    with open(os.path.join(ROT, *delar), encoding="utf-8") as f:
        return f.read()


class Annonsdata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(las("data", "annonser.json"))
        cls.ads = cls.data["annonser"]

    def test_toppniva(self):
        self.assertRegex(self.data["hamtad"], DATUM)
        self.assertRegex(self.data["fran"], DATUM)
        self.assertLess(self.data["fran"], self.data["hamtad"])
        self.assertGreaterEqual(len(self.ads), H.MIN_ANTAL, "för få annonser, troligen fel vid hämtningen")

    def test_data_inte_for_gammal(self):
        alder = (datetime.date.today() - datetime.date.fromisoformat(self.data["hamtad"])).days
        self.assertLessEqual(alder, 21, f"annonsdatan är {alder} dagar gammal, har veckouppdateringen slutat fungera?")

    def test_varje_annons_har_ratt_falt_och_typer(self):
        for a in self.ads:
            with self.subTest(id=a.get("id")):
                self.assertEqual(sorted(a), sorted(H.KEEP))
                for k in ("id", "rubrik", "arbetsgivare", "kommun", "lan", "url"):
                    self.assertIsInstance(a[k], str)
                    self.assertTrue(a[k].strip(), k)
                self.assertRegex(a["publicerad"], DATUM)
                self.assertTrue(a["sista"] == "" or DATUM.match(a["sista"]))
                self.assertIn(a["status"], ("aktuell", "arkiverad"))
                self.assertIn(a["match"], ("Hög", "Medel", "Grundläggande"))
                self.assertIsInstance(a["poang"], int)
                self.assertTrue(a["omraden"] and set(a["omraden"]) <= OMRADEN, a["omraden"])
                self.assertTrue(set(a["kurser"]) <= KURSKODER, a["kurser"])
                self.assertLessEqual(len(a["utdrag"]), 200)
                self.assertIsInstance(a["krav"], list)
                self.assertTrue(set(a["krav"]) <= set(H.KRAV_NAMN), a["krav"])

    def test_publiceringsdatum_inom_perioden(self):
        idag = datetime.date.today().isoformat()
        for a in self.ads:
            self.assertTrue(self.data["fran"] <= a["publicerad"] <= idag, (a["id"], a["publicerad"]))

    def test_unika_id(self):
        ids = [a["id"] for a in self.ads]
        self.assertEqual(len(ids), len(set(ids)))

    def test_lankar_gar_bara_till_platsbanken(self):
        for a in self.ads:
            self.assertRegex(a["url"], PLATSBANKEN_URL)

    def test_annonstexter_finns_for_alla(self):
        texter = json.loads(las("data", "annonstext.json"))
        saknas = [a["id"] for a in self.ads if a["id"] not in texter]
        self.assertEqual(saknas, [], "annonser utan text i annonstext.json")
        for t in texter.values():
            self.assertEqual(t, t.lower())
            self.assertLessEqual(len(t), H.TEXT_MAX)


class Kalenderdata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sokvag = os.path.join(ROT, "data", "kurskalender.ics")
        if not os.path.exists(sokvag):
            raise unittest.SkipTest("ingen kurskalender")
        cls.ev = B.las_ics(sokvag)["handelser"]

    def test_har_handelser(self):
        self.assertGreater(len(self.ev), 0)

    def test_varje_handelse_ar_giltig(self):
        for e in self.ev:
            with self.subTest(titel=e["titel"], start=e["start"]):
                self.assertIn(e["kod"], PROGRAMKURSER, "okänd eller saknad kurskod, händelsen hamnar som Övrigt")
                self.assertTrue(e["titel"].strip())
                self.assertRegex(e["start"], TID)
                self.assertTrue(e["slut"] == "" or TID.match(e["slut"]))
                if e["slut"] and not e["heldag"]:
                    self.assertLessEqual(e["start"], e["slut"], "sluttid före starttid")
                if not e["heldag"]:
                    timme = int(e["start"][11:13])
                    self.assertTrue(6 <= timme <= 23, "orimlig tid, fel tidszon?")


class Sakerhet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = las("index.html")
        cls.mall = las("skript", "mall.html")

    def test_inga_hemliga_lankar_eller_nycklar(self):
        for monster, vad in [(r"zoom\.us/", "Zoom-länk"), (r"instructure\.com/feeds", "Canvas-kalenderflöde"),
                             (r"ghp_[A-Za-z0-9]{20,}", "GitHub-token"), (r"user_[A-Za-z0-9]{30,}", "Canvas-flödesnyckel"),
                             (r"X-WR-CALNAME", "kalendernamn")]:
            with self.subTest(vad):
                self.assertIsNone(re.search(monster, self.html), f"{vad} får inte finnas på den publika sidan")

    def test_csp_och_referrer(self):
        self.assertIn('http-equiv="Content-Security-Policy"', self.html)
        self.assertIn("object-src 'none'", self.html)
        self.assertIn("base-uri 'none'", self.html)
        self.assertIn('name="referrer"', self.html)

    def test_inga_externa_skript_eller_iframes(self):
        self.assertIsNone(re.search(r"<script[^>]+src=", self.html, re.I))
        self.assertIsNone(re.search(r"<iframe|<object|<embed", self.html, re.I))

    def test_inga_platshallare_kvar(self):
        self.assertNotIn("__DATA__", self.html)
        self.assertNotIn("__LOGIK__", self.html)
        self.assertNotIn("module.exports", self.html)
        self.assertNotIn("<!--GRAFIK:", self.html)
        self.assertEqual(self.html.count('class="banner-art"'), 6, "varje flik ska ha sin illustration")
        self.assertEqual(self.html.count('class="hero-art"'), 1)

    def test_inbaddad_data_kan_inte_bryta_ut(self):
        # Två skript: det lilla temaskriptet först och sidans skript med datan
        skript = re.findall(r"<script>(.*?)</script>", self.html, re.S)
        self.assertEqual(len(skript), 2, "datan har avslutat <script>-taggen i förtid")
        self.assertIn("const DATA", skript[1])
        self.assertNotIn("<!--", skript[1])

    def test_nya_flikar_har_noopener(self):
        for tag in re.findall(r"<a\b[^>]*target=\"_blank\"[^>]*>", self.mall):
            self.assertIn("noopener", tag, tag)

    @staticmethod
    def uttryck(kod):
        """Alla ${...}-uttryck i mallen, även nästlade, med balanserade klamrar."""
        ut = []
        for m in re.finditer(r"\$\{", kod):
            djup, k = 1, m.end()
            while djup and k < len(kod):
                djup += {"{": 1, "}": -1}.get(kod[k], 0)
                k += 1
            ut.append(kod[m.end():k - 1])
        return ut

    def test_data_escapas_i_mallen(self):
        """Varje ${...} i mallen som tar ett fält från annonser eller kalendern måste gå genom esc()
        (eller en funktion som escapar själv). Uttryck som bara innehåller en mall (`...`) kontrolleras via sina delar."""
        falt = re.compile(r"\.(rubrik|arbetsgivare|kommun|lan|utdrag|titel|plats|info|url|kurs|roll|omfattning|omraden|krav)\b")
        sakra = re.compile(r"^\s*(esc|sakerAnnonsUrl|fmt|klock|sv|list|cname)\(")
        farliga = [u for u in self.uttryck(self.mall)
                   if "`" not in u and falt.search(u) and not sakra.match(u) and "esc(" not in u]
        self.assertEqual(farliga, [], "oescapade data i HTML-mallen")

    def test_escape_kontrollen_hittar_fel(self):
        """Kontrollen ovan måste slå larm på ett oescapat fält."""
        u = self.uttryck("x `<b>${a.rubrik}</b><i>${esc(a.titel)}</i>` y")
        self.assertEqual(u, ["a.rubrik", "esc(a.titel)"])

if __name__ == "__main__":
    unittest.main()
