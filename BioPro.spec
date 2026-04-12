# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

# Prevent PyInstaller from crashing when tracing PyTorch's massive dependency tree
sys.setrecursionlimit(5000)

# 1. Force-collect heavy imaging and AI libraries
sk_bins, sk_datas, sk_hidden = collect_all('skimage')
cp_bins, cp_datas, cp_hidden = collect_all('cellpose')
torch_bins, torch_datas, torch_hidden = collect_all('torch')

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

all_bins = filter_bloat(sk_bins + cp_bins + torch_bins)
all_datas = filter_bloat(sk_datas + cp_datas + torch_datas)
all_hidden = sk_hidden + cp_hidden + torch_hidden

# 2. Aggressive Excludes (Modules BioPro does not need to run)
bloat_modules = []

# 3. Hidden Imports (Ensuring dynamic libraries are packed)
hidden_imports = [
    'biopro.plugins',
    'matplotlib.backends.backend_qtagg',
    'matplotlib',
    'pandas',
    'numpy',
    'scipy',
    'cv2',
    'fcsparser',
    'psutil',          
    'PyQt6.QtPrintSupport',
    'PyQt6.QtCore',
    'flowkit',
    'flowio',      
    'flowutils' 
] + all_hidden

a = Analysis(
    ['biopro/__main__.py'],
    pathex=[],
    binaries=all_bins, 
    datas=[
        ('themes', 'themes'),
        ('biopro/shared', 'biopro/shared') 
    ] + all_datas, 
    hiddenimports=hidden_imports,
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
    console=False, 
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.icns'],
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
        bundle_identifier=None,
    )