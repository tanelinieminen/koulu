#!/bin/bash
# Hakee Wilmasta, rakentaa salatun sivun ja julkaisee sen gh-pages-haaraan.
# Ajetaan automaattisesti tunnin välein (LaunchAgent), klo 6–22.
set -euo pipefail

APP="$HOME/Library/Application Support/koulu"
REPO="$APP/repo"
LOG="$HOME/Library/Logs/koulu.log"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

exec >>"$LOG" 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M') ==="

HOUR=$(date +%H)
if [ "${1:-}" != "--nyt" ] && { [ "$HOUR" -lt 6 ] || [ "$HOUR" -ge 22 ]; }; then
  echo "Yöaika, ohitetaan."; exit 0
fi

kc() { security find-generic-password -s koulu -a "$1" -w; }
export WILMA_URL="https://jyvaskyla.inschool.fi"
export WILMA_USER="$(kc WILMA_USER)"
export WILMA_PASSWORD="$(kc WILMA_PASSWORD)"
SIVUN_SALASANA="$(kc SIVUN_SALASANA)"

cd "$REPO"
git pull -q --ff-only origin main || echo "git pull epäonnistui, jatketaan vanhalla koodilla"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

"$APP/venv/bin/python" wilma.py "$WORK/data.json"
"$APP/venv/bin/python" build_page.py "$WORK/data.json" "$WORK/build/index.html"

SALT=$(printf 'koulu-%s' "$SIVUN_SALASANA" | shasum -a 256 | cut -c1-32)
"$APP/node_modules/.bin/staticrypt" "$WORK/build/index.html" -p "$SIVUN_SALASANA" -s "$SALT" \
  -d "$WORK/site" --short --remember 365 --config false \
  --template-title "Koulu" \
  --template-instructions "Syötä perheen salasana" \
  --template-placeholder "Salasana" \
  --template-button "Avaa" \
  --template-remember "Muista minut tällä laitteella" \
  --template-error "Väärä salasana" \
  --template-color-primary "#2f5d50" \
  --template-color-secondary "#f6f5f1" >/dev/null
touch "$WORK/site/.nojekyll"

# Julkaisu: gh-pages-haarassa on aina vain yksi commit (ei kasvavaa historiaa)
cd "$WORK/site"
git init -q -b gh-pages
git add -A
git -c user.name="koulu-bot" -c user.email="koulu-bot@users.noreply.github.com" commit -q -m "Päivitys $(date '+%Y-%m-%d %H:%M')"
git push -q -f "$(git -C "$REPO" remote get-url origin)" gh-pages
echo "Julkaistu."
