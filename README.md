# MileWatch PL

Darmowy tracker promocji **Miles & More** (Lufthansa) jako prosta **aplikacja desktop**.

Monitoruje publicznie dostepne kanaly RSS i strony o programie Miles & More, wykrywa promocje
(kup mile z bonusem, bonusy partnerskie, okazje milowe, promocje kart), odrzuca duplikaty i
pokazuje je w jednym oknie z filtrami. Promocje zgodne z Twoim profilem sa wyrozniane.

Dodatkowo wykrywa **perelki lotnicze**: bledy cenowe / mega-tanie loty dalekodystansowe oraz
bardzo tanie promocyjne loty w klasie biznes. Sa one zawsze wyrozniane (kolor) i alertowane.

## Najwazniejsze cechy

- **Perelki lotnicze** - obok promocji Miles & More wykrywa TOP okazje: bledy cenowe / mistake
  fares, mega-tanie loty dalekodystansowe (np. Azja < 1500 zl) i tania klasa biznes
  (< 4000 zl / 900 EUR). Progi ustawisz w `deals.py`.

- **W pelni darmowa** - zero platnych API i kluczy. Wykrywanie promocji dziala lokalnie na
  slowach kluczowych i wyrazeniach regularnych (`extract.py`).
- **Lekka i responsywna** - interfejs w Tkinter (czesc standardowej biblioteki Pythona,
  bez ciezkich zaleznosci). Scraping chodzi w tle, okno sie nie zawiesza.
- **Scraping popularnych serwisow** - RSS + scraping stron (z poszanowaniem `robots.txt`,
  cache i rate-limitem).
- **Front na "jedno klikniecie"** - mozesz zbudowac pojedynczy plik `MileWatchPL.exe`
  (patrz nizej) i uruchamiac dwuklikiem, bez instalowania Pythona.
- **Prosty eksport na inne urzadzenie** - przycisk *Eksportuj / Udostepnij* zapisuje
  samodzielny plik HTML; opcjonalnie GitHub Actions publikuje go jako darmowy wspoldzielony
  link (GitHub Pages).

## Szybki start (tryb deweloperski)

```bash
pip install -r requirements.txt
python gui.py
```

W oknie:

- **Odswiez promocje** - pobiera i wykrywa nowe promocje (scraping w tle).
- **Filtry** (typ / partner / region / szukaj / tylko z profilu / tylko perelki) - zawezaja liste.
  Perelki (bledy cenowe = czerwone, tania biznes = zlote) sa sortowane na gore.
- **Dwuklik** na promocji - otwiera zrodlo w przegladarce.
- **Eksportuj / Udostepnij** - zapisuje plik HTML do wyslania na inne urzadzenie.

Baza danych: `data/milewatch.db` (SQLite, tworzona automatycznie). Cache odpowiedzi HTTP:
katalog `cache/` (RSS: 1h, strony: 6h), zeby nie obciazac zrodel przy kazdym odswiezeniu.

## Budowanie aplikacji .exe (jedno klikniecie)

Na Windowsie:

```bat
build_exe.bat
```

Skrypt instaluje PyInstaller (darmowy) i tworzy `dist\MileWatchPL.exe`. Skopiuj ten plik
gdziekolwiek i uruchamiaj dwuklikiem - przy pierwszym starcie obok `.exe` powstanie edytowalny
`config.yaml` oraz katalogi `data/` i `cache/`.

> Plik `.exe` budujesz **na Windowsie** (PyInstaller tworzy plik dla systemu, na ktorym dziala).

## Eksport na inne urzadzenie

Dwie darmowe drogi:

1. **Plik do wyslania** - kliknij *Eksportuj / Udostepnij*, zapisz `milewatch_promocje.html`
   i wyslij go mailem / komunikatorem. Plik dziala offline na kazdym urzadzeniu (filtry w
   przegladarce, bez serwera).
2. **Wspoldzielony link (GitHub Pages)** - workflow `.github/workflows/update.yml` codziennie
   robi scraping i publikuje `docs/index.html`. Wlacz w repo: **Settings -> Pages -> Source:
   "Deploy from a branch", branch = `main`, folder = `/docs`**. Dostaniesz staly adres, ktory
   otworzysz na kazdym urzadzeniu - zawsze aktualny. (Mozesz tez odpalic recznie:
   `python publish.py`.)

## Konfiguracja (`config.yaml`)

### Zrodla

```yaml
sources:
  - name: "Nazwa zrodla"
    type: rss      # albo: scrape
    url: "https://..."
    enabled: true
```

- `type: rss` - parsowane przez `feedparser` (kanaly RSS/Atom; lekkie, preferowane).
- `type: scrape` - pobierane przez `httpx`, czyszczone z nav/script/footer przez
  BeautifulSoup; caly tekst strony idzie do darmowej ekstrakcji slow kluczowych.

**Uwaga:** URL oficjalnej strony Miles & More PL w `config.yaml` to najlepsze przypuszczenie,
nie zweryfikowane na zywo. Sprawdz i popraw przed pierwszym realnym uruchomieniem.

### Dodawanie zrodla

1. Sprawdz `robots.txt` domeny (`fetch_scrape.py` i tak to weryfikuje i pomija zablokowane).
2. Dodaj wpis do `sources:` (RSS preferowany, gdy dostepny).
3. Nie trzeba pisac kodu - `fetch_rss.py`/`fetch_scrape.py` obsluguja kazde zrodlo generycznie,
   a `extract.py` wyciaga z tekstu strukturalne promocje.

### Profil uzytkownika

```yaml
profile:
  typy_promocji: [buy_miles, mileage_bargain, partner_bonus]
  partnerzy: ["Lufthansa", "LOT", "Hertz", "Marriott"]
  regiony: ["Europa", "Polska"]
  trasy: []
  min_bonus_pct: 20
```

Promocje zgodne z profilem sa wyrozniane (zielony wiersz/pasek + znaczek "profil").
Puste listy = brak filtra na danym polu.

## Architektura

1. **Fetch** (`fetch_rss.py`, `fetch_scrape.py`) - surowe dane ze zrodel (cache + rate-limit).
2. **Extract** (`extract.py`) - darmowe wykrywanie promocji Miles & More (slowa kluczowe +
   regex, PL/DE/EN): typ, bonus %, partner, data waznosci, regiony. Odsiewa newsy.
3. **Deals** (`deals.py`) - perelki: bledy cenowe / mega-tanie loty dalekodystansowe oraz
   tania klasa biznes (z parsowaniem ceny w PLN/EUR i progami).
4. **Scoring** (`scoring.py`) - ocena okazji 0-100 (kategoria, bonus %, dalekodystansowosc,
   kara za wylot spoza regionu). Steruje gwiazdka w alercie, sortowaniem i progiem `min_score`.
5. **Dedup** (`dedup.py`) - rapidfuzz + dopasowanie strukturalne wykrywaja te sama promocje.
5. **Storage** (`storage.py`) - SQLite, unikalny `hash_dedup`.
6. **Front** (`gui.py`) - aplikacja desktop Tkinter z filtrami, perelkami i eksportem.
7. **Export** (`export_html.py`, `publish.py`) - samodzielny HTML / GitHub Pages.
8. **Alerty** (`telegram_alert.py`, `signal_alert.py`, opcjonalnie, darmowe) - powiadomienia
   o nowych promocjach i perelkach na Telegram i/lub Signal.

Testy regresyjne: `python tests.py` (bez sieci/kluczy). Diagnostyka zrodel: `python diag.py`.

## Alerty: Telegram i Signal (opcjonalne, darmowe)

Mozesz wlaczyc jeden lub oba kanaly. Konfiguracje wpisujesz do pliku `.env`
(wzor: `.env.example`). Bez konfiguracji krok alertow jest po prostu pomijany.

Wysylane sa tylko **nowe, profilowo-zgodne** promocje. Mechanizm jest idempotentny: raz
wyslana promocja nie trafi ponownie, a nieudana wysylka jest ponawiana nastepnym razem.
Promocja jest oznaczana jako wyslana, gdy dotrze przez **co najmniej jeden** kanal.

### Telegram (bot przez @BotFather)

1. W Telegramie napisz do **@BotFather**, wyslij `/newbot`, odbierz token.
2. Napisz cokolwiek do swojego nowego bota (musi miec z Toba otwarta rozmowe).
3. `curl "https://api.telegram.org/bot<TOKEN>/getUpdates"` - znajdz `"chat":{"id":...}`.
4. Wpisz do `.env`: `TELEGRAM_BOT_TOKEN=...` oraz `TELEGRAM_CHAT_ID=...`.

### Signal (darmowy relay przez CallMeBot)

Signal nie ma wlasnego darmowego API dla botow, wiec uzywamy darmowego relaya CallMeBot.

1. Dodaj numer CallMeBot do kontaktow Signal: **+34 644 51 95 23**.
2. Wyslij do niego wiadomosc: `I allow callmebot to send me messages`.
3. W odpowiedzi dostaniesz swoj **API key**.
4. Wpisz do `.env`: `SIGNAL_PHONE=+48...` (Twoj numer) oraz `SIGNAL_API_KEY=...`.

Uwaga: wiadomosci Signal przechodza przez zewnetrzny serwis CallMeBot (to kompromis - Signal
nie udostepnia wlasnego darmowego API). Telegram dziala bezposrednio przez oficjalne API bota.

## Automatyczne, codzienne sprawdzanie (zalecane)

Promocje Miles & More pojawiaja sie nieregularnie - najwieksza wartosc to **bycie
powiadamianym automatycznie**, gdy pojawi sie nowa. Dwie darmowe drogi:

### A. GitHub Actions (w chmurze - nie wymaga wlaczonego komputera)

Workflow `.github/workflows/update.yml` codziennie robi scraping, aktualizuje strone
(`docs/index.html`) i wysyla alerty. Aby wlaczyc alerty, dodaj sekrety w repo:
**Settings -> Secrets and variables -> Actions -> New repository secret** i wpisz
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` oraz/lub `SIGNAL_PHONE`, `SIGNAL_API_KEY`.

### B. Harmonogram zadan Windows (lokalnie)

Uzyj `run_daily.bat`: w Harmonogramie zadan utworz zadanie podstawowe (wyzwalacz: codziennie),
akcja "Uruchom program" -> wskaz `run_daily.bat`. Konfiguracje alertow trzymaj w `.env`.
