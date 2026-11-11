#!/bin/bash
# Hämtar nya annonser och bygger om index.html.
# Kör:  ./uppdatera.sh
set -euo pipefail
cd "$(dirname "$0")"
PY="$(command -v python3 || echo /usr/bin/python3)"
echo "== $(date '+%Y-%m-%d %H:%M') Hämtar annonser"
"$PY" skript/hamta_annonser.py
# Hämta senaste kalenderfilen från ~/rhad-kalender om den finns (bara på din dator)
NY_KAL="$(ls -t "$HOME"/rhad-kalender/*.ics 2>/dev/null | head -1 || true)"
# Kopieras bara in om den är nyare än data/kurskalender.ics, så en nyare fil i projektet aldrig skrivs över
if [ -n "$NY_KAL" ] && [ "$NY_KAL" -nt data/kurskalender.ics ]; then cp "$NY_KAL" data/kurskalender.ics; echo "== Kalender: $(basename "$NY_KAL")"; fi
echo "== Bygger index.html"
"$PY" skript/bygg_sida.py
echo "== Testar"
./testa.sh
