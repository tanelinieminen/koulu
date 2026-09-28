# Koulu – läksyt ja kokeet Wilmasta

Sivu hakee Jyväskylän Wilmasta tunnin välein (n. klo 6–22) molempien lasten
- **kaikki tulevat kokeet** (≤ 3 pv päässä olevat korostettuna)
- **läksyt 3 viimeiseltä koulupäivältä** (ma–pe)

Sivu on salattu salasanalla. Lasten tietoja ei tallenneta repoon eikä tulosteta lokeihin.

## Käyttöönotto (kerran, n. 5 min)

1. Luo GitHubiin uusi repo, esim. `koulu`, ja lataa nämä tiedostot sinne.
2. **Settings → Secrets and variables → Actions → New repository secret**, lisää kolme:
   - `WILMA_USER` – huoltajan Wilma-tunnus
   - `WILMA_PASSWORD` – Wilma-salasana
   - `SIVUN_SALASANA` – salasana, jolla lapset avaavat sivun
3. **Settings → Pages → Source: GitHub Actions**
4. **Actions → Päivitä koulusivu → Run workflow** (ensimmäinen ajo käsin).
5. Sivu: `https://<käyttäjä>.github.io/koulu/`. Avaa se kerran omalla puhelimella
   salasanalla ja ruksi "Muista minut".
6. Sivun alareunaan ilmestyvät napit **Jaa suora linkki: Venla / Väinö**. Lähetä linkki
   lapselle (esim. WhatsAppilla). Linkki avaa sivun suoraan ilman salasanaa ja oikealle
   lapselle – lapsi lisää sen kotinäytölle. Linkki toimii kuin avain: älä jaa sitä muille.
   Jos vaihdat `SIVUN_SALASANA`:n, vanhat linkit lakkaavat toimimasta.

## Hyvä tietää

- Jos ajo epäonnistuu (esim. Wilman salasana vaihtui), GitHub lähettää sähköpostin
  ja sivulla näkyy edellinen versio. Päivitysaika muuttuu oranssiksi, jos tieto on yli 14 h vanha.
- Julkisessa repossa GitHub pysäyttää ajastuksen, jos repoon ei tule muutoksia 60 päivään
  (tulee sähköposti, uudelleenkäynnistys yhdellä klikkauksella). Yksityisessä repossa ei tätä ongelmaa,
  mutta Pages vaatii silloin GitHub Pro -tilin.
- Läksypäivien määrää voi muuttaa: workflowiin `env: LAKSYPAIVAT: "5"`.
- Testaus ilman Wilmaa: `python test/testaa.py && python build_page.py test/data.json build/index.html`
