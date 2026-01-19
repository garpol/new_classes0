# 🔥 Propuesta Radical de Simplificación - Feedback del Tutor

## 📋 Feedback Clave del Tutor

1. ✅ **Run NO debe entender de sets** - Solo carga datos y calcula offsets
2. ✅ **Clases MUY CORTAS** - Solo estructura de datos (data classes)
3. ✅ **Maquinaria en utils.py** - Todas las funciones de cálculo aparte
4. ✅ **Tree conoce las relaciones** - Es quien entiende la estructura
5. ✅ **CalibSet calcula media de offsets** - Pero NO referencia absoluta aún
6. ✅ **Tree-entrie calcula constantes finales** - Con referencia absoluta
7. ✅ **main.py aplica maquinaria** - Orquesta todo el proceso

---

## 🎯 Nueva Arquitectura Simplificada

### Filosofía: "Clases vacías + Relleno de datos + Aplicar maquinaria"

```
1. Clases vacías (data classes)     → Estructura pura
2. Funciones en utils.py            → Maquinaria de cálculo
3. main.py orquesta                 → Flujo de trabajo
```

---

## 📦 1. Clase `Sensor` - DATA CLASS (YA ESTÁ BIEN ✓)

```python
class Sensor:
    """Representa un sensor físico RTD - DATA CLASS"""
    def __init__(self, sensor_id: int):
        self.id = sensor_id
        self.calibration_constant: Optional[float] = None
    
    def __repr__(self):
        return f"Sensor(id={self.id}, cal={self.calibration_constant})"
    
    def __eq__(self, other):
        return isinstance(other, Sensor) and self.id == other.id
    
    def __hash__(self):
        return hash(self.id)
```

**✓ Perfecta**: Solo datos, sin lógica

---

## 📦 2. Clase `Run` - SIMPLIFICAR RADICALMENTE

### ❌ Problema Actual:
- Run entiende de sets (lee `set_number` del logfile)
- Run calcula offsets internamente
- Run conoce ventanas temporales
- Demasiada lógica dentro

### ✅ Nueva Versión (Solo Datos):

```python
class Run:
    """
    Contenedor de datos de un experimento - DATA CLASS
    NO entiende de sets, solo almacena datos crudos.
    """
    def __init__(self, filename: str):
        self.filename = filename
        
        # Datos crudos (sin procesar)
        self.temperature_data: Optional[pd.DataFrame] = None
        self.sensor_ids: List[int] = []
        
        # Metadata básica (del archivo, NO del logfile)
        self.is_valid: bool = True
        
        # Resultados (se llenan desde fuera)
        self.offsets: Dict[int, float] = {}  # Se calcula con función externa
    
    def __repr__(self):
        return f"Run(file={self.filename}, sensors={len(self.sensor_ids)})"
```

**Maquinaria movida a utils.py:**
```python
# En utils.py
def load_run_data(run: Run, data_dir: str) -> Run:
    """Carga datos de temperatura para un Run"""
    # Lógica actual de _load_temperature_file()
    pass

def calculate_run_offsets(run: Run, reference_id: int, 
                         time_window: Tuple[int, int]) -> Dict[int, float]:
    """Calcula offsets de un Run respecto a una referencia"""
    # Lógica actual de _calculate_offsets()
    return offsets
```

---

## 📦 3. Clase `CalibrationSet` - NUEVA (MUY CORTA)

```python
class CalibrationSet:
    """
    Agrupa sensores y runs de un set de calibración - DATA CLASS
    NO calcula constantes finales, solo media de offsets de sus runs.
    """
    def __init__(self, set_number: int):
        self.set_number = set_number
        self.round: int = 1
        self.parent_set: Optional[int] = None
        
        # Sensores (objetos vacíos al inicio)
        self.sensors: List[Sensor] = []          # 12 sensores
        self.reference_sensors: List[Sensor] = []  # 2 referencias
        self.discarded_ids: List[int] = []
        self.raised_ids: List[int] = []
        
        # Runs asociados (se añaden después)
        self.runs: List[Run] = []
        
        # Resultados intermedios (media de offsets de los runs)
        self.mean_offsets: Dict[int, float] = {}   # Media simple
        self.offset_errors: Dict[int, float] = {}  # Desviación estándar
        
        # Constantes finales (se calculan en Tree, NO aquí)
        # self.calibration_constants NO existe en CalibrationSet
    
    def __repr__(self):
        return f"CalibSet(n={self.set_number}, round={self.round}, sensors={len(self.sensors)}, runs={len(self.runs)})"
```

**Maquinaria movida a utils.py:**
```python
# En utils.py
def initialize_calibset_from_config(set_number: int, config: dict) -> CalibrationSet:
    """Crea CalibrationSet vacío desde config.yml"""
    calib_set = CalibrationSet(set_number)
    set_config = config['sensors']['sets'][set_number]
    
    # Crear sensores vacíos
    calib_set.sensors = [Sensor(sid) for sid in set_config['sensors']]
    calib_set.reference_sensors = [Sensor(rid) for rid in set_config['reference']]
    calib_set.discarded_ids = set_config.get('discarded', [])
    calib_set.raised_ids = set_config.get('raised', [])
    calib_set.round = set_config.get('round', 1)
    calib_set.parent_set = set_config.get('parent_set', None)
    
    return calib_set

def calculate_calibset_mean_offsets(calib_set: CalibrationSet) -> Dict[int, float]:
    """
    Calcula media de offsets de todos los runs del set.
    NO referencia a set absoluto, solo promedia offsets.
    """
    # Todos los runs del set tienen la misma referencia
    all_offsets = {}
    for run in calib_set.runs:
        for sensor_id, offset in run.offsets.items():
            if sensor_id not in all_offsets:
                all_offsets[sensor_id] = []
            all_offsets[sensor_id].append(offset)
    
    # Media simple
    mean_offsets = {sid: np.mean(vals) for sid, vals in all_offsets.items()}
    offset_errors = {sid: np.std(vals) for sid, vals in all_offsets.items()}
    
    calib_set.mean_offsets = mean_offsets
    calib_set.offset_errors = offset_errors
    
    return mean_offsets
```

---

## 📦 4. Clase `Tree` - SIMPLIFICAR A ORGANIZADOR

```python
class Tree:
    """
    Organizador de toda la estructura de calibración - DATA CLASS + RELACIONES
    Conoce cómo están conectados los CalibrationSets.
    NO calcula constantes, solo organiza y conoce relaciones.
    """
    def __init__(self, config: dict):
        self.config = config
        
        # Estructura principal: dict de CalibrationSets vacíos
        self.sets: Dict[int, CalibrationSet] = {}
        
        # Relaciones entre sets (derivadas de config.yml)
        self.parent_child_relations: Dict[int, List[int]] = {}  # {child: [parents]}
        self.sets_by_round: Dict[int, List[int]] = {1: [], 2: [], 3: []}
        
        # Construir estructura vacía
        self._build_empty_structure()
        self._derive_relations()
    
    def _build_empty_structure(self):
        """Crea todos los CalibrationSets vacíos desde config.yml"""
        sets_config = self.config['sensors']['sets']
        
        for set_number in sets_config.keys():
            calib_set = initialize_calibset_from_config(int(set_number), self.config)
            self.sets[int(set_number)] = calib_set
            
            # Clasificar por ronda
            round_num = calib_set.round
            self.sets_by_round[round_num].append(int(set_number))
    
    def _derive_relations(self):
        """
        Deriva relaciones parent-child automáticamente desde config.yml
        analizando sensores raised.
        """
        # Lógica actual de _find_parent_sets()
        # Movida aquí porque es ESTRUCTURA, no CÁLCULO
        pass
    
    def print_structure(self):
        """Imprime estructura clara del árbol"""
        print("\n" + "="*60)
        print("ESTRUCTURA DEL ÁRBOL DE CALIBRACIÓN")
        print("="*60)
        
        for round_num in [1, 2, 3]:
            sets = self.sets_by_round[round_num]
            if not sets:
                continue
            
            print(f"\n📊 RONDA {round_num}: {len(sets)} sets")
            for set_num in sorted(sets):
                calib_set = self.sets[set_num]
                refs = [s.id for s in calib_set.reference_sensors]
                raised = calib_set.raised_ids
                parents = self.parent_child_relations.get(set_num, [])
                
                print(f"  Set {set_num:2d}: {len(calib_set.sensors):2d} sensores | "
                      f"Refs: {refs} | Raised: {raised[:2]}{'...' if len(raised)>2 else ''} | "
                      f"Parents: {parents}")
        
        print("\n" + "="*60)
    
    def get_calibset(self, set_number: int) -> Optional[CalibrationSet]:
        """Obtiene un CalibrationSet"""
        return self.sets.get(set_number)
    
    def add_run_to_set(self, run: Run, set_number: int):
        """Añade un Run a un CalibrationSet"""
        if set_number in self.sets:
            self.sets[set_number].runs.append(run)
    
    def __repr__(self):
        total_sensors = sum(len(cs.sensors) for cs in self.sets.values())
        total_runs = sum(len(cs.runs) for cs in self.sets.values())
        return f"Tree(sets={len(self.sets)}, sensors={total_sensors}, runs={total_runs})"
```

**Maquinaria movida a utils.py:**
```python
# En utils.py
def calculate_tree_calibration_constants(tree: Tree) -> Dict[int, float]:
    """
    Calcula constantes finales usando el árbol completo.
    Referencia a set absoluto (Set 57 o el de ronda máxima).
    
    Esta es la función PRINCIPAL que implementa:
    - Construcción de caminos entre sets
    - Media ponderada de caminos
    - Propagación de errores
    - Referencia a set absoluto
    """
    # Lógica actual de Tree.calculate_all_offsets()
    # Movida TODA a utils.py
    pass
```

---

## 📦 5. utils.py - TODA LA MAQUINARIA

```python
# utils.py - FUNCIONES DE CÁLCULO

# ============================================================================
# CARGA DE DATOS
# ============================================================================

def load_run_data(run: Run, data_dir: str) -> Run:
    """Carga datos de temperatura de un archivo .txt"""
    pass

def get_run_metadata_from_logfile(filename: str, logfile: pd.DataFrame) -> dict:
    """Extrae metadata de un run desde logfile (set_number, validez, etc.)"""
    pass

# ============================================================================
# CÁLCULOS DE RUN
# ============================================================================

def calculate_run_offsets(run: Run, reference_id: int, 
                         time_window: Tuple[int, int] = (20, 40)) -> Dict[int, float]:
    """Calcula offsets de un Run respecto a una referencia"""
    pass

# ============================================================================
# CÁLCULOS DE CALIBRATIONSET
# ============================================================================

def calculate_calibset_mean_offsets(calib_set: CalibrationSet) -> Dict[int, float]:
    """Media simple de offsets de los runs de un set"""
    pass

# ============================================================================
# CONSTRUCCIÓN DE ESTRUCTURA
# ============================================================================

def initialize_calibset_from_config(set_number: int, config: dict) -> CalibrationSet:
    """Crea CalibrationSet vacío desde config.yml"""
    pass

def derive_parent_child_relations(tree: Tree) -> Dict[int, List[int]]:
    """Deriva relaciones entre sets analizando sensores raised"""
    pass

# ============================================================================
# CÁLCULOS GLOBALES (TREE)
# ============================================================================

def find_paths_between_sensors(tree: Tree, sensor_from: int, 
                               sensor_to: int) -> List[List[int]]:
    """Encuentra todos los caminos entre dos sensores en el árbol"""
    pass

def calculate_offset_along_path(tree: Tree, path: List[int]) -> Tuple[float, float]:
    """Calcula offset y error a lo largo de un camino de sensores"""
    pass

def weighted_average_of_paths(offsets: List[float], 
                              errors: List[float]) -> Tuple[float, float]:
    """Media ponderada de múltiples caminos"""
    pass

def calculate_tree_calibration_constants(tree: Tree, 
                                        absolute_reference_set: int = 57) -> Dict[int, float]:
    """
    FUNCIÓN PRINCIPAL: Calcula constantes finales para todos los sensores.
    Referencia al set absoluto (Set 57 por defecto).
    
    Esta es la "maquinaria pesada" que:
    1. Para cada sensor, encuentra caminos al set de referencia absoluta
    2. Calcula offset a lo largo de cada camino
    3. Hace media ponderada de todos los caminos
    4. Asigna constante final al sensor
    """
    calibration_constants = {}
    
    # Para cada sensor en el árbol
    for set_num, calib_set in tree.sets.items():
        for sensor in calib_set.sensors:
            # Encontrar caminos al set absoluto
            paths = find_paths_to_absolute_reference(tree, sensor.id, absolute_reference_set)
            
            # Calcular offset de cada camino
            path_offsets = []
            path_errors = []
            for path in paths:
                offset, error = calculate_offset_along_path(tree, path)
                path_offsets.append(offset)
                path_errors.append(error)
            
            # Media ponderada
            if path_offsets:
                final_offset, final_error = weighted_average_of_paths(path_offsets, path_errors)
                calibration_constants[sensor.id] = final_offset
                sensor.calibration_constant = final_offset  # Actualizar objeto
    
    return calibration_constants

# ============================================================================
# EXPORTACIÓN
# ============================================================================

def export_calibration_results(tree: Tree, output_path: str):
    """Exporta resultados a CSV/Excel"""
    pass
```

---

## 📦 6. main.py - ORQUESTACIÓN

```python
# main.py - FLUJO PRINCIPAL

from RTD_Calibration.src.sensor import Sensor
from RTD_Calibration.src.run import Run
from RTD_Calibration.src.calibration_set import CalibrationSet
from RTD_Calibration.src.tree import Tree
from RTD_Calibration.src import utils
import pandas as pd

def main():
    """Flujo principal de calibración"""
    
    print("="*60)
    print("SISTEMA DE CALIBRACIÓN RTD - FLUJO PRINCIPAL")
    print("="*60)
    
    # ========================================================================
    # PASO 1: CREAR ESTRUCTURA VACÍA
    # ========================================================================
    print("\n[1] Creando estructura vacía desde config.yml...")
    config = utils.load_config()
    tree = Tree(config)
    tree.print_structure()
    
    # ========================================================================
    # PASO 2: CARGAR LOGFILE
    # ========================================================================
    print("\n[2] Cargando logfile...")
    logfile = pd.read_csv("data/LogFile.csv")
    
    # ========================================================================
    # PASO 3: CARGAR RUNS Y LLENAR DATOS
    # ========================================================================
    print("\n[3] Cargando runs y calculando offsets...")
    
    # Para cada entrada del logfile
    for idx, row in logfile.iterrows():
        filename = row['Filename']
        set_number = int(row['CalibSetNumber']) if pd.notna(row['CalibSetNumber']) else None
        is_valid = row.get('Selection', 'GOOD') != 'BAD'
        
        if set_number is None or not is_valid:
            continue
        
        # Crear Run (vacío)
        run = Run(filename)
        run.is_valid = is_valid
        
        # Cargar datos (función externa)
        run = utils.load_run_data(run, data_dir="data/temperature_files")
        
        # Obtener IDs de sensores del logfile
        sensor_cols = [f'S{i}' for i in range(1, 21)]
        sensor_ids = [int(row[col]) for col in sensor_cols if pd.notna(row[col])]
        run.sensor_ids = sensor_ids
        
        # Obtener referencia del set (TODOS los runs de un set usan la misma ref)
        calib_set = tree.get_calibset(set_number)
        reference_id = calib_set.reference_sensors[0].id
        
        # Calcular offsets (función externa)
        run.offsets = utils.calculate_run_offsets(run, reference_id)
        
        # Añadir run al set
        tree.add_run_to_set(run, set_number)
    
    # ========================================================================
    # PASO 4: CALCULAR MEDIAS DE OFFSETS POR SET
    # ========================================================================
    print("\n[4] Calculando medias de offsets por set...")
    
    for set_num, calib_set in tree.sets.items():
        if calib_set.runs:
            utils.calculate_calibset_mean_offsets(calib_set)
            print(f"  Set {set_num}: {len(calib_set.runs)} runs procesados")
    
    # ========================================================================
    # PASO 5: CALCULAR CONSTANTES FINALES (MAQUINARIA PESADA)
    # ========================================================================
    print("\n[5] Calculando constantes de calibración finales...")
    print("    (Referencia al Set 57 - Set absoluto)")
    
    calibration_constants = utils.calculate_tree_calibration_constants(
        tree, 
        absolute_reference_set=57
    )
    
    print(f"  ✓ Constantes calculadas para {len(calibration_constants)} sensores")
    
    # ========================================================================
    # PASO 6: EXPORTAR RESULTADOS
    # ========================================================================
    print("\n[6] Exportando resultados...")
    utils.export_calibration_results(tree, "results/calibration_constants.csv")
    
    print("\n" + "="*60)
    print("✓ CALIBRACIÓN COMPLETADA")
    print("="*60)

if __name__ == "__main__":
    main()
```

---

## 🎯 Ventajas de esta Arquitectura

### ✅ 1. Clases Ultra Cortas
- Sensor: ~20 líneas
- Run: ~20 líneas
- CalibrationSet: ~30 líneas
- Tree: ~80 líneas (estructura + relaciones)

### ✅ 2. Separación Clara
- **Clases** = Estructura de datos (data classes)
- **utils.py** = Maquinaria de cálculo (funciones puras)
- **main.py** = Orquestación (flujo de trabajo)

### ✅ 3. Run NO Entiende de Sets
- Run solo carga datos
- El set_number se obtiene del logfile en main.py
- Tree decide a qué set pertenece cada run

### ✅ 4. Tree Conoce Relaciones
- Deriva parent-child desde config.yml
- Sabe qué sets están conectados
- Coordina la estructura

### ✅ 5. CalibrationSet Simple
- Solo promedia offsets de sus runs
- NO conoce referencia absoluta
- NO calcula constantes finales

### ✅ 6. Maquinaria en utils.py
- Todas las funciones de cálculo
- Fácil de testear individualmente
- Reutilizable

### ✅ 7. main.py Clara
- Flujo visible y entendible
- Paso a paso documentado
- Fácil de modificar

---

## 📋 Migración Sugerida

### Fase 1: Simplificar Clases (1-2 días)
1. ✅ Mantener Sensor como está
2. 🔨 Simplificar Run (solo datos)
3. 🔨 Crear CalibrationSet simple
4. 🔨 Simplificar Tree (solo estructura)

### Fase 2: Mover Maquinaria a utils.py (2-3 días)
1. 🔨 Mover cálculos de Run
2. 🔨 Mover cálculos de Set
3. 🔨 Mover cálculos de Tree
4. 🔨 Organizar funciones por categoría

### Fase 3: Crear main.py (1 día)
1. 🔨 Flujo principal
2. 🔨 Documentación clara
3. 🔨 Logs informativos

### Fase 4: Testing y Limpieza (1-2 días)
1. 🔨 Tests unitarios de utils.py
2. 🔨 Validar resultados
3. 🔨 Eliminar código antiguo

---

## ✅ Resumen para el Tutor

**Esta arquitectura:**
- ✅ Clases MUY cortas (data classes)
- ✅ Run NO entiende de sets
- ✅ Maquinaria en utils.py
- ✅ Tree conoce relaciones
- ✅ CalibrationSet solo promedia offsets
- ✅ main.py orquesta todo
- ✅ Fácil de explicar y mantener
- ✅ Testeable y modular

**¿Procedemos con esta reestructuración?** 🚀
