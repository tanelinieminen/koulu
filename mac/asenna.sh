#!/bin/bash
# Asentaa koulusivun automaattisen päivityksen tälle Macille.
# Aja kerran:  bash mac/asenna.sh
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

APP="$HOME/Library/Application Support/koulu"
REPO="$APP/repo"
PLIST="$HOME/Library/LaunchAgents/fi.koulu.paivita.plist"
REPO_URL="${REPO_URL:-https://github.com/tanelinieminen/koulu.git}"

echo "1/5 Tarkistetaan työkalut"
command -v python3 >/dev/null || { echo "python3 puuttuu (asenna: xcode-select --install)"; exit 1; }
command -v npm >/dev/null || { echo "Node.js puuttuu (asenna: brew install node)"; exit 1; }
command -v git >/dev/null || { echo "git puuttuu"; exit 1; }

echo "2/5 Haetaan koodi ja asennetaan riippuvuudet"
mkdir -p "$APP" "$HOME/Library/Logs"
if [ -d "$REPO/.git" ]; then git -C "$REPO" pull -q --ff-only; else git clone -q "$REPO_URL" "$REPO"; fi
[ -x "$APP/venv/bin/python" ] || python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install -q --upgrade requests beautifulsoup4
(cd "$APP" && npm install -s --no-audit --no-fund staticrypt@3 >/dev/null)

echo "3/5 Tunnukset Macin avainnippuun (Keychain)"
tallenna() {
  local nimi="$1" kehote="$2"
  if security find-generic-password -s koulu -a "$nimi" >/dev/null 2>&1; then
    read -r -p "$kehote on jo tallennettu. Vaihdetaanko? (k/E) " v
    [ "$v" = "k" ] || return 0
  fi
  echo "$kehote (kirjoitetaan kahdesti, ei näy ruudulla):"
  security add-generic-password -U -s koulu -a "$nimi" -w
}
tallenna WILMA_USER "Wilma-käyttäjätunnus"
tallenna WILMA_PASSWORD "Wilma-salasana"
tallenna SIVUN_SALASANA "Sivun salasana (lapset avaavat sivun tällä)"

echo "4/5 Testiajo (haku Wilmasta + julkaisu)"
git -C "$REPO" config core.fileMode false
if bash "$REPO/mac/paivita.sh" --nyt; then
  tail -n 5 "$HOME/Library/Logs/koulu.log"
else
  echo "Testiajo epäonnistui. Loki:"; tail -n 20 "$HOME/Library/Logs/koulu.log"; exit 1
fi

echo "5/5 Ajastus"
bash "$REPO/mac/ajastus.sh"
echo "Valmis. Sivu: https://tanelinieminen.github.io/koulu/  – loki: ~/Library/Logs/koulu.log"
