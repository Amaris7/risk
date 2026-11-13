# Karriär i riskhantering

En webbsida som matchar Karlstads universitets masterprogram **Riskhantering i samhället (SARHS)** mot jobbannonser i hela Sverige. Annonserna kommer från Arbetsförmedlingens öppna API:er (JobTech). Ingen API-nyckel behövs.

## Innehåll

| Fil | Vad den gör |
|---|---|
| `index.html` | Den färdiga sidan, en fristående fil som kan läggas på vilket webbhotell som helst |
| `uppdatera.sh` | Hämtar nya annonser och bygger om `index.html` i ett steg |
| `skript/hamta_annonser.py` | Hämtar och filtrerar annonser. Sökord, filter, arbetsområden och kurskoppling står överst i filen |
| `skript/bygg_sida.py` | Lägger in datan i mallen och skriver `index.html` |
| `skript/mall.html` | Sidans utseende, texter och flikar. `__DATA__` ersätts med annonsdatan |
| `skript/statistik.py` | **All statistik på sidan** (antal, andelar, topplistor, yrkesroller). Räknas i Python vid bygget. Kör `python3 skript/statistik.py` för att se rapporten |
| `skript/kompetenser.py` | Kompetenser och valbara kurser, andelar per grupp |
| `data/statistik.md`, `data/statistik.json` | Granskningsbar rapport med varje siffra som sidan visar, med antal och nämnare |
| `skript/logik.js` | Sidans rena logik (sökning, escaping, kalender). Bäddas in i sidan vid bygget och testas separat |
| `data/annonser.json`, `data/annonser.csv` | Senast hämtade annonser (CSV går att öppna i Excel) |
| `data/annonstext.json` | Hela annonstexterna (gemener), som sidan laddar först när någon söker. Måste publiceras bredvid `index.html` i mappen `data/` |
| `data/kurskalender.ics` | Kurskalendern som visas under fliken Kurskalender. `uppdatera.sh` kopierar in den senaste `.ics`-filen från `~/rhad-kalender` om den finns |
| `.github/workflows/veckouppdatering.yml` | Veckovis automatisk uppdatering och publicering på GitHub Pages |
| `schema-mac/` | Alternativ: veckovis uppdatering på din egen Mac |

Allt kräver bara Python 3, inga extra paket.

## Uppdatera för hand

```bash
./uppdatera.sh
```

Det tar ungefär en minut. Om API:et inte svarar (färre än 200 annonser) avbryts körningen och den gamla datan behålls.

## Automatisk veckouppdatering

### Alternativ A: GitHub (rekommenderas, helt fristående)

Körs i GitHub:s moln varje måndag morgon, även när din dator är avstängd, och publicerar sidan gratis på en egen adress.

1. Skapa ett konto på github.com om du inte har ett.
2. Skapa ett nytt **publikt** repo, t.ex. `riskhantering-jobb` (GitHub Pages är gratis för publika repon).
3. Ladda upp hela mappen. Antingen dra in filerna under *Add file → Upload files* (se till att mappen `.github` följer med), eller kör i Terminal:
   ```bash
   git init && git add . && git commit -m "Första versionen" && git branch -M main
   git remote add origin https://github.com/DITT-NAMN/riskhantering-jobb.git
   git push -u origin main
   ```
4. I repot: **Settings → Pages → Source: GitHub Actions**.
5. Gå till fliken **Actions → Veckouppdatering av jobbannonser → Run workflow** för att köra första gången.

Sidan finns sedan på `https://DITT-NAMN.github.io/riskhantering-jobb/`. Vill du ändra dag eller tid ändrar du `cron`-raden i workflow-filen (tiden är i UTC).

### Alternativ B: Din Mac

```bash
./schema-mac/installera.sh
```

Kör `uppdatera.sh` måndagar 08:00 när datorn är igång. Loggen hamnar i `logg/uppdatering.log`. Den nya `index.html` måste du sedan själv ladda upp där sidan ligger. Ta bort schemat med `./schema-mac/avinstallera.sh`.

Om mappen ligger i Dokument, Skrivbord eller Hämtade filer kan macOS blockera körningen. Lägg då projektet direkt i din hemmapp, eller ge `/bin/bash` åtkomst under *Systeminställningar → Integritet och säkerhet → Full skivåtkomst*.

## Kurskalendern

Byt kalender genom att lägga en ny `.ics`-fil i `~/rhad-kalender` (den nyaste används) eller direkt som `data/kurskalender.ics`, och kör `python3 skript/bygg_sida.py`. Personliga Zoom-länkar tas bort från sidan eftersom den kan vara publik. Vill du behålla dem, sätt `DOLJ_ZOOMLANKAR = False` i `skript/bygg_sida.py`. På GitHub används den kalenderfil som ligger i repot, så ladda upp en ny `data/kurskalender.ics` när kalendern ändras.

## Tester

`./testa.sh` kör alla tester. `./uppdatera.sh` och GitHub-workflowen kör dem automatiskt efter bygget. Går ett test sönder på GitHub sparas ingen ny data och sidan publiceras inte, så den gamla versionen ligger kvar.

| Del | Verktyg | Vad som testas |
|---|---|---|
| `tester/test_hamta.py` | Python `unittest` | Urval och klassning av annonser, utsortering av forskartjänster, krav och erfarenhet (med exempel från riktiga annonser), dubbletter, säkra länkar, sparade filer |
| `tester/test_bygg.py` | Python `unittest` | Kalenderläsning (Canvas-format, tidszoner, Zoom-länkar och namn tas bort), säker inbäddning av data, CSP |
| `tester/test_validering.py` | Python `unittest` | Validering av den riktiga datan och `index.html`: fält, datum, länkar, kalender, hemligheter, escaping |
| `tester/test_statistik.py` | Python `unittest` | Avrundning, rollindelning, klimatgrupperna, att varje siffra går att räkna om från datan, och att sökordsräknaren i webbläsaren ger exakt samma antal som Python |
| `tester/logik.test.cjs` | Node `node:test` | Sidans logik i `skript/logik.js`: sökning, escaping, kalender, länkar |
| `tester/webblasare/` | Playwright | Riktig webbläsare i dator- och mobilbredd: flikar och Mer-meny, filter, sökord, kalender, XSS-försök |

Första gången på en ny dator: `npm install && npx playwright install chromium`. Snabb körning utan webbläsare: `./testa.sh snabb`.

## Hur annonserna väljs ut och klassas

### Urval vid hämtningen (`skript/hamta_annonser.py`)

- **Rubriken** måste innehålla ett kärnord (`CORE`, t.ex. beredskap, kris, säkerhet, risk, klimat) och inget ord från `EXCLUDE` (IT-säkerhet, vakter, vård, säljare, säkerhetsarkitekter m.m.). "kris" räknas inte i ortnamn som Kristianstad och Kristinehamn.
- **Tjänster som programmet inte leder till** sorteras bort (`kraver_annan_utbildning`):
  - postdoktor och (biträdande) universitetslektor, som alltid kräver doktorsexamen,
  - forskare och forskningssekreterare när texten *kräver* doktorsexamen eller forskarutbildning (är den bara meriterande får annonsen vara kvar),
  - doktorandtjänster vars rubrik inte nämner risk, säkerhet, kris, beredskap eller civilt försvar.
- **Kopplingen till utbildningen** måste vara tillräckligt stark: antal kursområden som texten träffar, plus 2 om rubriken är en tydlig riskroll, ska vara minst 3.

### Krav och erfarenhet

- **Krav** (`KRAV`) plockas ur annonstexten. Meningar som säger meriterande, önskvärt, gärna m.m. räknas inte, och inte heller listor under en rubrik som "Meriterande:" eller "Vi ser gärna att du har:". Rubriken står ofta sist på en lång rad i Platsbankens text, så bara radens sista mening kan vara en rubrik.
- **Erfarenhet** (`hitta_erfarenheter`) är fraser som "Minst 3 års erfarenhet av …" ur texten. **Texten avgör:** om arbetsgivaren har kryssat i Arbetsförmedlingens ruta "erfarenhet krävs" men texten inte ställer något erfarenhetskrav räknas annonsen som *Kräver inte erfarenhet*, och kortet visar en anmärkning om rutan (fältet `erf_ruta`). Annonser som vänder sig till nyexaminerade får inga erfarenhetskrav. Uppgifter som "75 års erfarenhet" handlar om arbetsgivaren och räknas inte.
- **Passar nyexaminerade** betyder att annonsen uttryckligen vänder sig till nyexaminerade, juniorer eller traineer (`NYEXAD`).

### Klimatgrupper (`skript/kompetenser.py`, `klimattyp`)

| Grupp | Regel |
|---|---|
| **Klimatrisker och naturolyckor** | Rubriken nämner klimatanpassning, klimatrisk, klimatförändring, översvämning, skred, skyfall, naturolycka, extremväder, dagvatten m.m., eller texten nämner sådana risker minst två gånger. Har rubriken bara ordet klimat, energi eller utsläpp räknas inte "klimatförändring" i texten, eftersom den också står i annonser om att minska utsläpp. |
| **Klimatomställning, energi och utsläpp** | Rubriken nämner klimat, energistrateg, utsläpp, fossilfri m.m., men annonsen handlar inte om klimatrisker. |

Orden matchar i början av ord, så "skred" träffar inte "riskreducerande". "Kallt klimat", "arbetsklimat" och "inomhusklimat" räknas inte. Grupperna styr filtret *Klimat* under Jobbannonser, klimatraden på varje yrkesroll och fördelningen mellan rollerna *Klimatanpassning* och *Klimatomställning & energi*. Fliken Valbara kurser räknar bara klimatrisker.

## Ändra innehållet

- **Fler eller andra sökord:** lista `TERMS` i `skript/hamta_annonser.py`.
- **Bort med brus:** lägg till ord i `EXCLUDE`.
- **Hur matchningen räknas:** `COURSES` (kurskoppling) och gränserna för Hög/Medel längre ned i filen.
- **Utseende och texter:** `skript/mall.html`. Färgerna står samlade högst upp i `:root`.
- **Yrkesrollerna** definieras i `skript/statistik.py` (`ROLLER`), klimatgrupperna och kompetenserna i `skript/kompetenser.py`.

Kör `./uppdatera.sh` efter ändringar i hämtningen, eller bara `python3 skript/bygg_sida.py` efter ändringar i mallen.
