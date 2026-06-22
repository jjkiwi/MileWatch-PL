# MileWatch PL — raport oceny narzędzia i opcje monetyzacji

*Przygotowano: 22 czerwca 2026. Dokument roboczy do decyzji właściciela projektu.*

## 1. Streszczenie wykonawcze

MileWatch PL to darmowa, lekka aplikacja desktop (Python/Tkinter), która monitoruje
publiczne źródła RSS i strony WWW, wykrywa promocje programu Miles & More oraz „perełki"
lotnicze (błędy cenowe, mega-tanie loty dalekodystansowe, tania klasa biznes) i powiadamia
o nich przez Telegram lub Signal. Całość działa bez płatnych API i może chodzić automatycznie
w chmurze (GitHub Actions) albo lokalnie.

Narzędzie jest solidnym, działającym MVP w atrakcyjnej, lojalnej niszy (mile, punkty, tanie
loty premium). Jego realna wartość rynkowa zależy nie od kodu — który jest prosty do
odtworzenia — lecz od **jakości i szybkości kuracji okazji, zasięgu odbiorców i zaufania marki**.
Najbardziej realne ścieżki monetyzacji to **afiliacja (karty kredytowe Miles & More, rezerwacje
hoteli/lotów) oraz model freemium z natychmiastowymi alertami premium**. Reklamy displayowe i
darowizny są drugorzędne. Kluczowe ryzyka to kruchość scrapingu, kwestie prawne (regulaminy
serwisów, prawa autorskie, RODO) oraz rzadkość naprawdę dużych okazji.

## 2. Co narzędzie robi dzisiaj (stan faktyczny)

Pipeline: pobranie źródeł (RSS + scraping z poszanowaniem robots.txt, cache, rate-limit) →
darmowa ekstrakcja słowami kluczowymi/regex (PL/DE/EN) → wykrywanie perełek z parsowaniem cen
(PLN/EUR/USD) → deduplikacja (hash + fuzzy + dopasowanie strukturalne) → zapis SQLite →
prezentacja w oknie z filtrami i eksportem do samodzielnego HTML → opcjonalne alerty
Telegram/Signal. Automatyzacja: codzienny GitHub Actions publikujący stronę na GitHub Pages
i wysyłający alerty z sekretów repo.

Aktualne źródła: InsideFlyer.de/.com (M&M), Meilenoptimieren, Frankfurtflyer, Travel-Dealz
(DE), Mleczne Podróże, Fly4free.pl (PL), The Flight Deal (perełki), scraping InsideFlyer.

## 3. Mocne strony

Po pierwsze, **zerowy koszt operacyjny** — brak płatnych API, hosting w darmowym GitHub
Actions, alerty przez darmowe kanały. To realnie spełnia założenie „w pełni darmowa" i pozwala
testować rynek bez inwestycji. Po drugie, **lekkość i prostota** — stdlib Tkinter, brak ciężkich
zależności, łatwe pakowanie do .exe. Po trzecie, **wartościowa nisza** — entuzjaści mil i tanich
lotów premium to grupa o wysokiej skłonności do zakupów finansowych (karty kredytowe) i podróży,
czyli atrakcyjna dla afiliacji. Po czwarte, **architektura rozszerzalna** — dodanie źródła to
wpis w configu; klasyfikatory (M&M, błędy cenowe, biznes) są rozdzielone i łatwe do strojenia.

## 4. Słabe strony i ryzyka techniczne

Najpoważniejsza słabość to **kruchość pozyskiwania danych**. Część serwisów blokuje skrypty
(Reisetopia — Cloudflare 403), oficjalna strona Miles & More renderuje oferty JavaScriptem
(surowy HTML bezużyteczny), a feedy zmieniają adresy. Utrzymanie listy działających źródeł to
stała praca. Po drugie, **ekstrakcja słowami kluczowymi ma ograniczoną precyzję** — myli newsy
z promocjami (np. „90 Prozent udziałów"), a streszczenia RSS bywają zbyt krótkie, by wyłapać
szczegóły. Wprowadzone filtry to ograniczają, ale nie eliminują. Po trzecie, **rzadkość sygnału**
— naprawdę dużych okazji i błędów cenowych jest mało; aplikacja często będzie „pusta", co bywa
mylone z usterką. Po czwarte, **zależność od CallMeBot** dla Signala (zewnętrzny pośrednik,
brak gwarancji SLA i prywatności). Po piąte, **brak prawdziwych cen i tras** — bez wejścia w
treść artykułu klasyfikacja opiera się na tytule/zajawce.

## 5. Ryzyka prawne i zgodności (do świadomej decyzji, to nie porada prawna)

- **Regulaminy i prawa autorskie serwisów.** Scraping i ponowne publikowanie treści (nawet
  streszczeń) może naruszać regulaminy źródeł i prawa autorskie. Projekt świadomie streszcza
  „własnymi słowami" i linkuje do źródła — to dobra praktyka, ale przy publicznej dystrybucji
  (GitHub Pages, płatny produkt) ryzyko rośnie. Warto preferować oficjalne feedy/API i uzyskać
  zgody, jeśli treść stanie się produktem.
- **robots.txt i User-Agent.** Aplikacja respektuje robots.txt, ale używa przeglądarkowego
  User-Agent, by ominąć blokady nietypowych UA — to obszar szarej strefy regulaminowej.
- **RODO.** Przy alertach i subskrypcjach przetwarzasz dane (numer Signal/Telegram, e-mail).
  Komercjalizacja wymaga polityki prywatności, podstawy prawnej i obsługi zgód.
- **Afiliacja kart kredytowych** jest w UE/PL regulowana (pośrednictwo finansowe, ujawnianie
  linków afiliacyjnych). Wymaga zgodności i jawnych oznaczeń „materiał z linkami afiliacyjnymi".
- **Błędy cenowe** bywają anulowane przez linie; informowanie o nich jest legalne, ale komunikuj
  ryzyko anulacji, by nie wprowadzać w błąd.

## 6. Krajobraz konkurencyjny

Nisza jest zajęta, ale rozdrobniona. Globalnie: Secret Flying, The Flight Deal, Going (dawniej
Scott's Cheap Flights), Jack's Flight Club (model płatny), Thrifty Traveler. Niemcy (serce
Miles & More): Reisetopia, InsideFlyer.de, Meilenoptimieren, Frankfurtflyer — silne marki z
afiliacją kart i hoteli. Polska: Fly4free.pl, Mleczne Podróże, Pasażer.com. Wniosek: samo
„powiadamianie o okazjach" nie jest przewagą. Przewagą może być **wąska specjalizacja
(Miles & More + biznes klasa + błędy cenowe dla polskiego odbiorcy), szybkość alertu i
personalizacja po profilu/trasach**, których generyczne serwisy nie dają.

## 7. Opcje monetyzacji (od najbardziej do najmniej realnych)

**A. Afiliacja — najwyższy potencjał w tej niszy.** Karty kredytowe Miles & More / co-brandowane,
platformy rezerwacji hoteli i lotów, ubezpieczenia podróżne, wypożyczalnie. W segmencie
punktów/mil prowizje za pozyskanie klienta karty bywają wysokie (CPA). Wymaga ruchu i zaufania,
ale daje przychód bez pobierania opłat od użytkownika. To rekomendowany pierwszy filar.

**B. Freemium / subskrypcja.** Darmowo: dzienny przegląd i wybrane alerty. Premium (miesięczna
opłata): natychmiastowe alerty (kluczowe przy błędach cenowych, które znikają w godziny),
filtry po trasach/lotniskach wylotu, biznes/first, brak limitów. Model sprawdzony przez Jack's
Flight Club i Going. Wymaga niezawodności i realnie unikalnych okazji.

**C. Płatny newsletter (Substack/Ghost).** Niski próg wejścia, łączy się z afiliacją. Dobry
sposób na zbudowanie listy odbiorców zanim powstanie produkt płatny.

**D. Darowizny / patronat (Patronite, Buy Me a Coffee).** Realne na start jako „podziękowanie",
nieskalowalne, ale bezkosztowe i bez zobowiązań.

**E. B2B / white-label.** Licencjonowanie silnika monitorowania biurom podróży lub serwisom
mil jako wewnętrznego narzędzia. Nisza, ale wyższe kontrakty.

**F. Reklamy displayowe.** Najsłabsze przy małym ruchu; sensowne dopiero przy dużej skali strony
WWW. Pogarszają UX alertów.

**Rekomendacja:** zacznij od **afiliacji + budowy listy mailowej/Telegram**, dołóż **freemium z
natychmiastowymi alertami** gdy jakość i niezawodność źródeł będą stabilne. Darowizny jako
pomost. Reklam unikać do czasu realnego ruchu.

## 8. Co jest potrzebne, by monetyzacja miała sens

Trzy fundamenty: **(1) Niezawodność i zasięg źródeł** — więcej stabilnych, oficjalnych feedów,
wejście w treść artykułu po cenę/trasę, monitoring „martwych" źródeł. **(2) Skala odbiorców** —
kanał Telegram/newsletter z realną publicznością; bez tego afiliacja nie zarabia. **(3) Zaufanie
i zgodność** — marka, polityka prywatności, jawne oznaczanie afiliacji, ostrożność przy prawach
autorskich. Bez tych trzech rzeczy nawet najlepszy kod nie zarabia.

## 9. Rekomendowana mapa rozwoju

Krótko: ustabilizować źródła i podbić precyzję (mniej fałszywych trafień, wejście w treść po
cenę/trasę), uruchomić publiczny kanał Telegram z najlepszymi okazjami, dodać scoring „jak
dobra to okazja" i personalizację po lotnisku wylotu. Średnio: newsletter + pierwsze linki
afiliacyjne (karty, hotele), web-dashboard zamiast/obok desktopu. Długo: warstwa premium
z natychmiastowymi alertami i filtrami tras, ewentualnie oferta B2B.

## 10. Werdykt

Jako **darmowe narzędzie osobiste / projekt portfolio** — bardzo dobre: spełnia wymagania,
działa, jest rozszerzalne. Jako **produkt komercyjny** — obiecujący punkt startowy w dochodowej
niszy, ale przewaga nie leży w kodzie, tylko w kuracji, zasięgu, niezawodności i zgodności.
Najszybsza realna ścieżka pieniędzy to afiliacja kart/rezerwacji przy zbudowanej publiczności,
a w drugim kroku płatne natychmiastowe alerty. Potencjał istnieje, ale wymaga pracy nad
dystrybucją i stroną prawną, nie tylko nad funkcjami.

---

*Zastrzeżenie: to nie jest porada prawna ani inwestycyjna. Przed komercjalizacją skonsultuj
kwestie praw autorskich, regulaminów źródeł, RODO i afiliacji finansowej z prawnikiem.*
