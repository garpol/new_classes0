"""
Utilidades para configuración y validación.

Funciones:
- load_config(): Carga config.yml
- validate_sensor_in_set(): Valida sensor en set
"""
import yaml
from pathlib import Path
from typing import Union


def load_config(config_path: Union[str, Path, None] = None) -> dict:
    """
    Carga el archivo de configuración YAML.
    
    Args:
        config_path: Ruta al archivo config.yml (opcional)
    
    Returns:
        dict: Configuración completa
    
    Examples:
        >>> config = load_config()
        >>> sets = config['sensors']['sets']
    """
    if config_path is None:
        # Asumir que estamos en src/ o notebooks/
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def validate_sensor_in_set(sensor_id: int, set_id: Union[int, float], 
                          config: dict) -> bool:
    """
    Valida si un sensor pertenece a un set específico.
    
    Args:
        sensor_id: ID del sensor a validar
        set_id: Número del set (puede ser float como 3.0)
        config: Diccionario de configuración
    
    Returns:
        bool: True si el sensor pertenece al set
    
    Examples:
        >>> config = load_config()
        >>> is_valid = validate_sensor_in_set(48060, 3, config)
        >>> print(is_valid)  # True
    """
    try:
        # Intentar con diferentes formatos de key
        sets_dict = config.get('sensors', {}).get('sets', {})
        
        # Buscar el set (puede estar como '3.0', '3', o 3.0)
        set_config = None
        for key in [f'{set_id}.0', str(set_id), float(set_id), int(set_id)]:
            if key in sets_dict:
                set_config = sets_dict[key]
                break
        
        if set_config is None:
            return False
        
        # Obtener lista de sensores del set
        sensor_list = set_config.get('sensors', [])
        
        return sensor_id in sensor_list
        
    except (KeyError, TypeError):
        return False
