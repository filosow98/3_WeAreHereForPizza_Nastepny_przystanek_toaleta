# Następny przystanek: toaleta

Ulotki „Najbliższa toaleta” na przystankach komunikacji miejskiej w Warszawie
oraz mapa luk toaletowych. Projekt z Hackatonu Otwartych Danych Warszawy
(17–18.10.2026, wyzwanie „Twój ruch”).

**Co druga osoba ogranicza picie poza domem, bo boi się, że nie znajdzie
toalety** ([RSPH](https://www.rsph.org.uk/news/public-toilet-deserts-widespread-across-england/)).
**W Warszawie z 6 na 10 przystanków senior nie dojdzie w 10 minut do
bezpłatnej, dostępnej toalety.** Dlatego na każdym słupku wieszamy kartkę,
która pokazuje, gdzie jest najbliższa toaleta: kierunek, czas dojścia
tempem seniora, godziny otwarcia, mapka i kod QR z nawigacją. Bez telefonu,
bez aplikacji, po polsku i po angielsku.

## Co jest w repo

| Część | Co robi |
|---|---|
| `app/index.html` | podgląd i druk ulotki dla wybranego przystanku |
| `app/mapa.html` | mapa luk: słupki bez toalety w zasięgu |
| `app/druk.html` | widok do druku wielu ulotek naraz |
| `app/dane/` | gotowe dane dla strony (liczone przez `src/ulotki_dane.py`) |
| `src/` | skrypty: pobranie danych, obliczenia, trasy piesze, druk PDF |
| `data/` | dane źródłowe (toalety, przystanki, granice dzielnic) i trasy piesze |
| `docs/` | plan aplikacji: ulotka, mapa luk, dane, trasy piesze, druk |

## Uruchomienie strony

Dane są już w repo, więc do podglądu wystarczy sam Python (bez instalowania
pakietów). **Stronę trzeba otworzyć przez serwer** — otwarta z dysku
(`file:///...`) nie wczyta plików JSON.

```bash
python -m http.server 8000 --directory app
```

- http://localhost:8000 — ulotka dla wybranego przystanku,
- http://localhost:8000/mapa.html — mapa luk.

## Przeliczenie danych i druk

Instalacja (przez [uv](https://docs.astral.sh/uv/) albo zwykły `pip`):

```bash
uv venv
uv pip install -r requirements.txt
uv run python -m playwright install chromium   # tylko do druku PDF
```

Polecenia (z katalogu projektu):

```bash
uv run src/pobierz_male.py toalety przystanki   # świeże dane z API miasta (wymaga tokenu)
uv run src/ulotki_dane.py                       # przelicza app/dane/*.json
uv run src/ulotki_pdf.py --id 7013-01,7016-02   # wybrane słupki → data/out/ulotki/wybrane.pdf
uv run src/ulotki_pdf.py --dzielnica Wola       # jedna dzielnica → data/out/ulotki/Wola.pdf
uv run src/ulotki_pdf.py --wszystkie            # całe miasto, plik na dzielnicę + spis.csv
```

Bez uv: te same skrypty przez `python src/...` w aktywnym środowisku.

**Klucze** wpisz do `.env` (skopiuj z `.env.example`, nie wpisuj kluczy do
`.env.example`):

- `WAW_TOKEN` — token API https://dane.um.warszawa.pl/pl/key-api, potrzebny
  tylko do pobrania świeżych danych (`src/pobierz_male.py`),
- `MAPTILER_KEY` — darmowy klucz https://cloud.maptiler.com, potrzebny do druku
  powyżej 60 ulotek naraz (regulamin serwerów map OSM zabrania masowego
  pobierania kafelków).

### Trasy piesze

Odległości to trasy po chodnikach z OpenStreetMap, liczone lokalnym serwerem
OSRM w Dockerze i zapisane w `data/cache/trasy_piesze.json`. Trzeba je
przeliczyć tylko po zmianie listy toalet albo przystanków:

```bash
uv run src/trasy_piesze.py --wszystkie --serwer http://localhost:5000
```

Przygotowanie serwera OSRM: [docs/14](docs/14-plan-generatora-ulotek.md),
sekcja „Trasy piesze”. Bez pliku tras `src/ulotki_dane.py` używa szacunku
(linia prosta × 1,3).

## Dane

- Toalety i przystanki ZTM — [dane.um.warszawa.pl](https://dane.um.warszawa.pl)
  (zbiory `get_m_toalety`, `get_ztm_przystanki_komunikacji_miejskiej`),
- granice dzielnic i sieć chodników — © współtwórcy
  [OpenStreetMap](https://www.openstreetmap.org/copyright).

## Dokumentacja

Pełny opis aplikacji — co jest na ulotce, którą toaletę pokazujemy, pułapki
w danych, architektura, trasy piesze i druk:
[docs/14-plan-generatora-ulotek.md](docs/14-plan-generatora-ulotek.md).
