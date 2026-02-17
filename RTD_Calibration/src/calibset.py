"""
Clase CalibSet 

Responsabilidades:
- Almacenar set_number (del config.yml, ej: 3.0, 21.0)
- Almacenar sensors
"""
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

# Importar desde el módulo padre
parent_dir = Path(__file__).parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

if TYPE_CHECKING:
    try:
        from .run import Run
    except ImportError:
        from run import Run

try:
    from .sensor import Sensor
except ImportError:
    from sensor import Sensor    


class CalibSet:
    """
    Data class: almacena un conjunto de calibración completo (datos puros del set).
    
    Atributos:
        set_number: float - Número del set (del config, ej: 3.0, 21.0)
        sensors: list[Sensor] - Lista de 12 objetos Sensor del set (canales 1-12)
                                sensor[0] = canal 1, sensor[1] = canal 2, etc.
        reference_sensors: list[Sensor] - Sensores de referencia del set (canales 13-14 en runs)
        runs: list[Run] - Runs de este set (ciegos, con offsets por canal)
        mean_offsets: dict - {sensor_id: offset_medio} calculado de runs
        std_offsets: dict - {sensor_id: std_error} calculado de runs
    
    Esta clase solo ALMACENA datos del set de calibración.
    Los cálculos se hacen en utils.py.
    CalibSet NO conoce jerarquía (parent/children/raised) - eso es TreeEntry.
    
    Nota: Los sensores están en orden: sensors[0] corresponde al canal 1,
          sensors[1] al canal 2, etc. No necesitamos un mapping explícito.
    
    Filosofía:
        CalibSet responde: "¿Qué medí?" (datos, runs, estadísticas)
        TreeEntry responde: "¿Cómo se relaciona con otros?" (jerarquía, raised)
    """
    
    def __init__(self, set_number: float):
        """
        Crea un CalibSet vacío. Las funciones de utils lo rellenarán después.
        
        Args:
            set_number: Número del set (ej: 3.0, 21.0)
        """
        self.set_number: float = set_number
        
        # Lista de 12 sensores del set (objetos Sensor en orden de canal)
        # Importante: sensors[0] = canal 1, sensors[1] = canal 2, etc.
        # Este orden permite traducir directamente canal → sensor
        self.sensors: list[Sensor] = []
        
        # Sensores de referencia (ej: referencias generales en canales 13-14)
        # Estos sensores aparecen en múltiples sets del experimento
        self.reference_sensors: list[Sensor] = []
        
        # Runs de este set (objetos Run ciegos que trabajan solo con números de canal)
        self.runs: list['Run'] = []
        
        # Estadísticas calculadas por utils a partir de los runs (inicialmente vacíos)
        self.mean_offsets: Dict[int, float] = {}  # {sensor_id: offset_medio}
        self.std_offsets: Dict[int, float] = {}  # {sensor_id: std_error}
    
    
    def __repr__(self) -> str:
        """
        Representación del objeto.
        Ejemplo: CalibSet(set=3.0, sensors=12)
        """
        return f"CalibSet(set={self.set_number}, sensors={len(self.sensors)})"