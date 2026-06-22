# Niezawodny wyzwalacz co godzinę (gdy cron GitHuba zawodzi)

Cron GitHuba bywa opóźniony lub pomijany. Ten darmowy zewnętrzny wyzwalacz gwarantuje
uruchomienie co godzinę. Workflow ma juz dodany trigger `repository_dispatch` (typ `run-now`).

## Krok 1 — token GitHub (PAT)

1. GitHub → klik w awatar (prawy gorny rog) → **Settings** (ustawienia KONTA).
2. Na dole lewego menu: **Developer settings**.
3. **Personal access tokens → Tokens (classic)** → **Generate new token (classic)**.
4. Note: `milewatch-trigger`. Expiration: np. 1 rok.
5. Zaznacz zakres (scope): **`repo`** (cały).
6. **Generate token** i SKOPIUJ go (pokaze sie tylko raz).

## Krok 2 — darmowy pinger cron-job.org

1. Zarejestruj sie na https://cron-job.org (darmowe).
2. **Create cronjob**:
   - **Title:** MileWatch godzinowy
   - **URL:** `https://api.github.com/repos/jjkiwi/Apka2/dispatches`
   - **Schedule:** Every hour (np. „every 1 hour" albo minuta :15 co godzine).
3. Rozwin **Advanced / Request settings**:
   - **Request method:** `POST`
   - **Request headers** (dodaj po jednym):
     - `Accept: application/vnd.github+json`
     - `Authorization: Bearer TWOJ_TOKEN_PAT`
     - `X-GitHub-Api-Version: 2022-11-28`
     - `Content-Type: application/json`
   - **Request body:**
     ```json
     {"event_type":"run-now"}
     ```
4. **Create / Save**.

## Krok 3 — test

W cron-job.org kliknij **„Run now"** (albo poczekaj na pelna godzine). Potem na GitHubie:
**Actions → filtr `event:repository_dispatch`** — powinien pojawic sie przebieg.
Poprawna odpowiedz GitHuba to **HTTP 204** (sukces, bez tresci).

## Uwagi

- Token PAT to sekret — trzymaj go tylko w cron-job.org, nie wklejaj do repo.
- Mozesz zostawic tez cron w workflow (`schedule`) jako zapas - oba wyzwalacze dzialaja
  rownolegle, a deduplikacja i tak nie wysle tej samej promocji dwa razy.
- Alternatywa bez tokena i bez chmury: Harmonogram zadan Windows + `run_daily.bat`
  ustawiony „co godzine" (dziala, gdy komputer jest wlaczony).
