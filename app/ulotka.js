// Szablon ulotki „Najbliższa toaleta” — wspólny dla index.html (podgląd)
// i druk.html (druk wsadowy). Ulotka niczego nie liczy: wszystkie pola
// przychodzą gotowe z app/dane/ulotki.json (src/ulotki_dane.py).
// Ulotka wisi na przystanku, więc informacje o toalecie pokazujemy
// piktogramami, a tekst ograniczamy do minimum.

(function () {
  // Druk wsadowy (src/ulotki_pdf.py) podaje klucz MapTiler; podgląd używa OSM.
  function warstwaKafelkow() {
    if (window.MAPTILER_KEY) {
      return L.tileLayer(
        "https://api.maptiler.com/maps/streets-v2/256/{z}/{x}/{y}.png?key=" + window.MAPTILER_KEY,
        { maxZoom: 19, crossOrigin: true }
      );
    }
    return L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 });
  }

  const TYP = {
    "przenośna": "Toaleta przenośna (kabina)",
    "toaleta METRO": "Toaleta w metrze",
    "stacjonarna automatyczna": "Toaleta automatyczna",
  };

  // Piktogramy kafelków (viewBox 48×48, kolor z CSS przez currentColor).
  const IKONY = {
    bezplatna: '<circle cx="24" cy="24" r="20" fill="none" stroke="currentColor" stroke-width="3.5"/>' +
      '<text x="24" y="30" text-anchor="middle" font-size="16" font-weight="700" fill="currentColor">0 zł</text>',
    platna: '<circle cx="24" cy="24" r="20" fill="currentColor"/>' +
      '<text x="24" y="31" text-anchor="middle" font-size="19" font-weight="700" fill="#fff">zł</text>',
    // przewijak: standardowy piktogram — dorosły przewija niemowlę na blacie
    przewijak: '<circle cx="22" cy="5.8" r="3.6" fill="currentColor"/>' +
      '<path d="M17 10 L 22 10 L 23 30 L 10.7 30 Z" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>' +
      '<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">' +
      '<line x1="17" y1="30" x2="17" y2="43.5" stroke-width="3.8"/>' +
      '<line x1="21.5" y1="11.5" x2="28.8" y2="18" stroke-width="3.4"/>' +
      '<line x1="26.5" y1="26" x2="34" y2="26" stroke-width="3.2"/>' +
      '<line x1="32.6" y1="25" x2="32.6" y2="20.8" stroke-width="2.4"/>' +
      '<polyline points="26.5,26 24.3,21.6 29.4,23" stroke-width="2.6"/></g>' +
      '<circle cx="36.4" cy="25.4" r="2.5" fill="currentColor"/>' +
      '<rect x="24.3" y="28.6" width="14.4" height="1.8" fill="currentColor"/>',
    wozek: '<circle cx="21" cy="8" r="4" fill="currentColor"/>' +
      '<path d="M21 14 L 21 27 L 33 27 L 37 39" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>' +
      '<path d="M21 19 L 30 19" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"/>' +
      '<path d="M15 21 A 12 12 0 1 0 31 37" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"/>',
    przekreslenie: '<line x1="6" y1="42" x2="42" y2="6" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>',
  };

  function el(tag, klasa, tekst) {
    const e = document.createElement(tag);
    if (klasa) e.className = klasa;
    if (tekst != null) e.textContent = tekst;
    return e;
  }

  function dwujezyczny(tag, klasa, pl, en) {
    const e = el(tag, klasa, pl);
    e.append(el("span", "en", en));
    return e;
  }

  function odleglosc(m) {
    return m >= 1000 ? (m / 1000).toFixed(1).replace(".", ",") + " km" : m + " m";
  }

  // Kafelek: piktogram + znacznik ✔/✘ + krótki podpis PL/EN.
  function kafelek(ok, ikona, pl, en) {
    const k = el("div", "kafelek " + (ok ? "tak" : "nie"));
    k.innerHTML =
      '<span class="ikona"><svg viewBox="0 0 48 48" aria-hidden="true">' + ikona + "</svg>" +
      '<span class="znacznik">' + (ok ? "✔" : "✘") + "</span></span>";
    k.append(dwujezyczny("span", "podpis", pl, en));
    return k;
  }

  // 'pon.–pt. 8–16 · sob. 8–14' → wiersz łamany tylko na „·”, nigdy w środku godzin.
  function grupyGodzin(tekst, klasa) {
    const e = el("span", klasa);
    tekst.split(" · ").forEach((g, i) => {
      if (i) e.append(" · ");
      e.append(el("span", "grupa", g));
    });
    return e;
  }

  function linkNawigacji(r) {
    return (
      "https://www.google.com/maps/dir/?api=1&origin=" + r.lat + "," + r.lon +
      "&destination=" + r.glowna.lat + "," + r.glowna.lon + "&travelmode=walking"
    );
  }

  function naglowek(r) {
    const h = el("header", "u-naglowek");
    const img = el("img", "u-maskotka");
    img.src = "img/wc_syrenka.jpeg";
    img.alt = "";
    const tytul = el("div", "u-tytul");
    tytul.append(el("h1", "", "NAJBLIŻSZA TOALETA"), el("p", "en", "Nearest toilet · WC"));
    const przystanek = el("div", "u-przystanek");
    przystanek.append(
      el("span", "etykieta", "Przystanek / Stop"),
      el("strong", "", r.nazwa + " " + r.id.split("-")[1]),
      el("span", "u-id", "nr " + r.id)
    );
    h.append(img, tytul, przystanek);
    return h;
  }

  function sekcjaOdleglosci(r) {
    const t = r.glowna;
    const s = el("section", "u-odleglosc");
    const wiersz = el("div", "u-liczby");
    wiersz.append(
      el("span", "u-metry", "ok. " + odleglosc(t.odl_m)),
      dwujezyczny("span", "u-minuty", t.min + " min pieszo", "approx. " + t.min + " min walk")
    );
    s.append(wiersz, el("p", "u-adres", t.adres));
    const dopiski = [TYP[t.typ], t.wskazowka].filter(Boolean);
    if (dopiski.length) s.append(el("p", "u-wskazowka", dopiski.join(" · ")));
    return s;
  }

  function dol(r) {
    const t = r.glowna;
    const s = el("section", "u-dol");
    const kafelki = el("div", "u-kafelki");
    kafelki.append(
      t.platna
        ? kafelek(false, IKONY.platna, "PŁATNA", "Paid")
        : kafelek(true, IKONY.bezplatna, "BEZPŁATNA", "Free"),
      t.przewijak
        ? kafelek(true, IKONY.przewijak, "PRZEWIJAK", "Baby changing")
        : kafelek(false, IKONY.przewijak + IKONY.przekreslenie, "BEZ PRZEWIJAKA", "No baby changing"),
      t.dla_wozkow
        ? kafelek(true, IKONY.wozek, "DLA WÓZKÓW", "Wheelchair")
        : kafelek(false, IKONY.wozek + IKONY.przekreslenie, "NIE DLA WÓZKÓW", "No wheelchair access")
    );
    const godziny = el("p", "u-godziny");
    godziny.innerHTML =
      '<svg viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="19" fill="none" stroke="currentColor" stroke-width="4"/>' +
      '<path d="M24 12 L 24 24 L 32 29" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/></svg>';
    // Toaleta sezonowa: okres działania dopisany do godzin (osobnego kafelka już nie ma).
    const pl = grupyGodzin(t.godziny + (t.sezon_krotko ? " · sezonowo: " + t.sezon_krotko : ""));
    pl.append(grupyGodzin(t.godziny_en + (t.sezon_krotko_en ? " · seasonal: " + t.sezon_krotko_en : ""), "en"));
    godziny.append(pl);

    const qr = el("div", "u-qr");
    const kod = el("div", "kod");
    new QRCode(kod, { text: linkNawigacji(r), width: 360, height: 360, correctLevel: QRCode.CorrectLevel.M });
    qr.append(kod, dwujezyczny("p", "", "Prowadź mnie", "Navigate me"));
    s.append(kafelki, qr, godziny);
    return s;
  }

  function stopka(r) {
    const f = el("footer", "u-stopka");
    f.append(
      el("span", "", "Dane: dane.um.warszawa.pl (toalety: kwiecień 2026) · Mapa © OpenStreetMap" +
        (window.MAPTILER_KEY ? " © MapTiler" : "")),
      el("strong", "", "Błąd na ulotce? Zadzwoń 19115, podaj nr " + r.id)
    );
    return f;
  }

  // Toaleta: pinezka z „WC”, której ostry koniec wskazuje dokładny punkt.
  // Przystanek: kropka, której środek jest w punkcie, z podpisem.
  function pinezka(klasa, znak, pl, en, podpisZLewej) {
    const ksztalt = klasa === "pin-wc"
      ? '<svg class="znak" viewBox="0 0 44 58" aria-hidden="true">' +
        '<path d="M22 56 C 18 46, 2 34, 2 22 A 20 20 0 1 1 42 22 C 42 34, 26 46, 22 56 Z" fill="#fff" stroke="#111" stroke-width="4" stroke-linejoin="round"/>' +
        '<text x="22" y="28" text-anchor="middle" font-size="15" font-weight="700" fill="#111">' + znak + "</text></svg>"
      : '<span class="znak"></span>';
    return L.divIcon({
      className: "pin " + klasa + (podpisZLewej ? " lewa" : ""),
      html: ksztalt + (pl ? '<span class="podpis">' + pl + "<i>" + en + "</i></span>" : ""),
      iconSize: null,
    });
  }

  // Zwraca Promise<boolean>: true, gdy kafelki mapy się wczytały.
  // Mapę tworzymy dopiero po wczytaniu fontu: font zmienia wysokość tekstu,
  // a z nią rozmiar mapy — Leaflet zmierzony wcześniej zostawiłby szary pas.
  async function mapa(r, kontener) {
    await document.fonts.ready;
    const m = L.map(kontener, {
      zoomControl: false, attributionControl: false, dragging: false, scrollWheelZoom: false,
      doubleClickZoom: false, boxZoom: false, keyboard: false, touchZoom: false,
      fadeAnimation: false, zoomAnimation: false, zoomSnap: 0.25,
    });
    const tu = [r.lat, r.lon];
    const wc = [r.glowna.lat, r.glowna.lon];
    // Podpis przystanku po stronie odwrotnej do toalety, żeby nie zasłaniał
    // pinezki; margines po stronie podpisu go mieści, górny — pinezkę WC nad punktem.
    const wcZLewej = r.glowna.lon < r.lon;
    const PODPIS = 190, BOK = 50;
    // Trasa piesza po ulicach (src/trasy_piesze.py), a bez niej linia prosta.
    // Zaczyna się na przystanku i kończy przy toalecie.
    const linia = r.glowna.trasa || [tu, wc];
    m.fitBounds(linia, {
      paddingTopLeft: [wcZLewej ? BOK : PODPIS, 75],
      paddingBottomRight: [wcZLewej ? PODPIS : BOK, 30],
      maxZoom: 18.5,
    });
    L.polyline(linia, { color: "#111", weight: 5, dashArray: "4 10", lineCap: "round" }).addTo(m);
    L.marker(tu, { icon: pinezka("pin-tu", "", "JESTEŚ TUTAJ", "You are here", !wcZLewej) }).addTo(m);
    L.marker(wc, { icon: pinezka("pin-wc", "WC"), zIndexOffset: 1000 }).addTo(m);
    return new Promise((resolve) => {
      const limit = setTimeout(() => resolve(false), 30000);
      warstwaKafelkow()
        .once("load", () => { clearTimeout(limit); resolve(true); })
        .addTo(m);
    });
  }

  function renderuj(r, kontener) {
    const u = el("article", "ulotka");
    const mapaEl = el("div", "u-mapa");
    u.append(naglowek(r), sekcjaOdleglosci(r), mapaEl, dol(r), stopka(r));
    kontener.append(u);
    return mapa(r, mapaEl);
  }

  async function wczytajUlotki() {
    if (location.protocol === "file:") throw new Error(BLAD_FILE);
    const odp = await fetch("dane/ulotki.json");
    if (!odp.ok) throw new Error("Brak dane/ulotki.json — uruchom src/ulotki_dane.py");
    return odp.json();
  }

  // Przeglądarka nie wczyta JSON-a ze strony otwartej z dysku (file://).
  const BLAD_FILE =
    "Strona otwarta z dysku, więc przeglądarka blokuje wczytanie danych. Uruchom serwer " +
    "w katalogu projektu: uv run python -m http.server 8000 --directory app " +
    "i otwórz http://localhost:8000";

  window.Ulotka = { renderuj, wczytajUlotki, odleglosc, BLAD_FILE };
})();
