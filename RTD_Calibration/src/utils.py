"""Utility helpers for RTD Calibration.

Provides a small config loader that reads YAML (falls back to JSON-like dicts)
and returns a normalized dictionary with safe defaults.
"""
from __future__ import annotations

import os
from typing import Any, Dict

try:
	import yaml
except Exception:
	yaml = None


DEFAULT_CONFIG: Dict[str, Any] = {
	"paths": {
			"data_dir": "RTD_Calibration/data/temperature_files",
			"logfile": "RTD_Calibration/data/LogFile.csv",
			"logfile_parsed": "RTD_Calibration/data/LogFile_parsed.csv",
			"plots_dir": "RTD_Calibration/notebooks/Plots",
	},
		"selection": {"selected_sets": [], "require_integer_calibset": True},
	"sensors": {
		"discarded_sensors": {},
		"sensors_raised_by_set": {},
		"set_rounds": {},
	},
	"run_options": {"max_nan_threshold": 40, "valid_temp_range": {"min": 60, "max": 350}, "default_ref_channel": 2},
	"output": {"save_calibration_excel": True, "calibration_excel_name": "calibration_constants_and_errors.xlsx"},
	"logging": {"level": "INFO", "verbose": True},
}


def load_config(path: str | None = None) -> Dict[str, Any]:
	"""Load configuration from YAML file and return a normalized dict.

	If `path` is None, returns defaults. If YAML parser is not available, attempts
	to read a JSON-like file using eval (not recommended).

	Raises:
		FileNotFoundError: if path is provided and file does not exist.
		RuntimeError: if yaml is required but not installed and parsing fails.
	"""
	config = DEFAULT_CONFIG.copy()

	if path is None:
		return config

	if not os.path.exists(path):
		raise FileNotFoundError(f"Config file not found: {path}")

	with open(path, "r", encoding="utf-8") as fh:
		raw = fh.read()

	parsed = None
	if yaml is not None:
		parsed = yaml.safe_load(raw)
	else:
		# Minimal fallback: try to eval a Python dict literal (risky) or raise
		try:
			parsed = eval(raw, {})
		except Exception as e:
			raise RuntimeError("PyYAML not installed and config parsing fallback failed: " + str(e))

	if not isinstance(parsed, dict):
		raise RuntimeError("Config file did not parse to a dictionary")

	# Merge parsed with defaults, but do shallow merges for top-level keys
	merged = DEFAULT_CONFIG.copy()
	for k, v in parsed.items():
		if isinstance(v, dict) and isinstance(merged.get(k), dict):
			merged[k] = {**merged[k], **v}
		else:
			merged[k] = v

	# Normalize some types: ensure set_rounds keys are floats
	try:
		sensors = merged.get("sensors", {})
		# If config uses unified 'sets' structure, expand it into the older fields
		sets_cfg = sensors.get("sets")
		if isinstance(sets_cfg, dict):
			discarded = {}
			raised = {}
			set_rounds = {}
			for ks, vv in sets_cfg.items():
				try:
					kf = float(ks)
				except Exception:
					kf = float(str(ks))
				discarded[kf] = vv.get("discarded", [])  # new name
				raised[kf] = vv.get("raised", [])      # new name
				set_rounds[kf] = int(vv.get("round", 1))
			merged["sensors"]["discarded_sensors"] = discarded
			merged["sensors"]["sensors_raised_by_set"] = raised
			merged["sensors"]["set_rounds"] = set_rounds
		else:
			set_rounds = sensors.get("set_rounds", {})
			normalized = {}
			for ks, vv in set_rounds.items():
				try:
					kf = float(ks)
				except Exception:
					kf = float(str(ks))
				normalized[kf] = int(vv)
			merged["sensors"]["set_rounds"] = normalized
	except Exception:
		# If normalization fails, leave as-is
		pass

	return merged

