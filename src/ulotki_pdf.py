"""Druk wsadowy ulotek „Najbliższa toaleta” do PDF (docs/14-plan-generatora-ulotek.md).

Uruchomienie (z katalogu projektu, najpierw src/ulotki_dane.py):
    .venv/Scripts/python.exe src/ulotki_pdf.py --id 7013-01,7013-02    # wybrane słupki
    .venv/Scripts/python.exe src/ulotki_pdf.py --dzielnica Wola         # jedna dzielnica
    .venv/Scripts/python.exe src/ulotki_pdf.py --wszystkie              # całe miasto, 18 plików

Jednorazowo: pip install playwright pypdf && python -m playwright install chromium

Wynik: data/out/ulotki/<dzielnica>.pdf (albo wybrane.pdf) + spis.csv (która
strona to który przystanek — dla ekipy rozwieszającej).

Kafelki mapy: regulamin serwerów OSM zabrania masowego pobierania, więc powyżej
LIMIT_OSM ulotek skrypt wymaga klucza MapTiler w .env (MAPTILER_KEY=...,
darmowe konto na maptiler.com).
"""

from __future__ import annotations

import argparse
import csv
import functools
import io
import json
import os
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import waw_api  # noqa: F401 — UTF-8 na konsoli; wczytuje też .env

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
WYJSCIE = ROOT / "data" / "out" / "ulotki"
LIMIT_OSM = 60
CZEKAJ_MS = 180_000  # na jedną paczkę


class CichySerwer(SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass


def uruchom_serwer() -> ThreadingHTTPServer:
    serwer = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(CichySerwer, directory=str(APP)))
    threading.Thread(target=serwer.serve_forever, daemon=True).start()
    return serwer


def wybierz(ulotki: list[dict], args: argparse.Namespace) -> dict[str, list[dict]]:
    """Grupy ulotek → nazwa pliku. Kolejność jak w ulotki.json (dzielnica, nazwa, słupek)."""
    if args.id:
        ids = set(args.id.split(","))
        wybrane = [u for u in ulotki if u["id"] in ids]
        brak = ids - {u["id"] for u in wybrane}
        if brak:
            sys.exit(f"Nie znam przystanków: {', '.join(sorted(brak))}")
        return {"wybrane": wybrane}
    grupy: dict[str, list[dict]] = {}
    for u in ulotki:
        if args.wszystkie or u["dzielnica"] == args.dzielnica:
            grupy.setdefault(u["dzielnica"], []).append(u)
    if not grupy:
        dzielnice = sorted({u["dzielnica"] for u in ulotki})
        sys.exit(f"Nie ma dzielnicy „{args.dzielnica}”. Dostępne: {', '.join(dzielnice)}")
    return grupy


def main() -> None:
    parser = argparse.ArgumentParser(description="Drukuje ulotki do PDF")
    cel = parser.add_mutually_exclusive_group(required=True)
    cel.add_argument("--id", help="numery słupków po przecinku, np. 7013-01,7013-02")
    cel.add_argument("--dzielnica", help="np. Wola")
    cel.add_argument("--wszystkie", action="store_true", help="wszystkie słupki, plik na dzielnicę")
    parser.add_argument("--paczka", type=int, default=40, help="ulotek na jedno otwarcie strony (domyślnie 40)")
    args = parser.parse_args()

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from playwright.sync_api import sync_playwright
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        sys.exit("Brak pakietów: pip install playwright pypdf && python -m playwright install chromium")

    plik_danych = APP / "dane" / "ulotki.json"
    if not plik_danych.exists():
        sys.exit("Brak app/dane/ulotki.json — najpierw uruchom src/ulotki_dane.py")
    grupy = wybierz(json.loads(plik_danych.read_text(encoding="utf-8")), args)
    razem = sum(len(g) for g in grupy.values())

    klucz = os.getenv("MAPTILER_KEY")
    if not klucz and razem > LIMIT_OSM:
        sys.exit(
            f"{razem} ulotek to za dużo kafelków dla serwerów OSM (limit tu: {LIMIT_OSM}).\n"
            "Dopisz do .env MAPTILER_KEY=... (darmowe konto: https://cloud.maptiler.com) "
            "albo wybierz mniej przystanków (--id)."
        )
    print(f"Ulotek: {razem} w {len(grupy)} plikach · mapa: {'MapTiler' if klucz else 'OpenStreetMap'}")

    WYJSCIE.mkdir(parents=True, exist_ok=True)
    serwer = uruchom_serwer()
    spis, bez_mapy = [], []
    start = time.time()
    with sync_playwright() as p:
        przegladarka = p.chromium.launch()
        strona = przegladarka.new_page()
        if klucz:
            # klucz trafia tylko do pamięci przeglądarki, nie do plików aplikacji
            strona.add_init_script(f"window.MAPTILER_KEY = {json.dumps(klucz)};")
        gotowe = 0
        for nazwa, lista in grupy.items():
            pdf = PdfWriter()
            for i in range(0, len(lista), args.paczka):
                paczka = lista[i : i + args.paczka]
                ids = ",".join(u["id"] for u in paczka)
                strona.goto(f"http://127.0.0.1:{serwer.server_port}/druk.html?ids={ids}")
                try:
                    strona.wait_for_function("window.gotowe === true", timeout=CZEKAJ_MS)
                except PlaywrightTimeout:
                    sys.exit(f"Strona druku nie odpowiedziała w {CZEKAJ_MS // 1000} s (paczka od {paczka[0]['id']})")
                bez_mapy += strona.evaluate("window.bledy")
                pdf.append(PdfReader(io.BytesIO(strona.pdf(prefer_css_page_size=True, print_background=True))))
                gotowe += len(paczka)
                print(f"  {nazwa}: {min(i + args.paczka, len(lista))}/{len(lista)}  (razem {gotowe}/{razem})")

            if len(pdf.pages) != len(lista):
                print(f"  UWAGA: {nazwa}.pdf ma {len(pdf.pages)} stron, a ulotek jest {len(lista)} "
                      "— któraś ulotka nie mieści się na jednej stronie A4")
            plik = WYJSCIE / f"{nazwa}.pdf"
            with plik.open("wb") as f:
                pdf.write(f)
            spis += [
                {"plik": plik.name, "strona": n, "id": u["id"], "przystanek": u["nazwa"], "dzielnica": u["dzielnica"]}
                for n, u in enumerate(lista, start=1)
            ]
        przegladarka.close()
    serwer.shutdown()

    with (WYJSCIE / "spis.csv").open("w", newline="", encoding="utf-8-sig") as f:
        pisarz = csv.DictWriter(f, fieldnames=["plik", "strona", "id", "przystanek", "dzielnica"], delimiter=";")
        pisarz.writeheader()
        pisarz.writerows(spis)

    print(f"Gotowe w {time.time() - start:.0f} s → {WYJSCIE.relative_to(ROOT)}")
    if bez_mapy:
        print(f"Mapa nie wczytała się na {len(bez_mapy)} ulotkach (wydrukuj ponownie przez --id): {','.join(bez_mapy)}")


if __name__ == "__main__":
    main()
