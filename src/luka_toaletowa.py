"""Luka toaletowa — ile przystanków nie ma toalety w zasięgu kilku minut pieszo.

Uruchomienie (z katalogu projektu):
    .venv/Scripts/python.exe src/luka_toaletowa.py
    .venv/Scripts/python.exe src/luka_toaletowa.py --promien 300

Wymaga pobranych zbiorów (src/pobierz_male.py):
    data/raw/male/toalety.json, data/raw/male/przystanki.json

Odległość w linii prostej — po chodnikach będzie dłuższa, więc wynik to
dolne oszacowanie luki. Opis metody: docs/14-plan-generatora-ulotek.md.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import waw_api  # noqa: F401 — ustawia UTF-8 na konsoli (Windows, cp1251)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "male"


def wczytaj_toalety() -> list[tuple[float, float, dict]]:
    dane = json.loads((RAW_DIR / "toalety.json").read_text(encoding="utf-8"))
    return [
        (t["geometry"]["coordinates"][1], t["geometry"]["coordinates"][0], t["properties"])
        for t in dane
    ]


def wczytaj_przystanki() -> list[tuple[float, float, str]]:
    dane = json.loads((RAW_DIR / "przystanki.json").read_text(encoding="utf-8"))
    wynik = []
    for rekord in dane:
        pola = {x["key"]: x["value"] for x in rekord["values"]}
        try:
            wynik.append((float(pola["szer_geo"]), float(pola["dlug_geo"]), pola["nazwa_zespolu"]))
        except (KeyError, TypeError, ValueError):
            pass  # słupek bez współrzędnych
    return wynik


def odleglosc_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Przybliżenie płaskie — na skalę miasta błąd jest pomijalny."""
    x = (lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2)) * 111_320
    y = (lat2 - lat1) * 110_540
    return math.hypot(x, y)


def sezonowa(p: dict) -> bool:
    uwagi = (p["uwagi"] or "").lower()
    return "paźdz" in uwagi or "wrześ" in uwagi or "grud" in uwagi or "sezon" in uwagi


def czynna_w_niedziele(p: dict) -> bool:
    m = re.search(r"Niedziela:\s*([^;]*)", p["godziny"] or "")
    return bool(m) and "nieczyn" not in m.group(1).lower()


def dla_seniora(p: dict) -> bool:
    """Bezpłatna, dostępna dla osób z niepełnosprawnością, nie toi-toi."""
    return p["platnosc"] == 0 and p["dostepnosc"] == 1 and p["typ"] != "przenośna"


WARIANTY = {
    "dowolna": lambda p: True,
    "dla seniora": dla_seniora,
    "dla seniora, całoroczna": lambda p: dla_seniora(p) and not sezonowa(p),
    "dla seniora, czynna w niedzielę": lambda p: dla_seniora(p) and czynna_w_niedziele(p),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Liczy lukę toaletową przy przystankach")
    parser.add_argument("--promien", type=int, default=500, help="zasięg w metrach (domyślnie: 500)")
    args = parser.parse_args()

    toalety = wczytaj_toalety()
    przystanki = wczytaj_przystanki()

    # Przystanki spoza Warszawy odcinamy prostokątem wokół toalet (przybliżenie
    # granic miasta — część gmin podmiejskich nadal zostaje).
    lat = [t[0] for t in toalety]
    lon = [t[1] for t in toalety]
    margines = 0.01
    przystanki = [
        s for s in przystanki
        if min(lat) - margines <= s[0] <= max(lat) + margines
        and min(lon) - margines <= s[1] <= max(lon) + margines
    ]
    print(f"Toalet: {len(toalety)}, słupków w obrębie Warszawy (przybliżenie): {len(przystanki)}")
    print(f"Zasięg: {args.promien} m w linii prostej\n")

    print(f"{'wariant':34s} {'toalet':>6s} {'bez toalety':>12s} {'mediana':>8s}")
    for nazwa, filtr in WARIANTY.items():
        wybrane = [t for t in toalety if filtr(t[2])]
        odl = sorted(
            min(odleglosc_m(s[0], s[1], t[0], t[1]) for t in wybrane) for s in przystanki
        )
        luka = sum(d > args.promien for d in odl)
        print(
            f"{nazwa:34s} {len(wybrane):6d} {100 * luka / len(odl):11.0f}% "
            f"{odl[len(odl) // 2]:7.0f}m"
        )


if __name__ == "__main__":
    main()
