# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for OneToTwo API
"""
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

api_path = Path(SPECPATH)

binaries = []
datas = []

datas += collect_data_files('jinja2', include_py_files=True)
datas += collect_data_files('matplotlib', include_py_files=True)
datas += collect_data_files('scipy', include_py_files=True)
datas += collect_data_files('sklearn', include_py_files=True)
datas += collect_data_files('akshare', include_py_files=True)

datas.append((str(api_path / "pipeline_defaults.json"), "."))
datas.append((str(api_path / "pipeline" / "templates"), "pipeline/templates"))
datas.append((str(api_path / "schemas"), "schemas"))
datas.append((str(api_path / "routes"), "routes"))
datas.append((str(api_path / "services"), "services"))
datas.append((str(api_path / "core"), "core"))
datas.append((str(api_path / "data"), "data"))
datas.append((str(api_path / "ml"), "ml"))
datas.append((str(api_path / "pipeline"), "pipeline"))

hidden_imports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'fastapi.applications',
    'fastapi.routing',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'fastapi.staticfiles',
    'fastapi.responses',
    'fastapi.exceptions',
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',
    'starlette.staticfiles',
    'starlette.responses',
    'starlette.exceptions',
    'pydantic',
    'pydantic.fields',
    'pandas',
    'numpy',
    'scipy',
    'scipy.special',
    'scipy.special._ufuncs',
    'sklearn',
    'sklearn.utils',
    'sklearn.utils._cython_blas',
    'sklearn.neighbors',
    'sklearn.neighbors._quad_tree',
    'sklearn.tree',
    'sklearn.tree._utils',
    'joblib',
    'jinja2',
    'matplotlib',
    'matplotlib.pyplot',
    'akshare',
    'httpx',
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',
    'h11',
    'asyncio',
    'asyncio.subprocess',
    'multiprocessing',
    'multiprocessing.spawn',
    'concurrent',
    'concurrent.futures',
    'concurrent.futures._base',
    'queue',
    'threading',
    'logging',
    'logging.config',
    'json',
    'pathlib',
    'typing',
    'typing_extensions',
    'core',
    'core.constants',
    'core.emotion',
    'core.features',
    'core.heatmap',
    'core.label',
    'core.logging',
    'core.rules',
    'core.scoring',
    'core.scheduler',
    'data',
    'data.ak',
    'data.cache',
    'data.columns',
    'data.prepare',
    'data.sync_cache',
    'data.trade_calendar',
    'ml',
    'ml.evaluator',
    'ml.trainer',
    'pipeline',
    'pipeline.backtest_emotion',
    'pipeline.config',
    'pipeline.daily',
    'pipeline.heatmap',
    'pipeline.report',
    'pipeline.rolling',
    'pipeline.train_model',
    'schemas',
    'schemas.responses',
    'schemas.tasks',
]

hidden_imports.extend(collect_submodules('routes'))
hidden_imports.extend(collect_submodules('services'))
hidden_imports.extend(collect_submodules('schemas'))
hidden_imports.extend(['py_mini_racer'])

try:
    import py_mini_racer
    py_mini_racer_path = Path(py_mini_racer.__file__).parent
    binaries.append((str(py_mini_racer_path / 'mini_racer.dll'), '.'))
    datas.append((str(py_mini_racer_path / 'icudtl.dat'), '.'))
    print(f"Included py_mini_racer from: {py_mini_racer_path}")
except Exception as e:
    print(f"Warning: Could not locate py_mini_racer: {e}")

a = Analysis(
    ['standalone_main.py'],
    pathex=[str(api_path)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[str(api_path)],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'ruff', 'mypy', 'IPython', 'jupyter', 'notebook'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='onetotwo-api',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(api_path.parent / "build" / "icon.ico") if (api_path.parent / "build" / "icon.ico").exists() else None,
)
