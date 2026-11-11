// Funktions- och säkerhetstester för sidans logik (skript/logik.js). Kör: node --test tester/*.test.cjs
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../skript/logik.js");

test("esc gör HTML ofarlig, även i attribut", () => {
  assert.equal(L.esc('<img src=x onerror="alert(1)">'), "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;");
  assert.equal(L.esc("a'b & c"), "a&#39;b &amp; c");
  assert.equal(L.esc(null), "");
  assert.equal(L.esc(undefined), "");
  assert.equal(L.esc(42), "42");
});

test("count räknar värden och listor, flest först", () => {
  const r = L.count([{ a: ["x", "y"] }, { a: ["x"] }, { a: [] }, { a: [""] }], o => o.a);
  assert.deepEqual(r, [["x", 2], ["y", 1]]);
});

test("sökning: ord matchas från början av ett ord", () => {
  const m = L.makeMatcher("gis");
  assert.equal(m("erfarenhet av gis och kartor"), true);
  assert.equal(m("god kunskap i GIS"), true);
  assert.equal(m("logistik och registrering"), false);
  assert.equal(L.makeMatcher("krisled")("du leder krisledningsstaben"), true);
});

test("sökning: flera ord betyder att alla måste finnas", () => {
  const m = L.makeMatcher("räddningstjänst körkort");
  assert.equal(m("räddningstjänst, b-körkort krävs"), true);
  assert.equal(m("räddningstjänsten söker"), false);
});

test("sökning: svenska tecken och skiftläge", () => {
  assert.equal(L.makeMatcher("Övning")("planera övningar"), true);
  assert.equal(L.makeMatcher("SÄKERHETSPRÖVNING")("säkerhetsprövning görs"), true);
});

test("sökning: specialtecken tolkas bokstavligt och kraschar inte (ingen regex-injektion)", () => {
  for (const q of ["(", "[", "a+b", ".*", "\\", "$^", "risk- och", "c++", "(?<x>)"]) {
    assert.doesNotThrow(() => L.makeMatcher(q)("text"));
  }
  assert.equal(L.makeMatcher(".*")("vad som helst"), false);
  assert.equal(L.makeMatcher("c++")("kunskap i c++"), true);
  assert.equal(L.makeMatcher("risk- och")("risk- och sårbarhetsanalys"), true);
});

test("sökning: tom sökning matchar allt, null-text tål", () => {
  assert.equal(L.makeMatcher("")("x"), true);
  assert.equal(L.makeMatcher("   ")("x"), true);
  assert.equal(L.makeMatcher("x")(null), false);
});

test("kalTyp klassar händelser", () => {
  assert.deepEqual(L.kalTyp({ titel: "Inlämning PM", uppgift: true }), ["Uppgift/inlämning", "typ-inl"]);
  assert.deepEqual(L.kalTyp({ titel: "Kursstart – Personsäkerhet II", plats: "Distans (Canvas)" }), ["Kursstart", ""]);
  assert.deepEqual(L.kalTyp({ titel: "Webbinarium – myter", plats: "Zoom" }), ["Distans", "plain"]);
  assert.deepEqual(L.kalTyp({ titel: "Campusträff", plats: "Karlstads universitet, sal 3D418" }), ["Campus", "typ-campus"]);
  assert.deepEqual(L.kalTyp({ titel: "Något", plats: "" }), ["Övrigt", "plain"]);
});

test("kalRubrik tar bort kursnamnet ur titeln", () => {
  assert.equal(L.kalRubrik("Hantering av naturkatastrofer 1 – campusträff", "Hantering av naturkatastrofer 1"), "Campusträff");
  assert.equal(L.kalRubrik("Kursstart – Teoribildning inom riskhantering", "Teoribildning inom riskhantering"), "Kursstart");
  assert.equal(L.kalRubrik("Personsäkerhet I – campusträff", "Personsäkerhet I: skadeanalys och riskbedömning"), "Campusträff");
  assert.equal(L.kalRubrik("inlämning PM", "Övrigt"), "Inlämning PM");
});

test("klock formaterar tider", () => {
  assert.equal(L.klock({ heldag: true }), "Heldag");
  assert.equal(L.klock({ start: "2026-10-09T23:59", slut: "2026-10-09T23:59" }), "senast 23:59");
  assert.equal(L.klock({ start: "2026-11-10T13:15", slut: "2026-11-10T16:00" }), "13:15–16:00");
});

test("aktivaFilter räknar valda filter", () => {
  assert.equal(L.aktivaFilter({ status: "alla", match: "alla" }), 0);
  assert.equal(L.aktivaFilter({ lan: "Skåne län", kommun: "Malmö", status: "aktuell", match: "Hög" }), 4);
});

test("sakerAnnonsUrl släpper bara igenom Platsbanken över https", () => {
  const ok = "https://arbetsformedlingen.se/platsbanken/annonser/31687701";
  assert.equal(L.sakerAnnonsUrl(ok), ok);
  for (const bad of ["javascript:alert(1)", "http://arbetsformedlingen.se/platsbanken/annonser/1",
    "https://arbetsformedlingen.se.evil.com/platsbanken/annonser/1", "https://arbetsformedlingen.se/platsbanken/annonser/1\"onmouseover=x", "", null]) {
    assert.equal(L.sakerAnnonsUrl(bad), "", String(bad));
  }
});

test("kortTitel kortar rubriker utan att klippa sammansatta ord", () => {
  assert.equal(L.kortTitel("Säkerhets- och beredskapshandläggare"), "Säkerhets- och beredskapshandläggare");
  assert.equal(L.kortTitel("Beredskapssamordnare till Heby kommun"), "Beredskapssamordnare");
  assert.equal(L.kortTitel("Säkerhetssamordnare i Botkyrka"), "Säkerhetssamordnare");
  assert.equal(L.kortTitel("Handläggare inom krisberedskap"), "Handläggare inom krisberedskap");
  assert.equal(L.kortTitel("Säkerhetsstrateg – Helsingborgs stad"), "Säkerhetsstrateg");
  assert.equal(L.kortTitel("Riskanalytiker, Göteborg"), "Riskanalytiker");
  assert.equal(L.kortTitel("Beredskapssamordnare sökes!"), "Beredskapssamordnare");
  assert.equal(L.kortTitel("Samordnare - beredskap inom kommunal hälso- och sjukvård"), "Samordnare");
  assert.equal(L.kortTitel("risk manager"), "Risk manager");
});

test("procent avrundar och tål noll", () => {
  assert.equal(L.procent(1, 3), "33 %");
  assert.equal(L.procent(0, 0), "–");
});
