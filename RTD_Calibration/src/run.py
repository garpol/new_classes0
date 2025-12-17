import os
import glob
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class Run:
    """Represents a single calibration run and its temperature data.

    Responsibilities:
    - Locate and load the run's temperature file (local data/temperature_files or CERNBox fallback)
    - Clean temperature measurements and mark excessive NaNs
    - Map channels to RTD sensor IDs using the provided logfile DataFrame
    - Provide plotting helpers and offset / RMS calculations
    """

    def __init__(self, filename: str, logfile: pd.DataFrame) -> None:
        """Create a Run instance and (optionally) load/process data.

        Parameters
        - filename: base name of the temperature file (without .txt)
        - logfile: DataFrame with the LogFile.csv contents used to map sensors
        """
        self.filename = filename
        self.logfile = logfile
        self.temperature_data: pd.DataFrame | None = None
        self.sensor_mapping: dict | None = None
        self.path_to_file: str | None = None
        self.nan_data: pd.DataFrame | None = None
        # list of channel names (e.g. 'channel_8') detected as defective due to many NaNs
        self.defective_channels = []
        self.run_info: dict | None = None

        # Load and prepare data; these are best-effort and will set empty frames on failure
        try:
            self.load_temperature_file()
        except Exception:
            # load_temperature_file already prints errors; ensure attributes are sane
            self.temperature_data = pd.DataFrame()

    def load_temperature_file(self) -> "Run":
        """Locate and load the temperature data file into self.temperature_data.

        Searches in: RTD_Calibration_VGP/data/temperature_files (recursively)

        The expected file is tab-separated with no header. Columns are: Date, Time, channel_1..channel_14.
        Values outside 60–350 K are set to NaN. Columns with many NaNs are recorded and left as NaN.
        """
        # Determine candidate paths
        repo_root = Path(__file__).parents[1].resolve()
        local_base = repo_root / "data" / "temperature_files"

        candidates = []
        if local_base.exists():
            candidates = glob.glob(os.path.join(str(local_base), "**", self.filename + ".txt"), recursive=True)

        if not candidates:
            raise FileNotFoundError(
                f"Temperature file '{self.filename}.txt' not found in {local_base}.\n"
                f"Make sure data files are placed under RTD_Calibration_VGP/data/temperature_files/"
            )

        self.path_to_file = candidates[0]
        print(f"Temperature file found: {self.path_to_file}")

        # Read and name columns
        df = pd.read_csv(self.path_to_file, sep="\t", header=None)
        expected_cols = ["Date", "Time"] + [f"channel_{i}" for i in range(1, 15)]
        if df.shape[1] < len(expected_cols):
            # If the file has fewer columns than expected, raise a clear error
            raise ValueError(f"Unexpected number of columns in {self.path_to_file}: found {df.shape[1]}")

        df.columns = expected_cols + list(df.columns[len(expected_cols):])

        # Parse datetimes using multiple common formats
        dt = pd.to_datetime(df["Date"] + " " + df["Time"], errors="coerce", format="%m/%d/%Y %I:%M:%S %p")
        if dt.isna().any():
            dt = pd.to_datetime(df["Date"] + " " + df["Time"], errors="coerce", format="%m/%d/%Y %H:%M:%S")
        if dt.isna().any():
            dt = pd.to_datetime(df["Date"] + " " + df["Time"], errors="coerce", dayfirst=True)
        if dt.isna().any():
            raise ValueError(f"Could not parse datetimes in file {self.path_to_file}.")

        # Keep only the channel columns and use datetime as index
        temp_cols = df[[c for c in df.columns if c.startswith("channel_")]].copy()
        temp_cols.index = dt

        # Apply plausible range mask and drop rows where all channels are NaN
        valid_mask = (temp_cols >= 60) & (temp_cols <= 350)
        temp_cols = temp_cols.where(valid_mask)
        temp_cols = temp_cols.dropna(how="all")

        # Record NaN locations for inspection
        nan_locs = temp_cols[temp_cols.isna().any(axis=1)].copy()
        nan_locs["datetime"] = nan_locs.index
        nan_df = nan_locs.melt(id_vars="datetime", var_name="channel", value_name="value")
        nan_df = nan_df[nan_df["value"].isna()]
        self.nan_data = nan_df

        # Columns with too many NaNs may be considered defective
        nan_count = temp_cols.isna().sum()
        max_nan_threshold = 40
        defective = nan_count[nan_count > max_nan_threshold].index.tolist()
        if defective:
            print(f"Columns with excessive NaNs: {defective}")

        # store defective channel list on the instance for callers to consult
        try:
            # ensure it's a plain list of strings
            self.defective_channels = [str(x) for x in defective]
        except Exception:
            self.defective_channels = []

        self.temperature_data = temp_cols
        print(f"Temperature file processed successfully: {self.path_to_file}")
        return self

    def associate_sensors(self) -> None:
        """Map temperature channels to RTD sensor IDs using the logfile DataFrame.

        The logfile is expected to contain columns S1..S20. The method maps channel_1..channel_14
        to the first 14 non-null S* values in the matching logfile row.
        """
        if self.temperature_data is None or self.temperature_data.empty:
            raise ValueError("No temperature data loaded to associate sensors.")

        matching_row = self.logfile[self.logfile["Filename"] == self.filename]
        if matching_row.empty:
            raise ValueError(f"Filename '{self.filename}' not found in logfile.")

        sensor_cols = [f"S{i}" for i in range(1, 21)]
        sensor_vals = matching_row.loc[:, sensor_cols].iloc[0].dropna().values
        # Convert sensor ids to strings of integers when possible
        sensor_ids = []
        for v in sensor_vals:
            try:
                sensor_ids.append(str(int(float(v))))
            except Exception:
                sensor_ids.append(str(v))

        channels = [f"channel_{i}" for i in range(1, 15)]
        mapping = dict(zip(channels, sensor_ids[: len(channels)]))
        self.sensor_mapping = mapping
        # Rename columns in the temperature dataframe
        self.temperature_data = self.temperature_data.rename(columns=self.sensor_mapping)
        print(f"Associated sensors: {self.sensor_mapping}")

    def filter_faulty_channels(self, min_temp: float = 70, max_temp: float = 320) -> dict:
        """Detect and report faulty channels.

        Returns a dict channel -> list(reasons) describing issues found.
        """
        if self.temperature_data is None or self.temperature_data.empty:
            raise ValueError("No temperature data available to filter.")

        faulty = {}
        for ch in self.temperature_data.columns:
            reasons = []
            series = self.temperature_data[ch]
            if series.min(skipna=True) < min_temp:
                reasons.append(f"min below {min_temp} K")
            if series.max(skipna=True) > max_temp:
                reasons.append(f"max above {max_temp} K")
            if series.nunique(dropna=True) == 1:
                reasons.append("constant readings")
            if series.isna().any():
                reasons.append("contains NaN")
            if reasons:
                faulty[ch] = reasons

        if faulty:
            print("Detected faulty channels:")
            for ch, rs in faulty.items():
                print(f" - {ch}: {', '.join(rs)}")
        else:
            print("No faulty channels detected.")

        return faulty

    def read_run_info(self) -> None:
        """Read run-level metadata from the logfile for this filename.

        Extracts CalibSetNumber, Date, N_Run and reference sensor information.
        Reference sensors (REF1, REF2) are typically in channels 13-14 and are
        NOT part of the calibration tree - they are external references.
        """
        matching_row = self.logfile[self.logfile["Filename"] == self.filename]
        if matching_row.empty:
            raise ValueError(f"Filename '{self.filename}' not found in logfile.")

        calib_set = matching_row["CalibSetNumber"].iloc[0]
        date = matching_row["Date"].iloc[0]
        n_run = matching_row["N_Run"].iloc[0]

        def to_int_safe(x):
            try:
                return int(float(x))
            except Exception:
                return None

        # Extract reference sensor information from dedicated columns
        ref1_id = to_int_safe(matching_row.get("REF1_ID", pd.Series([None])).iloc[0])
        ref2_id = to_int_safe(matching_row.get("REF2_ID", pd.Series([None])).iloc[0])
        ref1_chan = matching_row.get("REF1_CHAN", pd.Series([None])).iloc[0]
        ref2_chan = matching_row.get("REF2_CHAN", pd.Series([None])).iloc[0]
        n_ref1 = to_int_safe(matching_row.get("N_Ref1", pd.Series([None])).iloc[0])
        n_ref2 = to_int_safe(matching_row.get("N_Ref2", pd.Series([None])).iloc[0])
        
        # For backward compatibility, also check S19/S20 if REF columns don't exist
        if ref1_id is None:
            ref1_id = to_int_safe(matching_row.get("S19", pd.Series([None])).iloc[0])
        if ref2_id is None:
            ref2_id = to_int_safe(matching_row.get("S20", pd.Series([None])).iloc[0])

        # Extract first and last calibration sensor (typically S7 and S18 for 12 sensors)
        first_sensor = to_int_safe(matching_row.get("S7", pd.Series([None])).iloc[0])
        last_sensor = to_int_safe(matching_row.get("S18", pd.Series([None])).iloc[0])

        self.run_info = {
            "CalibSetNumber": calib_set,
            "Date": date,
            "N_Run": n_run,
            "First_Sensor_ID": first_sensor,
            "Last_Sensor_ID": last_sensor,
            "Ref1_ID": ref1_id,
            "Ref2_ID": ref2_id,
            "Ref1_Channel": ref1_chan,
            "Ref2_Channel": ref2_chan,
            "N_Ref1": n_ref1,
            "N_Ref2": n_ref2,
        }

    def get_reference_sensor_ids(self) -> list:
        """Get the IDs of reference sensors (channels 13-14, typically REF1 and REF2).
        
        These sensors are NOT part of the calibration tree and should be excluded
        from raised sensor detection and offset calculations.
        
        Returns:
            list: List of reference sensor IDs (excluding None values)
        """
        if self.run_info is None:
            self.read_run_info()
        
        ref_ids = []
        ref1 = self.run_info.get("Ref1_ID")
        ref2 = self.run_info.get("Ref2_ID")
        
        if ref1 is not None:
            ref_ids.append(ref1)
        if ref2 is not None:
            ref_ids.append(ref2)
        
        return ref_ids

    def offsets(self, tini: int = 20, tend: int = 40) -> pd.DataFrame:
        """Compute a symmetric mean offset matrix between active sensors in the given minute window.

        Returns a DataFrame indexed/columned by sensor id with mean offsets (sensor_i - sensor_j).
        """
        if self.temperature_data is None or self.temperature_data.empty:
            raise ValueError("No temperature data available.")

        t0 = self.temperature_data.index.min() + pd.Timedelta(minutes=tini)
        t1 = self.temperature_data.index.min() + pd.Timedelta(minutes=tend)

        # Try a label-based datetime slice first; some DatetimeIndex layouts can raise
        # KeyError when an exact Timestamp is not locatable. Fall back to integer
        # position slicing using searchsorted/get_indexer as a robust alternative.
        try:
            window = self.temperature_data.loc[t0:t1]
        except Exception:
            idx = self.temperature_data.index
            # searchsorted gives indices where the timestamps would be inserted
            start_ix = int(idx.searchsorted(t0))
            end_ix = int(idx.searchsorted(t1, side="right"))
            window = self.temperature_data.iloc[start_ix:end_ix]

        if window is None or window.empty:
            raise ValueError("No data in the requested time window to compute offsets.")

        sensors = [s for s in (self.sensor_mapping or {}).values() if s in window.columns]
        sensors = sensors or list(window.columns)
        mat = pd.DataFrame(index=sensors, columns=sensors, dtype=float)

        for i, s1 in enumerate(sensors):
            for j, s2 in enumerate(sensors):
                if i == j:
                    mat.loc[s1, s2] = 0.0
                elif i < j:
                    col1 = window[s1]
                    col2 = window[s2]
                    if col1.isna().all() or col2.isna().all():
                        val = np.nan
                    else:
                        val = (col1 - col2).mean()
                    mat.loc[s1, s2] = val
                    mat.loc[s2, s1] = -val if pd.notna(val) else np.nan

        self.offsets_data = mat
        print("Mean offsets computed.")
        return mat

    def stat_err_offsets(self, tini: int = -20, tend: int = 0) -> pd.DataFrame:
        """Compute RMS error around the mean offset for each sensor pair over a time window relative to run end.

        The default window is the last 20 minutes of the run (tini=-20, tend=0).
        """
        if not hasattr(self, "offsets_data"):
            raise ValueError("Offsets must be computed before RMS calculation.")
        if self.temperature_data is None or self.temperature_data.empty:
            raise ValueError("No temperature data available.")

        t_end = self.temperature_data.index.max()
        t0 = t_end + pd.Timedelta(minutes=tini)
        t1 = t_end + pd.Timedelta(minutes=tend)

        # As with offsets(), prefer label-based slicing but fall back to integer
        # positional slicing when the DatetimeIndex cannot locate the exact bounds.
        try:
            window = self.temperature_data.loc[t0:t1]
        except Exception:
            idx = self.temperature_data.index
            start_ix = int(idx.searchsorted(t0))
            end_ix = int(idx.searchsorted(t1, side="right"))
            window = self.temperature_data.iloc[start_ix:end_ix]

        sensors = [s for s in (self.sensor_mapping or {}).values() if s in window.columns]
        sensors = sensors or list(window.columns)
        rms_mat = pd.DataFrame(index=sensors, columns=sensors, dtype=float)

        for i, s1 in enumerate(sensors):
            for j, s2 in enumerate(sensors):
                if i == j:
                    rms_mat.loc[s1, s2] = 0.0
                elif i < j:
                    col1 = window[s1]
                    col2 = window[s2]
                    if col1.isna().all() or col2.isna().all():
                        val = np.nan
                    else:
                        mean_off = self.offsets_data.loc[s1, s2]
                        val = np.sqrt(((col1 - col2 - mean_off) ** 2).mean())
                    rms_mat.loc[s1, s2] = val
                    rms_mat.loc[s2, s1] = val

        self.rms_offsets = rms_mat
        print("RMS errors computed.")
        return rms_mat
