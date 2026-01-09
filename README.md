# RTD Calibration System

Sistema de calibración multi-ronda para sensores RTD (Resistance Temperature Detectors) mediante análisis de múltiples caminos y media ponderada.

## 📋 Descripción

Este proyecto implementa un sistema completo de calibración para sensores de temperatura RTD organizados en sets y rondas jerárquicas. El sistema:

- **Procesa datos de múltiples rondas de calibración** (R1 → R2 → R3)
- **Calcula constantes de calibración** usando media ponderada (1/error²)
- **Explora todos los caminos válidos** entre sensores y referencia
- **Maneja sensores "raised"** con lógica especial de calibración
- **Genera CSVs listos para uso** con constantes y análisis detallado

## 🏗️ Estructura del Proyecto

```
RTD_Calibration/
├── config/
│   ├── config.yml              # Configuración principal (sets, sensores, rondas)
│   ├── reference_sensors.yaml  # Sensores de referencia por ronda
│   ├── sensors.yaml            # Listado completo de sensores
│   └── tree.yaml              # Estructura del árbol de calibración
├── data/
│   ├── LogFile.csv            # Registro de archivos de temperatura
│   ├── temperature_files/     # Datos RAW de temperatura
│   └── results/               # Resultados (CSVs generados)
├── src/
│   ├── set.py                 # Procesamiento de sets individuales
│   ├── tree.py                # Construcción del árbol y cálculo multi-camino
│   ├── run.py                 # Procesamiento de runs individuales
│   ├── logfile.py             # Gestión del LogFile
│   └── calibration_network.py # Red de calibración (deprecado)
├── notebooks/
│   ├── SET.ipynb              # Análisis de sets individuales
│   ├── RUN.ipynb              # Análisis de runs
│   └── TREE.ipynb             # Análisis completo del árbol (PRINCIPAL)
└── main.py                    # Script principal para producción
```

## 🚀 Uso Rápido

### Ejecución del Script Principal

El script `main.py` procesa todos los sets y genera las constantes de calibración:

```bash
# Procesar sets por defecto (3-39, Ronda 1 completa)
python main.py

# Procesar rango específico
python main.py --range 3 39

# Procesar sets específicos
python main.py --sets 3 4 5 49 57
```

### Salidas Generadas

El script genera dos archivos CSV en `data/results/`:

1. **`calibration_analisis_multicamino.csv`**: Análisis completo con 3 estrategias
   - Primer camino
   - Camino de mínimo error
   - **Media ponderada (RECOMENDADO)**

2. **`calibration_constants_media_ponderada.csv`**: CSV simplificado para uso final
   - Columnas: Sensor, Set, Constante_Calibracion_K, Error_K, N_Caminos

### Análisis Interactivo con Notebooks

Para exploración y visualización, usar los notebooks en orden:

1. **`SET.ipynb`**: Analizar un set individual
2. **`TREE.ipynb`**: Análisis completo multi-ronda (PRINCIPAL)

## 📊 Metodología

### Estructura de Calibración

El sistema usa una estructura jerárquica de tres rondas:

- **Ronda 1 (R1)**: Sets 3-39 (sensores a calibrar)
- **Ronda 2 (R2)**: Sets 49-54 (puentes intermedios)
- **Ronda 3 (R3)**: Set 57 (referencia final, sensor 48484)

### Tipos de Sensores

- **Sensores regulares**: 8-9 por set, calibrados normalmente
- **Sensores "raised"**: 2 por set, calibrados primero entre sí (Paso 0) y luego hacia la cadena
- **Sensores descartados**: Marcados en config, no se calibran

### Algoritmo de Cálculo

1. **Exploración de caminos**: El sistema encuentra TODOS los caminos válidos desde cada sensor hasta la referencia
2. **Cálculo por camino**: Cada camino acumula offsets y propaga errores (RSS)
3. **Media ponderada**: Se calcula la media ponderada usando `1/(error² + ε)` como peso
4. **Sensores raised**: Tienen 2 caminos (via otro raised → 2 bridges R2→R3)
5. **Sensores regulares**: Tienen 4 caminos (2 raised R1 × 2 bridges R2→R3)

### Propagación de Errores

```
Error_total = sqrt(error_paso1² + error_paso2² + ... + error_pasoN²)
```

## 📦 Requisitos

### Python 3.12+

```bash
pip install pandas numpy matplotlib pyyaml
```

### Estructura de Datos

Los archivos de temperatura deben seguir el formato:
- Columnas: `fecha`, `hora`, sensor IDs (48060, 48176, etc.)
- Valores: Resistencias en Ohms
- Ubicación: `data/temperature_files/RTD_Calibs/CalSetN_X/`

## 📈 Resultados Típicos

Para el rango 3-39 (Ronda 1 completa):

- **Sensores calculados**: ~376 (304 regulares + 72 raised)
- **Sensores descartados**: ~56
- **Error medio global**: ~100-120 mK
- **Error sensores raised**: ~25 mK (mejor precisión)
- **Caminos promedio**: 2 (raised) o 4 (regulares)

## 🔧 Configuración

### `config/config.yml`

Define la estructura de sets, sensores raised, sensores descartados y rondas:

```yaml
sensors:
  sets:
    3.0:
      raised: [48203, 48479]
      discarded: [48060, 48176]
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

**Use siempre --range 3 39** para procesar la Ronda 1 completa. Sets fuera de este rango pueden tener conexiones incompletas.

## 🧪 Testing

Los notebooks incluyen validaciones integradas:
- Verificación de integridad de CSVs
- Comparación de estrategias (primer camino vs media ponderada)
- Histogramas de distribución de errores

## 👨‍🔬 Autor

Proyecto de calibración RTD - TFG/TFM
Universidad Politécnica de Madrid

## 📄 Licencia

Este proyecto es material académico para evaluación.
