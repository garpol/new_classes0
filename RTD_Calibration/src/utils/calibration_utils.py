"""
Utilidades para cálculo de constantes de calibración usando Tree.

Funciones principales:
- find_all_paths(): Encuentra todos los caminos posibles R1 → R3
- weighted_average_paths(): Media ponderada de múltiples caminos
- calibrate_tree(): Función principal que calcula constantes finales
"""

from typing import List, Tuple, Optional
import pandas as pd
import numpy as np
from pathlib import Path
import sys

parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from tree_entry import TreeEntry
from tree import Tree
from utils.math_utils import propagate_error


def find_all_paths_to_reference(
    sensor: 'Sensor',
    start_entry: TreeEntry,
    tree: Tree
) -> List[Tuple[float, float, List[Tuple[TreeEntry, 'Sensor']]]]:
    """
    Encuentra TODOS los caminos desde un sensor hasta la referencia.
    
    Args:
        sensor: Objeto Sensor de origen (típicamente en R1)
        start_entry: TreeEntry donde está el sensor
        tree: Tree completo
    
    Returns:
        Lista de tuplas (offset_total, error_total, path_details)
    """
    paths = []
    root = tree.get_root()
    
    if root is None:
        return paths
    
    # Si está descartado, no calcular
    if start_entry.is_sensor_discarded(sensor):
        return paths
    
    # Obtener raised disponibles para este sensor
    available_raised = start_entry.get_raised_for_sensor(sensor)
    
    if not available_raised:
        return paths
    
    # Para cada raised en R1, buscar caminos hacia R3
    for raised_r1 in available_raised:
        # Paso 1: Calcular offset del sensor hasta el raised de R1
        # Esto nos da cuánto difiere el sensor respecto al raised
        offset_step1 = start_entry.get_offset_to_raised(sensor, raised_r1)
        
        if offset_step1 is None:
            continue
        
        offset_1, error_1 = offset_step1
        
        # Paso 2: Buscar en qué entry de R2 (Ronda 2) aparece el raised_r1
        # El raised de R1 debe estar también en algún set de R2 para poder subir
        r2_entries = tree.get_entries_by_round(2)
        
        for entry_r2 in r2_entries:
            # Verificar si este entry de R2 contiene el raised_r1
            if raised_r1 not in entry_r2.calibset.sensors:
                continue
            
            # Paso 3: Desde raised_r1 (ahora en R2), subir a un raised de R2
            available_raised_r2 = entry_r2.get_raised_for_sensor(raised_r1)
            
            if not available_raised_r2:
                continue
            
            for raised_r2 in available_raised_r2:
                # Calcular offset de raised_r1 hasta raised_r2 (segundo salto)
                offset_step2 = entry_r2.get_offset_to_raised(raised_r1, raised_r2)
                
                if offset_step2 is None:
                    continue
                
                offset_2, error_2 = offset_step2
                
                # Paso 4: Desde raised_r2, subir hasta la referencia absoluta en R3
                # R3 es la ronda final que contiene la referencia absoluta del experimento
                r3_entries = tree.get_entries_by_round(3)
                
                for entry_r3 in r3_entries:
                    if raised_r2 not in entry_r3.calibset.sensors:
                        continue
                    
                    # Obtener referencia del R3 (primer sensor de reference_sensors)
                    reference_id = entry_r3.calibset.reference_sensors[0].id if entry_r3.calibset.reference_sensors else None
                    
                    # Offset raised_r2 → reference
                    if raised_r2.id == reference_id:
                        offset_3 = 0.0
                        error_3 = 0.0
                    elif raised_r2.id in entry_r3.calibset.mean_offsets:
                        offset_3 = entry_r3.calibset.mean_offsets[raised_r2.id]
                        error_3 = entry_r3.calibset.std_offsets.get(raised_r2.id, 0.0)
                    else:
                        continue
                    
                    # Encadenar los tres offsets para obtener el offset total
                    # offset_total = (sensor → raised_r1) + (raised_r1 → raised_r2) + (raised_r2 → referencia)
                    total_offset = offset_1 + offset_2 + offset_3
                    total_error = propagate_error(error_1, error_2, error_3)
                    
                    # Guardar información del camino completo
                    path_details = [
                        (start_entry, raised_r1),
                        (entry_r2, raised_r2),
                        (entry_r3, reference_id)
                    ]
                    
                    # Añadir este camino a la lista de caminos válidos
                    paths.append((total_offset, total_error, path_details))
    
    return paths


def weighted_average_paths(
    paths: List[Tuple[float, float, any]]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calcula la media ponderada de múltiples caminos usando 1/σ² como peso.
    
    Args:
        paths: Lista de tuplas (offset, error, path_details)
    
    Returns:
        Tupla (offset_promedio, error_propagado) o (None, None) si no hay caminos
    
    Formula:
        w_i = 1 / σ_i²
        μ = Σ(w_i * x_i) / Σ(w_i)
        σ = 1 / √(Σ(w_i))
    
    Examples:
        >>> paths = [(0.123, 0.002), (0.125, 0.003), (0.124, 0.0025)]
        >>> offset, error = weighted_average_paths(paths)
        >>> print(f"Media ponderada: {offset:.4f} ± {error:.4f}")
    """
    if not paths:
        return None, None
    
    # Si solo hay un camino, devolver su offset y error directamente
    if len(paths) == 1:
        return paths[0][0], paths[0][1]
    
    # Extraer los offsets y errores de todos los caminos
    offsets = np.array([p[0] for p in paths])
    errors = np.array([p[1] for p in paths])
    
    # Calcular pesos para la media ponderada: peso = 1/error²
    # Los caminos con menor error tienen más peso (son más confiables)
    # Evitar división por cero usando un valor muy pequeño
    errors_safe = np.where(errors == 0, 1e-10, errors)
    weights = 1.0 / (errors_safe ** 2)
    
    # Calcular la media ponderada: suma(peso * offset) / suma(pesos)
    weighted_mean = np.sum(weights * offsets) / np.sum(weights)
    
    # Calcular el error propagado: 1 / raíz(suma de pesos)
    # Esto da un error menor cuando hay más caminos (más información)
    propagated_error = 1.0 / np.sqrt(np.sum(weights))
    
    return weighted_mean, propagated_error


def calibrate_tree(
    tree: Tree,
    reference_sensor_id: Optional[int] = None,
    output_csv: Optional[str] = None
) -> pd.DataFrame:
    """
    Calcula constantes de calibración finales para todos los sensores del tree.
    
    Proceso:
    1. Para cada sensor en R1:
       - Encontrar TODOS los caminos posibles hacia la referencia R3
       - Calcular media ponderada de todos los caminos
    2. Incluir sensores de R2 y R3 también
    3. Exportar a CSV (opcional)
    
    Args:
        tree: Tree con estructura completa y offsets calculados
        reference_sensor_id: Sensor de referencia absoluta (None = usar root.calibset.reference_id)
        output_csv: Ruta para exportar CSV (None = no exportar)
    
    Returns:
        DataFrame con constantes de calibración
        Columnas: Sensor, Set, Round, Constante_Calibracion_K, Error_K, N_Paths, Status
    
    Examples:
        >>> tree = create_tree_from_calibsets(calibsets, config)
        >>> df = calibrate_tree(tree, output_csv="../data/results/calibration_constants.csv")
        >>> print(df[df['Status'] == 'Calculado'])
    """
    results = []
    
    root = tree.get_root()
    if root is None:
        print("[WARNING] Error: Tree no tiene root establecido")
        return pd.DataFrame()
    
    # Obtener sensor de referencia
    if reference_sensor_id is None:
        reference_sensor_id = root.calibset.reference_sensors[0].id if root.calibset.reference_sensors else None
    
    print(f"\nCalculando constantes de calibración:")
    print(f"  Referencia absoluta: Sensor {reference_sensor_id} (Set {root.set_number})")
    print("=" * 70)
    
    # Procesar sensores de R1
    r1_entries = tree.get_entries_by_round(1)
    print(f"\nProcesando {len(r1_entries)} sets de Ronda 1...")
    
    total_sensors = 0
    calculated_sensors = 0
    
    for entry in sorted(r1_entries, key=lambda e: e.set_number):
        print(f"\n  Set {entry.set_number}:")
        
        for sensor in entry.calibset.sensors:
            total_sensors += 1
            
            # Verificar si está descartado
            if entry.is_sensor_discarded(sensor):
                results.append({
                    'Sensor': sensor.id,
                    'Set': entry.set_number,
                    'Round': tree.get_round(entry),
                    'Constante_Calibracion_K': np.nan,
                    'Error_K': np.nan,
                    'N_Paths': 0,
                    'Status': 'Descartado'
                })
                continue
            
            # Encontrar caminos desde sensor hasta referencia
            paths = find_all_paths_to_reference(sensor, entry, tree)
            
            if not paths:
                results.append({
                    'Sensor': sensor.id,
                    'Set': entry.set_number,
                    'Round': tree.get_round(entry),
                    'Constante_Calibracion_K': np.nan,
                    'Error_K': np.nan,
                    'N_Paths': 0,
                    'Status': 'Sin conexión'
                })
                continue
            
            # Media ponderada de todos los caminos
            offset, error = weighted_average_paths(paths)
            
            if offset is not None:
                calculated_sensors += 1
                results.append({
                    'Sensor': sensor.id,
                    'Set': entry.set_number,
                    'Round': tree.get_round(entry),
                    'Constante_Calibracion_K': offset,
                    'Error_K': error,
                    'N_Paths': len(paths),
                    'Status': 'Calculado'
                })
                
                if sensor in entry.raised_sensors:
                    print(f"    Sensor {sensor.id} (RAISED): {offset:.4f} ± {error:.4f} K ({len(paths)} caminos)")
                elif len(paths) > 2:
                    print(f"    Sensor {sensor.id}: {offset:.4f} ± {error:.4f} K ({len(paths)} caminos)")
    
    # Agregar referencia absoluta
    results.append({
        'Sensor': reference_sensor_id,
        'Set': root.set_number,
        'Round': tree.get_round(root),  # Calcular dinámicamente (debería ser 3)
        'Constante_Calibracion_K': 0.0,
        'Error_K': 0.0,
        'N_Paths': 0,
        'Status': 'Referencia'
    })
    
    # Crear DataFrame
    df = pd.DataFrame(results)
    df = df.sort_values(['Set', 'Sensor'])
    
    # Resumen
    print("\n" + "=" * 70)
    print(f"[OK] Calibración completada:")
    print(f"  Total sensores: {total_sensors}")
    print(f"  Calculados: {calculated_sensors}")
    print(f"  Descartados: {len(df[df['Status'] == 'Descartado'])}")
    print(f"  Sin conexión: {len(df[df['Status'] == 'Sin conexión'])}")
    
    # Estadísticas de caminos
    calculated = df[df['Status'] == 'Calculado']
    if len(calculated) > 0:
        print(f"\n  Caminos por sensor:")
        print(f"    Promedio: {calculated['N_Paths'].mean():.1f}")
        print(f"    Máximo: {calculated['N_Paths'].max()}")
        print(f"    Mínimo: {calculated['N_Paths'].min()}")
    
    # Exportar CSV
    if output_csv:
        df.to_csv(output_csv, index=False)
        print(f"\n[OK] CSV exportado: {output_csv}")
    
    return df


def export_calibration_details(
    tree: Tree,
    output_csv: str,
    reference_sensor_id: Optional[int] = None
) -> pd.DataFrame:
    """
    Exporta detalles completos de TODOS los caminos de calibración para análisis.
    
    Incluye:
    - Cada camino individual (sin promediar)
    - Pasos intermedios (offset_1, offset_2, offset_3)
    - Errores de cada paso
    - Raised usados en cada paso
    - Media ponderada final
    
    Args:
        tree: Tree con estructura completa
        output_csv: Ruta para exportar CSV
        reference_sensor_id: Sensor de referencia (None = usar root.reference_id)
    
    Returns:
        DataFrame con detalles de todos los caminos
    """
    results = []
    
    root = tree.get_root()
    if root is None:
        print("[WARNING] Error: Tree no tiene root establecido")
        return pd.DataFrame()
    
    if reference_sensor_id is None:
        reference_sensor_id = root.calibset.reference_sensors[0].id if root.calibset.reference_sensors else None
    
    print(f"\nExportando detalles de calibración...")
    print(f"  Referencia: Sensor {reference_sensor_id}")
    
    # Solo procesar R1
    r1_entries = tree.get_entries_by_round(1)
    
    for entry in sorted(r1_entries, key=lambda e: e.set_number):
        for sensor in entry.calibset.sensors:
            # Skip descartados
            if entry.is_sensor_discarded(sensor):
                continue
            
            # Buscar todos los caminos
            paths = find_all_paths_to_reference(sensor, entry, tree)
            
            if not paths:
                continue
            
            # Registrar cada camino individualmente
            for path_idx, (total_offset, total_error, path_details) in enumerate(paths, 1):
                # Extraer detalles de cada paso
                entry_r1, raised_r1 = path_details[0]
                entry_r2, raised_r2 = path_details[1]
                entry_r3, reference = path_details[2]
                
                # Paso 1: sensor → raised_r1
                offset_1, error_1 = entry_r1.get_offset_to_raised(sensor, raised_r1)
                
                # Paso 2: raised_r1 → raised_r2
                offset_2, error_2 = entry_r2.get_offset_to_raised(raised_r1, raised_r2)
                
                # Paso 3: raised_r2 → reference
                if raised_r2.id == reference:
                    offset_3 = 0.0
                    error_3 = 0.0
                else:
                    offset_3 = entry_r3.calibset.mean_offsets.get(raised_r2.id, 0.0)
                    error_3 = entry_r3.calibset.std_offsets.get(raised_r2.id, 0.0)
                
                results.append({
                    'Sensor': sensor.id,
                    'Set': entry.set_number,
                    'Round': tree.get_round(entry),  # Calcular dinámicamente
                    'Path_Number': path_idx,
                    
                    # Paso 1: sensor → raised_r1 en R1
                    'Paso1_From': sensor.id,
                    'Paso1_To': raised_r1.id,
                    'Paso1_Set': entry_r1.set_number,
                    'Paso1_Offset_K': offset_1,
                    'Paso1_Error_K': error_1,
                    
                    # Paso 2: raised_r1 → raised_r2 en R2
                    'Paso2_From': raised_r1.id,
                    'Paso2_To': raised_r2.id,
                    'Paso2_Set': entry_r2.set_number,
                    'Paso2_Offset_K': offset_2,
                    'Paso2_Error_K': error_2,
                    
                    # Paso 3: raised_r2 → reference en R3
                    'Paso3_From': raised_r2.id,
                    'Paso3_To': reference,
                    'Paso3_Set': entry_r3.set_number,
                    'Paso3_Offset_K': offset_3,
                    'Paso3_Error_K': error_3,
                    
                    # Total
                    'Total_Offset_K': total_offset,
                    'Total_Error_K': total_error,
                })
            
            # Añadir también la media ponderada
            if len(paths) > 0:
                final_offset, final_error = weighted_average_paths(paths)
                
                results.append({
                    'Sensor': sensor.id,
                    'Set': entry.set_number,
                    'Round': tree.get_round(entry),  # Calcular dinámicamente
                    'Path_Number': 0,  # 0 indica media ponderada
                    
                    'Paso1_From': sensor.id,
                    'Paso1_To': 'PROMEDIO',
                    'Paso1_Set': entry.set_number,
                    'Paso1_Offset_K': np.nan,
                    'Paso1_Error_K': np.nan,
                    
                    'Paso2_From': 'PROMEDIO',
                    'Paso2_To': 'PROMEDIO',
                    'Paso2_Set': np.nan,
                    'Paso2_Offset_K': np.nan,
                    'Paso2_Error_K': np.nan,
                    
                    'Paso3_From': 'PROMEDIO',
                    'Paso3_To': reference,
                    'Paso3_Set': entry_r3.set_number,
                    'Paso3_Offset_K': np.nan,
                    'Paso3_Error_K': np.nan,
                    
                    'Total_Offset_K': final_offset,
                    'Total_Error_K': final_error,
                })
    
    # Crear DataFrame
    df = pd.DataFrame(results)
    df = df.sort_values(['Sensor', 'Path_Number'])
    
    # Exportar
    df.to_csv(output_csv, index=False)
    print(f"[OK] Detalles exportados: {output_csv}")
    print(f"  Total filas: {len(df)}")
    print(f"  Sensores únicos: {df['Sensor'].nunique()}")
    
    return df
