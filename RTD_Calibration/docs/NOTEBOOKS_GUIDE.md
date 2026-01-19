# Guía de Notebooks: TREE vs TREE_CALIBRATION

## 📚 Resumen Rápido

| Aspecto | TREE.ipynb | TREE_CALIBRATION.ipynb |
|---------|------------|------------------------|
| **Objetivo** | Mostrar ARQUITECTURA | CALCULAR constantes |
| **Enfoque** | TreeEntry + Tree (estructura) | Uso de Tree (calibración) |
| **Tree** | Se crea vacío y se rellena | Se usa ya construido |
| **Resultado** | Entender estructura | Obtener constantes |
| **Complejidad** | Básico (5 sets) | Completo (60 sets) |

---

## 🎯 TREE.ipynb - Arquitectura

### ¿Qué hace?
Explora la **arquitectura modular** del sistema Tree SIN hacer calibración.

### Contenido:

#### 1. TreeEntry (Nodos)
- **Definición**: Representa UN CalibSet con sus relaciones
- **Almacena**:
  - `calibset`: CalibSet procesado
  - `round`: Ronda (1, 2, 3)
  - `sensors`, `raised_sensors`, `discarded_sensors`
  - `parent_entries`, `children_entries`: Links bidireccionales
  - `offsets_to_raised`: Dict con offsets hacia cada raised

#### 2. Tree (Contenedor)
- **Definición**: Organiza TODOS los TreeEntry jerárquicamente
- **Almacena**:
  - `entries`: Dict de todos los TreeEntry
  - `root`: TreeEntry raíz (Set 57, R3)
  - `entries_by_round`: Dict clasificando por ronda

#### 3. Crear Tree Vacío → Rellenar → Visualizar
```python
# Paso 1: Tree vacío
tree = Tree()

# Paso 2: Crear TreeEntry
entry = TreeEntry(
    set_number=57.0,
    calibset=calibset_57,
    round=3,
    sensors=[...],
    raised_sensors=[...],
    ...
)

# Paso 3: Añadir al Tree
tree.add_entry(entry)
tree.set_root(entry)

# Paso 4: Visualizar
print(tree)  # Muestra estructura jerárquica
```

#### 4. Uso Automático
```python
# En producción usamos función automática
tree = create_tree_from_calibsets(
    calibsets=calibsets,
    config=config,
    root_set_id=57.0
)

print(tree)  # Ver estructura completa
```

### Resultado:
- ✅ Entender cómo funciona TreeEntry
- ✅ Entender cómo funciona Tree
- ✅ Ver estructura con `print(tree)`
- ✅ Saber cómo se crea vacío y se rellena

---

## 🔬 TREE_CALIBRATION.ipynb - Calibración

### ¿Qué hace?
USA el Tree construido para **CALCULAR constantes de calibración** finales.

### Contenido:

#### 1. Construcción del Tree Completo
- Crea TODOS los CalibSets (60 sets)
- Construye Tree con jerarquía completa
- Puede tardar varios minutos

#### 2. Búsqueda de Múltiples Caminos
```python
# Encuentra TODOS los caminos posibles
paths = find_all_paths_to_reference(
    sensor_id=48060,
    start_entry=entry_r1,
    tree=tree
)

# Ejemplo de resultado:
# [(offset1, error1, path1), 
#  (offset2, error2, path2),
#  (offset3, error3, path3),
#  (offset4, error4, path4)]
```

**¿Por qué múltiples caminos?**
- Si R1 tiene 2 raised y R2 tiene 2 raised → 4 caminos posibles
- Cada camino es independiente
- Más caminos = mayor redundancia y precisión

#### 3. Media Ponderada
```python
# Combina caminos usando 1/σ² como peso
final_offset, final_error = weighted_average_paths(paths)
```

**Fórmulas**:
- Peso: `w_i = 1/σ_i²`
- Media: `μ = Σ(w_i * x_i) / Σ(w_i)`
- Error: `σ = 1/√(Σw_i)`

**Ventaja**: Caminos con menor error tienen más peso

#### 4. Calibración Completa
```python
# Calcula constantes para TODOS los sensores
df_results = calibrate_tree(
    tree=tree,
    output_csv="calibration_constants_tree.csv"
)
```

#### 5. Análisis y Visualizaciones
- Estadísticas globales
- Histogramas de offsets y errores
- Comparación por sets
- Validación: error vs N_caminos

### Resultado:
- ✅ CSV con constantes de calibración finales
- ✅ Estadísticas por set
- ✅ Validación de método multi-camino
- ✅ Gráficos de distribuciones

---

## 🔄 Flujo de Trabajo Completo

### 1. Entender (TREE.ipynb)
```
Leer TREE.ipynb → Entender TreeEntry → Entender Tree → 
Ver cómo se crea vacío → Ver print(tree)
```

### 2. Aplicar (TREE_CALIBRATION.ipynb)
```
Leer TREE_CALIBRATION.ipynb → Crear Tree completo → 
Buscar caminos → Media ponderada → Obtener constantes
```

### 3. Producción (main.py)
```
Ejecutar main.py → Procesa 60 sets → Genera CSVs
```

---

## 📊 Analogías

### TreeEntry vs Tree

**TreeEntry** = Página individual de un libro
- Tiene contenido (CalibSet)
- Tiene referencias a otras páginas (parent/child links)
- Es un NODO en la estructura

**Tree** = El libro completo
- Organiza todas las páginas
- Tiene índice (entries_by_round)
- Tiene portada (root)
- Es la ESTRUCTURA completa

### TREE.ipynb vs TREE_CALIBRATION.ipynb

**TREE.ipynb** = Manual de cómo se construye un libro
- Muestra cómo crear páginas (TreeEntry)
- Muestra cómo unirlas en un libro (Tree)
- Muestra el índice (print(tree))

**TREE_CALIBRATION.ipynb** = Usar el libro para resolver un problema
- Ya tienes el libro construido
- Lo usas para buscar información (caminos)
- Combinas información de varias páginas (media ponderada)
- Obtienes una solución (constantes)

---

## 🎓 ¿Cuándo usar cada notebook?

### Usa TREE.ipynb cuando:
- ❓ Necesitas entender cómo funciona la arquitectura
- ❓ Quieres ver la estructura del Tree
- ❓ Necesitas debuggear un TreeEntry específico
- ❓ Quieres entender parent/child links
- ❓ Necesitas ver offsets_to_raised

### Usa TREE_CALIBRATION.ipynb cuando:
- 🔬 Necesitas calcular constantes de calibración
- 🔬 Quieres validar el método multi-camino
- 🔬 Necesitas analizar estadísticas de error
- 🔬 Quieres comparar diferentes sets
- 🔬 Necesitas exportar resultados finales

### Usa main.py cuando:
- 🚀 Necesitas procesar TODOS los sets
- 🚀 Quieres resultados en producción
- 🚀 Necesitas CSVs finales para análisis
- 🚀 Quieres automatizar el proceso

---

## 🐛 Errores Comunes Resueltos

### Error 1: `ModuleNotFoundError: No module named 'set'`
**Problema**: Import incorrecto en notebooks
```python
# ❌ Incorrecto
from set import CalibSet

# ✅ Correcto
from calibset import CalibSet
```

**Solución**: Ya corregido en ambos notebooks

### Error 2: `Tree no muestra estructura`
**Problema**: Tree no implementa `__str__()`

**Solución**: Tree ya tiene `__str__()` implementado:
```python
tree = create_tree_from_calibsets(...)
print(tree)  # Muestra jerarquía completa
```

### Error 3: `Tree vacío no funciona`
**Problema**: No se puede crear Tree sin entries

**Solución**: Tree se puede crear vacío:
```python
tree = Tree()  # ✅ Funciona
tree.add_entry(entry)  # Añadir entries
tree.set_root(entry)  # Establecer root
```

---

## 📝 Código Clave

### Crear Tree Vacío y Rellenar
```python
# 1. Crear vacío
tree = Tree()

# 2. Crear entry
entry = TreeEntry(
    set_number=57.0,
    calibset=calibset,
    round=3,
    sensors=[...],
    raised_sensors=[...],
    discarded_sensors=[],
    parent_entries=[],
    children_entries=[],
    offsets_to_raised={}
)

# 3. Añadir
tree.add_entry(entry)
tree.set_root(entry)

# 4. Ver estructura
print(tree)
```

### Crear Tree Automáticamente
```python
tree = create_tree_from_calibsets(
    calibsets={3.0: cs3, 49.0: cs49, 57.0: cs57},
    config=config,
    root_set_id=57.0
)
print(tree)
```

### Buscar Caminos y Calcular
```python
# Buscar caminos
paths = find_all_paths_to_reference(
    sensor_id=48060,
    start_entry=tree.get_entry(3.0),
    tree=tree
)

# Media ponderada
offset, error = weighted_average_paths(paths)

# Calibración completa
df = calibrate_tree(tree, output_csv="results.csv")
```

---

## ✅ Checklist de Comprensión

Después de leer esta guía, deberías poder:

- [ ] Explicar qué es un TreeEntry
- [ ] Explicar qué es un Tree
- [ ] Crear un Tree vacío
- [ ] Añadir un TreeEntry al Tree
- [ ] Ver la estructura con `print(tree)`
- [ ] Entender qué son los offsets_to_raised
- [ ] Explicar por qué hay múltiples caminos
- [ ] Entender la media ponderada con 1/σ²
- [ ] Ejecutar calibración completa
- [ ] Interpretar resultados del CSV

---

**Fecha**: 15 de enero de 2026  
**Versión**: 2.0 (Nueva arquitectura modular)
