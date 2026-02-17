"""
Utilidades para construcción y procesamiento del Tree.

Funciones principales:
- find_parent_sets(): Encuentra el parent de un entry según config
- calculate_offsets_to_raised(): Calcula offsets de sensores respecto a raised
- calculate_raised_sensors(): Calcula automáticamente los sensores raised
- build_tree_hierarchy(): Construye jerarquía parent-child en el tree
- create_tree_from_calibsets(): Construye Tree completo desde calibsets
"""

from typing import Dict, List, Tuple, Optional
import sys
from pathlib import Path

# Importar desde el módulo padre
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from tree_entry import TreeEntry
from tree import Tree
from calibset import CalibSet
from sensor import Sensor


def find_parent_sets(target_entry: TreeEntry, all_entries: List[TreeEntry], parent_set_id: Optional[float] = None) -> List[TreeEntry]:
    """
    Encuentra el parent de un entry basándose en parent_set del config.
    
    Args:
        target_entry: Entry a analizar
        all_entries: Lista de todos los entries
        parent_set_id: ID del parent_set desde config (opcional)
    
    Returns:
        Lista con el TreeEntry parent (máximo 1 elemento)
    """
    # Si no hay parent_set definido, no tiene parent
    if parent_set_id is None:
        return []
    
    # Buscar el entry que corresponda al parent_set_id
    for entry in all_entries:
        if entry.set_number == parent_set_id:
            return [entry]
    
    # Si no se encuentra, devolver lista vacía
    return []


def calculate_offsets_to_raised(
    tree_entry: TreeEntry,
    calibset: CalibSet
) -> Dict[Sensor, Dict[Sensor, Tuple[float, float]]]:
    """
    Calcula offsets de sensores respecto a raised.
    
    Args:
        tree_entry: TreeEntry con raised_sensors
        calibset: CalibSet con offsets
    
    Returns:
        Dict {raised_sensor: {sensor: (offset, error)}}
    """
    from utils.math_utils import propagate_error
    
    # Diccionario que almacenará los resultados: {raised_sensor: {sensor: (offset, error)}}
    offsets_to_raised = {}
    
    # Obtener offsets ya calculados del CalibSet (todos son respecto a la referencia interna del set)
    calibset_offsets = calibset.mean_offsets  # {sensor_id: offset}
    calibset_errors = calibset.std_offsets    # {sensor_id: error}
    reference_id = calibset.reference_sensors[0].id if calibset.reference_sensors else None
    
    # Procesar cada raised sensor disponible en este entry
    for raised_sensor in tree_entry.raised_sensors:
        offsets_to_raised[raised_sensor] = {}
        
        # Obtener offset del raised respecto a la referencia interna del set
        # Si el raised ES la referencia, su offset es 0
        if raised_sensor.id == reference_id:
            raised_offset = 0.0
            raised_error = 0.0
        # Si no es la referencia, buscar su offset en los calculados
        elif raised_sensor.id in calibset_offsets:
            raised_offset = calibset_offsets[raised_sensor.id]
            raised_error = calibset_errors.get(raised_sensor.id, 0.0)
        else:
            # Si el raised no tiene offset calculado, hay un problema
            print(f"  Warning: Raised {raised_sensor.id} no tiene offset en CalibSet {tree_entry.set_number}")
            continue
        
        # Para cada sensor del set, calcular su offset respecto a este raised
        for sensor in tree_entry.calibset.sensors:
            # Saltar sensores descartados (defectuosos o inválidos)
            if sensor in tree_entry.discarded_sensors:
                continue
            
            # No calcular offset de un sensor consigo mismo (sería 0 siempre)
            # Nota: se cambió el 19/01/26 para evitar caminos triviales
            if sensor == raised_sensor:
                continue

            # Obtener offset del sensor respecto a la referencia interna del set
            if sensor.id == reference_id:
                sensor_offset = 0.0
                sensor_error = 0.0
            elif sensor.id in calibset_offsets:
                sensor_offset = calibset_offsets[sensor.id]
                sensor_error = calibset_errors.get(sensor.id, 0.0)
            else:
                # Si el sensor no tiene offset, fue omitido en todos los runs (sin datos válidos)
                continue

            # Cambio de base de referencia:
            # offset(sensor → raised) = offset(sensor → ref) - offset(raised → ref)
            offset_to_raised = sensor_offset - raised_offset
            error_to_raised = propagate_error(sensor_error, raised_error)

            # Guardar el offset calculado
            offsets_to_raised[raised_sensor][sensor] = (offset_to_raised, error_to_raised)
    
    return offsets_to_raised


def calculate_raised_sensors(entry: TreeEntry, general_references: List[int]) -> List:
    """
    Calcula automáticamente los sensores raised comparando con el parent_set.
    
    Raised = sensores que aparecen tanto en el set actual como en su parent,
    excluyendo las referencias generales del experimento.
    
    Args:
        entry: TreeEntry a analizar
        general_references: Lista de IDs de referencias generales (ej: [48176, 48177])
    
    Returns:
        Lista de Sensor objects que son raised
    """
    # Si el entry no tiene parent, es el root y no tiene raised
    if not entry.parent_entries:
        return []
    
    # Obtener lista de sensores del set actual
    current_sensors = entry.calibset.sensors
    
    # Obtener sensores del parent (asumimos que solo hay un parent)
    parent = entry.parent_entries[0]
    parent_sensors = parent.calibset.sensors
    
    # Buscar sensores que están en ambos sets (current y parent)
    raised_sensors = []
    for sensor in current_sensors:
        # No incluir las referencias generales del experimento
        if sensor.id in general_references:
            continue
        
        # Si el sensor aparece en el parent, es un raised
        if sensor in parent_sensors:
            raised_sensors.append(sensor)
    
    return raised_sensors


def build_tree_hierarchy(tree: Tree, sets_config: dict):
    """
    Construye jerarquía parent-child en el tree usando parent_set del config.
    
    Args:
        tree: Tree con entries
        sets_config: Configuración de sets (para parent_set)
    """
    all_entries = list(tree.entries.values())
    # Recorrer cada entry para establecer sus relaciones parent-child
    for entry in all_entries:
        # Buscar el parent_set definido en la configuración para este set
        set_config = sets_config.get(float(entry.set_number), {})
        parent_set_id = set_config.get('parent_set', None)
        
        # Si tiene parent_set definido, establecer la conexión
        if parent_set_id is not None:
            parents = find_parent_sets(entry, all_entries, parent_set_id)
            for parent in parents:
                entry.add_parent(parent)  # Conectar el entry con su parent
                parent.add_child(entry)   # Conectar el parent con este entry (bidireccional)


def create_tree_from_calibsets(
    calibsets: Dict[float, CalibSet],
    config: dict,
    root_set_id: Optional[float] = None
) -> Tree:
    """
    Construye Tree desde calibsets y config.
    
    Args:
        calibsets: Dict {set_number: CalibSet}
        config: Config (solo para discarded)
        root_set_id: ID del root (None = automático)
    
    Returns:
        Tree completo
    """
    tree = Tree()
    sets_config = config.get('sensors', {}).get('sets', {})
    
    print(f"Construyendo Tree desde {len(calibsets)} CalibSets...")
    
    # Paso 1: Crear TreeEntry para cada CalibSet con solo discarded desde config
    for set_number, calibset in calibsets.items():
        set_config = sets_config.get(float(set_number), {})
        
        # Extraer solo discarded desde config
        discarded_ids = set_config.get('discarded', [])
        
        # Mapear IDs a objetos Sensor
        discarded_sensors = [s for s in calibset.sensors if s.id in discarded_ids]
        
        # Crear TreeEntry con raised vacío (se calculará después)
        entry = TreeEntry(
            calibset=calibset,
            raised_sensors=[],  # Se calculará automáticamente
            discarded_sensors=discarded_sensors
        )
        
        tree.add_entry(entry)
        print(f"  Set {set_number}: {len(discarded_sensors)} discarded")
    
    # Paso 2: Construir jerarquía parent-child usando parent_set del config
    print("\nConstruyendo jerarquía parent-child...")
    build_tree_hierarchy(tree, sets_config)
    
    # Paso 3: Calcular raised automáticamente comparando con parent
    print("\nCalculando raised sensors automáticamente...")
    
    # Obtener referencias generales del config (aparecen en 'reference' de los sets)
    general_references = set()
    for set_cfg in sets_config.values():
        refs = set_cfg.get('reference', [])
        general_references.update(refs)
    general_references = list(general_references)
    print(f"  Referencias generales excluidas: {general_references}")
    
    all_entries = list(tree.entries.values())
    for entry in all_entries:
        entry.raised_sensors = calculate_raised_sensors(entry, general_references)
        print(f"  Set {entry.set_number}: {len(entry.raised_sensors)} raised = {[s.id for s in entry.raised_sensors]}")
    
    # Paso 4: Calcular offsets respecto a cada raised
    print("\nCalculando offsets_to_raised...")
    for entry in all_entries:
        if entry.raised_sensors:  # Solo si hay raised
            entry.offsets_to_raised = calculate_offsets_to_raised(entry, entry.calibset)
            n_offsets = sum(len(d) for d in entry.offsets_to_raised.values())
            print(f"  Set {entry.set_number}: {len(entry.offsets_to_raised)} raised, {n_offsets} offsets")
        else:
            print(f"  Set {entry.set_number}: No raised sensors")
    
    # Verificar conexiones
    total_entries = len(tree.entries)
    total_parents = sum(len(e.parent_entries) for e in tree.entries.values())
    total_children = sum(len(e.children_entries) for e in tree.entries.values())
    print(f"  Total: {total_entries} entries, "
          f"{total_parents} conexiones parent, {total_children} conexiones child")
    
    # Paso 4: Establecer root
    if root_set_id is None:
        # Buscar el entry que no tiene parents (root)
        root_candidates = [e for e in tree.entries.values() if not e.parent_entries]
        if root_candidates:
            # Tomar el de mayor set_number si hay varios
            root_entry = max(root_candidates, key=lambda e: e.set_number)
            tree.set_root(root_entry)
            print(f"\n[OK] Root establecido automáticamente: Set {root_entry.set_number}")
        else:
            print(f"\n  Warning: No hay entries sin parents, no se pudo establecer root")
    else:
        root_entry = tree.get_entry(root_set_id)
        if root_entry:
            tree.set_root(root_entry)
            print(f"\n[OK] Root establecido: Set {root_entry.set_number}")
        else:
            print(f"\n  Error: Set {root_set_id} no encontrado en el tree")
    
    print(f"\n[OK] Tree construido: {len(tree.entries)} entries")
    
    return tree
