"""
EJEMPLO CONCRETO DE USO - Nueva Arquitectura OOP
=================================================

Este archivo muestra paso a paso cómo usar el nuevo sistema.
"""

# =============================================================================
# PASO 1: SETUP - Cargar configuración y logfile
# =============================================================================

from RTD_Calibration.src.tree import Tree
from RTD_Calibration.src.utils import load_config
import pandas as pd

# Cargar config.yml
config = load_config()

# Cargar logfile
logfile = pd.read_csv("data/LogFile.csv")

print("✓ Configuración cargada")


# =============================================================================
# PASO 2: CREAR ESTRUCTURA VACÍA - Solo desde config.yml
# =============================================================================

# Crear árbol completo (estructura vacía)
tree = Tree(config, logfile)

# Output esperado:
# ✓ Estructura creada: 60 CalibrationSets
# Cada set tiene 12 sensores creados pero sin constantes
# No hay runs cargados todavía

print(tree)
# Tree(sets=60, total_sensors=720)


# =============================================================================
# PASO 3: EXPLORAR ESTRUCTURA - Antes de cargar datos
# =============================================================================

# Ver un set específico
set_3 = tree.get_set(3)
print(set_3)
# CalibrationSet(set=3, sensors=12, runs=0)

# Ver sensores del set
print(f"Sensores en Set 3: {[s.id for s in set_3.sensors]}")
# [48060, 48061, 48062, 48063, 48202, 48203, 48204, 48205, 48476, 48477, 48478, 48479]

# Ver referencias
print(f"Referencias: {[s.id for s in set_3.reference_sensors]}")
# [48176, 48177]

# Ver metadata
print(f"Round: {set_3.round}")
print(f"Parent set: {set_3.parent_set}")
print(f"Descartados: {set_3.discarded_sensors}")
print(f"Raised: {set_3.raised_sensors}")


# =============================================================================
# PASO 4: CARGAR RUNS PARA UN SET ESPECÍFICO
# =============================================================================

# Lista de archivos del Set 3
filenames_set_3 = [
    "20220201_ln2_r48176_r48177_487178-48189_1",
    "20220201_ln2_r48176_r48177_487178-48189_2",
    "20220201_ln2_r48176_r48177_487178-48189_3",
    "20220201_ln2_r48176_r48177_487178-48189_4",
]

# Cargar runs
tree.load_runs_for_set(set_number=3, filenames=filenames_set_3)

# Output esperado:
# Cargando: .../20220201_ln2_r48176_r48177_487178-48189_1.txt
#   Datos cargados: 2400 registros
#   Set 3 | ✓ VALID | Sensores: [48178, 48179, 48180]...48177
#   Offsets calculados: 14 sensores respecto a 48176
# ... (para cada archivo)
# ✓ 4 runs cargados para Set 3

# Verificar que se cargaron
set_3 = tree.get_set(3)
print(f"Set 3 ahora tiene {len(set_3.runs)} runs")
# Set 3 ahora tiene 4 runs


# =============================================================================
# PASO 5: CALIBRAR UN SET
# =============================================================================

# Calibrar Set 3 usando todos los runs cargados
tree.calibrate_set(3)

# Output esperado:
# === Calibrando Set 3 ===
# Construyendo caminos entre sensores...
#   Camino directo: 48176 -> 48060
#   Camino indirecto: 48176 -> 48177 -> 48060
#   ...
# Calculando media ponderada...
# ✓ Constantes calculadas para 12 sensores

# Ver resultados
set_3 = tree.get_set(3)
for sensor in set_3.sensors:
    if not set_3.is_sensor_discarded(sensor.id):
        const = sensor.calibration_constant
        error = set_3.calibration_errors.get(sensor.id, 0)
        print(f"Sensor {sensor.id}: {const:.6f} ± {error:.6f}")


# =============================================================================
# PASO 6: VER SENSOR ESPECÍFICO
# =============================================================================

# Buscar un sensor
sensor_48060 = set_3.get_sensor(48060)
print(sensor_48060)
# Sensor(id=48060, cal=1.002345)

# Ver su constante
print(f"Constante: {sensor_48060.calibration_constant}")

# Ver sus caminos
paths = set_3.paths.get(48060, [])
print(f"Caminos usados: {paths}")
# ['48176->48060', '48176->48177->48060']


# =============================================================================
# PASO 7: CARGAR Y CALIBRAR MÚLTIPLES SETS
# =============================================================================

# Diccionario de sets a procesar
sets_to_process = {
    3: ["20220201_ln2_r48176_r48177_487178-48189_1",
        "20220201_ln2_r48176_r48177_487178-48189_2"],
    4: ["20220202_ln2_..._1",
        "20220202_ln2_..._2"],
    5: ["20220203_ln2_..._1",
        "20220203_ln2_..._2"],
}

# Cargar todos
for set_num, filenames in sets_to_process.items():
    tree.load_runs_for_set(set_num, filenames)

# Calibrar todos
tree.calibrate_all()

# Output esperado:
# === Calibrando Set 3 ===
# ✓ Constantes calculadas
# === Calibrando Set 4 ===
# ✓ Constantes calculadas
# === Calibrando Set 5 ===
# ✓ Constantes calculadas


# =============================================================================
# PASO 8: EXPORTAR RESULTADOS
# =============================================================================

# Obtener todos los sensores con constantes
all_sensors = tree.get_all_sensors()

# Crear DataFrame
import pandas as pd

results = []
for sensor in all_sensors:
    if sensor.calibration_constant is not None:
        results.append({
            'sensor_id': sensor.id,
            'calibration_constant': sensor.calibration_constant,
        })

df_results = pd.DataFrame(results)
print(df_results.head())

# Exportar
df_results.to_csv('calibration_results.csv', index=False)


# =============================================================================
# PASO 9: ANÁLISIS AVANZADO - Filtrar runs por validez
# =============================================================================

# Ver solo runs válidos de un set
set_3 = tree.get_set(3)
valid_runs = [r for r in set_3.runs if r.is_valid]
invalid_runs = [r for r in set_3.runs if not r.is_valid]

print(f"Set 3:")
print(f"  Runs válidos: {len(valid_runs)}")
print(f"  Runs inválidos: {len(invalid_runs)}")

# Re-calibrar usando solo runs válidos
set_3.runs = valid_runs  # Filtrar
tree.calibrate_set(3)  # Re-calibrar


# =============================================================================
# PASO 10: NAVEGACIÓN POR SETS CONECTADOS
# =============================================================================

# Ver sets conectados (parent_set)
set_3 = tree.get_set(3)
if set_3.parent_set:
    parent = tree.get_set(set_3.parent_set)
    print(f"Set 3 es hijo de Set {parent.set_number}")
    
    # Ver sensores comunes (referencias)
    refs_3 = {s.id for s in set_3.reference_sensors}
    refs_parent = {s.id for s in parent.reference_sensors}
    common = refs_3 & refs_parent
    print(f"Sensores comunes: {common}")


# =============================================================================
# PASO 11: COMPARAR RUNS DENTRO DE UN SET
# =============================================================================

import matplotlib.pyplot as plt

set_3 = tree.get_set(3)
test_sensor = 48061

fig, ax = plt.subplots(figsize=(12, 6))

for i, run in enumerate(set_3.runs):
    if test_sensor in run.offsets:
        offset = run.offsets[test_sensor]
        color = 'green' if run.is_valid else 'red'
        ax.scatter(i, offset, s=200, color=color, alpha=0.7, 
                  edgecolor='black', linewidth=2)
        ax.text(i, offset, run.filename[:15], rotation=45, ha='right')

ax.set_xlabel('Run Index')
ax.set_ylabel(f'Offset sensor {test_sensor} (K)')
ax.set_title(f'Comparación de offsets - Set {set_3.set_number}')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()


# =============================================================================
# RESUMEN DE USO
# =============================================================================

"""
WORKFLOW TÍPICO:
===============

1. Tree(config, logfile)              → Crear estructura vacía
2. tree.load_runs_for_set(3, files)   → Cargar datos
3. tree.calibrate_set(3)              → Calibrar
4. set_3.sensors[0].calibration_constant → Usar resultados

VENTAJAS:
=========

✓ Estructura clara y jerárquica
✓ Fácil añadir/quitar runs
✓ Fácil re-calibrar
✓ Fácil filtrar por validez
✓ Fácil explorar resultados
✓ Código limpio y simple
"""
