"""Klient API otwartych danych m.st. Warszawy (api.um.warszawa.pl).

Uwaga na pułapkę tego API: błędy przychodzą z HTTP 200 i polem
{"result": "false", "error": "..."}, więc samo raise_for_status() nie wystarczy.
Pole "result" bywa listą (sukces) albo stringiem "false" (błąd).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv()

# Konsola Windows bywa ustawiona na cp1250/cp1251 i wywala się na polskich
# znakach (UnicodeEncodeError). Przestawiamy strumienie na UTF-8.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://api.um.warszawa.pl/api/action"
# Nowszy portal: POST + token w nagłówku Authorization (inny model niż BASE_URL).
NEW_BASE_URL = "https://dane.um.warszawa.pl/api/action"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class WawApiError(RuntimeError):
    """API zwróciło result=false (zły apikey, zły resource_id, limit zapytań)."""


class WawApi:
    def __init__(self, api_key: str | None = None, timeout: int = 30):
        self.api_key = api_key or os.getenv("WAW_API_KEY")
        if not self.api_key or self.api_key.startswith("tu_wklej"):
            raise RuntimeError(
                "Brak klucza. Skopiuj .env.example -> .env i wklej apikey "
                "z https://api.um.warszawa.pl"
            )
        self.timeout = timeout
        self.session = requests.Session()

    # Ponawiamy tylko błędy sieciowe. Zły apikey czy resource_id to błąd
    # trwały — retry nic nie da. reraise=True zapobiega opakowaniu wyjątku
    # w RetryError, dzięki czemu `except WawApiError` u wywołującego działa.
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def call(self, endpoint: str, **params):
        """Surowe wywołanie endpointu. Zwraca zawartość pola 'result'."""
        params["apikey"] = self.api_key
        resp = self.session.get(
            f"{BASE_URL}/{endpoint}/", params=params, timeout=self.timeout
        )
        resp.raise_for_status()

        try:
            payload = resp.json()
        except json.JSONDecodeError as exc:  # czasem HTML przy awarii backendu
            raise WawApiError(f"Odpowiedź nie jest JSON-em: {resp.text[:200]}") from exc

        result = payload.get("result")
        # Błąd sygnalizowany jest stringiem "false" w polu result.
        if isinstance(result, str) and result.lower() == "false":
            raise WawApiError(payload.get("error", "nieznany błąd API"))
        if result is None:
            raise WawApiError(f"Brak pola 'result': {payload}")
        return result

    # --- konkretne zasoby -------------------------------------------------

    def buses(self, line: str | None = None, brigade: str | None = None):
        """Pozycje GPS autobusów (type=1). Dane odświeżają się co ~10 s."""
        return self._vehicles(vehicle_type="1", line=line, brigade=brigade)

    def trams(self, line: str | None = None, brigade: str | None = None):
        """Pozycje GPS tramwajów (type=2)."""
        return self._vehicles(vehicle_type="2", line=line, brigade=brigade)

    def _vehicles(self, vehicle_type: str, line=None, brigade=None):
        params = {
            "resource_id": "f2e5503e-927d-4ad3-9500-4ab9e55deb59",
            "type": vehicle_type,
        }
        if line:
            params["line"] = line
        if brigade:
            params["brigade"] = brigade
        return self.call("busestrams_get", **params)

    def dbstore(self, resource_id: str, **params):
        """Zasoby słownikowe/statyczne (np. przystanki, parkingi, WC)."""
        return self.call("dbstore_get", id=resource_id, **params)

    def dbtimetable(self, resource_id: str, **params):
        """Rozkłady jazdy ZTM (linie i odjazdy dla przystanku)."""
        return self.call("dbtimetable_get", id=resource_id, **params)

    def wfsstore(self, resource_id: str, **params):
        """Warstwy przestrzenne (geometrie) — zwraca GeoJSON-podobny format."""
        return self.call("wfsstore_get", id=resource_id, **params)


class WawApiNew:
    """Klient nowszego portalu dane.um.warszawa.pl.

    Różnice wobec WawApi (api.um.warszawa.pl):
      - metoda POST, nie GET (GET zwraca 405 Method Not Allowed),
      - token w nagłówku `Authorization`, nie w query stringu,
      - parametry w ciele JSON, nie w URL-u,
      - brak `resource_id` — zasób wybiera sama nazwa endpointu.

    Token pochodzi z dane.um.warszawa.pl/pl/key-api i może być inny niż
    apikey starego portalu — stąd osobna zmienna WAW_TOKEN (z fallbackiem).
    """

    def __init__(self, token: str | None = None, timeout: int = 30):
        self.token = token or os.getenv("WAW_TOKEN") or os.getenv("WAW_API_KEY")
        if not self.token or self.token.startswith("tu_wklej"):
            raise RuntimeError(
                "Brak tokenu. Ustaw WAW_TOKEN w .env — token pobierzesz z "
                "https://dane.um.warszawa.pl/pl/key-api"
            )
        self.timeout = timeout
        self.session = requests.Session()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def call(self, endpoint: str, **body):
        resp = self.session.post(
            f"{NEW_BASE_URL}/{endpoint}",
            json=body,
            headers={
                "Authorization": self.token,
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )

        # Ten portal sygnalizuje błędy statusem HTTP, nie polem result.
        if resp.status_code == 401:
            raise WawApiError("401 — nieprawidłowy lub brakujący token")
        if resp.status_code == 404:
            raise WawApiError(f"404 — endpoint '{endpoint}' nie istnieje")
        if resp.status_code >= 500:
            raise WawApiError(
                f"{resp.status_code} — awaria po stronie serwera "
                f"({resp.text[:120]}). Spróbuj później."
            )
        resp.raise_for_status()

        payload = resp.json()
        # Bywa {"result": [...]} albo gołe [...] — normalizujemy.
        if isinstance(payload, dict):
            if isinstance(payload.get("result"), str):
                raise WawApiError(payload.get("error", payload["result"]))
            return payload.get("result", payload)
        return payload

    # --- zasoby potwierdzone w dokumentacji portalu -----------------------

    def lokalizacja_pojazdow(self, typ: int = 1):
        """GPS pojazdów: typ=1 autobusy, typ=2 tramwaje. Odświeżane co 10 s.

        Zwraca rekordy z polami: Lat, Lon, Time, Lines, Brigade, VehicleNumber.
        """
        return self.call("get_ztm_lokalizacja_pojazdow", type=typ)

    def linie_na_przystanku(self, busstop_id: str, busstop_nr: str):
        """Linie zatrzymujące się na danym słupku przystankowym."""
        return self.call(
            "get_ztm_lista_linii_na_przystanku",
            busstopId=busstop_id,
            busstopNr=busstop_nr,
        )

    def ceny_nieruchomosci(
        self,
        dzielnica: str,
        rodzaj_nieruchomosci: str,
        rodzaj_rynku: str,
        rok: str | int,
    ):
        """Rejestr Cen Nieruchomości — zwraca GeoJSON.

        Dzielnica bez polskich znaków i łącznie, np. "pragapolnoc".
        Przykład: ceny_nieruchomosci("Bemowo", "nieruchomoscLokalowa",
                                     "rynekPierwotny", 2022)

        UWAGA: `rok` musi być liczbą w JSON-ie. Przykład curl w dokumentacji
        miasta podaje "rok": "2022" (string) — taki zapis zwraca HTTP 500
        "Service unavailable", co wygląda na awarię, a jest błędem typu.
        Zweryfikowane 13.10.2026: int działa, string nie.
        """
        return self.call(
            "get_bgk_rcn",
            dzielnica=dzielnica,
            rodzajNieruchomosci=rodzaj_nieruchomosci,
            rodzajRynku=rodzaj_rynku,
            rok=int(rok),
        )


# --- pomocnicze -----------------------------------------------------------


def snapshot(data, name: str) -> Path:
    """Zapisuje surową odpowiedź na dysk — dane realtime znikają bezpowrotnie."""
    path = CACHE_DIR / f"{name}_{int(time.time())}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    api = WawApi()
    pojazdy = api.buses()
    print(f"Pobrano {len(pojazdy)} autobusów.")
    if pojazdy:
        print("Przykładowy rekord:", json.dumps(pojazdy[0], ensure_ascii=False))
        print("Zapisano:", snapshot(pojazdy, "buses"))
