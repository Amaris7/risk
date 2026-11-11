#!/bin/bash
# Kör alla tester: Python (hämtning, bygge, validering, säkerhet), JavaScript (logik) och Playwright (webbläsare).
# Kör:  ./testa.sh            (alla)
#       ./testa.sh snabb      (hoppar över webbläsartesterna)
set -euo pipefail
cd "$(dirname "$0")"
PY="$(command -v python3 || echo /usr/bin/python3)"

echo "== Python: hämtning, bygge, validering och säkerhet"
"$PY" -m unittest discover -s tester -p "test_*.py"

if command -v node >/dev/null; then
  echo "== JavaScript: sidans logik"
  node --test tester/
else
  echo "!! Node saknas, hoppar över JavaScript-testerna"
fi

if [ "${1:-}" = "snabb" ]; then
  echo "== Hoppar över webbläsartesterna"
elif [ -d node_modules/@playwright/test ]; then
  echo "== Playwright: webbläsartester (dator och mobil)"
  npx playwright test
else
  echo "!! Playwright är inte installerat. Kör en gång:  npm install && npx playwright install chromium"
fi
echo "== Alla tester gick igenom"
