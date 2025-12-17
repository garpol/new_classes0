"""Compatibility package for tests expecting lowercase package name.

This package re-exports modules from the existing `RTD_Calibration_VGP` package
so tests which import `rtd_calibration_vgp.src.*` continue to work.
"""

__all__ = ["src"]
