# -*- mode: python ; coding: utf-8 -*-
import sys
import shutil
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Prevent PyInstaller from crashing when tracing PyTorch's massive dependency tree
sys.setrecursionlimit(5000)

# 1. Force-collect heavy core libraries
pil_bins, pil_datas, pil_hidden = collect_all('PIL')
cert_bins, cert_datas, cert_hidden = collect_all('certifi')
sdk_bins, sdk_datas, sdk_hidden = collect_all('biopro_sdk')
bokeh_bins, bokeh_datas, bokeh_hidden = collect_all('bokeh')
fk_bins, fk_datas, fk_hidden = collect_all('flowkit')

# --- THE OPTIMIZATION ENGINE ---
# Strip out hundreds of MBs of useless testing/mock data from the final build
def filter_bloat(item_list):
    clean_list = []
    for item in item_list:
        dest = item[1].lower() if len(item) > 1 else item[0].lower()
        if any(bad in dest for bad in ['/test/', '/tests/', '/testing/', 'test_', '__pycache__']):
            continue
        clean_list.append(item)
    return clean_list

all_bins = sorted(filter_bloat(pil_bins + cert_bins + sdk_bins + bokeh_bins + fk_bins))
all_datas = sorted(filter_bloat(pil_datas + cert_datas + sdk_datas + bokeh_datas + fk_datas))
all_hidden = sorted(list(set(pil_hidden + cert_hidden + sdk_hidden + bokeh_hidden + fk_hidden)))

# --- BUNDLE UV SIDECAR ---
# We package the uv binary into sys._MEIPASS/bin/uv so the PackageManager
# can use it to install dependencies in the frozen environment.
uv_path = shutil.which('uv')
if uv_path:
    all_bins.append((uv_path, 'bin'))

# 2. Aggressive Excludes (Modules BioPro does not need to run)
# Explicitly exclude test modules and development dependencies
bloat_modules = [
    'tests',
    'pytest',
    'pytest_qt',
    'mock',
    'coverage',
]

# 3. Hidden Imports (Ensuring dynamic libraries are packed)
hidden_imports = [
    'biopro_sdk',
    'biopro_sdk.plugin',
    'biopro_sdk.host',
    'biopro.plugins',
    'matplotlib.backends.backend_qtagg',
    'matplotlib',
    'pandas',
    'numpy',
    'scipy',
    'psutil',
    'requests',
    'PyQt6.QtPrintSupport',
    'PyQt6.QtCore',
    'PIL',
    'certifi',
    'cryptography',
    'markdown',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebEngineCore',
    'pygments',
    'flowkit',
    'flowio',
    'flowutils',
    'bokeh',
    'fast_histogram',
    # --- Standard Library Guarantees for Dynamic Plugins ---
    'fileinput',
    'multiprocessing',
    'concurrent.futures',
    'ctypes',
    'ctypes.util',
    'sqlite3',
    'urllib',
    'urllib.request',
    'bz2',
    'lzma',
    'gzip',
    'zipfile',
    'tarfile',
    'xml.etree.ElementTree',
    'csv',
    'json',
    'logging.config',
] + collect_submodules('biopro')

a = Analysis(
    ['biopro/__main__.py'],
    pathex=[],
    binaries=all_bins,
    datas=[
        ('biopro/themes', 'themes'),
        ('biopro/shared', 'biopro/shared'),
        ('biopro/plugins', 'biopro/plugins'),
        ('docs', 'docs'),
        ('icon.icns', '.'),
        ('pyproject.toml', '.')
    ] + all_datas,
    hiddenimports=hidden_imports + all_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=bloat_modules,
    noarchive=False,
    optimize=1, # Strips assert statements and docstrings to save space
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BioPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False, # Reverted for stability; use biopro.log for troubleshooting
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='BioPro',
)

# Protects Windows/Linux servers from trying to build Apple bundles
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='BioPro.app',
        icon='icon.icns',
        bundle_identifier='com.biopro.analysis',
    )
