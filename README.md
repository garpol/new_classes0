# RTD Calibration System

Multi-round calibration system for RTD temperature sensors using weighted average method.

## About

This project calculates calibration constants for RTD (Resistance Temperature Detector) sensors organized in sets across multiple calibration rounds. The system processes data from three rounds (R1 → R2 → R3) and finds all possible calibration paths from each sensor to the reference sensor.

Main features:
- Processes multiple calibration rounds with hierarchical structure
- Calculates calibration constants using weighted average (1/error²)
- Explores all valid paths between sensors and reference
- Handles "raised" sensors with special calibration logic
- Generates CSV files ready to use
- **Automatic structure derivation** from config.yml (no need for tree.yaml!)

> **Note**: The `Sensor` class and `SENSOR.ipynb` notebook are provisional and not currently used in the production pipeline.

## Project Structure

```
RTD_Calibration/
├── config/
│   ├── config.yml              # Main configuration (sets, sensors, rounds)
│   └── reference_sensors.yaml  # Reference sensor definition
├── data/                        # NOT in git (see .gitignore)
│   ├── LogFile.csv             # Temperature files registry
│   ├── temperature_files/      # Raw temperature data
│   └── results/                # Output CSVs
├── docs/                        # NOT in git (AI-generated docs)
├── src/
│   ├── set.py                  # Set processing (local offsets)
│   ├── tree.py                 # Network construction (global offsets)
│   ├── run.py                  # Run processing
│   ├── logfile.py              # LogFile management
│   └── utils.py                # Helper functions
├── notebooks/
│   ├── SET.ipynb               # Individual set analysis
│   ├── RUN.ipynb               # Run analysis
│   ├── TREE.ipynb              # Complete tree analysis (MAIN)
│   └── SENSOR.ipynb            # Provisional, not used
└── main.py                     # Production script
```

## How to Use

### Running the Main Script

The `main.py` script processes all sets and generates calibration constants:

```bash
# Process default sets (3-39, complete Round 1)
python main.py

# Process specific range
python main.py --range 3 39

# Process specific sets
python main.py --sets 3 4 5 49 57
```

### Generated Outputs

The script generates two CSV files in `data/results/`:

1. **`calibration_analisis_multicamino.csv`**: Complete analysis with 3 strategies
   - First path
   - Minimum error path
   - **Weighted average (RECOMMENDED)**

2. **`calibration_constants_media_ponderada.csv`**: Simplified CSV for final use
   - Columns: Sensor, Set, Constante_Calibracion_K, Error_K, N_Caminos

### Interactive Analysis with Notebooks

For exploration and visualization, use the notebooks in order:

1. **`SET.ipynb`**: Analyze individual sets
2. **`TREE.ipynb`**: Complete multi-round analysis (MAIN)

## 📊 Methodology

### Calibration Structure

The system uses a three-round hierarchical structure:

- **Round 1 (R1)**: Sets 3-39 (sensors to calibrate)
- **Round 2 (R2)**: Sets 49-54 (intermediate bridges)
- **Round 3 (R3)**: Set 57 (final reference, sensor 48484)

### Sensor Types

- **Regular sensors**: 8-9 per set, standard calibration
- **Raised sensors**: 2 per set, calibrated first between them (Step 0) then to chain
- **Discarded sensors**: Marked in config, not calibrated

### How it Works

1. **Path exploration**: Finds all valid paths from each sensor to reference
2. **Per-path calculation**: Each path accumulates offsets and propagates errors (RSS)
3. **Weighted average**: Calculates weighted mean using 1/(error² + ε) as weight
4. **Raised sensors**: Have 2 paths (via other raised → 2 bridges R2→R3)
5. **Regular sensors**: Have 4 paths (2 raised R1 × 2 bridges R2→R3)

### Error Propagation

```
Error_total = sqrt(error_1² + error_2² + ... + error_n²)
```

## 📦 Requirements

### Python 3.12+

```bash
pip install pandas numpy matplotlib pyyaml
```

### Data Structure

Temperature files must follow this format:
- Columns: `fecha`, `hora`, sensor IDs (48060, 48176, etc.)
- Values: Resistances in Ohms
- Location: `data/temperature_files/RTD_Calibs/CalSetN_X/`

## 📈 Typical Results

For range 3-39 (complete Round 1):

- **Calculated sensors**: ~376 (304 regular + 72 raised)
- **Discarded sensors**: ~56
- **Average global error**: ~100-120 mK
- **Raised sensor error**: ~25 mK (better precision)
- **Average paths per sensor**: 2 (raised) or 4 (regular)

## 🔧 Configuration

### `config/config.yml`

Defines set structure, raised sensors, discarded sensors and rounds:

```yaml
sensors:
  sets:
    3.0:
      raised: [48203, 48479]
      discarded: [48060, 48176]
    # ... more sets
```

### Automatic Structure Derivation

**The system NO LONGER uses `tree.yaml`**. The round structure is automatically derived from `config.yml`:

- **Parent detection**: Sets identify their parents by comparing "raised" sensors between rounds
- **Round filtering**: Only connects sets from consecutive rounds (R2→R1, R3→R2)
- **Reference**: Defined in `config/reference_sensors.yaml`

**Example**: Set 57 (R3) automatically detects its 6 parents in R2 because it shares raised sensors with them.

## 📝 Important Notes

### Difference: Set vs Tree

**For students**: It's important to understand the distinction:

- **Set** (`set.py`): Processes A SINGLE calibration set (e.g., CalSetN_3)
  - Reads temperature files from that set
  - Calculates LOCAL offsets (within the set)
  - Averages pre/post measurements
  - Handles raised, regular, and discarded sensors

- **Tree** (`tree.py`): Connects ALL sets forming a calibration network
  - Automatically derives round structure from config.yml
  - Finds paths from each sensor to the reference (48484)
  - Calculates GLOBAL offsets (multi-round chain)
  - Performs weighted average of all available paths

**Typical flow**: Set (local offsets) → Tree (global chain) → Final constants

### Raised Sensors

Raised sensors require special handling:

- **Step 0**: Calibrated first against the OTHER raised sensor in same set
- **Steps 1-3**: Follow normal chain to reference
- **Rationale**: Physical validation in same bath before jumping rounds

### Recommended Range

**Use `--range 3 39`** to process complete Round 1. Sets outside this range may have incomplete connections.

## 👨‍💻 Author

RTD Calibration Project  
IFIC, UV 
