# PyInstaller hook for mini-racer (py_mini_racer)
# This ensures the native DLL is included in the packaged application

from PyInstaller.utils.hooks import collect_data_files, get_package_paths
import os
from pathlib import Path

package_path = get_package_paths('py_mini_racer')

datas = collect_data_files('py_mini_racer', include_py_files=False)

binaries = []

py_mini_racer_path = Path(package_path[1]) / 'py_mini_racer'

dll_path = py_mini_racer_path / 'mini_racer.dll'
if dll_path.exists():
    binaries.append((str(dll_path), '.'))

icudtl_path = py_mini_racer_path / 'icudtl.dat'
if icudtl_path.exists():
    datas.append((str(icudtl_path), '.'))

hiddenimports = [
    'py_mini_racer',
    'py_mini_racer._dll',
    'py_mini_racer._mini_racer',
    'py_mini_racer._exc',
    'py_mini_racer._types',
]
