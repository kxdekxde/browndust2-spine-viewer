# hook-unitypy.py
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("UnityPy") + [
    "lz4.block",
    "zstandard",
    "zstandard.backends",
    "zstandard.backends.cffi",
]
