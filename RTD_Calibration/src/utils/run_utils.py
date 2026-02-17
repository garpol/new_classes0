"""
Utilidades para procesamiento de runs individuales.

Funciones:
- load_run_from_file(): Carga datos crudos de archivo .txt
- map_sensor_ids_to_run(): Mapea IDs de sensores al Run
- calculate_run_offsets(): Calcula offsets respecto a referencia
- process_run_complete(): Procesa run completo con validaciones
"""

import glob
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union, Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..run import Run
    from ..sensor import Sensor


def load_run_from_file(filename: str, config: dict) -> 'Run':
    """
    Carga datos de un archivo .txt y crea un objeto Run con datos crudos.
    
    Args:
        filename: Nombre del archivo (sin .txt)
        config: Diccionario de configuración
    
    Returns:
        Run: Objeto Run con timestamps y temperatures cargados
    
    Esta función:
    1. Busca el archivo .txt recursivamente
    2. Lee y parsea las columnas Date/Time
    3. Extrae canales de temperatura (channel_1 a channel_14)
    4. Filtra temperaturas fuera de rango válido
    5. Retorna Run con datos crudos (sin procesar offsets)
    """
    try:
        from ..run import Run
    except ImportError:
        from run import Run
    
    run = Run(filename)
    
    # Buscar archivo
    repo_root = Path(__file__).parents[2]  # src/utils/ -> src/
    search_path = repo_root / "data" / "temperature_files"
    
    matches = glob.glob(str(search_path / "**" / f"{filename}.txt"), recursive=True)
    if not matches:
        print(f"  No se encontró {filename}.txt")
        return run
    
    filepath = matches[0]
    
    # Leer archivo
    try:
        # Leer sin header, el archivo no tiene nombres de columnas
        df = pd.read_csv(filepath, sep='\t', header=None, low_memory=False)
        
        # Asignar nombres de columnas manualmente
        # Formato: Date, Time, channel_1, channel_2, ..., channel_14
        col_names = ['Date', 'Time'] + [f'channel_{i}' for i in range(1, 15)]
        df.columns = col_names
        
    except Exception as e:
        print(f"  Error leyendo {filepath}: {e}")
        return run
    
    # Verificar columnas requeridas
    required_cols = ['Date', 'Time']
    if not all(col in df.columns for col in required_cols):
        print(f"  Columnas requeridas faltan en {filename}")
        return run
    
    # Crear timestamps
    try:
        datetime_str = df['Date'] + ' ' + df['Time']
        # Intentar formato flexible (mixed) para aceptar DD/MM/YYYY y MM/DD/YYYY con/sin AM/PM
        timestamps = pd.to_datetime(datetime_str, format='mixed', dayfirst=True, errors='coerce')
        
        # Filtrar timestamps inválidos (NaT)
        valid_mask = timestamps.notna()
        if valid_mask.sum() == 0:
            print(f"  Error: No se pudieron parsear timestamps en {filename}")
            return run
        
        # Filtrar DataFrame y timestamps
        df = df[valid_mask].copy().reset_index(drop=True)
        timestamps = timestamps[valid_mask].reset_index(drop=True)
        
        run.timestamps = timestamps
    except Exception as e:
        print(f"  Error parseando timestamps en {filename}: {e}")
        return run
    
    # Extraer temperaturas (channel_1 a channel_14)
    temp_cols = {}
    for i in range(1, 15):  # 14 canales
        col_name = f'channel_{i}'
        if col_name in df.columns:
            temps = pd.to_numeric(df[col_name], errors='coerce')
            
            # Filtrar valores fuera de rango válido (LN2: ~77K, ambiente: ~300K)
            valid_mask = (temps >= 50) & (temps <= 400)  # K
            temps_filtered = temps.where(valid_mask, np.nan)
            
            temp_cols[col_name] = temps_filtered.values  # Usar .values para array puro
    
    if temp_cols:
        run.temperatures = pd.DataFrame(temp_cols, index=timestamps)
        print(f"  [OK] Cargado {filename}: {len(run.temperatures)} registros, {len(temp_cols)} canales")
    else:
        print(f"  [WARNING] No se encontraron canales de temperatura en {filename}")
    
    return run


def map_sensor_ids_to_run(run: 'Run', logfile, config: dict) -> list:
    """
    Obtiene la lista de sensor IDs del logfile para un run.
    
    NO modifica run (que es ciego a sensor IDs).
    Retorna la lista de sensor IDs para que CalibSet cree el mapping.
    
    Args:
        run: Objeto Run (para obtener filename y marcar is_valid)
        logfile: DataFrame con LogFile.csv
        config: Diccionario de configuración
    
    Returns:
        list[int]: Lista de sensor IDs en orden de canal (canal 1 → sensor_ids[0], etc.)
    """
    import pandas as pd
    
    # Buscar el run en el logfile
    match = logfile[logfile["Filename"] == run.filename]
    if match.empty:
        print(f"[WARNING] '{run.filename}' no encontrado en logfile")
        return []
    
    row = match.iloc[0]
    
    # Obtener validez del run (BAD/GOOD)
    selection_col_names = ["Selection", "selection", "SELECTION", "Status", "status"]
    for col_name in selection_col_names:
        if col_name in match.columns:
            selection_value = row[col_name]
            if pd.notna(selection_value):
                selection_str = str(selection_value).strip().upper()
                run.is_valid = selection_str != "BAD"
                break
    
    # Obtener sensor_ids
    sensor_cols = [f"S{i}" for i in range(1, 21)]
    sensor_ids = [int(float(row[col])) for col in sensor_cols if col in row.index and pd.notna(row[col])]
    
    return sensor_ids


def calculate_run_offsets(run: 'Run', reference_channel: int, 
                          time_window: tuple = (20, 40),
                          config: dict = None,
                          set_number: int = None) -> None:
    """
    Calcula offsets de todos los canales respecto a un canal de referencia.
    
    Modifica run in-place:
        - run.offsets: {canal: offset_medio} canales válidos (1-12)
        - run.offset_errors: {canal: std_error} error de cada offset
        - run.omitted_channels: {canal: razón} canales omitidos
        - run.reference_channel: canal usado como referencia
    
    Args:
        run: Objeto Run con temperatures ya cargados (columnas: channel_1, channel_2, ...)
        reference_channel: Número de canal de referencia (1-14)
        time_window: (start_min, end_min) ventana temporal estable (default: 20-40 min)
        config: Diccionario de configuración (para threshold NaN)
        set_number: Número del set (no se usa, mantenido por compatibilidad)
    
    Cálculo:
        offset[canal] = mean(T_canal - T_referencia) en ventana estable
    
    Validaciones aplicadas:
        - SOLO calcula para los primeros 12 canales (ignora refs en canales 13-14)
        - Excluye canales con >max_nan_threshold NaN (default: 40 registros)
        - Ventana temporal 20-40 min (región estable en LN2)
        - NO calcula si run.is_valid == False
    
    Búsqueda automática de referencia:
        - Si referencia tiene >max_nan_threshold NaN, busca automáticamente otro canal
        - Intenta con cualquiera de los 12 canales del set
        - Actualiza run.reference_channel con el canal realmente usado
    
    Notes:
        Run es CIEGO - solo trabaja con números de canal (1-14).
        CalibSet mapea canal → Sensor usando índice: sensors[canal-1]
    """
    import pandas as pd
    
    if run.temperatures is None or run.temperatures.empty:
        return
    
    # Guardar la referencia usada
    run.reference_channel = reference_channel
    
    if not run.is_valid:
        print(f"[WARNING] Run {run.filename} marcado como inválido (BAD), no se calculan offsets")
        return
    
    # Verificar que el canal de referencia existe
    ref_col = f"channel_{reference_channel}"
    if ref_col not in run.temperatures.columns:
        print(f"[WARNING] Canal {reference_channel} no encontrado en {run.filename}")
        return
    
    # Ventana temporal estable
    if config is not None:
        time_window_cfg = config.get('run_options', {}).get('time_window', {})
        start_min = time_window_cfg.get('start_min', 20)
        end_min = time_window_cfg.get('end_min', 40)
    else:
        start_min, end_min = time_window
    
    t0 = run.timestamps.min() + pd.Timedelta(minutes=start_min)
    t1 = run.timestamps.min() + pd.Timedelta(minutes=end_min)
    
    # Usar máscara booleana en lugar de .loc[t0:t1] para evitar KeyError
    # cuando t0/t1 no existen exactamente en el índice
    mask = (run.temperatures.index >= t0) & (run.temperatures.index <= t1)
    window = run.temperatures[mask]
    
    if window.empty:
        print(f"[WARNING] Ventana [{start_min}-{end_min}min] vacía en {run.filename}")
        return
    
    # Calcular offsets respecto al canal de referencia
    ref_col = f"channel_{reference_channel}"
    if ref_col not in window.columns:
        print(f"[WARNING] Columna {ref_col} no encontrada en {run.filename}")
        return
    
    ref_temps = window[ref_col]
    
    # Obtener threshold de NaN desde config
    max_nan_threshold = 40  # Default: 40 registros con NaN
    max_nan_percentage = 0.90  # Default: 90% de NaN permitidos
    
    if config is not None:
        run_opts = config.get('run_options', {})
        max_nan_threshold = run_opts.get('max_nan_threshold', 40)
        max_nan_percentage = run_opts.get('max_nan_percentage', 0.90)
    
    # Calcular threshold dinámico basado en tamaño de ventana
    window_size = len(window)
    dynamic_threshold = int(window_size * max_nan_percentage)
    # Usar el más permisivo de los dos
    effective_threshold = max(max_nan_threshold, dynamic_threshold)
    
    # Verificar que la referencia tenga pocos NaN
    ref_nan_count = ref_temps.isna().sum()
    if ref_nan_count > effective_threshold:
        print(f"[WARNING] Referencia original canal {reference_channel} tiene {ref_nan_count} NaN (>{effective_threshold})")
        
        # Buscar referencia alternativa entre los primeros 12 canales
        alternative_channel = None
        for channel_num in range(1, 13):  # Canales 1-12
            if channel_num == reference_channel:
                continue
            
            channel_col = f"channel_{channel_num}"
            if channel_col in window.columns:
                channel_nan_count = window[channel_col].isna().sum()
                if channel_nan_count <= effective_threshold:
                    alternative_channel = channel_num
                    ref_col = channel_col
                    ref_temps = window[ref_col]
                    print(f"  [OK] Referencia alternativa: canal {alternative_channel} ({channel_nan_count} NaN)")
                    break
        
        if alternative_channel is None:
            print(f"  [FAIL] No se encontró referencia alternativa válida, no se calculan offsets")
            return
        else:
            reference_channel = alternative_channel  # Actualizar para el resto del cálculo
            run.reference_channel = reference_channel  # Actualizar en el objeto Run
    
    # Solo calcular offsets para los primeros 12 canales (ignorar refs en canales 13-14)
    for channel_num in range(1, 13):  # Canales 1-12
        channel_col = f"channel_{channel_num}"
        if channel_col in window.columns:
            channel_temps = window[channel_col]
            
            # Verificar número de NaN en el canal (usa mismo threshold que referencia)
            nan_count = channel_temps.isna().sum()
            
            if nan_count > effective_threshold:
                run.omitted_channels[channel_num] = f"defectuoso ({nan_count} NaN > {effective_threshold})"
                print(f"   [WARNING] Canal {channel_num}: {nan_count} NaN (>{effective_threshold}), omitido como defectuoso")
                continue
            
            # Calcular offset y su error (std del offset en la ventana)
            differences = (channel_temps - ref_temps).dropna()
            
            if len(differences) > 0:
                offset = differences.mean()
                offset_error = differences.std(ddof=1) if len(differences) > 1 else 0.0
                
                # Verificar que el offset no sea NaN
                if pd.notna(offset):
                    run.offsets[channel_num] = offset
                    run.offset_errors[channel_num] = offset_error
                else:
                    print(f"   [WARNING] Canal {channel_num}: offset = NaN, omitido")
            else:
                print(f"   [WARNING] Canal {channel_num}: sin datos válidos, omitido")


def process_run_complete(filename: str, logfile, config: dict, 
                        set_number: int, reference_channel: int,
                        time_window: tuple = (20, 40),
                        exclude_keywords: list = None) -> 'Run':
    """
    Procesa un run COMPLETO con todas las validaciones automáticas.
    
    Esta es la función de alto nivel que debe usarse para procesar runs.
    Aplica TODAS las validaciones necesarias:
    
    Args:
        filename: Nombre del archivo del run
        logfile: DataFrame con LogFile.csv
        config: Diccionario de configuración
        set_number: Número del set de calibración
        reference_channel: Número de canal de referencia (1-14) para calcular offsets
        time_window: (start_min, end_min) ventana temporal (default: 20-40 min)
        exclude_keywords: Keywords a excluir (default: ['pre', 'st', 'lar'])
    
    Returns:
        Run: Objeto Run procesado con offsets por canal (o vacío si inválido)
    
    Validaciones aplicadas:
        1. [OK] Keywords excluidas ('pre', 'st', 'lar')
        2. [OK] Selection != 'BAD' en logfile (run.is_valid)
        3. [OK] Ventana temporal 20-40 min por defecto
        4. [OK] Solo primeros 12 canales (excluye refs en canales 13-14)
        5. [OK] Excluye canales con >max_nan_threshold NaN (default: 40 registros)
        6. [OK] Detecta canales defectuosos automáticamente
        7. [OK] Búsqueda automática de referencia alternativa si la original tiene muchos NaN
    
    Examples:
        >>> run = process_run_complete(
        ...     '20220531_ln2_r48176_r48177_48060_48479_7',
        ...     logfile, config, set_number=3, reference_channel=1
        ... )
        >>> if run.is_valid and run.offsets:
        ...     print(f"Run válido con {len(run.offsets)} offsets")
    
    Notes:
        - Run es CIEGO: trabaja con canales (1-14), no sensor IDs
        - Si el run es inválido, se retorna con offsets vacíos
        - El CalibSet traduce offsets de canal → sensor usando sensors[canal-1]
    """
    try:
        from ..run import Run
    except ImportError:
        from run import Run
    
    # 1. Validar keywords
    from .filtering import should_exclude_run
    if should_exclude_run(filename, exclude_keywords):
        print(f"[WARNING] Run '{filename}' excluido por keywords")
        run = Run(filename)
        run.is_valid = False
        return run
    
    # 2. Cargar archivo
    run = load_run_from_file(filename, config)
    
    # 3. Obtener is_valid desde logfile (Run NO se entera de sensor IDs)
    map_sensor_ids_to_run(run, logfile, config)  # Solo marca is_valid, no modifica run
    
    # 4. Si es inválido, retornar sin calcular offsets
    if not run.is_valid:
        print(f"[WARNING] Run '{filename}' marcado como BAD en logfile")
        return run
    
    # 5. Calcular offsets entre canales
    calculate_run_offsets(
        run, 
        reference_channel=reference_channel,
        time_window=time_window,
        config=config,
        set_number=set_number
    )
    
    return run
