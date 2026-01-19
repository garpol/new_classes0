"""
Clase Run - Data class para almacenar datos de una única inmersión de calibración.

Responsabilidades:
- Almacenar filename
- Almacenar tiempos (timestamps)
- Almacenar temperaturas (DataFrame con sensor_ids como columnas)
- Almacenar offsets (solo sensores válidos: medias de diferencias respecto a referencia)
- Almacenar omitted_sensors (sensores excluidos con razón)
- Almacenar reference_id (sensor usado como referencia)
- Almacenar is_valid (False si es 'BAD' en logfile o tiene keywords 'pre'/'st'/'lar')

Todo el procesamiento está en utils
"""
import pandas as pd
from typing import Dict, Optional


class Run:
    """
    Data class: almacena datos de un experimento de calibración.
    
    Atributos:
        filename: str - Nombre del archivo (sin .txt)
        timestamps: pd.DatetimeIndex - Tiempos de medición
        temperatures: pd.DataFrame - Temperaturas con sensor_ids como columnas
        sensor_ids: list[int] - IDs de sensores presentes
        offsets: dict[int, float] - {sensor_id: offset} calculados por utils
        offset_errors: dict[int, float] - {sensor_id: std_error} error de cada offset
        is_valid: bool - False si marcado como 'BAD' en logfile o excluido por keywords
        omitted_sensors: dict[int, str] - {sensor_id: razón} sensores omitidos
        reference_id: int - ID del sensor usado como referencia para offsets
    
    Esta clase solo ALMACENA datos. Los cálculos se hacen en utils.py y se guardan aquí.
    
    Ejemplo de uso:
        >>> run = utils.process_run_complete(filename, logfile, config, set_number, reference_id)
        >>> if run.is_valid and run.offsets:
        >>>     print(f"{run.filename}: {len(run.offsets)} offsets válidos")
    """
    
    def __init__(self, filename: str) -> None:
        """
        Crea un Run vacío.
        
        Args:
            filename: Nombre del archivo (sin .txt)
        """
        self.filename: str = filename
        
        # Datos raw del archivo
        self.timestamps: Optional[pd.DatetimeIndex] = None #juntar con el siguiente df 
        self.temperatures: Optional[pd.DataFrame] = None  # Columnas = sensor_ids
        self.sensor_ids: list[int] = [] #un set, no los 'ids'/mapping 
        
        # Resultados de procesamiento (calculados por utils)
        self.offsets: Dict[int, float] = {}  # {sensor_id: offset} solo sensores válidos, es una utilidad para almacenar los offsets y no tener q hacer los cálculos cada vez, pero realmente lo hará el tree.
        self.offset_errors: Dict[int, float] = {}  # {sensor_id: std_error} error del offset
        self.omitted_sensors: Dict[int, str] = {}  # {sensor_id: razón} sensores omitidos, cambiar id por sensor
        self.reference_id: Optional[int] = None  # Sensor usado como referencia, obligatorio, list[int]
        self.is_valid: bool = True  # False si 'BAD' en logfile o excluido
    
    def __repr__(self) -> str:
        """
        Representación del objeto.
        
        Ejemplo:
            >>> run = Run('20220531_ln2_r48176_r48177_48060_48479_7')
            >>> print(run)
            Run('20220531_ln2_r48176_r48177_48060_48479_7', valid=True, offsets=10, omitted=2)
        """
        return f"Run('{self.filename}', valid={self.is_valid}, offsets={len(self.offsets)}, omitted={len(self.omitted_sensors)})"



