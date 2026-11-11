"""Funktions- och säkerhetstester för bygget: kalenderläsning, säker inbäddning av data och sidans skal."""
import json
import os
import re
import tempfile
import unittest

import hjalp  # noqa: F401
import bygg_sida as B

ICS = "\r\n".join([
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "X-WR-CALNAME:Förnamn Efternamn Kalender (Canvas)",
    # Egen händelse, vintertid (UTC 12:15 → 13:15), kurskod först vinner över Canvas-koden
    "BEGIN:VEVENT",
    "DTSTART:20261109T121500Z",
    "DTEND:20261109T160000Z",
    "SUMMARY:RHAD01: Posterseminarium (campus) [RHAD14\\, ht26]",
    "LOCATION:Karlstads universitet\\, sal 21A258",
    "DESCRIPTION:Lärare: Test.\\nAnslut via Zoom: https://kau-se.zoom.us/my/hemlig",
    "URL:https://kau-se.zoom.us/my/hemlig",
    "END:VEVENT",
    # Canvas-uppgift: kod sist, ingen plats, ikon i titeln, ombruten rad
    "BEGIN:VEVENT",
    "DTSTART;VALUE=DATE:20261119",
    "DTEND;VALUE=DATE:20261120",
    "SUMMARY:🔔 Inlämning PM [RHAD12\\, ht26]",
    "DESCRIPTION:Lämna in via Canvas\\, se instruktion",
    " er.",
    "END:VEVENT",
    # Sommartid (UTC 11:00 → 13:00)
    "BEGIN:VEVENT",
    "DTSTART:20270602T110000Z",
    "DTEND:20270602T150000Z",
    "SUMMARY:RHAD03: Föreläsning (campus)",
    "LOCATION:Karlstads universitet\\, sal 21A259",
    "END:VEVENT",
    # Lokal tid med TZID lämnas orörd
    "BEGIN:VEVENT",
    "DTSTART;TZID=Europe/Stockholm:20270118T081500",
    "DTEND;TZID=Europe/Stockholm:20270118T120000",
    "SUMMARY:RHAD12: Personsäkerhet I – campusträff",
    "LOCATION:Karlstads universitet\\, sal 3D417",
    "END:VEVENT",
    "END:VCALENDAR",
])


class Kalender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.NamedTemporaryFile("w", suffix=".ics", delete=False, encoding="utf-8") as f:
            f.write(ICS)
            cls.sokvag = f.name
        cls.kal = B.las_ics(cls.sokvag)
        cls.ev = cls.kal["handelser"]

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.sokvag)

    def test_antal_och_sortering(self):
        self.assertEqual(len(self.ev), 4)
        self.assertEqual([e["start"] for e in self.ev], sorted(e["start"] for e in self.ev))

    def test_utc_blir_svensk_vintertid(self):
        self.assertEqual(self.ev[0]["start"], "2026-11-09T13:15")
        self.assertEqual(self.ev[0]["slut"], "2026-11-09T17:00")

    def test_utc_blir_svensk_sommartid(self):
        e = next(e for e in self.ev if e["kod"] == "RHAD03")
        self.assertEqual(e["start"], "2027-06-02T13:00")

    def test_lokal_tid_orord(self):
        e = next(e for e in self.ev if "Personsäkerhet" in e["titel"])
        self.assertEqual(e["start"], "2027-01-18T08:15")

    def test_egen_kurskod_vinner_over_canvas(self):
        self.assertEqual(self.ev[0]["kod"], "RHAD01")
        self.assertEqual(self.ev[0]["titel"], "Posterseminarium (campus)")

    def test_canvas_uppgift(self):
        e = self.ev[1]
        self.assertEqual((e["kod"], e["titel"], e["heldag"], e["uppgift"]), ("RHAD12", "Inlämning PM", True, True))

    def test_ombrutna_rader_och_escape(self):
        self.assertEqual(self.ev[1]["info"], "Lämna in via Canvas, se instruktioner.")

    def test_zoomlankar_tas_bort(self):
        self.assertNotIn("zoom.us", json.dumps(self.kal))
        self.assertEqual(self.ev[0]["url"], "")

    def test_kalendernamn_med_personnamn_tas_inte_med(self):
        self.assertNotIn("Efternamn", json.dumps(self.kal, ensure_ascii=False))


class SakerInbaddning(unittest.TestCase):
    def test_data_kan_inte_avsluta_scripttaggen(self):
        js = B.data_som_js({"x": "</script><script>alert(1)</script><!--"})
        self.assertNotIn("<", js)
        self.assertEqual(json.loads(js)["x"], "</script><script>alert(1)</script><!--")

    def test_node_export_tas_bort(self):
        kod = "function a(){}\n/* node-export */\nif (typeof module !== 'undefined') module.exports = {a};\n"
        self.assertNotIn("module.exports", B.logik_som_js(kod))
        self.assertIn("function a(){}", B.logik_som_js(kod))

    def test_skal_med_csp_och_inga_platshallare(self):
        html = B.bygg("<title>T</title><script>/*__LOGIK__*/\nconst DATA = __DATA__;</script>", {"a": 1}, "function f(){}\n/* node-export */\nx")
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn('http-equiv="Content-Security-Policy"', html)
        self.assertIn("object-src 'none'", html)
        self.assertNotIn("__DATA__", html)
        self.assertNotIn("__LOGIK__", html)
        self.assertRegex(html, re.compile(r'<html lang="sv">'))


class Illustrationer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import illustrationer as I
        cls.I = I
        data = {"annonser": [{"lan": "Skåne län"}, {"lan": "Stockholms län"}, {"lan": "Stockholms län"}],
                "kalender": {"handelser": [{"kod": "RHAD12", "start": "2026-11-11T09:15", "plats": "sal 3D417", "uppgift": False},
                                           {"kod": "RHAD12", "start": "2027-01-14T08:15", "plats": "", "uppgift": True}]}}
        cls.bilder = I.alla(data, {"1": "höjd beredskap och brand", "2": "cyber"})

    def test_alla_illustrationer_ar_giltig_svg(self):
        import xml.etree.ElementTree as ET
        self.assertEqual(set(self.bilder), {"hero", "matris", "tidslinje", "natverk", "karta", "hot", "flode"})
        for namn, svg in self.bilder.items():
            with self.subTest(namn):
                rot = ET.fromstring(svg)
                self.assertTrue(rot.tag.endswith("svg"))
                self.assertEqual(rot.get("aria-hidden"), "true")

    def test_hot_raknar_andelar(self):
        self.assertIn(">50 %<", self.bilder["hot"])

    def test_tom_data_kraschar_inte(self):
        tom = self.I.alla({"annonser": [], "kalender": None}, {})
        self.assertTrue(all(v.startswith("<svg") for v in tom.values()))

    def test_text_i_illustrationer_escapas(self):
        self.assertEqual(self.I.esc('<b>&"'), "&lt;b&gt;&amp;&quot;")

    def test_platshallare_byts(self):
        self.assertEqual(B.grafik("a<!--GRAFIK:x-->b<!--GRAFIK:okand-->c", {"x": "<svg/>"}), "a<svg/>bc")


if __name__ == "__main__":
    unittest.main()
