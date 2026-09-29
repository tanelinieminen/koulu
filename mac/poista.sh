#!/bin/bash
# Poistaa automaattisen päivityksen ja tallennetut tunnukset tältä Macilta.
for l in fi.koulu.ajastus fi.koulu.paivita; do
  rm -f "$HOME/Library/LaunchAgents/$l.plist"
  launchctl bootout "gui/$(id -u)/$l" 2>/dev/null || true
done
for n in WILMA_USER WILMA_PASSWORD SIVUN_SALASANA; do security delete-generic-password -s koulu -a "$n" >/dev/null 2>&1 || true; done
rm -rf "$HOME/Library/Application Support/koulu"
echo "Poistettu. (Sivu jää GitHubiin viimeisimpään tilaan.)"
