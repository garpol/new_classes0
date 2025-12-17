# RTD Calibration Tree Documentation

Este directorio contiene la configuración del **árbol de calibración jerárquico** para el proyecto RTD.

## 📁 Archivos

- **`tree.yaml`**: Estructura completa del árbol de calibración
- **`sensors.yaml`**: Configuración de sensores descartados y raised por set (si existe)
- **`config.yaml`**: Configuración general del proyecto (si existe)

---

## 🌳 ¿Qué es el Tree de Calibración?

El **tree** es una estructura jerárquica que conecta sensores a través de múltiples rondas de calibración. Cada sensor puede ser:

- **Calibrado**: Sensor medido en una ronda específica
- **Raised** (elevado): Sensor seleccionado para participar en la siguiente ronda de calibración
- **Reference**: Sensor usado como referencia en múltiples sets

### Estructura jerárquica

```
Ronda 2                    Ronda 3
───────────                ─────────
Set 49 (2 raised) ─┐
Set 50 (2 raised) ─┤
Set 51 (2 raised) ─┼─────→ Set 57 (12 sensores)
Set 52 (2 raised) ─┤
Set 53 (2 raised) ─┤
Set 54 (2 raised) ─┘

Set 55 (6 raised) ─┬─────→ Future Set (12 sensores)
Set 56 (6 raised) ─┘
```

---

## 📋 Reglas del Tree

### 1. **Sets de 3ª Ronda**
- **Siempre contienen 12 sensores**
- Provienen de sensores **raised** de sets de 2ª ronda
- Cada set padre aporta un número fijo de sensores raised

### 2. **Sensores Raised**
- Son sensores seleccionados por su **buen desempeño** en una ronda anterior
- Se eligen basándose en criterios de **repeatability** y **offset**
- Típicamente: 2-6 sensores raised por set padre

### 3. **Validación**
- Total de sensores en set de ronda 3 = `Σ(sensores_per_parent × num_parents)`
- Ejemplo Set 57: `6 parents × 2 sensores = 12 sensores ✓`
- Ejemplo Future Set: `2 parents × 6 sensores = 12 sensores ✓`

---

## 🔍 Contenido de `tree.yaml`

### Estructura principal

```yaml
sets:
  57:                              # ID del set de 3ª ronda
    round: 3                       # Ronda de calibración
    status: processed              # Estado: processed, pending, future
    parents: [49, 50, 51, 52, 53, 54]  # Sets padres (2ª ronda)
    sensors_per_parent: 2          # Sensores raised por parent
    total_sensors: 12              # Total esperado
    composition:                   # Detalle de sensores por parent
      from_set_49: []              # IDs de sensores del Set 49
      from_set_50: []              # IDs de sensores del Set 50
      # ... etc
```

### Metadata del árbol

```yaml
tree_metadata:
  project: RTD_Calibration_VGP
  version: "1.0"
  date_created: "2025-10-23"
  author: "VGP Lab"
```

### Reglas de validación

```yaml
validation_rules:
  round_3_sensor_count: 12         # Sets de ronda 3 deben tener 12 sensores
  min_sensors_per_parent: 1        # Mínimo de sensores por parent
  max_sensors_per_parent: 6        # Máximo de sensores por parent
```

---

## 💻 Uso en Python

### Cargar el árbol

```python
import yaml

with open('RTD_Calibration_VGP/config/tree.yaml', 'r') as f:
    tree_config = yaml.safe_load(f)

# Acceder a información de un set
set_57_info = tree_config['sets']['57']
print(f"Set 57 tiene {set_57_info['total_sensors']} sensores")
print(f"Parents: {set_57_info['parents']}")
```

### Validar el árbol (futuro)

```python
from RTD_Calibration_VGP.src.calibration_network import validate_tree

# Validar que la estructura cumple las reglas
ok, issues = validate_tree(tree_config, logfile_df)
if not ok:
    print("⚠️ Problemas detectados:")
    for issue in issues:
        print(f"  - {issue}")
```

### Visualizar el árbol (futuro)

```python
from RTD_Calibration_VGP.src.calibration_network import visualize_tree

# Generar gráfico del árbol
visualize_tree(tree_config, highlight=57, output='tree_diagram.png')
```

---

## 📊 Estado Actual

### Sets de 3ª Ronda

| Set ID | Status | Parents | Sensores/Parent | Total |
|--------|--------|---------|-----------------|-------|
| 57 | ✅ Procesado | 49-54 (6 sets) | 2 | 12 |
| Future | ⏳ Pendiente | 55-56 (2 sets) | 6 | 12 |

### Sets de 2ª Ronda (Contributors)

| Set ID | Status | Contribuye a | Sensores Raised |
|--------|--------|--------------|-----------------|
| 49-54 | ✅ Procesado | Set 57 | 2 cada uno |
| 55 | ✅ Procesado | Future Set | 6 |
| 56 | ⏳ Pendiente | Future Set | 6 |

---

## 🔄 Flujo de Trabajo

### Para añadir un nuevo set de 3ª ronda:

1. **Identificar sets padres** (2ª ronda) que aportarán sensores
2. **Seleccionar sensores raised** de cada set padre
3. **Actualizar `tree.yaml`**:
   ```yaml
   new_set_id:
     round: 3
     status: future
     parents: [...]
     sensors_per_parent: X
     total_sensors: 12
     composition:
       from_set_XX: []
   ```
4. **Validar** que `total_sensors = len(parents) × sensors_per_parent = 12`
5. **Procesar el set** usando los notebooks de análisis
6. **Actualizar status** a `processed` una vez completado

### Para actualizar composición de sensores:

1. **Leer el LogFile.csv** para obtener IDs de sensores raised
2. **Actualizar la sección `composition`** en `tree.yaml`:
   ```yaml
   composition:
     from_set_49: [48484, 48747]  # Ejemplo de IDs
     from_set_50: [48869, 48956]
     # ... etc
   ```
3. **Validar** que la suma de sensores = 12

---

## ⚙️ Herramientas Futuras

### `calibration_network.py`

Funciones planeadas para trabajar con el tree:

- `load_tree_config(path)`: Carga y valida el YAML
- `validate_tree(tree_config, logfile_df)`: Verifica reglas
- `get_parents(set_id)`: Retorna sets padres de un set
- `get_children(set_id)`: Retorna sets hijos (siguiente ronda)
- `get_composition(set_id, logfile_df)`: Extrae IDs de sensores reales
- `visualize_tree(tree_config, highlight)`: Genera gráfico del árbol
- `export_tree_report(tree_config, output)`: Crea CSV/Markdown con estructura

---

## 📝 Notas Importantes

1. **Siempre mantener `total_sensors = 12`** para sets de ronda 3
2. **Actualizar `status`** cuando se procesa un set (`pending` → `processed`)
3. **Documentar cambios** en la sección `notes` de cada set
4. **Sincronizar** con `LogFile.csv` para obtener IDs reales de sensores
5. **Validar** antes de ejecutar análisis masivos

---

## 🐛 Troubleshooting

### Error: "Total sensors ≠ 12"
- Verificar que `len(parents) × sensors_per_parent = 12`
- Revisar si algún parent no tiene suficientes sensores raised

### Error: "Parent set not found"
- Asegurarse de que todos los sets padres existen en `LogFile.csv`
- Verificar que los IDs de sets son correctos

### Error: "Missing sensor IDs in composition"
- Completar la sección `composition` con IDs reales del LogFile
- Usar scripts de análisis para extraer sensores raised automáticamente

---

## 📚 Referencias

- **LogFile.csv**: Contiene información completa de todos los runs y sensors
- **Notebooks de análisis**: `SET_BUENO.ipynb`, `SET_BUENO_4runs.ipynb`
- **Código fuente**: `src/set.py`, `src/calibration_network.py`

---

**Última actualización**: 23 de octubre de 2025  
**Mantenido por**: VGP Lab
