# MileWatch PL — roadmap rozwoju

Cel nadrzędny: z „strumienia linków" zrobić **kurację najlepszych okazji dla mnie**
(Polska + kraje ościenne), z wiarygodnymi tagami i oceną „jak dobra to okazja".

## Faza 0 — naprawa tagu „błąd cenowy" (najpierw, szybkie)

**Problem (zgłoszony):** zwykłe promki (np. lot do Szwecji za 150 zł w obie strony) dostają
tag `[‼️ BŁĄD CENOWY]`, bo słowa-hype z serwisów („rekordowo tanio", „najtaniej", „❗OKAZJA❗")
są traktowane jak sygnał błędu cenowego.

**Rozwiązanie:**
- `error_fare` (tag `[‼️ BŁĄD CENOWY]`) TYLKO dla jawnych błędów: „błąd cenowy", „error fare",
  „mistake fare", „Fehlerfare/Fehlpreis". To rzadkie i naprawdę wyjątkowe.
- Nowa kategoria `great_deal` (tag `[🔥 TANI LOT]`) dla bardzo tanich/dalekich lotów i ofert
  z hype, ale BEZ słowa „błąd". Hype („rekordowo", „najtaniej w historii") → great_deal.
- `business_class` bez zmian (`[💺 BIZNES KLASA]`).
- Aktualizacja: tagi w alertach, kolory w GUI, etykiety w eksporcie, always-alert w digest.

*Status: w realizacji.*

## Faza 1 — filtr lotnisk wylotu (Polska + kraje ościenne)

**Cel:** alarmować głównie o okazjach z **moich** lotnisk. Preferencja: cała Polska + kraje
ościenne (Niemcy, Czechy, Słowacja, Litwa, Austria w zasięgu; lotniska, do których Polak
realnie dojeżdża: Berlin, Drezno, Praga, Ostrawa, Bratysława, Wiedeń, Wilno).

**Rozwiązanie:**
- Wykrywanie lotniska/miasta wylotu z tytułu/treści (np. „z Warszawy", „from Berlin", kody IATA).
- Nowe pole `wylot` w modelu i bazie (migracja `ALTER TABLE` bez utraty danych).
- Lista preferowanych wylotów w `config.yaml` (`profile.wyloty`) — domyślnie PL + ościenne.
- Filtr stosowany do PEREŁEK (tani lot / błąd cenowy / biznes): jeśli wykryto wylot i nie jest
  preferowany → pomijamy. Jeśli wylotu nie da się ustalić → zostawiamy (nie odrzucamy).
  Promocje Miles & More (globalne) nie podlegają temu filtrowi.
- Oznaczanie wylotu w alercie, na stronie i w GUI.

## Faza 2 — scoring „jak dobra to okazja" (0–100)

**Cel:** liczbowa ocena jakości, żeby od razu widać było, co warte uwagi, i móc ustawić próg.

**Rozwiązanie:**
- Punkty za: wielkość zniżki/bonusu %, jak tanio względem typowej ceny (pełnia po Fazie 3),
  klasę (biznes/first wyżej), dalekodystansowość, jawny błąd cenowy = maksimum.
- W alercie „★ 78/100", sortowanie na stronie/GUI wg score.
- Konfigurowalny próg alertu (np. wysyłaj tylko ≥ 60) — ogranicza szum.

## Faza 3 — pełna treść artykułu + baseline cen

**Cel:** dokładna cena/trasa/data oraz „czy to naprawdę wyjątkowa cena" (domyka problem
„150 zł do Szwecji to normalka").

**Rozwiązanie:**
- Pobranie pełnej treści artykułu (nie tylko zajawki RSS) i precyzyjne wyłuskanie ceny/trasy/daty.
- Baseline cen tras w czasie (SQLite) — oznaczanie „najtaniej od X miesięcy".
- Dopiero realnie wyjątkowa cena = perełka; reszta z niższym score albo bez alertu.

---

Kolejność realizacji: Faza 0 → 1 → 2 → 3. Każda faza = osobny commit/push.
