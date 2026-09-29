#!/bin/bash
# Asettaa ajastuksen: joka tunti klo x.05 (skripti ajaa klo 6–22, yöllä ohittaa).
# Kalenteriajastus ajaa väliin jääneen päivityksen heti, kun kone herää unesta.
set -euo pipefail
REPO="$HOME/Library/Application Support/koulu/repo"
AGENTS="$HOME/Library/LaunchAgents"
PLIST="$AGENTS/fi.koulu.ajastus.plist"
OLD="$AGENTS/fi.koulu.paivita.plist"
mkdir -p "$AGENTS"
cat >"$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>fi.koulu.ajastus</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$REPO/mac/paivita.sh</string></array>
  <key>StartCalendarInterval</key><dict><key>Minute</key><integer>5</integer></dict>
  <key>RunAtLoad</key><true/>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/koulu.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/fi.koulu.ajastus" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Ajastus päällä: joka tunti klo x.05 (6–22) ja heti koneen herätessä."
# Vanha tunnin välein -ajastus pois (viimeisenä, koska se voi pysäyttää tämän ajon)
if [ -f "$OLD" ]; then
  rm -f "$OLD"
  launchctl bootout "gui/$(id -u)/fi.koulu.paivita" 2>/dev/null || true
fi
