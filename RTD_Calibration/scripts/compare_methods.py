#!/usr/bin/env python3
"""
Script para comparar resultados entre método antiguo (rtd-calib-simple) 
y método nuevo (rtd-calib-desde0).

Genera:
1. Estadísticas globales de diferencias
2. Top 20 sensores con mayores diferencias
3. Análisis detallado de pasos para sensores problemáticos
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Rutas
OLD_PATH = Path.home() / "Desktop/rtd-calib-simple/RTD_Calibration/data/results"
NEW_PATH = Path.home() / "Desktop/rtd-calib-desde0/RTD_Calibration/data/results"

# Cargar constantes finales
print("="*80)
print("COMPARACIÓN GLOBAL: Método Antiguo vs Nuevo")
print("="*80)

old_constants = pd.read_csv(OLD_PATH / "calibration_constants_media_ponderada.csv")
new_constants = pd.read_csv(NEW_PATH / "calibration_constants_tree.csv")

print(f"\n1. Archivos cargados:")
print(f"   Antiguo: {len(old_constants)} sensores")
print(f"   Nuevo: {len(new_constants)} sensores")

# Filtrar solo calculados (método antiguo no tiene columna Status, todos son calculados)
old_calc = old_constants.copy()
new_calc = new_constants[new_constants['Status'] == 'Calculado'].copy()

print(f"\n2. Sensores calculados:")
print(f"   Antiguo: {len(old_calc)} sensores")
print(f"   Nuevo: {len(new_calc)} sensores")

# Normalizar nombres de columnas
# Método antiguo (simple) usa 'N_Caminos', nuevo usa 'N_Paths'
old_calc = old_calc.rename(columns={'N_Caminos': 'N_Paths'})

# Merge por Sensor
merged = pd.merge(
    old_calc[['Sensor', 'Set', 'Constante_Calibracion_K', 'Error_K', 'N_Paths']],
    new_calc[['Sensor', 'Set', 'Constante_Calibracion_K', 'Error_K', 'N_Paths']],
    on=['Sensor', 'Set'],
    suffixes=('_old', '_new'),
    how='inner'
)

print(f"\n3. Sensores en común: {len(merged)}")

# Calcular diferencias
merged['Diff_K'] = merged['Constante_Calibracion_K_new'] - merged['Constante_Calibracion_K_old']
merged['Diff_mK'] = merged['Diff_K'] * 1000
merged['Abs_Diff_mK'] = merged['Diff_mK'].abs()
merged['Error_old_mK'] = merged['Error_K_old'] * 1000
merged['Error_new_mK'] = merged['Error_K_new'] * 1000
merged['Error_improvement_%'] = ((merged['Error_K_old'] - merged['Error_K_new']) / merged['Error_K_old']) * 100

# Estadísticas globales
print("\n" + "="*80)
print("ESTADÍSTICAS GLOBALES")
print("="*80)

print(f"\nDiferencia en constantes (NEW - OLD):")
print(f"  Media: {merged['Diff_mK'].mean():.3f} mK")
print(f"  Std: {merged['Diff_mK'].std():.3f} mK")
print(f"  Mediana: {merged['Diff_mK'].median():.3f} mK")
print(f"  Min: {merged['Diff_mK'].min():.3f} mK (Sensor {merged.loc[merged['Diff_mK'].idxmin(), 'Sensor']})")
print(f"  Max: {merged['Diff_mK'].max():.3f} mK (Sensor {merged.loc[merged['Diff_mK'].idxmax(), 'Sensor']})")

print(f"\nDiferencia absoluta:")
print(f"  Media: {merged['Abs_Diff_mK'].mean():.3f} mK")
print(f"  Mediana: {merged['Abs_Diff_mK'].median():.3f} mK")

print(f"\nErrores:")
print(f"  Antiguo - Media: {merged['Error_old_mK'].mean():.3f} mK")
print(f"  Nuevo - Media: {merged['Error_new_mK'].mean():.3f} mK")
print(f"  Mejora promedio: {merged['Error_improvement_%'].mean():.1f}%")

print(f"\nNúmero de caminos:")
print(f"  Antiguo - Media: {merged['N_Paths_old'].mean():.2f}")
print(f"  Nuevo - Media: {merged['N_Paths_new'].mean():.2f}")

# Distribución de diferencias
print(f"\nDistribución de diferencias absolutas:")
thresholds = [0.5, 1.0, 2.0, 5.0, 10.0, 50.0]
for thresh in thresholds:
    count = (merged['Abs_Diff_mK'] <= thresh).sum()
    pct = count / len(merged) * 100
    print(f"  ≤ {thresh:>5.1f} mK: {count:>4} sensores ({pct:>5.1f}%)")

# Top 20 mayores diferencias
print("\n" + "="*80)
print("TOP 20 SENSORES CON MAYORES DIFERENCIAS ABSOLUTAS")
print("="*80)

top20 = merged.nlargest(20, 'Abs_Diff_mK')[
    ['Sensor', 'Set', 'Constante_Calibracion_K_old', 'Constante_Calibracion_K_new', 
     'Diff_mK', 'Error_old_mK', 'Error_new_mK', 'N_Paths_old', 'N_Paths_new']
]

print(f"\n{'Sensor':<8} {'Set':<5} {'OLD (K)':<12} {'NEW (K)':<12} {'Diff (mK)':<10} "
      f"{'Err_OLD':<10} {'Err_NEW':<10} {'N_Old':<6} {'N_New':<6}")
print("-"*100)

for _, row in top20.iterrows():
    sensor = int(row['Sensor'])
    set_id = int(row['Set'])
    old_k = row['Constante_Calibracion_K_old']
    new_k = row['Constante_Calibracion_K_new']
    diff_mk = row['Diff_mK']
    err_old = row['Error_old_mK']
    err_new = row['Error_new_mK']
    n_old = int(row['N_Paths_old'])
    n_new = int(row['N_Paths_new'])
    
    print(f"{sensor:<8} {set_id:<5} {old_k:<12.6f} {new_k:<12.6f} {diff_mk:<10.3f} "
          f"{err_old:<10.3f} {err_new:<10.3f} {n_old:<6} {n_new:<6}")

# Guardar análisis completo
output_path = NEW_PATH / "comparison_analysis.csv"
merged_sorted = merged.sort_values('Abs_Diff_mK', ascending=False)
merged_sorted.to_csv(output_path, index=False)
print(f"\n✓ Análisis completo guardado en: {output_path}")

print("\n" + "="*80)
print("SENSORES PARA INVESTIGACIÓN DETALLADA")
print("="*80)

# Sensores con diferencias > 5 mK
problematic = merged[merged['Abs_Diff_mK'] > 5.0].sort_values('Abs_Diff_mK', ascending=False)
print(f"\nSensores con diferencias > 5 mK: {len(problematic)}")
if len(problematic) > 0:
    print("\nTop 10 para investigar:")
    for idx, (_, row) in enumerate(problematic.head(10).iterrows(), 1):
        sensor = int(row['Sensor'])
        set_id = int(row['Set'])
        diff = row['Diff_mK']
        print(f"  {idx}. Sensor {sensor} (Set {set_id}): {diff:+.3f} mK")
else:
    print("\n✓ Todos los sensores tienen diferencias < 5 mK")

print("\n" + "="*80)
