import pandas as pd
import numpy as np
import logging
import yaml
from typing import Dict, Tuple, List, Optional, Any, Union
try:
    from .utils import load_config, DEFAULT_CONFIG
except ImportError:
    from utils import load_config, DEFAULT_CONFIG

# Attempt to import networkx and provide a clear instruction if it is missing.
try:
    import networkx as nx
except ImportError as exc:
    logging.error(
        "The 'networkx' library is not available; install it with: pip install networkx"
    )
    raise ImportError(
        "Missing dependency 'networkx'. Install it with: pip install networkx"
    ) from exc

# ----------------------------------------------------------------------
# Configuration of logging
# -----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Main class: CalibrationNetwork
# -----------------------------------------------------------------------

class CalibrationNetwork:
    """
    Class that manages global calibration by connecting multiple 'sets'
    through 'raised' sensors that serve as bridges between rounds.
    
    Capabilities:
        - Build the connection graph between sets.
        - Calculate global offsets between sensors in different sets.
        - Propagate uncertainties (errors) along paths in the tree.
    """

    def __init__(self, sets_dict: Dict[float, Any], config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None) -> None:
        """
        Initialize CalibrationNetwork with sets and configuration.
        
        Args:
            sets_dict (dict): Dictionary {CalibSetNumber: SetObject}.
                              Each SetObject must have:
                                  - calibration_constants (DataFrame)
                                  - calibration_errors (DataFrame)
            config (dict, optional): Configuration dictionary. If provided, overrides config_path.
            config_path (str, optional): Path to the YAML file with tree definition
                               (relationships between sets, raised sensors, etc.)
        """
        self.sets = sets_dict
        self.graph = nx.Graph()
        
        # Load configuration using the same pattern as Set and Run classes
        try:
            if config is not None:
                self.config = config
            elif config_path:
                self.config = load_config(config_path)
            else:
                self.config = DEFAULT_CONFIG.copy()
        except (FileNotFoundError, yaml.YAMLError, KeyError) as e:
            logger.warning("Could not load configuration: %s. Using defaults.", e)
            self.config = DEFAULT_CONFIG.copy()
        
        # Validate sets_dict
        if not isinstance(sets_dict, dict):
            raise TypeError("sets_dict must be a dictionary")
        
        if not sets_dict:
            logger.warning("No sets provided in sets_dict")
        
        # ═════════════════════════════════════════════════════════════════
        # ALMACENAMIENTO DE OFFSETS Y ERRORES DE LA RED COMPLETA
        # ═════════════════════════════════════════════════════════════════
        # Diccionarios para almacenar offsets y errores calculados entre sensores
        # Estructura: {(sensor_from, sensor_to): valor}
        self.global_offsets: Dict[Tuple[int, int], float] = {}
        self.global_errors: Dict[Tuple[int, int], float] = {}
        self.offset_paths: Dict[Tuple[int, int], List] = {}
        
        # Offsets directos dentro de un set
        # Estructura: {(sensor_from, sensor_to): {'offset': float, 'error': float, 'set_id': float}}
        self.direct_offsets: Dict[Tuple[int, int], Dict] = {}
        
        # Normalize DataFrame indices/columns to strings for consistency
        self._normalize_dataframe_indices()
        
        # Build graph from configuration
        self._build_graph_from_config()

    # ------------------------------------------------------------------
    # UTILITY: NORMALIZE DATAFRAME INDICES
    # ------------------------------------------------------------------
    def _normalize_dataframe_indices(self) -> None:
        """
        Normalize all DataFrame indices and columns to strings for consistency.
        This prevents KeyError issues when mixing int/str sensor IDs.
        """
        for set_id, set_obj in self.sets.items():
            try:
                if hasattr(set_obj, 'calibration_constants') and set_obj.calibration_constants is not None:
                    df = set_obj.calibration_constants
                    df.index = df.index.astype(str)
                    df.columns = df.columns.astype(str)
                    set_obj.calibration_constants = df
                
                if hasattr(set_obj, 'calibration_errors') and set_obj.calibration_errors is not None:
                    df = set_obj.calibration_errors
                    df.index = df.index.astype(str)
                    df.columns = df.columns.astype(str)
                    set_obj.calibration_errors = df
            except (ValueError, KeyError, AttributeError) as e:
                logger.warning("Could not normalize DataFrames for set %s: %s", set_id, e)

    # ------------------------------------------------------------------
    # BUILDING THE CONNECTION GRAPH BETWEEN SETS
    # ------------------------------------------------------------------
    def _build_graph_from_config(self) -> None:
        """
        Builds the connection graph between sets using the configuration.
        Each node is a CalibSetNumber.
        Each edge connects two consecutive sets through one or more 'raised' sensors.
        """
        logger.info("Building calibration graph from configuration...")

        # Primero añadir todos los sets como nodos
        for set_id in self.sets.keys():
            self.graph.add_node(set_id)
        
        sets_config = self._extract_sets_configuration()
        edges_added = self._build_graph_edges(sets_config)
        
        logger.info("Graph built with %d sets and %d connections.", len(self.graph.nodes), edges_added)
        
        # Validate tree connectivity and remove disconnected sets
        self._validate_and_prune_disconnected_sets()

    def _validate_and_prune_disconnected_sets(self) -> None:
        """
        Validate tree connectivity and automatically remove sets that are not connected
        to the reference set (highest round). This prevents processing sets that belong
        to incomplete branches of the calibration tree.
        
        Example:
            If Set 57 (R3) is the reference and Sets 55-56 (R2) connect to a future
            Set 58 (R3) that doesn't exist yet, those sets will be automatically removed.
        """
        if len(self.graph.nodes) == 0:
            logger.warning("Graph is empty, nothing to validate.")
            return
        
        # Find the reference set (highest round number)
        ref_set = self._find_reference_set()
        if ref_set is None:
            logger.warning("Could not identify reference set, skipping connectivity validation.")
            return
        
        # Find all sets connected to the reference (using BFS/DFS)
        try:
            # Get connected component containing the reference set
            if ref_set not in self.graph.nodes:
                logger.error("Reference set %s not found in graph!", ref_set)
                return
                
            connected_sets = set(nx.node_connected_component(self.graph, ref_set))
            all_sets = set(self.graph.nodes)
            disconnected_sets = all_sets - connected_sets
            
            if disconnected_sets:
                logger.warning("⚠️  TREE VALIDATION: Found %d set(s) NOT connected to reference set %s", len(disconnected_sets), ref_set)
                logger.warning("    Disconnected sets: %s", sorted(disconnected_sets))
                logger.warning("    These sets will be REMOVED from analysis (likely waiting for future reference sets).")
                
                # Remove disconnected sets from graph AND from self.sets
                for disc_set in disconnected_sets:
                    self.graph.remove_node(disc_set)
                    if disc_set in self.sets:
                        del self.sets[disc_set]
                        logger.debug("    Removed set %s from analysis", disc_set)
                
                logger.info("✅ Tree validated: %d sets remain (all connected to reference %s)", len(connected_sets), ref_set)
            else:
                logger.info("✅ Tree validated: All %d sets are connected to reference %s", len(all_sets), ref_set)
                
        except (nx.NetworkXError, KeyError) as e:
            logger.error("Error during tree validation: %s", e)

    def _find_reference_set(self) -> Optional[Union[float, str]]:
        """
        Find the reference set (set with the highest round number).
        
        Returns:
            Optional[Union[float, str]]: Reference set ID or None if not found
        """
        try:
            sets_config = self._extract_sets_configuration()
            max_round = -1
            ref_set = None
            
            for set_id_str, data in sets_config.items():
                # Skip non-numeric keys (like "Refs", "metadata", etc.)
                if not self._is_numeric_key(set_id_str):
                    continue
                
                # Skip if data is not a dict or doesn't have proper round value
                if not isinstance(data, dict):
                    continue
                    
                try:
                    round_num = int(data.get("round", 1))  # Convert to int
                except (ValueError, TypeError):
                    continue
                    
                if round_num > max_round:
                    max_round = round_num
                    # Find matching set_id in self.sets
                    for candidate in self.sets.keys():
                        if str(candidate) == str(set_id_str):
                            ref_set = candidate
                            break
                        try:
                            if float(candidate) == float(set_id_str):
                                ref_set = candidate
                                break
                        except (ValueError, TypeError):
                            continue
            
            if ref_set:
                logger.debug("Reference set identified: %s (Round %s)", ref_set, max_round)
            return ref_set
        except (ValueError, TypeError, KeyError) as e:
            logger.error("Error finding reference set: %s", e)
            return None

    def _is_numeric_key(self, key: Any) -> bool:
        """Check if a key can be interpreted as a numeric set ID."""
        try:
            float(key)
            return True
        except (ValueError, TypeError):
            return False
    
    def _extract_sets_configuration(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract sets configuration from the loaded config.
        
        Returns:
            Dict[str, Dict[str, Any]]: Sets configuration dictionary
        """
        try:
            # Get sensor configuration from the loaded config
            sensors_config = self.config.get("sensors", {})
            
            # Try to get sets configuration (unified structure)
            sets_config = sensors_config.get("sets", {})
            if not sets_config:
                # Fallback to individual dictionaries
                raised_sensors = sensors_config.get("sensors_raised_by_set", {})
                set_rounds = sensors_config.get("set_rounds", {})
                
                # Convert to sets format for processing
                sets_config = {}
                for set_id in raised_sensors.keys():
                    sets_config[str(set_id)] = {
                        "raised": raised_sensors.get(set_id, []),
                        "round": set_rounds.get(set_id, 1)
                    }
            return sets_config
        except (KeyError, AttributeError, TypeError) as e:
            logger.error("Error processing sensor configuration: %s", e)
            return {}

    def _build_graph_edges(self, sets_config: Dict[str, Dict[str, Any]]) -> int:
        """
        Build graph edges from sets configuration.
        
        Args:
            sets_config (Dict[str, Dict[str, Any]]): Sets configuration
            
        Returns:
            int: Number of edges added
        """
        edges_added = 0
        for set_id_str, data in sets_config.items():
            # Keep set IDs as-is (don't force conversion to float)
            # Try to match with keys in self.sets which could be float or str
            set_id = None
            for candidate in self.sets.keys():
                if str(candidate) == str(set_id_str) or candidate == set_id_str:
                    set_id = candidate
                    break
                try:
                    if float(candidate) == float(set_id_str):
                        set_id = candidate
                        break
                except (ValueError, TypeError):
                    continue
            
            if set_id is None:
                logger.debug("Set ID '%s' from config not found in sets_dict, skipping", set_id_str)
                continue

            round_id = data.get("round", 1)
            raised_sensors = data.get("raised", [])

            # Search for sets in the next level that contain any of these sensors
            edges_added += self._connect_to_next_round(
                set_id, round_id, raised_sensors, sets_config
            )

        return edges_added

    def _connect_to_next_round(
        self, 
        set_id: Union[float, str], 
        round_id: int, 
        raised_sensors: List[int], 
        sets_config: Dict[str, Dict[str, Any]]
    ) -> int:
        """
        Connect a set to sets in the next round.
        
        Args:
            set_id (float or str): Current set ID
            round_id (int): Current round number
            raised_sensors (List[int]): Raised sensors for current set
            sets_config (Dict[str, Dict[str, Any]]): All sets configuration
            
        Returns:
            int: Number of edges added
        """
        edges_added = 0
        for other_id_str, other_data in sets_config.items():
            # Find matching other_id in self.sets (same logic as _build_graph_edges)
            other_id = None
            for candidate in self.sets.keys():
                if str(candidate) == str(other_id_str) or candidate == other_id_str:
                    other_id = candidate
                    break
                try:
                    if float(candidate) == float(other_id_str):
                        other_id = candidate
                        break
                except (ValueError, TypeError):
                    continue
            
            if other_id is None:
                continue
                
            if other_data.get("round", 1) != round_id + 1:
                continue

            # Find bridge sensors by checking actual calibration_constants
            bridge_sensors = self._find_bridge_sensors(raised_sensors, other_id)
            
            if bridge_sensors:
                # Add a single edge with all bridge sensors
                try:
                    self.graph.add_edge(set_id, other_id, sensors=bridge_sensors)
                    edges_added += 1
                    logger.debug("Added edge: %s ↔ %s via sensors %s", set_id, other_id, bridge_sensors)
                except (nx.NetworkXError, ValueError) as e:
                    logger.warning("Failed to add edge between %s and %s: %s", set_id, other_id, e)

        return edges_added

    def _find_bridge_sensors(
        self, 
        raised_sensors: List[int], 
        other_set_id: Union[float, str]
    ) -> List[int]:
        """
        Find bridge sensors between two sets by checking if raised sensors
        actually appear in the calibration_constants of the other set.
        
        Args:
            raised_sensors (List[int]): Raised sensors from current set
            other_set_id: ID of the other set to check
            
        Returns:
            List[int]: Bridge sensors found (sensors that exist in both sets)
        """
        if other_set_id not in self.sets:
            return []
        
        other_set = self.sets[other_set_id]
        if not hasattr(other_set, 'calibration_constants') or other_set.calibration_constants is None:
            return []
        
        # Get sensor IDs from calibration_constants index (converted to integers)
        try:
            other_sensors = [int(float(s)) for s in other_set.calibration_constants.index]
        except (ValueError, TypeError):
            logger.warning("Could not convert sensor IDs to int for set %s", other_set_id)
            return []
        
        # Find raised sensors that appear in the other set's calibration_constants
        bridge_sensors = [s for s in raised_sensors if s in other_sensors]
        
        return bridge_sensors

    def _get_set_round(self, set_id: Union[float, str]) -> int:
        """
        Get the round number for a given set ID from configuration.
        
        Args:
            set_id (float or str): Set identifier
            
        Returns:
            int: Round number (defaults to 1 if not found)
        """
        sensors_config = self.config.get("sensors", {})
        
        # Try unified sets structure first
        sets_config = sensors_config.get("sets", {})
        if sets_config:
            # Try multiple key formats: direct, as float, as string, as int
            keys_to_try = [
                set_id,  # Original type
                float(set_id) if self._can_convert_to_float(set_id) else None,  # As float
                int(float(set_id)) if self._can_convert_to_float(set_id) else None,  # As int
                str(set_id),  # As string
            ]
            
            for key in keys_to_try:
                if key is None:
                    continue
                # Try direct lookup (without string conversion)
                if key in sets_config:
                    set_data = sets_config[key]
                    if set_data and isinstance(set_data, dict):
                        round_val = set_data.get("round", 1)
                        try:
                            return int(round_val)
                        except (ValueError, TypeError):
                            continue
        
        # Fallback to set_rounds dictionary
        set_rounds = sensors_config.get("set_rounds", {})
        for key in [set_id, str(set_id), float(set_id) if self._can_convert_to_float(set_id) else None]:
            if key is None:
                continue
            if key in set_rounds:
                try:
                    return int(set_rounds[key])
                except (ValueError, TypeError):
                    continue
        
        return 1
    
    def _can_convert_to_float(self, value: Any) -> bool:
        """Helper to check if a value can be converted to float."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def _get_reference_sensor(self, set_id: Union[float, str]) -> Optional[int]:
        """
        Get the reference sensor for a given set ID from configuration.
        
        Args:
            set_id (float or str): Set identifier
            
        Returns:
            int or None: Reference sensor ID (first raised sensor)
        """
        sensors_config = self.config.get("sensors", {})
        
        # Try unified sets structure first
        sets_config = sensors_config.get("sets", {})
        if sets_config:
            # Try multiple key formats
            for key in [set_id, str(set_id), float(set_id) if self._can_convert_to_float(set_id) else None]:
                if key is None:
                    continue
                set_data = sets_config.get(str(key), {})
                if set_data:
                    raised_sensors = set_data.get("raised", [])
                    if raised_sensors:
                        return raised_sensors[0]
        
        # Fallback to sensors_raised_by_set dictionary
        sensors_raised = sensors_config.get("sensors_raised_by_set", {})
        for key in [set_id, str(set_id), float(set_id) if self._can_convert_to_float(set_id) else None]:
            if key is None:
                continue
            if key in sensors_raised:
                raised_sensors = sensors_raised[key]
                return raised_sensors[0] if raised_sensors else None
        
        return None

    def get_sets_by_round(self, round_number: int) -> List[Union[float, str]]:
        """
        Get all sets that belong to a specific round.
        
        Args:
            round_number (int): Round number to filter by
            
        Returns:
            List[Union[float, str]]: List of set IDs in the specified round
        """
        sets_in_round = []
        for set_id in self.sets.keys():
            if self._get_set_round(set_id) == round_number:
                sets_in_round.append(set_id)
        return sorted(sets_in_round, key=lambda x: (float(x) if self._can_convert_to_float(x) else str(x)))

    def get_reference_set(self) -> Optional[Union[float, str]]:
        """
        Get the reference set (typically the highest round set).
        
        Returns:
            Union[float, str] or None: Reference set ID, or None if not found
        """
        if not self.sets:
            return None
        
        # Find the set with the highest round number
        max_round = 0
        reference_set = None
        
        for set_id in self.sets.keys():
            round_num = self._get_set_round(set_id)
            if round_num > max_round:
                max_round = round_num
                reference_set = set_id
        
        if reference_set is None:
            logger.warning("No reference set found; returning first set as fallback")
            reference_set = list(self.sets.keys())[0] if self.sets else None
        
        return reference_set
    
    def get_absolute_reference_sensor(self) -> Optional[int]:
        """
        Get the absolute reference sensor ID for the entire calibration system.
        
        This is the first sensor from the reference set (highest round), which serves
        as the base reference for all calibration calculations in the system.
        
        Returns:
            int or None: Absolute reference sensor ID, or None if not found
        """
        ref_set = self.get_reference_set()
        if ref_set is None:
            logger.warning("No reference set found, cannot determine absolute reference sensor")
            return None
        
        ref_sensor = self._get_reference_sensor(ref_set)
        if ref_sensor is None:
            logger.warning("Reference set %s has no reference sensor", ref_set)
        
        return ref_sensor
    
    # ═════════════════════════════════════════════════════════════════════
    # MÉTODOS DE AUTO-DETECCIÓN Y VALIDACIÓN DE SENSORES RAISED
    # ═════════════════════════════════════════════════════════════════════
    
    def auto_detect_raised_sensors(
        self, 
        set_id: Union[float, str], 
        logfile_df: pd.DataFrame,
        verbose: bool = False,
        exclude_reference_sensors: bool = True
    ) -> List[int]:
        """
        Auto-detecta sensores 'raised' comparando el sensor mapping de un set R1
        con los sensor mappings de sets R2, identificando sensores comunes.
        
        IMPORTANTE: Los sensores de referencia (channels 13-14) son excluidos por defecto,
        ya que se repiten en múltiples sets para monitoreo pero NO son parte del árbol
        de calibración y NO deben considerarse como 'raised'.
        
        Args:
            set_id: ID del set (típicamente Ronda 1)
            logfile_df: DataFrame del LogFile con columnas S1..S20
            verbose: Si True, imprime información detallada
            exclude_reference_sensors: Si True (default), excluye sensores de referencia
                                      (channels 13-14) de la detección
            
        Returns:
            List[int]: Lista de sensor IDs que aparecen en sets de ronda superior
                      (excluyendo sensores de referencia)
        """
        # Obtener ronda del set actual
        current_round = self._get_set_round(set_id)
        
        if set_id not in self.sets:
            logger.warning("Set %s no encontrado en sets_dict", set_id)
            return []
        
        # Obtener sensores del set actual desde calibration_constants
        current_set_obj = self.sets[set_id]
        if not hasattr(current_set_obj, 'calibration_constants') or current_set_obj.calibration_constants is None:
            logger.warning("Set %s no tiene calibration_constants", set_id)
            return []
        
        current_sensors = set([int(float(s)) for s in current_set_obj.calibration_constants.index])
        
        # Obtener y excluir sensores de referencia si está habilitado
        reference_sensor_ids = set()
        if exclude_reference_sensors:
            try:
                ref_info = current_set_obj.get_reference_sensors_for_set(set_id)
                reference_sensor_ids = ref_info.get('ref_sensor_ids', set())
                if reference_sensor_ids and verbose:
                    print(f"\n📌 Sensores de referencia encontrados (serán excluidos): {sorted(reference_sensor_ids)}")
            except (AttributeError, TypeError):
                # Método no disponible o set_obj no tiene el método
                pass
        
        # Excluir sensores de referencia de los sensores del set actual
        current_sensors = current_sensors - reference_sensor_ids
        
        if verbose:
            print(f"\n🔍 Auto-detección de sensores raised para Set {set_id} (Ronda {current_round})")
            print(f"   Sensores en el set (sin referencias): {sorted(current_sensors)}")
        
        # Buscar sets de ronda superior
        raised_candidates = set()
        
        for other_set_id in self.sets.keys():
            other_round = self._get_set_round(other_set_id)
            
            # Solo comparar con sets de ronda inmediatamente superior
            if other_round != current_round + 1:
                continue
            
            other_set_obj = self.sets[other_set_id]
            if not hasattr(other_set_obj, 'calibration_constants') or other_set_obj.calibration_constants is None:
                continue
            
            other_sensors = set([int(float(s)) for s in other_set_obj.calibration_constants.index])
            
            # También excluir referencias del set de ronda superior
            if exclude_reference_sensors:
                try:
                    other_ref_info = other_set_obj.get_reference_sensors_for_set(other_set_id)
                    other_ref_ids = other_ref_info.get('ref_sensor_ids', set())
                    other_sensors = other_sensors - other_ref_ids
                except (AttributeError, TypeError):
                    pass
            
            # Encontrar sensores comunes (ambos ya tienen referencias excluidas)
            common = current_sensors & other_sensors
            
            if common:
                raised_candidates.update(common)
                if verbose:
                    print(f"   ✅ Set {other_set_id} (Ronda {other_round}): sensores comunes {sorted(common)}")
        
        result = sorted(list(raised_candidates))
        
        if verbose:
            if result:
                print(f"\n   🎯 Sensores raised detectados: {result}")
            else:
                print(f"\n   ⚠️ No se detectaron sensores raised (set posiblemente desconectado)")
        
        return result
    
    def validate_and_suggest_raised_sensors(
        self, 
        logfile_df: pd.DataFrame,
        auto_fix_missing: bool = False,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Valida la configuración de sensores raised comparando lo declarado en
        sensors.yaml con lo detectado automáticamente del sensor mapping.
        
        Comprueba:
        1. Sets sin raised definidos que deberían tenerlos
        2. Raised declarados que no coinciden con la detección automática
        3. Raised declarados que no existen en sets de ronda superior
        
        Args:
            logfile_df: DataFrame del LogFile con sensor mappings
            auto_fix_missing: Si True, sugiere añadir raised faltantes al config
            verbose: Si True, imprime reportes detallados
            
        Returns:
            Dict con resultados de validación:
            {
                'missing_raised': [(set_id, detected_raised), ...],
                'mismatched_raised': [(set_id, declared, detected), ...],
                'invalid_raised': [(set_id, invalid_sensors), ...],
                'all_valid': bool
            }
        """
        if verbose:
            print("\n" + "="*80)
            print("🔍 VALIDACIÓN DE SENSORES RAISED")
            print("="*80)
        
        missing_raised = []
        mismatched_raised = []
        invalid_raised = []
        
        # Obtener configuración de sets
        sets_config = self.config.get("sensors", {}).get("sets", {})
        
        # Validar cada set
        for set_id in self.sets.keys():
            round_num = self._get_set_round(set_id)
            
            # Solo validar sets que NO sean la ronda máxima (referencia)
            max_round = max([self._get_set_round(s) for s in self.sets.keys()])
            if round_num >= max_round:
                continue
            
            # Obtener raised declarados en config
            declared_raised = []
            set_config_key = None
            # Intentar múltiples variantes de tipo para buscar en el config
            for key in [set_id, int(set_id) if self._can_convert_to_float(set_id) else None, 
                       float(set_id) if self._can_convert_to_float(set_id) else None, str(set_id)]:
                if key is None:
                    continue
                # Buscar con el tipo original (no convertir a string)
                if key in sets_config:
                    set_config_key = key
                    declared_raised = sets_config[key].get('raised', [])
                    break
            
            # Auto-detectar raised (excluyendo sensores de referencia)
            detected_raised = self.auto_detect_raised_sensors(
                set_id, 
                logfile_df, 
                verbose=False,
                exclude_reference_sensors=True
            )
            
            # CASO 1: No hay raised declarados pero se detectaron automáticamente
            if not declared_raised and detected_raised:
                missing_raised.append((set_id, detected_raised))
                if verbose:
                    print(f"\n⚠️  Set {set_id} (Ronda {round_num}): NO tiene raised declarados")
                    print(f"   📊 Detección automática sugiere: {detected_raised}")
                    print(f"   💡 Considera añadir a sensors.yaml:")
                    print(f"      {set_config_key or set_id}:")
                    print(f"        raised: {detected_raised}")
            
            # CASO 2: Hay raised declarados pero no coinciden con los detectados
            elif declared_raised and detected_raised:
                declared_set = set(declared_raised)
                detected_set = set(detected_raised)
                
                if declared_set != detected_set:
                    mismatched_raised.append((set_id, declared_raised, detected_raised))
                    
                    extra_declared = declared_set - detected_set
                    missing_declared = detected_set - declared_set
                    
                    if verbose:
                        print(f"\n⚠️  Set {set_id} (Ronda {round_num}): Discrepancia en sensores raised")
                        print(f"   📝 Declarados en config: {declared_raised}")
                        print(f"   📊 Detectados automáticamente: {detected_raised}")
                        if extra_declared:
                            print(f"   ❌ En config pero NO detectados: {sorted(extra_declared)}")
                            print(f"      → Estos sensores NO aparecen en sets R{round_num+1}")
                        if missing_declared:
                            print(f"   ➕ Detectados pero NO en config: {sorted(missing_declared)}")
                            print(f"      → Considera añadirlos a sensors.yaml")
            
            # CASO 3: Hay raised declarados pero ninguno fue detectado (posible error)
            elif declared_raised and not detected_raised:
                invalid_raised.append((set_id, declared_raised))
                if verbose:
                    print(f"\n❌ Set {set_id} (Ronda {round_num}): Raised declarados NO VÁLIDOS")
                    print(f"   📝 Declarados: {declared_raised}")
                    print(f"   ⚠️ NINGUNO aparece en sets de Ronda {round_num+1}")
                    print(f"   💡 Verifica que los IDs sean correctos o que existan sets R{round_num+1}")
        
        all_valid = not missing_raised and not mismatched_raised and not invalid_raised
        
        if verbose:
            print("\n" + "="*80)
            if all_valid:
                print("✅ VALIDACIÓN COMPLETA: Todos los sensores raised son correctos")
            else:
                print("⚠️  VALIDACIÓN COMPLETA: Se encontraron discrepancias")
                print(f"   - Sets sin raised: {len(missing_raised)}")
                print(f"   - Sets con discrepancias: {len(mismatched_raised)}")
                print(f"   - Sets con raised inválidos: {len(invalid_raised)}")
            print("="*80)
        
        return {
            'missing_raised': missing_raised,
            'mismatched_raised': mismatched_raised,
            'invalid_raised': invalid_raised,
            'all_valid': all_valid
        }
    
    # ═════════════════════════════════════════════════════════════════════
    # MÉTODOS DE ALMACENAMIENTO Y RECUPERACIÓN DE OFFSETS
    # ═════════════════════════════════════════════════════════════════════
    
    def store_offset(self, sensor_from: int, sensor_to: int, offset: float, 
                    error: float, set_id: Optional[Union[float, str]] = None, 
                    path: Optional[List] = None):
        """
        Almacenar un offset calculado entre dos sensores.
        
        Args:
            sensor_from: ID del sensor origen
            sensor_to: ID del sensor destino (referencia)
            offset: Valor del offset
            error: Error asociado
            set_id: Set donde se calculó (opcional, para offsets directos)
            path: Camino de sets utilizado (opcional)
        """
        key = (int(sensor_from), int(sensor_to))
        self.global_offsets[key] = offset
        self.global_errors[key] = error
        
        if path:
            self.offset_paths[key] = path
        
        # Si es un offset directo (dentro de un set)
        if set_id is not None:
            self.direct_offsets[key] = {
                'offset': offset,
                'error': error,
                'set_id': set_id
            }
    
    def get_offset(self, sensor_from: int, sensor_to: int) -> Tuple[Optional[float], Optional[float]]:
        """
        Obtener offset almacenado entre dos sensores.
        
        Args:
            sensor_from: ID del sensor origen
            sensor_to: ID del sensor destino
            
        Returns:
            Tupla (offset, error) o (None, None) si no existe
        """
        key = (int(sensor_from), int(sensor_to))
        if key in self.global_offsets:
            return self.global_offsets[key], self.global_errors[key]
        return None, None
    
    def get_all_offsets_for_sensor(self, sensor_id: int) -> Dict[int, Dict]:
        """
        Obtener todos los offsets calculados para un sensor.
        
        Args:
            sensor_id: ID del sensor
            
        Returns:
            Diccionario {sensor_ref: {'offset': float, 'error': float, 'path': list}}
        """
        sensor_id = int(sensor_id)
        results = {}
        
        for (s_from, s_to), offset in self.global_offsets.items():
            if s_from == sensor_id:
                results[s_to] = {
                    'offset': offset,
                    'error': self.global_errors.get((s_from, s_to), None),
                    'path': self.offset_paths.get((s_from, s_to), None)
                }
        
        return results
    
    def export_all_offsets(self) -> pd.DataFrame:
        """
        Exportar todos los offsets y errores calculados a un DataFrame.
        
        Returns:
            DataFrame con columnas: sensor_from, sensor_to, offset, error, path
        """
        data = []
        for (s_from, s_to), offset in self.global_offsets.items():
            data.append({
                'sensor_from': s_from,
                'sensor_to': s_to,
                'offset': offset,
                'error': self.global_errors.get((s_from, s_to), None),
                'path': self.offset_paths.get((s_from, s_to), None)
            })
        return pd.DataFrame(data)
    
    def clear_offsets(self):
        """Limpiar todos los offsets almacenados."""
        self.global_offsets.clear()
        self.global_errors.clear()
        self.offset_paths.clear()
        self.direct_offsets.clear()

    def validate_sets_structure(self) -> Dict[str, List[str]]:
        """
        Validate that all sets have the required structure.
        
        Returns:
            Dict[str, List[str]]: Validation results with issues found
        """
        issues = {
            "missing_constants": [],
            "missing_errors": [],
            "missing_sets": []
        }
        
        for set_id, set_obj in self.sets.items():
            if not hasattr(set_obj, 'calibration_constants') or set_obj.calibration_constants is None:
                issues["missing_constants"].append(str(set_id))
            if not hasattr(set_obj, 'calibration_errors') or set_obj.calibration_errors is None:
                issues["missing_errors"].append(str(set_id))
        
        return issues

    @classmethod
    def from_sets(cls, sets_list: List[Any], config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None) -> 'CalibrationNetwork':
        """
        Create a CalibrationNetwork from a list of Set objects.
        
        Args:
            sets_list (List): List of Set objects
            config (dict, optional): Configuration dictionary
            config_path (str, optional): Path to configuration file
            
        Returns:
            CalibrationNetwork: New network instance
        """
        sets_dict = {}
        for set_obj in sets_list:
            # Extract set ID from the set object
            if hasattr(set_obj, 'runs_by_set') and set_obj.runs_by_set:
                # Get the first set ID from runs_by_set
                set_id = list(set_obj.runs_by_set.keys())[0]
                sets_dict[set_id] = set_obj
            else:
                logger.warning("Set object has no runs_by_set, skipping")
        
        return cls(sets_dict, config=config, config_path=config_path)

    # ------------------------------------------------------------------
    # INSPECTION AND DEBUGGING
    # ------------------------------------------------------------------
    def show_graph_summary(self):
        """Display a summary of the calibration graph."""
        print("Summary of calibration graph:")
        for edge in self.graph.edges(data=True):
            # Handle both 'sensor' (singular, old format) and 'sensors' (plural, new format)
            sensors = edge[2].get('sensors', [edge[2].get('sensor')] if 'sensor' in edge[2] else [])
            if sensors:
                print(f"  {edge[0]} ↔ {edge[1]}  (bridge sensors: {sensors})")
        
        # Also log for debugging
        logger.info("Summary of calibration graph:")
        for edge in self.graph.edges(data=True):
            sensors = edge[2].get('sensors', [edge[2].get('sensor')] if 'sensor' in edge[2] else [])
            if sensors:
                logger.info("  %s ↔ %s  (bridge sensors: %s)", edge[0], edge[1], sensors)

    # ------------------------------------------------------------------
    # FUNCTIONS FOR FINDING CONNECTIONS
    # ------------------------------------------------------------------
    def find_path_between_sets(self, set_a: float, set_b: float) -> List[float]:
        """
        Finds the shortest path (in number of connections) between two sets.
        """
        try:
            path = nx.shortest_path(self.graph, source=set_a, target=set_b)
            logger.info("Path found between %s and %s: %s", set_a, set_b, path)
            return path
        except nx.NetworkXNoPath:
            logger.warning("No path exists between %s and %s", set_a, set_b)
            return []

    def find_sensor_set(self, sensor_id: int) -> Optional[Union[float, str]]:
        """
        Locates which set a sensor belongs to.
        Checks both numeric and string indices in calibration_constants.
        """
        sensor_str = str(sensor_id)
        for set_num, set_obj in self.sets.items():
            constants = getattr(set_obj, "calibration_constants", None)
            if constants is not None:
                # Check if sensor exists in index (now normalized to str)
                if sensor_str in constants.index or sensor_id in constants.index:
                    return set_num
        return None

    # ------------------------------------------------------------------
    # CALCULATIONS OF OFFSETS BETWEEN SENSORS IN DIFFERENT SETS
    # ------------------------------------------------------------------
    def compute_offset_between(self, sensor_i: int, sensor_j: int) -> Tuple[float, float]:
        """
        Calculates the global offset between two sensors (i, j) which can be in different sets.
        Uses 'raised' sensors as bridges to connect both sets.
        
        Special case: If sensor_i == sensor_j (raised sensor in different sets),
        the offset is 0.0 by definition.
        """
        # Handle same sensor (raised sensor case)
        if str(sensor_i) == str(sensor_j):
            return 0.0, 0.0
        
        set_i = self.find_sensor_set(sensor_i)
        set_j = self.find_sensor_set(sensor_j)

        if set_i is None or set_j is None:
            raise ValueError(f"One of the sensors ({sensor_i}, {sensor_j}) was not found in any set.")

        if set_i == set_j:
            set_obj = self.sets[set_i]
            # Use string indices for DataFrame access
            si_str = str(sensor_i)
            sj_str = str(sensor_j)
            try:
                d = set_obj.calibration_constants.loc[si_str, sj_str]
                e = set_obj.calibration_errors.loc[si_str, sj_str]
            except KeyError:
                # Try inverse
                try:
                    d = -set_obj.calibration_constants.loc[sj_str, si_str]
                    e = set_obj.calibration_errors.loc[sj_str, si_str]
                except KeyError:
                    logger.warning("Could not find offset between %s and %s in set %s", sensor_i, sensor_j, set_i)
                    d, e = 0.0, 0.0
            return d, e

        # Find path of sets
        path = self.find_path_between_sets(set_i, set_j)
        if not path:
            raise RuntimeError(f"Cannot connect {sensor_i} (Set {set_i}) with {sensor_j} (Set {set_j}).")

        total_offset = 0.0
        total_error2 = 0.0

        for a, b in zip(path[:-1], path[1:]):
            # Get bridge sensors list and pick the first one
            bridge_sensors = self.graph[a][b].get('sensors', [])
            if not bridge_sensors:
                raise RuntimeError(f"No bridge sensors found between Set {a} and Set {b}")
            sensor_bridge = bridge_sensors[0]  # Use first bridge sensor
            
            setA = self.sets[a]
            setB = self.sets[b]

            # Use string indices
            si_str = str(sensor_i)
            sb_str = str(sensor_bridge)
            sj_str = str(sensor_j)

            # offset A→bridge
            dA = 0.0
            eA = 0.0
            if si_str == sb_str:
                # Same sensor, offset is 0
                dA = 0.0
                eA = 0.0
            elif si_str in setA.calibration_constants.index and sb_str in setA.calibration_constants.columns:
                dA = setA.calibration_constants.loc[si_str, sb_str]
                eA = setA.calibration_errors.loc[si_str, sb_str] if hasattr(setA, 'calibration_errors') and setA.calibration_errors is not None else 0.0

            # offset bridge→j
            dB = 0.0
            eB = 0.0
            if sb_str == sj_str:
                # Same sensor, offset is 0
                dB = 0.0
                eB = 0.0
            elif sj_str in setB.calibration_constants.columns and sb_str in setB.calibration_constants.index:
                dB = setB.calibration_constants.loc[sb_str, sj_str]
                eB = setB.calibration_errors.loc[sb_str, sj_str] if hasattr(setB, 'calibration_errors') and setB.calibration_errors is not None else 0.0

            total_offset += dA + dB
            total_error2 += eA**2 + eB**2

        return total_offset, np.sqrt(total_error2)

    # ------------------------------------------------------------------
    # CALIBRATION CHAIN METHODS
    # ------------------------------------------------------------------
    def build_calibration_chain(
        self,
        sensor_id: int,
        logfile_df: pd.DataFrame,
        verbose: bool = True
    ) -> List[Tuple[int, int, int]]:
        """
        Construye la cadena de calibración completa para un sensor dado,
        siguiendo los sensores 'raised' desde ronda 1 hasta la ronda máxima.
        
        Args:
            sensor_id: ID del sensor inicial (típicamente de Ronda 1)
            logfile_df: DataFrame del LogFile con información de runs y sensores
            verbose: Si True, imprime información detallada del proceso
            
        Returns:
            List[Tuple[int, int, int]]: Lista de (sensor_id, set_id, round_num)
            representando la cadena completa desde R1 hasta Rmax
            
        Example:
            >>> chain = net.build_calibration_chain(48203, logfile.log_file)
            >>> # Returns: [(48203, 3, 1), (48203, 49, 2), (48484, 57, 3)]
        """
        chain = []
        
        if verbose:
            print(f"\n🔗 Construyendo cadena de calibración para sensor {sensor_id}")
        
        # 1. Encontrar en qué set de R1 está el sensor
        current_set = None
        current_round = 1
        
        for set_id in logfile_df['CalibSetNumber'].dropna().unique():
            try:
                set_id_int = int(float(set_id))
            except (ValueError, TypeError):
                continue
            
            # Verificar la ronda del set
            if set_id_int not in self.sets:
                continue
            
            try:
                round_num = self._get_set_round(set_id_int)
            except (KeyError, AttributeError):
                continue
            
            if round_num != 1:
                continue
            
            # Buscar el sensor en las columnas S1-S20 del logfile
            set_rows = logfile_df[logfile_df['CalibSetNumber'] == set_id]
            if set_rows.empty:
                continue
            
            # Extraer valores de sensores de todas las columnas S1-S20
            sensor_values = []
            for col in [f'S{i}' for i in range(1, 21)]:
                if col in set_rows.columns:
                    vals = set_rows[col].dropna().values
                    sensor_values.extend(vals)
            
            # Convertir a int para comparar
            sensor_values_int = []
            for val in sensor_values:
                try:
                    sensor_values_int.append(int(float(val)))
                except (ValueError, TypeError):
                    pass
            
            if sensor_id in sensor_values_int:
                current_set = set_id_int
                break
        
        if current_set is None:
            if verbose:
                print(f"   ⚠️ No se encontró el sensor {sensor_id} en ningún set de Ronda 1")
            return chain
        
        if verbose:
            print(f"   ✅ Sensor {sensor_id} encontrado en Set {current_set} (Ronda {current_round})")
        
        # Agregar el primer paso de la cadena
        chain.append((sensor_id, current_set, current_round))
        
        # 2. Seguir la cadena de sensores raised hasta llegar a la ronda máxima
        while True:
            # Obtener sensores raised del set actual desde config
            if current_set not in self.config.get('sensors', {}).get('sets', {}):
                if verbose:
                    print(f"   ⚠️ Set {current_set} no tiene configuración de sensores raised")
                break
            
            set_config = self.config['sensors']['sets'][current_set]
            raised_sensors = set_config.get('raised', [])
            
            if not raised_sensors:
                if verbose:
                    print(f"   ℹ️ Set {current_set} no tiene sensores raised (ronda máxima alcanzada)")
                break
            
            # Tomar el primer sensor raised
            raised_sensor = raised_sensors[0]
            next_round = current_round + 1
            
            if verbose:
                print(f"   🔸 Sensor raised: {raised_sensor} → buscando en Ronda {next_round}")
            
            # Buscar en qué set de la siguiente ronda está este sensor raised
            next_set = None
            found = False
            
            for set_id in logfile_df['CalibSetNumber'].dropna().unique():
                try:
                    set_id_int = int(float(set_id))
                except (ValueError, TypeError, KeyError):
                    continue
                
                if set_id_int not in self.sets:
                    continue
                
                try:
                    round_num = self._get_set_round(set_id_int)
                except (ValueError, TypeError, KeyError):
                    continue
                
                if round_num != next_round:
                    continue
                
                # Buscar raised_sensor en este set
                set_rows = logfile_df[logfile_df['CalibSetNumber'] == set_id]
                if set_rows.empty:
                    continue
                
                sensor_values = []
                for col in [f'S{i}' for i in range(1, 21)]:
                    if col in set_rows.columns:
                        vals = set_rows[col].dropna().values
                        sensor_values.extend(vals)
                
                sensor_values_int = []
                for val in sensor_values:
                    try:
                        sensor_values_int.append(int(float(val)))
                    except (ValueError, TypeError):
                        pass
                
                if raised_sensor in sensor_values_int:
                    next_set = set_id_int
                    found = True
                    break
            
            if not found:
                if verbose:
                    print(f"   ⚠️ No se encontró set de Ronda {next_round} para sensor raised {raised_sensor}")
                break
            
            if verbose:
                print(f"   ✅ Sensor raised {raised_sensor} encontrado en Set {next_set} (Ronda {next_round})")
            
            # Obtener el primer sensor del mapping del siguiente set (será la referencia)
            set_rows_next = logfile_df[logfile_df['CalibSetNumber'] == next_set]
            if not set_rows_next.empty:
                first_sensor = None
                for col in [f'S{i}' for i in range(1, 21)]:
                    if col in set_rows_next.columns:
                        val = set_rows_next[col].dropna().values
                        if len(val) > 0:
                            try:
                                first_sensor = int(float(val[0]))
                                break
                            except (ValueError, TypeError):
                                pass
                
                if first_sensor is not None:
                    if verbose:
                        print(f"      📍 Primer sensor de Set {next_set}: {first_sensor} (referencia)")
                    chain.append((first_sensor, next_set, next_round))
                else:
                    chain.append((raised_sensor, next_set, next_round))
            else:
                chain.append((raised_sensor, next_set, next_round))
            
            current_set = next_set
            current_round = next_round
        
        if verbose:
            print(f"\n📋 CADENA COMPLETA ({len(chain)} pasos):")
            for i, (sens, s, r) in enumerate(chain):
                arrow = " → " if i < len(chain) - 1 else ""
                ref_mark = " 🎯 REFERENCIA ABSOLUTA" if i == len(chain) - 1 else ""
                print(f"   {i+1}. Sensor {sens} en Set {s} (Ronda {r}){ref_mark}{arrow}")
        
        return chain
    
    def calculate_offset_from_chain(
        self,
        chain: List[Tuple[int, int, int]],
        verbose: bool = True
    ) -> Tuple[Optional[float], Optional[float], Dict]:
        """
        Calcula el offset total y error propagado a través de una cadena de calibración.
        
        Estrategia:
        - Usa compute_offset_between() que maneja automáticamente paths en el grafo
        - Acumula offsets paso a paso desde R1 hasta Rmax
        - Propaga errores cuadráticamente
        
        Args:
            chain: Lista de (sensor_id, set_id, round_num) desde R1 hasta Rmax
            verbose: Si True, imprime información detallada
            
        Returns:
            tuple: (offset_total, error_total, detalles_dict)
            
        Example:
            >>> chain = net.build_calibration_chain(48203, logfile.log_file)
            >>> offset, error, details = net.calculate_offset_from_chain(chain)
        """
        if len(chain) < 2:
            if verbose:
                print("⚠️ Cadena muy corta (necesita al menos 2 elementos)")
            return None, None, {}
        
        offset_total = 0.0
        error_sq_sum = 0.0
        detalles = {}
        
        if verbose:
            print(f"\n🔗 Calculando offsets para cadena de {len(chain)} pasos:")
        
        # Calcular offset entre cada par consecutivo
        for i in range(len(chain) - 1):
            sensor_from = str(chain[i][0])  # Convertir a string para compute_offset_between
            sensor_to = str(chain[i+1][0])
            set_from = chain[i][1]
            set_to = chain[i+1][1]
            round_from = chain[i][2]
            round_to = chain[i+1][2]
            
            if verbose:
                print(f"\n   Paso {i+1}: Ronda {round_from} → Ronda {round_to}")
                print(f"      Sensor {sensor_from} (Set {set_from}) → Sensor {sensor_to} (Set {set_to})")
            
            try:
                # Usar compute_offset_between que maneja paths en el grafo
                offset, error = self.compute_offset_between(sensor_from, sensor_to)
                
                if verbose:
                    print(f"      📊 Offset: {offset:.6f} ± {error:.6f} mK")
                
                detalles[f'step_{i+1}'] = {
                    'sensor_from': sensor_from,
                    'sensor_to': sensor_to,
                    'set_from': set_from,
                    'set_to': set_to,
                    'round_from': round_from,
                    'round_to': round_to,
                    'offset': offset,
                    'error': error
                }
                
                offset_total += offset
                error_sq_sum += error**2
                
            except Exception as e:
                if verbose:
                    print(f"      ⚠️ Error calculando offset: {e}")
                return None, None, detalles
        
        error_total = np.sqrt(error_sq_sum)
        detalles['total'] = {
            'offset': offset_total,
            'error': error_total,
            'steps': len(chain) - 1
        }
        
        if verbose:
            print("\n🎯 RESULTADO FINAL:")
            print(f"   Offset Total: {offset_total:.6f} mK")
            print(f"   Error Total:  {error_total:.6f} mK")
            print(f"   Expresión: ({offset_total:.6f} ± {error_total:.6f}) mK")
        
        return offset_total, error_total, detalles

    def compute_weighted_offset_all_paths(
        self,
        sensor_id: int,
        logfile_df: pd.DataFrame,
        verbose: bool = True
    ) -> Tuple[Optional[float], Optional[float], Dict]:
        """
        Calcula el offset ponderado usando TODOS los caminos posibles a través
        de TODOS los sensores 'raised' disponibles.
        
        Estrategia:
        1. Genera todas las cadenas posibles (cada sensor raised es un camino)
        2. Calcula offset y error para cada camino
        3. Identifica el camino con menor error
        4. Calcula media ponderada de todos los offsets usando error como peso
        
        Media ponderada:
            - Peso: w_i = 1 / error_i²
            - Offset final: Σ(offset_i * w_i) / Σ(w_i)
            - Error final: 1 / √(Σw_i)
        
        Args:
            sensor_id: ID del sensor inicial (típicamente de Ronda 1)
            logfile_df: DataFrame del LogFile con información de runs y sensores
            verbose: Si True, imprime información detallada del proceso
            
        Returns:
            tuple: (offset_weighted, error_weighted, info_dict)
            
            info_dict contiene:
                - 'paths': Lista de todos los caminos calculados
                - 'best_path': Camino con menor error
                - 'n_paths': Número total de caminos encontrados
                - 'weights': Pesos calculados para cada camino
                
        Example:
            >>> offset, error, info = net.compute_weighted_offset_all_paths(
            ...     48203, logfile.log_file, verbose=True
            ... )
            >>> print(f"Caminos disponibles: {info['n_paths']}")
            >>> print(f"Mejor camino: {info['best_path']['chain']}")
        """
        if verbose:
            print("\n" + "="*80)
            print("🌐 CÁLCULO DE OFFSET PONDERADO POR TODOS LOS CAMINOS POSIBLES")
            print("="*80)
            print(f"\n🔍 Sensor de partida: {sensor_id}")
        
        # 1. Encontrar el set de R1 del sensor
        current_set = None
        for set_id in logfile_df['CalibSetNumber'].dropna().unique():
            try:
                set_id_int = int(float(set_id))
            except (ValueError, TypeError, KeyError):
                continue
            
            if set_id_int not in self.sets:
                continue
            
            try:
                round_num = self._get_set_round(set_id_int)
            except (ValueError, TypeError, KeyError):
                continue
            
            if round_num != 1:
                continue
            
            set_rows = logfile_df[logfile_df['CalibSetNumber'] == set_id]
            if set_rows.empty:
                continue
            
            sensor_values = []
            for col in [f'S{i}' for i in range(1, 21)]:
                if col in set_rows.columns:
                    vals = set_rows[col].dropna().values
                    sensor_values.extend(vals)
            
            sensor_values_int = []
            for val in sensor_values:
                try:
                    sensor_values_int.append(int(float(val)))
                except (ValueError, TypeError):
                    pass
            
            if sensor_id in sensor_values_int:
                current_set = set_id_int
                break
        
        if current_set is None:
            if verbose:
                print(f"   ⚠️ No se encontró el sensor {sensor_id} en ningún set de Ronda 1")
            return None, None, {}
        
        if verbose:
            print(f"   ✅ Sensor encontrado en Set {current_set} (Ronda 1)")
        
        # 2. Obtener TODOS los sensores raised del set
        if current_set not in self.config.get('sensors', {}).get('sets', {}):
            if verbose:
                print(f"   ⚠️ Set {current_set} no tiene configuración")
            return None, None, {}
        
        set_config = self.config['sensors']['sets'][current_set]
        all_raised_sensors = set_config.get('raised', [])
        
        if not all_raised_sensors:
            if verbose:
                print(f"   ⚠️ Set {current_set} no tiene sensores raised")
            return None, None, {}
        
        if verbose:
            print(f"\n📋 Sensores 'raised' disponibles en Set {current_set}: {all_raised_sensors}")
            print(f"   Total de caminos potenciales: {len(all_raised_sensors)}")
        
        # 3. Construir cadena para CADA sensor raised (un camino por cada uno)
        all_paths = []
        
        for idx, raised_sensor in enumerate(all_raised_sensors, 1):
            if verbose:
                print(f"\n🛤️  CAMINO {idx}/{len(all_raised_sensors)}: Usando sensor raised {raised_sensor}")
            
            # Construir cadena forzando el uso de este sensor raised específico
            chain = self._build_chain_with_specific_raised(
                sensor_id=sensor_id,
                current_set=current_set,
                raised_sensor=raised_sensor,
                logfile_df=logfile_df,
                verbose=verbose
            )
            
            if not chain or len(chain) < 2:
                if verbose:
                    print("   ⚠️ No se pudo construir cadena completa")
                continue
            
            # Calcular offset para este camino
            offset, error, details = self.calculate_offset_from_chain(chain, verbose=False)
            
            if offset is None:
                if verbose:
                    print("   ⚠️ No se pudo calcular offset")
                continue
            
            path_info = {
                'path_id': idx,
                'raised_sensor': raised_sensor,
                'chain': chain,
                'offset': offset,
                'error': error,
                'details': details
            }
            all_paths.append(path_info)
            
            if verbose:
                print(f"   ✅ Offset: {offset:.6f} ± {error:.6f}")
                chain_str = " → ".join([f"{s} (R{r})" for s, set_id, r in chain])
                print(f"   Cadena: {chain_str}")
        
        if not all_paths:
            if verbose:
                print("\n⚠️ No se pudo calcular ningún camino válido")
            return None, None, {}
        
        if verbose:
            print("\n" + "="*80)
            print("📊 RESUMEN DE CAMINOS CALCULADOS")
            print("="*80)
            print(f"   Total de caminos válidos: {len(all_paths)}/{len(all_raised_sensors)}")
        
        # 4. Identificar el camino con menor error
        best_path = min(all_paths, key=lambda p: p['error'])
        
        if verbose:
            print("\n🏆 MEJOR CAMINO (menor error):")
            print(f"   Camino #{best_path['path_id']}: Sensor raised {best_path['raised_sensor']}")
            print(f"   Offset: {best_path['offset']:.6f} ± {best_path['error']:.6f}")
        
        # 5. Calcular media ponderada usando error como peso
        # Peso: w_i = 1 / error_i²
        weights = []
        weighted_offsets = []
        
        if verbose:
            print("\n⚖️  CÁLCULO DE MEDIA PONDERADA:")
            print("   Fórmula: w_i = 1 / error_i²")
        
        for path in all_paths:
            weight = 1.0 / (path['error'] ** 2)
            weights.append(weight)
            weighted_offsets.append(path['offset'] * weight)
            
            if verbose:
                print(f"   Camino #{path['path_id']}: peso = {weight:.6f}")
        
        sum_weights = sum(weights)
        sum_weighted_offsets = sum(weighted_offsets)
        
        offset_weighted = sum_weighted_offsets / sum_weights
        error_weighted = 1.0 / np.sqrt(sum_weights)
        
        if verbose:
            print("\n🎯 RESULTADO FINAL (MEDIA PONDERADA):")
            print(f"   Offset ponderado: {offset_weighted:.6f}")
            print(f"   Error ponderado:  {error_weighted:.6f}")
            print(f"   Expresión: {offset_weighted:.6f} ± {error_weighted:.6f}")
            
            # Comparar con el mejor camino
            diff_offset = abs(offset_weighted - best_path['offset'])
            diff_error = abs(error_weighted - best_path['error'])
            print("\n📈 COMPARACIÓN CON MEJOR CAMINO:")
            print(f"   Diferencia en offset: {diff_offset:.6f}")
            print(f"   Diferencia en error:  {diff_error:.6f}")
            
            if error_weighted < best_path['error']:
                print(f"   ✅ Media ponderada tiene MENOR error ({error_weighted:.6f} < {best_path['error']:.6f})")
            else:
                print(f"   ℹ️  Mejor camino individual tiene menor error ({best_path['error']:.6f} < {error_weighted:.6f})")
        
        # 6. Preparar diccionario de información
        info = {
            'n_paths': len(all_paths),
            'n_raised_sensors': len(all_raised_sensors),
            'paths': all_paths,
            'best_path': best_path,
            'weights': weights,
            'offset_weighted': offset_weighted,
            'error_weighted': error_weighted,
            'offset_best': best_path['offset'],
            'error_best': best_path['error']
        }
        
        if verbose:
            print("="*80)
        
        return offset_weighted, error_weighted, info
    
    def _build_chain_with_specific_raised(
        self,
        sensor_id: int,
        current_set: int,
        raised_sensor: int,
        logfile_df: pd.DataFrame,
        verbose: bool = False
    ) -> List[Tuple[int, int, int]]:
        """
        Construye una cadena de calibración usando un sensor raised específico.
        
        Método auxiliar para compute_weighted_offset_all_paths().
        Similar a build_calibration_chain() pero fuerza el uso de un sensor raised concreto.
        
        Args:
            sensor_id: ID del sensor inicial
            current_set: Set donde está el sensor inicial
            raised_sensor: Sensor raised específico a usar
            logfile_df: DataFrame del LogFile
            verbose: Si True, imprime información
            
        Returns:
            List[Tuple[int, int, int]]: Cadena de (sensor_id, set_id, round_num)
        """
        chain = [(sensor_id, current_set, 1)]
        current_round = 1
        
        # Seguir la cadena desde este sensor raised específico
        while True:
            next_round = current_round + 1
            
            # Buscar en qué set de la siguiente ronda está este raised_sensor
            next_set = None
            
            for set_id in logfile_df['CalibSetNumber'].dropna().unique():
                try:
                    set_id_int = int(float(set_id))
                except (ValueError, TypeError, KeyError):
                    continue
                
                if set_id_int not in self.sets:
                    continue
                
                try:
                    round_num = self._get_set_round(set_id_int)
                except (ValueError, TypeError, KeyError):
                    continue
                
                if round_num != next_round:
                    continue
                
                set_rows = logfile_df[logfile_df['CalibSetNumber'] == set_id]
                if set_rows.empty:
                    continue
                
                sensor_values = []
                for col in [f'S{i}' for i in range(1, 21)]:
                    if col in set_rows.columns:
                        vals = set_rows[col].dropna().values
                        sensor_values.extend(vals)
                
                sensor_values_int = []
                for val in sensor_values:
                    try:
                        sensor_values_int.append(int(float(val)))
                    except (ValueError, TypeError):
                        pass
                
                if raised_sensor in sensor_values_int:
                    next_set = set_id_int
                    break
            
            if next_set is None:
                break
            
            # Obtener primer sensor del siguiente set
            set_rows_next = logfile_df[logfile_df['CalibSetNumber'] == next_set]
            if not set_rows_next.empty:
                first_sensor = None
                for col in [f'S{i}' for i in range(1, 21)]:
                    if col in set_rows_next.columns:
                        val = set_rows_next[col].dropna().values
                        if len(val) > 0:
                            try:
                                first_sensor = int(float(val[0]))
                                break
                            except (ValueError, TypeError):
                                pass
                
                if first_sensor is not None:
                    chain.append((first_sensor, next_set, next_round))
                else:
                    chain.append((raised_sensor, next_set, next_round))
            else:
                chain.append((raised_sensor, next_set, next_round))
            
            # Obtener próximo sensor raised del set actual
            if next_set not in self.config.get('sensors', {}).get('sets', {}):
                break
            
            next_config = self.config['sensors']['sets'][next_set]
            next_raised_sensors = next_config.get('raised', [])
            
            if not next_raised_sensors:
                break
            
            # Usar el primer raised del siguiente set
            raised_sensor = next_raised_sensors[0]
            current_set = next_set
            current_round = next_round
        
        return chain

    # ------------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------------
    def export_graph(self, filename="calibration_graph.png"):
        """
        Exports the graph as an image.
        """
        import matplotlib.pyplot as plt

        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(self.graph, seed=42)
        nx.draw(
            self.graph, pos,
            with_labels=True,
            node_color="skyblue",
            node_size=1200,
            font_size=10,
            edge_color="gray"
        )
        edge_labels = nx.get_edge_attributes(self.graph, "sensor")
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels)
        plt.title("Calibration Set Network")
        plt.tight_layout()
        plt.savefig(filename, dpi=150)
        plt.close()
        logger.info("Graph exported to %s", filename)

            # ------------------------------------------------------------------
    # CALCULO DE OFFSET ABSOLUTO HACIA SENSOR DE REFERENCIA DEL SET DE MAYOR RONDA
    # ------------------------------------------------------------------
    def compute_offset_to_top_reference(self, sensor_id: int, ref_set: Optional[Union[float, str]] = None):
        """
        Calcula el offset entre cualquier sensor (de ronda 1 o 2) y el sensor de referencia
        absoluto del set de referencia (ronda más alta). Sube el árbol acumulando offsets.
        
        Args:
            sensor_id (int): ID del sensor cuyo offset se quiere calcular
            ref_set (float or str, optional): Set de referencia. Si None, usa get_reference_set()
        
        Returns:
            Tuple[float, float, List[dict]]: (offset_total, error_total, pasos_detallados)
        """
        # --- 1. Definir la jerarquía ---
        round_by_set = {}
        for s, set_obj in self.sets.items():
            if hasattr(set_obj, "set_rounds") and s in set_obj.set_rounds:
                round_by_set[s] = set_obj.set_rounds[s]
            else:
                # Use configuration-based round detection
                round_by_set[s] = self._get_set_round(s)

        # --- 2. Definir sensor de referencia absoluto ---
        if ref_set is None:
            ref_set = self.get_reference_set()
            if ref_set is None:
                raise RuntimeError("No se pudo determinar el set de referencia (ningún set con ronda máxima)")
        
        if ref_set not in self.sets:
            raise RuntimeError(f"Set de referencia {ref_set} no está en sets_dict")
        
        ref_sensor = self._get_reference_sensor(ref_set)
        if ref_sensor is None:
            # Fallback to set object attributes
            if hasattr(self.sets[ref_set], "sensors_raised_by_set"):
                ref_sensors = getattr(self.sets[ref_set], "sensors_raised_by_set", {}).get(ref_set, [])
                if ref_sensors:
                    ref_sensor = ref_sensors[0]
            
            if ref_sensor is None:
                # Si el set de referencia es de Ronda 3 (referencia absoluta), 
                # usar el primer sensor del sensor mapping como referencia
                ref_round = round_by_set.get(ref_set, 0)
                if ref_round == 3:
                    # Intentar obtener el primer sensor del calibration_constants
                    df_ref = getattr(self.sets[ref_set], "calibration_constants", None)
                    if df_ref is not None and not df_ref.empty:
                        ref_sensor = df_ref.index[0]
                        logger.info("Set %s es Ronda 3 (referencia absoluta): usando primer sensor %s", ref_set, ref_sensor)
                    else:
                        raise RuntimeError(f"Set {ref_set} (Ronda 3) no tiene calibration_constants disponibles")
                else:
                    raise RuntimeError(f"Set {ref_set} (Ronda {ref_round}) no tiene sensores raised definidos en la configuración.")

        # Guardamos el sensor de referencia para usos futuros
        self.reference_sensor = ref_sensor
        self.reference_set = ref_set
        logger.info("Usando sensor de referencia absoluta %s del set %s (ronda %s)", ref_sensor, ref_set, round_by_set.get(ref_set, '?'))

        # --- 3. Encontrar el set del sensor de entrada ---
        set_i = self.find_sensor_set(sensor_id)
        if set_i is None:
            raise ValueError(f"No se encontró el set que contiene el sensor {sensor_id}")
        if set_i == ref_set:
            logger.info("Sensor %d ya está en el set de referencia %s", sensor_id, ref_set)
            return 0.0, 0.0, [{"info": f"sensor {sensor_id} ya está en el set de referencia"}]

        current_round = round_by_set.get(set_i, 1)
        ref_round = round_by_set.get(ref_set, 3)
        current_set = set_i
        current_sensor = sensor_id
        total_offset = 0.0
        total_error2 = 0.0
        pasos = []

        # --- 4. Función auxiliar para obtener offset seguro ---
        def safe_get(df, i, j):
            if df is None:
                return 0.0
            try:
                return df.loc[str(i), str(j)]
            except KeyError:
                try:
                    return -df.loc[str(j), str(i)]
                except KeyError:
                    logger.warning("No se encontró offset entre %s y %s en la matriz", i, j)
                    return 0.0

        # --- 5. Ir subiendo ronda a ronda hasta llegar al set de referencia ---
        max_iterations = 10  # Evitar loops infinitos
        iteration = 0
        while current_round < ref_round and iteration < max_iterations:
            iteration += 1
            
            # Si ya llegamos al set de referencia, salir del loop
            if current_set == ref_set:
                break
            
            # Obtener sensores raised del set actual
            raised = None
            if hasattr(self.sets[current_set], "sensors_raised_by_set"):
                raised = getattr(self.sets[current_set], "sensors_raised_by_set", {}).get(current_set, [])
            
            if not raised:
                # Try config
                raised = self.config.get("sensors", {}).get("sets", {}).get(str(current_set), {}).get("raised", [])
            
            if not raised:
                # Si es el set de referencia (Ronda 3), no necesita raised
                if current_set == ref_set:
                    break
                raise RuntimeError(f"Set {current_set} (ronda {current_round}) no tiene sensores raised definidos")

            bridge = raised[0]  # puente hacia siguiente ronda
            next_set = None

            # Buscar el set superior que contenga este bridge
            for s, obj in self.sets.items():
                if s == current_set:
                    continue
                
                # Verificar si este set es de la ronda siguiente
                if round_by_set.get(s, 0) != current_round + 1:
                    continue
                
                # Para sets de Ronda 3+ (referencia), buscar bridge en calibration_constants
                # porque estos sets no tienen "raised" definidos (ellos SON la referencia)
                next_round = round_by_set.get(s, 0)
                if next_round >= 3:
                    # Buscar bridge en los sensores del calibration_constants
                    df_next = getattr(obj, "calibration_constants", None)
                    if df_next is not None:
                        sensors_in_next = list(df_next.index)
                        # Comparar con normalización de tipos (int/str)
                        bridge_str = str(bridge)
                        sensors_str = [str(x) for x in sensors_in_next]
                        if bridge_str in sensors_str:
                            next_set = s
                            logger.info("Encontrado sensor puente %s en Set %s (Ronda %s, referencia)", bridge, s, next_round)
                            break
                else:
                    # Para Rondas 1-2, buscar en raised (lógica original)
                    raised_next = None
                    if hasattr(obj, "sensors_raised_by_set"):
                        raised_next = getattr(obj, "sensors_raised_by_set", {}).get(s, [])
                    
                    if not raised_next:
                        raised_next = self.config.get("sensors", {}).get("sets", {}).get(str(s), {}).get("raised", [])
                    
                    if raised_next:
                        # Comparar con normalización de tipos (int/str)
                        bridge_str = str(bridge)
                        raised_str = [str(x) for x in raised_next]
                        if bridge_str in raised_str:
                            next_set = s
                            break

            if next_set is None:
                raise RuntimeError(
                    f"No se encontró set de ronda {current_round + 1} que contenga el sensor puente {bridge} "
                    f"(desde set {current_set}, ronda {current_round})"
                )

            df_c = getattr(self.sets[current_set], "calibration_constants", None)
            df_e = getattr(self.sets[current_set], "calibration_errors", None)
            off = safe_get(df_c, current_sensor, bridge)
            err = safe_get(df_e, current_sensor, bridge) if df_e is not None else 0.0

            pasos.append({
                "from_set": current_set,
                "to_set": next_set,
                "from_sensor": current_sensor,
                "bridge_sensor": bridge,
                "offset": float(off),
                "error": float(err),
            })

            total_offset += float(off)
            total_error2 += float(err) ** 2

            current_sensor = bridge
            current_set = next_set
            current_round += 1

        if iteration >= max_iterations:
            raise RuntimeError(f"Excedido número máximo de iteraciones ({max_iterations}) al subir el árbol")

        # --- 6. Último paso: dentro del set de referencia ---
        df_c_ref = getattr(self.sets[ref_set], "calibration_constants", None)
        df_e_ref = getattr(self.sets[ref_set], "calibration_errors", None)
        off_final = safe_get(df_c_ref, current_sensor, ref_sensor)
        err_final = safe_get(df_e_ref, current_sensor, ref_sensor) if df_e_ref is not None else 0.0

        pasos.append({
            "from_set": ref_set,
            "from_sensor": current_sensor,
            "to_sensor": ref_sensor,
            "offset": float(off_final),
            "error": float(err_final),
        })

        total_offset += float(off_final)
        total_error2 += float(err_final) ** 2

        return total_offset, np.sqrt(total_error2), pasos
    
    # ------------------------------------------------------------------
    # RECORRIDO DE CAMINOS EN EL ÁRBOL Y PROMEDIO DE OFFSET
    # ------------------------------------------------------------------
    def compute_average_offset_to_reference(self, sensor_id: int, ref_set: Optional[Union[float, str]] = None):
        """
        Recorre todas las rutas posibles desde un sensor dado (de ronda 1 o 2)
        hasta el sensor de referencia del set de mayor ronda y devuelve:
          - offset medio acumulado
          - error medio (propagado cuadráticamente)
          - detalle de cada camino
        
        Args:
            sensor_id (int): ID del sensor
            ref_set (float or str, optional): Set de referencia. Si None, usa el guardado en self.reference_set
        
        Returns:
            Tuple[float, float, List[dict]]: (offset_promedio, error_promedio, caminos_detallados)
        """
        if ref_set is None:
            if not hasattr(self, "reference_sensor") or not hasattr(self, "reference_set"):
                # Compute it first
                logger.info("compute_average_offset_to_reference: calculando referencia automáticamente...")
                self.compute_offset_to_top_reference(sensor_id, ref_set=None)
            ref_set = self.reference_set

        ref_sensor = self.reference_sensor if hasattr(self, "reference_sensor") else self._get_reference_sensor(ref_set)
        if ref_sensor is None:
            raise RuntimeError("No se pudo determinar el sensor de referencia")

        set_i = self.find_sensor_set(sensor_id)
        if set_i is None:
            raise ValueError(f"No se encontró el set que contiene el sensor {sensor_id}")

        # --- 1. Convertimos el grafo en direccional (flechas de subida) ---
        G_up = nx.DiGraph()
        for u, v, data in self.graph.edges(data=True):
            round_u = self._get_set_round(u)
            round_v = self._get_set_round(v)
            if round_v == round_u + 1:
                G_up.add_edge(u, v, **data)  # dirección hacia arriba
            elif round_u == round_v + 1:
                G_up.add_edge(v, u, **data)

        # --- 2. Encontrar todos los caminos posibles hacia la referencia ---
        all_paths = list(nx.all_simple_paths(G_up, source=set_i, target=ref_set))
        if not all_paths:
            raise RuntimeError(f"No hay camino posible entre el set {set_i} y {ref_set}")

        path_results = []
        total_offsets = []
        total_errors2 = []

        # --- 3. Evaluar cada camino ---
        for path in all_paths:
            total_offset = 0.0
            total_error2 = 0.0
            current_sensor = sensor_id
            pasos = []

            def safe_get(df, i, j):
                try:
                    return df.loc[str(i), str(j)]
                except KeyError:
                    try:
                        return -df.loc[str(j), str(i)]
                    except KeyError:
                        return 0.0

            for a, b in zip(path[:-1], path[1:]):
                bridge = G_up[a][b]['sensor']
                df_c = getattr(self.sets[a], "calibration_constants", None)
                df_e = getattr(self.sets[a], "calibration_errors", None)
                off = safe_get(df_c, current_sensor, bridge)
                err = safe_get(df_e, current_sensor, bridge) if df_e is not None else 0.0

                pasos.append({
                    "from_set": a,
                    "to_set": b,
                    "from_sensor": current_sensor,
                    "bridge_sensor": bridge,
                    "offset": float(off),
                    "error": float(err),
                })

                total_offset += float(off)
                total_error2 += float(err) ** 2
                current_sensor = bridge

            # dentro del set 57
            df_c_ref = getattr(self.sets[ref_set], "calibration_constants", None)
            df_e_ref = getattr(self.sets[ref_set], "calibration_errors", None)
            off_final = safe_get(df_c_ref, current_sensor, ref_sensor)
            err_final = safe_get(df_e_ref, current_sensor, ref_sensor) if df_e_ref is not None else 0.0

            total_offset += float(off_final)
            total_error2 += float(err_final) ** 2

            pasos.append({
                "from_set": ref_set,
                "from_sensor": current_sensor,
                "to_sensor": ref_sensor,
                "offset": float(off_final),
                "error": float(err_final),
            })

            path_results.append({"path": path, "steps": pasos,
                                 "offset": total_offset, "error": np.sqrt(total_error2)})
            total_offsets.append(total_offset)
            total_errors2.append(total_error2)

        # --- 4. Calcular promedio global ---
        avg_offset = np.mean(total_offsets)
        avg_error = np.sqrt(np.mean(total_errors2))

        return avg_offset, avg_error, path_results


