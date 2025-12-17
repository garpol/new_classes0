"""
Test script para validar las mejoras en calibration_network.py
Enfocado en sets de ronda 1 y ronda 2 (según sensors.yaml)
"""
import sys
import os
import pandas as pd
import numpy as np

# Add project to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from RTD_Calibration_VGP.src.calibration_network import CalibrationNetwork
from RTD_Calibration_VGP.src.utils import load_config

def create_mock_set_object(set_id, sensor_ids, raised_sensors):
    """Create a mock Set object with calibration_constants and calibration_errors"""
    class MockSet:
        def __init__(self, set_id, sensor_ids, raised):
            self.runs_by_set = {set_id: {}}
            self.sensors_raised_by_set = {set_id: raised}
            
            # Create mock calibration matrices
            n = len(sensor_ids)
            # Offsets are small random values
            offsets = np.random.randn(n, n) * 0.001
            np.fill_diagonal(offsets, 0.0)
            
            # Errors are small positive values
            errors = np.abs(np.random.randn(n, n) * 0.0001)
            np.fill_diagonal(errors, 0.0)
            
            # Convert to DataFrames with string indices
            sensor_ids_str = [str(s) for s in sensor_ids]
            self.calibration_constants = pd.DataFrame(
                offsets,
                index=sensor_ids_str,
                columns=sensor_ids_str
            )
            self.calibration_errors = pd.DataFrame(
                errors,
                index=sensor_ids_str,
                columns=sensor_ids_str
            )
    
    return MockSet(set_id, sensor_ids, raised_sensors)

def test_basic_functionality():
    """Test 1: Verificar construcción básica del grafo"""
    print("\n" + "="*80)
    print("TEST 1: Construcción básica del grafo")
    print("="*80)
    
    # Load real config
    config_path = os.path.join(project_root, "RTD_Calibration_VGP/config/sensors.yaml")
    config = load_config(config_path)
    print(f"✅ Config cargado desde {config_path}")
    
    # Create mock sets for ronda 1 (sets 3, 4) y ronda 2 (set 49)
    # According to sensors.yaml:
    # Set 3: raised=[48203, 48479]
    # Set 4: raised=[48484, 48491]
    # Set 49: raised=[48484, 48747]  (bridge to set 4 via 48484)
    
    sets_dict = {}
    
    # Set 3 (ronda 1)
    set3_sensors = [48203, 48479, 48205, 48478]  # 2 raised + 2 discarded
    sets_dict[3.0] = create_mock_set_object(3.0, set3_sensors, [48203, 48479])
    
    # Set 4 (ronda 1)
    set4_sensors = [48484, 48491, 48485, 48490]  # 2 raised + 2 discarded
    sets_dict[4.0] = create_mock_set_object(4.0, set4_sensors, [48484, 48491])
    
    # Set 49 (ronda 2) - bridge sensor 48484 connects to set 4
    set49_sensors = [48484, 48747, 48203]  # includes bridges from set 3 and 4
    sets_dict[49.0] = create_mock_set_object(49.0, set49_sensors, [48484, 48747])
    
    # Create network
    net = CalibrationNetwork(sets_dict, config=config)
    
    print(f"✅ Red creada con {len(net.sets)} sets")
    print(f"   Nodos en grafo: {len(net.graph.nodes)}")
    print(f"   Aristas en grafo: {len(net.graph.edges)}")
    
    # Show connections
    net.show_graph_summary()
    
    return net

def test_round_detection(net):
    """Test 2: Verificar detección de rondas"""
    print("\n" + "="*80)
    print("TEST 2: Detección de rondas")
    print("="*80)
    
    sets_r1 = net.get_sets_by_round(1)
    sets_r2 = net.get_sets_by_round(2)
    sets_r3 = net.get_sets_by_round(3)
    
    print(f"Sets de ronda 1: {sets_r1}")
    print(f"Sets de ronda 2: {sets_r2}")
    print(f"Sets de ronda 3: {sets_r3}")
    
    assert 3.0 in sets_r1, "Set 3 debe estar en ronda 1"
    assert 4.0 in sets_r1, "Set 4 debe estar en ronda 1"
    assert 49.0 in sets_r2, "Set 49 debe estar en ronda 2"
    print("✅ Detección de rondas correcta")

def test_reference_sensor(net):
    """Test 3: Verificar obtención de sensores de referencia"""
    print("\n" + "="*80)
    print("TEST 3: Sensores de referencia")
    print("="*80)
    
    ref_set = net.get_reference_set()
    print(f"Set de referencia (mayor ronda): {ref_set}")
    
    ref_sensor_3 = net._get_reference_sensor(3.0)
    ref_sensor_4 = net._get_reference_sensor(4.0)
    ref_sensor_49 = net._get_reference_sensor(49.0)
    
    print(f"Sensor de referencia del set 3: {ref_sensor_3}")
    print(f"Sensor de referencia del set 4: {ref_sensor_4}")
    print(f"Sensor de referencia del set 49: {ref_sensor_49}")
    
    assert ref_sensor_3 == 48203, "Ref de set 3 debe ser 48203"
    assert ref_sensor_4 == 48484, "Ref de set 4 debe ser 48484"
    assert ref_sensor_49 == 48484, "Ref de set 49 debe ser 48484"
    print("✅ Sensores de referencia correctos")

def test_sensor_search(net):
    """Test 4: Verificar búsqueda de sensores en sets"""
    print("\n" + "="*80)
    print("TEST 4: Búsqueda de sensores")
    print("="*80)
    
    # Test finding sensors
    set_of_48203 = net.find_sensor_set(48203)
    set_of_48484 = net.find_sensor_set(48484)
    set_of_48747 = net.find_sensor_set(48747)
    
    print(f"Sensor 48203 está en set: {set_of_48203}")
    print(f"Sensor 48484 está en set: {set_of_48484} (debería estar en 4.0 y 49.0, retorna el primero)")
    print(f"Sensor 48747 está en set: {set_of_48747}")
    
    assert set_of_48203 == 3.0, "48203 debe estar en set 3"
    assert set_of_48484 in [4.0, 49.0], "48484 debe estar en set 4 o 49"
    assert set_of_48747 == 49.0, "48747 debe estar en set 49"
    print("✅ Búsqueda de sensores correcta")

def test_offset_calculation(net):
    """Test 5: Verificar cálculo de offsets entre sensores del mismo set"""
    print("\n" + "="*80)
    print("TEST 5: Cálculo de offsets dentro de un set")
    print("="*80)
    
    # Calculate offset between two sensors in set 3
    try:
        offset, error = net.compute_offset_between(48203, 48479)
        print(f"Offset entre 48203 y 48479 (set 3): {offset:.6f} K ± {error:.6f} K")
        assert isinstance(offset, (int, float)), "Offset debe ser numérico"
        assert isinstance(error, (int, float)), "Error debe ser numérico"
        print("✅ Cálculo de offset dentro de set correcto")
    except Exception as e:
        print(f"❌ Error calculando offset: {e}")
        raise

def test_path_finding(net):
    """Test 6: Verificar búsqueda de caminos entre sets"""
    print("\n" + "="*80)
    print("TEST 6: Búsqueda de caminos entre sets")
    print("="*80)
    
    # Find path from set 4 (ronda 1) to set 49 (ronda 2)
    try:
        path = net.find_path_between_sets(4.0, 49.0)
        print(f"Camino entre set 4 y set 49: {path}")
        assert len(path) >= 2, "Debe haber un camino de al menos 2 sets"
        assert path[0] == 4.0 and path[-1] == 49.0, "Camino debe empezar en 4 y terminar en 49"
        print("✅ Búsqueda de caminos correcta")
    except Exception as e:
        print(f"❌ Error buscando camino: {e}")
        raise

def test_dataframe_normalization(net):
    """Test 7: Verificar normalización de índices a string"""
    print("\n" + "="*80)
    print("TEST 7: Normalización de índices de DataFrames")
    print("="*80)
    
    for set_id, set_obj in net.sets.items():
        if hasattr(set_obj, 'calibration_constants') and set_obj.calibration_constants is not None:
            idx_types = set([type(x).__name__ for x in set_obj.calibration_constants.index])
            col_types = set([type(x).__name__ for x in set_obj.calibration_constants.columns])
            print(f"Set {set_id}: index types = {idx_types}, column types = {col_types}")
            assert idx_types == {'str'}, f"Índices de set {set_id} deben ser strings"
            assert col_types == {'str'}, f"Columnas de set {set_id} deben ser strings"
    
    print("✅ Todos los DataFrames tienen índices normalizados a string")

def run_all_tests():
    """Ejecutar todos los tests"""
    print("\n" + "="*80)
    print("🧪 INICIANDO TESTS DE CALIBRATION_NETWORK.PY")
    print("="*80)
    
    try:
        net = test_basic_functionality()
        test_round_detection(net)
        test_reference_sensor(net)
        test_sensor_search(net)
        test_offset_calculation(net)
        test_path_finding(net)
        test_dataframe_normalization(net)
        
        print("\n" + "="*80)
        print("✅ TODOS LOS TESTS PASARON CORRECTAMENTE")
        print("="*80)
        return True
        
    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ TESTS FALLARON: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
