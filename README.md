# MileWatch PL

Tracker promocji Miles & More (Lufthansa) - Faza 1: pipeline terminalowy.

Monitoruje publicznie dostepne kanaly RSS i strony Miles & More, normalizuje znalezione
promocje przy pomocy Claude (do strukturalnego, polskojezycznego streszczenia WLASNYMI SLOWAMI -
nigdy kopiowania tresci zrodlowej), odrzuca duplikaty i pokazuje w terminalu tylko te nowe
promocje, ktore odpowiadaja Twojemu profilowi zainteresowan.

## Wymagania

- Python 3.11+
- Klucz API Anthropic (zmienna `ANTHROPIC_API_KEY`)

## Instalacja

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# wpisz swoj klucz w .env: ANTHROPIC_API_KEY=sk-ant-...
```

## Uruchomienie

```bash
python run.py
```

Przy pierwszym uruchomieniu wszystkie znalezione promocje sa "nowe" (pusta baza).
Kolejne uruchomienia pokaza tylko promocje, ktorych jeszcze nie widziano (dedup po hashu
i fuzzy-matching tytulow przez rapidfuzz).

Baza danych: `data/milewatch.db` (SQLite, tworzona automatycznie).
Cache surowych odpowiedzi HTTP: katalog `cache/` (RSS: 1h, strony scrapowane: 6h) - zeby nie
bic w te same endpointy przy kazdym uruchomieniu.

## Konfiguracja (`config.yaml`)

### Zrodla

```yaml
sources:
  - name: "Nazwa zrodla"
    type: rss      # albo: scrape
    url: "https://..."
    enabled: true
```

- `type: rss` - parsowane przez `feedparser` (kanaly RSS/Atom).
- `type: scrape` - pobierane przez `httpx`, czyszczone z nav/script/script/footer przez
  BeautifulSoup i caly tekst strony oddawany do normalizacji przez Claude (zamiast kruchych
  selektorow CSS, ktore latwo sie psuja przy zmianie strony).

**Uwaga:** URL trzeciego zrodla (oficjalna strona Miles & More PL) jest najlepszym przypuszczeniem
i nie zostal zweryfikowany na zywo (brak dostepu do internetu w srodowisku, w ktorym pisano ten
kod). Sprawdz i popraw przed pierwszym realnym uruchomieniem.

### Dodawanie nowego zrodla

1. Sprawdz `robots.txt` domeny - jesli scrapowanie konkretnego URL-a jest zablokowane,
   `fetch_scrape.py` i tak to sprawdzi automatycznie i pominie zrodlo z ostrzezeniem w logu.
2. Dodaj wpis do `sources:` w `config.yaml` (RSS jest preferowany, gdy jest dostepny - jest
   lekki i nie wymaga scrapowania).
3. Nie trzeba pisac nowego kodu parsujacego - `fetch_rss.py` i `fetch_scrape.py` obsluguja
   kazde zrodlo danego typu generycznie, a Claude (`normalize.py`) wyciaga z surowego tekstu
   strukturalne promocje.

### Profil uzytkownika

```yaml
profile:
  typy_promocji: [buy_miles, mileage_bargain, partner_bonus]
  partnerzy: ["Lufthansa", "LOT", "Hertz", "Marriott"]
  regiony: ["Europa", "Polska"]
  trasy: []
  min_bonus_pct: 20
```

Digest w terminalu pokazuje tylko nowe promocje spelniajace ten profil (puste listy = brak
filtra na danym polu).

## Architektura pipeline'u (`run.py`)

1. **Fetch** (`fetch_rss.py`, `fetch_scrape.py`) - pobiera surowe dane z kazdego zrodla
   (z cache i rate-limitem).
2. **Normalize** (`normalize.py`) - Claude (`claude-haiku-4-5`, structured outputs) zamienia
   surowy tekst w 0-N obiektow promocji w jezyku polskim, wlasnymi slowami.
3. **Dedup** (`dedup.py`) - rapidfuzz wykrywa te sama promocje zgloszona przez wiele zrodel
   w tym samym uruchomieniu oraz porownuje z promocjami juz w bazie (nieprzedawnionymi).
4. **Storage** (`storage.py`) - SQLite, unikalny `hash_dedup` jako dodatkowa siatka
   bezpieczenstwa przy zapisie.
5. **Digest** (`digest.py`) - filtruje nowo zapisane promocje wg profilu i formatuje wyjscie
   terminalowe ze zrodlami.

## Status

Faza 1 (ten pipeline terminalowy) - zaimplementowana.
Faza 2 (alerty Telegram) i Faza 3 (automatyzacja GitHub Actions) - jeszcze nie zaczete.
