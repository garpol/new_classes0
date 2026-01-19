"""
Utilidades compartidas para el proyecto RTD_Calibration.

Funciones helper reutilizables entre set.py, run.py, tree.py.
"""
import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Union, Optional, List, Dict


def load_config(config_path: Union[str, Path, None] = None) -> dict:
    """
    Carga el archivo de configuración config.yml.
    
    Args:
        config_path: Ruta al archivo config.yml. Si es None, busca en 
                     RTD_Calibration/config/config.yml
    
    Returns:
        dict: Diccionario con la configuración. Diccionario vacío si falla.
    
    Examples:
        >>> config = load_config()
        >>> config = load_config('/custom/path/config.yml')
    """
    # Si no se proporciona path, usar ruta por defecto
    if config_path is None:
        # Obtener directorio del módulo actual (RTD_Calibration/src/)
        current_dir = Path(__file__).resolve().parent
        config_path = current_dir.parent / "config" / "config.yml"
    else:
        config_path = Path(config_path)
    
    # Verificar que existe
    if not config_path.exists():
        print(f"Advertencia: No se encontró config en {config_path}, usando valores por defecto")
        return {}
    
    # Cargar YAML
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config if config is not None else {}
    except (FileNotFoundError, yaml.YAMLError, OSError) as e:
        print(f"Advertencia: Error al cargar configuración desde {config_path}: {e}")
        return {}


def propagate_error(*errors: float) -> float:
    """
    Propaga errores independientes usando la regla de suma en cuadratura (RSS).
    
    Calcula: sqrt(error1² + error2² + ... + errorN²)
    
    Args:
        *errors: Errores individuales (floats). Se ignoran None y NaN.
    
    Returns:
        float: Error propagado (raíz de la suma de cuadrados).
    
    Examples:
        >>> propagate_error(0.1, 0.2)
        0.2236067977499790
        >>> propagate_error(0.3, 0.4, 0.5)
        0.7071067811865476
        >>> propagate_error(0.1, None, 0.2)  # Ignora None
        0.2236067977499790
    
    Notes:
        Esta función asume errores independientes y utiliza la fórmula estándar
        de propagación de incertidumbres para suma/resta:
        δf = sqrt((δx₁)² + (δx₂)² + ... + (δxₙ)²)
    """
    # Filtrar None y NaN
    valid_errors = [e for e in errors if e is not None and not np.isnan(e)]
    
    if not valid_errors:
        return 0.0
    
    # Suma de cuadrados
    sum_sq = sum(e**2 for e in valid_errors)
    
    return np.sqrt(sum_sq)


def validate_sensor_in_set(sensor_id: int, set_id: Union[int, float], 
                          config: dict) -> bool:
    """
    Verifica si un sensor pertenece a un set de calibración.
    
    Args:
        sensor_id: ID del sensor RTD (ej: 48176)
        set_id: Número del set de calibración (ej: 3, 39, 57)
        config: Diccionario de configuración con estructura 'sets'
    
    Returns:
        bool: True si el sensor pertenece al set, False en caso contrario
    
    Examples:
        >>> config = load_config()
        >>> validate_sensor_in_set(48176, 3, config)
        True
        >>> validate_sensor_in_set(99999, 3, config)
        False
    """
    try:
        # Obtener sensores del set desde config
        sets_config = config.get('sets', {})
        set_info = sets_config.get(str(set_id), {})
        
        # Buscar en 'sensors' o 'raised_sensors'
        sensors = set_info.get('sensors', [])
        raised = set_info.get('raised_sensors', [])
        
        all_sensors = sensors + raised
        
        return int(sensor_id) in [int(s) for s in all_sensors]
        
    except (KeyError, ValueError, TypeError):
        return False


def ensure_numeric(value, default=0.0):
    """
    Convierte un valor a float, retornando default si falla.
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si la conversión falla
    
    Returns:
        float: Valor convertido o default
    
    Examples:
        >>> ensure_numeric("3.14")
        3.14
        >>> ensure_numeric("invalid", default=0.0)
        0.0
        >>> ensure_numeric(None, default=-1.0)
        -1.0
    """
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def get_run_metadata(filename: str, logfile) -> dict:
    """
    Extrae metadata completa de un run desde el logfile.
    
    Args:
        filename: Nombre del archivo de calibración (sin extensión)
        logfile: DataFrame con la información del LogFile.csv
    
    Returns:
        dict: Diccionario con metadata del run:
            - set_number: Número del set de calibración
            - date: Fecha del experimento
            - liquid_media: Medio líquido usado (LN2, etc)
            - type: Tipo de calibración (Cal, Pre)
            - selection: Estado de selección (BAD, etc)
            - ref1_id, ref2_id: IDs de sensores de referencia
            - ref1_chan, ref2_chan: Canales de los sensores de referencia
            - board: Placa de adquisición usada
            - n_run: Número de run
            - sampling_rate: Tasa de muestreo
            - comments: Comentarios del experimento
            - all_sensors: Lista de todos los sensores en el run (S1-S20)
    
    Examples:
        >>> from logfile import Logfile
        >>> logfile = Logfile('data/LogFile.csv').log_file
        >>> metadata = get_run_metadata('20220201_ln2_r48176_r48177_487178-48189_1', logfile)
        >>> print(metadata['set_number'])
        1
        >>> print(metadata['ref1_id'])
        48176
    
    Notes:
        - Retorna diccionario vacío si no se encuentra el run en el logfile
        - Los sensores (S1-S20) se retornan como lista sin NaN
        - Útil para futura expansión: tracking de sets, filtrado por medio, etc.
    """
    import pandas as pd
    
    # Buscar el run en el logfile
    run_row = logfile[logfile['Filename'] == filename]
    
    if run_row.empty:
        print(f"Advertencia: No se encontró '{filename}' en el logfile")
        return {}
    
    # Extraer primera fila (debería ser única)
    row = run_row.iloc[0]
    
    # Extraer sensores (S1-S20) que no sean NaN
    sensor_columns = [f'S{i}' for i in range(1, 21)]
    all_sensors = [
        int(row[col]) for col in sensor_columns 
        if col in row and pd.notna(row[col])
    ]
    
    # Construir diccionario de metadata
    metadata = {
        'set_number': int(row['CalibSetNumber']) if pd.notna(row.get('CalibSetNumber')) else None,
        'date': row.get('Date'),
        'liquid_media': row.get('Liquid Media'),
        'type': row.get('Type'),
        'selection': row.get('Selection'),
        'ref1_id': int(row['REF1_ID']) if pd.notna(row.get('REF1_ID')) else None,
        'ref2_id': int(row['REF2_ID']) if pd.notna(row.get('REF2_ID')) else None,
        'ref1_chan': row.get('REF1_CHAN'),
        'ref2_chan': row.get('REF2_CHAN'),
        'board': row.get('BOARD'),
        'n_run': int(row['N_Run']) if pd.notna(row.get('N_Run')) else None,
        'sampling_rate': int(row['SamplingRate']) if pd.notna(row.get('SamplingRate')) else None,
        'comments': row.get('Comments'),
        'general_comments': row.get('General Comments'),
        'all_sensors': all_sensors,
    }
    
    return metadata


# =============================================================================
# FUNCIONES PARA PROCESAMIENTO DE RUN
# =============================================================================

def should_exclude_run(filename: str, exclude_keywords: list = None) -> bool:
    """
    Determina si un run debe excluirse basándose en keywords en el filename.
    
    Args:
        filename: Nombre del archivo del run
        exclude_keywords: Lista de palabras clave a excluir (default: ['pre', 'st', 'lar'])
    
    Returns:
        bool: True si el run debe excluirse, False si es válido
    
    Examples:
        >>> should_exclude_run('20220201_ln2_r48176_r48177_48060_48479_1_pre')
        True
        >>> should_exclude_run('20220201_ln2_r48176_r48177_48060_48479_1')
        False
        >>> should_exclude_run('test_lar_file', exclude_keywords=['lar', 'test'])
        True
    
    Notes:
        Las keywords comunes a excluir son:
        - 'pre': pre-calibraciones (no usar)
        - 'st': stabilization tests (no usar)
        - 'lar': archivos de prueba o descartados
    """
    if exclude_keywords is None:
        exclude_keywords = ['pre', 'st', 'lar']
    
    filename_lower = filename.lower()
    return any(keyword in filename_lower for keyword in exclude_keywords)


def filter_valid_runs(logfile, set_number: int, exclude_keywords: list = None) -> list:
    """
    Filtra runs válidos de un set desde el logfile.
    
    Args:
        logfile: DataFrame con LogFile.csv
        set_number: Número del set de calibración
        exclude_keywords: Lista de keywords a excluir (default: ['pre', 'st', 'lar'])
    
    Returns:
        list: Lista de filenames válidos para procesar
    
    Criterios de filtrado:
        1. Pertenece al set indicado
        2. Selection != 'BAD' en logfile
        3. No contiene keywords excluidas en el filename
    
    Examples:
        >>> import pandas as pd
        >>> logfile = pd.read_csv('data/LogFile.csv')
        >>> valid_files = filter_valid_runs(logfile, set_number=3)
        >>> print(f"Set 3 tiene {len(valid_files)} runs válidos")
    """
    import pandas as pd
    
    if exclude_keywords is None:
        exclude_keywords = ['pre', 'st', 'lar']
    
    # Función helper para convertir set number
    def get_set_number(x):
        """Convierte CalibSetNumber a float, retorna None si no es válido"""
        try:
            return float(str(x).replace(',', '.'))
        except (ValueError, TypeError):
            return None
    
    # Filtrar por set
    logfile_temp = logfile.copy()
    logfile_temp['SetNum'] = logfile_temp['CalibSetNumber'].apply(get_set_number)
    
    set_df = logfile_temp[
        (logfile_temp['SetNum'] == float(set_number)) & 
        (logfile_temp['Selection'] != 'BAD')
    ]
    
    # Excluir keywords
    valid_filenames = []
    for filename in set_df['Filename'].values:
        if not should_exclude_run(filename, exclude_keywords):
            valid_filenames.append(filename)
    
    return valid_filenames


def get_discarded_sensors(set_number: int, config: dict) -> list:
    """
    Obtiene lista de sensores descartados para un set.
    
    Args:
        set_number: Número del set de calibración
        config: Diccionario de configuración
    
    Returns:
        list: Lista de IDs de sensores descartados
    
    Examples:
        >>> config = load_config()
        >>> discarded = get_discarded_sensors(3, config)
        >>> print(f"Set 3 tiene {len(discarded)} sensores descartados: {discarded}")
    
    Notes:
        Los sensores descartados son canales que:
        - Están físicamente defectuosos
        - Tienen lecturas inconsistentes
        - No deben usarse para calibración
        
        Estos sensores se marcan como NaN en las matrices de constantes.
    """
    sets_dict = config.get('sensors', {}).get('sets', {})
    
    # Intentar con múltiples formatos de clave
    set_config = (sets_dict.get(f'{set_number}.0') or 
                  sets_dict.get(str(set_number)) or 
                  sets_dict.get(float(set_number)))
    
    if set_config is None:
        return []
    
    return set_config.get('discarded', [])


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
    import glob
    import pandas as pd
    try:
        from .run import Run
    except ImportError:
        from run import Run
    
    run = Run(filename)
    
    # Buscar archivo
    repo_root = Path(__file__).parents[1]
    search_path = repo_root / "data" / "temperature_files"
    
    matches = glob.glob(str(search_path / "**" / f"{filename}.txt"), recursive=True)
    if not matches:
        print(f"⚠️  No se encontró {filename}.txt")
        return run
    
    filepath = matches[0]
    
    # Leer archivo
    df = pd.read_csv(filepath, sep="\t", header=None)
    
    # Nombrar columnas
    cols = ["Date", "Time"] + [f"channel_{i}" for i in range(1, 15)]
    df.columns = cols + list(df.columns[len(cols):])
    
    # Parsear fechas
    df["datetime"] = pd.to_datetime(
        df["Date"] + " " + df["Time"], 
        errors="coerce",
        format="%m/%d/%Y %I:%M:%S %p"
    )
    if df["datetime"].isna().all():
        df["datetime"] = pd.to_datetime(
            df["Date"] + " " + df["Time"], 
            errors="coerce"
        )
    
    # Extraer solo canales de temperatura
    temp_cols = [c for c in df.columns if c.startswith("channel_")]
    temps = df[temp_cols].copy()
    temps.index = df["datetime"]
    
    # Filtrar valores inválidos
    run_opts = config.get('run_options', {})
    temp_range = run_opts.get('valid_temp_range', {})
    temp_min = temp_range.get('min', 60)
    temp_max = temp_range.get('max', 350)
    
    temps = temps.mask((temps < temp_min) | (temps > temp_max))
    temps = temps.dropna(how="all")
    
    # Guardar en Run
    run.timestamps = temps.index
    run.temperatures = temps
    
    return run


def map_sensor_ids_to_run(run: 'Run', logfile, config: dict) -> None:
    """
    Mapea IDs de sensores a un Run usando logfile.
    
    Modifica run in-place:
    - run.sensor_ids: lista de IDs de sensores
    - run.temperatures: columnas renombradas de channel_X a sensor_id
    - run.is_valid: False si 'BAD' en logfile
    
    Args:
        run: Objeto Run a modificar
        logfile: DataFrame con LogFile.csv
        config: Diccionario de configuración
    """
    import pandas as pd
    
    # Buscar el run en el logfile
    match = logfile[logfile["Filename"] == run.filename]
    if match.empty:
        print(f"⚠️  '{run.filename}' no encontrado en logfile")
        return
    
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
    run.sensor_ids = sensor_ids
    
    # Renombrar columnas en temperatures
    if run.temperatures is not None:
        channels = [f"channel_{i}" for i in range(1, len(sensor_ids) + 1)]
        sensor_mapping = dict(zip(channels, [str(sid) for sid in sensor_ids]))
        run.temperatures = run.temperatures.rename(columns=sensor_mapping)


def calculate_run_offsets(run: 'Run', reference_id: int, 
                          time_window: tuple = (20, 40),
                          config: dict = None,
                          set_number: int = None) -> None:
    """
    Calcula offsets de todos los sensores respecto a una referencia.
    
    Modifica run in-place:
        - run.offsets: {sensor_id: offset_medio} solo sensores válidos
        - run.offset_errors: {sensor_id: std_error} error de cada offset
        - run.omitted_sensors: {sensor_id: razón} sensores omitidos
        - run.reference_id: sensor usado como referencia
    
    Args:
        run: Objeto Run con temperatures ya cargados
        reference_id: ID del sensor de referencia
        time_window: (start_min, end_min) ventana temporal estable (default: 20-40 min)
        config: Diccionario de configuración (para threshold NaN)
        set_number: Número del set (no se usa, mantenido por compatibilidad)
    
    Cálculo:
        offset[sensor] = mean(T_sensor - T_reference) en ventana estable
    
    Validaciones aplicadas:
        - SOLO calcula para los primeros 12 sensores (ignora refs en canales 13-14)
        - Excluye sensores con >max_nan_threshold NaN (default: 40 registros)
        - Excluye canales defectuosos detectados automáticamente
        - Ventana temporal 20-40 min (región estable en LN2)
        - NO calcula si run.is_valid == False
        - **NO excluye sensores descartados** - eso es responsabilidad de Tree
    
    Búsqueda automática de referencia:
        - Si referencia tiene >max_nan_threshold NaN, busca automáticamente otra
        - Intenta con cualquiera de los 12 sensores del set
        - Actualiza run.reference_id con la referencia realmente usada
    
    Notes:
        max_nan_threshold se obtiene de config.run_options.max_nan_threshold (default: 40)
        Es un número ABSOLUTO de registros NaN, no un porcentaje.
        Si un sensor tiene >40 NaN en la ventana [20-40min], se considera defectuoso.
        Los sensores descartados (config.discarded) NO son filtrados aquí.
        Tree será quien decida excluir sensores descartados al propagar offsets.
    """
    import pandas as pd
    
    if run.temperatures is None or run.temperatures.empty:
        return
    
    if not run.is_valid:
        print(f"⚠️  Run {run.filename} marcado como inválido (BAD), no se calculan offsets")
        return
    
    if reference_id not in run.sensor_ids:
        print(f"⚠️  Referencia {reference_id} no está en {run.filename}")
        return
    
    # Guardar referencia usada
    run.reference_id = reference_id
    
    # Ventana temporal estable
    start_min, end_min = time_window
    t0 = run.timestamps.min() + pd.Timedelta(minutes=start_min)
    t1 = run.timestamps.min() + pd.Timedelta(minutes=end_min)
    
    # Usar máscara booleana en lugar de .loc[t0:t1] para evitar KeyError
    # cuando t0/t1 no existen exactamente en el índice
    mask = (run.temperatures.index >= t0) & (run.temperatures.index <= t1)
    window = run.temperatures[mask]
    
    if window.empty:
        print(f"⚠️  Ventana [{start_min}-{end_min}min] vacía en {run.filename}")
        return
    
    # Calcular offsets respecto a la referencia
    ref_col = str(reference_id)
    if ref_col not in window.columns:
        print(f"⚠️  Columna {ref_col} no encontrada en {run.filename}")
        return
    
    ref_temps = window[ref_col]
    
    # Obtener threshold de NaN desde config (número absoluto, no porcentaje)
    max_nan_threshold = 40  # Default: 40 registros con NaN
    if config is not None:
        max_nan_threshold = config.get('run_options', {}).get('max_nan_threshold', 40)
    
    # Verificar que la referencia tenga pocos NaN (cuenta absoluta)
    ref_nan_count = ref_temps.isna().sum()
    if ref_nan_count > max_nan_threshold:
        print(f"⚠️  Referencia original {reference_id} tiene {ref_nan_count} NaN (>{max_nan_threshold})")
        
        # Buscar referencia alternativa entre los primeros 12 sensores
        alternative_ref = None
        for sensor_id in run.sensor_ids[:12]:
            if sensor_id == reference_id:
                continue
            
            sensor_col = str(sensor_id)
            if sensor_col in window.columns:
                sensor_nan_count = window[sensor_col].isna().sum()
                if sensor_nan_count <= max_nan_threshold:
                    alternative_ref = sensor_id
                    ref_col = sensor_col
                    ref_temps = window[ref_col]
                    run.reference_id = alternative_ref
                    print(f"  ✓ Referencia alternativa: {alternative_ref} ({sensor_nan_count} NaN)")
                    break
        
        if alternative_ref is None:
            print(f"  ✗ No se encontró referencia alternativa válida, no se calculan offsets")
            return
        else:
            reference_id = alternative_ref  # Actualizar para el resto del cálculo
    
    # Solo calcular offsets para los primeros 12 sensores (ignorar refs en canales 13-14)
    for sensor_id in run.sensor_ids[:12]:
        sensor_col = str(sensor_id)
        if sensor_col in window.columns:
            sensor_temps = window[sensor_col]
            
            # Verificar número de NaN en el sensor (cuenta absoluta, no porcentaje)
            nan_count = sensor_temps.isna().sum()
            
            if nan_count > max_nan_threshold:
                run.omitted_sensors[sensor_id] = f"defectuoso ({nan_count} NaN > {max_nan_threshold})"
                print(f"   ⚠️  Sensor {sensor_id}: {nan_count} NaN (>{max_nan_threshold}), omitido como defectuoso")
                continue
            
            # Calcular offset y su error (std del offset en la ventana)
            differences = (sensor_temps - ref_temps).dropna()
            
            if len(differences) > 0:
                offset = differences.mean()
                offset_error = differences.std(ddof=1) if len(differences) > 1 else 0.0
                
                # Verificar que el offset no sea NaN
                if pd.notna(offset):
                    run.offsets[sensor_id] = offset
                    run.offset_errors[sensor_id] = offset_error
                else:
                    print(f"   ⚠️  Sensor {sensor_id}: offset = NaN, omitido")
            else:
                print(f"   ⚠️  Sensor {sensor_id}: sin datos válidos, omitido")


def process_run_complete(filename: str, logfile, config: dict, 
                        set_number: int, reference_id: int,
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
        reference_id: ID del sensor de referencia para calcular offsets
        time_window: (start_min, end_min) ventana temporal (default: 20-40 min)
        exclude_keywords: Keywords a excluir (default: ['pre', 'st', 'lar'])
    
    Returns:
        Run: Objeto Run procesado con offsets calculados (o vacío si inválido)
    
    Validaciones aplicadas:
        1. ✓ Keywords excluidas ('pre', 'st', 'lar')
        2. ✓ Selection != 'BAD' en logfile (run.is_valid)
        3. ✓ Ventana temporal 20-40 min por defecto
        4. ✓ Solo primeros 12 sensores (excluye refs en canales 13-14)
        5. ✓ Excluye sensores con >max_nan_threshold NaN (default: 40 registros)
        6. ✓ Detecta canales defectuosos automáticamente
        7. ✓ Búsqueda automática de referencia alternativa si la original tiene muchos NaN
        8. ✗ **NO excluye sensores descartados** - eso es responsabilidad de Tree
    
    Examples:
        >>> run = process_run_complete(
        ...     '20220201_ln2_r48176_r48177_48060_48479_1',
        ...     logfile, config, set_number=3, reference_id=48060
        ... )
        >>> if run.is_valid and run.offsets:
        ...     print(f"Run válido con {len(run.offsets)} offsets")
    
    Notes:
        - Si el run es inválido, se retorna con offsets vacíos
        - El Tree debe usar SOLO runs con is_valid=True y offsets no vacíos
        - Esta función centraliza todas las validaciones en un solo lugar
    """
    try:
        from .run import Run
    except ImportError:
        from run import Run
    
    # 1. Validar keywords
    if should_exclude_run(filename, exclude_keywords):
        print(f"⚠️  Run '{filename}' excluido por keywords")
        run = Run(filename)
        run.is_valid = False
        return run
    
    # 2. Cargar archivo
    run = load_run_from_file(filename, config)
    
    # 3. Mapear IDs y obtener is_valid desde logfile
    map_sensor_ids_to_run(run, logfile, config)
    
    # 4. Si es inválido, retornar sin calcular offsets
    if not run.is_valid:
        print(f"⚠️  Run '{filename}' marcado como BAD en logfile")
        return run
    
    # 5. Calcular offsets con todas las exclusiones
    calculate_run_offsets(
        run, 
        reference_id=reference_id,
        time_window=time_window,
        config=config,
        set_number=set_number
    )
    
    return run


def export_run_to_csv(run: 'Run', set_number: int = None, output_path: str = None) -> str:
    """
    Exporta un Run individual a CSV con offsets, errores y sensores omitidos.
    
    **CSV para clase Run**: Un run con todos sus offsets y errores individuales.
    
    Args:
        run: Objeto Run procesado
        set_number: Número del set (opcional, para metadata)
        output_path: Ruta del archivo CSV (opcional). Si None, usa run_<filename>.csv
    
    Returns:
        str: Ruta del archivo CSV generado
    
    Format CSV:
        set_number, filename, sensor_id, offset, offset_error, reference_id, omitted_reason
        
    Notes:
        - Una fila por sensor en el run
        - Sensores con offset válido: offset + offset_error
        - Sensores omitidos: offset=NaN, error=NaN, razón incluida
        - Para debugging de runs individuales
    
    Examples:
        >>> run = process_run_complete(...)
        >>> csv_path = export_run_to_csv(run, set_number=3)
        >>> print(f"Run exportado a {csv_path}")
    """
    import pandas as pd
    from pathlib import Path
    
    if output_path is None:
        output_path = f"run_{run.filename}.csv"
    
    # Crear lista de registros
    records = []
    
    # Agregar sensores con offsets válidos
    for sensor_id, offset in run.offsets.items():
        offset_error = run.offset_errors.get(sensor_id, 0.0)
        records.append({
            'set_number': set_number,
            'filename': run.filename,
            'sensor_id': sensor_id,
            'offset': offset,
            'offset_error': offset_error,
            'reference_id': run.reference_id,
            'omitted_reason': None
        })
    
    # Agregar sensores omitidos
    for sensor_id, reason in run.omitted_sensors.items():
        records.append({
            'set_number': set_number,
            'filename': run.filename,
            'sensor_id': sensor_id,
            'offset': None,
            'offset_error': None,
            'reference_id': run.reference_id,
            'omitted_reason': reason
        })
    
    # Crear DataFrame y exportar
    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    
    return output_path


def export_multiple_runs_to_csv(
    runs: list,
    set_number: int = None,
    output_path: str = None
) -> str:
    """
    Exporta múltiples runs a un CSV consolidado.
    
    **CSV para múltiples Runs**: Todos los runs de un set con offsets y errores individuales.
    
    Args:
        runs: Lista de objetos Run procesados
        set_number: Número del set (opcional, para metadata)
        output_path: Ruta del CSV de salida (opcional). Si None, usa runs_set_{N}.csv
    
    Returns:
        str: Ruta del archivo CSV generado
    
    CSV Format:
        set_number, filename, sensor_id, offset, offset_error, reference_id, omitted_reason
        
    Notes:
        - Concatena todos los runs en un solo CSV
        - Útil para comparar runs dentro de un mismo set
        - Para análisis de variabilidad entre runs
    
    Usage:
        >>> # Procesar runs del set 3
        >>> runs = []
        >>> for fname in filenames:
        ...     run = process_run_complete(fname, logfile, config, 3)
        ...     if run.is_valid and run.offsets:
        ...         runs.append(run)
        >>> 
        >>> csv_path = export_multiple_runs_to_csv(runs, set_number=3)
        >>> print(f"Exportados {len(runs)} runs a {csv_path}")
    """
    import pandas as pd
    from pathlib import Path
    
    if output_path is None:
        set_suffix = f"_set_{set_number}" if set_number else ""
        output_path = f"runs{set_suffix}.csv"
    
    all_records = []
    
    for run in runs:
        # Agregar offsets válidos
        for sensor_id, offset in run.offsets.items():
            offset_error = run.offset_errors.get(sensor_id, 0.0)
            all_records.append({
                'set_number': set_number,
                'filename': run.filename,
                'sensor_id': sensor_id,
                'offset': offset,
                'offset_error': offset_error,
                'reference_id': run.reference_id,
                'omitted_reason': None
            })
        
        # Agregar sensores omitidos
        for sensor_id, reason in run.omitted_sensors.items():
            all_records.append({
                'set_number': set_number,
                'filename': run.filename,
                'sensor_id': sensor_id,
                'offset': None,
                'offset_error': None,
                'reference_id': run.reference_id,
                'omitted_reason': reason
            })
    
    # Crear DataFrame y exportar
    df = pd.DataFrame(all_records)
    df.to_csv(output_path, index=False)
    
    print(f"✓ Exportados {len(runs)} runs → {output_path}")
    print(f"  Total registros: {len(df)}")
    print(f"  Offsets válidos: {df['offset'].notna().sum()}")
    print(f"  Sensores omitidos: {df['offset'].isna().sum()}")
    
    return output_path


# =============================================================================
# CalibSet Processing Functions
# =============================================================================

def create_calibration_set(
    set_number: Union[int, float],
    logfile: pd.DataFrame,
    config: dict,
    use_cache: bool = False,
    cache_path: Optional[str] = None
):
    """
    Crea y rellena un CalibSet completo con sensors, runs y estadísticas.
    
    Esta función:
    1. Crea un CalibSet vacío
    2. Crea 12 instancias Sensor (del config) y las agrega al Set
    3. Procesa todos los runs válidos del set
    4. Calcula mean_offsets y std_offsets
    
    Args:
        set_number: Número del set (ej: 3.0, 21.0)
        logfile: DataFrame con LogFile.csv
        config: Diccionario de configuración
        use_cache: Si True, intenta cargar desde CSV en cache_path
        cache_path: Ruta al CSV de caché (opcional)
    
    Returns:
        CalibSet: Instancia completa con sensors, runs y estadísticas
    
    Example:
        >>> calib_set = create_calibration_set(
        >>>     set_number=3.0,
        >>>     logfile=logfile,
        >>>     config=config
        >>> )
        >>> print(calib_set)
        CalibSet(set=3.0, sensors=12, runs=4, offsets=10, ref=48060)
        >>> 
        >>> # Acceder a sensors
        >>> for sensor in calib_set.sensors:
        >>>     print(f"Sensor {sensor.id}")
    """
    try:
        from .calibset import CalibSet
        from .sensor import Sensor
    except ImportError:
        from calibset import CalibSet
        from sensor import Sensor
    
    # Convertir set_number a float
    set_number = float(set_number)
    
    # 1. Crear CalibSet vacío
    calib_set = CalibSet(set_number)
    
    # 2. Obtener configuración del set
    sets_config = config.get('sensors', {}).get('sets', {})
    
    # Intentar diferentes formatos de clave
    set_config = sets_config.get(set_number) or sets_config.get(str(set_number)) or sets_config.get(int(set_number))
    
    if not set_config:
        print(f"⚠️  No se encontró configuración para el set {set_number}")
        return calib_set
    
    # 3. Obtener sensor_ids del config (los 12 sensores del set)
    sensor_ids = set_config.get('sensors', [])
    
    if not sensor_ids:
        print(f"⚠️  Set {set_number} no tiene sensors definidos en config")
        return calib_set
    
    # 4. Crear instancias Sensor y agregarlas al Set
    for sensor_id in sensor_ids:
        sensor = Sensor(sensor_id)
        calib_set.sensors.add(sensor)
    
    print(f"✓ Set {set_number}: {len(calib_set.sensors)} sensores creados")
    
    # 5. Elegir sensor de referencia (primer sensor del set)
    reference_id = sensor_ids[0]
    calib_set.reference_id = reference_id
    
    print(f"  Referencia: {reference_id}")
    
    # 6. Obtener runs válidos del logfile
    valid_filenames = filter_valid_runs(logfile, set_number)
    
    if not valid_filenames:
        print(f"⚠️  Set {set_number} no tiene runs válidos")
        return calib_set
    
    print(f"  Procesando {len(valid_filenames)} runs válidos...")
    
    # 7. Procesar cada run y agregarlo a calib_set
    for filename in valid_filenames:
        run = process_run_complete(
            filename=filename,
            logfile=logfile,
            config=config,
            set_number=set_number,
            reference_id=reference_id,
            time_window=(20, 40)
        )
        
        # Solo agregar si es válido Y tiene offsets
        if run.is_valid and run.offsets:
            calib_set.runs.append(run)
    
    print(f"  ✓ {len(calib_set.runs)} runs válidos con offsets")
    
    # 8. Calcular estadísticas (mean_offsets, std_offsets)
    if calib_set.runs:
        n_sensors_with_offsets = calculate_set_statistics(calib_set)
        n_sensors_total = len(calib_set.sensors)
        
        if n_sensors_with_offsets < n_sensors_total:
            n_missing = n_sensors_total - n_sensors_with_offsets
            print(f"  ℹ️  {n_missing} sensores sin offsets (descartados o con NaN en todos los runs)")
        
        print(f"  ✓ Estadísticas calculadas: {n_sensors_with_offsets}/{n_sensors_total} sensores")
    else:
        print(f"  ⚠️  Sin runs válidos, no se calcularon estadísticas")
    
    return calib_set


def calculate_set_statistics(calib_set):
    """
    Calcula mean_offsets y std_offsets usando MEDIA PONDERADA por error.
    
    Esta función:
    1. Recopila offsets y errores de todos los runs por sensor
    2. Calcula media ponderada usando 1/error² como peso
    3. Calcula error propagado combinando errores de los runs
    4. Fuerza offset=0 y std=0 para el sensor de referencia
    
    Modifica calib_set in-place:
        - calib_set.mean_offsets: {sensor_id: weighted_mean}
        - calib_set.std_offsets: {sensor_id: propagated_error}
    
    Args:
        calib_set: Instancia CalibSet con runs procesados
    
    Returns:
        int: Número de sensores con offsets calculados
    
    Fórmulas:
        - Peso: w_i = 1 / σ_i²
        - Media ponderada: μ = Σ(w_i * x_i) / Σ(w_i)
        - Error propagado: σ = 1 / √(Σ(w_i))
    
    Notes:
        - Solo calcula para sensores que aparecen en AL MENOS UN run
        - Si un sensor tiene error=0 en algún run, usa peso=1.0 para ese run
        - Si todos los runs tienen error=0, usa media simple
        - Si un sensor aparece en 1 solo run, std = error de ese run
        - El sensor de referencia SIEMPRE tiene offset=0.0 y std=0.0
    
    Examples:
        >>> calib_set = CalibSet(3.0)
        >>> # ... agregar runs ...
        >>> n_sensors = calculate_set_statistics(calib_set)
        >>> print(f"Offsets calculados para {n_sensors} sensores")
    """
    if not calib_set.runs:
        return 0
    
    # Recopilar offsets y errores por sensor_id
    offsets_by_sensor = {}  # {sensor_id: [offset1, offset2, ...]}
    errors_by_sensor = {}   # {sensor_id: [error1, error2, ...]}
    
    for run in calib_set.runs:
        for sensor_id, offset in run.offsets.items():
            if sensor_id not in offsets_by_sensor:
                offsets_by_sensor[sensor_id] = []
                errors_by_sensor[sensor_id] = []
            
            offsets_by_sensor[sensor_id].append(offset)
            error = run.offset_errors.get(sensor_id, 0.0)
            errors_by_sensor[sensor_id].append(error)
    
    # Calcular media ponderada y error propagado
    for sensor_id in offsets_by_sensor.keys():
        offsets = np.array(offsets_by_sensor[sensor_id])
        errors = np.array(errors_by_sensor[sensor_id])
        
        # Si todos los errores son 0, usar media simple
        if np.all(errors == 0):
            calib_set.mean_offsets[sensor_id] = np.mean(offsets)
            calib_set.std_offsets[sensor_id] = 0.0
            continue
        
        # Reemplazar errores=0 con un valor pequeño para evitar división por 0
        errors_safe = np.where(errors == 0, 1e-10, errors)
        
        # Pesos: w_i = 1 / σ_i²
        weights = 1.0 / (errors_safe ** 2)
        
        # Media ponderada: μ = Σ(w_i * x_i) / Σ(w_i)
        weighted_mean = np.sum(weights * offsets) / np.sum(weights)
        
        # Error propagado: σ = 1 / √(Σ(w_i))
        propagated_error = 1.0 / np.sqrt(np.sum(weights))
        
        calib_set.mean_offsets[sensor_id] = weighted_mean
        calib_set.std_offsets[sensor_id] = propagated_error
    
    # Forzar referencia a offset=0, std=0 (si está presente)
    if calib_set.reference_id in calib_set.mean_offsets:
        calib_set.mean_offsets[calib_set.reference_id] = 0.0
        calib_set.std_offsets[calib_set.reference_id] = 0.0
    
    return len(calib_set.mean_offsets)


def create_multiple_calibsets(
    set_numbers: Union[List[Union[int, float]], str],
    logfile: pd.DataFrame,
    config: dict
) -> Dict[float, 'CalibSet']:
    """
    Crea múltiples CalibSets de una vez.
    
    Args:
        set_numbers: Lista de números de set o 'all' para todos
        logfile: DataFrame con LogFile.csv
        config: Diccionario de configuración
    
    Returns:
        Dict[float, CalibSet]: {set_number: calib_set}
    
    Example:
        >>> calibsets = create_multiple_calibsets(
        >>>     set_numbers=[3, 21, 25],
        >>>     logfile=logfile,
        >>>     config=config
        >>> )
        >>> print(f"{len(calibsets)} sets creados")
        >>> for set_num, calib_set in calibsets.items():
        >>>     print(calib_set)
    """
    try:
        from .calibset import CalibSet
    except ImportError:
        from calibset import CalibSet
    
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
            
            calib_set = create_calibration_set(
                set_number=set_num,
                logfile=logfile,
                config=config
            )
            
            if calib_set.runs and calib_set.mean_offsets:
                calibsets[float(set_num)] = calib_set
                success_count += 1
            else:
                print(f"  ⚠️  Set {set_num} sin datos válidos")
        
        except Exception as e:
            print(f"  ⚠️  Error en set {set_num}: {e}")
            continue
    
    print("\n" + "=" * 70)
    print(f"✓ COMPLETADO: {success_count}/{len(set_numbers)} CalibSets creados")
    print("=" * 70)
    
    return calibsets


def export_calibset_to_csv(
    calib_set,
    output_path: Optional[str] = None
) -> str:
    """
    Exporta un CalibSet a CSV con media ponderada y error propagado.
    
    **CSV para clase CalibSet**: Resultado final con media ponderada por error.
    
    Args:
        calib_set: Instancia CalibSet con mean_offsets y std_offsets calculados
        output_path: Ruta de salida (opcional, default: calibset_{N}.csv)
    
    Returns:
        str: Ruta del archivo CSV generado
    
    Formato CSV:
        set_number, sensor_id, mean_offset, std_offset, n_runs, reference_id
        
    Notes:
        - mean_offset: Media ponderada por 1/σ² de todos los runs
        - std_offset: Error propagado (1/√(Σw))
        - n_runs: Cantidad de runs válidos usados en el cálculo
        - Este es el resultado FINAL para cada sensor del set
    
    Example:
        >>> calib_set = create_calibration_set(3.0, logfile, config)
        >>> csv_path = export_calibset_to_csv(calib_set)
        >>> print(f"CalibSet 3 exportado: {csv_path}")
        >>> 
        >>> # Leer resultado
        >>> df = pd.read_csv(csv_path)
        >>> print(df[['sensor_id', 'mean_offset', 'std_offset']])
    """
    if not calib_set.mean_offsets:
        print(f"⚠️  CalibSet {calib_set.set_number} no tiene offsets para exportar")
        return ""
    
    # Ruta por defecto
    if output_path is None:
        repo_root = Path(__file__).parent.parent
        results_dir = repo_root / "data" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        output_path = results_dir / f"calibset_{int(calib_set.set_number)}.csv"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Crear DataFrame
    rows = []
    for sensor_id in sorted(calib_set.mean_offsets.keys()):
        rows.append({
            'set_number': calib_set.set_number,
            'sensor_id': sensor_id,
            'mean_offset': calib_set.mean_offsets[sensor_id],
            'std_offset': calib_set.std_offsets.get(sensor_id, 0.0),
            'n_runs': len(calib_set.runs),
            'reference_id': calib_set.reference_id
        })
    
    df = pd.DataFrame(rows)
    
    # Guardar CSV
    df.to_csv(output_path, index=False)
    
    print(f"✓ CalibSet {calib_set.set_number} exportado → {output_path}")
    print(f"  Sensores: {len(rows)}")
    print(f"  Runs usados: {len(calib_set.runs)}")
    
    return str(output_path)


def export_multiple_calibsets_to_csv(
    calib_sets: list,
    output_dir: Optional[str] = None
) -> dict:
    """
    Exporta múltiples CalibSets a CSV (uno por set).
    
    **CSV para múltiples CalibSets**: Medias ponderadas de varios sets.
    
    Args:
        calib_sets: Lista de objetos CalibSet
        output_dir: Directorio de salida (opcional, default: data/results/)
    
    Returns:
        dict: {set_number: csv_path} con rutas generadas
    
    Example:
        >>> # Crear varios calibsets
        >>> calib_sets = []
        >>> for set_num in [3, 21, 39]:
        ...     cs = create_calibration_set(set_num, logfile, config)
        ...     calib_sets.append(cs)
        >>> 
        >>> paths = export_multiple_calibsets_to_csv(calib_sets)
        >>> print(f"Exportados {len(paths)} calibsets")
    """
    if output_dir is None:
        repo_root = Path(__file__).parent.parent
        output_dir = repo_root / "data" / "results"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    exported_paths = {}
    
    print(f"Exportando {len(calib_sets)} CalibSets...")
    
    for calib_set in calib_sets:
        output_path = output_dir / f"calibset_{int(calib_set.set_number)}.csv"
        csv_path = export_calibset_to_csv(calib_set, str(output_path))
        
        if csv_path:
            exported_paths[calib_set.set_number] = csv_path
    
    print(f"\n✓ {len(exported_paths)} CalibSets exportados a {output_dir}")
    
    return exported_paths
