#!/usr/bin/env python3
"""
Script principal para procesamiento de calibración RTD.

Calcula constantes de calibración usando el método de MEDIA PONDERADA (1/error²)
que considera todos los caminos válidos disponibles para cada sensor.

IMPORTANTE: Usar rango 3-39 para procesar todos los sets de Ronda 1 (R1)
que tienen conexión completa con la referencia del Set 57 (Ronda 3).

Uso:
    python main.py [--range inicio fin] [--sets S1 S2 S3...]
    
Ejemplos:
    python main.py                       # Por defecto: procesa sets 3-39
    python main.py --range 3 39          # Procesar sets del 3 al 39 (RECOMENDADO)
    python main.py --range 3 10          # Solo sets 3-10 (para pruebas)
    python main.py --sets 3 4 5 49 57    # Procesar sets específicos
    
Salida:
    - Estadísticas en terminal (errores, constantes, resumen por set)
    - calibration_analisis_multicamino.csv (análisis completo con 3 estrategias)
    - calibration_constants_media_ponderada.csv (CSV simplificado para uso final)
"""

import sys
import argparse
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from set import Set  # type: ignore
from tree import Tree  # type: ignore
import yaml


def main():
    """
    Punto de entrada principal para el procesamiento de calibración.
    """
    
    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description='Procesamiento de calibración RTD con media ponderada'
    )
    parser.add_argument('--range', nargs=2, type=int, metavar=('INICIO', 'FIN'),
                       help='Rango de sets R1 a procesar (ej: --range 3 39)')
    parser.add_argument('--sets', nargs='+', type=int,
                       help='Sets específicos a procesar (ej: --sets 3 4 5 49 57)')
    
    args = parser.parse_args()
    
    print("="*80)
    print("RTD CALIBRATION - Constantes con Media Ponderada (1/error²)")
    print("="*80)
    
    # Determinar sets a procesar
    if args.range:
        r1_start, r1_end = args.range
        print(f"\nModo: Rango de sets R1 ({r1_start}-{r1_end})")
    elif args.sets:
        sets_to_process = args.sets
        print(f"\nModo: Sets específicos {sets_to_process}")
    else:
        # Por defecto: procesar sets 3-39 (R1 completo)
        r1_start, r1_end = 3, 39
        print(f"\nModo: Rango por defecto R1 ({r1_start}-{r1_end})")
    
    # Cargar config para obtener todos los sets necesarios
    config_path = Path(__file__).parent / 'config' / 'config.yml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    all_set_ids = list(config['sensors']['sets'].keys())
    
    print(f"\nCargando datos de {len(all_set_ids)} sets configurados...")
    set_handler = Set()
    
    # Procesar todos los sets (necesarios para el árbol)
    set_handler.group_runs(all_set_ids)
    set_handler.calculate_calibration_constants(all_set_ids)
    
    # Crear diccionario de sets procesados
    sets_dict = {}
    for set_id in all_set_ids:
        class SetData:
            def __init__(self, constants, errors):
                self.calibration_constants = constants
                self.calibration_errors = errors
        
        if set_id in set_handler.calibration_constants:
            sets_dict[float(set_id)] = SetData(
                set_handler.calibration_constants[set_id],
                set_handler.calibration_errors[set_id]
            )
    
    print(f"Sets procesados: {len(sets_dict)}")
    
    # Construcción del árbol
    print("\nConstruyendo árbol de calibración...")
    tree = Tree(sets_dict, str(config_path))
    
    # Calcular constantes con MEDIA PONDERADA
    print("\nCalculando constantes con MEDIA PONDERADA de todos los caminos...")
    print("(Esto explora todas las combinaciones posibles de caminos)\n")
    
    if args.range or (not args.sets):
        df_results = tree.calculate_all_offsets_multi_path(r1_sets_range=(r1_start, r1_end))
    else:
        # Para sets específicos, aún usar calculate_all_offsets_multi_path con rango amplio
        df_results = tree.calculate_all_offsets_multi_path(r1_sets_range=(min(sets_to_process), max(sets_to_process)))
    
    # Filtrar solo sensores calculados
    calculated = df_results[df_results['Status'] == 'Calculado'].copy()
    
    # Mostrar estadísticas globales
    print("="*80)
    print("RESULTADOS GLOBALES")
    print("="*80)
    print(f"\nTotal sensores procesados: {len(df_results)}")
    print(f"  Calculados: {len(calculated)}")
    print(f"  Descartados: {(df_results['Status'] == 'Sensor descartado').sum()}")
    print(f"  Sin conexión: {(df_results['Status'] == 'Sin conexión').sum()}")
    print(f"  Referencia: {(df_results['Status'] == 'Referencia').sum()}")
    
    print("\n--- Estadísticas de MEDIA PONDERADA ---")
    print(f"Error medio: {calculated['Error_Media_Ponderada_K'].mean() * 1000:.3f} mK")
    print(f"Error std: {calculated['Error_Media_Ponderada_K'].std() * 1000:.3f} mK")
    print(f"Constante media: {calculated['Constante_Media_Ponderada_K'].mean():.6f} K")
    print(f"Constante std: {calculated['Constante_Media_Ponderada_K'].std():.6f} K")
    
    # Mostrar comparación con primer camino
    mejora = (calculated['Error_Primer_Camino_K'].mean() - calculated['Error_Media_Ponderada_K'].mean()) * 1000
    print(f"\nMejora vs primer camino: {mejora:.3f} mK")
    
    # Resumen por set
    print("\n" + "="*80)
    print("RESUMEN POR SET (Media Ponderada)")
    print("="*80)
    
    for set_id in sorted(calculated['Set'].unique()):
        set_data = calculated[calculated['Set'] == set_id]
        
        print(f"\nSet {int(set_id)}:")
        print(f"  Sensores calculados: {len(set_data)}")
        print(f"  Constante media: {set_data['Constante_Media_Ponderada_K'].mean():.6f} ± {set_data['Constante_Media_Ponderada_K'].std():.6f} K")
        print(f"  Error medio: {set_data['Error_Media_Ponderada_K'].mean() * 1000:.3f} mK")
        print(f"  Caminos promedio por sensor: {set_data['N_Caminos'].mean():.1f}")
    
    # Mostrar tabla de constantes (primeros 20 sensores)
    print("\n" + "="*80)
    print("CONSTANTES INDIVIDUALES (Primeros 20 sensores)")
    print("="*80)
    print(f"\n{'Sensor':<8} {'Set':<5} {'Constante (K)':<15} {'Error (mK)':<12} {'N_Caminos':<10}")
    print("-"*80)
    
    for _, row in calculated.head(20).iterrows():
        sensor = int(row['Sensor'])
        set_id = int(row['Set'])
        const = row['Constante_Media_Ponderada_K']
        error = row['Error_Media_Ponderada_K'] * 1000
        n_paths = int(row['N_Caminos'])
        print(f"{sensor:<8} {set_id:<5} {const:<15.6f} {error:<12.3f} {n_paths:<10}")
    
    if len(calculated) > 20:
        print(f"\n... y {len(calculated) - 20} sensores más (ver archivos CSV)")
    
    # Guardar resultados a CSV
    output_dir = Path(__file__).parent / 'data' / 'results'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # CSV completo con análisis multi-camino
    output_multi = output_dir / 'calibration_analisis_multicamino.csv'
    df_results.to_csv(output_multi, index=False)
    print(f"\n✓ CSV completo guardado: {output_multi}")
    
    # CSV simplificado con solo media ponderada (para usuarios)
    df_simple = calculated[['Sensor', 'Set', 'Constante_Media_Ponderada_K', 
                            'Error_Media_Ponderada_K', 'N_Caminos']].copy()
    df_simple.columns = ['Sensor', 'Set', 'Constante_Calibracion_K', 'Error_K', 'N_Caminos']
    output_simple = output_dir / 'calibration_constants_media_ponderada.csv'
    df_simple.to_csv(output_simple, index=False)
    print(f"✓ CSV simplificado guardado: {output_simple}")
    
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80)
    print("\nLos resultados incluyen:")
    print("  1. Análisis completo (3 estrategias): calibration_analisis_multicamino.csv")
    print("  2. Constantes finales (media ponderada): calibration_constants_media_ponderada.csv")
    print("="*80)


if __name__ == "__main__":
    main()
