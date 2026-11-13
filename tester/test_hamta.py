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

    def test_kris_i_ortnamn_raknas_inte(self):
        for rubrik in ("Budbilsförare Kristianstad", "Erfaren CE-chaufför till kund i Kristianstad!", "Lagerarbetare Kristinehamn"):
            with self.subTest(rubrik=rubrik):
                self.assertIsNone(H.CORE.search(rubrik))
        for rubrik in ("Krisberedskapssamordnare", "Kris- och kontinuitetsledare", "Krisstöd till Kristianstads kommun"):
            with self.subTest(rubrik=rubrik):
                self.assertIsNotNone(H.CORE.search(rubrik))

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


class AnnanUtbildning(unittest.TestCase):
    """Tjänster som kräver doktorsexamen eller är doktorandtjänster i andra ämnen sorteras bort."""
    RSA = "Du arbetar med krisberedskap, risk- och sårbarhetsanalys (RSA), krisledning, övningar och utvärderar åtgärder. "

    def ta_med(self, rubrik, text=""):
        return H.bearbeta(annons(headline=rubrik, description={"text": self.RSA + text}), "aktuell", "x", fran="2026-01-01") is not None

    def test_postdoktor_och_lektor_sorteras_alltid_bort(self):
        for rubrik in ("Postdoktor i krisberedskap", "Universitetslektor i krisberedskap och civilt försvar",
                       "Biträdande universitetslektor i Riskhantering"):
            with self.subTest(rubrik=rubrik):
                self.assertFalse(self.ta_med(rubrik))

    def test_forskare_bara_om_doktorsexamen_kravs(self):
        self.assertFalse(self.ta_med("Forskare inom riskhantering", "Du ska ha avlagt doktorsexamen i ett relevant ämne."))
        self.assertTrue(self.ta_med("Forskare eller analytiker inom krisberedskap", "Doktorsexamen är meriterande."))
        self.assertTrue(self.ta_med("Forskare eller analytiker inom krisberedskap"))
        # Kravet ska hittas även efter ett långt inledande stycke som slutar med kolon och innehåller "Välkommen"
        intro = "Välkommen att söka anställning som forskare. Våra sex forskningsavdelningar:\nGeofysik\n"
        self.assertFalse(self.ta_med("Forskare inom klimathändelser", intro + "Kvalifikationskrav\nDoktorsexamen i klimatvetenskap."))
        self.assertTrue(self.ta_med("Forskare eller analytiker inom krisberedskap", "Det är meriterande för tjänsten om du har:\ndoktorsexamen"))

    def test_doktorand_bara_i_programmets_amnen(self):
        self.assertTrue(self.ta_med("Doktorand i trafiksäkerhet"))
        self.assertTrue(self.ta_med("Doktorand i krisberedskap"))
        self.assertFalse(self.ta_med("Doktorand i fysiologi och modellering av ärftlig klimatanpassning"))

    def test_andra_forskningsroller_finns_kvar(self):
        for rubrik in ("Forskningsassistent inom krisberedskap", "Universitetsadjunkt i risk och miljöstudier",
                       "Forskningssamordnare för totalförsvar"):
            with self.subTest(rubrik=rubrik):
                self.assertTrue(self.ta_med(rubrik))

    def test_sakerhetsarkitekt_ar_it_sakerhet(self):
        self.assertFalse(self.ta_med("Säkerhetsarkitekt inom krisberedskap"))


class Kravavsnitt(unittest.TestCase):
    """Exempel från riktiga annonser: rubriken för en meriterande lista står ofta sist på en lång rad."""

    def test_meriterande_rubrik_sist_pa_raden(self):
        text = ("Vi vill också att du har:\nB-körkort. Det är meriterande om du har\n"
                "erfarenhet av att hantera säkerhetsskyddsklassificerade uppgifter\n\nAnställningsform: tillsvidare")
        self.assertEqual(H.hitta_erfarenheter(text), [])
        self.assertIn("Körkort", H.hitta_krav(text))

    def test_lista_under_meriterande_hoppas_over_till_tom_rad(self):
        text = "Minst 2 års erfarenhet av arbete med våldsutsatta.\nMeriterande\nErfarenhet från socialtjänstens arbete"
        self.assertEqual(H.hitta_erfarenheter(text), ["Minst 2 års erfarenhet av arbete med våldsutsatta"])

    def test_valkomsttext_med_kolon_doljer_inte_kraven(self):
        text = ("Välkommen att söka anställning hos oss. Våra sex avdelningar:\nGeofysik\n"
                "Kvalifikationskrav\nErfarenhet av krisledning och kontinuitetsplanering.")
        self.assertEqual(H.hitta_erfarenheter(text), ["Erfarenhet av krisledning och kontinuitetsplanering"])

    def test_vanlig_mening_med_garna_ar_ingen_rubrik(self):
        text = "Skicka gärna in din ansökan redan idag!\nErfarenhet av beredskapsarbete."
        self.assertEqual(H.hitta_erfarenheter(text), ["Erfarenhet av beredskapsarbete"])

    def test_ser_vi_som_vardefullt_ar_meriterande(self):
        self.assertEqual(H.hitta_erfarenheter("Erfarenhet av sannolikhetsanalyser ser vi som värdefullt."), [])

    def test_arbetsgivarens_historia_ar_inget_krav(self):
        text = "Om Studsvik:\nStudsvik har över 75 års erfarenhet av kärnteknik.\nMinst 3 års erfarenhet av säkerhetsarbete."
        self.assertEqual(H.hitta_erfarenheter(text), ["Minst 3 års erfarenhet av säkerhetsarbete"])


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

    def test_mjuka_formuleringar_ar_inte_krav(self):
        for text in ("Har du erfarenhet av krisberedskap från dina studier är det bra.",
                     "Du har gärna erfarenhet av riskanalys.",
                     "Erfarenhet av beredskap genom praktik eller examensarbete är välkommen."):
            with self.subTest(text=text):
                self.assertEqual(H.hitta_krav(text), [])

    def test_nyexaminerade_far_inga_erfarenhetskrav(self):
        text = "Du har akademisk examen. Du har minst 2 års erfarenhet av krisberedskap."
        self.assertEqual(H.hitta_krav(text, erfarenhet_kravs=True, nyexad=True), ["Akademisk examen"])
        self.assertIn("Erfarenhet av beredskap/kris", H.hitta_krav(text))

    def test_tom_text(self):
        self.assertEqual(H.hitta_krav(""), [])
        self.assertEqual(H.hitta_krav(None), [])

    def test_krav_finns_i_posten(self):
        r = H.bearbeta(annons(driving_license_required=True), "aktuell", "x", fran="2026-01-01")
        self.assertIn("Körkort", r["krav"])


class Nyexaminerade(unittest.TestCase):
    def test_uttryckliga_formuleringar(self):
        for text in ("Vi söker dig som är nyexaminerad.", "Rollen passar dig i början av din karriär.", "Vi söker juniora utredare.",
                     "Traineeprogram för civilt försvar."):
            with self.subTest(text=text):
                self.assertTrue(H.passar_nyexad("Handläggare", text.lower()))
        self.assertTrue(H.passar_nyexad("Junior beredskapshandläggare", ""))

    def test_inte_nar_juniora_bara_namns(self):
        for text in ("du coachar våra mer juniora konsulter", "vi har både erfarna och mer juniora medarbetare"):
            with self.subTest(text=text):
                self.assertFalse(H.passar_nyexad("Säkerhetskonsult", text))


class Erfarenheter(unittest.TestCase):
    def test_fraser_plockas_ut(self):
        text = ("Du har minst 3 års erfarenhet av riskhantering. Vi söker dig med erfarenhet av SimCorp. "
                "Erfarenhet av projektledning är meriterande.")
        self.assertEqual(H.hitta_erfarenheter(text), ["Minst 3 års erfarenhet av riskhantering", "Erfarenhet av SimCorp"])

    def test_meriterande_lista_och_arbetsgivarens_text_ar_inte_krav(self):
        text = ("Kvalifikationer:\nErfarenhet av krisberedskap\n\nDet är meriterande om du har:\nErfarenhet av GIS\n"
                "Erfarenhet av SimCorp\n\nVi erbjuder:\nDu får erfarenhet av internationellt arbete")
        self.assertEqual(H.hitta_erfarenheter(text), ["Erfarenhet av krisberedskap"])

    def test_texten_avgor_inte_arbetsformedlingens_ruta(self):
        """Länsstyrelsen Västra Götaland, Handläggare för riskhänsyn: rutan "erfarenhet krävs" är ikryssad,
        men texten kräver bara utbildning och kunskap. Erfarenheterna står under "Vi ser gärna att du har:"."""
        text = ("Du har:\nHögskoleutbildning inom riskhantering\nRelevant kunskap om riskhantering\n\n"
                "Vi ser gärna att du har:\nRelevant yrkeserfarenhet inom risk- och beredskapshänsyn\n"
                "Erfarenhet av översvämningshantering\n\nVälkommen med din ansökan!")
        h = annons(description={"text": "Du arbetar med risk- och sårbarhetsanalys, krisberedskap, klimatanpassning och översvämning. "
                                        "Du utvärderar åtgärder.\n" + text}, experience_required=True)
        r = H.bearbeta(h, "aktuell", "x", fran="2026-01-01")
        self.assertEqual(r["erfarenheter"], [])
        self.assertTrue(r["erf_ruta"])
        self.assertNotIn("Tidigare erfarenhet", r["krav"])
        # Utan ikryssad ruta finns ingen anmärkning
        h["experience_required"] = False
        self.assertFalse(H.bearbeta(h, "aktuell", "x", fran="2026-01-01")["erf_ruta"])

    def test_rutan_anmarks_inte_nar_texten_kraver_erfarenhet(self):
        h = annons(description={"text": "Du arbetar med krisberedskap, risk- och sårbarhetsanalys (RSA), krisledning och övningar. "
                                        "Du utvärderar åtgärder. Du har minst 3 års erfarenhet av kommunal verksamhet."},
                   experience_required=True)
        r = H.bearbeta(h, "aktuell", "x", fran="2026-01-01")
        self.assertEqual(r["erfarenheter"], ["Minst 3 års erfarenhet av kommunal verksamhet"])
        self.assertFalse(r["erf_ruta"])

    def test_nyexaminerade_och_mjuka_formuleringar(self):
        self.assertEqual(H.hitta_erfarenheter("Du har erfarenhet av beredskap.", nyexad=True), [])
        self.assertEqual(H.hitta_erfarenheter("Har du erfarenhet av beredskap från dina studier är det bra."), [])

    def test_langa_fraser_kortas_vid_ordgrans(self):
        f = H.hitta_erfarenheter("Du har erfarenhet av " + "mycket långa och detaljerade beskrivningar " * 6 + "av saker.")[0]
        self.assertLessEqual(len(f), 112)
        self.assertTrue(f.endswith(" …"))


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
