"""
Clase Run - Data class CIEGA para almacenar datos de una única inmersión.

Responsabilidades:
- Almacenar filename
- Almacenar tiempos (timestamps)
- Almacenar temperaturas (DataFrame con channel_1 a channel_14)
- Almacenar offsets entre canales (respecto a un canal de referencia)
- Almacenar canales omitidos
- Almacenar is_valid (False si es 'BAD' en logfile)

Run es CIEGO: no sabe los sensor IDs, solo trabaja con números de canal (1-14).
El mapping canal → sensor se maneja en CalibSet.
Todo el procesamiento está en utils.
"""
import pandas as pd
from typing import Dict, Optional


class Run:
    """
    Data class CIEGA: almacena datos de un experimento usando solo números de canal.
    
    Atributos:
        filename: str - Nombre del archivo (sin .txt)
        timestamps: pd.DatetimeIndex - Tiempos de medición
        temperatures: pd.DataFrame - Temperaturas con columnas channel_1 a channel_14
        reference_channel: int - Número de canal usado como referencia (1-14)
        offsets: dict[int, float] - {canal: offset} para canales válidos (1-14)
        offset_errors: dict[int, float] - {canal: error} error de cada offset
        omitted_channels: dict[int, str] - {canal: razón} canales omitidos
        is_valid: bool - False si marcado como 'BAD' en logfile
    
    Esta clase solo ALMACENA datos. Los cálculos se hacen en utils.py.
    Run NO conoce sensor IDs - solo trabaja con canales (1-14).
    """
    
    def __init__(self, filename: str) -> None:
        """
        Crea un Run vacío. Argumentos: filename: Nombre del archivo (sin .txt)
        """
        self.filename: str = filename
        
        # Datos raw del archivo
        self.timestamps: Optional[pd.DatetimeIndex] = None
        self.temperatures: Optional[pd.DataFrame] = None  # Columnas = channel_1 a channel_14
        
        # Resultados de procesamiento (calculados por utils)
        self.reference_channel: Optional[int] = None  # Canal usado como referencia (1-14)
        self.offsets: Dict[int, float] = {}  # {canal: offset} canales válidos (1-14)
        self.offset_errors: Dict[int, float] = {}  # {canal: error} error del offset
        self.omitted_channels: Dict[int, str] = {}  # {canal: razón} canales omitidos
        self.is_valid: bool = True  # False si el run es 'BAD' en logfile o excluido por keywords
    
    def __repr__(self) -> str:
        """
        Representación del objeto cuando se imprime.
        Ejemplo:
            >>> run = Run('20220531_ln2_r48176_r48177_48060_48479_7')
            >>> print(run)
            Run('20220531_ln2_r48176_r48177_48060_48479_7', valid=True, offsets=10, omitted=2)
        """
        return f"Run('{self.filename}', valid={self.is_valid}, offsets={len(self.offsets)}, omitted={len(self.omitted_channels)})"



