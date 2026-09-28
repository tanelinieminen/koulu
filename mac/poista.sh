#!/bin/bash
# Poistaa automaattisen päivityksen ja tallennetut tunnukset tältä Macilta.
launchctl bootout "gui/$(id -u)/fi.koulu.paivita" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/fi.koulu.paivita.plist"
for n in WILMA_USER WILMA_PASSWORD SIVUN_SALASANA; do security delete-generic-password -s koulu -a "$n" >/dev/null 2>&1 || true; done
rm -rf "$HOME/Library/Application Support/koulu"
echo "Poistettu. (Sivu jää GitHubiin viimeisimpään tilaan.)"
