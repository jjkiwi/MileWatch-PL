# MileWatch PL — checklista na rano (kopiuj-wklej)

Wykonaj po kolei. Wszystko jest darmowe.

## 0. Test, że wszystko działa lokalnie

```powershell
cd C:\Users\Laptop\Documents\GitHub\Apka2
python tests.py
```

Oczekiwane: na końcu `=== WYNIK: N OK, 0 FAIL ===`.

## 1. Odwołaj stary token Telegrama (był widoczny w czacie)

1. W Telegramie napisz do **@BotFather** → `/revoke` → wybierz swojego bota → skopiuj **nowy token**.
2. Wstaw nowy token do pliku `.env` (podmień linię `TELEGRAM_BOT_TOKEN=...`).
   `TELEGRAM_CHAT_ID` zostaw bez zmian (Twoj wlasny chat_id z `getUpdates`).
3. Szybki test wysyłki:

```powershell
python test_alert.py
```

## 2. Commit i push kodu

```powershell
cd C:\Users\Laptop\Documents\GitHub\Apka2
git add -A
git status
```

W `git status` upewnij się, że **`.env` NIE jest na liście** (powinien być ignorowany).
Jeśli przypadkiem jest — `git rm --cached .env` i dopiero commit.

```powershell
git commit -m "MileWatch PL: darmowy pipeline, perelki (bledy cenowe/biznes), alerty Telegram/Signal, automatyzacja"
git push origin claude/milewatch-pl-tracker-2z5vsy
```

## 3. (Aby działał codzienny harmonogram) — kod na gałęzi domyślnej

GitHub uruchamia harmonogram (cron) tylko z **gałęzi domyślnej** repo. Masz dwie opcje:

**Opcja A — ustaw obecną gałąź jako domyślną** (najprościej):
GitHub → repo `Apka2` → **Settings → General → Default branch** → zmień na
`claude/milewatch-pl-tracker-2z5vsy`.

**Opcja B — scal do `main`:**

```powershell
git checkout main
git merge claude/milewatch-pl-tracker-2z5vsy
git push origin main
```

(Ręczne uruchomienie z zakładki **Actions → „Run workflow"** działa z każdej gałęzi —
harmonogramu to nie dotyczy.)

## 4. Dodaj sekrety alertów (chmura)

GitHub → repo `Apka2` → **Settings → Secrets and variables → Actions → New repository secret**.
Dodaj:

| Name | Value |
|------|-------|
| `TELEGRAM_BOT_TOKEN` | *(nowy token z kroku 1)* |
| `TELEGRAM_CHAT_ID` | *(Twoj chat_id z `getUpdates`)* |
| `SIGNAL_PHONE` | *(opcjonalnie, np. +48...)* |
| `SIGNAL_API_KEY` | *(opcjonalnie, z CallMeBot)* |

## 5. Włącz i przetestuj automat

1. GitHub → zakładka **Actions** → jeśli zapyta, kliknij **„I understand… enable workflows"**.
2. Wybierz workflow **„Aktualizuj promocje (GitHub Pages)"** → **Run workflow** (ręczny test).
3. Sprawdź log kroku „Scraping + generowanie strony + alerty" i czy przyszedł alert.

Od teraz workflow chodzi codziennie o 06:00 UTC (08:00 w PL latem).

## 6. (Opcjonalnie) Współdzielona strona — GitHub Pages

GitHub → repo `Apka2` → **Settings → Pages → Source: „Deploy from a branch"** →
branch = gałąź domyślna, folder = **/docs** → Save. Po pierwszym przebiegu workflow
dostaniesz publiczny link do strony z promocjami.

---

### Lokalnie zamiast chmury?

Jeśli wolisz codzienne sprawdzanie na swoim komputerze: użyj `run_daily.bat` w Harmonogramie
zadań Windows (instrukcja w pliku). Konfiguracja alertów wtedy w `.env` (nie w Secrets).
