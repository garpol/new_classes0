"""Proxy package to expose RTD_Calibration_VGP.src under the lowercase package name.

This file imports and exposes the modules from the original package so tests
referencing `rtd_calibration_vgp.src.*` will find the expected modules.
"""

from importlib import import_module
from types import ModuleType
import sys

# Import the real package modules and insert them into this package's namespace
real_pkg = import_module('RTD_Calibration_VGP.src')
for attr in dir(real_pkg):
    if not attr.startswith('_'):
        try:
            setattr(sys.modules[__name__], attr, getattr(real_pkg, attr))
        except Exception:
            # ignore any attributes that can't be copied
            pass

__all__ = [name for name in dir(real_pkg) if not name.startswith('_')]
