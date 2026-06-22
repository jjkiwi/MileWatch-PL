@echo off
REM ============================================================
REM  MileWatch PL - budowanie aplikacji desktop do pliku .exe
REM  Wymaga tylko darmowych narzedzi. Uruchom dwuklikiem.
REM ============================================================

echo [1/3] Instalacja zaleznosci...
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo [2/3] Budowanie pliku MileWatchPL.exe...
python -m PyInstaller --noconfirm --clean MileWatchPL.spec

echo [3/3] Gotowe.
echo Plik znajdziesz w:  dist\MileWatchPL.exe
echo Skopiuj go gdziekolwiek i uruchom dwuklikiem - config.yaml utworzy sie obok.
pause
