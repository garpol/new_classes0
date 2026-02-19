# DISEÑO TREE GIGANTE - TODOS LOS SENSORES DUNE

## RESUMEN DE SENSORES DISPONIBLES

### Sensores Calibrados (en config.yml actual)
- **Total sensores únicos ronda 1**: 540
- **Sensores válidos (no descartados)**: 514
- **Sensores descartados definitivos**: 26 (destacar que no tengo localizados los 26 en el lab (ver si están en set-ups del propio lab))

### Sensores por Calibrar (en laboratorio)
- **PT-111** (cajón lab): 4 unidades (en el presupuesto de compra se indican 20), estos van en las INLETS.
- **PT-103** (cajón lab): 56 unidades (en el presupuesto se indican 65 comprados pero 4 ya los usé para completar el último set de ronda 1).
- **Total por calibrar**: 60 sensores = 56 + 4 comprados 

### Total Potencial
- **514 + 60 = 574 sensores** se necesitan 450 + 66 + 66 sensores (ver PRR)

---

## DISTRIBUCIÓN PARA DETECTORES DUNE

### Necesidades
- **APAs (detector principal)**: 450 sensores
- **Detector HD**: 66 sensores 
- **Detector VD**: 66 sensores 
- **TOTAL**: 450 + 66 + 66 = 582 sensores necesarios

### Asignación desde sensores calibrados (514)
- **APAs**: 450 sensores (de los 514 calibrados)
- **Sobrantes calibrados**: 514 - 450 = 64 sensores
  - Para Detector HD: 66 sensores (de sobrantes + nuevos) - **FALTAN 2 sensores**
  - Para Detector VD: 66 sensores (de sobrantes + nuevos) - **FALTAN 2 sensores**

### DÉFICIT: 8 SENSORES
- Necesitamos: 582 sensores (450 + 66 + 66)
- Tenemos: 574 sensores (514 calibrados + 60 por calibrar)
- **FALTAN: 8 sensores**

**Acciones necesarias:**
1. Buscar sensores perdidos del inventario:
   - Frame Set 13 (no localizado)
   - 16 PT-111 faltantes del presupuesto
   - 5 PT-103 faltantes del presupuesto
   - 26 sensores descartados (verificar si están físicamente y pueden recuperarse)
2. Si no se localizan, comprar 8 sensores adicionales y calibrarlos

---

## OPCIONES DE ESTRUCTURACIÓN: COMPARATIVA

### OPCIÓN A: TREE GIGANTE UNIFICADO

#### Ventajas
1. **Gestión centralizada**: Todas las calibraciones en un único tree
2. **Flexibilidad**: Reasignación fácil entre detectores
3. **Trazabilidad completa**: Historial unificado
4. **Escalabilidad**: Fácil añadir los 60 nuevos sensores cuando se calibren
5. **Sin déficit**: 574 sensores cubren exactamente las necesidades ajustadas
6. **Un solo archivo de salida**: Simplifica la gestión

#### Desventajas
1. **Archivo muy grande**: 574 entradas en un solo tree
2. **Complejidad de filtrado**: Necesita lógica adicional para separar por detector
3. **Riesgo de error**: Un problema afecta a todos los sensores

#### Campos adicionales necesarios en TreeEntry

```python
# Campos actuales del TreeEntry
- sensor_id
- calibration_set
- run_number
- alpha, beta (constantes de calibración)
- T_ref (temperatura de referencia)
- R_ref (resistencia de referencia)
- errors, quality metrics, etc.

# NUEVOS CAMPOS PROPUESTOS
- detector_assignment: str  # "APAs", "Detector2", "Detector3", "Unassigned"
- sensor_type: str          # "PT-103", "PT-111", "Standard"
- calibration_status: str   # "Calibrated", "Pending", "InProgress"
- physical_location: str    # Para trazabilidad en lab
- notes: str                # Observaciones adicionales
```

---

### OPCIÓN B: 3 TREES SEPARADOS POR DETECTOR

#### Ventajas
1. **Separación clara**: Cada detector tiene su propio tree independiente
2. **Archivos manejables**: ~450, ~66, ~66 entradas por tree
3. **Sin contaminación cruzada**: Problemas en un tree no afectan otros
4. **Especialización**: Cada tree puede tener configuración específica
5. **Distribución física**: Corresponde con la realidad de los detectores
6. **IMPORTANTE: Aprovecha calibraciones existentes**: Los 514 sensores YA están calibrados

#### Desventajas
1. **Gestión múltiple**: 3 archivos separados
2. **Reorganización inicial**: Decidir qué sensores van a cada detector
3. **Menos flexibilidad**: Reasignar sensores entre detectores requiere más trabajo

#### Estructura propuesta

**Tree 1 - APAs (450 sensores)**
- Tomar los 450 mejores sensores de los 514 calibrados
- Criterios de selección:
  - Error de calibración más bajo
  - Mayor estabilidad
  - Mejor caracterización (más runs)
  - Sensores de sets tempranos (más confiables)

**Tree 2 - Detector HD (66 sensores)**
- De los 64 sensores sobrantes calibrados: ~32 sensores
- De los 60 nuevos PT-111/PT-103 calibrados: ~30 sensores
- De sensores localizados o comprados: ~4 sensores
- Total: 66 sensores

**Tree 3 - Detector VD (66 sensores)**
- De los 64 sensores sobrantes calibrados: ~32 sensores
- De los 60 nuevos PT-111/PT-103 calibrados: ~30 sensores
- De sensores localizados o comprados: ~4 sensores
- Total: 66 sensores

#### Implementación con calibraciones existentes

**VENTAJA CLAVE**: Ya tienes 514 sensores calibrados con todos sus sets y runs
- No necesitas recalibrar nada
- Solo necesitas ORGANIZAR los sensores en 3 trees
- Los 60 nuevos se calibrarán después y se añadirán a Trees 2 y 3

**Proceso:**
1. Clasificar los 514 sensores calibrados según calidad
2. Asignar top 450 → Tree APAs
3. Asignar 64 restantes → Trees HD y VD (32 cada uno provisonalmente)
4. Buscar los 8 sensores faltantes en el laboratorio o comprarlos
5. Calibrar los 60 nuevos sensores (PT-111 y PT-103) + 8 localizados/comprados
6. Completar Trees HD y VD hasta 66 cada uno con los nuevos calibrados

---

### COMPARACIÓN DIRECTA

| Aspecto | Tree Gigante | 3 Trees Separados |
|---------|--------------|-------------------|
| **Complejidad inicial** | Baja | Media (clasificación) |
| **Aprovecha calibraciones existentes** | ✓ Sí | ✓ Sí |
| **Flexibilidad futura** | Alta | Media |
| **Claridad organizativa** | Media | Alta |
| **Riesgo de errores** | Medio | Bajo |
| **Trabajo adicional** | Mínimo | Mínimo |
| **Correspondencia física** | No directa | Directa |
| **Escalabilidad** | Alta | Media |

---

### RECOMENDACIÓN

**Opción B (3 Trees Separados)** es más adecuada porque:

1. **Ya tienes todas las calibraciones hechas** → No hay trabajo extra innecesario
2. **Separación natural**: Corresponde con los 3 detectores físicos
3. **Menor riesgo**: Problemas aislados por detector
4. **Facilita entrega**: Cada detector recibe su tree específico
5. **Trazabilidad**: Más fácil rastrear qué sensores van a qué detector

**Trabajo necesario**:
- Desarrollar criterio de selección para los 450 mejores → Tree APAs
- Distribuir los 64 restantes entre Trees 2 y 3
- NO requiere recalibración
- Solo organización de datos existentes

---

## JERARQUÍA DE CALIBRACIÓN

### Nivel 1: Calibración Individual (Sets 3-45)
- Sensores calibrados individualmente en sets de ~12 sensores
- **514 sensores ya calibrados**

### Nivel 2: Sets de Recuperación (Sets 46-48)
- Intentos de recuperación de sensores descartados
- **33 sensores recuperados exitosamente**

### Nivel 3: Rondas Jerárquicas (Sets 49-57)
- Calibraciones basadas en sensores raised de rondas anteriores
- **Ronda 2, 3, 4**: Refinamiento jerárquico

### Nivel 4 (FUTURO): Nuevos Sensores del Lab
- **Set 64+**: Calibración de los 60 sensores PT-111 y PT-103
- Seguir metodología establecida
- Asignar a Detector 2 y Detector 3

---

## ASIGNACIÓN PROVISIONAL DE SENSORES A DETECTORES

### APAs (450 sensores)
- Tomar los mejores sensores calibrados según criterios:
  - Error de calibración más bajo
  - Mayor estabilidad en calibración
  - Sensores de sets tempranos (mejor caracterizados)

### Detector HD (66 sensores)
- 32 de los 64 sobrantes calibrados
- 30 de los 60 sensores nuevos calibrados
- 4 de los 8 sensores localizados/comprados y calibrados
- Priorizar PT-103 si están disponibles

### Detector VD (66 sensores)
- 32 de los 64 sobrantes calibrados
- 30 de los 60 sensores nuevos calibrados
- 4 de los 8 sensores localizados/comprados y calibrados
- Priorizar PT-111 si están disponibles

---

## PRÓXIMOS PASOS

### 1. Asignación de IDs a nuevos sensores
- **PT-111**: Asignar IDs en rango no usado (ej: 60000-60003)
- **PT-103**: Asignar IDs en rango no usado (ej: 60004-60059)
- Documentar en config.yml

### 2. Planificación de calibración
- Crear nuevos sets (64-69?) para los 60 sensores
- Sets de ~12 sensores siguiendo metodología actual
- Definir referencias a usar

### 3. Implementación del Tree Gigante
- Extender clase TreeEntry con nuevos campos
- Migrar datos actuales al tree gigante
- Añadir función de filtrado por detector_assignment

### 4. Asignación de sensores a detectores
- Desarrollar algoritmo de asignación óptima
- Considerar criterios de calidad
- Generar reportes por detector

---

## PREGUNTAS PENDIENTES

1. **IDs para nuevos sensores**: ¿Qué rango de IDs usar?
2. **Criterios de asignación**: ¿Qué criterios priorizamos para asignar a APAs vs otros detectores?
3. **Timing**: ¿Cuándo se calibrarán los 60 sensores del lab?
4. **Frame Set 13**: ¿Buscar o dar por perdido?
5. **Sensores PT-103 y PT-111 faltantes**: ¿Reclamar o comprar nuevos?

---

## NOTAS ADICIONALES

### Sensores descartados recuperados
- Set 46: 12 sensores (1 descartado nuevamente: 49107)
- Set 47: 12 sensores (1 descartado nuevamente: 55199)
- Set 48: 12 sensores (1 descartado nuevamente: 55245)
- **33 sensores recuperados con éxito**

### Inventario faltante
- PT-111: Faltan 16 de 20 (solo 4 en cajón)
- PT-103: Faltan 5 de 65 (solo 60 disponibles: 56 lab + 4 usados para tree)
- Frame Set 13: No localizado

### Distribución final requerida
```
APAs:          450 sensores
Detector HD:    66 sensores
Detector VD:    66 sensores
-----------
TOTAL:         582 sensores

Disponibles:   574 sensores (514 calibrados + 60 por calibrar)
FALTAN:          8 sensores (buscar en lab o comprar)
```
