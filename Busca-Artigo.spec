# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['tcc_research_assistant/main.py'],
    pathex=['tcc_research_assistant'],
    binaries=[],
    datas=[
        ('tcc_research_assistant/styles.qss', '.'),
        ('tcc_research_assistant/assets', 'assets'),
    ],
    hiddenimports=[
        'langdetect',
        'langdetect.detector',
        'langdetect.detector_factory',
        'langdetect.lang_detect_exception',
        'langdetect.utils',
        'langdetect.utils.lang_profile',
        'sklearn.feature_extraction.text',
        'sklearn.metrics.pairwise',
        'sklearn.utils._cython_blas',
        'sklearn.neighbors.typedefs',
        'sklearn.neighbors.quad_tree',
        'sklearn.tree._utils',
        'openpyxl',
        'openpyxl.workbook',
        'fpdf',
        'fpdf.fpdf',
        'pandas',
        'bs4',
        'bs4.builder',
        'bs4.builder._htmlparser',
        'tenacity',
        'requests',
        'sqlite3',
        'xml.etree.ElementTree',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],  # 'unittest'/'test' são necessários por numpy.testing (via scipy/sklearn)
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
    name='Busca-Artigo',
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
    icon='tcc_research_assistant/assets/icons/logopag.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Busca-Artigo',
)
