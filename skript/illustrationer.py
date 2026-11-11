"""Illustrationer för sidan, ritade som SVG i kod (inga foton, inga rättighetsfrågor).
Används av bygg_sida.py: mallen har platshållare <!--GRAFIK:namn--> som byts mot SVG:n.
Färgerna kommer från CSS-variablerna --hero-* och --risk-* i mallen."""
import math
import random


def hero():
    """Översikt: riskkurvor över ett rutnät och en flygbild av ett översvämmat bostadsområde."""
    random.seed(11)
    W, H = 1200, 460
    MAP_Y = 300                      # där flygbilden börjar
    ut = []
    a = ut.append

    a(f'<svg class="hero-art" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false">')
    a('<defs><linearGradient id="hg-fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--hero-bg)" stop-opacity="0"/>'
      '<stop offset="1" stop-color="var(--hero-bg)" stop-opacity=".9"/></linearGradient>'
      '<pattern id="hg-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
      '<line x1="0" y1="0" x2="0" y2="8" stroke="var(--hero-warn)" stroke-width="1.4" stroke-opacity=".55"/></pattern></defs>')

    # Rutnät
    for x in range(0, W + 1, 60):
        a(f'<line x1="{x}" y1="0" x2="{x}" y2="{MAP_Y}" stroke="var(--hero-grid)" stroke-width="1"/>')
    for y in range(30, MAP_Y, 45):
        a(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="var(--hero-grid)" stroke-width="1"/>')


    def path(pts):
        d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            cx = (x0 + x1) / 2
            d += f" C{cx:.1f} {y0:.1f} {cx:.1f} {y1:.1f} {x1:.1f} {y1:.1f}"
        return d


    # Överskridandekurvor (sannolikhet mot skada), tre scenarier
    for i, (k, op) in enumerate([(0.0042, 1), (0.0034, .55), (0.0052, .35)]):
        pts = [(x, 40 + 230 * (1 - math.exp(-k * (x - 560)))) for x in range(560, W + 1, 40)]
        a(f'<path d="{path(pts)}" fill="none" stroke="var(--hero-line)" stroke-width="{2 if i == 0 else 1.3}" stroke-opacity="{op}"/>')
    for x in (640, 760, 880, 1000, 1120):
        y = 40 + 230 * (1 - math.exp(-0.0042 * (x - 560)))
        a(f'<circle cx="{x}" cy="{y:.1f}" r="3.5" fill="var(--hero-bg)" stroke="var(--hero-line)" stroke-width="1.6"/>')

    # Flödestopp (hydrograf) över en varningsnivå
    pts = []
    for x in range(600, W + 1, 20):
        t = (x - 600) / (W - 600)
        y = 262 - 150 * math.exp(-((t - .45) / .12) ** 2) - 14 * math.sin(t * 9) * (1 - t) - random.uniform(0, 4)
        pts.append((x, y))
    a(f'<path d="{path(pts)}" fill="none" stroke="var(--hero-line-2)" stroke-width="2" stroke-opacity=".9"/>')
    a(f'<line x1="600" y1="170" x2="{W}" y2="170" stroke="var(--hero-warn)" stroke-width="1.4" stroke-dasharray="6 6" stroke-opacity=".8"/>')

    # Flygbild: mark, gator, hus, å och översvämmad yta
    a(f'<rect x="0" y="{MAP_Y}" width="{W}" height="{H - MAP_Y}" fill="var(--hero-ground)"/>')
    river = [(x, MAP_Y + 85 + 34 * math.sin(x / 140) + 10 * math.sin(x / 47)) for x in range(-20, W + 41, 40)]
    flood_top = [(x, y - 26 - 14 * math.exp(-((x - 640) / 170) ** 2) * 2) for x, y in river]
    flood_bot = [(x, y + 24 + 12 * math.exp(-((x - 640) / 170) ** 2) * 2) for x, y in river]
    # Gator
    for x in range(30, W, 150):
        a(f'<line x1="{x + 20}" y1="{MAP_Y}" x2="{x - 10}" y2="{H}" stroke="var(--hero-street)" stroke-width="5"/>')
    for y in (MAP_Y + 30, MAP_Y + 140):
        a(f'<line x1="0" y1="{y}" x2="{W}" y2="{y + 6}" stroke="var(--hero-street)" stroke-width="5"/>')
    # Hus, utom i ån
    for _ in range(240):
        x, y = random.uniform(0, W), random.uniform(MAP_Y + 6, H - 6)
        ry = MAP_Y + 85 + 34 * math.sin(x / 140) + 10 * math.sin(x / 47)
        if abs(y - ry) < 22:
            continue
        w, h = random.uniform(10, 18), random.uniform(8, 13)
        a(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="1.5" fill="var(--hero-house)" transform="rotate({random.uniform(-8, 8):.0f} {x:.0f} {y:.0f})"/>')
    # Översvämmad yta (halvgenomskinlig) och riskzon (streckad)
    flood = path(flood_top) + " L" + " L".join(f"{x:.0f} {y:.0f}" for x, y in reversed(flood_bot)) + " Z"
    a(f'<path d="{flood}" fill="var(--hero-water)" fill-opacity=".45"/>')
    river_d = path([(x, y - 9) for x, y in river]) + " L" + " L".join(f"{x:.0f} {y + 9:.0f}" for x, y in reversed(river)) + " Z"
    a(f'<path d="{river_d}" fill="var(--hero-water)"/>')
    zon = f"M470 {MAP_Y + 18} C560 {MAP_Y + 4} 700 {MAP_Y + 10} 800 {MAP_Y + 40} L780 {MAP_Y + 150} C680 {MAP_Y + 162} 560 {MAP_Y + 150} 460 {MAP_Y + 130} Z"
    a(f'<path d="{zon}" fill="url(#hg-hatch)" stroke="var(--hero-warn)" stroke-width="1.6" stroke-dasharray="7 5"/>')
    # Skugga bakom texten till vänster, så att den alltid går att läsa
    a('<linearGradient id="hg-scrim" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="var(--hero-bg)" stop-opacity=".92"/>'
      '<stop offset=".45" stop-color="var(--hero-bg)" stop-opacity=".75"/><stop offset=".62" stop-color="var(--hero-bg)" stop-opacity="0"/></linearGradient>')
    a(f'<rect x="0" y="0" width="{W}" height="{MAP_Y + 40}" fill="url(#hg-scrim)"/>')
    # Övergång mellan diagram och karta
    a(f'<rect x="0" y="{MAP_Y - 60}" width="{W}" height="60" fill="url(#hg-fade)"/>')
    a('</svg>')
    return "".join(ut)


# ---------------------------------------------------------------------------
# Banderoller för flikarna. Alla är 1200 x 240, mörka, med motivet till höger och plats för text till vänster.
BW, BH = 1200, 240


def _start(namn):
    return [f'<svg class="banner-art" viewBox="560 0 640 {BH}" preserveAspectRatio="xMaxYMid meet" aria-hidden="true" focusable="false">',
            f'<defs><linearGradient id="sc-{namn}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="var(--hero-bg)" stop-opacity="1"/>'
            f'<stop offset=".42" stop-color="var(--hero-bg)" stop-opacity=".85"/><stop offset=".6" stop-color="var(--hero-bg)" stop-opacity="0"/></linearGradient></defs>']


def _rutnat(ut, steg=40):
    for x in range(0, BW + 1, steg):
        ut.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{BH}" stroke="var(--hero-grid)"/>')
    for y in range(0, BH + 1, steg):
        ut.append(f'<line x1="0" y1="{y}" x2="{BW}" y2="{y}" stroke="var(--hero-grid)"/>')


def _slut(ut, namn):
    ut.append(f'<rect x="0" y="0" width="{BW}" height="{BH}" fill="url(#sc-{namn})"/></svg>')
    return "".join(ut)


def _txt(x, y, s, size=13, fill="var(--hero-muted)", anchor="start", weight=500):
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'font-family="IBM Plex Sans, system-ui, sans-serif">{esc(s)}</text>')


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def riskmatris():
    """Utbildningen: riskmatris, sannolikhet gånger konsekvens."""
    ut = _start("matris")
    _rutnat(ut)
    nivafarg = ["var(--risk-1)", "var(--risk-2)", "var(--risk-3)", "var(--risk-4)", "var(--risk-5)"]
    x0, y0, c, g = 760, 26, 34, 5
    for r in range(5):
        for k in range(5):
            niva = min(4, (r + k) // 2)
            ut.append(f'<rect x="{x0 + k * (c + g)}" y="{y0 + (4 - r) * (c + g)}" width="{c}" height="{c}" rx="5" fill="{nivafarg[niva]}" fill-opacity=".85"/>')
    for k, r, namn in [(3, 3, "Brand"), (1, 4, "Elavbrott"), (4, 1, "Skred"), (2, 2, "Fallolycka")]:
        cx, cy = x0 + k * (c + g) + c / 2, y0 + (4 - r) * (c + g) + c / 2
        ut.append(f'<circle cx="{cx}" cy="{cy}" r="8" fill="none" stroke="var(--hero-fg)" stroke-width="2"/>')
        ut.append(_txt(cx + 14 if k < 3 else cx - 14, cy + 4, namn, 12, "var(--hero-fg)", "start" if k < 3 else "end"))
    ut.append(_txt(x0 + 2.5 * (c + g), y0 + 5 * (c + g) + 16, "Konsekvens →", 12, anchor="middle"))
    ut.append(f'<text x="{x0 - 14}" y="{y0 + 2.5 * (c + g)}" fill="var(--hero-muted)" font-size="12" text-anchor="middle" '
              f'transform="rotate(-90 {x0 - 14} {y0 + 2.5 * (c + g)})" font-family="IBM Plex Sans, system-ui, sans-serif">Sannolikhet →</text>')
    # Pil som visar riskreducering
    ut.append(f'<path d="M{x0 + 3.5 * (c + g)} {y0 + 1.5 * (c + g)} C{x0 + 3.5 * (c + g) - 40} {y0 + 2 * (c + g)} {x0 + 2 * (c + g)} {y0 + 3 * (c + g)} '
              f'{x0 + 1.6 * (c + g)} {y0 + 3.4 * (c + g)}" fill="none" stroke="var(--hero-line)" stroke-width="2" stroke-dasharray="5 5"/>')
    ut.append(_txt(985, 150, "Åtgärder", 12, "var(--hero-line)", "start"))
    ut.append(_txt(985, 166, "sänker risken", 12, "var(--hero-line)", "start"))
    return _slut(ut, "matris")


def tidslinje(kalender):
    """Kurskalender: kursperioder och träffar ur kalenderfilen."""
    ut = _start("tid")
    _rutnat(ut)
    ev = (kalender or {}).get("handelser") or []
    if not ev:
        return _slut(ut, "tid")
    import datetime as dt
    dag = lambda s: dt.date.fromisoformat(s[:10])
    d0 = min(dag(e["start"]) for e in ev).replace(day=1)
    d1 = max(dag(e["start"]) for e in ev)
    x0, x1 = 620, 1170
    span = max(1, (d1 - d0).days)
    X = lambda d: x0 + (d - d0).days / span * (x1 - x0)
    # månadsmarkeringar
    m = d0
    while m <= d1:
        x = X(m)
        ut.append(f'<line x1="{x:.0f}" y1="22" x2="{x:.0f}" y2="{BH - 30}" stroke="var(--hero-grid)" stroke-width="2"/>')
        ut.append(_txt(x + 4, BH - 14, ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"][m.month - 1], 11))
        m = (m.replace(day=28) + dt.timedelta(days=5)).replace(day=1)
    koder = sorted({e["kod"] for e in ev if e["kod"]}, key=lambda k: min(e["start"] for e in ev if e["kod"] == k))
    rad = (BH - 70) / max(1, len(koder))
    for i, k in enumerate(koder):
        es = [e for e in ev if e["kod"] == k]
        a_, b_ = min(dag(e["start"]) for e in es), max(dag(e["start"]) for e in es)
        y = 30 + i * rad + rad / 2
        ut.append(f'<rect x="{X(a_):.0f}" y="{y - 3:.0f}" width="{max(6, X(b_) - X(a_)):.0f}" height="6" rx="3" fill="var(--hero-line)" fill-opacity=".35"/>')
        for e in es:
            campus = "sal " in (e.get("plats") or "").lower() or "universitet" in (e.get("plats") or "").lower()
            fill = "var(--hero-warn)" if e.get("uppgift") else ("var(--hero-line)" if campus else "var(--hero-line-2)")
            ut.append(f'<circle cx="{X(dag(e["start"])):.0f}" cy="{y:.0f}" r="{5 if campus else 4}" fill="{fill}"/>')
    # idag
    idag = dt.date.today()
    if d0 <= idag <= d1:
        ut.append(f'<line x1="{X(idag):.0f}" y1="26" x2="{X(idag):.0f}" y2="{BH - 30}" stroke="var(--hero-fg)" stroke-width="1.5" stroke-dasharray="3 4"/>')
        ut.append(_txt(X(idag) + 6, BH - 34, "idag", 11, "var(--hero-fg)"))
    for i, (f, t) in enumerate([("var(--hero-line)", "Campus"), ("var(--hero-line-2)", "Distans"), ("var(--hero-warn)", "Inlämning")]):
        ut.append(f'<circle cx="{x0 + i * 100}" cy="12" r="4" fill="{f}"/>' + _txt(x0 + 10 + i * 100, 16, t, 11))
    return _slut(ut, "tid")


def natverk():
    """Yrkesroller: samverkan mellan aktörerna i krisberedskapen."""
    ut = _start("nat")
    noder = [("Kommun", 930, 120, 30), ("Region", 1080, 60, 22), ("Länsstyrelse", 1090, 180, 24), ("Myndighet", 790, 50, 22),
             ("Försvarsmakten", 770, 190, 20), ("Näringsliv", 1150, 128, 16), ("Frivilliga", 660, 118, 16)]
    kanter = [(0, 1), (0, 2), (0, 3), (0, 4), (0, 6), (1, 2), (1, 5), (2, 4), (2, 5), (3, 6), (3, 1), (4, 6)]
    for i, j in kanter:
        a_, b_ = noder[i], noder[j]
        ut.append(f'<line x1="{a_[1]}" y1="{a_[2]}" x2="{b_[1]}" y2="{b_[2]}" stroke="var(--hero-line)" stroke-opacity=".35" stroke-width="1.5"/>')
    for n, x, y, r in noder:
        ut.append(f'<circle cx="{x}" cy="{y}" r="{r + 10}" fill="var(--hero-line)" fill-opacity=".08"/>')
        ut.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="var(--hero-bg)" stroke="var(--hero-line)" stroke-width="2"/>')
        ut.append(_txt(x, y + r + 18, n, 12, "var(--hero-fg)", "middle"))
    ut.append(f'<circle cx="930" cy="120" r="9" fill="var(--hero-warn)"/>')
    return _slut(ut, "nat")


LAN = {  # ungefärliga mittpunkter (lat, lon)
    "Stockholms län": (59.4, 18.2), "Uppsala län": (60.1, 17.6), "Södermanlands län": (59.1, 16.6), "Östergötlands län": (58.4, 15.6),
    "Jönköpings län": (57.6, 14.4), "Kronobergs län": (56.8, 14.6), "Kalmar län": (57.3, 16.2), "Gotlands län": (57.5, 18.5),
    "Blekinge län": (56.2, 15.3), "Skåne län": (55.9, 13.5), "Hallands län": (56.9, 12.7), "Västra Götalands län": (58.2, 12.4),
    "Värmlands län": (59.8, 13.2), "Örebro län": (59.4, 15.0), "Västmanlands län": (59.8, 16.2), "Dalarnas län": (61.0, 14.4),
    "Gävleborgs län": (61.5, 16.4), "Västernorrlands län": (63.0, 17.4), "Jämtlands län": (63.2, 14.0), "Västerbottens län": (64.8, 17.8),
    "Norrbottens län": (66.9, 20.0),
}


def karta(annonser):
    """Jobbannonser: punktkarta över Sverige, cirklar per län efter antal annonser."""
    import math
    ut = _start("karta")
    k = 15.5
    X = lambda lon: 860 + (lon - 15.5) * k * 0.5 * 2
    Y = lambda lat: 10 + (69.3 - lat) * k
    # Prickraster som formar landet: punkter nära någon länsmittpunkt
    kontur = [(55.4, 13.0), (55.6, 14.2), (56.1, 14.7), (56.2, 15.9), (56.7, 16.4), (57.3, 16.6), (57.9, 16.7), (58.6, 16.9),
              (59.0, 17.6), (59.3, 18.6), (59.8, 18.9), (60.4, 18.4), (60.9, 17.3), (61.7, 17.2), (62.4, 17.5), (62.9, 18.3), (63.5, 19.6),
              (64.0, 20.6), (64.7, 21.3), (65.3, 21.6), (65.7, 22.4), (65.8, 23.6), (66.6, 23.7), (67.5, 23.4), (68.3, 22.5), (68.9, 21.0),
              (68.4, 19.0), (68.0, 18.0), (67.2, 16.6), (66.4, 15.6), (65.6, 14.6), (64.8, 13.9), (64.0, 13.4), (63.2, 12.4), (62.4, 12.3),
              (61.6, 12.6), (61.0, 12.6), (60.3, 12.6), (59.6, 11.9), (59.0, 11.3), (58.4, 11.5), (57.7, 11.9), (57.0, 12.3), (56.5, 12.9),
              (55.9, 12.8), (57.4, 18.4), (57.7, 18.8), (57.1, 18.2)]
    pts = list(LAN.values()) + kontur + [(66.5, 19.5), (67.4, 20.5), (65.5, 18.0), (64.2, 16.5), (63.0, 15.5), (62.2, 14.5), (61.0, 15.0),
                                         (60.2, 15.0), (58.8, 14.0), (57.0, 13.8), (56.5, 14.0), (66.0, 21.5), (64.5, 19.0)]
    lat = 55.3
    while lat < 69.2:
        lon = 10.9
        while lon < 24.2:
            d = min(math.hypot(lat - a, (lon - b) * 0.5) for a, b in pts)
            if d < 0.5:
                ut.append(f'<circle cx="{X(lon):.0f}" cy="{Y(lat):.0f}" r="1.5" fill="var(--hero-muted)" fill-opacity=".38"/>')
            lon += 0.36
        lat += 0.3
    antal = {}
    for a in annonser:
        antal[a["lan"]] = antal.get(a["lan"], 0) + 1
    mx = max(antal.values() or [1])
    for namn, (la, lo) in LAN.items():
        n = antal.get(namn, 0)
        if not n:
            continue
        r = 3 + 18 * math.sqrt(n / mx)
        ut.append(f'<circle cx="{X(lo):.0f}" cy="{Y(la):.0f}" r="{r:.1f}" fill="var(--hero-warn)" fill-opacity=".55" stroke="var(--hero-warn)" stroke-width="1.2"/>')
    topp = sorted(antal.items(), key=lambda x: -x[1])[:3]
    for i, (namn, n) in enumerate(topp):
        ut.append(_txt(1010, 160 + i * 20, f"{namn.replace(' län', '')}  {n}", 12, "var(--hero-fg)"))
    ut.append(_txt(1010, 140, "Flest annonser", 11))
    return _slut(ut, "karta")


IKON = {  # enkla linjeikoner, 24 x 24
    "brand": "M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-3 2-4 2-7 1 1 2 2 2 4 1-2 1-5 1-7z",
    "el": "M13 2 5 14h6l-1 8 8-12h-6z",
    "skydd": "M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z",
    "trygg": "M3 11l9-7 9 7M5 10v10h14V10M10 20v-5h4v5",
    "cyber": "M4 6h16v10H4zM9 20h6M12 16v4M8 10l2 2-2 2M13 14h3",
    "vatten": "M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z",
    "kemi": "M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3M7 15h10",
    "stralning": "M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0M12 10 9 4.8A8 8 0 0 1 15 4.8zM13.7 13l5.2 3a8 8 0 0 1-3 5.2zM10.3 13l-5.2 3a8 8 0 0 0 3 5.2z",
}


def hot(texter):
    """Vad efterfrågas: hot och händelser som annonstexterna nämner, med andel."""
    import re
    ut = _start("hot")
    _rutnat(ut, 48)
    n = max(1, len(texter))
    grupper = [("skydd", "Höjd beredskap", r"\bkrig|höjd beredskap|väpnat angrepp|totalförsvar"),
               ("trygg", "Otrygghet, brott", r"brottslighet|kriminalitet|otrygghet|brottsförebygg"),
               ("brand", "Brand", r"\bbrand|bränder"),
               ("el", "Elavbrott, infrastruktur", r"elavbrott|strömavbrott|samhällsviktig verksamhet|kritisk infrastruktur"),
               ("cyber", "Cyberangrepp", r"cyber|it-attack|it-incident|dataintrång"),
               ("vatten", "Vatten, klimat", r"dricksvatten|vattenförsörjning|översvämning|klimatförändring|skyfall")]
    for i, (ik, namn, rx) in enumerate(grupper):
        andel = sum(1 for t in texter.values() if re.search(rx, t)) / n
        col, row = i % 3, i // 3
        x, y = 640 + col * 185, 34 + row * 100
        ut.append(f'<rect x="{x}" y="{y}" width="170" height="84" rx="12" fill="var(--hero-fg)" fill-opacity=".04" stroke="var(--hero-line)" stroke-opacity=".25"/>')
        ut.append(f'<g transform="translate({x + 14} {y + 14}) scale(1.25)" fill="none" stroke="var(--hero-warn)" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="{IKON[ik]}"/></g>')
        ut.append(_txt(x + 156, y + 36, f"{round(andel * 100)} %", 22, "var(--hero-fg)", "end", 300))
        ut.append(_txt(x + 14, y + 68, namn, 12))
    return _slut(ut, "hot")


def dataflode():
    """Om datan: från Arbetsförmedlingens API till sidan."""
    ut = _start("flode")
    _rutnat(ut)
    steg = [("API", "Arbetsförmedlingen"), ("Urval", "40 sökord, filter"), ("Matchning", "kurser och krav"), ("Tester", "validering"), ("Sidan", "varje måndag")]
    for i, (t, s) in enumerate(steg):
        x = 640 + i * 112
        ut.append(f'<rect x="{x}" y="88" width="92" height="64" rx="10" fill="var(--hero-bg)" stroke="var(--hero-line)" stroke-width="1.6"/>')
        ut.append(_txt(x + 46, 116, t, 14, "var(--hero-fg)", "middle", 600))
        ut.append(_txt(x + 46, 136, s, 10, "var(--hero-muted)", "middle", 400))
        if i:
            ut.append(f'<path d="M{x - 18} 120h14m-5-5 5 5-5 5" fill="none" stroke="var(--hero-warn)" stroke-width="1.8"/>')
    ut.append(f'<path d="M1150 156 C1150 210 690 210 686 158" fill="none" stroke="var(--hero-line)" stroke-opacity=".5" stroke-dasharray="4 5" stroke-width="1.5"/>')
    ut.append(_txt(918, 214, "upprepas automatiskt varje vecka", 11, anchor="middle"))
    return _slut(ut, "flode")


def profil():
    """Valbara kurser: spindeldiagram, kompetensprofil med bara obligatoriska kurser och med valbara."""
    import kompetenser
    ut = _start("profil")
    _rutnat(ut)
    K = kompetenser.KOMPETENSER
    cx, cy, R = 905, 122, 92
    n = len(K)
    vinkel = lambda i: -math.pi / 2 + 2 * math.pi * i / n
    P = lambda i, r: (cx + r * math.cos(vinkel(i)), cy + r * math.sin(vinkel(i)))
    for niva in (1, 2, 3):
        ring = " ".join(f"{x:.1f},{y:.1f}" for x, y in (P(i, R * niva / 3) for i in range(n)))
        ut.append(f'<polygon points="{ring}" fill="none" stroke="var(--hero-line)" stroke-opacity=".18"/>')
    korta = {"rsa": "RSA", "kontinuitet": "Kontinuitet", "utredning": "Olycksutredning", "larande": "Lärande",
             "implementering": "Åtgärder", "kommunikation": "Riskkommunikation", "klimat": "Klimat", "hallbarhet": "Hållbarhet"}
    for i, k in enumerate(K):
        x, y = P(i, R)
        ut.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="var(--hero-line)" stroke-opacity=".18"/>')
        lx, ly = P(i, R + 16)
        anchor = "middle" if abs(lx - cx) < 10 else ("start" if lx > cx else "end")
        ut.append(_txt(f"{lx:.0f}", f"{ly + 4:.0f}", korta[k[0]], 11, anchor=anchor))
    for idx, farg, op, bredd in ((4, "var(--hero-warn)", .28, 2.2), (3, "var(--hero-line)", .22, 1.8)):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (P(i, R * K[i][idx] / 3) for i in range(n)))
        ut.append(f'<polygon points="{pts}" fill="{farg}" fill-opacity="{op}" stroke="{farg}" stroke-width="{bredd}" stroke-linejoin="round"/>')
    ut.append(f'<rect x="1040" y="176" width="12" height="4" rx="2" fill="var(--hero-line)"/>' + _txt(1058, 182, "Bara obligatoriska", 11))
    ut.append(f'<rect x="1040" y="196" width="12" height="4" rx="2" fill="var(--hero-warn)"/>' + _txt(1058, 202, "Med valbara kurser", 11, "var(--hero-fg)"))
    return _slut(ut, "profil")


def alla(data, texter):
    """Alla illustrationer, nyckel = namnet i mallens <!--GRAFIK:namn-->."""
    return {"hero": hero(), "matris": riskmatris(), "tidslinje": tidslinje(data.get("kalender")), "natverk": natverk(),
            "karta": karta(data.get("annonser", [])), "hot": hot(texter), "flode": dataflode(), "profil": profil()}
