"""
Clase CalibSet - Data class para almacenar un conjunto de calibración completo.

Responsabilidades:
- Almacenar set_number (del config.yml, ej: 3.0, 21.0)
- Almacenar sensors (Set de 12 instancias Sensor del config.yml)
- Almacenar runs (List de ~4 instancias Run válidas con offsets)
- Almacenar reference_id (copiado de run.reference_id o el primer sensor)
- Almacenar mean_offsets (media ponderada calculada por utils)
- Almacenar std_offsets (desviación estándar calculada por utils)

Esta clase INTEGRA: Sensor + Run
Todo el procesamiento está en utils.py
"""
from typing import List, Dict, Optional, Set as SetType


class CalibSet:
    """
    Data class: almacena un conjunto de calibración completo.
    
    Un CalibSet agrupa:
    - 12 sensores (instancias de Sensor) en un Set
    - ~4 runs válidos (instancias de Run) en una List
    - Estadísticas agregadas (mean_offsets, std_offsets)
    
    Atributos:
        set_number: float - Número del set (del config, ej: 3.0, 21.0)
        sensors: set[Sensor] - Set de 12 instancias Sensor (del config)
        runs: list[Run] - Runs válidos con offsets calculados (~4 runs)
        reference_id: int - Sensor de referencia (del run o primer sensor)
        mean_offsets: dict[int, float] - {sensor_id: offset_medio} (calculado por utils)
        std_offsets: dict[int, float] - {sensor_id: std} (calculado por utils)
    
    Esta clase solo ALMACENA datos. Los cálculos se hacen en utils.py.
    
    Nota: CalibSet NO sabe nada de parent_sets o rounds. Eso es responsabilidad de Tree.
    
    Ejemplo de uso:
        >>> # Utils crea el CalibSet completo
        >>> calib_set = utils.create_calibration_set(
        >>>     set_number=3.0,
        >>>     logfile=logfile,
        >>>     config=config
        >>> )
        >>> 
        >>> # CalibSet contiene todo integrado
        >>> print(f"Set {calib_set.set_number}")
        >>> print(f"  Sensors: {len(calib_set.sensors)} instancias")
        >>> print(f"  Runs: {len(calib_set.runs)} válidos")
        >>> print(f"  Offsets: {calib_set.mean_offsets}")
        >>>
        >>> # Acceder a sensors
        >>> for sensor in calib_set.sensors:
        >>>     print(f"Sensor {sensor.id}")
    """
    
    def __init__(self, set_number: float):
        """
        Crea un CalibSet vacío. Utils lo rellenará.
        
        Args:
            set_number: Número del set (del config, ej: 3.0, 21.0)
        """
        self.set_number: float = set_number
        
        # Conjunto de 12 instancias Sensor (del config.yml)
        # Usamos set() de Python para almacenar objetos Sensor únicos
        self.sensors: SetType = set()  # set[Sensor] - Array de los 12 sensores del config, hacer un array sin usar set()
        
        # Lista de runs válidos procesados (con offsets calculados)
        self.runs: List = []  # List[Run] - ~4 runs válidos, aqui no, moverlo al tree_entry
        
        # Sensor de referencia (copiado de run.reference_id o primer sensor)
        self.reference_id: Optional[int] = None #esto probablemente no haga falta aqui, moverlo al tree_entry
        
        # Estadísticas agregadas (calculadas por utils a partir de self.runs). No queremos esto aquí.
        self.mean_offsets: Dict[int, float] = {}  # {sensor_id: mean_offset}
        self.std_offsets: Dict[int, float] = {}   # {sensor_id: std_offset}
    
    def __repr__(self) -> str:
        """
        Representación del objeto.
        
        Ejemplo:
            >>> calib_set = CalibSet(3.0)
            >>> # Después de ser rellenado por utils:
            >>> print(calib_set)
            CalibSet(set=3.0, sensors=12, runs=4, offsets=10, ref=48060)
        """
        n_sensors = len(self.sensors)
        n_runs = len(self.runs)
        n_offsets = len(self.mean_offsets)
        ref = self.reference_id if self.reference_id else "None"
        return f"CalibSet(set={self.set_number}, sensors={n_sensors}, runs={n_runs}, offsets={n_offsets}, ref={ref})"
