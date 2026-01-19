"""
TreeEntry: Nodo del árbol de calibración que representa un CalibSet con sus relaciones.

Un TreeEntry es como un "nodo" que almacena:
- El CalibSet procesado (con offsets ya calculados)
- Información de config.yml (round, raised, parent_sets, discarded)
- Offsets de los 12 sensores respecto a CADA raised disponible
- Referencias a nodos parent y children

TreeEntry NO calcula, solo almacena estructura y datos.
Todas las funciones de cálculo están en utils.py
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class TreeEntry:
    """
    Nodo del árbol de calibración que representa un set con sus relaciones jerárquicas.
    
    Attributes:
        set_number: ID del set (ej: 3.0, 21.0, 57.0), lo tiene el calibset, quitar.
        calibset: Objeto CalibSet 
        #añadir runs, quitar del calibset.
        #round: Ronda del set (1, 2, 3) no hace falta la ronda
        #sensors: Lista de IDs de los 12 sensores del set
        #raised_sensors: Lista de sensores "raised" que conectan con rondas superiores, no haran falta porque se puede hacer de forma automática
        #discarded_sensors: Lista de sensores descartados en config, en calibset
        parent_entry: Lista de TreeEntry de la ronda anterior (parents), va a ser una tree_entry
        children_entries: Lista de TreeEntry de la ronda siguiente (children)
        
        offsets_to_raised: Offsets de cada sensor respecto a cada raised disponible.
            Estructura: {raised_id: {sensor_id: (offset, error)}}
            Ejemplo: {48176: {48060: (0.123, 0.002), 48061: (0.456, 0.003), ...},
                      48177: {48060: (0.125, 0.002), 48061: (0.458, 0.003), ...}}
            
            Esto permite calcular múltiples caminos usando diferentes raised.
            La media ponderada se hace DESPUÉS en utils, no aquí.
    
    Example:
        >>> # Set 3 de R1 con 2 raised
        >>> entry = TreeEntry(
        ...     set_number=3.0,
        ...     calibset=calibset_3,
        ...     round=1,
        ...     sensors=[48060, 48061, ...],
        ...     raised_sensors=[48176, 48177],
        ...     discarded_sensors=[48062]
        ... )
        >>> print(entry)
        TreeEntry(Set 3.0, R1, 12 sensors, 2 raised, 1 discarded)
    """
    
    set_number: float
    calibset: 'CalibSet'  # Forward reference
    round: int
    sensors: List[int]
    raised_sensors: List[int] = field(default_factory=list)
    discarded_sensors: List[int] = field(default_factory=list)
    
    # Relaciones jerárquicas
    parent_entries: List['TreeEntry'] = field(default_factory=list)
    children_entries: List['TreeEntry'] = field(default_factory=list)
    
    # Offsets respecto a cada raised
    # {raised_id: {sensor_id: (offset, error)}}
    offsets_to_raised: Dict[int, Dict[int, Tuple[float, float]]] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        """Representación string del TreeEntry."""
        return (f"TreeEntry(Set {self.set_number}, R{self.round}, "
                f"{len(self.sensors)} sensors, {len(self.raised_sensors)} raised, "
                f"{len(self.discarded_sensors)} discarded)")
    
    def __str__(self) -> str:
        """String legible para print()."""
        lines = [
            f"Set {self.set_number} (Round {self.round})",
            f"  Sensors: {self.sensors[:3]}... ({len(self.sensors)} total)",
            f"  Raised: {self.raised_sensors}",
        ]
        
        if self.discarded_sensors:
            lines.append(f"  Discarded: {self.discarded_sensors}")
        
        if self.parent_entries:
            parent_ids = [p.set_number for p in self.parent_entries]
            lines.append(f"  Parents: {parent_ids}")
        
        if self.children_entries:
            children_ids = [c.set_number for c in self.children_entries]
            lines.append(f"  Children: {children_ids}")
        
        if self.offsets_to_raised:
            lines.append(f"  Offsets calculated for {len(self.offsets_to_raised)} raised sensors")
        
        return "\n".join(lines)
    
    def add_parent(self, parent: 'TreeEntry'):
        """Añade un parent entry (ronda anterior)."""
        if parent not in self.parent_entries:
            self.parent_entries.append(parent)
    
    def add_child(self, child: 'TreeEntry'):
        """Añade un child entry (ronda siguiente)."""
        if child not in self.children_entries:
            self.children_entries.append(child)
    
    def get_offset_to_raised(self, sensor_id: int, raised_id: int) -> Optional[Tuple[float, float]]:
        """
        Obtiene el offset de un sensor respecto a un raised específico.
        
        Args:
            sensor_id: ID del sensor
            raised_id: ID del raised
        
        Returns:
            Tupla (offset, error) o None si no existe
        """
        if raised_id not in self.offsets_to_raised:
            return None
        
        return self.offsets_to_raised[raised_id].get(sensor_id)
    
    def has_sensor(self, sensor_id: int) -> bool:
        """Verifica si el set contiene un sensor."""
        return sensor_id in self.sensors
    
    def is_sensor_discarded(self, sensor_id: int) -> bool:
        """Verifica si un sensor está descartado."""
        return sensor_id in self.discarded_sensors
    
    def is_sensor_raised(self, sensor_id: int) -> bool:
        """Verifica si un sensor es raised."""
        return sensor_id in self.raised_sensors
    
    def get_valid_sensors(self) -> List[int]:
        """Obtiene lista de sensores válidos (no descartados)."""
        return [s for s in self.sensors if s not in self.discarded_sensors]
    
    def get_raised_for_sensor(self, sensor_id: int) -> List[int]:
        """
        Obtiene los raised disponibles para calcular offset de un sensor.
        
        Si el sensor ES un raised, retorna los OTROS raised del set.
        Si el sensor es normal, retorna TODOS los raised del set.
        
        Args:
            sensor_id: ID del sensor
        
        Returns:
            Lista de raised_ids disponibles para este sensor
        """
        if sensor_id in self.raised_sensors:
            # El sensor ES raised, usar los otros raised
            return [r for r in self.raised_sensors if r != sensor_id]
        else:
            # Sensor normal, usar todos los raised
            return self.raised_sensors.copy()
