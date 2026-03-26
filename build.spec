# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None
ROOT = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(ROOT, 'main.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'web', 'templates'), 'web/templates'),
        (os.path.join(ROOT, 'web', 'static'), 'web/static'),
        (os.path.join(ROOT, '.env.example'), '.'),
    ],
    hiddenimports=[
        'gevent',
        'gevent.monkey',
        'geventwebsocket',
        'geventwebsocket.handler',
        'engineio.async_drivers.gevent',
        'flask_socketio',
        'flask.json',
        'pandas_ta',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'notebook', 'IPython'],
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
    name='ETH-Trading-Bot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ETH-Trading-Bot',
)
