# DISEÑO TREE GIGANTE - TODOS LOS SENSORES DUNE

## RESUMEN DE SENSORES DISPONIBLES

### Sensores Calibrados (en config.yml actual)
- **Total sensores únicos ronda 1**: 540
- **Sensores válidos (no descartados)**: 514
- **Sensores descartados definitivos**: 26 (destacar que no tengo localizados los 26 en el lab (ver si están en set-ups del propio lab))

### Sensores por Calibrar (en laboratorio)
- **PT-111** (cajón lab): 4 unidades (en el presupuesto de compra se indican 20), estos van en las INLETS.
- **PT-103** (cajón lab): 56 unidades (en el presupuesto se indican 65 comprados pero 4 ya los usé para completar el último set de ronda 1).
- **Sensores a localizar/comprar**: 8 unidades adicionales necesarios
- **Total por calibrar**: 68 sensores = 60 en lab + 8 a buscar/comprar 

### Total Potencial
- **514 + 68 = 582 sensores** → EXACTO para los 3 detectores (450 + 66 + 66)
- **Condición**: Localizar o comprar los 8 sensores faltantes

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
- Tenemos calibrados: 514 sensores
- Tenemos en lab: 60 sensores (4 PT-111 + 56 PT-103)
- Disponible: 514 + 60 = 574 sensores
- **FALTAN: 8 sensores**

**Acciones necesarias:**
1. Buscar sensores perdidos del inventario:
   - Frame Set 13 (no localizado) - podría tener hasta 12 sensores
   - 16 PT-111 faltantes del presupuesto
   - 5 PT-103 faltantes del presupuesto  
   - 26 sensores descartados (verificar si están físicamente y pueden recuperarse)
2. Si se localizan 8+ sensores: calibrar para completar 68 total
3. Si no se localizan: comprar 8 sensores adicionales y calibrarlos
4. Total a calibrar: 68 sensores (60 del lab + 8 localizados/comprados)

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

**NO VIABLE** debido a la jerarquía encadenada existente.

#### Por qué no funciona:
1. **Sensores raised están en múltiples rondas**: Un sensor de Ronda 1 que es raised aparece también en Ronda 2
2. **Dependencias jerárquicas**: Ronda 2 depende de Ronda 1, Ronda 3 de Ronda 2, etc.
3. **Duplicación masiva**: Separar requeriría duplicar sensores que están en múltiples niveles
4. **Pérdida de trazabilidad**: La cadena de calibración se rompería

#### Si se quisiera implementar:
- Requeriría reestructuración completa del config.yml
- Recalibración o reinterpretación de todas las rondas jerárquicas  
- Pérdida de la metodología de calibración jerárquica ya establecida

**Conclusión: Descartada por inviable técnicamente.**

---

### COMPARACIÓN DIRECTA

| Aspecto | Tree Gigante | 3 Trees Separados |
|---------|--------------|-------------------|
| **Complejidad inicial** | Baja | **IMPOSIBLE** |
| **Aprovecha calibraciones existentes** | ✓ Sí | ✗ Rompe jerarquía |
| **Mantiene jerarquía encadenada** | ✓ Sí | ✗ No |
| **Flexibilidad futura** | Alta | N/A |
| **Claridad organizativa** | Media (filtrar por campo) | No viable |
| **Riesgo de errores** | Bajo | Alto (duplicación) |
| **Trabajo adicional** | Mínimo | Reestructuración masiva |
| **Trazabilidad completa** | ✓ Sí | ✗ Fragmentada |

**CONCLUSIÓN**: Dado que la calibración está jerárquicamente encadenada (Ronda 1→2→3→4), separar en 3 trees requeriría:
- Duplicar sensores raised que están en múltiples rondas
- Romper las dependencias de calibración
- Recalibrar o reestructurar completamente

**Por tanto, Tree Gigante es la única opción viable.**

---

### ANÁLISIS DE LA JERARQUÍA ACTUAL

**Estructura del tree existente:**
```
Ronda 1: Sets 3-48, 59-61 (540 sensores únicos, 514 válidos)
    ↓ (sensores raised como referencias)
Ronda 2: Sets 49-56 (84 sensores = sensores raised de Ronda 1)
    ↓ (sensores raised como referencias)
Ronda 3: Sets 57, 62 (12 sensores = sensores raised de Ronda 2)
    ↓ (sensores raised como referencias)
Ronda 4: Set 63 (vacío - preparado para siguiente nivel)
```

**Encadenamiento jerárquico:**
- Cada set de Ronda 1 tiene `parent_set` apuntando a un set de Ronda 2
- Los sensores `raised` de cada set son los que se usan en el parent_set
- La calibración está **encadenada jerárquicamente** - no son independientes
- Los sensores de rondas superiores dependen de los de rondas inferiores

**IMPLICACIÓN CRÍTICA**: No se pueden separar los trees sin romper las dependencias jerárquicas.

---

### RECOMENDACIÓN ACTUALIZADA

**Opción A (Tree Gigante Unificado)** es la única viable porque:

1. **Mantiene la jerarquía intacta**: Los encadenamientos Ronda 1→2→3→4 se preservan
2. **Evita duplicación**: Los sensores raised están en múltiples rondas - separarlos requeriría duplicarlos
3. **Ya tienes todas las calibraciones**: 514 sensores calibrados en su estructura jerárquica
4. **Trazabilidad completa**: Se mantiene toda la cadena de calibración de cada sensor
5. **Flexibilidad**: Añadir campo `detector_assignment` permite filtrar por detector sin romper jerarquía

**Trabajo necesario**:
- Extender TreeEntry con campo `detector_assignment: str` ("APAs", "HD", "VD", "Unassigned")
- Algoritmo para asignar los 450 mejores → APAs
- Distribuir 64 restantes entre HD y VD
- Añadir los 60 nuevos sensores cuando se calibren
- **NO requiere recalibración ni reestructuración**

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

**Sensores a calibrar cuando se localicen/compren:**
- **PT-111** (cajón lab): 4 unidades
- **PT-103** (cajón lab): 56 unidades  
- **Sensores a localizar o comprar**: 8 unidades (para completar los 582 necesarios)
- **Total a calibrar**: 68 sensores

**Organización en sets (RAMA PARALELA):**

```
RONDA 1: 6 sets nuevos (Sets 64-69)
  - Set 64: 12 sensores → 2 raised
  - Set 65: 12 sensores → 2 raised
  - Set 66: 12 sensores → 2 raised
  - Set 67: 12 sensores → 2 raised
  - Set 68: 12 sensores → 2 raised
  - Set 69: 8 sensores  → 2 raised
  Total: 68 sensores → 12 raised
      ↓
RONDA 2: 1 set nuevo (Set 70)
  - 12 sensores (raised de Sets 64-69 Ronda 1)
  - 2 raised
      ↓
RONDA 3: 1 set parcial nuevo (Set 71)
  - 2 sensores (raised del Set 70 Ronda 2)
  - Converge con Sets 57, 62 existentes
      ↓
RONDA 4: Set 63 (ya existe)
  - CONVERGENCIA de toda la jerarquía
```

**Total sets nuevos:** 8 (Sets 64-71: 6 en R1 + 1 en R2 + 1 en R3)

**Ventajas:**
- Rama paralela limpia, no interfiere con calibraciones existentes
- Converge naturalmente en Ronda 4 (Set 63)
- Fácil rastrear: Sets 64+ son los nuevos
- Patrón consistente: 2 raised por set

**Paso previo:** Localizar los 8 sensores faltantes o comprarlos antes de calibrar

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

Calibrados:    514 sensores
En laboratorio: 60 sensores (4 PT-111 + 56 PT-103)
A buscar/comprar: 8 sensores
-----------
POR CALIBRAR:   68 sensores (cuando se completen)
TOTAL FINAL:   582 sensores ✓
```
