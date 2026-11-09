# -*- mode: python ; coding: utf-8 -*-
# PyInstaller tarifi: aynı kaynak koddan macOS (.app) ve Windows (.exe) paketleri üretir.
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).parent
sys.path.insert(0, str(ROOT / "backend"))
from kelebek.version import APP_VERSION  # noqa: E402

datas = [
    (str(ROOT / "backend" / "migrations"), "migrations"),
    (str(ROOT / "frontend" / "dist"), "frontend_dist"),
]
binaries = []
hiddenimports = collect_submodules("kelebek") + ["waitress", "logging.config"]
for package in ("ortools", "reportlab", "alembic", "pdfplumber", "pdfminer", "openpyxl"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

a = Analysis(
    [str(ROOT / "packaging" / "launch.py")],
    pathex=[str(ROOT / "backend")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
icon_dir = ROOT / "packaging" / ("macos" if sys.platform == "darwin" else "windows")
icon = next((str(path) for path in icon_dir.glob("*.icns" if sys.platform == "darwin" else "*.ico")), None)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="KelebekSinavSistemi",
    console=sys.platform == "win32",
    icon=icon,
)
coll = COLLECT(exe, a.binaries, a.datas, name="KelebekSinavSistemi")
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Kelebek Sınav Sistemi.app",
        icon=icon,
        bundle_identifier="tr.kelebek.sinavsistemi",
        info_plist={"CFBundleShortVersionString": APP_VERSION, "LSUIElement": False,
                    "NSHighResolutionCapable": True},
    )
