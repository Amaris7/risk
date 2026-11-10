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
| `data/annonser.json`, `data/annonser.csv` | Senast hämtade annonser (CSV går att öppna i Excel) |
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

## Ändra innehållet

- **Fler eller andra sökord:** lista `TERMS` i `skript/hamta_annonser.py`.
- **Bort med brus:** lägg till ord i `EXCLUDE`.
- **Hur matchningen räknas:** `COURSES` (kurskoppling) och gränserna för Hög/Medel längre ned i filen.
- **Utseende och texter:** `skript/mall.html`. Färgerna står samlade högst upp i `:root`.
- **Yrkesrollerna** och kurslistan på sidan definieras i `skript/mall.html` (`ROLES` och `TERMS`).

Kör `./uppdatera.sh` efter ändringar i hämtningen, eller bara `python3 skript/bygg_sida.py` efter ändringar i mallen.
