"""Dane do ulotek „Najbliższa toaleta” i mapy luk (docs/14-plan-generatora-ulotek.md).

Uruchomienie (z katalogu projektu):
    .venv/Scripts/python.exe src/ulotki_dane.py

Wymaga data/raw/male/{toalety,przystanki}.json (src/pobierz_male.py). Granice
dzielnic pobiera sam przy pierwszym uruchomieniu do data/raw/dzielnice.geojson.

Wynik w app/dane/:
    ulotki.json   1 rekord = 1 słupek, wzór rekordu jak w docs/14
    mapa.json     odległości piesze słupek → toaleta w 4 wariantach (mapa luk)
    toalety.json  toalety z polami do wyświetlenia
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import requests

import waw_api  # noqa: F401 — ustawia UTF-8 na konsoli (Windows, cp1251)
from luka_toaletowa import RAW_DIR, czynna_w_niedziele, odleglosc_m

ROOT = Path(__file__).resolve().parent.parent
APP_DANE = ROOT / "app" / "dane"
DZIELNICE_PLIK = ROOT / "data" / "raw" / "dzielnice.geojson"
TRASY_PLIK = ROOT / "data" / "cache" / "trasy_piesze.json"
DZIELNICE_URL = (
    "https://raw.githubusercontent.com/andilabs/warszawa-dzielnice-geojson/"
    "master/warszawa-dzielnice.geojson"
)

OBJAZD = 1.3  # droga po chodnikach vs linia prosta
TEMPO_SENIORA = 1.0  # m/s = 3,6 km/h, środek tempa zdrowego seniora (3,0–4,5 km/h)
MAX_ALTERNATYWA = 3000  # m — dalszej „pewnej” toalety nie dopisujemy

DNI = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
DNI_SKROT = ["pon.", "wt.", "śr.", "czw.", "pt.", "sob.", "niedz."]
DNI_SKROT_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MIESIACE_DOPELNIACZ = (
    "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca",
    "sierpnia", "września", "października", "listopada", "grudnia",
)
# Uwagi z miesiącami, które mówią o zmianie godzin, a nie o zamknięciu na
# część roku — toaleta działa cały rok.
CALOROCZNE_ZMIENNE_GODZINY = ("w pozostałym okresie", "styczeń-maj", "listopad - marzec")

# Warianty mapy luk (decyzja 18.10: każdy wariant to jedno kryterium,
# wcześniej „dla seniora” = bezpłatna + dostępna + nie toi-toi).
WARIANTY = {
    "wszystkie": lambda p: True,
    "bezplatna": lambda p: p["platnosc"] == 0,
    "dostepna": lambda p: p["dostepnosc"] == 1,
    "niedziela": czynna_w_niedziele,
}


# --- toalety -------------------------------------------------------------

def godzina(hhmm: str) -> str:
    """'09:00' → '9', '09:30' → '9:30'."""
    h, m = hhmm.strip().split(":")
    return str(int(h)) if m == "00" else f"{int(h)}:{m}"


def parsuj_godziny(tekst: str | None) -> list[str | None]:
    """7 wartości pon.–niedz.: '9–19', 'całą dobę' albo None (nieczynne)."""
    wynik: list[str | None] = [None] * 7
    for czesc in (tekst or "").split(";"):
        if ":" not in czesc:
            continue
        dzien, wartosc = czesc.split(":", 1)
        dzien, wartosc = dzien.strip(), wartosc.strip().lower()
        if dzien not in DNI:
            continue
        if "całodob" in wartosc:
            wynik[DNI.index(dzien)] = "całą dobę"
        elif m := re.match(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", wartosc):
            wynik[DNI.index(dzien)] = f"{godzina(m.group(1))}–{godzina(m.group(2))}"
    return wynik


def skrot_godzin(dni: list[str | None], en: bool = False) -> str:
    """Skleja jednakowe kolejne dni: 'pon.–pt. 9–19 · sob. 9–15 · niedz. nieczynne'
    (en: 'Mon–Fri 9–19 · Sat 9–15 · Sun closed')."""
    skroty = DNI_SKROT_EN if en else DNI_SKROT
    if en:
        dni = ["24 h" if d == "całą dobę" else d for d in dni]
    if len(set(dni)) == 1:
        if en:
            return f"daily {dni[0]}" if dni[0] else "closed"
        return f"codziennie {dni[0]}" if dni[0] else "nieczynna"
    grupy = []
    start = 0
    for i in range(1, 8):
        if i == 7 or dni[i] != dni[start]:
            nazwa = skroty[start] if i - 1 == start else f"{skroty[start]}–{skroty[i - 1]}"
            grupy.append(f"{nazwa} {dni[start] or ('closed' if en else 'nieczynne')}")
            start = i
    return " · ".join(grupy)


def rozdziel_uwagi(uwagi: str | None) -> tuple[str | None, str | None]:
    """Pole `uwagi` miesza okres działania i wskazówki dojścia → (sezon, wskazówka)."""
    tekst = " ".join((uwagi or "").split())
    niski = tekst.lower()
    if niski in ("", "czynna"):
        return None, None
    if any(k in niski for k in CALOROCZNE_ZMIENNE_GODZINY):
        return None, tekst
    if any(m in niski for m in MIESIACE_DOPELNIACZ):
        return re.sub(r"^czynna\s+", "", tekst, flags=re.IGNORECASE), None
    return None, tekst


RZYMSKIE = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")


def sezon_krotko(sezon: str | None) -> str | None:
    """Okres na kafelek ulotki: 'od 1 maja do 30 września w weekendy' → '1.05–30.09, weekendy'."""
    if not sezon:
        return None
    s = sezon.lower().replace("całodobowo", "")
    for nr, miesiac in enumerate(MIESIACE_DOPELNIACZ, start=1):
        s = re.sub(rf"(\d{{1,2}}) {miesiac}", rf"\1.{nr:02d}", s)
        s = s.replace(miesiac, RZYMSKIE[nr - 1])
    s = re.sub(r"od (\S+) do (\S+)", r"\1–\2", s)
    s = re.sub(r"\s+w\s+", ", ", s)
    return " ".join(s.split())


def sezon_krotko_en(krotko: str | None) -> str | None:
    """'do 31.10' → 'until 31.10', '1.05–30.09, weekendy' → '1.05–30.09, weekends'."""
    if not krotko:
        return None
    return re.sub(r"^do ", "until ", krotko).replace("weekendy", "weekends")


def wczytaj_toalety() -> list[dict]:
    dane = json.loads((RAW_DIR / "toalety.json").read_text(encoding="utf-8"))
    toalety = []
    for t in dane:
        p = t["properties"]
        lon, lat = t["geometry"]["coordinates"]
        dni = parsuj_godziny(p["godziny"])
        sezon, wskazowka = rozdziel_uwagi(p["uwagi"])
        toalety.append({
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "adres": (p["lokalizacja"] or "").strip(),
            "typ": p["typ"],
            "dzielnica": p["dzielnica"],
            "platna": p["platnosc"] == 1,
            "dla_wozkow": p["dostepnosc"] == 1,
            "przewijak": p["przewijak"] == 1,
            "niedziela": dni[6],
            "godziny": skrot_godzin(dni),
            "godziny_en": skrot_godzin(dni, en=True),
            "sezon": sezon,
            "sezon_krotko": sezon_krotko(sezon),
            "sezon_krotko_en": sezon_krotko_en(sezon_krotko(sezon)),
            "wskazowka": wskazowka,
            "warianty": [nazwa for nazwa, f in WARIANTY.items() if f(p)],
        })
    return toalety


def pewna(t: dict) -> bool:
    """Toaleta, na którą senior może liczyć zawsze: bezpłatna, cały rok, w niedzielę, nie toi-toi."""
    return not t["platna"] and t["sezon"] is None and t["niedziela"] is not None and t["typ"] != "przenośna"


# --- dzielnice i przystanki ----------------------------------------------

def wczytaj_dzielnice() -> list[tuple[str, list]]:
    if not DZIELNICE_PLIK.exists():
        print(f"Pobieram granice dzielnic → {DZIELNICE_PLIK.relative_to(ROOT)}")
        odp = requests.get(DZIELNICE_URL, timeout=30)
        odp.raise_for_status()
        DZIELNICE_PLIK.write_bytes(odp.content)
    dane = json.loads(DZIELNICE_PLIK.read_text(encoding="utf-8"))
    return [
        (f["properties"]["name"], f["geometry"]["coordinates"])
        for f in dane["features"]
        if f["properties"]["name"] != "Warszawa"
    ]


def w_pierscieniu(lon: float, lat: float, pierscien: list) -> bool:
    wewnatrz = False
    j = len(pierscien) - 1
    for i in range(len(pierscien)):
        xi, yi = pierscien[i][:2]
        xj, yj = pierscien[j][:2]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            wewnatrz = not wewnatrz
        j = i
    return wewnatrz


def dzielnica_punktu(lat: float, lon: float, dzielnice: list[tuple[str, list]]) -> str | None:
    for nazwa, multipolygon in dzielnice:
        for polygon in multipolygon:
            zewn, *dziury = polygon
            if w_pierscieniu(lon, lat, zewn) and not any(w_pierscieniu(lon, lat, d) for d in dziury):
                return nazwa
    return None


def wczytaj_przystanki(dzielnice: list[tuple[str, list]]) -> list[dict]:
    dane = json.loads((RAW_DIR / "przystanki.json").read_text(encoding="utf-8"))
    wynik = []
    for rekord in dane:
        pola = {x["key"]: x["value"] for x in rekord["values"]}
        try:
            lat, lon = float(pola["szer_geo"]), float(pola["dlug_geo"])
        except (KeyError, TypeError, ValueError):
            continue  # słupek bez współrzędnych
        dzielnica = dzielnica_punktu(lat, lon, dzielnice)
        if dzielnica is None:
            continue  # poza Warszawą
        wynik.append({
            "id": f"{pola['zespol']}-{pola['slupek']}",
            "nazwa": pola["nazwa_zespolu"],
            "slupek": pola["slupek"],
            "dzielnica": dzielnica,
            "lat": lat,
            "lon": lon,
        })
    wynik.sort(key=lambda s: (s["dzielnica"], s["nazwa"], s["slupek"]))
    return wynik


# --- ulotki --------------------------------------------------------------

def opis_toalety(t: dict, prosta_m: float, trasa: dict | None = None) -> dict:
    """Pola toalety na ulotce. Odległość z trasy pieszej (src/trasy_piesze.py),
    a bez niej szacunek: linia prosta × objazd."""
    odl = trasa["odl_m"] if trasa else OBJAZD * prosta_m
    pola = {k: v for k, v in t.items() if k not in ("dzielnica", "warianty")}
    wynik = {
        **pola,
        "odl_m": int(round(odl, -1)),
        "min": max(1, math.ceil(odl / TEMPO_SENIORA / 60)),
    }
    if trasa:
        wynik["trasa"] = trasa["ksztalt"]
    return wynik


def wczytaj_trasy() -> dict:
    """Trasy piesze z cache src/trasy_piesze.py (brak pliku = same szacunki)."""
    return json.loads(TRASY_PLIK.read_text(encoding="utf-8")) if TRASY_PLIK.exists() else {}


def main() -> None:
    toalety = wczytaj_toalety()
    przystanki = wczytaj_przystanki(wczytaj_dzielnice())
    trasy = wczytaj_trasy()
    po_wsp: dict[str, list[int]] = {}  # "lat,lon" → indeksy toalet (bywa kilka w jednym punkcie)
    for i, t in enumerate(toalety):
        po_wsp.setdefault(f"{t['lat']},{t['lon']}", []).append(i)
    print(f"Toalet: {len(toalety)}, słupków w granicach Warszawy: {len(przystanki)}")

    ulotki, mapa = [], []
    z_trasa = z_mapa_pieszo = 0
    for s in przystanki:
        odl = [odleglosc_m(s["lat"], s["lon"], t["lat"], t["lon"]) for t in toalety]

        def najblizsza(warunek) -> int | None:
            kandydaci = [i for i, t in enumerate(toalety) if warunek(t)]
            return min(kandydaci, key=odl.__getitem__) if kandydaci else None

        # Z trasą pieszą główna = najbliższa pieszo, nie w linii prostej
        # (toaleta za torami albo rzeką odpada).
        trasa = trasy.get(s["id"])
        if trasa and (trasa["lat"], trasa["lon"]) != (s["lat"], s["lon"]):
            trasa = None  # słupek przesunięty — trasa nieaktualna
        if trasa and trasa["cel"] in po_wsp:
            glowna = po_wsp[trasa["cel"]][0]
            trasa_glownej = {"odl_m": trasa["pieszo"][trasa["cel"]], "ksztalt": trasa["trasa"]}
            z_trasa += 1
        else:
            glowna = najblizsza(lambda t: True)
            trasa_glownej = None
        alternatywa = None
        if not pewna(toalety[glowna]):
            alt = najblizsza(pewna)
            if alt is not None and odl[alt] <= MAX_ALTERNATYWA:
                alternatywa = opis_toalety(toalety[alt], odl[alt])
        ulotki.append({
            **{k: s[k] for k in ("id", "nazwa", "dzielnica", "lat", "lon")},
            "glowna": opis_toalety(toalety[glowna], odl[glowna], trasa_glownej),
            "alternatywa": alternatywa,
        })

        # Mapa luk liczy jak ulotka: najbliższa pieszo w każdym wariancie,
        # a bez trasy szacunek linia prosta × objazd.
        pieszo = [
            (d, i)
            for k, d in (trasa["pieszo"].items() if trasa else ())
            if d is not None and k in po_wsp
            for i in po_wsp[k]
        ]
        najblizsze, odleglosci = [], []
        for w in WARIANTY:
            w_wariancie = [(d, i) for d, i in pieszo if w in toalety[i]["warianty"]]
            if w_wariancie:
                d, i = min(w_wariancie)
                z_mapa_pieszo += 1
            else:
                i = najblizsza(lambda t, w=w: w in t["warianty"])
                d = OBJAZD * odl[i]
            najblizsze.append(i)
            odleglosci.append(round(d))
        mapa.append({
            **{k: s[k] for k in ("id", "nazwa", "dzielnica", "lat", "lon")},
            "d": odleglosci,  # m pieszo
            "t": najblizsze,  # indeks w toalety.json
        })

    APP_DANE.mkdir(parents=True, exist_ok=True)
    zapisz = lambda nazwa, obj: (APP_DANE / nazwa).write_text(  # noqa: E731
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    zapisz("ulotki.json", ulotki)
    zapisz("mapa.json", {"warianty": list(WARIANTY), "przystanki": mapa})
    zapisz("toalety.json", toalety)

    z_alternatywa = sum(u["alternatywa"] is not None for u in ulotki)
    print(f"Zapisano {len(ulotki)} ulotek ({z_alternatywa} z alternatywą, {z_trasa} z trasą pieszą) "
          f"→ {APP_DANE.relative_to(ROOT)}")
    print(f"Mapa luk: {z_mapa_pieszo} z {len(mapa) * len(WARIANTY)} odległości pieszo, reszta szacunek × {OBJAZD}")


if __name__ == "__main__":
    main()
