"""Tester för statistiken (skript/statistik.py): avrundning, rollindelning, titlar, topplistor och att varje siffra
som sidan visar går att räkna fram igen från annonsdatan. Testar också att sökordsräknaren i webbläsaren (JavaScript)
ger exakt samma antal träffar som Python-versionen."""
import json
import os
import shutil
import subprocess
import unittest

import hjalp
import hamta_annonser as H
import kompetenser as K
import statistik as S

ROT = hjalp.ROT


def ladda():
    with open(os.path.join(ROT, "data", "annonser.json"), encoding="utf-8") as f:
        ads = json.load(f)["annonser"]
    with open(os.path.join(ROT, "data", "annonstext.json"), encoding="utf-8") as f:
        tx = json.load(f)
    return ads, tx


class Avrundning(unittest.TestCase):
    def test_halvor_avrundas_uppat(self):
        self.assertEqual(S.procent(1, 8), 13)     # 12,5 -> 13 (inte bankavrundning till 12)
        self.assertEqual(S.procent(5, 200), 3)    # 2,5 -> 3
        self.assertEqual(S.procent(1, 3), 33)
        self.assertEqual(S.procent(2, 3), 67)
        self.assertEqual(S.procent(0, 0), 0)

    def test_en_decimal_under_tio_procent(self):
        self.assertEqual(S.procent_dec(14, 1237), 1.1)
        self.assertEqual(S.procent_dec(25, 1237), 2.0)
        self.assertEqual(S.procent_dec(200, 1000), 20)


class Roller(unittest.TestCase):
    def test_forsta_matchande_roll_galler(self):
        self.assertEqual(S.roll("Beredskapssamordnare till Heby"), "Beredskapssamordnare")
        self.assertEqual(S.roll("Säkerhetssamordnare"), "Säkerhetssamordnare")
        # Rubriker som nämner båda rollerna får en egen grupp
        for rubrik in ("Säkerhetssamordnare med inriktning krisberedskap", "Beredskaps- och säkerhetssamordnare",
                       "Säkerhetssamordnare / Beredskapssamordnare"):
            with self.subTest(rubrik=rubrik):
                self.assertEqual(S.roll(rubrik), "Säkerhets- och beredskapssamordnare")
        self.assertEqual(S.roll("Beredskapssamordnare till Heby"), "Beredskapssamordnare")
        self.assertEqual(S.roll("Handläggare inom krisberedskap"), "Beredskapshandläggare & -planerare")
        self.assertEqual(S.roll("Krisstöd till regionen"), "Krisledning & krisstöd")
        self.assertEqual(S.roll("Kock"), "Övrigt")

    def test_korta_titlar(self):
        fall = {"Säkerhets- och beredskapshandläggare": "Säkerhets- och beredskapshandläggare",
                "Beredskapssamordnare till Heby kommun": "Beredskapssamordnare",
                "Säkerhetssamordnare i Botkyrka": "Säkerhetssamordnare",
                "Handläggare inom krisberedskap": "Handläggare inom krisberedskap",
                "Säkerhetsstrateg – Helsingborgs stad": "Säkerhetsstrateg",
                "Riskanalytiker, Göteborg": "Riskanalytiker",
                "Beredskapssamordnare sökes!": "Beredskapssamordnare",
                "Samordnare - beredskap inom kommunal hälso- och sjukvård": "Samordnare",
                "risk manager": "Risk manager"}
        for rubrik, vantat in fall.items():
            with self.subTest(rubrik=rubrik):
                self.assertEqual(S.kort_titel(rubrik), vantat)

    def test_rakna_flest_forst_och_stabil_vid_lika(self):
        poster = [{"k": ["b", "a"]}, {"k": ["a"]}, {"k": ["c"]}, {"k": ["b"]}]
        self.assertEqual(S.rakna(poster, lambda p: p["k"]), [["b", 2], ["a", 2], ["c", 1]])


class Sokning(unittest.TestCase):
    def test_ordborjan_och_alla_ord(self):
        m = S.sok_matcher("gis")
        self.assertTrue(m("kunskap i gis"))
        self.assertFalse(m("logistik"))
        self.assertTrue(S.sok_matcher("krisled")("du leder krisledningen"))
        self.assertTrue(S.sok_matcher("räddningstjänst körkort")("räddningstjänst, b-körkort"))
        self.assertFalse(S.sok_matcher("räddningstjänst körkort")("räddningstjänsten"))
        self.assertTrue(S.sok_matcher("c++")("kunskap i c++"))
        self.assertTrue(S.sok_matcher("")("vad som helst"))


class RiktigaSiffror(unittest.TestCase):
    """Räknar om varje siffra på sidan från grunden och jämför med statistiken."""

    @classmethod
    def setUpClass(cls):
        cls.ads, cls.tx = ladda()
        cls.st = S.berakna(cls.ads, {c for c, _, _ in H.COURSES}, cls.tx)
        cls.n = len(cls.ads)

    def test_nyckeltal(self):
        f = self.st["fakta"]
        self.assertEqual(f["annonser"], self.n)
        self.assertEqual(f["aktuella"], len([a for a in self.ads if a["status"] == "aktuell"]))
        self.assertEqual(f["hog_matchning"], len([a for a in self.ads if a["match"] == "Hög"]))
        self.assertEqual(f["orter"], len(set(a["kommun"] for a in self.ads)))
        self.assertEqual(f["arbetsgivare"], len(set(a["arbetsgivare"] for a in self.ads)))

    def test_erfarenhet_delar_upp_alla_annonser(self):
        f = self.st["fakta"]
        self.assertEqual(f["kraver_erfarenhet"] + f["kraver_inte_erfarenhet"], self.n)
        self.assertEqual(f["kraver_erfarenhet"], len([a for a in self.ads if a["erfarenheter"]]))
        self.assertTrue(all(not a["erfarenheter"] for a in self.ads if a["junior"]), "nyexaminerade har inga erfarenhetskrav")
        self.assertEqual(S.ERF_OSPEC, H.ERF_OSPEC)

    def test_klimatannonser_per_roll(self):
        """Klimatfiltret och rollkortens klimatrad använder samma urval som gruppen på fliken Valbara kurser."""
        k = K.statistik(self.ads, self.tx)
        f = self.st["fakta"]
        typ = {a["id"]: K.klimattyp(a, self.tx.get(a["id"], "")) for a in self.ads}
        self.assertEqual(f["klimat"], k["grupper"]["klim"]["antal"])
        self.assertEqual(f["klimat"], list(typ.values()).count("risk"))
        self.assertEqual(f["klimat_omst"], list(typ.values()).count("omst"))
        self.assertEqual(f["klimat_procent"], S.procent(f["klimat"], self.n))
        self.assertEqual(f["klimat_omst_procent"], S.procent(f["klimat_omst"], self.n))
        self.assertEqual(sum(r["klimat"][0] for r in self.st["roller"]), f["klimat"])
        self.assertEqual(sum(r["omst"][0] for r in self.st["roller"]), f["klimat_omst"])
        for r in self.st["roller"]:
            with self.subTest(roll=r["namn"]):
                for nyckel, t in (("klimat", "risk"), ("omst", "omst")):
                    n = len([a for a in self.ads if a["roll"] == r["namn"] and typ[a["id"]] == t])
                    self.assertEqual(r[nyckel], [n, S.procent(n, r["antal"])])
        # Klimatrollerna följer vad annonsen handlar om
        for a in self.ads:
            if a["roll"] == "Klimatomställning & energi":
                self.assertNotEqual(typ[a["id"]], "risk", a["rubrik"])

    def test_klimatregeln(self):
        t = lambda rubrik, text="": K.klimattyp({"rubrik": rubrik}, text)
        self.assertEqual(t("Klimatanpassningsstrateg"), "risk")
        self.assertEqual(t("Projektledare inom ras- och skredförebyggande arbete"), "risk")
        self.assertEqual(t("Beredskapssamordnare", "arbetet rör översvämning."), "", "en enstaka träff räcker inte")
        self.assertEqual(t("Beredskapssamordnare", "översvämning och skyfall"), "risk")
        # "skred" ska inte träffa i "riskreducerande"
        self.assertEqual(t("Säkerhetsspecialist", "riskreducerande åtgärder och riskreducerande arbete"), "")
        # Klimatrubriker utan klimatrisker är omställning, även om texten nämner klimatförändringar
        self.assertEqual(t("Klimat- och energistrateg", "för att bromsa klimatförändringarna. klimatförändringar"), "omst")
        self.assertEqual(t("Klimat- och energistrateg", "enheten arbetar med klimatanpassning."), "omst", "en enstaka träff räcker inte")
        self.assertEqual(t("Miljö- och klimatstrateg", "leda arbetet med klimatanpassning och skyfall"), "risk")
        self.assertEqual(t("Energistrateg"), "omst")
        self.assertEqual(t("Projektledare, dagvattenhantering i kallt klimat"), "risk", "dagvatten är klimatanpassning")
        self.assertEqual(t("Chef med fokus på arbetsklimat"), "")

    def test_varje_annons_har_exakt_en_roll(self):
        self.assertEqual(sum(r["antal"] for r in self.st["roller"]), self.n)
        for r in self.st["roller"]:
            self.assertEqual(r["antal"], len([a for a in self.ads if a["roll"] == r["namn"]]))
            self.assertLessEqual(r["aktuella"], r["antal"])

    def test_andelar_stammer_med_antal(self):
        for k, antal, p in self.st["krav"]:
            with self.subTest(krav=k):
                self.assertEqual(antal, len([a for a in self.ads if k in a["krav"]]))
                self.assertEqual(p, S.procent(antal, self.n))
                self.assertTrue(0 <= p <= 100)
        for r in self.st["roller"]:
            for k, antal, p in r["krav"]:
                self.assertEqual(p, S.procent(antal, r["antal"]))

    def test_topplistor_ar_sorterade(self):
        for nyckel in ("omraden", "nyckelord", "kurser", "arbetsgivare", "lan"):
            tal = [n for _, n in self.st[nyckel]]
            self.assertEqual(tal, sorted(tal, reverse=True), nyckel)
        self.assertEqual(sum(n for _, n in self.st["lan"]), self.n, "varje annons ligger i exakt ett län")

    def test_ortsfilter_per_lan(self):
        for lan, rader in self.st["filter"]["kommuner"].items():
            vantat = len([a for a in self.ads if not lan or a["lan"] == lan])
            self.assertEqual(sum(n for _, n in rader), vantat, lan)

    def test_kompetenser_stammer(self):
        k = K.statistik(self.ads, self.tx)
        for g in k["grupper"].values():
            for kid, t in g["traff"].items():
                self.assertEqual(g["procent"][kid], S.procent(t, g["antal"]))
                self.assertEqual(g["procent_av_alla"][kid], S.procent_dec(t, self.n))

    def test_sparad_statistik_ar_aktuell(self):
        """data/statistik.json ska vara exakt det som Python räknar fram ur nuvarande data (byggt efter senaste hämtningen)."""
        with open(os.path.join(ROT, "data", "statistik.json"), encoding="utf-8") as f:
            sparad = json.load(f)
        self.assertEqual(sparad["statistik"], json.loads(json.dumps(self.st)))


@unittest.skipUnless(shutil.which("node"), "Node saknas")
class PythonOchJavaScriptRaknarLika(unittest.TestCase):
    """Sökordsräknaren körs i webbläsaren. Här kontrolleras att JavaScript-versionen ger exakt samma antal som Python."""

    ORD = ["krisledning", "risk- och sårbarhetsanalys", "kontinuitet", "säkerhetsprövning", "körkort", "projektledning",
           "gis", "statistik", "klimatanpassning", "övningar", "räddningstjänst körkort", "c++", "(", "brand", "kris"]

    def test_samma_antal_traffar(self):
        ads, tx = ladda()
        py = {q: sum(1 for a in ads if S.sok_matcher(q)(S.sokbar_text(a, tx))) for q in self.ORD}
        skript = r"""
const L = require(process.argv[1]); const fs = require("fs"); const path = require("path");
const rot = process.argv[2], ord = JSON.parse(process.argv[3]);
const ads = JSON.parse(fs.readFileSync(path.join(rot, "data/annonser.json"), "utf8")).annonser;
const tx = JSON.parse(fs.readFileSync(path.join(rot, "data/annonstext.json"), "utf8"));
ads.forEach(a => { a._s = (a.rubrik + " " + a.arbetsgivare + " " + a.kommun + " " + a.lan + " " + a.utdrag).toLowerCase(); if (tx[a.id]) a._s += " " + tx[a.id]; });
const ut = {}; for (const q of ord) ut[q] = ads.filter(a => L.makeMatcher(q)(a._s)).length;
console.log(JSON.stringify(ut));
"""
        res = subprocess.run(["node", "-e", skript, os.path.join(ROT, "skript", "logik.js"), ROT, json.dumps(self.ORD)],
                             capture_output=True, text=True, check=True)
        js = json.loads(res.stdout)
        self.assertEqual(js, py)


if __name__ == "__main__":
    unittest.main()
