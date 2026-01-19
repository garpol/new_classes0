"""
Utilidades matemáticas para cálculos de calibración.

Funciones:
- propagate_error(): Propagación de errores
- ensure_numeric(): Conversión segura a numérico
"""
import math
from typing import Union


def propagate_error(*errors: float) -> float:
    """
    Calcula la propagación de errores (suma cuadrática).
    
    Args:
        *errors: Errores individuales a propagar
    
    Returns:
        float: Error propagado (sqrt(sum(e^2)))
    
    Examples:
        >>> error = propagate_error(0.1, 0.2, 0.15)
        >>> print(f"{error:.3f}")  # 0.277
    
    Formula:
        σ_total = √(σ₁² + σ₂² + ... + σₙ²)
    
    Notes:
        - Se usa para combinar errores independientes
        - Asume que los errores no están correlacionados
        - Devuelve 0 si no hay errores
    """
    if not errors:
        return 0.0
    
    return math.sqrt(sum(e**2 for e in errors if e is not None))


def ensure_numeric(value, default=0.0):
    """
    Convierte un valor a numérico de forma segura.
    
    Args:
        value: Valor a convertir (puede ser str, float, int, etc.)
        default: Valor por defecto si la conversión falla
    
    Returns:
        float: Valor numérico o default
    
    Examples:
        >>> ensure_numeric("3,14", 0.0)  # 3.14 (reemplaza coma)
        >>> ensure_numeric("invalid", 0.0)  # 0.0
        >>> ensure_numeric(None, -999.0)  # -999.0
    
    Notes:
        - Reemplaza comas por puntos (formato europeo)
        - Retorna default si el valor no es convertible
        - Útil para leer datos de CSV con formato mixto
    """
    if value is None:
        return default
    
    try:
        # Si ya es número, devolverlo
        if isinstance(value, (int, float)):
            return float(value)
        
        # Si es string, intentar conversión
        if isinstance(value, str):
            # Reemplazar coma por punto (formato europeo)
            value = value.replace(',', '.')
            return float(value)
        
        # Intentar conversión directa
        return float(value)
        
    except (ValueError, TypeError):
        return default
