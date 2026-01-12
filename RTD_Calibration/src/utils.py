"""
Utilidades compartidas para el proyecto RTD_Calibration.

Funciones helper reutilizables entre set.py, run.py, tree.py.
"""
import yaml
import numpy as np
from pathlib import Path
from typing import Union


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
