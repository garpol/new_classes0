"""
Utilidades para construcción y procesamiento del Tree.

Funciones principales:
- create_tree_from_calibsets(): Construye Tree desde calibsets y config
- calculate_offsets_to_raised(): Calcula offsets respecto a raised
- find_parent_sets(): Encuentra parent sets de un set
- build_tree_hierarchy(): Construye relaciones parent-child
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


def find_parent_sets(target_set_id: float, config: dict) -> List[float]:
    """
    Encuentra los sets "parent" de un set dado analizando qué sets tienen
    sensores raised que aparecen como sensores normales en el target_set.
    
    Solo retorna parents de la ronda INMEDIATAMENTE ANTERIOR (no salta rondas).
    
    Args:
        target_set_id: ID del set para el cual buscar parents
        config: Diccionario de configuración
    
    Returns:
        Lista de IDs de sets parent (ronda inmediatamente anterior)
    
    Examples:
        >>> config = load_config()
        >>> parents = find_parent_sets(49.0, config)  # Set R2
        >>> print(parents)  # [3.0, 21.0, ...]  (Sets R1)
    """
    sets_config = config.get('sensors', {}).get('sets', {})
    target_config = sets_config.get(float(target_set_id), {})
    target_sensors = set(target_config.get('sensors', []))
    target_round = target_config.get('round', 0)
    
    # Convertir round a int si es string
    try:
        target_round = int(target_round)
    except (ValueError, TypeError):
        # Si no se puede convertir (ej: 'Refs', 'RRefs'), no tiene parents
        return []
    
    # La ronda parent debe ser inmediatamente anterior
    parent_round = target_round - 1
    if parent_round < 1:
        return []  # No hay ronda anterior
    
    parents = []
    
    # Buscar sets de la ronda anterior cuyo 'raised' contenga sensores del target_set
    for set_id, set_config in sets_config.items():
        if set_id == target_set_id:
            continue
        
        # Filtrar solo sets de la ronda parent
        set_round = set_config.get('round', 0)
        try:
            set_round = int(set_round)
        except (ValueError, TypeError):
            continue  # Ignorar sets con rounds inválidos
        
        if set_round != parent_round:
            continue
        
        raised_sensors = set(set_config.get('raised', []))
        
        # Si algún raised de este set está en el target, es un parent
        if raised_sensors & target_sensors:  # Intersección
            parents.append(float(set_id))
    
    return sorted(parents)


def calculate_offsets_to_raised(
    tree_entry: TreeEntry,
    calibset: CalibSet
) -> Dict[int, Dict[int, Tuple[float, float]]]:
    """
    Calcula offsets de cada sensor del set respecto a CADA raised disponible.
    
    Para cada raised, calcula el offset de TODOS los sensores válidos del set
    (excepto el raised respecto a sí mismo y los descartados).
    
    Esto incluye calcular offsets ENTRE raised, permitiendo múltiples caminos
    de calibración entre diferentes raised del mismo set.
    
    Args:
        tree_entry: TreeEntry con información del set
        calibset: CalibSet con mean_offsets ya calculados
    
    Returns:
        Dict {raised_id: {sensor_id: (offset, error)}}
        
    Examples:
        >>> entry = TreeEntry(set_number=3.0, calibset=calibset_3, ...)
        >>> # Set 3 tiene raised [48203, 48479] y sensores [48060, ..., 48477]
        >>> offsets_to_raised = calculate_offsets_to_raised(entry, calibset_3)
        >>> # offsets_to_raised = {
        >>> #   48203: {48060: (0.123, 0.002), ..., 48479: (0.456, 0.003)},
        >>> #   48479: {48060: (0.125, 0.002), ..., 48203: (0.458, 0.003)}
        >>> # }
        >>> # Nota: 48203 → 48479 y 48479 → 48203 permiten caminos alternativos
    
    Notes:
        - Los offsets se calculan a partir del mean_offsets del CalibSet
        - Se usa la referencia interna del CalibSet para hacer el cambio de base
        - Un raised NO aparece en su propio dict (offset consigo mismo = 0)
        - Los raised SÍ aparecen en los dicts de OTROS raised (caminos entre raised)
    """
    import numpy as np
    from math_utils import propagate_error
    
    # Diccionario resultado: {raised_id: {sensor_id: (offset, error)}}
    offsets_to_raised = {}
    
    # Obtener offsets del CalibSet (respecto a su referencia interna)
    calibset_offsets = calibset.mean_offsets  # {sensor_id: offset}
    calibset_errors = calibset.std_offsets    # {sensor_id: error}
    reference_id = calibset.reference_id
    
    # Para cada raised disponible
    for raised_id in tree_entry.raised_sensors:
        offsets_to_raised[raised_id] = {}
        
        # Obtener offset del raised respecto a la referencia interna
        # raised_offset = mean_offsets[raised_id]  (si raised NO es la referencia)
        if raised_id == reference_id:
            raised_offset = 0.0
            raised_error = 0.0
        elif raised_id in calibset_offsets:
            raised_offset = calibset_offsets[raised_id]
            raised_error = calibset_errors.get(raised_id, 0.0)
        else:
            # El raised no tiene offset calculado (problema)
            print(f"⚠️  Warning: Raised {raised_id} no tiene offset en CalibSet {tree_entry.set_number}")
            continue
        
        # Calcular offset de cada sensor respecto a este raised
        for sensor_id in tree_entry.sensors:
            # Si el sensor está descartado, skip
            if sensor_id in tree_entry.discarded_sensors:
                continue
            
            # Permitir el offset consigo mismo (trivial) Cambiado 19/01/26 y comentado
            if sensor_id == raised_id:
                #offset_to_raised = 0.0
                #error_to_raised = 0.0
                #offsets_to_raised[raised_id][sensor_id] = (offset_to_raised, error_to_raised)
                continue

            # Obtener offset del sensor respecto a referencia interna
            if sensor_id == reference_id:
                sensor_offset = 0.0
                sensor_error = 0.0
            elif sensor_id in calibset_offsets:
                sensor_offset = calibset_offsets[sensor_id]
                sensor_error = calibset_errors.get(sensor_id, 0.0)
            else:
                # Sensor no tiene offset (omitido en todos los runs)
                continue

            # Cambio de base: offset(sensor → raised) = offset(sensor → ref) - offset(raised → ref)
            offset_to_raised = sensor_offset - raised_offset
            error_to_raised = propagate_error(sensor_error, raised_error)

            offsets_to_raised[raised_id][sensor_id] = (offset_to_raised, error_to_raised)
    
    return offsets_to_raised


def build_tree_hierarchy(tree: Tree, config: dict):
    """
    Construye las relaciones parent-child entre TreeEntries del árbol.
    
    Modifica el tree in-place, añadiendo referencias parent/child a cada entry.
    
    Args:
        tree: Tree con entries ya añadidos (sin relaciones)
        config: Diccionario de configuración
    
    Examples:
        >>> tree = Tree()
        >>> tree.add_entry(entry_3)
        >>> tree.add_entry(entry_49)
        >>> tree.add_entry(entry_57)
        >>> build_tree_hierarchy(tree, config)
        >>> # Ahora entry_49.parent_entries = [entry_3, entry_21, ...]
        >>> # Y entry_3.children_entries = [entry_49]
    """
    # Para cada entry, encontrar sus children
    # NOTA: find_parent_sets está mal nombrada - retorna sets de ronda INFERIOR
    # Es decir, retorna los CHILDREN, no los parents
    for entry in tree.entries.values():
        child_ids = find_parent_sets(entry.set_number, config)
        
        for child_id in child_ids:
            child_entry = tree.get_entry(child_id)
            
            if child_entry is not None:
                # Añadir relación bidireccional
                # entry es el parent (ronda superior)
                # child_entry es el child (ronda inferior)
                child_entry.add_parent(entry)
                entry.add_child(child_entry)


def create_tree_from_calibsets(
    calibsets: Dict[float, CalibSet],
    config: dict,
    root_set_id: Optional[float] = None
) -> Tree:
    """
    Construye un Tree completo desde calibsets y config.yml
    
    Proceso:
    1. Crear TreeEntry para cada CalibSet
    2. Calcular offsets_to_raised para cada entry
    3. Construir jerarquía parent-child
    4. Establecer root (set de referencia R3)
    
    Args:
        calibsets: Dict {set_number: CalibSet} con calibsets procesados
        config: Diccionario de configuración
        root_set_id: ID del set root (None = buscar automáticamente el de mayor ronda)
    
    Returns:
        Tree con estructura completa y offsets calculados
    
    Examples:
        >>> # Después de crear calibsets con utils.create_calibration_set()
        >>> calibsets = {3.0: calibset_3, 21.0: calibset_21, ..., 57.0: calibset_57}
        >>> tree = create_tree_from_calibsets(calibsets, config)
        >>> print(tree)  # Muestra estructura jerárquica
        >>> 
        >>> # Acceder a entries
        >>> entry_3 = tree.get_entry(3.0)
        >>> print(entry_3.offsets_to_raised)  # Offsets respecto a cada raised
    """
    tree = Tree()
    sets_config = config.get('sensors', {}).get('sets', {})
    
    print(f"Construyendo Tree desde {len(calibsets)} CalibSets...")
    
    # Paso 1: Crear TreeEntry para cada CalibSet
    for set_number, calibset in calibsets.items():
        set_config = sets_config.get(float(set_number), {})
        
        # Extraer información del config
        round_num = set_config.get('round', 1)
        sensors = set_config.get('sensors', [])
        raised = set_config.get('raised', [])
        discarded = set_config.get('discarded', [])
        
        # Crear TreeEntry
        entry = TreeEntry(
            set_number=set_number,
            calibset=calibset,
            round=round_num,
            sensors=sensors,
            raised_sensors=raised,
            discarded_sensors=discarded
        )
        
        # Paso 2: Calcular offsets respecto a cada raised
        if raised:  # Solo si hay raised
            entry.offsets_to_raised = calculate_offsets_to_raised(entry, calibset)
            # Determinar ronda desde config en lugar de adivinar
            sets_config = config.get('sensors', {}).get('sets', {})
            round_num = sets_config.get(set_number, {}).get('round', '?')
            print(f"  Set {set_number} (R{round_num}): {len(entry.offsets_to_raised)} raised, "
                  f"{sum(len(d) for d in entry.offsets_to_raised.values())} offsets calculados")
        else:
            # Obtener ronda real en lugar de adivinar
            sets_config = config.get('sensors', {}).get('sets', {})
            round_num = sets_config.get(set_number, {}).get('round', '?')
            print(f"  Set {set_number} (R{round_num}): No raised sensors")
        
        tree.add_entry(entry)
    
    # Paso 3: Construir jerarquía parent-child
    print("\nConstruyendo jerarquía parent-child...")
    build_tree_hierarchy(tree, config)
    
    # Verificar conexiones
    for round_num in [1, 2, 3]:
        entries = tree.get_entries_by_round(round_num)
        total_parents = sum(len(e.parent_entries) for e in entries)
        total_children = sum(len(e.children_entries) for e in entries)
        print(f"  R{round_num}: {len(entries)} entries, "
              f"{total_parents} conexiones parent, {total_children} conexiones child")
    
    # Paso 4: Establecer root
    if root_set_id is None:
        # Buscar el set de mayor ronda (típicamente R3)
        r3_entries = tree.get_entries_by_round(3)
        if r3_entries:
            # Tomar el primero (o el de mayor set_number si hay varios)
            root_entry = max(r3_entries, key=lambda e: e.set_number)
            tree.set_root(root_entry)
            print(f"\n✓ Root establecido automáticamente: Set {root_entry.set_number} (R3)")
        else:
            print("\n⚠️  Warning: No hay entries de R3, no se pudo establecer root")
    else:
        root_entry = tree.get_entry(root_set_id)
        if root_entry:
            tree.set_root(root_entry)
            print(f"\n✓ Root establecido: Set {root_entry.set_number} (R{root_entry.round})")
        else:
            print(f"\n⚠️  Error: Set {root_set_id} no encontrado en el tree")
    
    print(f"\n✓ Tree construido: {len(tree.entries)} entries")
    
    return tree
