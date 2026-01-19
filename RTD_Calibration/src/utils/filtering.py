"""
Utilidades para filtrado y validación de runs.

Funciones:
- should_exclude_run(): Detecta keywords de exclusión
- filter_valid_runs(): Filtra runs válidos de un set
- get_discarded_sensors(): Obtiene sensores descartados de un set
"""


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
        >>> valid_runs = filter_valid_runs(logfile, set_number=3)
        >>> print(f"Set 3 tiene {len(valid_runs)} runs válidos")
    
    Notes:
        - Usa should_exclude_run() para detectar keywords
        - Selection='BAD' indica runs con problemas
        - Devuelve lista vacía si no hay runs válidos
    """
    # Función auxiliar para convertir set numbers
    def get_set_number(x):
        try:
            # Reemplazar comas por puntos (formato europeo)
            return float(str(x).replace(',', '.'))
        except (ValueError, TypeError):
            return None
    
    # Crear columna temporal con set number
    logfile_temp = logfile.copy()
    logfile_temp['SetNum'] = logfile_temp['CalibSetNumber'].apply(get_set_number)
    
    # Filtrar por set
    set_df = logfile_temp[logfile_temp['SetNum'] == float(set_number)]
    
    # Filtrar por Selection != 'BAD'
    valid_df = set_df[set_df['Selection'] != 'BAD']
    
    # Filtrar por keywords
    valid_filenames = []
    for filename in valid_df['Filename'].values:
        if not should_exclude_run(filename, exclude_keywords):
            valid_filenames.append(filename)
    
    return valid_filenames


def get_discarded_sensors(set_number: int, config: dict) -> list:
    """
    Obtiene la lista de sensores descartados de un set.
    
    Args:
        set_number: Número del set
        config: Diccionario de configuración
    
    Returns:
        list: Lista de sensor IDs descartados ([] si ninguno)
    
    Examples:
        >>> discarded = get_discarded_sensors(3, config)
        >>> print(f"Set 3: {discarded}")  # [48205, 48478]
    
    Notes:
        - Lee desde config.sensors.sets[N].discarded
        - Retorna lista vacía si no hay descartados
        - Estos sensores se excluyen automáticamente en calculate_run_offsets
    """
    try:
        sets_dict = config.get('sensors', {}).get('sets', {})
        
        # Buscar el set (puede estar como '3.0', '3', o 3.0)
        set_config = None
        for key in [f'{set_number}.0', str(set_number), float(set_number)]:
            if key in sets_dict:
                set_config = sets_dict[key]
                break
        
        if set_config is None:
            return []
        
        # Obtener lista de descartados
        discarded = set_config.get('discarded', [])
        
        return discarded if discarded else []
        
    except (KeyError, TypeError):
        return []
