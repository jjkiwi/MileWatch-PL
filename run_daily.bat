@echo off
REM ============================================================
REM  MileWatch PL - jednorazowy przebieg pipeline'u (scraping + alerty).
REM  Przeznaczony do Harmonogramu zadan Windows (codzienne uruchamianie).
REM
REM  Jak ustawic codzienne uruchamianie:
REM   1. Otworz "Harmonogram zadan" (Task Scheduler).
REM   2. "Utworz zadanie podstawowe" -> wyzwalacz: codziennie, np. 8:00.
REM   3. Akcja: "Uruchom program" -> wskaz ten plik (run_daily.bat).
REM   4. Alerty Telegram/Signal wysla sie, jesli wypelnisz plik .env (patrz README).
REM ============================================================

cd /d "%~dp0"
python run.py
