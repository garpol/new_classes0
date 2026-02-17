"""
TreeEntry: Nodo del árbol de calibración que representa un CalibSet con sus relaciones.

Un TreeEntry es como un "nodo" que almacena:
- El CalibSet 
- Runs válidos
- Información de config.yml (parent_sets, discarded)
- Offsets de los 12 sensores respecto a CADA raised
- Referencias a nodos parent y children

TreeEntry NO calcula, solo almacena estructura y datos.
Todas las funciones de cálculo están en utils.py
"""


from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
try:
    from .calibset import CalibSet
except ImportError:
    from calibset import CalibSet
try:
    from .sensor import Sensor
except ImportError:
    from sensor import Sensor
try:
    from .run import Run
except ImportError:
    from run import Run

@dataclass
class TreeEntry:
    """
    Nodo del árbol de calibración: maneja RELACIONES jerárquicas entre CalibSets.
    
    TreeEntry es "ciego" a la estructura del árbol - solo almacena datos y relaciones.
    El Tree es quien organiza y calcula jerarquías (como rondas).
    
    Almacena:
        - calibset: referencia a un CalibSet (datos puros del set)
        - discarded_sensors: objetos Sensor descartados (del config)
        - raised_sensors: objetos Sensor raised (comparados con parent)
        - parent_entries: nodos padre (TreeEntry)
        - children_entries: nodos hijo (TreeEntry)
        - offsets_to_raised: {raised: {sensor: (offset, error)}} calculados de calibset.runs
    
    Filosofía:
        - CalibSet: "¿Qué medí?" (datos, runs, estadísticas)
        - TreeEntry: "¿Cómo se relaciona?" (parent, children, raised, offsets dirigidos)
        - Tree: "¿Qué estructura tiene?" (rondas, root, jerarquía global)
    
    Notas:
        - No conoce su "ronda" - eso lo calcula el Tree según distancia al root
        - No realiza cálculos; todo se hace en utils.py
        - NO duplica runs (están en calibset.runs)
    """
    
    calibset: CalibSet
    discarded_sensors: List[Sensor] = field(default_factory=list)  # Del config
    raised_sensors: List[Sensor] = field(default_factory=list)  # Comparados con parent
    
    parent_entries: List['TreeEntry'] = field(default_factory=list)
    children_entries: List['TreeEntry'] = field(default_factory=list)
    
    # Offsets de sensores de ESTE entry hacia sus raised
    # Calculados de calibset.runs usando índice directo (sensors[canal-1])
    offsets_to_raised: Dict[Sensor, Dict[Sensor, Tuple[float, float]]] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"TreeEntry(Set {self.calibset.set_number}, {len(self.discarded_sensors)} discarded, {len(self.calibset.runs)} runs)"

    def add_parent(self, parent: 'TreeEntry'):
        """
        Añade un nodo padre a la lista de parents.
        Solo lo añade si no está ya en la lista (evita duplicados).
        """
        if parent not in self.parent_entries:
            self.parent_entries.append(parent)
    
    def add_child(self, child: 'TreeEntry'):
        """
        Añade un nodo hijo a la lista de children.
        Solo lo añade si no está ya en la lista (evita duplicados).
        """
        if child not in self.children_entries:
            self.children_entries.append(child)
    
    def get_offset_to_raised(self, sensor: Sensor, raised: Sensor) -> Optional[Tuple[float, float]]:
        """
        Devuelve el offset y error de un sensor respecto a un raised.
        
        Args:
            sensor: Objeto Sensor del cual queremos el offset
            raised: Objeto Sensor raised usado como referencia
        
        Returns:
            Tupla (offset, error) si existe, None si no hay datos.
            
        Ejemplo:
            offset, error = entry.get_offset_to_raised(sensor_48178, raised_48060)
            # Devuelve cuánto difiere 48178 respecto a 48060 en este set
        """
        return self.offsets_to_raised.get(raised, {}).get(sensor)
    
    def get_valid_sensors(self) -> List[Sensor]:
        """Devuelve los objetos Sensor válidos (no descartados)."""
        return [s for s in self.calibset.sensors if s not in self.discarded_sensors]
    
    def is_sensor_discarded(self, sensor: Sensor) -> bool:
        """Verifica si un sensor está descartado."""
        return sensor in self.discarded_sensors
    
    def get_raised_for_sensor(self, sensor: Sensor) -> List[Sensor]:
        """
        Devuelve lista de raised disponibles para un sensor (excluye el sensor mismo).
        
        Un sensor no puede usar su propio offset (sería 0), por eso se excluye.
        Esto es útil para encontrar caminos válidos hacia rondas superiores.
        """
        return [r for r in self.raised_sensors if r != sensor]
    
    @property
    def set_number(self) -> float:
        """Acceso rápido al número del set desde calibset."""
        return self.calibset.set_number
    
    @property
    def all_children(self) -> List['TreeEntry']:
        """Devuelve todos los hijos de este nodo (múltiples)."""
        return self.children_entries.copy()
    
    @property
    def all_parents(self) -> List['TreeEntry']:
        """Devuelve todos los padres de este nodo."""
        return self.parent_entries.copy()
