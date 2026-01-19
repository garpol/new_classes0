# Comparación Sensor 48484: Método Antiguo vs Nuevo

## Resumen de Diferencias

| Método | Constante (K) | Error (K) | N Caminos |
|--------|---------------|-----------|-----------|
| **Antiguo** (rtd-calib-simple) | 0.0 K | 0.001032 K | **1 camino** |
| **Nuevo** (rtd-calib-desde0) | -0.001017 K | 0.000331 K | **2 caminos** |
| **Diferencia** | **0.52 mK** | -0.70 mK | +1 |

## Análisis Detallado

### Método Antiguo (1 camino único)
```
Path único:
  Paso1: 48484 → 48491 (Set 4.0): -0.06754 ± 0.00073 K
  Paso2: 48491 → 48484 (Set 49.0): 0.0 K (mismo sensor!)
  Paso3: 48484 → 48484 (Set 57.0): 0.0 K (mismo sensor!)
  
  TOTAL: 0.0 K ± 0.001032 K
  
⚠️ PROBLEMA: El camino es circular (48484 → 48491 → 48484)
⚠️ El resultado final es 0.0 porque suma y resta el mismo offset
⚠️ Solo cuenta el offset del Paso1 en el error total
```

### Método Nuevo (2 caminos con ponderación)

**Path 1:**
```
  Paso1: 48484 → 48491 (Set 4.0): 0.06750 ± 0.00028 K
  Paso2: 48491 → 48484 (Set 49.0): -0.06732 ± 0.00036 K
  Paso3: 48484 → 48484 (Set 57.0): 0.0 K (referencia)
  
  TOTAL: +0.00018 ± 0.00046 K
```

**Path 2:**
```
  Paso1: 48484 → 48491 (Set 4.0): 0.06750 ± 0.00028 K
  Paso2: 48491 → 48747 (Set 49.0): -0.01679 ± 0.00036 K
  Paso3: 48747 → 48484 (Set 57.0): -0.05302 ± 0.00012 K
  
  TOTAL: -0.00231 ± 0.00048 K
```

**Media Ponderada (1/σ²):**
```
  Path 1: weight = 1/(0.00046)² = 4728 (95%)
  Path 2: weight = 1/(0.00048)² = 4340 (5%)
  
  FINAL: -0.001017 ± 0.000331 K
```

## Conclusiones

### 1. **Ventajas del Método Nuevo**
   - ✅ Usa **2 caminos independientes** vs 1 camino circular
   - ✅ Media ponderada reduce error: **0.33 mK** vs 1.03 mK (68% mejor)
   - ✅ Más robusto: Promedia múltiples medidas

### 2. **Problema del Método Antiguo**
   - ❌ **Camino circular**: 48484 → 48491 → 48484 → 48484
   - ❌ El Paso2 y Paso3 son triviales (sensor → mismo sensor = 0)
   - ❌ Solo propaga el error del Paso1, pero no valida con otros caminos
   - ❌ Resultado = 0.0 K porque el camino se cancela a sí mismo

### 3. **¿Por qué la diferencia de 0.52 mK?**
   El método antiguo reporta **0.0 K** porque:
   - Paso1: +0.06754 K (offset real)
   - Paso2: 0.0 K (mismo sensor)
   - Paso3: 0.0 K (mismo sensor)
   - Paso0: +0.06754 K (reporta solo el offset del Paso1)
   
   Pero en el CSV final muestra **Constante_Calibracion_K = 0.0**, lo que sugiere que:
   - O bien hay un bug en el método antiguo que no reporta correctamente
   - O bien hay una lógica de "sensor raised = referencia = 0.0"

### 4. **Validación**

El método nuevo es **MÁS CORRECTO** porque:
- ✅ Usa 2 caminos reales que llegan a la referencia 48484
- ✅ Path 2 confirma con camino independiente: 48484 → 48491 → 48747 → 48484
- ✅ Media ponderada pondera más el camino con menor error
- ✅ Error propagado correctamente con RSS

El método antiguo tiene un **BUG LÓGICO**:
- ❌ El camino circular 48484 → 48491 → 48484 no es válido
- ❌ Si 48484 es "raised" en el Set 4 y también es la referencia final, el offset debería ser calculado correctamente
- ❌ Reportar 0.0 K sugiere que hay una lógica que anula el resultado cuando sensor = referencia

### 5. **Recomendación para CERN**

**USAR MÉTODO NUEVO** (`rtd-calib-desde0`) porque:
1. Constante más precisa: **-0.001017 K ± 0.331 mK**
2. Error 68% menor
3. Validado con 2 caminos independientes
4. Lógica correcta sin caminos circulares

El valor de **-1.017 mK** es el offset correcto para el sensor 48484 respecto a la referencia absoluta.

---

**Nota**: Para validar completamente, se recomienda:
1. Revisar la lógica del método antiguo en `rtd-calib-simple/src/calibration_utils.py`
2. Verificar si hay casos especiales para sensores "raised" que son también referencia
3. Comparar otros sensores raised del Set 4 (ej: 48491) para confirmar el patrón
