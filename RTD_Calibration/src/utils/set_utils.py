"""
Utilidades para procesamiento de sets de calibración.

Funciones:
- create_calibration_set(): Crea y procesa un set completo
- calculate_set_statistics(): Calcula estadísticas de offsets
- export_calibset_to_csv(): Exporta resultados a CSV
- create_multiple_calibsets(): Crea múltiples sets
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union, Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..calibset import CalibSet
    from ..run import Run
    from ..sensor import Sensor


def calculate_set_statistics(calib_set, runs: list['Run']) -> tuple[Dict['Sensor', float], Dict['Sensor', float]]:
    """
    Calcula mean_offsets y std_offsets usando MEDIA PONDERADA por error.
    Traduce offsets de canal → sensor usando el índice de la lista.
    
    Args:
        calib_set: Instancia CalibSet con sensors (en orden de canal)
        runs: Lista de runs válidos (con offsets por canal)
    
    Returns:
        tuple: (mean_offsets, std_offsets) donde:
            - mean_offsets: {Sensor: weighted_mean}
            - std_offsets: {Sensor: propagated_error}
    
    Nota:
        sensors[0] = canal 1, sensors[1] = canal 2, etc.
        Así que sensor = calib_set.sensors[canal - 1]
    """
    if not runs:
        return {}, {}
    
    # Recopilar offsets y errores por sensor (traduciendo desde canales)
    offsets_by_sensor = {}  # {sensor: [offset1, offset2, ...]}
    errors_by_sensor = {}   # {sensor: [error1, error2, ...]}
    
    # Recorrer todos los runs válidos para recopilar datos
    for run in runs:
        # run.offsets es un dict {canal: offset}
        # Necesitamos traducirlo a {sensor: offset} usando la lista de sensores
        for channel, offset in run.offsets.items():
            # El canal 1 corresponde a sensors[0], canal 2 a sensors[1], etc.
            if channel < 1 or channel > len(calib_set.sensors):
                continue  # Canal fuera de rango, ignorar
            
            # Obtener el objeto Sensor que corresponde a este canal
            sensor = calib_set.sensors[channel - 1]  # canal 1 está en índice 0
            
            # Inicializar listas para este sensor si es la primera vez
            if sensor not in offsets_by_sensor:
                offsets_by_sensor[sensor] = []
                errors_by_sensor[sensor] = []
            
            # Agregar offset y error de este run para este sensor
            offsets_by_sensor[sensor].append(offset)
            error = run.offset_errors.get(channel, 0.0)
            errors_by_sensor[sensor].append(error)
    
    # Inicializar diccionarios de resultados
    mean_offsets = {}
    std_offsets = {}
    
    # Calcular media ponderada y error propagado para cada sensor
    for sensor in offsets_by_sensor.keys():
        offsets = np.array(offsets_by_sensor[sensor])
        errors = np.array(errors_by_sensor[sensor])
        
        # Caso especial: si solo hay un offset disponible, usarlo directamente
        if len(offsets) == 1:
            mean_offsets[sensor] = offsets[0]
            std_offsets[sensor] = errors[0] if errors[0] > 0 else 0.0
            continue
        
        # Si todos los errores son 0, usar media aritmética simple
        if np.all(errors == 0):
            mean_offsets[sensor] = np.mean(offsets)
            std_offsets[sensor] = 0.0
            continue
        
        # Reemplazar errores=0 con un valor pequeño para evitar división por 0
        errors_safe = np.where(errors == 0, 1e-10, errors)
        
        # Pesos: w_i = 1 / σ_i²
        weights = 1.0 / (errors_safe ** 2)
        
        # Media ponderada: μ = Σ(w_i * x_i) / Σ(w_i)
        weighted_mean = np.sum(weights * offsets) / np.sum(weights)
        
        # Error propagado: σ = 1 / √(Σ(w_i))
        propagated_error = 1.0 / np.sqrt(np.sum(weights))
        
        mean_offsets[sensor] = weighted_mean
        std_offsets[sensor] = propagated_error
    
    # Forzar referencia a offset=0, std=0 (primer sensor, canal 1)
    reference_sensor = calib_set.sensors[0] if calib_set.sensors else None
    if reference_sensor and reference_sensor in mean_offsets:
        mean_offsets[reference_sensor] = 0.0
        std_offsets[reference_sensor] = 0.0
    
    return mean_offsets, std_offsets


def create_calibration_set(
    set_number: Union[int, float],
    logfile: pd.DataFrame,
    config: dict
) -> tuple['CalibSet', Dict['Sensor', float], Dict['Sensor', float]]:
    """
    Crea y rellena un CalibSet completo con sensors, runs y estadísticas.
    
    Returns:
        tuple: (calib_set, mean_offsets, std_offsets)
    """
    try:
        from ..calibset import CalibSet
    except ImportError:
        from calibset import CalibSet
    
    # Convertir set_number a float
    set_number = float(set_number)
    
    # 1. Crear CalibSet vacío
    calib_set = CalibSet(set_number)
    
    # Inicializar resultados
    mean_offsets = {}
    std_offsets = {}
    
    # 2. Obtener configuración del set
    sets_config = config.get('sensors', {}).get('sets', {})
    set_config = sets_config.get(str(set_number), sets_config.get(set_number, {}))
    
    if not set_config:
        print(f"[WARNING] Set {set_number} no encontrado en config")
        return calib_set, {}, {}
    
    sensor_ids = set_config.get('sensors', [])
    
    if not sensor_ids:
        print(f"[WARNING] Set {set_number} no tiene sensors definidos en config")
        return calib_set, {}, {}
    
    # 3. Crear instancias Sensor y agregarlas al Set
    try:
        from ..sensor import Sensor
    except ImportError:
        from sensor import Sensor
    
    for sensor_id in sensor_ids:
        sensor = Sensor(sensor_id)
        calib_set.sensors.append(sensor)
    
    print(f"[OK] Set {set_number}: {len(calib_set.sensors)} sensores creados")
    
    # 4. Elegir sensor de referencia (primer sensor del set, que está en canal 1)
    reference_sensor = calib_set.sensors[0]
    reference_channel = 1  # Primer sensor está en canal 1
    
    # Guardar como reference_sensors (lista, aunque solo sea uno)
    calib_set.reference_sensors = [reference_sensor]
    
    print(f"  Referencia: {reference_sensor.id} (canal {reference_channel})")
    
    # 5. Obtener runs válidos del logfile
    from .filtering import filter_valid_runs
    valid_filenames = filter_valid_runs(logfile, set_number)
    
    if not valid_filenames:
        print(f"[WARNING] Set {set_number} no tiene runs válidos")
        return calib_set, {}, {}
    
    print(f"  Procesando {len(valid_filenames)} runs válidos...")
    
    # 6. Procesar cada run y agregarlo a la lista
    from .run_utils import process_run_complete
    runs = []
    for filename in valid_filenames:
        run = process_run_complete(
            filename=filename,
            logfile=logfile,
            config=config,
            set_number=set_number,
            reference_channel=reference_channel,  # Cambio: usar canal en lugar de sensor ID
            time_window=(20, 40)
        )
        
        # Solo agregar si es válido Y tiene offsets
        if run.is_valid and run.offsets:
            runs.append(run)
    
    # Guardar runs en CalibSet
    calib_set.runs = runs
    
    print(f"  [OK] {len(runs)} runs válidos con offsets")
    
    # 7. Calcular estadísticas (mean_offsets, std_offsets)
    if runs:
        mean_offsets, std_offsets = calculate_set_statistics(calib_set, runs)
        
        # Asignar al CalibSet
        calib_set.mean_offsets = {s.id: mean_offsets[s] for s in mean_offsets}
        calib_set.std_offsets = {s.id: std_offsets[s] for s in std_offsets}
        
        n_sensors_with_offsets = len(mean_offsets)
        n_sensors_total = len(calib_set.sensors)
        
        if n_sensors_with_offsets < n_sensors_total:
            n_missing = n_sensors_total - n_sensors_with_offsets
            print(f"  ℹ️  {n_missing} sensores sin offsets (descartados o con NaN en todos los runs)")
        
        print(f"  [OK] Estadísticas calculadas: {n_sensors_with_offsets}/{n_sensors_total} sensores")
    else:
        print(f"    Sin runs válidos, no se calcularon estadísticas")
        mean_offsets = {}
        std_offsets = {}
        calib_set.mean_offsets = {}
        calib_set.std_offsets = {}
    
    return calib_set, mean_offsets, std_offsets


def export_calibset_to_csv(
    calib_set,
    mean_offsets: Dict['Sensor', float],
    std_offsets: Dict['Sensor', float],
    n_runs: int,
    reference_id: int,
    output_path: Optional[str] = None
) -> str:
    """
    Exporta un CalibSet a CSV con media ponderada y error propagado.
    
    Args:
        calib_set: Instancia CalibSet con sensors
        mean_offsets: {Sensor: mean_offset} calculados
        std_offsets: {Sensor: std_offset} calculados
        n_runs: Número de runs usados en el cálculo
        reference_id: ID del sensor de referencia
        output_path: Ruta de salida (opcional, default: calibset_{N}.csv)
    
    Returns:
        str: Ruta del archivo CSV generado
    """
    if not mean_offsets:
        print(f"[WARNING] No hay offsets para exportar")
        return ""
    
    # Ruta por defecto
    if output_path is None:
        repo_root = Path(__file__).parents[2]
        results_dir = repo_root / "data" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        output_path = results_dir / f"calibset_{int(calib_set.set_number)}.csv"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Crear DataFrame
    rows = []
    for sensor in sorted(mean_offsets.keys(), key=lambda s: s.id):
        rows.append({
            'set_number': calib_set.set_number,
            'sensor_id': sensor.id,
            'mean_offset': mean_offsets[sensor],
            'std_offset': std_offsets.get(sensor, 0.0),
            'n_runs': n_runs,
            'reference_id': reference_id
        })
    
    df = pd.DataFrame(rows)
    
    # Guardar CSV
    df.to_csv(output_path, index=False)
    
    print(f"[OK] CalibSet {calib_set.set_number} exportado → {output_path}")
    print(f"  Sensores: {len(rows)}")
    print(f"  Runs usados: {n_runs}")
    
    return str(output_path)


def create_multiple_calibsets(
    set_numbers: Union[List[Union[int, float]], str],
    logfile: pd.DataFrame,
    config: dict
) -> Dict[float, tuple]:
    """
    Crea múltiples CalibSets de una vez.
    
    Returns:
        Dict[float, tuple]: {set_number: (calib_set, mean_offsets, std_offsets)}
    """
    # Si set_numbers es 'all', obtener todos del config
    if isinstance(set_numbers, str) and set_numbers.lower() == 'all':
        sets_config = config.get('sensors', {}).get('sets', {})
        set_numbers = sorted([float(k) for k in sets_config.keys()])
    
    print("=" * 70)
    print(f"CREANDO {len(set_numbers)} CALIBSETS")
    print("=" * 70)
    
    calibsets = {}
    success_count = 0
    
    for set_num in set_numbers:
        try:
            print(f"\n[{success_count + 1}/{len(set_numbers)}] Set {set_num}:")
            
            calib_set, mean_offsets, std_offsets = create_calibration_set(
                set_number=set_num,
                logfile=logfile,
                config=config
            )
            
            if mean_offsets:
                calibsets[float(set_num)] = (calib_set, mean_offsets, std_offsets)
                success_count += 1
            else:
                print(f"  [FAIL] Set {set_num} no tiene offsets válidos")
                
        except Exception as e:
            print(f"  [FAIL] Error procesando set {set_num}: {e}")
    
    print(f"\n[OK] Completado: {success_count}/{len(set_numbers)} sets procesados exitosamente")
    return calibsets
