"""Pobiera 18 małych zbiorów z dane.um.warszawa.pl, każdy do osobnego pliku JSON.

"Małe" = jedno wywołanie bez parametrów zwraca cały zbiór. Projekt
potrzebuje tylko dwóch: toalety i przystanki.

Uruchomienie (z katalogu projektu):
    .venv/Scripts/python.exe src/pobierz_male.py              # wszystkie 18
    .venv/Scripts/python.exe src/pobierz_male.py --lista      # tylko pokaż listę
    .venv/Scripts/python.exe src/pobierz_male.py toalety przystanki   # wybrane

Wynik: data/raw/male/<nazwa>.json + wpisy w data/raw/opis_plikow.json
(wspólny opis małych i dużych zbiorów — wpisy dużych skrypt zostawia bez zmian).
Ponowne uruchomienie nadpisuje pliki — zbiory są małe, a dane mają być świeże.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from waw_api import WawApiNew

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "male"

# (nazwa pliku, endpoint, kategoria, tytuł w katalogu)
# Endpointy odczytane z plików call_examples (*_pw.json) portalu, 13.10.2026.
ZBIORY = [
    ("konsultacje_spoleczne", "get_cks_konsultacje_spoleczne", "Aktywni mieszkańcy", "Konsultacje społeczne"),
    ("konsultacje_dzielnice", "get_cks_konsultacje_spoleczne_dzielnice", "Aktywni mieszkańcy", "Konsultacje społeczne dzielnice"),
    ("konsultacje_kategorie", "get_cks_konsultacje_spoleczne_kategorie", "Aktywni mieszkańcy", "Konsultacje społeczne kategorie"),
    ("trasy_turystyczne", "get_sbt_trasy_turystyczne", "Aktywni mieszkańcy", "Trasy turystyczne"),
    ("otwarte_boiska", "get_be_otwarte_boiska", "Sport", "Otwarte boiska"),
    ("zajecia_sportowe", "get_bmm_zajecia_sportowe", "Sport", "Zajęcia sportowe"),
    ("pojazdy_transportu_publicznego", "get_ztm_pojazdy", "Transport", "Pojazdy transportu publicznego"),
    ("przystanki", "get_ztm_przystanki_komunikacji_miejskiej", "Transport", "Lokalizacja przystanków komunikacji miejskiej"),
    ("utrudnienia_drogowe", "get_bin_utrudnienia_drogowe", "Transport", "Utrudnienia w ruchu drogowym"),
    ("parkingi_wolne_miejsca", "get_m_parkingi_wolne_miejsca", "Transport", "Wolne miejsca parkingowe"),
    ("kalendarz_wydarzen", "get_bmm_kalendarz_wydarzen", "Wydarzenia", "Kalendarz wydarzeń"),
    ("defibrylatory_aed", "get_scb_lokalizacja_defibrylatorow", "Zdrowie", "Lokalizacja defibrylatorów (AED)"),
    ("eko_punkty", "get_bos_ekopunkty", "Środowisko", "Eko punkty"),
    ("segregacja_odpadow", "get_bmm_segregacja_odpadow", "Środowisko", "Segregacja odpadów"),
    ("toalety", "get_m_toalety", "Środowisko", "Toalety"),
    ("typy_odpadow", "get_bmm_typy_odpadow", "Środowisko", "Typy odpadów"),
    ("jakosc_powietrza", "get_bopipk_monitoring_jakosci_powietrza", "Środowisko", "Monitoring jakości powietrza"),
    ("pogoda", "get_zom_pogoda", "Środowisko", "Pogoda"),
]


def _ile_rekordow(dane) -> int | dict | None:
    """Liczba rekordów.

    Zwykle zbiór to lista. Bywa też słownik list — np. pojazdy
    ({"busy": [...], "tramwaje": [...]}) albo parkingi ({"carParks": [...]}).
    Wtedy liczymy każdą listę osobno, bo ich suma nie miałaby sensu.
    """
    if isinstance(dane, list):
        return len(dane)
    if isinstance(dane, dict):
        listy = {k: len(v) for k, v in dane.items() if isinstance(v, list)}
        if len(listy) == 1:
            return next(iter(listy.values()))
        return listy or None
    return None


def _opis(rekordy) -> str:
    if isinstance(rekordy, dict):
        return ", ".join(f"{k}: {v}" for k, v in rekordy.items())
    return f"{rekordy if rekordy is not None else '?'} rekordów"


def main() -> None:
    ap = argparse.ArgumentParser(description="Pobiera 18 małych zbiorów, każdy do osobnego JSON-a")
    ap.add_argument("nazwy", nargs="*", help="pobierz tylko te zbiory (nazwy z --lista)")
    ap.add_argument("--lista", action="store_true", help="pokaż zbiory i nic nie pobieraj")
    args = ap.parse_args()

    if args.lista:
        for nazwa, endpoint, kategoria, _ in ZBIORY:
            print(f"  {nazwa:32} {kategoria:20} {endpoint}")
        return

    wybrane = ZBIORY
    if args.nazwy:
        znane = {z[0] for z in ZBIORY}
        nieznane = [n for n in args.nazwy if n not in znane]
        if nieznane:
            print(f"[STOP] Nieznane zbiory: {', '.join(nieznane)}. Zobacz --lista.")
            return
        wybrane = [z for z in ZBIORY if z[0] in args.nazwy]

    try:
        api = WawApiNew()
    except RuntimeError as exc:
        print(f"[STOP] {exc}")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    opis_path = OUT_DIR.parent / "opis_plikow.json"
    # Zachowujemy wpisy pozostałych zbiorów, także dużych.
    opis = {}
    if opis_path.exists():
        opis = json.loads(opis_path.read_text(encoding="utf-8"))

    ok = 0
    for i, (nazwa, endpoint, kategoria, tytul) in enumerate(wybrane, 1):
        print(f"[{i:2}/{len(wybrane)}] {tytul} ... ", end="", flush=True)
        wpis = {
            "typ": "maly",
            "tytul": tytul,
            "kategoria": kategoria,
            "endpoint": endpoint,
            "pobrano": datetime.now().isoformat(timespec="seconds"),
        }
        try:
            dane = api.call(endpoint)
        except Exception as exc:  # jeden zbiór nie zatrzymuje reszty
            wpis.update(status="blad", blad=str(exc)[:300])
            print(f"BŁĄD: {exc}")
        else:
            plik = OUT_DIR / f"{nazwa}.json"
            plik.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
            rekordy = _ile_rekordow(dane)
            wpis.update(status="ok", plik=f"{OUT_DIR.name}/{plik.name}", rekordy=rekordy, bajty=plik.stat().st_size)
            print(f"OK, {_opis(rekordy)} -> {plik.name}")
            ok += 1
        opis[nazwa] = wpis
        time.sleep(0.5)  # nie zasypujemy portalu zapytaniami

    opis_path.write_text(json.dumps(opis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGotowe: {ok}/{len(wybrane)} zbiorów w {OUT_DIR}")
    if ok < len(wybrane):
        print("Szczegóły błędów: data/raw/opis_plikow.json. HTTP 500 bywa tu błędem parametrów, nie awarią.")


if __name__ == "__main__":
    main()
