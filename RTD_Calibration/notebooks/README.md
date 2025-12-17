# RTD Calibration Analysis Notebooks

This directory contains Jupyter notebooks for analyzing RTD calibration data.

## � Quick Navigation

- [Main Notebooks](#-main-notebooks) — Which notebook to use
- [Code Structure](#-code-structure) — Where to modify parameters
- [Common Modifications](#-common-modifications) — Step-by-step examples
- [Output Structure](#-output-structure) — Where to find results
- [Configuration](#-configuration) — Advanced settings
- [Troubleshooting](#-troubleshooting) — Common issues

---

## �📓 Main Notebooks

### **SET_BUENO.ipynb** (Recommended workflow)
Set-level analysis: processes multiple calibration runs grouped by `CalibSetNumber`.

**Workflow:**
1. Loads logfile and groups runs by calibration set
2. Calculates temperature offsets and RMS errors
3. Generates repeatability plots with IQR outlier filtering
4. Produces global mean/sigma plots across all sensors
5. Exports summary CSVs with calibration constants

**Outputs:** `outputs/plot_global_means/`, `outputs/plot_global_sigmas/`

---

### **RUN_BUENO.ipynb**
Run-level analysis: inspect individual temperature measurement files.

**Use cases:**
- Visual inspection of temperature time series
- Channel-by-channel offset plots
- Debugging faulty sensor readings

---

### **SET_BUENO_4runs.ipynb** ⭐ (Actualizado)
Análisis de sets con **exactamente 4 runs NO-BAD** (excluye 'BAD', solo LN2).

**Características:**
- ✅ Excluye runs marcados como `'BAD'` (solo GOOD o vacío)
- ✅ Filtra por `Liquid Media = LN2`
- ✅ Solo procesa sets con exactamente 4 runs válidos
- ✅ Gráfico visual destacando sets seleccionados (verde)
- ✅ Estructura moderna similar a ANALYSIS_ALL_SETS_LN2

**Uso:** Análisis de sets con calibración estándar completa (4 runs de calidad).

**Outputs:** `outputs/set_4runs_no_bad/`

---

### **TREE.ipynb**
Exploratory notebook for dataset structure analysis.

---

### **RUN_BUENO-STS.ipynb**
Run analysis with special temperature setpoint handling.

---

### **ANALYSIS_ALL_SETS_LN2.ipynb** ⭐ (Nuevo)
Análisis exhaustivo de **todos los calibration sets** con filtros completos.

**Características:**
- ✅ Procesa automáticamente todos los sets con ≥4 runs
- ✅ **Filtra por Liquid Media = LN2** (excluye LAr)
- ✅ Incluye/excluye runs 'BAD' (configurable)
- ✅ Análisis exploratorio con estadísticas de filtrado
- ✅ Gráficos comparativos y exports CSV

**Uso:** Ideal para análisis completos del dataset con control total sobre filtros.

**Outputs:** `outputs/analysis_all_sets_LN2_*/`

---

## 📂 Output Structure

```
outputs/
├── plot_global_means/         # Mean offset plots per sensor
│   ├── global_mean_offsets_part_*.png
│   ├── skipped_runs_due_to_defects.csv
│   ├── outliers_filtered_by_iqr.csv  (if outliers detected)
│   └── offset_repeatability_summary.csv
│
└── plot_global_sigmas/        # Sigma/repeatability histograms
    ├── global_sigma_histogram_round_*.png
    └── ...
```

### **Generated CSV Files:**

| File | Description |
|------|-------------|
| `skipped_runs_due_to_defects.csv` | Runs excluded due to faulty channels (filter_faulty_channels) |
| `outliers_filtered_by_iqr.csv` | Individual measurements filtered by IQR method (3×IQR bounds) |
| `offset_repeatability_summary.csv` | Statistical summary: mean, std, min, max per sensor |

---

## 🏗️ Code Structure

Understanding where to modify parameters for common tasks:

### **Core Modules** (`RTD_Calibration_VGP/src/`)

```
src/
├── run.py              # Individual run processing
│   ├── load_temperature_file()    # Temperature data loading
│   ├── filter_faulty_channels()   # Channel-level quality control
│   └── offsets()                  # Offset calculation (tini, tend params)
│
├── set.py              # Multi-run set analysis
│   ├── group_runs_by_set()        # Run grouping logic
│   ├── calculate_offsets_and_rms() # Offset aggregation
│   ├── offset_repeatability()     # Main plotting function
│   │   ↳ Parameters: tini, tend, ref, save_dir
│   ├── plot_global_means()        # Sensor mean plots
│   └── plot_global_sigmas()       # Repeatability histograms
│
├── logfile.py          # LogFile.csv interface
│   └── Logfile.log_file           # Main DataFrame attribute
│
└── utils.py            # Utilities (config loading, etc.)
```

### **Key Data Structures**

| Component | Location | Purpose |
|-----------|----------|---------|
| `LogFile.csv` | `RTD_Calibration_VGP/data/` | Run metadata (sensors, dates, selection status) |
| Temperature files | `data/temperature_files/RTD_Calibs/CalSetN_*/` | Raw temperature measurements (.txt) |
| `runs_by_set` | `Set` instance attribute | Dictionary: `{CalibSetNumber: {filename: Run}}` |
| `offsets_data` | `Set` instance attribute | Aggregated offset matrices after `calculate_offsets_and_rms()` |

---

## � Common Modifications

### **1. Change Time Window for Offset Calculation**

**Where:** `set.py` → `offset_repeatability()` or notebook cell calling it

**Parameters:**
- `tini=20` (default) — Start time for offset window (seconds)
- `tend=40` (default) — End time for offset window (seconds)

**Example in notebook:**
```python
s.offset_repeatability(
    tini=30,      # ← Change: start at 30 seconds
    tend=50,      # ← Change: end at 50 seconds
    save_dir='outputs/custom_window',
    write_csv=False,
    write_excel=False
)
```

**Effect:** Only temperature data between 30-50 seconds used for offset calculation.

---

### **2. Change Reference Sensor**

**Where:** `set.py` → `offset_repeatability()`

**Parameter:**
- `ref=2` (default) — Use sensor at position 2 as reference (or `'auto'` for dynamic selection)

**Example:**
```python
s.offset_repeatability(
    ref=5,        # ← Change: use sensor 5 as reference
    # or
    ref='auto'    # ← Use dynamic reference (raised sensors logic)
)
```

**Where reference is used:** Set 3 uses dynamic references from `sensors_raised_by_set[3.0] = [6, 12]`

---

### **3. Include/Exclude BAD Runs**

**Where:** Notebook `ANALYSIS_ALL_SETS_LN2.ipynb` → Cell 3 (Configuration)

**Parameter:**
```python
INCLUDE_BAD_RUNS = True   # ← Change to False to exclude
```

**Effect:** Filters rows where `Selection == 'BAD'` before processing.

**Alternative (code level):** `set.py` → `group_runs_by_set()` line 287:
```python
if selection != "BAD":    # ← Change logic here
```

---

### **4. Change Liquid Media Filter**

**Where:** Notebook `ANALYSIS_ALL_SETS_LN2.ipynb` → Cell 3

**Parameter:**
```python
LIQUID_MEDIA_FILTER = 'LN2'   # ← Change to 'LAr' or None
```

**Effect:** Only processes runs with specified liquid media type.

---

### **5. Adjust IQR Outlier Detection Threshold**

**Where:** `set.py` → `offset_repeatability()` line ~598-650

**Current logic:**
```python
iqr = q3 - q1
lower_bound = q1 - 3 * iqr    # ← Multiplier here
upper_bound = q3 + 3 * iqr    # ← Multiplier here
```

**To change:** Modify the multiplier (3 → 2.5 for stricter, 3 → 4 for looser)

**Effect:** More/fewer measurements flagged as outliers in `outliers_filtered_by_iqr.csv`

---

### **6. Change Minimum Runs per Set**

**Where:** Notebook `ANALYSIS_ALL_SETS_LN2.ipynb` → Cell 3

**Parameter:**
```python
MIN_RUNS_PER_SET = 4   # ← Change to 3, 5, etc.
```

**Or in code:** `set.py` → `group_runs_by_set()` line ~287

---

### **7. Modify Faulty Channel Detection**

**Where:** `run.py` → `filter_faulty_channels()` lines ~248-292

**Current thresholds:**
```python
# Temperature range
valid_temp = (temp >= 70) & (temp <= 320)  # ← Kelvin bounds

# NaN threshold
nan_count = df[channel].isna().sum()
if nan_count > 40:  # ← Max allowed NaNs

# Constant reading detection
if df[channel].std() < 1e-6:  # ← Variation threshold
```

**To modify:** Edit these numeric thresholds in the source code.

---

### **8. Add/Remove Sensors from Discarded List**

**Where:** `set.py` → `discarded_sensors` dictionary (lines ~120-140)

**Example:**
```python
self.discarded_sensors = {
    3.0: [8],        # ← Set 3: discard sensor 8 (channel 8)
    4.0: [8, 14],    # ← Set 4: discard sensors 8, 14
    # Add new entries:
    42.0: [5, 12],   # ← Custom: discard sensors 5, 12 in Set 42
}
```

**Effect:** Sensors excluded before statistical calculations and plotting.

---

### **9. Customize Plot Output Directory**

**Where:** Notebook cells or `set.py` function calls

**Parameter:**
```python
s.offset_repeatability(
    save_dir='outputs/my_custom_analysis',  # ← Change path
)
```

**Result location:** Plots saved to `RTD_Calibration_VGP/notebooks/outputs/my_custom_analysis/`

---

### **10. Disable CSV/Excel Export**

**Where:** Notebook cells calling `offset_repeatability()`

**Parameters:**
```python
s.offset_repeatability(
    write_csv=False,    # ← No CSV files
    write_excel=False,  # ← No Excel files
)
```

**Effect:** Only PNG plots generated (reduces clutter and processing time).

---

## �🔄 Typical Workflow

1. **Start kernel** and run cell 1 (module reload)
2. **Load data** (cell 2): reads LogFile.csv, groups runs, calculates offsets
3. **Configure parameters** (cell 3): set filters, thresholds, output directories
4. **Generate plots** (cells 4-5): creates mean/sigma visualizations
5. **Inspect outputs**: check `outputs/` directory for plots and CSVs

---

## 🛠️ Configuration

- **Config file**: `RTD_Calibration_VGP/config/config.yaml`
- **Per-set metadata**: `discarded_sensors`, `sensors_raised_by_set`, `set_rounds`
- **Logfile**: `RTD_Calibration_VGP/data/LogFile.csv`
- **Temperature files**: `RTD_Calibration_VGP/data/temperature_files/RTD_Calibs/CalSetN_*/`

---

## 🧪 Filtering Logic

### **1. Channel-level filtering** (`filter_faulty_channels()`)
Excludes entire channels with:
- Temperature outside valid range (70-320 K)
- >40 NaN values
- Constant readings (no variation)

### **2. Statistical outlier filtering** (IQR method)
Removes individual measurements outside:
- Lower bound: Q1 - 3×IQR
- Upper bound: Q3 + 3×IQR

Both filtering stages are logged to CSV files in the output directory.

---

## � Where to Find Results

### **By Analysis Type:**

| What you want | Location | File pattern |
|---------------|----------|--------------|
| **Offset repeatability plots** | `outputs/analysis_all_sets_LN2_*/repeatability_set_X/` | `offset_repeatability_set_X.png` |
| **Global mean plots** | `outputs/plot_global_means/` | `global_mean_offsets_part_*.png` |
| **Sigma histograms** | `outputs/plot_global_sigmas/` | `global_sigma_histogram_round_*.png` |
| **Outlier log** | Same as plots | `outliers_filtered_by_iqr.csv` |
| **Skipped runs log** | Same as plots | `skipped_runs_due_to_defects.csv` |
| **Statistical summary** | Same as plots | `offset_repeatability_summary.csv` |

### **Quick Find Commands:**

```bash
# Find all Set 3 outputs
find RTD_Calibration_VGP/notebooks/outputs -name "*set_3*"

# List all repeatability plots
find RTD_Calibration_VGP/notebooks/outputs -name "offset_repeatability*.png"

# Count total processed sets
find RTD_Calibration_VGP/notebooks/outputs -type d -name "repeatability_set_*" | wc -l

# Open specific plot (macOS)
open RTD_Calibration_VGP/notebooks/outputs/analysis_all_sets_LN2_with_bad/repeatability_set_3/offset_repeatability_set_3.0.png
```

---

## 🐛 Troubleshooting

### **Problem: Set X not appearing in outputs**

**Possible causes:**
1. **Fewer than minimum runs** — Check `MIN_RUNS_PER_SET` parameter (default 4)
2. **All runs filtered** — Check `skipped_runs_due_to_defects.csv` for that set
3. **Individual run failures** — Look for `⚠️ Warning: Could not compute offsets` in notebook output
4. **Liquid Media mismatch** — Verify `Liquid Media` column in LogFile matches filter

**Debug steps:**
```python
# Check how many runs in logfile for Set X
df = lf.log_file.copy()
df = df[df['Liquid Media'] == 'LN2']
df = df[df['CalibSetNumber'] == X]
print(f"Set {X}: {len(df)} runs in logfile")
print(df[['Filename', 'Selection']])
```

---

### **Problem: Module changes not taking effect**

**Solution:** Always run the reload cell **before** re-running analysis:

```python
# Cell: Reload module
import importlib
from RTD_Calibration_VGP.src import set as set_module
importlib.reload(set_module)
from RTD_Calibration_VGP.src.set import Set
```

**Alternative:** Restart kernel (Kernel → Restart & Run All)

---

### **Problem: "No data in requested time window"**

**Cause:** Temperature file has data but not within `tini`-`tend` range

**Solutions:**
1. **Adjust time window:**
   ```python
   s.offset_repeatability(tini=10, tend=60)  # Wider window
   ```

2. **Check actual data range:**
   ```python
   r = Run('problematic_filename', lf.log_file)
   print(f"Time range: {r.temperature_data['Time'].min()} - {r.temperature_data['Time'].max()}")
   ```

3. **Inspect raw file:**
   ```bash
   head -20 RTD_Calibration_VGP/data/temperature_files/RTD_Calibs/CalSetN_X/filename.txt
   ```

---

### **Problem: Sigma values too high (>1000 mK)**

**Cause:** Faulty channels not being filtered properly

**Solution:** Check if `filter_faulty_channels()` is called:

```python
# In notebook cell:
for fname, run in s.runs_by_set[set_num].items():
    faulty = run.filter_faulty_channels()
    if faulty:
        print(f"{fname}: faulty channels {faulty}")
```

**If not filtered:** Make sure `group_runs_by_set()` includes filtering step (line ~315-320 in `set.py`).

---

### **Problem: Too many outliers filtered**

**Cause:** IQR threshold too strict (3×IQR default)

**Solution:** Modify multiplier in `set.py` line ~600:
```python
lower_bound = q1 - 4 * iqr  # Looser (was 3)
upper_bound = q3 + 4 * iqr
```

---

### **Problem: Can't find temperature files**

**Cause:** Hard-coded path in `run.py` doesn't match your system

**Location:** `run.py` → `load_temperature_file()` line ~170:
```python
cernbox_base = Path('/eos/user/j/jcapotor/RTDdata/')
```

**Solution:** Create symlink or modify path:
```bash
# Option 1: Symlink
ln -s /your/actual/path /eos/user/j/jcapotor/RTDdata

# Option 2: Edit source
# Change cernbox_base in run.py to your path
```

---

### **Problem: Plots not updating**

**Causes & solutions:**
1. **Old files cached** → Delete `outputs/` directory and re-run
2. **Wrong output directory** → Check `save_dir` parameter
3. **Image viewer caching** → Close and reopen image

```bash
# Clean and regenerate
rm -rf RTD_Calibration_VGP/notebooks/outputs/analysis_all_sets_LN2_with_bad/
# Then re-run notebook cells
```

---

## 📝 Best Practices

- ✅ **Always reload the module** (cell 1) after editing `src/` code to avoid stale imports
- ✅ **Check CSV logs** to audit which data was filtered out
- ✅ **Use descriptive save_dir names** for different analyses (e.g., `outputs/test_strict_iqr/`)
- ✅ **Keep LogFile.csv backups** before manual edits
- ✅ **Document parameter changes** in notebook markdown cells
- ✅ **Plots are regenerable** — feel free to delete `outputs/` and re-run
- ✅ **Version control changes** to `src/` code for reproducibility

---

## 📚 Further Reading

- **Copilot Instructions:** `.github/copilot-instructions.md` — Project conventions and patterns
- **Main README:** `../../README.md` — Installation and quick start
- **Source Code:** `../src/` — Full implementation details
- **Documentation:** `../../docs/` — Analysis methodology and references
