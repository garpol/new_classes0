# Run Class - Simplificación Radical ✅

## Cambios Realizados

### 1. **Run Class Simplificada** (62 líneas vs 245 anteriores)

**Antes:**
- 245 líneas con múltiples métodos
- Cargaba archivos, procesaba datos, calculaba offsets
- Conocía config, logfile, referencias, ventanas temporales
- Mezcla de datos + lógica

**Después:**
- 62 líneas ultra-simple
- Solo **almacena datos** (data class pura)
- No hace cálculos
- No entiende de sets ni referencias

```python
class Run:
    """Data class: almacena datos crudos de un experimento"""
    
    def __init__(self, filename: str):
        self.filename = filename
        
        # Datos raw del archivo
        self.timestamps = None
        self.temperatures = None  # DataFrame con sensor_ids como columnas
        self.sensor_ids = []
        
        # Resultados (calculados externamente)
        self.offsets = {}  # {sensor_id: offset}
        self.is_valid = True  # False si 'BAD'
```

---

### 2. **Funciones de Utils** (todo el procesamiento)

Añadidas 3 funciones principales en `utils.py`:

#### `load_run_from_file(filename, config) → Run`
- Busca archivo .txt recursivamente
- Lee y parsea Date/Time
- Extrae canales de temperatura (channel_1 a channel_14)
- Filtra temperaturas fuera de rango
- **Retorna Run con datos crudos**

#### `map_sensor_ids_to_run(run, logfile, config) → None`
- Busca filename en logfile
- Extrae sensor_ids (S1-S20)
- Renombra columnas: `channel_X` → `sensor_id`
- Marca `is_valid` (BAD/GOOD)
- **Modifica run in-place**

#### `calculate_run_offsets(run, reference_id, time_window) → None`
- Selecciona ventana temporal estable (ej: 20-40 min)
- Calcula: `offset[sensor] = mean(T_sensor - T_ref)`
- Solo primeros 12 sensores (ignora refs canales 13-14)
- **Retorna 12 offsets** (no 13)
- **Modifica run.offsets in-place**

---

### 3. **Flujo de Uso**

```python
# 1. Crear Run vacío
run = Run("20220201_ln2_r48176_r48177_487178-48189_1")

# 2. Cargar datos del archivo
run = utils.load_run_from_file(run.filename, config)
# → run.timestamps, run.temperatures cargados

# 3. Mapear IDs de sensores
utils.map_sensor_ids_to_run(run, logfile, config)
# → run.sensor_ids = [48060, 48061, ..., 48177]
# → run.temperatures columnas renombradas a IDs

# 4. Calcular offsets respecto a referencia
utils.calculate_run_offsets(run, reference_id=48176, time_window=(20, 40))
# → run.offsets = {48060: 0.123, 48061: -0.045, ...}
```

---

### 4. **Ventajas de la Nueva Arquitectura**

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Líneas en Run** | 245 | 62 (-75%) |
| **Responsabilidad** | Datos + Lógica | Solo Datos |
| **Testabilidad** | Difícil (clase grande) | Fácil (funciones puras) |
| **Reutilización** | Acoplada | Composable |
| **Dependencias** | Run depende de todo | Run no depende de nada |

---

### 5. **Relación con config.yml**

El `config.yml` ahora tiene `parent_set` en cada set:

```yaml
sensors:
  sets:
    3.0:
      parent_set: 49.0
      round: 1
      reference: [48176, 48177]
      sensors: [48060, 48061, ...]
      raised: [48203, 48479]
      discarded: [48205, 48478]
```

**Esto facilita:**
- Tree conoce relaciones parent-child directamente
- No necesita calcular parent sets
- CalibrationSet puede leer sus runs del config
- Tree.print_structure() funciona desde el inicio

---

### 6. **Conceptos Clave Recordados**

✅ **Run contiene:**
- Tiempos (timestamps)
- Temperaturas (DataFrame)
- **Offsets (12 números)**: medias de diferencias con referencia

✅ **Run NO entiende:**
- De qué set forma parte
- Quién es su referencia
- Qué ventana temporal usar

✅ **Referencias (canales 13-14):**
- Se alejan del cálculo de offsets
- No calculamos sus constantes (de momento)
- Solo los primeros 12 sensores tienen offsets

✅ **Tree-entry conoce:**
- Runs del set
- Sets hijos (parent_set)
- Relaciones de raised sensors
- Rounds (1-3)

---

### 7. **Próximos Pasos**

1. ✅ **Run simplificado** → COMPLETADO
2. 🔨 **CalibrationSet** → Crear clase simple
3. 🔨 **Tree** → Simplificar a estructura + relaciones
4. 🔨 **utils.py** → Añadir funciones para CalibrationSet y Tree
5. 🔨 **main.py** → Orquestar todo el flujo

---

### 8. **Archivos Modificados**

```
RTD_Calibration/
├── src/
│   ├── run.py              ← 62 líneas (antes 245) ✅
│   └── utils.py            ← +150 líneas de funciones ✅
├── notebooks/
│   └── RUN_SIMPLE.ipynb    ← Ejemplo completo ✅
└── config/
    └── config.yml          ← parent_set añadido ✅
```

---

## Resumen Ejecutivo

**De abajo arriba** → Empezamos por Run ✅

- **Run**: 62 líneas, data class pura
- **utils.py**: 3 funciones de procesamiento
- **Notebook**: Ejemplo interactivo completo
- **Separación clara**: Data (Run) vs Logic (utils)

**Siguiente:** CalibrationSet (clase simple con lista de runs)
