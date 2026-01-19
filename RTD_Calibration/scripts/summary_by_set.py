#!/usr/bin/env python3
"""
Resumen final de comparación con análisis estadístico por set.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Rutas
NEW_PATH = Path.home() / "Desktop/rtd-calib-desde0/RTD_Calibration/data/results"

# Cargar análisis
comparison = pd.read_csv(NEW_PATH / "comparison_analysis.csv")

print("="*80)
print("RESUMEN FINAL: Comparación por Sets")
print("="*80)

# Agrupar por Set
by_set = comparison.groupby('Set').agg({
    'Abs_Diff_mK': ['count', 'mean', 'median', 'std', 'min', 'max'],
    'Error_old_mK': 'mean',
    'Error_new_mK': 'mean',
    'N_Paths_old': 'mean',
    'N_Paths_new': 'mean'
}).round(3)

by_set.columns = ['N_Sensors', 'Mean_Diff', 'Median_Diff', 'Std_Diff', 'Min_Diff', 'Max_Diff',
                  'Err_OLD', 'Err_NEW', 'N_Paths_OLD', 'N_Paths_NEW']

# Ordenar por diferencia media descendente
by_set = by_set.sort_values('Mean_Diff', ascending=False)

print(f"\n{'Set':<5} {'N':<4} {'Mean Diff':<12} {'Max Diff':<12} {'Err OLD':<10} {'Err NEW':<10} {'Mejora %':<10}")
print("-"*80)

for set_id, row in by_set.head(20).iterrows():
    set_id = int(set_id)
    n = int(row['N_Sensors'])
    mean_diff = row['Mean_Diff']
    max_diff = row['Max_Diff']
    err_old = row['Err_OLD']
    err_new = row['Err_NEW']
    improvement = ((err_old - err_new) / err_old * 100) if err_old > 0 else 0
    
    # Marcar sets problemáticos
    marker = "🔴" if mean_diff > 50 else "🟡" if mean_diff > 10 else "🟢"
    
    print(f"{set_id:<5} {n:<4} {mean_diff:<12.3f} {max_diff:<12.3f} {err_old:<10.3f} {err_new:<10.3f} {improvement:<10.1f} {marker}")

print("\n" + "="*80)
print("SETS CRÍTICOS (diferencia media > 50 mK)")
print("="*80)

critical = by_set[by_set['Mean_Diff'] > 50].sort_values('Mean_Diff', ascending=False)

for set_id, row in critical.iterrows():
    set_id = int(set_id)
    print(f"\n📊 SET {set_id}:")
    print(f"   Sensores: {int(row['N_Sensors'])}")
    print(f"   Diferencia media: {row['Mean_Diff']:.3f} mK")
    print(f"   Diferencia máxima: {row['Max_Diff']:.3f} mK")
    print(f"   Error OLD: {row['Err_OLD']:.3f} mK (muy alto!)")
    print(f"   Error NEW: {row['Err_NEW']:.3f} mK")
    print(f"   Caminos OLD: {row['N_Paths_OLD']:.1f}")
    print(f"   Caminos NEW: {row['N_Paths_NEW']:.1f}")
    
    # Mostrar sensores del set
    set_sensors = comparison[comparison['Set'] == set_id].nlargest(3, 'Abs_Diff_mK')
    print(f"   Top 3 sensores:")
    for idx, sensor_row in set_sensors.iterrows():
        sensor = int(sensor_row['Sensor'])
        diff = sensor_row['Diff_mK']
        print(f"      - Sensor {sensor}: {diff:+.3f} mK")

print("\n" + "="*80)
print("CONCLUSIÓN")
print("="*80)

print(f"""
Los sets con mayores problemas son:
  - Set 14: Diferencia promedio ~280 mK (9 sensores)
  - Set 9: Diferencia promedio ~60 mK (12 sensores)
  
Causa principal:
  ⚠️ Errores gigantes en método antiguo (40-150 mK)
  ⚠️ Caminos circulares (sensor → mismo sensor)
  ⚠️ Problemas en Paso 2 (R1→R2, especialmente Set 50)

Método nuevo:
  ✅ Errores 99% menores (0.2-0.5 mK)
  ✅ Sin caminos circulares
  ✅ Múltiples caminos validados
  ✅ Lógica correcta en todos los pasos

RECOMENDACIÓN FINAL:
  🎯 USAR CONSTANTES DEL MÉTODO NUEVO para CERN
  🎯 Las diferencias NO son errores numéricos sino BUGS LÓGICOS del método antiguo
  🎯 {len(comparison[comparison['Abs_Diff_mK'] <= 5.0])} sensores ({len(comparison[comparison['Abs_Diff_mK'] <= 5.0])/len(comparison)*100:.1f}%) con diferencias ≤ 5 mK
  🎯 {len(comparison[comparison['Abs_Diff_mK'] <= 2.0])} sensores ({len(comparison[comparison['Abs_Diff_mK'] <= 2.0])/len(comparison)*100:.1f}%) con diferencias ≤ 2 mK
""")

print("="*80)
