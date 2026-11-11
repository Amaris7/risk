"""Funktionstester för hämtningen: urval, klassning, dubbletter, säkra länkar och sparade filer."""
import json
import os
import tempfile
import unittest

import hjalp  # noqa: F401  (gör skript/ importerbart)
import hamta_annonser as H


def annons(**over):
    """En påhittad annons i samma form som Arbetsförmedlingens API."""
    h = {
        "id": "12345",
        "headline": "Beredskapssamordnare",
        "publication_date": "2026-10-01T08:00:00",
        "application_deadline": "2026-11-30T23:59:59",
        "employer": {"name": "TESTKOMMUN", "workplace": "Testkommun"},
        "workplace_address": {"municipality": "Karlstad", "region": "Värmlands län"},
        "description": {"text": "Du arbetar med krisberedskap, risk- och sårbarhetsanalys (RSA), krisledning och övningar. "
                                "Du utvärderar åtgärder och arbetar med omvärldsbevakning."},
        "webpage_url": "https://arbetsformedlingen.se/platsbanken/annonser/12345",
        "working_hours_type": {"label": "Heltid"},
    }
    h.update(over)
    return h


class Urval(unittest.TestCase):
    def test_relevant_annons_tas_med(self):
        r = H.bearbeta(annons(), "aktuell", "beredskapssamordnare", fran="2026-01-01")
        self.assertIsNotNone(r)
        self.assertEqual(r["status"], "aktuell")
        self.assertIn("Krisberedskap & civilt försvar", r["omraden"])
        self.assertIn("RHAD21/RHAD31", r["kurser"])
        self.assertIn(r["match"], ("Hög", "Medel", "Grundläggande"))

    def test_rubrik_utan_koppling_sorteras_bort(self):
        self.assertIsNone(H.bearbeta(annons(headline="Lagerarbetare"), "aktuell", "x", fran="2026-01-01"))

    def test_uteslutna_yrken_sorteras_bort(self):
        for rubrik in ("Brandman till räddningstjänsten", "IT-säkerhetsspecialist", "Ordningsvakt"):
            with self.subTest(rubrik=rubrik):
                self.assertIsNone(H.bearbeta(annons(headline=rubrik), "aktuell", "x", fran="2026-01-01"))

    def test_for_gammal_annons_sorteras_bort(self):
        self.assertIsNone(H.bearbeta(annons(publication_date="2024-01-01T00:00:00"), "historisk", "x", fran="2025-11-10"))

    def test_for_svag_koppling_sorteras_bort(self):
        h = annons(headline="Handläggare säkerhet", description={"text": "Allmän administration."})
        self.assertIsNone(H.bearbeta(h, "aktuell", "x", fran="2026-01-01"))

    def test_finansiell_risk_markeras_som_angransande(self):
        h = annons(headline="Riskanalytiker till bank",
                   description={"text": "Riskhantering och riskanalys av kreditrisk och marknadsrisk i bank och finans. "
                                        "Utvärdering, uppföljning, statistik och analys."})
        r = H.bearbeta(h, "aktuell", "riskanalytiker", fran="2026-01-01")
        self.assertEqual(r["omraden"], ["Finansiell & operativ risk (angränsande)"])

    def test_arkiverad_status(self):
        self.assertEqual(H.bearbeta(annons(), "historisk", "x", fran="2026-01-01")["status"], "arkiverad")

    def test_text_och_utdrag_kortas(self):
        r = H.bearbeta(annons(description={"text": "krisberedskap RSA krisledning övningar " * 500}), "aktuell", "x", fran="2026-01-01")
        self.assertLessEqual(len(r["utdrag"]), 200)
        self.assertLessEqual(len(r["text"]), H.TEXT_MAX)


class Krav(unittest.TestCase):
    def test_krav_hittas_i_fast_ordning(self):
        text = ("Vi söker dig som har en akademisk examen inom samhällsvetenskap. Du har B-körkort. "
                "Tjänsten kräver säkerhetsprövning med registerkontroll. Du har minst 3 års erfarenhet av krisberedskap. "
                "Du uttrycker dig väl i svenska och engelska i tal och skrift.")
        self.assertEqual(H.hitta_krav(text), ["Akademisk examen", "Säkerhetsprövning", "Körkort", "Erfarenhet av beredskap/kris",
                                              "Flera års erfarenhet", "Svenska i tal och skrift", "Engelska i tal och skrift"])

    def test_meriterande_raknas_inte_som_krav(self):
        text = "Du har högskoleexamen. Det är meriterande med erfarenhet av projektledning. Körkort är önskvärt."
        self.assertEqual(H.hitta_krav(text), ["Akademisk examen"])

    def test_strukturerade_falt_fran_api(self):
        self.assertEqual(H.hitta_krav("Inget särskilt.", korkort_kravs=True, erfarenhet_kravs=True), ["Körkort", "Tidigare erfarenhet"])
        self.assertNotIn("Tidigare erfarenhet", H.hitta_krav("Du har flerårig erfarenhet.", erfarenhet_kravs=True))

    def test_tom_text(self):
        self.assertEqual(H.hitta_krav(""), [])
        self.assertEqual(H.hitta_krav(None), [])

    def test_krav_finns_i_posten(self):
        r = H.bearbeta(annons(driving_license_required=True), "aktuell", "x", fran="2026-01-01")
        self.assertIn("Körkort", r["krav"])


class SakraLankar(unittest.TestCase):
    def test_farlig_lank_ersatts_med_platsbanken(self):
        for url in ("javascript:alert(1)", "http://evil.example/x", "", None):
            with self.subTest(url=url):
                r = H.bearbeta(annons(webpage_url=url), "aktuell", "x", fran="2026-01-01")
                self.assertEqual(r["url"], "https://arbetsformedlingen.se/platsbanken/annonser/12345")

    def test_id_kodas_i_reservlank(self):
        r = H.bearbeta(annons(id="1/../x", webpage_url=None), "aktuell", "x", fran="2026-01-01")
        self.assertNotIn("/../", r["url"].replace(H.PLATSBANKEN, ""))


class Dubbletter(unittest.TestCase):
    def test_dubblett_laggs_inte_till_tva_ganger(self):
        ads = {}
        h = annons()
        H.lagg_till(ads, h, H.bearbeta(h, "historisk", "x", fran="2026-01-01"))
        H.lagg_till(ads, h, H.bearbeta(h, "historisk", "x", fran="2026-01-01"))
        self.assertEqual(len(ads), 1)

    def test_aktuell_version_vinner(self):
        ads = {}
        h = annons()
        H.lagg_till(ads, h, H.bearbeta(h, "historisk", "x", fran="2026-01-01"))
        H.lagg_till(ads, h, H.bearbeta(h, "aktuell", "x", fran="2026-01-01"))
        self.assertEqual(next(iter(ads.values()))["status"], "aktuell")


class Spara(unittest.TestCase):
    def test_filer_och_falt(self):
        r = H.bearbeta(annons(), "aktuell", "x", fran="2026-01-01")
        with tempfile.TemporaryDirectory() as d:
            H.spara([r], d)
            with open(os.path.join(d, "annonser.json"), encoding="utf-8") as f:
                data = json.load(f)
            with open(os.path.join(d, "annonstext.json"), encoding="utf-8") as f:
                texter = json.load(f)
            self.assertTrue(os.path.exists(os.path.join(d, "annonser.csv")))
        post = data["annonser"][0]
        self.assertEqual(sorted(post), sorted(H.KEEP))
        self.assertNotIn("text", post, "hela texten ska bara ligga i annonstext.json")
        self.assertEqual(texter[post["id"]], texter[post["id"]].lower())
        self.assertIn("krisberedskap", texter[post["id"]])


if __name__ == "__main__":
    unittest.main()
