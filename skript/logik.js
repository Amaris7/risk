/* Ren logik för sidan (ingen DOM). Bäddas in i index.html av skript/bygg_sida.py
   och testas med Node: node --test tester/*.test.cjs */

/** Gör text säker att lägga in i HTML (även i attribut). Allt från datan ska gå genom esc(). */
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/** Räknar förekomster. f får returnera ett värde eller en lista. Sorterat med flest först. */
function count(arr, f) {
  const m = new Map();
  arr.forEach(x => [].concat(f(x)).forEach(k => k && m.set(k, (m.get(k) || 0) + 1)));
  return [...m].sort((a, b) => b[1] - a[1]);
}

/** Sökning: alla ord måste finnas, och varje ord måste stå i början av ett ord i texten.
    "gis" hittar "GIS" men inte "logistik", "krisled" hittar "krisledning". Specialtecken tolkas bokstavligt. */
const _matchCache = new Map();
function makeMatcher(q) {
  const key = String(q ?? "");
  if (!_matchCache.has(key)) {
    const res = key.toLowerCase().split(/\s+/).filter(Boolean)
      .map(w => new RegExp("(?:^|[^\\p{L}\\p{N}])" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "u"));
    _matchCache.set(key, text => res.every(re => re.test(String(text ?? "").toLowerCase())));
  }
  return _matchCache.get(key);
}

/** Typ av kalenderhändelse: [etikett, css-klass]. */
function kalTyp(e) {
  const txt = ((e.titel || "") + " " + (e.plats || "")).toLowerCase();
  if (e.uppgift || /inlämning|deadline/.test(txt)) return ["Uppgift/inlämning", "typ-inl"];
  if (/kursstart/.test(txt)) return ["Kursstart", ""];
  if (/zoom|webbinar|canvas/.test(txt) && !/campus|sal /.test(txt)) return ["Distans", "plain"];
  if (/campus|sal |universitet/.test(txt)) return ["Campus", "typ-campus"];
  return ["Övrigt", "plain"];
}

/** Kortar kalendertiteln: kursnamnet i början tas bort (det visas redan som etikett). */
function kalRubrik(titel, kursnamn) {
  let t = String(titel || "");
  const n = String(kursnamn || "").split(":")[0];
  if (n && t.toLowerCase().startsWith(n.toLowerCase())) t = t.slice(n.length).replace(/^\s*[–-]\s*/, "");
  t = t.replace(/^Kursstart\s*[–-]\s*.*/, "Kursstart");
  return t.charAt(0).toUpperCase() + t.slice(1);
}

/** Klockslag för en händelse: "Heldag", "senast 23:59" eller "13:15–16:00". */
function klock(e) {
  if (e.heldag) return "Heldag";
  const s = (e.start || "").slice(11), t = (e.slut || "").slice(11);
  return !t || s === t ? `senast ${s}` : `${s}–${t}`;
}

/** Antal aktiva filter (sökningen räknas inte). */
function aktivaFilter(st) {
  return ["lan", "kommun", "omr", "roll"].filter(k => st[k]).length + (st.status !== "alla") + (st.match !== "alla") + (!!st.erf && st.erf !== "alla") + !!st.klim;
}

/** Säker länk: bara https-adresser till Platsbanken, annars ingen länk. */
function sakerAnnonsUrl(url) {
  return /^https:\/\/arbetsformedlingen\.se\/platsbanken\/annonser\/[\w-]+$/.test(String(url || "")) ? url : "";
}

// Titlar, procent och all annan statistik räknas i Python: skript/statistik.py

/** Erfarenhetsfiltret. "ja": annonsen kräver erfarenhet (se a.erfarenheter för vilken). "nej": inga erfarenhetskrav.
    "ny": annonsen vänder sig uttryckligen till nyexaminerade eller juniora. Samma regel som kraver_erfarenhet() i Python. */
const kraverErfarenhet = a => (a.erfarenheter || []).length > 0;
function erfarenhetOk(a, val) {
  if (val === "ja") return kraverErfarenhet(a);
  if (val === "nej") return !kraverErfarenhet(a);
  if (val === "ny") return !!a.junior;
  return true;
}

/* node-export */
if (typeof module !== "undefined") module.exports = { esc, count, makeMatcher, kalTyp, kalRubrik, klock, aktivaFilter, sakerAnnonsUrl, erfarenhetOk };
