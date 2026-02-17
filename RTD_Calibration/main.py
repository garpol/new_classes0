#!/usr/bin/env python3
"""
Script principal para procesamiento de calibración RTD.

Calcula constantes de calibración usando el método de MEDIA PONDERADA (1/error²)
que considera todos los caminos válidos disponibles para cada sensor.

NUEVA ARQUITECTURA:
- TreeEntry: Nodos con información de cada CalibSet y relaciones
- Tree: Contenedor jerárquico R3 → R2 → R1
- utils/tree_utils.py: Construcción del Tree
- utils/calibration_utils.py: Cálculo de constantes finales

IMPORTANTE: Procesa TODOS los sets necesarios para construir el Tree completo.
La referencia absoluta es el Set 57 (Ronda 3).

Uso:
    python main.py [--output PATH]
    
Ejemplos:
    python main.py                                    # Usa rutas por defecto
    python main.py --output custom_results.csv        # CSV personalizado
    
Salida:
    - calibration_constants_tree.csv (constantes finales con multi-camino)
    - calibration_stats_by_set.csv (estadísticas por set)
"""

import sys
import argparse
from pathlib import Path
import time

# Añadir src al path una sola vez
src_path = Path(__file__).parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Imports de las clases principales
from logfile import Logfile

# Imports de utils - todos en un solo lugar
from utils.config import load_config
from utils.tree_utils import create_tree_from_calibsets
from utils.calibration_utils import calibrate_tree, export_calibration_details
from utils.set_utils import create_calibration_set


def main():
    """
    Punto de entrada principal para el procesamiento de calibración.
    
    Usa la nueva arquitectura modular:
    1. Carga configuración
    2. Crea CalibSets para todos los sets
    3. Construye Tree jerárquico
    4. Calcula constantes finales con multi-camino
    """
    
    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description='Procesamiento de calibración RTD con arquitectura modular Tree'
    )
    parser.add_argument('--output', type=str, 
                       help='Ruta para el CSV de salida (default: data/results/calibration_constants_tree.csv)')
    
    args = parser.parse_args()
    
    print("="*80)
    print("RTD CALIBRATION - Nueva Arquitectura Tree")
    print("="*80)
    print("\nArquitectura:")
    print("  - TreeEntry: Nodos con CalibSets y relaciones")
    print("  - Tree: Contenedor jerárquico R3 → R2 → R1")
    print("  - Multi-camino: Media ponderada con 1/σ²")
    
    # Rutas
    project_root = Path(__file__).parent
    config_path = project_root / 'config' / 'config.yml'
    
    if args.output:
        output_path = project_root / args.output
    else:
        output_path = project_root / 'data' / 'results' / 'calibration_constants_tree.csv'
    
    print(f"\nConfiguracion: {config_path}")
    print(f"Salida: {output_path}")
    
    # 1. Cargar configuración
    print("\n" + "="*80)
    print("PASO 1: Carga de Configuración")
    print("="*80)
    
    config = load_config(str(config_path))
    all_set_ids = sorted(config['sensors']['sets'].keys())
    
    print(f"✓ Configuración cargada")
    print(f"  Total sets: {len(all_set_ids)}")
    
    # Contar por rondas
    rounds_count = {}
    for set_info in config['sensors']['sets'].values():
        try:
            r = int(set_info['round'])  # Asegurar que sea int
            rounds_count[r] = rounds_count.get(r, 0) + 1
        except (ValueError, KeyError):
            # Ignorar sets sin round válido (ej: 'Refs')
            continue
    
    print(f"  Distribución por rondas:")
    for r in sorted(rounds_count.keys()):
        print(f"    R{r}: {rounds_count[r]} sets")
    
    # 2. Crear CalibSets
    print("\n" + "="*80)
    print("PASO 2: Creación de CalibSets")
    print("="*80)
    
    # Cargar logfile una sola vez
    # El config tiene rutas relativas que incluyen RTD_Calibration, necesitamos ajustar
    logfile_relative = config['paths']['logfile']
    if logfile_relative.startswith('RTD_Calibration/'):
        logfile_relative = logfile_relative.replace('RTD_Calibration/', '', 1)
    logfile_path = project_root / logfile_relative
    
    logfile_obj = Logfile(filepath=str(logfile_path))
    logfile = logfile_obj.log_file
    print(f"✓ Logfile cargado: {len(logfile)} entradas")
    
    calibsets = {}
    failed_sets = []
    start_time = time.time()
    
    print(f"\nProcesando {len(all_set_ids)} sets...")
    
    for i, set_id in enumerate(all_set_ids, 1):
        try:
            # Usar create_calibration_set de utils - devuelve tupla (calibset, mean_offsets, std_offsets)
            calibset, mean_offsets, std_offsets = create_calibration_set(
                set_number=set_id,
                logfile=logfile,
                config=config
            )
            calibsets[set_id] = calibset  # Solo guardamos el CalibSet
            
            # Log cada 10 sets
            if i % 10 == 0:
                elapsed = time.time() - start_time
                print(f"  Procesados: {i}/{len(all_set_ids)} sets ({elapsed:.1f}s)")
        
        except Exception as e:
            failed_sets.append((set_id, str(e)))
            print(f"  ✗ Set {set_id}: {e}")
    
    elapsed = time.time() - start_time
    
    print(f"\n✓ CalibSets creados: {len(calibsets)}")
    print(f"✗ Fallos: {len(failed_sets)}")
    print(f"⏱  Tiempo: {elapsed:.1f}s")
    
    if not calibsets:
        print("\n⚠️  ERROR: No se pudo crear ningún CalibSet")
        return
    
    # 3. Construir Tree
    print("\n" + "="*80)
    print("PASO 3: Construcción del Tree")
    print("="*80)
    
    tree = create_tree_from_calibsets(
        calibsets=calibsets,
        config=config,
        root_set_id=57.0  # Set 57 es R3 (root/referencia)
    )
    
    print(f"\n✓ Tree construido:")
    print(f"  Total entries: {len(tree.entries)}")
    print(f"  Root: Set {tree.root.set_number if tree.root else 'N/A'}")
    
    # Estadísticas por ronda
    print(f"\n  Entries por ronda:")
    for r in [1, 2, 3]:
        entries = tree.get_entries_by_round(r)
        print(f"    R{r}: {len(entries)} entries")
    
    # Mostrar estructura
    print(f"\n  Estructura jerárquica:")
    print(tree)
    
    # 4. Calcular constantes finales
    print("\n" + "="*80)
    print("PASO 4: Cálculo de Constantes de Calibración")
    print("="*80)
    print("\nUsando MEDIA PONDERADA de múltiples caminos (1/σ²)")
    print("Buscando todos los caminos posibles R1 → R2 → R3...\n")
    
    df_results = calibrate_tree(
        tree=tree,
        reference_sensor_id=None,  # Usa reference del root
        output_csv=str(output_path)
    )
    
    # 4b. Exportar detalles de calibración (pasos intermedios)
    print("\n" + "="*80)
    print("PASO 4b: Exportar Detalles de Calibración")
    print("="*80)
    print("\nGenerando CSV con todos los pasos intermedios...")
    
    details_path = project_root / 'data' / 'results' / 'calibration_details_tree.csv'
    export_calibration_details(
        tree=tree,
        output_csv=str(details_path),
        reference_sensor_id=None
    )
    print(f"✓ Detalles exportados: {details_path}")
    
    # 5. Análisis de resultados
    print("\n" + "="*80)
    print("PASO 5: Análisis de Resultados")
    print("="*80)
    
    # Filtrar solo calculados
    calculated = df_results[df_results['Status'] == 'Calculado'].copy()
    
    if len(calculated) == 0:
        print("\n⚠️  No se calcularon constantes para ningún sensor")
        return
    
    print(f"\nTotal sensores procesados: {len(df_results)}")
    print(f"  Calculados: {len(calculated)}")
    print(f"  Descartados: {(df_results['Status'] == 'Descartado').sum()}")
    print(f"  Sin conexión: {(df_results['Status'] == 'Sin conexión').sum()}")
    print(f"  Referencia: {(df_results['Status'] == 'Referencia').sum()}")
    
    print("\n--- Estadísticas Globales ---")
    print(f"Constante media: {calculated['Constante_Calibracion_K'].mean():.6f} K")
    print(f"Constante std: {calculated['Constante_Calibracion_K'].std():.6f} K")
    print(f"Error medio: {calculated['Error_K'].mean() * 1000:.3f} mK")
    print(f"Error std: {calculated['Error_K'].std() * 1000:.3f} mK")
    print(f"Caminos promedio: {calculated['N_Paths'].mean():.1f}")
    print(f"SNR medio: {(calculated['Constante_Calibracion_K'].abs() / calculated['Error_K']).mean():.1f}")
    
    # Tabla de constantes individuales
    print("\n--- Constantes Individuales (Primeros 20) ---")
    print(f"\n{'Sensor':<8} {'Set':<5} {'Constante (K)':<15} {'Error (mK)':<12} {'N_Paths':<10}")
    print("-"*70)
    
    for _, row in calculated.head(20).iterrows():
        sensor = int(row['Sensor'])
        set_id = int(row['Set'])
        const = row['Constante_Calibracion_K']
        error = row['Error_K'] * 1000
        n_paths = int(row['N_Paths'])
        print(f"{sensor:<8} {set_id:<5} {const:<15.6f} {error:<12.3f} {n_paths:<10}")
    
    if len(calculated) > 20:
        print(f"\n... y {len(calculated) - 20} sensores más (ver CSV)")
    
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80)
    print("\nArchivos generados:")
    print(f"  Constantes finales: {output_path}")
    print(f"  Detalles de calibración: {details_path}")
    print("\nColumnas del CSV de constantes:")
    print("  - Sensor: ID del sensor")
    print("  - Set: Número de set de calibración")
    print("  - Round: Ronda (1, 2 o 3)")
    print("  - Constante_Calibracion_K: Offset final (K)")
    print("  - Error_K: Error propagado (K)")
    print("  - N_Paths: Número de caminos usados")
    print("  - Status: Estado (Calculado/Descartado/Sin conexión)")
    print("\nColumnas del CSV de detalles:")
    print("  - Path_Number=0: Media ponderada final")
    print("  - Path_Number>0: Caminos individuales")
    print("  - Paso1/2/3: Detalles de cada paso del camino")
    print("="*80)


if __name__ == "__main__":
    main()
