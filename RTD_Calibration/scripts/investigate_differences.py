#!/usr/bin/env python3
"""
Investigar causas de diferencias grandes en sensores específicos.
Enfoque: Set 14 (9 sensores problemáticos) y Set 9 (varios sensores).
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Rutas
OLD_PATH = Path.home() / "Desktop/rtd-calib-simple/RTD_Calibration/data/results"
NEW_PATH = Path.home() / "Desktop/rtd-calib-desde0/RTD_Calibration/data/results"

# Cargar detalles de pasos
print("="*80)
print("INVESTIGACIÓN DETALLADA: Sensores con grandes diferencias")
print("="*80)

old_details = pd.read_csv(OLD_PATH / "calibration_pasos_intermedios.csv")
new_details = pd.read_csv(NEW_PATH / "calibration_details_tree.csv")

# Sensores a investigar
problematic_sensors = [
    (48956, 14, "Diferencia: -405.5 mK"),
    (48912, 14, "Diferencia: -286.0 mK"),
    (48857, 9, "Diferencia: +283.9 mK"),
    (48863, 9, "Diferencia: -122.2 mK"),
]

for sensor_id, set_id, description in problematic_sensors:
    print(f"\n{'='*80}")
    print(f"SENSOR {sensor_id} (Set {set_id}): {description}")
    print(f"{'='*80}")
    
    # Método antiguo
    old_sensor = old_details[old_details['Sensor'] == sensor_id]
    if len(old_sensor) == 0:
        print(f"⚠️  Sensor {sensor_id} no encontrado en método antiguo")
        continue
    
    old_row = old_sensor.iloc[0]
    
    print(f"\n--- MÉTODO ANTIGUO (rtd-calib-simple) ---")
    print(f"Constante final: {old_row['Constante_Calibracion_K']:.6f} K")
    print(f"Error total: {old_row['Error_Total_K']*1000:.3f} mK")
    print(f"\nCamino único:")
    print(f"  Paso 1: {old_row['Paso1_Sensor_from']:.0f} → {old_row['Paso1_Sensor_to']:.0f} (Set {old_row['Paso1_Set']:.0f})")
    print(f"          Offset: {old_row['Paso1_Offset_K']:.6f} K ± {old_row['Paso1_Error_K']*1000:.3f} mK")
    print(f"  Paso 2: {old_row['Paso2_Sensor_from']:.0f} → {old_row['Paso2_Sensor_to']:.0f} (Set {old_row['Paso2_Set']:.0f})")
    print(f"          Offset: {old_row['Paso2_Offset_K']:.6f} K ± {old_row['Paso2_Error_K']*1000:.3f} mK")
    print(f"  Paso 3: {old_row['Paso3_Sensor_from']:.0f} → {old_row['Paso3_Sensor_to']:.0f} (Set {old_row['Paso3_Set']:.0f})")
    print(f"          Offset: {old_row['Paso3_Offset_K']:.6f} K ± {old_row['Paso3_Error_K']*1000:.3f} mK")
    
    if 'Paso0_Sensor_from' in old_row and pd.notna(old_row['Paso0_Sensor_from']):
        print(f"  Paso 0: {old_row['Paso0_Sensor_from']:.0f} → {old_row['Paso0_Sensor_to']:.0f} (Set {old_row['Paso0_Set']:.0f})")
        print(f"          Offset: {old_row['Paso0_Offset_K']:.6f} K ± {old_row['Paso0_Error_K']*1000:.3f} mK")
    
    # Método nuevo
    new_sensor = new_details[
        (new_details['Sensor'] == sensor_id) & 
        (new_details['Set'] == set_id)
    ]
    
    if len(new_sensor) == 0:
        print(f"\n⚠️  Sensor {sensor_id} no encontrado en método nuevo")
        continue
    
    # Path promedio (Path_Number = 0)
    new_avg = new_sensor[new_sensor['Path_Number'] == 0]
    if len(new_avg) > 0:
        avg_row = new_avg.iloc[0]
        print(f"\n--- MÉTODO NUEVO (rtd-calib-desde0) ---")
        print(f"Constante final (media ponderada): {avg_row['Total_Offset_K']:.6f} K")
        print(f"Error total: {avg_row['Total_Error_K']*1000:.3f} mK")
    
    # Caminos individuales
    new_paths = new_sensor[new_sensor['Path_Number'] > 0].sort_values('Path_Number')
    print(f"\nCaminos individuales ({len(new_paths)} total):")
    
    for idx, path_row in new_paths.iterrows():
        path_num = int(path_row['Path_Number'])
        print(f"\n  Path {path_num}:")
        
        # Manejar posibles strings como "PROMEDIO"
        p1_from = path_row['Paso1_From']
        p1_to = path_row['Paso1_To']
        p1_set = path_row['Paso1_Set']
        
        if isinstance(p1_from, (int, float)) and not pd.isna(p1_from):
            print(f"    Paso 1: {int(p1_from)} → {p1_to} (Set {p1_set})")
        else:
            print(f"    Paso 1: {p1_from} → {p1_to} (Set {p1_set})")
        
        if pd.notna(path_row['Paso1_Offset_K']):
            print(f"            Offset: {path_row['Paso1_Offset_K']:.6f} K ± {path_row['Paso1_Error_K']*1000:.3f} mK")
        
        p2_from = path_row['Paso2_From']
        p2_to = path_row['Paso2_To']
        p2_set = path_row['Paso2_Set']
        
        if isinstance(p2_from, (int, float)) and not pd.isna(p2_from):
            print(f"    Paso 2: {int(p2_from)} → {p2_to} (Set {p2_set})")
        else:
            print(f"    Paso 2: {p2_from} → {p2_to} (Set {p2_set})")
        
        if pd.notna(path_row['Paso2_Offset_K']):
            print(f"            Offset: {path_row['Paso2_Offset_K']:.6f} K ± {path_row['Paso2_Error_K']*1000:.3f} mK")
        
        p3_from = path_row['Paso3_From']
        p3_to = path_row['Paso3_To']
        p3_set = path_row['Paso3_Set']
        
        if isinstance(p3_from, (int, float)) and not pd.isna(p3_from):
            print(f"    Paso 3: {int(p3_from)} → {p3_to} (Set {p3_set})")
        else:
            print(f"    Paso 3: {p3_from} → {p3_to} (Set {p3_set})")
        
        if pd.notna(path_row['Paso3_Offset_K']):
            print(f"            Offset: {path_row['Paso3_Offset_K']:.6f} K ± {path_row['Paso3_Error_K']*1000:.3f} mK")
        
        print(f"    TOTAL: {path_row['Total_Offset_K']:.6f} K ± {path_row['Total_Error_K']*1000:.3f} mK")
    
    # Comparación
    print(f"\n--- COMPARACIÓN ---")
    old_const = old_row['Constante_Calibracion_K']
    if len(new_avg) > 0:
        new_const = avg_row['Total_Offset_K']
        diff = (new_const - old_const) * 1000
        print(f"Diferencia (NEW - OLD): {diff:+.3f} mK")
        
        # Análisis de qué paso difiere más
        print(f"\nAnálisis de pasos:")
        
        # Comparar Paso 1
        old_p1 = old_row['Paso1_Offset_K']
        # Tomar el primer path del nuevo método para comparar estructura
        if len(new_paths) > 0:
            first_path = new_paths.iloc[0]
            new_p1 = first_path['Paso1_Offset_K']
            new_p2 = first_path['Paso2_Offset_K']
            new_p3 = first_path['Paso3_Offset_K']
            
            print(f"  Paso 1: OLD={old_p1:.6f} vs NEW={new_p1:.6f} → Diff={(new_p1-old_p1)*1000:+.3f} mK")
            print(f"  Paso 2: OLD={old_row['Paso2_Offset_K']:.6f} vs NEW={new_p2:.6f} → Diff={(new_p2-old_row['Paso2_Offset_K'])*1000:+.3f} mK")
            print(f"  Paso 3: OLD={old_row['Paso3_Offset_K']:.6f} vs NEW={new_p3:.6f} → Diff={(new_p3-old_row['Paso3_Offset_K'])*1000:+.3f} mK")

print("\n" + "="*80)
print("FIN DEL ANÁLISIS")
print("="*80)
