# PyInstaller spec - MileWatch PL (aplikacja desktop, pojedynczy plik .exe)
# Budowanie:  python -m PyInstaller --noconfirm --clean MileWatchPL.spec

block_cipher = None

a = Analysis(
    ["gui.py"],
    pathex=["."],
    binaries=[],
    # config.yaml dolaczamy do paczki; przy pierwszym uruchomieniu kopiuje sie obok .exe
    datas=[("config.yaml", ".")],
    hiddenimports=["feedparser", "rapidfuzz", "bs4", "httpx", "yaml"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["anthropic", "flask"],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="MileWatchPL",
    debug=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,          # aplikacja okienkowa, bez czarnej konsoli
    disable_windowed_traceback=False,
)
