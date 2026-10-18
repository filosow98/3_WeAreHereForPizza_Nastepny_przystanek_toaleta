# Generator ulotek „Najbliższa toaleta” — plan aplikacji

Stan: 18.10.2026. Plan budowy narzędzia „Następny przystanek: toaleta”: dla każdego
słupka przystankowego generujemy ulotkę do wywieszenia, projektowaną dla
seniorów, ale czytelną dla wszystkich. Na ulotce: odległość do najbliższej
toalety, mapa, czy toaleta jest płatna, czy ma przewijak i czy jest dostępna
dla wózków, godziny otwarcia, identyfikator przystanku, kod QR z nawigacją
pieszą i maskotka — syrenka.

## W skrócie

- **Ulotka działa na trzy sposoby:** mapa na papierze (seniorzy), kod QR
  z nawigacją pieszą w telefonie (kto woli telefon), syrenka i napis „WC”
  (obcokrajowcy).
- **Projektujemy dla seniora, korzystają wszyscy** (decyzja 17.10). Teksty po
  polsku i angielsku. Senior zostaje bohaterem opowieści: jeśli ulotka działa
  dla niego, zadziała dla każdego.
- **Ulotki dla wszystkich przystanków drukują się automatycznie:** jedno
  polecenie daje 18 PDF-ów, po jednym na dzielnicę, ok. 4400 stron A4.
- **Dwa widoki, jedna paczka danych.** Ulotka (dla pasażera) i mapa luk (dla
  urzędu) czytają dane z `app/dane/`.
- **Prawdziwa trasa piesza, nie linia prosta.** Najbliższą toaletę wybieramy
  według długości dojścia chodnikami (OSRM, profil pieszy), a mapa na
  ulotce rysuje trasę po ulicach. Mapa luk liczy tymi samymi odległościami
  pieszymi (próg 600 m = 10 min tempem seniora).
- **Python liczy, przeglądarka rysuje.** Ulotka to HTML + CSS z mapą Leaflet.
  Ten sam szablon służy do podglądu, do druku pojedynczej ulotki i do druku
  wsadowego (Playwright).
- Stronę da się wystawić na GitHub Pages, więc jury może ją otworzyć samo.
  To punkty za wdrożenie.

## Co jest na ulotce

Format **A4 pionowo** (mieści się w ramce rozkładu albo jako laminat na
słupku). Stan wdrożony:

```
┌─────────────────────────────────────────────┐
│ ┌────────┐  NAJBLIŻSZA TOALETA   Przystanek /│
│ │SYRENKA │  Nearest toilet · WC  Stop        │
│ │  WC    │                       Sympatyczna 03
│ └────────┘                       [nr 4225-03]│
├─────────────────────────────────────────────┤
│  ok. 350 m   6 min pieszo                    │
│              approx. 6 min walk              │
│  Inwalidów 3, Biblioteka Publiczna           │
│  toaleta stacjonarna · wejście od ul. …      │
├─────────────────────────────────────────────┤
│  [ MAPA: ● JESTEŚ TUTAJ - - - - 📍WC ]       │
│  [        You are here               ]       │
├─────────────────────────────────────────────┤
│ ┌────────┐┌────────┐┌────────┐   ┌──────┐   │
│ │ ✔ ikona││ ✔ ikona││ ✘ ikona│   │  QR  │   │
│ │BEZPŁAT-││PRZEWI- ││NIE DLA │   │ 4 cm │   │
│ │NA Free ││JAK     ││WÓZKÓW  │   └──────┘   │
│ └────────┘└────────┘└────────┘  Prowadź mnie │
│ 🕒 pon.–pt. 9–19 · sob. 9–15     Navigate me │
│    Mon–Fri 9–19 · Sat 9–15                   │
├─────────────────────────────────────────────┤
│ Dane: dane.um.warszawa.pl, toalety IV 2026   │
│ Błąd na ulotce? Zadzwoń 19115, podaj 4225-03 │
└─────────────────────────────────────────────┘
```

**Dwa języki bez utraty czytelności:** polski duży, angielski pod spodem
mniejszą czcionką (ok. połowa wielkości), szarym, ale nadal z wysokim
kontrastem. Liczby (350 m) i ikony są wspólne dla obu języków, więc nie
dublujemy ich. Angielski w nagłówkach, etykietach i godzinach, nie w adresie.

| Pole | Skąd | Uwagi |
|---|---|---|
| Syrenka + nagłówek PL/EN | stałe | „WC” jest zrozumiałe w każdym języku; opis w sekcji „Maskotka” |
| Nazwa i nr przystanku | `przystanki.json`: `nazwa_zespolu`, `zespol`, `slupek` | ID w formacie `4225-03` (zespół-słupek) |
| Odległość, minuty | liczone | długość trasy pieszej z OSRM (sekcja „Trasy piesze”); tempo seniora 1,0 m/s = 3,6 km/h, zaokrąglone w górę do 1 min; zawsze „ok.” |
| Adres toalety | `lokalizacja` | |
| Wskazówka | typ toalety + `uwagi`, gdy nie dotyczy sezonu | „poziom -1”, „przejście podziemne”, „wejście od ul. …” |
| Kafelek: płatna / bezpłatna | `platnosc` 0/1 | zbiór nie mówi, jak się płaci (karta, moneta) |
| Kafelek: przewijak | `przewijak` 0/1 | brak przewijaka = przekreślona ikona i ✘ |
| Kafelek: dla wózków | `dostepnosc` 0/1 | |
| Godziny PL + EN | `godziny` | sklejamy jednakowe dni: „pon.–pt. 9–19” / „Mon–Fri 9–19” |
| Sezon | `uwagi` + `typ` | dopisany do godzin: „sezonowo: do 31.10” / „seasonal: until 31.10” |
| Kod QR | liczone | nawigacja piesza; opis w sekcji „Kod QR” |
| Stopka | stałe | data danych + 19115 (Warszawskie Centrum Kontaktu) z numerem przystanku |

Niedzielę i „cały rok” pokazywaliśmy wcześniej w osobnych kafelkach. Zostały
usunięte (18.10), żeby kafelki i godziny były większe. Niedziela jest widoczna
w godzinach, sezon też.

**Zasady czytelności dla seniorów:**

- Odległość to najważniejsza liczba na kartce: co najmniej 60 pt. Treść co
  najmniej 15 pt.
- Czarne na białym, wysoki kontrast. Druk w czerni i bieli też musi działać,
  łącznie z syrenką i kodem QR.
- Nie polegamy na samym kolorze ani ikonach: zawsze ✔/✘ **i** słowo.
- Pełne słowa zamiast skrótów i żargonu („czynna”, a nie „otw.”).
- Mapa ustawiona na północ, z dużymi znacznikami i podpisem „JESTEŚ TUTAJ”.
- **Ulotka działa bez telefonu.** Kod QR jest dodatkiem dla tych, którzy wolą
  nawigację, a nie jedynym źródłem informacji. Tym różnimy się od miejskich
  tabliczek „Mapa WC” z samym kodem QR (patrz plik 13).

## Kod QR: nawigacja do toalety

Kod QR na ulotce otwiera **pieszą nawigację od przystanku do toalety**
w Google Maps. Link w oficjalnym formacie Google Maps URLs, bez klucza API:

```
https://www.google.com/maps/dir/?api=1&origin=52.2103,20.91986&destination=52.2081,20.9214&travelmode=walking
```

- `origin` = współrzędne słupka, `destination` = współrzędne toalety (z
  `ulotki.json`). Na telefonie link otwiera aplikację Google Maps, jeśli jest
  zainstalowana, a jeśli nie, przeglądarkę. Wystarczy nacisnąć „Start”.
- Kod generujemy w przeglądarce, przy renderze ulotki: biblioteka
  `qrcodejs` 1.0.0 z cdnjs. Działa offline, więc nie spowalnia druku
  wsadowego.
- **Rozmiar:** kod skanuje się z odległości ok. 10× jego boku, więc na
  ulotce co najmniej 4 cm (jest 4,2 cm). Poziom korekcji błędów M (ulotka na
  zewnątrz, zabrudzenia).
- Podpis przy kodzie w obu językach: „Prowadź mnie / Navigate me”.
- Sprawdzić przed prezentacją: wydruk w czerni i bieli, skan dwoma telefonami
  (Android i iPhone).
- Na prezentacji pokazać na żywo: skan → nawigacja do toalety. Dobry moment
  dla jury.

**Wariant na później: kod prowadzi przez naszą stronę,** np.
`https://<konto>.github.io/<repo>/t.html?id=4225-03`. Strona `t.html` wczytuje
mały plik `dane/trasy.json` (numer przystanku → współrzędne) i przekierowuje
do Google Maps, z przyciskami zapasowymi (OpenStreetMap, Apple Maps). Zalety:

- **Wydrukowany kod można zaktualizować.** Gdy toaleta zostanie zamknięta,
  wystarczy przeliczyć `trasy.json`, a stare ulotki zaczną prowadzić do nowej
  najbliższej toalety. Papier zostaje bez zmian.
- Krótszy adres to mniejszy i prostszy kod QR.
- Możemy policzyć skanowania.

Ryzyko: gdy strona przestanie działać, kody przestaną prowadzić dokądkolwiek.
Wymaga stałego hostingu, docelowo w domenie miasta (pytanie do mentora).

## Maskotka: syrenka

Cel: obcokrajowiec w sekundę rozumie, że kartka dotyczy toalety, nawet gdy
nie zna polskiego. Syrenka przy okazji mówi „to jest Warszawa”, co dobrze
wygląda na prezentacji.

- Plik: `app/img/wc_syrenka.jpeg` (koło z syrenką; szablon wycina je z białego
  marginesu przez `clip-path`).
- Sama maskotka nie wystarczy: obcokrajowiec może nie znać syrenki. Dlatego
  zawsze stoi obok napisu „Nearest toilet · WC”.
- Musi być czytelna w czerni i bieli przy ok. 4–5 cm na A4.
- Ta sama syrenka może być logo strony i postacią na slajdach.

**Uwaga prawna:** używamy własnej syrenki, nie kopii herbu Warszawy (syrenka
na czerwonej tarczy z koroną). Używanie herbu jest uregulowane przez miasto.
Na hackaton wystarczy własny rysunek. Przy wdrożeniu o wyglądzie zdecyduje
miasto (pytanie do mentora).

## Którą toaletę pokazujemy

1. **Główna** = najbliższa **pieszo** toaleta dowolnego typu (decyzja 18.10:
   toaleta za torami albo rzeką odpada, nawet gdy w linii prostej jest
   bliżej). Pokazujemy uczciwie jej cechy, także gdy to toi-toi albo toaleta
   płatna. Do niej prowadzą mapa i kod QR.
2. **Alternatywa** = najbliższa toaleta „pewna”: bezpłatna, całoroczna, czynna
   w niedzielę, nie przenośna. `ulotki_dane.py` liczy ją, gdy główna nie
   spełnia tych warunków, ale **obecna, uproszczona ulotka jej nie drukuje**.
   Pole zostaje w danych na wypadek powrotu.
3. Daleka toaleta nie dostaje dopisku „W pobliżu nie ma toalety” (usunięty
   18.10) — odległość i minuty mówią same za siebie, a przystanek i tak
   trafia na mapę luk.

Dlaczego alternatywa w ogóle: najbliższa toaleta bywa toi-toiem czynnym do 31
października albo toaletą w urzędzie zamkniętym w niedzielę, a w niedzielę
senior jedzie do kościoła albo na cmentarz.

## Druk dla wszystkich przystanków

Jedno polecenie generuje ulotki dla całego miasta:

```bash
.venv/Scripts/python.exe src/ulotki_pdf.py --wszystkie        # ok. 4400 stron, plik na dzielnicę
.venv/Scripts/python.exe src/ulotki_pdf.py --dzielnica Wola   # jedna dzielnica
.venv/Scripts/python.exe src/ulotki_pdf.py --id 4225-03       # wybrane słupki (po przecinku)
```

**Jak działa `ulotki_pdf.py`:**

1. Uruchamia w tle lokalny serwer HTTP dla katalogu `app/`.
2. Otwiera Chromium przez Playwright i ładuje `druk.html?ids=...` z paczką
   40 ulotek (`--paczka`), każda na osobnej stronie A4 (`break-after: page`).
3. Czeka, aż strona ustawi `window.gotowe = true`, czyli gdy wszystkie mapy
   wczytają kafelki, a kody QR się wygenerują.
4. Zapisuje paczkę do PDF i skleja paczki w jeden plik na dzielnicę (`pypdf`):
   `data/out/ulotki/Wola.pdf`.
5. Zapisuje `data/out/ulotki/spis.csv`: plik, numer strony, numer przystanku,
   nazwa, dzielnica. Ekipa rozwieszająca wie, która kartka gdzie idzie.
6. Sprawdza, czy liczba stron = liczba ulotek (ulotka za długa = 2 strony),
   i wypisuje przystanki, dla których mapa się nie wczytała.

**Dlaczego paczki:** tysiące map Leaflet na jednej stronie zabiją
przeglądarkę, a osobne otwarcie strony dla każdej ulotki trwa godzinami.

**Kolejność w PDF:** dzielnica → nazwa zespołu → numer słupka. Słupki tego
samego zespołu leżą obok siebie, więc da się je rozwieszać po kolei.

**Przypisanie dzielnicy:** przystanki nie mają pola z dzielnicą.
`ulotki_dane.py` pobiera granice 18 dzielnic (GeoJSON, zapis do
`data/raw/dzielnice.geojson`) i sprawdza, w której leży słupek (punkt
w wielokącie). Przy okazji odpadają słupki spoza Warszawy.

**Kafelki mapy przy druku masowym:** regulamin serwerów kafelków OSM zabrania
masowego pobierania. Powyżej 60 ulotek skrypt wymaga klucza MapTiler:

- **Na hackaton:** darmowy klucz MapTiler w `.env` jako `MAPTILER_KEY`.
  Skrypt przekazuje go tylko do pamięci przeglądarki, nie do plików aplikacji.
- **Docelowo:** własny wycinek map Warszawy w pliku PMTiles (Protomaps), bez
  zewnętrznego serwera i limitów. Albo serwer map miasta.
- Podgląd pojedynczej ulotki na stronie korzysta z kafelków OSM.

**Zależności** (tylko do druku wsadowego): `playwright` (+ jednorazowo
`playwright install chromium`) i `pypdf`.

## Pułapki w danych (sprawdzone 17.10)

- **Godziny** mają jeden stały format: `Dzień: HH:MM - HH:MM` / `Całodobowo` /
  `nieczynne`, rozdzielony `; `. Parser to kilka linijek.
- **`uwagi` miesza dwie rzeczy:** okres działania (ok. 90 toalet, np.
  „do 31 października”, „od 1 maja do 30 września w weekendy”) i wskazówki
  dojścia („poziom -1”, „wejście od ul. Piekarskiej”). Trzeba je rozdzielić.
- Funkcja `sezonowa()` w `src/luka_toaletowa.py` myli się na pojedynczych
  rekordach: toaleta z godzinami „styczeń–maj… październik–grudzień” wychodzi
  jako sezonowa, choć działa cały rok. Rekordów z okresem jest kilkanaście
  rodzajów, więc można je oznaczyć ręcznie w słowniku.
- **Teraz jest październik.** Ulotka wydrukowana dziś wskaże toi-toia, który
  za dwa tygodnie zniknie. Dlatego okres działania zawsze jest na ulotce
  (przy godzinach).
- **Linia prosta przez Wisłę i tory.** Najbliższa toaleta w linii prostej może
  być po drugiej stronie rzeki albo torów. **Rozwiązane trasami pieszymi**
  (sekcja „Trasy piesze”): 853 słupki (19%) wskazują przez to inną toaletę
  niż w linii prostej. Od 18.10 także mapa luk (`mapa.html`) liczy pieszo.
- **Czas dojścia inny niż w Google Maps.** Odległość zgadza się z Google
  (np. CH Reduta 01: 960 m u nas, 950 m w Google), ale Google liczy minuty dla
  przeciętnego dorosłego (ok. 1,25 m/s), a my dla seniora (1,0 m/s): 17 min
  na ulotce, 13 min w telefonie po zeskanowaniu QR. To celowe.
- 54 toalety typu „toaleta METRO”: nie wiemy, czy są przed bramkami, czy za
  nimi. Pytanie do mentora.

## Architektura

```
data/raw/male/{przystanki,toalety}.json  +  data/raw/dzielnice.geojson
            │
            ├──► src/trasy_piesze.py ◄──► OSRM w Dockerze (localhost:5000)
            │          │
            │          ▼
            │    data/cache/trasy_piesze.json   (w gicie, ok. 3 MB)
            ▼          │
src/ulotki_dane.py ◄───┘
            │
            ├─► app/dane/ulotki.json   (1 rekord = 1 słupek, ok. 4400)
            ├─► app/dane/toalety.json  (toalety z opisem)
            └─► app/dane/mapa.json     (dla mapy luk)
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
 app/index.html          app/druk.html          app/mapa.html
 wyszukiwarka →          wiele ulotek na        mapa luk dla urzędu,
 podgląd ulotki →        stronę, druk wsadowy   statystyki dzielnic
 „Drukuj / PDF”                │
                               ▼
                    src/ulotki_pdf.py (Playwright)
                    → data/out/ulotki/<dzielnica>.pdf + spis.csv
```

**Pliki:**

| Plik | Co robi |
|---|---|
| `src/trasy_piesze.py` | dla każdego słupka pyta OSRM o dojście pieszo do 10 najbliższych toalet, wybiera najbliższą pieszo i zapisuje jej trasę do `data/cache/trasy_piesze.json` |
| `src/ulotki_dane.py` | wczytuje dane, przypisuje dzielnice, liczy główną toaletę (z trasą pieszą z cache) i alternatywę, parsuje godziny (PL + EN) i sezon, zapisuje JSON-y |
| `app/ulotka.js` + `ulotka.css` | **jeden szablon ulotki** (mapa, kafelki, QR, syrenka), używany przez `index.html` i `druk.html`; `@page { size: A4 }` |
| `app/index.html` | pole „wpisz nazwę lub nr przystanku” (`?id=4225-03`), podgląd, przycisk druku |
| `app/druk.html` | wiele ulotek na stronę (`?ids=...` albo `?dzielnica=Wola&od=0&ile=20`), sygnał `window.gotowe` dla Playwright |
| `app/mapa.html` | mapa luk w 4 kategoriach toalet + liczby na slajd (patrz plik 13) |
| `app/img/wc_syrenka.jpeg` | maskotka |
| `src/ulotki_pdf.py` | druk wsadowy: paczki → PDF na dzielnicę + `spis.csv` |

**Rekord w `ulotki.json`:**

```json
{
  "id": "4225-03", "nazwa": "Sympatyczna", "dzielnica": "Wola",
  "lat": 52.2103, "lon": 20.91986,
  "glowna": {
    "lat": 52.2081, "lon": 20.9214, "adres": "Inwalidów 3, Biblioteka Publiczna",
    "typ": "toaleta stacjonarna", "odl_m": 350, "min": 6,
    "platna": false, "dla_wozkow": true, "przewijak": true,
    "niedziela": null,
    "godziny": "pon.–pt. 9–19 · sob. 9–15 · niedz. nieczynne",
    "godziny_en": "Mon–Fri 9–19 · Sat 9–15 · Sun closed",
    "sezon": null, "sezon_krotko": null, "sezon_krotko_en": null,
    "wskazowka": "wejście od ul. Piekarskiej",
    "trasa": [[52.2103, 20.91986], [52.2095, 20.9203], "...", [52.2081, 20.9214]]
  },
  "alternatywa": { "...": "te same pola albo null" }
}
```

**Zasady pracy z `ulotki.json`:**

- **Wzór rekordu to umowa** między osobą od danych a osobą od ulotek.
  Zmianę nazwy albo znaczenia pola uzgadniamy we dwoje i od razu
  poprawiamy wzór powyżej. Inaczej ulotka po cichu pokaże puste miejsca.
- **Python liczy, przeglądarka tylko wyświetla.** Ulotka i mapa nie liczą
  odległości, godzin ani sezonu. Brakuje pola? Dopisujemy je
  w `src/ulotki_dane.py` i uruchamiamy skrypt jeszcze raz. Dzięki temu
  liczby na ulotkach, mapie i slajdach zawsze się zgadzają.
- **Wyjątek:** link do nawigacji w kodzie QR ulotka składa sama z gotowych
  pól `lat`/`lon` przystanku i toalety (sekcja „Kod QR”).

**Uruchomienie podglądu:**

```bash
.venv/Scripts/python.exe src/ulotki_dane.py
.venv/Scripts/python.exe -m http.server 8000 -d app
# → http://localhost:8000/?id=4225-03
```

Serwer jest potrzebny, bo przeglądarka nie wczyta JSON-a przez `file://`.
Pliki w `app/dane/` to pochodne otwartych danych (kilka MB), więc są w gicie.
Wtedy GitHub Pages działa od razu. Wygenerowane PDF-y (`data/out/`) zostają
poza gitem.

**Mapa na ulotce:** Leaflet 1.9.4 z cdnjs. Mapę tworzymy dopiero po
wczytaniu fontu (`document.fonts.ready`), inaczej zostaje szary pas. Przed
drukiem czekamy na zdarzenie `load` warstwy kafelków, inaczej PDF wyjdzie
z szarą mapą. Linia przerywana biegnie po trasie pieszej (`glowna.trasa`),
a mapa jest dopasowana do całej trasy. Rekord bez trasy dostaje linię prostą.

## Trasy piesze

Odległość i linia na mapie pochodzą z prawdziwej trasy pieszej, a nie
z linii prostej × 1,3. Liczy je `src/trasy_piesze.py`:

1. Dla słupka bierze 10 najbliższych toalet w linii prostej w każdym
   wariancie mapy luk (wszystkie, bezpłatne, dostępne, w niedzielę) —
   razem 10–40 toalet, bo warianty się pokrywają.
2. Jednym zapytaniem OSRM `/table` (profil pieszy) pobiera odległości
   pieszo do wszystkich i wybiera najkrótszą. Doliczamy dojście
   od punktu do najbliższej ścieżki (toaleta w parku itp.).
3. Zapytaniem `/route` pobiera kształt trasy, upraszcza go (Douglas–Peucker,
   2 m; mediana 10 punktów na trasę) i zapisuje w
   `data/cache/trasy_piesze.json`.

`src/ulotki_dane.py` czyta ten plik: główna toaleta to ta najbliższa pieszo,
odległość to długość trasy. **Bez pliku ulotki wracają do linii prostej** —
dlatego cache jest w gicie i nie trzeba liczyć tras, żeby przeliczyć dane.
Mapa luk bierze z tego samego pliku najbliższą pieszo toaletę w każdym
wariancie (`mapa.json`, pole `d` w metrach pieszo), więc wariant „wszystkie”
zgadza się z ulotką co do metra.

**Serwer tras: lokalny OSRM w Dockerze.** Serwer publiczny
(`routing.openstreetmap.de`) ma limit zapytań (HTTP 429): ok. 12 s na słupek,
czyli ok. 15 h dla miasta. Lokalnie całe miasto liczy się w 7 minut.
Jednorazowe przygotowanie (ok. 2 min + pobranie 300 MB):

```bash
# mapa Mazowsza z Geofabrik → data/osrm/ (katalog poza gitem, ok. 1,5 GB po przygotowaniu)
curl -L -o data/osrm/mazowieckie-latest.osm.pbf https://download.geofabrik.de/europe/poland/mazowieckie-latest.osm.pbf
# Git Bash na Windows: najpierw export MSYS_NO_PATHCONV=1
docker run --rm -v "$PWD/data/osrm:/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-extract -p /opt/foot.lua /data/mazowieckie-latest.osm.pbf
docker run --rm -v "$PWD/data/osrm:/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-partition /data/mazowieckie-latest.osrm
docker run --rm -v "$PWD/data/osrm:/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-customize /data/mazowieckie-latest.osrm
# serwer na localhost:5000
docker run -d --name osrm-pieszo -p 5000:5000 -v "$PWD/data/osrm:/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld --max-table-size 1000 /data/mazowieckie-latest.osrm
```

Potem:

```bash
.venv/Scripts/python.exe src/trasy_piesze.py --wszystkie --serwer http://localhost:5000
.venv/Scripts/python.exe src/ulotki_dane.py
docker stop osrm-pieszo        # ponownie: docker start osrm-pieszo
```

Skrypt dolicza tylko brakujące odległości (nowy słupek, nowa toaleta
wśród kandydatów), a trasę pobiera ponownie tylko wtedy, gdy zmieni się
najbliższa toaleta. Żeby przeliczyć
wszystko od nowa (np. po zmianie listy toalet), usuń
`data/cache/trasy_piesze.json`. Bez `--serwer` skrypt pyta serwer publiczny
— wystarczy na kilka słupków, nie na dzielnicę.

**Wynik (18.10, mapa OSM z 17.10):** 4433 słupki, 0 błędów. Mediana różnicy
wobec starego szacunku +10 m, ale 129 słupków ma trasę ponad 2× dłuższą
(tory, rzeka, ruchliwa ulica bez przejścia), a 853 (19%) inną toaletę.
`app/dane/ulotki.json` urósł z 3,3 do 4,8 MB.

**Warianty mapy luk (18.10):** doliczenie odległości do kandydatów ze
wszystkich wariantów trwało 3 minuty, 0 błędów. Dwie ulotki (Targówek,
Utrata 01 i Łubinowa 02) dostały bliższą pieszo toaletę, która wcześniej
nie była wśród 10 kandydatów. Po zmianie kategorii mapy (18.10) doliczenie
trwało 3,5 minuty, ulotki się nie zmieniły.

## Kolejność prac

Każdy krok kończy się czymś, co działa. Jeśli czas się skończy, oddajemy
ostatni działający krok.

| # | Krok | Stan | Wynik |
|---|---|---|---|
| 1 | `ulotki_dane.py`: dzielnice, najbliższa toaleta + alternatywa, parser godzin i `uwagi` | gotowe | `ulotki.json`, sprawdzone ręcznie |
| 2 | Szablon ulotki w HTML/CSS, PL + EN, kafelki, syrenka | gotowe | wygląd zatwierdzony (18.10: przewijak, większe kafelki i godziny) |
| 3 | Podpięcie JSON + mapa Leaflet + kod QR + wyszukiwarka | gotowe | dowolny przystanek → ulotka → PDF; QR otwiera trasę w telefonie |
| 4 | `druk.html` + `ulotki_pdf.py`, klucz MapTiler | gotowe | PDF na dzielnicę + `spis.csv` |
| 5 | Mapa luk dla urzędu + statystyki dzielnic | gotowe (18.10: odległości piesze) | slajd z liczbami i mapą |
| 6 | GitHub Pages + makieta ulotki na zdjęciu prawdziwego przystanku | do zrobienia | link dla jury, zdjęcie do prezentacji |
| 7 | Test wydruku w czerni i bieli + skan QR różnymi telefonami | do zrobienia | pewność, że ulotka działa na papierze |
| 8 | Trasa piesza po ulicach zamiast linii prostej × 1,3 (OSRM w Dockerze) | gotowe (18.10) | prawdziwa odległość, najbliższa toaleta pieszo, trasa na mapie; sekcja „Trasy piesze” |

**Punkty kontrolne:** **zamrożenie kodu w niedzielę o 9:00.** Potem tylko
prezentacja i próba. Oddanie o 11:00.

**Na demo:** gotowe PDF-y („ulotki dla całego miasta z jednego polecenia”)
plus na żywo wydruk jednego przystanku i skan kodu QR telefonem. Pełnego
przebiegu na żywo nie puszczamy, bo trwa za długo.

**Podział ról (3 osoby, ustalony 17.10):**

- **Osoba 1 (Roman): dane + mapa.** Krok 1, potem krok 5 (mapa luk,
  statystyki dzielnic), opcjonalnie 8.
- **Osoba 2: ulotki.** Kroki 2–4 (szablon, kod QR, druk wsadowy).
- **Osoba 3: prezentacja i storytelling.** Scenariusz pitchu, slajdy, źródła,
  liczby z kroku 5, krok 6 (makieta ulotki na zdjęciu
  przystanku), próba prezentacji. Testy ulotki na kilkunastu przystankach
  (Wisła, tory, pętle) i pytania do mentora.

## Jak to wypada wobec kryteriów jury

- **Dane Warszawy (20%):** dwa zbiory z portalu, połączone w coś, czego żaden
  z nich osobno nie pokazuje.
- **Innowacyjność (25%):** nie „kolejna mapa toalet”, tylko informacja
  w miejscu, w którym się czeka, dla trzech grup naraz: papier dla seniorów,
  QR z nawigacją dla tych, którzy wolą telefon, syrenka i PL + EN dla
  obcokrajowców. Do tego wniosek dla miasta: 57% słupków nie ma w 10 minut
  pieszo (600 m) bezpłatnej, dostępnej toalety, a w niedzielę 73%.
- **Wdrożenie (20%):** gotowe PDF-y dla wszystkich przystanków z jednego
  polecenia, spis do rozwieszania, koszt druku kilka zł za sztukę, działająca
  strona, numer 19115 do zgłaszania błędów.
- **Realia miasta (15%):** kampania „Toalety ratują życie” (Głos Seniora,
  15.10.2026), starzejące się miasto, upały, turyści.
- **Prezentacja (20%):** syrenka jako bohaterka pitchu, zdjęcie ulotki na
  prawdziwym przystanku, skan QR na żywo, mapa luk.

## Decyzje drużyny

- [x] Dla kogo: wszyscy (mieszkańcy, turyści), teksty PL + EN; senior jako
  bohater opowieści.
- [x] Format: A4.
- [x] Kod QR: nawigacja piesza prosto do Google Maps (wariant przez `t.html`
  na później).
- [x] Źródło kafelków do druku masowego: MapTiler.
- [x] Kafelki na ulotce: płatność, przewijak, wózki (niedziela i „cały rok”
  usunięte 18.10; niedziela i sezon są w godzinach).
- [ ] Alternatywa: wraca na ulotkę czy zostaje tylko w danych?
- [x] Trasa piesza (krok 8): tak, główna toaleta = najbliższa pieszo.
- [x] Tempo seniora: 1,0 m/s = 3,6 km/h (środek tempa zdrowego seniora,
  3,0–4,5 km/h). Wcześniej 0,8 m/s — za wolno.
- [x] Mapa luk: odległości piesze jak na ulotkach, domyślny próg 600 m
  pieszo = 10 min tempem seniora (18.10). Wcześniej 500 m w linii prostej.
- [x] Kategorie mapy luk (18.10), każda to jedno kryterium: Wszystkie,
  Bezpłatna, Dla osób z niepełnosprawnością (dostępna dla wózków), Czynna
  w niedzielę. Domyślnie „Wszystkie”. Wcześniej „Dla seniora” (bezpłatna
  + dostępna + nie toi-toi) i „Dla seniora, czynna w niedzielę”.
- [ ] Zdanie i liczba na slajd po zmianie kategorii.

## Pytania do mentora

- Czy toalety „METRO” są dostępne bez biletu?
- Kto decyduje o tym, co wisi na przystankach (ZTM? operator wiat?) i czy
  dopuszcza ulotki innych instytucji?
- Czy miasto ma własny serwer map, z którego można drukować?
- Czy kody QR mogłyby prowadzić do adresu w domenie miasta?
- Czy własna syrenka (nie herb) na materiałach informacyjnych jest w porządku?
