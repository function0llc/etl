# Build with: pyinstaller packaging/pyinstaller/etl-loader.spec
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ["app/main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=collect_submodules("psycopg") + collect_submodules("keyring.backends"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="etl-loader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(a.binaries, a.zipfiles, a.datas, exe, strip=False, upx=True, name="etl-loader")
