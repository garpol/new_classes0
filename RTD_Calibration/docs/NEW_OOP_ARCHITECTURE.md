# 🏗️ Nueva Arquitectura OOP - Sistema de Calibración RTD

## 📋 Resumen Ejecutivo

Propuesta de reestructuración completa del código usando **Programación Orientada a Objetos** con clases simples y responsabilidades claras.

---

## 🎯 Jerarquía de Clases Propuesta

```
Tree (raíz)
  └── CalibrationSet (uno por cada set, ej: Set 3, Set 4...)
        ├── metadata: set_number, round, parent_set
        ├── reference_sensors: [Sensor, Sensor]  # 2 sensores de referencia
        ├── sensors: [Sensor × 12]  # 12 sensores a calibrar
        ├── runs: [Run, Run, ...]  # Múltiples experimentos
        └── calibration_results: dict  # Resultados finales
```

---

## 📦 1. Clase `Sensor` (Ya implementada - MUY SIMPLE ✓)

**Responsabilidad**: Representar un sensor RTD físico individual.

```python
class Sensor:
    """Sensor RTD físico - Ultra simple"""
    def __init__(self, sensor_id: int):
        self.id = sensor_id
        self.calibration_constant: Optional[float] = None
```

**Características**:
- ✅ Solo ID y constante de calibración
- ✅ Puede aparecer en múltiples sets
- ✅ No almacena datos temporales
- ✅ Es inmutable (representa objeto físico)

---

## 📦 2. Clase `Run` (Ya implementada - Necesita ajustes)

**Responsabilidad**: Un experimento individual (un archivo .txt).

```python
class Run:
    """Un experimento de calibración individual"""
    def __init__(self, filename: str, logfile: pd.DataFrame, 
                 reference_sensor_id: int):
        self.filename = filename
        self.set_number: int
        self.sensor_ids: List[int]  # IDs en este run
        self.reference_sensor_id: int
        self.is_valid: bool  # False si "BAD"
        
        # Resultados: offsets respecto a LA referencia
        self.offsets: Dict[int, float]  # {sensor_id: offset}
        self.time_window: Tuple[int, int] = (20, 40)
    
    def get_offsets(self) -> Dict[int, float]:
        """Retorna offsets calculados"""
        return self.offsets
```

**Características**:
- ✅ Carga archivo .txt
- ✅ Calcula offsets respecto a UNA referencia
- ✅ Sabe si es válido (BAD/GOOD)
- ✅ Retorna dict simple con offsets

---

## 📦 3. Clase `CalibrationSet` (NUEVA - Reemplaza `Set` actual)

**Responsabilidad**: Agrupa 12 sensores que se calibran juntos.

```python
class CalibrationSet:
    """
    Representa un conjunto de 12 sensores que se calibran juntos.
    Ejemplo: Set 3 tiene sensores [48060, 48061, ..., 48479]
    """
    def __init__(self, set_number: int, config: dict):
        # Identificación
        self.set_number = set_number
        self.round = config.get('round', 1)
        self.parent_set = config.get('parent_set', None)
        
        # Sensores (creados desde config.yml)
        self.sensors: List[Sensor] = []  # 12 sensores
        self.reference_sensors: List[Sensor] = []  # 2 referencias
        self.discarded_sensors: List[int] = []  # IDs descartados
        self.raised_sensors: List[int] = []  # IDs con problemas
        
        # Runs asociados a este set
        self.runs: List[Run] = []
        
        # Resultados finales
        self.calibration_constants: Dict[int, float] = {}  # {sensor_id: constant}
        self.calibration_errors: Dict[int, float] = {}  # {sensor_id: error}
        self.paths: Dict[int, List[str]] = {}  # {sensor_id: [caminos]}
        
        # Inicializar desde config
        self._initialize_from_config(config)
    
    def _initialize_from_config(self, config: dict):
        """Crea objetos Sensor desde config.yml"""
        # Crear sensores principales
        sensor_ids = config.get('sensors', [])
        self.sensors = [Sensor(sid) for sid in sensor_ids]
        
        # Crear sensores de referencia
        ref_ids = config.get('reference', [])
        self.reference_sensors = [Sensor(rid) for rid in ref_ids]
        
        # Metadata
        self.discarded_sensors = config.get('discarded', [])
        self.raised_sensors = config.get('raised', [])
    
    def add_run(self, run: Run):
        """Añade un Run a este set"""
        if run.set_number == self.set_number:
            self.runs.append(run)
    
    def calculate_calibration_constants(self):
        """
        Calcula constantes de calibración usando los runs.
        Implementa la lógica de media ponderada de caminos.
        """
        # Aquí va la lógica actual de Tree
        # - Construir caminos entre sensores
        # - Media ponderada de offsets
        # - Calcular constantes finales
        pass
    
    def get_sensor(self, sensor_id: int) -> Optional[Sensor]:
        """Busca un sensor por ID"""
        for sensor in self.sensors:
            if sensor.id == sensor_id:
                return sensor
        return None
    
    def is_sensor_discarded(self, sensor_id: int) -> bool:
        """Verifica si un sensor está descartado"""
        return sensor_id in self.discarded_sensors
    
    def is_sensor_raised(self, sensor_id: int) -> bool:
        """Verifica si un sensor tiene problemas"""
        return sensor_id in self.raised_sensors
    
    def __repr__(self):
        return f"CalibrationSet(set={self.set_number}, sensors={len(self.sensors)}, runs={len(self.runs)})"
```

**Características**:
- ✅ Contiene 12 sensores (objetos Sensor)
- ✅ Tiene 2 sensores de referencia
- ✅ Agrupa múltiples Runs
- ✅ Calcula constantes de calibración finales
- ✅ Se inicializa desde config.yml

---

## 📦 4. Clase `Tree` (Simplificada - Organizador de Sets)

**Responsabilidad**: Organizar todos los CalibrationSet y crear la estructura.

```python
class Tree:
    """
    Árbol completo de calibración.
    Organiza todos los CalibrationSet y sabe cómo están conectados.
    """
    def __init__(self, config: dict, logfile: pd.DataFrame):
        self.config = config
        self.logfile = logfile
        
        # Estructura principal: dict de CalibrationSet
        self.sets: Dict[int, CalibrationSet] = {}
        
        # Crear estructura vacía desde config
        self._build_structure()
    
    def _build_structure(self):
        """
        Crea todos los CalibrationSet desde config.yml.
        Inicialmente están "vacíos" (sin runs ni constantes).
        """
        sets_config = self.config.get('sensors', {}).get('sets', {})
        
        for set_number, set_config in sets_config.items():
            set_num = int(set_number)
            calib_set = CalibrationSet(set_num, set_config)
            self.sets[set_num] = calib_set
        
        print(f"✓ Estructura creada: {len(self.sets)} CalibrationSets")
    
    def load_runs_for_set(self, set_number: int, filenames: List[str]):
        """
        Carga runs para un set específico.
        Usa la primera referencia del set por defecto.
        """
        if set_number not in self.sets:
            print(f"Error: Set {set_number} no existe")
            return
        
        calib_set = self.sets[set_number]
        
        # Usar primera referencia
        ref_id = calib_set.reference_sensors[0].id
        
        for fname in filenames:
            run = Run(fname, self.logfile, reference_sensor_id=ref_id)
            if run.is_valid:
                calib_set.add_run(run)
    
    def calibrate_set(self, set_number: int):
        """
        Calibra un set específico usando todos sus runs.
        """
        if set_number not in self.sets:
            print(f"Error: Set {set_number} no existe")
            return
        
        calib_set = self.sets[set_number]
        calib_set.calculate_calibration_constants()
        
        # Actualizar constantes en objetos Sensor
        for sensor in calib_set.sensors:
            if sensor.id in calib_set.calibration_constants:
                sensor.calibration_constant = calib_set.calibration_constants[sensor.id]
    
    def calibrate_all(self):
        """Calibra todos los sets"""
        for set_number in self.sets:
            self.calibrate_set(set_number)
    
    def get_set(self, set_number: int) -> Optional[CalibrationSet]:
        """Obtiene un CalibrationSet por número"""
        return self.sets.get(set_number)
    
    def get_all_sensors(self) -> List[Sensor]:
        """Retorna todos los sensores únicos en el árbol"""
        all_sensors = {}
        for calib_set in self.sets.values():
            for sensor in calib_set.sensors:
                all_sensors[sensor.id] = sensor
        return list(all_sensors.values())
    
    def __repr__(self):
        return f"Tree(sets={len(self.sets)}, total_sensors={len(self.get_all_sensors())})"
```

**Características**:
- ✅ Organiza todos los CalibrationSet
- ✅ Crea estructura "vacía" desde config.yml
- ✅ Carga runs cuando sea necesario
- ✅ Coordina calibración de todos los sets
- ✅ Sabe qué sets están conectados (parent_set)

---

## 🔄 Flujo de Trabajo Completo

### Paso 1: Crear estructura vacía
```python
# Cargar config y logfile
config = load_config()
logfile = pd.read_csv("LogFile.csv")

# Crear árbol vacío (solo estructura)
tree = Tree(config, logfile)
# Output: ✓ Estructura creada: 60 CalibrationSets
# Los sets existen pero no tienen runs ni constantes
```

### Paso 2: Cargar runs para un set específico
```python
# Cargar runs del Set 3
filenames = [
    "20220201_ln2_r48176_r48177_487178-48189_1",
    "20220201_ln2_r48176_r48177_487178-48189_2",
    "20220201_ln2_r48176_r48177_487178-48189_3",
]

tree.load_runs_for_set(set_number=3, filenames=filenames)
# Los runs se añaden al Set 3
```

### Paso 3: Calibrar un set
```python
# Calibrar Set 3 usando todos sus runs
tree.calibrate_set(3)

# Ver resultados
set_3 = tree.get_set(3)
for sensor in set_3.sensors:
    print(f"Sensor {sensor.id}: {sensor.calibration_constant}")
```

### Paso 4: Calibrar todos los sets
```python
# Primero cargar todos los runs necesarios
# Luego calibrar todo
tree.calibrate_all()

# Exportar resultados
all_sensors = tree.get_all_sensors()
results = [(s.id, s.calibration_constant) for s in all_sensors]
```

---

## 🎨 Ventajas de esta Arquitectura

### ✅ 1. Separación de Responsabilidades
- **Sensor**: Solo ID y constante (super simple)
- **Run**: Carga archivo y calcula offsets
- **CalibrationSet**: Agrupa sensores y coordina calibración
- **Tree**: Organiza sets y estructura global

### ✅ 2. Estructura Vacía Primero
- El Tree se crea desde config.yml
- Los CalibrationSet existen aunque no tengan datos
- Los Runs se cargan solo cuando sea necesario
- Permite trabajar con estructura antes de tener datos

### ✅ 3. Flexibilidad
- Puedes calibrar un set sin tocar otros
- Fácil añadir/quitar runs
- Cambiar referencias fácilmente
- Probar diferentes algoritmos de calibración

### ✅ 4. Código Limpio
- Cada clase hace una cosa
- No hay código duplicado
- Fácil de testear
- Fácil de explicar al tutor

---

## 📝 Migración Sugerida

### Fase 1: Clases Base (YA HECHO ✓)
- ✅ Sensor simplificado
- ✅ Run simplificado

### Fase 2: CalibrationSet (SIGUIENTE)
- Crear clase CalibrationSet
- Migrar lógica de cálculo de constantes desde Set actual
- Implementar media ponderada de caminos

### Fase 3: Tree (FINAL)
- Simplificar Tree a organizador de sets
- Crear estructura desde config.yml
- Coordinar calibración

### Fase 4: Limpieza
- Eliminar código antiguo
- Actualizar notebooks
- Documentar

---

## 🤔 Preguntas para Resolver

1. **Nombre de CalibrationSet**: ¿Te gusta "CalibrationSet" o prefieres otro nombre?
   - Alternativas: `SensorSet`, `CalibrationGroup`, `SetEntry`

2. **Algoritmo de caminos**: ¿La media ponderada actual va en `CalibrationSet.calculate_calibration_constants()`?

3. **Runs múltiples**: ¿Un CalibrationSet puede tener runs con diferentes referencias?

4. **Parent set**: ¿Cómo se usa la info de `parent_set`? ¿Para construir caminos entre sets?

---

## 💡 Próximos Pasos

1. Revisar esta propuesta contigo
2. Ajustar nombres y responsabilidades
3. Implementar `CalibrationSet`
4. Migrar lógica de cálculo
5. Simplificar `Tree`

---

**¿Qué te parece esta arquitectura? ¿Algún cambio o mejora?** 🚀
