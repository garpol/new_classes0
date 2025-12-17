import pandas as pd
import os
import math
import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap
from typing import Literal
import numpy as np
try:
    from .run import Run
    from .utils import load_config, DEFAULT_CONFIG
except ImportError:
    from run import Run
    from utils import load_config, DEFAULT_CONFIG
import yaml
from typing import Optional

# Module-level default sensors (fallback) - kept here for backward compatibility but can be moved to config
DEFAULT_SENSORS = {
    'discarded_sensors': {
        3.0: [48205, 48478],
        60.0: [58384],
    },
    'sensors_raised_by_set': {
        3.0: [48203, 48479],
        54.0: [55233, 55221],
    },
    'set_rounds': {},
}

class Set:
    def __init__(self, logfile: pd.DataFrame, config: dict = None, config_path: Optional[str] = None) -> None:
        """Initialize a Set that groups multiple Run instances by CalibSetNumber.
        
        Parameters:
            logfile (pd.DataFrame): DataFrame containing sensor assignments and metadata
            config (dict, optional): Configuration dict with per-set sensor mappings.
                If provided, overrides default discarded_sensors/sensors_raised_by_set.
        """
        # If config_path provided, load it; otherwise normalize provided config dict
        combined_cfg = None
        try:
            if config_path:
                combined_cfg = load_config(config_path)
            elif isinstance(config, dict):
                # merge with defaults
                merged = DEFAULT_CONFIG.copy()
                for k, v in config.items():
                    if isinstance(v, dict) and isinstance(merged.get(k), dict):
                        merged[k] = {**merged[k], **v}
                    else:
                        merged[k] = v
                combined_cfg = merged
        except Exception as e:
            print(f"Warning: could not load config: {e}")

        # Configure logfile source: logfile parameter may be a DataFrame, or a path, or None
        if isinstance(logfile, pd.DataFrame):
            self.logfile = logfile
        else:
            # prefer path from config if available
            lf_path = None
            if combined_cfg:
                lf_path = combined_cfg.get('paths', {}).get('logfile')
            lf_path = logfile or lf_path
            from .logfile import Logfile
            lf = Logfile(filepath=lf_path)
            self.logfile = lf.log_file
            
        self.runs_by_set = {}  # Dict mapping CalibSetNumber to Run instances
        self.offsets_data = None  # Matrix of offsets from all runs
        self.rms_offsets_data = None  # Matrix of RMS errors from all runs
        self.calibration_constants = None  # Calibration constants calculated
        # Defaults; these can be overridden by passing a `config` dict or a `config_path` to Set
        self.discarded_sensors = DEFAULT_SENSORS.get('discarded_sensors', {})
        self.sensors_raised_by_set = DEFAULT_SENSORS.get('sensors_raised_by_set', {})
        # Default rounds mapping (can be overridden by config)
        self.set_rounds = DEFAULT_SENSORS.get('set_rounds', {})

        # Apply config overrides if provided (config dict or config_path)
        loaded_cfg = None
        if config_path and not config:
            try:
                with open(config_path, 'r') as f:
                    loaded_cfg = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: could not load config_path '{config_path}': {e}")
        elif isinstance(config, str) and not config_path:
            # config passed as a path string
            try:
                with open(config, 'r') as f:
                    loaded_cfg = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: could not load config from string path '{config}': {e}")
        elif isinstance(config, dict):
            loaded_cfg = config

        if loaded_cfg:
            try:
                sensors_cfg = loaded_cfg.get("sensors", {})
                # If user provided unified per-set structure under sensors.sets, prefer it
                sets_cfg = sensors_cfg.get("sets")
                if isinstance(sets_cfg, dict) and sets_cfg:
                    # normalize and populate the three dictionaries
                    sd = {}
                    sr = {}
                    srounds = {}
                    for ks, vv in sets_cfg.items():
                        # Normalize set key to float if possible; skip if not
                        try:
                            kf = float(ks)
                        except Exception:
                            try:
                                kf = float(str(ks))
                            except Exception:
                                # skip entries with non-numeric keys
                                continue
                        # support both Spanish and English keys inside each set entry
                        discarded_list = vv.get("discarded") or vv.get("descartados") or vv.get("discarded_sensors") or []
                        raised_list = vv.get("raised") or vv.get("rojo") or vv.get("sensors_raised") or []
                        sd[kf] = discarded_list
                        sr[kf] = raised_list
                        # parse round robustly; allow numeric strings, otherwise skip this field
                        round_raw = vv.get("round", 1)
                        try:
                            srounds[kf] = int(float(round_raw))
                        except Exception:
                            # ignore invalid non-numeric round values (e.g., 'Refs')
                            pass
                    # assign to English-named attributes consistently
                    self.discarded_sensors = sd
                    self.sensors_raised_by_set = sr
                    self.set_rounds = srounds
                else:
                    # backward-compatible fields (accept both English and Spanish keys)
                    if sensors_cfg.get("discarded_sensors") or sensors_cfg.get("descartados"):
                        raw = sensors_cfg.get("discarded_sensors") or sensors_cfg.get("descartados")
                        self.discarded_sensors = {float(k): v for k, v in raw.items()}
                    if sensors_cfg.get("sensors_raised_by_set") or sensors_cfg.get("sensors_raised") or sensors_cfg.get("rojo"):
                        raw = sensors_cfg.get("sensors_raised_by_set") or sensors_cfg.get("sensors_raised") or sensors_cfg.get("rojo")
                        self.sensors_raised_by_set = {float(k): v for k, v in raw.items()}
                    if sensors_cfg.get("set_rounds"):
                        normalized_rounds = {}
                        for k, v in sensors_cfg.get("set_rounds", {}).items():
                            try:
                                kf = float(k)
                            except Exception:
                                try:
                                    kf = float(str(k))
                                except Exception:
                                    continue
                            try:
                                normalized_rounds[kf] = int(float(v))
                            except Exception:
                                # skip invalid round values
                                continue
                        self.set_rounds = normalized_rounds
            except Exception as e:
                print(f"Warning: failed to apply sensors config: {e}")

        # plots default directory (can be controlled via config paths)
        self.plots_dir = None
        if config and isinstance(config, dict):
            paths_cfg = config.get("paths", {})
            self.plots_dir = paths_cfg.get("plots_dir")
        if not self.plots_dir:
            self.plots_dir = "RTD_Calibration_VGP/notebooks/Plots"
        # Output write defaults (can be overridden by providing 'output' in config loaded earlier)
        # Default to True for backward compatibility
        if not hasattr(self, 'write_csv'):
            self.write_csv = True
        if not hasattr(self, 'write_excel'):
            self.write_excel = True
        

    
    def group_runs_by_set(self, selected_sets=None) -> None:
        """
        Group runs by 'CalibSetNumber' and create instances of the 'Run' class for each one.
        Excludes filenames that contain certain keywords (e.g. 'pre', 'st', 'lar') and runs
        marked as 'BAD' in the Selection column.
        """
        try:
            import numpy as np
            # Usar .copy() para evitar SettingWithCopyWarning
            self.logfile = self.logfile.copy()
            self.logfile["CalibSetNumber"] = pd.to_numeric(self.logfile["CalibSetNumber"], errors='coerce')
            calib_set_numbers = self.logfile["CalibSetNumber"].unique()
            calib_set_numbers = sorted([
                calib_set_number for calib_set_number in calib_set_numbers
                if isinstance(calib_set_number, (int, float, np.integer, np.floating)) 
                and not pd.isna(calib_set_number)
                and float(calib_set_number).is_integer()
                and calib_set_number > 0
                and len(str(int(calib_set_number))) <= 2  # Verify that the number has two or fewer digits
            ])
            excluded_keywords = ['pre', 'st', 'lar']  # Palabras a excluir de los filenames
            # Agrupar los runs por CalibSetNumber
            for calib_set_number in calib_set_numbers:
                if selected_sets and calib_set_number not in selected_sets:
                    continue
                print(f"\nProcessing CalibSetNumber: {calib_set_number}")
                # Filtramos el logfile para obtener todos los runs de este CalibSetNumber
                runs_in_set = self.logfile[self.logfile["CalibSetNumber"] == calib_set_number]
                valid_runs = {}
                # self.runs_by_set[calib_set_number] = {} now initialized later with valid sets

                # Iteramos por cada run en el set
                for _, run_row in runs_in_set.iterrows():
                    filename = run_row["Filename"]
                    selection = run_row["Selection"]

                    if isinstance(filename, str) and all(keyword not in filename.lower() for keyword in excluded_keywords):
                        # Include runs where Selection is not 'BAD' (including NaN/empty values)
                        if pd.isna(selection) or selection != "BAD":
                            run_instance = Run(filename, self.logfile)
                            # Try to associate sensors, read run info, and filter faulty channels
                            try:
                                run_instance.associate_sensors()
                                run_instance.read_run_info()
                                # Call filter_faulty_channels to detect additional issues beyond NaN counts
                                faulty = run_instance.filter_faulty_channels()
                                # Update defective_channels with any additional issues found
                                if faulty:
                                    # Merge detected faults into defective_channels (avoid duplicates)
                                    existing_defective = set(run_instance.defective_channels or [])
                                    existing_defective.update(faulty.keys())
                                    run_instance.defective_channels = list(existing_defective)
                            except Exception as e:
                                print(f"    Warning: failed to associate sensors or read run info for {filename}: {e}. Skipping this run.")
                                continue
                            # If association succeeded, keep the run
                            valid_runs[filename] = run_instance
                            print(f"    Included: {filename}")
                        else:
                            print(f"    Excluded: {filename} (marked as 'BAD' in Selection)")
                    else:
                        print(f"    Excluded: {filename} (contains 'pre' or 'st')")
                        
                # Only save the group if there are valid runs
                if valid_runs:
                    self.runs_by_set[calib_set_number] = valid_runs
                        
        except KeyError as e:
            print(f"Error: {e}")
            raise
            
        except Exception as e:
            raise RuntimeError(f"Error grouping runs: {e}")

    def calculate_offsets_and_rms(self, selected_sets=None) -> None:
        """
        Calcula los offsets y errores RMS para todos los runs en el conjunto,
        manteniendo el orden de los sensores basado en el primer run (con más sensores).
        Si el orden de sensores difiere en algún run, se reorganizan las matrices
        para que coincidan con el del run de referencia.
        """
        try:
            offsets_list = []
            rms_list = []
            keys_for_concat = []

            # Itera sobre los runs y calcula offsets y RMS
            for calib_set_number, runs_in_set in self.runs_by_set.items():
                if selected_sets and calib_set_number not in selected_sets:
                    continue
                print(f"\nProcessing CalibSetNumber: {calib_set_number}")

                # Find the run with the most sensors (reference) within this set
                max_sensors = 0
                reference_run = None
                for run_instance in runs_in_set.values():
                    if run_instance.sensor_mapping is not None:
                        num_sensors = len(run_instance.sensor_mapping)
                        if num_sensors > max_sensors:
                            max_sensors = num_sensors
                            reference_run = run_instance
                    else:
                        print(f"Warning: sensor_mapping is None for run {run_instance.filename}. Skipping this run.")

                if not reference_run:
                    print(f"No valid run found to compute offsets in set {calib_set_number}.")
                    continue

                print(f"Reference run has {max_sensors} sensors: {reference_run.filename}")
                print("Reference sensor mapping:")
                print(f"Sensor_mapping : {reference_run.sensor_mapping}")

                # Usa el orden del run de referencia
                reference_sensors = list(reference_run.sensor_mapping.values())
                print(f"Reference based on run: {reference_run.filename} with sensors: {reference_sensors}")

                for filename, run_instance in runs_in_set.items():
                    print(f"  Processing Run: {filename}")

                    if run_instance.sensor_mapping is not None:
                        current_sensors = list(run_instance.sensor_mapping.values())
                        print(f"Current sensors: {current_sensors}")

                        try:
                            # Calcular offsets y RMS
                            offsets = run_instance.offsets()
                            rms_offsets = run_instance.stat_err_offsets()

                            # Crear DataFrames con el orden actual
                            offsets_df = pd.DataFrame(offsets, index=current_sensors, columns=current_sensors)
                            rms_df = pd.DataFrame(rms_offsets, index=current_sensors, columns=current_sensors)

                            print("  → ORIGINAL offsets matrix:")
                            print(offsets_df)

                            # Reorder rows and columns according to reference order
                            offsets_df = offsets_df.reindex(index=reference_sensors, columns=reference_sensors)
                            rms_df = rms_df.reindex(index=reference_sensors, columns=reference_sensors)

                            print("  → REORDERED offsets matrix:")
                            print(offsets_df)

                            offsets_list.append(offsets_df)
                            rms_list.append(rms_df)
                            keys_for_concat.append(calib_set_number)

                            print(f"  Dimensiones de la matriz de offsets: {offsets_df.shape}")
                            print(f"  Dimensiones de la matriz de RMS: {rms_df.shape}")
                        except Exception as e:
                            print(f"  ⚠️  Warning: Could not compute offsets for run {filename}: {str(e)[:100]}")
                            print(f"  ⏭️  Skipping this run and continuing with the rest...")
                    else:
                        print(f"Warning: Cannot compute offsets or RMS for run {run_instance} because sensor_mapping is None.")

            # Construye las matrices de offsets y RMS
            if offsets_list:
                # keys_for_concat aligns with each appended run matrix in offsets_list/rms_list
                self.offsets_data = pd.concat(offsets_list, axis=1, keys=keys_for_concat)
                self.rms_offsets_data = pd.concat(rms_list, axis=1, keys=keys_for_concat)

            print("Offsets and RMS calculations complete.")

        except ValueError as e:
            print(f"Error: {e}")
            raise RuntimeError(f"Error calculating offsets and RMS errors: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise RuntimeError(f"Error calculating offsets and RMS errors: {e}")


    def offset_repeatability(self, tini=20, tend=40, save_dir="offset_repeatability_copy", selected_sets=None, ref=2, write_csv=None, write_excel=None):

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        self.global_stats = {}
        # record skipped runs due to defective channels for auditing
        skipped_runs_list = []
        # record outliers filtered by IQR method
        outliers_filtered = []
        calib_sets_to_process = self.runs_by_set.keys() if selected_sets is None else set(selected_sets)

        for calib_set_number in calib_sets_to_process:
            runs = self.runs_by_set.get(calib_set_number)
            if runs is None:
                print(f"WARNING: Set {calib_set_number} not in self.runs_by_set, skipping.")
                continue

            print(f"\nProcessing CalibSetNumber: {calib_set_number}")

            filenames = list(runs.keys())
            first_run = runs[filenames[0]]

            if first_run.sensor_mapping is None:
                print(f"WARNING: sensor_mapping is None for the first run of set {calib_set_number}, skipping set.")
                continue

            mapping = first_run.sensor_mapping

            sensor_names = {}
            for ch in range(1, 15):
                sensor_names[ch] = mapping.get(f"channel_{ch}", None)

            # Determine dynamic or fixed references
            ref_channel_por_sensor = {}

            red_ids = self.sensors_raised_by_set.get(calib_set_number, [])
            if red_ids and len(red_ids) >= 2:
                # Mapear IDs a canales
                red_channels = []
                for red_id in red_ids[:2]:  # solo usar los primeros dos
                    for ch, sid in sensor_names.items():
                        if str(sid).strip() == str(red_id).strip():
                            red_channels.append(ch)
                            break

                if len(red_channels) < 2:
                    print(f"WARNING: Could not find both raised sensors in mapping for set {calib_set_number}, using fixed reference channel {ref}.")
                    red_channels = []
            else:
                red_channels = []

            if len(red_channels) == 2:
                print(f"OK: Set {calib_set_number}: Using dynamic references from raised sensors in channels {red_channels}")
                for ch in range(1, 15):
                    if sensor_names[ch] is None:
                        continue
                    if ch in red_channels:
                        # If it's one of the raised sensors, use the other as reference
                        ref_channel_por_sensor[ch] = [r for r in red_channels if r != ch][0]
                    else:
                        # Distancia circular
                        distances = [
                            (abs(ch - red) % 12 if abs(ch - red) % 12 <= 6 else 12 - abs(ch - red) % 12)
                            for red in red_channels
                        ]
                        closest_idx = np.argmin(distances)
                        ref_channel_por_sensor[ch] = red_channels[closest_idx]
            else:
                # No raised sensors: use fixed reference channel
                print(f"INFO: Set {calib_set_number}: Using fixed reference channel {ref} → Sensor ID {sensor_names.get(ref)}")
                for ch in range(1, 15):
                    if sensor_names[ch] is not None:
                        ref_channel_por_sensor[ch] = ref

            # Plot setup
            fig, axes = plt.subplots(3, 5, figsize=(21, 13))
            axes = axes.flatten()
            fig.subplots_adjust(top=0.80)
            for ax in axes[14:]:
                ax.set_visible(False)

            for idx in range(14):
                channel_num = idx + 1
                sensor_id = sensor_names.get(channel_num, None)

                if sensor_id is None:
                    axes[idx].set_visible(False)
                    continue

                ref_ch = ref_channel_por_sensor[channel_num]
                ref_sensor_id = sensor_names.get(ref_ch, "Unknown")

                # Avoid duplicates between raised sensor pairs
                if channel_num in red_channels and ref_ch in red_channels:
                    if channel_num > ref_ch:
                        axes[idx].set_visible(False)
                        continue

                axes[idx].set_title(
                    f"Offset: Ref Ch {ref_ch} ({ref_sensor_id}) - Ch {channel_num} ({sensor_id})",
                    fontsize=11,
                    fontweight="bold"
                )
                axes[idx].set_xlabel("Time (minutes)", fontsize=10, fontweight="bold")
                axes[idx].set_ylabel("Offset (mK)", fontsize=10, fontweight="bold")
                axes[idx].grid(which='both', linestyle='--', linewidth=0.5)

                run_means = []
                run_stds = []
                run_labels = []

                for run_index, filename in enumerate(filenames):
                    run_label = f"Run {run_index + 1}"
                    run = runs[filename]

                    if run.sensor_mapping is None:
                        print(f"WARNING: sensor_mapping is None for run {filename} in set {calib_set_number}, skipping run.")
                        continue

                    # If this run detected defective channels, skip it for this sensor pair
                    defective = getattr(run, 'defective_channels', []) or []
                    # defective contains channel names like 'channel_8'; map sensor ids back to channel names
                    # find the channel name(s) corresponding to sensor_id and ref_sensor_id
                    skip_due_to_defect = False
                    try:
                        # find channel key for this sensor_id and ref_sensor_id
                        channel_for_sensor = None
                        channel_for_ref = None
                        for ch_key, sid in run.sensor_mapping.items():
                            if str(sid) == str(sensor_id):
                                channel_for_sensor = ch_key
                            if str(sid) == str(ref_sensor_id):
                                channel_for_ref = ch_key
                        if channel_for_sensor in defective or channel_for_ref in defective:
                            skip_due_to_defect = True
                    except Exception:
                        skip_due_to_defect = False

                    if skip_due_to_defect:
                        print(f"  Skipping run {filename} for sensor {sensor_id} because defective channels detected: {defective}")
                        # record skipped runs for auditing
                        skipped_entry = {
                            'CalibSetNumber': calib_set_number,
                            'SensorID': sensor_id,
                            'RunFilename': filename,
                            'DefectiveChannels': ";".join(defective) if defective else ''
                        }
                        skipped_runs_list.append(skipped_entry)
                        continue

                    temperature_data = run.temperature_data
                    time_start = temperature_data.index.min()
                    time_20min = time_start + pd.Timedelta(minutes=tini)
                    time_40min = time_start + pd.Timedelta(minutes=tend)
                    mask = (temperature_data.index >= time_20min) & (temperature_data.index <= time_40min)
                    filtered_data = temperature_data.loc[mask]
                    #filtered_data = temperature_data.loc[time_20min:time_40min]
                    time_relative = (filtered_data.index - time_20min).total_seconds() / 60

                    try:
                        ref_temp = filtered_data[str(ref_sensor_id)]
                        sensor_temp = filtered_data[str(sensor_id)]
                        offset = 1e3 * (ref_temp - sensor_temp)
                    except KeyError:
                        offset = pd.Series([float('nan')] * len(filtered_data), index=filtered_data.index)

                    offset_values = offset.dropna().values
                    if len(offset_values) > 1:
                        run_mean = np.mean(offset_values)
                        run_std = np.std(offset_values, ddof=1)
                        print(f"  [Sensor Ch {channel_num} vs Ref Ch {ref_ch} | {run_label}] Mean: {run_mean:.3f} mK, Std: {run_std:.3f} mK")
                    else:
                        run_mean = np.nan
                        run_std = np.nan

                    run_means.append(run_mean)
                    run_stds.append(run_std)
                    run_labels.append(run_label)

                    axes[idx].plot(time_relative, offset, label=run_label)

                run_means = np.array(run_means)
                run_stds = np.array(run_stds)
                valid = ~np.isnan(run_means) & ~np.isnan(run_stds) & (run_stds > 0)

                if np.sum(valid) >= 2:
                    # Filter outliers using IQR method to remove extreme values
                    valid_means = run_means[valid]
                    valid_stds = run_stds[valid]
                    valid_labels = [run_labels[i] for i, v in enumerate(valid) if v]
                    
                    # Calculate IQR on valid means
                    q1 = np.percentile(valid_means, 25)
                    q3 = np.percentile(valid_means, 75)
                    iqr = q3 - q1
                    
                    # Define outlier bounds (using 3*IQR for extreme outliers)
                    lower_bound = q1 - 3 * iqr
                    upper_bound = q3 + 3 * iqr
                    
                    # Filter out extreme outliers
                    outlier_mask = (valid_means >= lower_bound) & (valid_means <= upper_bound)
                    
                    # Log outliers that were filtered out
                    num_outliers = np.sum(~outlier_mask)
                    if num_outliers > 0:
                        print(f"  ⚠️  Filtered {num_outliers} outlier(s) for sensor channel {idx} using IQR (bounds: [{lower_bound:.2f}, {upper_bound:.2f}] mK)")
                        for i, is_outlier in enumerate(~outlier_mask):
                            if is_outlier:
                                print(f"      - {valid_labels[i]}: mean={valid_means[i]:.2f} mK (outside IQR bounds)")
                                outlier_record = {
                                    'CalibSetNumber': calib_set_number,
                                    'SensorID': idx,
                                    'RunLabel': valid_labels[i],
                                    'Mean_mK': valid_means[i],
                                    'Std_mK': valid_stds[i],
                                    'IQR_Lower': lower_bound,
                                    'IQR_Upper': upper_bound,
                                    'Reason': 'IQR_outlier'
                                }
                                outliers_filtered.append(outlier_record)
                    
                    if np.sum(outlier_mask) >= 2:
                        # Recalculate with filtered data
                        filtered_means = valid_means[outlier_mask]
                        filtered_stds = valid_stds[outlier_mask]
                        weights = 1 / filtered_stds ** 2
                        global_mean = np.average(filtered_means, weights=weights)
                        global_sigma = np.std(filtered_means, ddof=1)
                    elif np.sum(outlier_mask) == 1:
                        # Only one point remains after filtering, use it but mark sigma as NaN
                        global_mean = valid_means[outlier_mask][0]
                        global_sigma = np.nan
                    else:
                        # All points were outliers (unlikely), fall back to unfiltered calculation
                        weights = 1 / valid_stds ** 2
                        global_mean = np.average(valid_means, weights=weights)
                        global_sigma = np.std(valid_means, ddof=1)
                else:
                    # Not enough valid runs to compute a reproducibility estimate.
                    # Use NaN so downstream aggregation and histograms can ignore these.
                    global_mean = np.nan
                    global_sigma = np.nan

                # DEBUG: Print sigma values to identify sources of high sigmas
                if global_sigma > 100:
                    print(f"⚠️  HIGH SIGMA DETECTED: Set {calib_set_number}, Channel {idx}, σ={global_sigma:.2f} mK")
                    print(f"    Valid means: {valid_means[outlier_mask] if np.sum(outlier_mask) > 0 else valid_means}")
                    print(f"    IQR bounds: [{lower_bound:.2f}, {upper_bound:.2f}]")
                
                if calib_set_number not in self.global_stats:
                    self.global_stats[calib_set_number] = {}
                self.global_stats[calib_set_number][idx] = {
                    "mean": global_mean,
                    "sigma": global_sigma,
                    "run_means": run_means.tolist(),
                    "run_stds": run_stds.tolist(),
                    "run_labels": run_labels
                }

                # Display 'N/A' for non-finite values to avoid 'nan' showing up on plots
                def fmt(x):
                    try:
                        if x is None or (isinstance(x, float) and (np.isnan(x) or not np.isfinite(x))):
                            return 'N/A'
                        return f"{x:.3f}"
                    except Exception:
                        return 'N/A'

                stats_text = f"$\\mu$ = {fmt(global_mean)} mK\n$\\sigma$ = {fmt(global_sigma)} mK"
                axes[idx].text(
                    0.95, 0.95,
                    stats_text,
                    fontsize=9,
                    fontweight="bold",
                    ha="right",
                    va="top",
                    transform=axes[idx].transAxes,
                    bbox=dict(boxstyle="round", facecolor="white", edgecolor="black", alpha=0.8)
                )

                axes[idx].legend(fontsize=8, loc="upper left", ncol=1)

            fig.suptitle(
                f"Offset Repeatability for Set {int(calib_set_number)} (Ref channels assigned per sensor)",
                fontsize=20,
                fontweight="bold"
            )
            fig.tight_layout()
            plot_filename = os.path.join(save_dir, f"offset_repeatability_set_{calib_set_number}.png")
            fig.savefig(plot_filename)
            print(f"Plot saved to: {plot_filename}")
            plt.close(fig)

        print("Global data saved in self.global_stats")

        # Save summary CSV/Excel (guarded by flags)
        csv_rows = []
        for calib_set, sensors in self.global_stats.items():
            for idx, stats in sensors.items():
                row = {
                    "CalibSetNumber": calib_set,
                    "SensorIndex": idx,
                    "WeightedMean": stats["mean"],
                    "SigmaOfMeans": stats["sigma"]
                }
                for i, (mean, std, label) in enumerate(zip(stats["run_means"], stats["run_stds"], stats["run_labels"])):
                    row[f"Run_{i + 1}_Label"] = label
                    row[f"Run_{i + 1}_Mean"] = mean
                    row[f"Run_{i + 1}_Std"] = std
                csv_rows.append(row)

        df_csv = pd.DataFrame(csv_rows)
        # Resolve effective flags: prefer explicit args, otherwise use instance defaults
        effective_write_csv = self.write_csv if write_csv is None else bool(write_csv)
        effective_write_excel = self.write_excel if write_excel is None else bool(write_excel)

        csv_path = os.path.join(save_dir, "offset_repeatability_summary.csv")
        if effective_write_csv:
            df_csv.to_csv(csv_path, index=False)
            print(f"Summary CSV saved to: {csv_path}")
        else:
            print("Skipping CSV write (write_csv disabled)")

        # Additionally save a CSV with skipped runs due to defective channels, if any
        try:
            skipped_csv_path = os.path.join(save_dir, 'skipped_runs_due_to_defects.csv')
            if 'skipped_runs_list' in locals() and skipped_runs_list:
                pd.DataFrame(skipped_runs_list).to_csv(skipped_csv_path, index=False)
                print(f"Skipped runs (defects) saved to: {skipped_csv_path}")
            else:
                print("No skipped runs due to defects were recorded.")
        except Exception as e:
            print(f"Warning: could not write skipped-runs CSV ({e})")
        
        # Save a CSV with outliers filtered by IQR method, if any
        try:
            outliers_csv_path = os.path.join(save_dir, 'outliers_filtered_by_iqr.csv')
            if 'outliers_filtered' in locals() and outliers_filtered:
                pd.DataFrame(outliers_filtered).to_csv(outliers_csv_path, index=False)
                print(f"Outliers filtered by IQR saved to: {outliers_csv_path}")
            else:
                print("No outliers were filtered by IQR method.")
        except Exception as e:
            print(f"Warning: could not write outliers CSV ({e})")

        excel_path = os.path.join(save_dir, "offset_repeatability_summary.xlsx")
        if effective_write_excel:
            try:
                df_csv.to_excel(excel_path, index=False)
                print(f"Excel saved to: {excel_path}")
            except Exception as e:
                print(f"Warning: could not write Excel file ({e}), continuing.")
        else:
            print("Skipping Excel write (write_excel disabled)")


    def calculate_weighted_mean_offsets(self, selected_sets=None) -> dict:
        """
        Calcula una matriz de constantes de calibración y los errores asociados (RMS de offsets)
        para cada CalibSetNumber.

        Retorna:
            dict: Un diccionario donde las claves son los CalibSetNumber y los valores son
                  las matrices 14x14 de constantes de calibración con nombres de sensores.
        """
        try:
            calibration_constants = {}  # Dictionary to store calibration constant matrices
            calibration_errors = {}     # Diccionario para almacenar matrices de errores asociados
            
            # Filtrar conjuntos de datos si se proporciona `selected_sets`, donde seleccionamos 1 o varios del total de sets
            calib_sets_to_process = self.runs_by_set.keys() if selected_sets is None else set(selected_sets)

            for calib_set_number, runs_in_set in self.runs_by_set.items():
                if calib_set_number not in calib_sets_to_process:
                    continue
                print(f"\nProcessing CalibSetNumber: {calib_set_number}")

                # Find the run with the most sensors (reference) that is usually the first to reorder the offset matrices if in any run the same mapping does not occur
                max_sensors = 0
                reference_run = None

                for run_instance in runs_in_set.values():
                    if run_instance.sensor_mapping is not None:
                        num_sensors = len(run_instance.sensor_mapping)
                        if num_sensors > max_sensors:
                            max_sensors = num_sensors
                            reference_run = run_instance
                    else:
                        print(f"Warning: sensor_mapping is None for run {run_instance.filename}. Skipping this run.")

                if not reference_run:
                    print(f"Warning: No valid run found to compute offsets for CalibSetNumber {calib_set_number}, skipping this set.")
                    continue

                print(f"  Selected reference run: {reference_run.filename}")
                print(f"  Reference sensor mapping: {reference_run.sensor_mapping}")

                reference_sensors = list(reference_run.sensor_mapping.values())
                print(f"  Reference sensors: {reference_sensors}")

                # Extraer las matrices de offsets y RMS para este set
                offsets_matrices = []
                rms_matrices = []

                for run_instance in runs_in_set.values():
                    if run_instance.sensor_mapping is not None:
                        offsets = run_instance.offsets()
                        rms_offsets = run_instance.stat_err_offsets()

                        # Crear DataFrames con el orden actual
                        offsets_df = pd.DataFrame(offsets)
                        rms_df = pd.DataFrame(rms_offsets)

                        # Reorder rows and columns according to reference order. WE SHOULD CALCULATE IT ONLY FOR THE LAST 20 MIN.
                        offsets_df = offsets_df.reindex(index=reference_sensors, columns=reference_sensors)
                        rms_df = rms_df.reindex(index=reference_sensors, columns=reference_sensors)

                        print(f"  → Offsets matrix for {run_instance.filename}:")
                        print(offsets_df)
                        print(f"  → Errors (RMS) matrix for {run_instance.filename}:")
                        print(rms_df)

                        offsets_matrices.append(offsets_df.values)
                        rms_matrices.append(rms_df.values)

                    else:
                        print(f"Advertencia: No se puede calcular offsets ni RMS para el run {run_instance.filename} porque sensor_mapping es None.")

                # Convertir las listas de matrices a arrays numpy para facilitar las operaciones
                offsets_array = np.array(offsets_matrices)  # Forma (num_runs, 14, 14)
                rms_array = np.array(rms_matrices)          # Forma (num_runs, 14, 14)

                # Create a valid boolean mask: excludes NaN and values greater than 1 in offsets
                valid_mask = ~np.isnan(offsets_array) & (offsets_array <= 1)

                # Create a mask for valid values in RMS (excludes NaN)
                valid_rms_mask = ~np.isnan(rms_array)

                # Combined final mask: valid values in both offsets and RMS
                final_mask = valid_mask & valid_rms_mask

                # Calcular los pesos como el inverso del cuadrado de los RMS
                # Avoid division by zero: only compute weights where rms != 0
                weights = np.zeros_like(rms_array, dtype=float)  # Inicializar matriz de pesos
                mask_nonzero_rms = final_mask & (rms_array != 0)
                if np.any(mask_nonzero_rms):
                    weights[mask_nonzero_rms] = 1.0 / (rms_array[mask_nonzero_rms] ** 2)

                # Calcular el numerador y el denominador de la media ponderada
                weighted_sum = np.sum(offsets_array * weights, axis=0)  # Suma ponderada de offsets
                total_weights = np.sum(weights, axis=0)  # Suma de los pesos

                # Avoid division by zero at positions where all weights are zero
                with np.errstate(divide='ignore', invalid='ignore'):
                    constants_matrix = np.divide(weighted_sum, total_weights)
                    constants_matrix[total_weights == 0] = np.nan  # Assign NaN where there is no valid data
                    
                print("\n=== ERROR CALCULATION ===")
                print(f"offsets_array shape: {offsets_array.shape}")
                print("Example offsets_array[0]:")
                print(offsets_array[0])  # First run

                # Calculate the associated error as the RMS of offsets for each position (i, j). REVIEW. 
                #errors_matrix = np.sqrt(np.mean(offsets_array ** 2, axis=0))
                errors_matrix = np.std(offsets_array, axis=0, ddof=1)
                
                print("Calculated RMS errors matrix (errors_matrix):")
                print(errors_matrix)

                # Obtener los nombres de los sensores desde el primer run
                sensor_names = list(runs_in_set.values())[0].sensor_mapping.values()
                

                # Crear DataFrames para las matrices de constantes y errores
                constants_df = pd.DataFrame(constants_matrix, index=sensor_names, columns=sensor_names)
                errors_df = pd.DataFrame(errors_matrix, index=sensor_names, columns=sensor_names)
                

                # Print matrices for debugging
                print(f"Constants matrix for CalibSetNumber {calib_set_number}:")
                print(constants_df)
                print(f"Errors matrix for CalibSetNumber {calib_set_number}:")
                print(errors_df)

                # Almacenar las matrices resultantes en los diccionarios
                calibration_constants[calib_set_number] = constants_df
                calibration_errors[calib_set_number] = errors_df

            # Save the calibration and error matrices to an Excel file only if we have content
            if calibration_constants:
                excel_filename = 'calibration_constants_and_errors.xlsx'
                with pd.ExcelWriter(excel_filename) as writer:
                    for calib_set_number in calibration_constants:
                        # Save calibration constant matrices
                        constants_df = calibration_constants[calib_set_number]
                        # Use a safe sheet name
                        sheet_name_consts = f'CalibSet_{int(calib_set_number)}'
                        constants_df.to_excel(writer, sheet_name=sheet_name_consts)

                        # Guardar matrices de errores asociados
                        errors_df = calibration_errors[calib_set_number]
                        sheet_name_errors = f'Errors_CalibSet_{int(calib_set_number)}'
                        errors_df.to_excel(writer, sheet_name=sheet_name_errors)

                print(f"Calculation of constants and errors complete and saved in '{excel_filename}'.")
            else:
                print("No calibration constants calculated; skipping Excel export.")
            return calibration_constants, calibration_errors  # Add the errors

        except Exception as e:
            raise RuntimeError(f"Error calculating constants and associated errors: {e}")
            

   