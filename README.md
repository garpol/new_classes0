# RTD Calibration System# RTD Calibration System



Multi-round calibration system for RTD temperature sensors using weighted average method.Multi-round calibration system for RTD temperature sensors using weighted average method.



## About## About



This project calculates calibration constants for RTD (Resistance Temperature Detector) sensors organized in sets across multiple calibration rounds. The system processes data from three rounds (R1 → R2 → R3) and finds all possible calibration paths from each sensor to the reference sensor.This project calculates calibration constants for RTD (Resistance Temperature Detector) sensors organized in sets across multiple calibration rounds. The system processes data from three rounds (R1 → R2 → R3) and finds all possible calibration paths from each sensor to the reference sensor.



Main features:Main features:

- Processes multiple calibration rounds with hierarchical structure- Processes multiple calibration rounds with hierarchical structure

- Calculates calibration constants using weighted average (1/error²)- Calculates calibration constants using weighted average (1/error²)

- Explores all valid paths between sensors and reference- Explores all valid paths between sensors and reference

- Handles "raised" sensors with special calibration logic- Handles "raised" sensors with special calibration logic

- Generates CSV files ready to use- Generates CSV files ready to use



## Project Structure## Project Structure



``````

RTD_Calibration/RTD_Calibration/

├── config/├── config/

│   ├── config.yml              # Main configuration (sets, sensors, rounds)│   ├── config.yml              # Main configuration (sets, sensors, rounds)

│   └── tree.yaml              # Calibration tree structure│   └── tree.yaml              # Calibration tree structure

├── data/├── data/

│   ├── LogFile.csv            # Temperature files registry│   ├── LogFile.csv            # Temperature files registry

│   ├── temperature_files/     # Raw temperature data│   ├── temperature_files/     # Raw temperature data

│   └── results/               # Output CSVs│   └── results/               # Output CSVs

├── src/├── src/

│   ├── set.py                 # Set processing│   ├── set.py                 # Set processing

│   ├── tree.py                # Tree construction and multi-path calculation│   ├── tree.py                # Tree construction and multi-path calculation

│   ├── run.py                 # Run processing│   ├── run.py                 # Run processing

│   └── logfile.py             # LogFile management│   └── logfile.py             # LogFile management

├── notebooks/├── notebooks/

│   ├── SET.ipynb              # Individual set analysis│   ├── SET.ipynb              # Individual set analysis

│   ├── RUN.ipynb              # Run analysis│   ├── RUN.ipynb              # Run analysis

│   └── TREE.ipynb             # Complete tree analysis (MAIN)│   └── TREE.ipynb             # Complete tree analysis (MAIN)

└── main.py                    # Production script└── main.py                    # Production script

``````



## How to Use## How to Use



### Running the Main Script### Running the Main Script



```bashThe `main.py` script processes all sets and generates calibration constants:

# Process default range (sets 3-39, complete Round 1)

python main.py```bash

# Procesar sets por defecto (3-39, Ronda 1 completa)

# Process specific rangepython main.py

python main.py --range 3 39

# Procesar rango específico

# Process specific setspython main.py --range 3 39

python main.py --sets 3 4 5 49 57

```# Procesar sets específicos

python main.py --sets 3 4 5 49 57

### Output Files```



Two CSV files are generated in `data/results/`:### Salidas Generadas



1. **calibration_analisis_multicamino.csv** - Complete analysis with 3 strategies:El script genera dos archivos CSV en `data/results/`:

   - First path

   - Minimum error path  1. **`calibration_analisis_multicamino.csv`**: Análisis completo con 3 estrategias

   - Weighted average (recommended)   - Primer camino

   - Camino de mínimo error

2. **calibration_constants_media_ponderada.csv** - Simplified CSV for final use   - **Media ponderada (RECOMENDADO)**

   - Columns: Sensor, Set, Constante_Calibracion_K, Error_K, N_Caminos

2. **`calibration_constants_media_ponderada.csv`**: CSV simplificado para uso final

### Using Notebooks   - Columnas: Sensor, Set, Constante_Calibracion_K, Error_K, N_Caminos



For interactive exploration:### Análisis Interactivo con Notebooks



1. **SET.ipynb** - Analyze individual setsPara exploración y visualización, usar los notebooks en orden:

2. **TREE.ipynb** - Complete multi-round analysis (main notebook)

1. **`SET.ipynb`**: Analizar un set individual

## Method2. **`TREE.ipynb`**: Análisis completo multi-ronda (PRINCIPAL)



### Calibration Structure## 📊 Metodología



Three-round hierarchy:### Estructura de Calibración



- **Round 1 (R1)**: Sets 3-39 (sensors to calibrate)El sistema usa una estructura jerárquica de tres rondas:

- **Round 2 (R2)**: Sets 49-54 (intermediate bridges)

- **Round 3 (R3)**: Set 57 (final reference, sensor 48484)- **Ronda 1 (R1)**: Sets 3-39 (sensores a calibrar)

- **Ronda 2 (R2)**: Sets 49-54 (puentes intermedios)

### Sensor Types- **Ronda 3 (R3)**: Set 57 (referencia final, sensor 48484)



- **Regular sensors**: 8-9 per set, standard calibration### Tipos de Sensores

- **Raised sensors**: 2 per set, calibrated first between them (Step 0) then to chain

- **Discarded sensors**: Marked in config, not calibrated- **Sensores regulares**: 8-9 por set, calibrados normalmente

- **Sensores "raised"**: 2 por set, calibrados primero entre sí (Paso 0) y luego hacia la cadena

### How it Works- **Sensores descartados**: Marcados en config, no se calibran



1. **Path exploration**: Finds all valid paths from each sensor to reference### Algoritmo de Cálculo

2. **Per-path calculation**: Each path accumulates offsets and propagates errors (RSS)

3. **Weighted average**: Calculates weighted mean using 1/(error² + ε) as weight1. **Exploración de caminos**: El sistema encuentra TODOS los caminos válidos desde cada sensor hasta la referencia

4. Raised sensors have 2 paths, regular sensors have 4 paths2. **Cálculo por camino**: Cada camino acumula offsets y propaga errores (RSS)

3. **Media ponderada**: Se calcula la media ponderada usando `1/(error² + ε)` como peso

Error propagation formula:4. **Sensores raised**: Tienen 2 caminos (via otro raised → 2 bridges R2→R3)

```5. **Sensores regulares**: Tienen 4 caminos (2 raised R1 × 2 bridges R2→R3)

Error_total = sqrt(error_1² + error_2² + ... + error_n²)

```### Propagación de Errores



## Requirements```

Error_total = sqrt(error_paso1² + error_paso2² + ... + error_pasoN²)

Python 3.12+```



```bash## 📦 Requisitos

pip install pandas numpy matplotlib pyyaml

```### Python 3.12+



## Typical Results```bash

pip install pandas numpy matplotlib pyyaml

For range 3-39 (complete Round 1):```



- Calculated sensors: ~376 (304 regular + 72 raised)### Estructura de Datos

- Discarded sensors: ~56

- Average global error: ~100-120 mKLos archivos de temperatura deben seguir el formato:

- Raised sensor error: ~25 mK (better precision)- Columnas: `fecha`, `hora`, sensor IDs (48060, 48176, etc.)

- Average paths per sensor: 2 (raised) or 4 (regular)- Valores: Resistencias en Ohms

- Ubicación: `data/temperature_files/RTD_Calibs/CalSetN_X/`

## Configuration

## 📈 Resultados Típicos

`config/config.yml` defines set structure, raised sensors, discarded sensors and rounds.

Para el rango 3-39 (Ronda 1 completa):

`config/tree.yaml` defines connections between rounds and sets.

- **Sensores calculados**: ~376 (304 regulares + 72 raised)

## Important Notes- **Sensores descartados**: ~56

- **Error medio global**: ~100-120 mK

### Raised Sensors- **Error sensores raised**: ~25 mK (mejor precisión)

- **Caminos promedio**: 2 (raised) o 4 (regulares)

Raised sensors need special handling:

- **Step 0**: Calibrated first against the other raised sensor in same set## 🔧 Configuración

- **Steps 1-3**: Follow normal chain to reference

- **Why**: Physical validation in same bath before jumping rounds### `config/config.yml`



### Recommended RangeDefine la estructura de sets, sensores raised, sensores descartados y rondas:



Always use `--range 3 39` to process complete Round 1. Sets outside this range may have incomplete connections.```yaml

sensors:

## Author  sets:

    3.0:

RTD Calibration Project        raised: [48203, 48479]

Universidad Politécnica de Madrid      discarded: [48060, 48176]

    # ... más sets
```

### `config/tree.yaml`

Define las conexiones entre rondas y sets:

```yaml
ronda_1:
  set_ids: [3.0, 4.0, ..., 39.0]
  next_ronda: ronda_2
ronda_2:
  set_ids: [49.0, 50.0, ..., 54.0]
  next_ronda: ronda_3
ronda_3:
  set_ids: [57.0]
  reference_sensor: 48484
```

## 📝 Notas Importantes

### Sensores Raised

Los sensores "raised" requieren calibración especial:
- **Paso 0**: Se calibran primero contra el OTRO sensor raised en su mismo set
- **Pasos 1-3**: Siguen la cadena normal hacia la referencia
- **Justificación**: Validación física en el mismo baño antes de saltar de ronda

### Rango Recomendado

**Usar --range 3 39** para procesar la Ronda 1 completa. Sets fuera de este rango pueden tener conexiones incompletas.


