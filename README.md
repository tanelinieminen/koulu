# Koulu – läksyt ja kokeet Wilmasta

Sivu **https://tanelinieminen.github.io/koulu/** näyttää Venlan ja Väinön
- **kaikki tulevat kokeet** (≤ 3 pv päässä olevat korostettuna)
- **läksyt 5 viimeiseltä koulupäivältä** (ma–pe)
- ison **"Päivitetty …"** -leiman (vihreä = tuore, oranssi = yli 3 h vanha)

## Miten toimii

Wilma estää pilvipalvelimet, joten haku tehdään Macilta:
`mac/paivita.sh` ajetaan automaattisesti joka tunti klo x.05, klo 6–22 (macOS LaunchAgent).
Se hakee tiedot, rakentaa salasanalla salatun sivun ja julkaisee sen `gh-pages`-haaraan.
Kun Mac on kiinni tai unessa, sivu näyttää viimeisimmän haun; väliin jäänyt ajo tehdään heti kun kone herää.

Tunnukset ovat vain Macin avainnipussa (Keychain), eivät GitHubissa. Lasten tietoja ei tallenneta repoon.

## Asennus (kerran)

```
git clone https://github.com/tanelinieminen/koulu.git ~/koulu-asennus
bash ~/koulu-asennus/mac/asenna.sh
```
Asennin kysyy Wilma-tunnuksen, Wilma-salasanan ja sivun salasanan, tekee testiajon ja laittaa ajastuksen päälle.

Sen jälkeen: avaa sivu omalla puhelimella salasanalla, ruksi "Muista minut", ja lähetä sivun
alareunan napeista **Jaa suora linkki: Venla / Väinö** linkit lapsille. Linkki toimii kuin avain.

## Ylläpito

- Loki: `~/Library/Logs/koulu.log`
- Aja heti: `bash ~/Library/Application\ Support/koulu/repo/mac/paivita.sh --nyt`
- Vaihda salasana: aja `asenna.sh` uudelleen (sivun salasanan vaihto mitätöi vanhat linkit)
- Poista kaikki: `bash ~/Library/Application\ Support/koulu/repo/mac/poista.sh`
- Läksypäivien määrä: `LAKSYPAIVAT` (oletus 5) `build_page.py`:ssä
- Testaus ilman Wilmaa: `python test/testaa.py && python build_page.py test/data.json build/index.html`
