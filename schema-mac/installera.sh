#!/bin/bash
# Lägger in en veckovis körning av uppdatera.sh på din Mac (måndagar kl. 08:00).
# Körs bara när datorn är igång; missad körning tas igen när datorn vaknar.
# Avinstallera:  ./schema-mac/avinstallera.sh
set -euo pipefail
PROJ="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="se.riskhantering.veckouppdatering"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$PROJ/logg"
chmod +x "$PROJ/uppdatera.sh"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$PROJ/uppdatera.sh</string></array>
  <key>StartCalendarInterval</key>
  <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
  <key>StandardOutPath</key><string>$PROJ/logg/uppdatering.log</string>
  <key>StandardErrorPath</key><string>$PROJ/logg/uppdatering.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installerat. Körs måndagar 08:00. Logg: $PROJ/logg/uppdatering.log"
echo "Testkör direkt med:  launchctl kickstart gui/$(id -u)/$LABEL"
