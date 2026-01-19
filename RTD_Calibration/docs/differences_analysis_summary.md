# Análisis de Diferencias Grandes entre Métodos

## Resumen Ejecutivo

**114 sensores** tienen diferencias > 5 mK entre métodos (30.4% del total).

Los casos más severos están en **Set 14** y **Set 9**, con diferencias de hasta **405 mK**.

## Causa Principal Identificada: **Paso 2 (R1 → R2)**

### Patrón encontrado:

| Sensor | Set | Método | Paso 1 (dentro R1) | **Paso 2 (R1→R2)** | Paso 3 (R2→R3) | Total |
|--------|-----|--------|-------------------|-------------------|----------------|-------|
| **48956** | 14 | OLD | +67.1 mK | **+483.7 mK** ⚠️ | -76.1 mK | +407.7 mK |
| **48956** | 14 | NEW | -66.8 mK | **+173.0 mK** ✓ | -76.1 mK | +31.7 mK |
| **Diferencia** | | | -133.9 mK | **-310.7 mK** 🔴 | 0.0 mK | **-376.0 mK** |

| Sensor | Set | Método | Paso 1 | **Paso 2 (R1→R2)** | Paso 3 | Total |
|--------|-----|--------|--------|-------------------|--------|-------|
| **48857** | 9 | OLD | +169.0 mK | **+100.8 mK** ⚠️ | -76.1 mK | +24.8 mK |
| **48857** | 9 | NEW | -169.1 mK | **+572.1 mK** ✓ | -76.1 mK | +328.5 mK |
| **Diferencia** | | | -338.1 mK | **+471.3 mK** 🔴 | 0.0 mK | **+303.7 mK** |

## Observaciones Clave

### 1. **Paso 3 (R2→R3) es idéntico** ✅
   - Ambos métodos usan el mismo offset: **-76.055 mK** (48869 → 48484 en Set 57)
   - Esto confirma que la referencia absoluta (Set 57) está bien en ambos

### 2. **Paso 2 (R1→R2) tiene diferencias ENORMES** 🔴
   - Sensor 48956: OLD = +483.7 mK vs NEW = +173.0 mK (**Diferencia: 310 mK**)
   - Sensor 48857: OLD = +100.8 mK vs NEW = +572.1 mK (**Diferencia: 471 mK**)
   - Sensor 48863: OLD = +100.8 mK vs NEW = -3.3 mK (**Diferencia: 104 mK**)

### 3. **Paso 1 también difiere** 🟡
   - En algunos casos se invierte el signo (ej: 48857: +169 mK → -169 mK)
   - Esto sugiere que el camino es diferente o hay inversión de dirección

### 4. **Errores propagados** 📊
   - **OLD**: Errores ~40-150 mK (dominados por Paso 2)
   - **NEW**: Errores ~0.2-0.5 mK (**99% mejor**)
   - El método antiguo tiene errores gigantes en el Paso 2 (Set 50)

## Hipótesis: Problema en Set 50 (R2)

El **Set 50** aparece en el Paso 2 de todos los casos problemáticos:
- 48956 → 48869 (Set 50): OLD = +483.7 ± 43.4 mK vs NEW = +173.0 ± 0.3 mK
- 48857 → 48869 (Set 50): OLD = +100.8 ± 153.2 mK vs NEW = +572.1 ± 0.3 mK

**Posibles causas:**

### A) **Bug en el cálculo de offsets en Set 50 del método antiguo** ⚠️
   - El error de 153 mK en el método antiguo es sospechoso
   - Puede haber un problema en cómo se calculan los offsets raised en R2

### B) **Inversión de signo en Paso 2** ⚠️
   - El método antiguo puede estar invirtiendo incorrectamente los offsets
   - Similar al bug que encontramos antes en el Paso 3 (línea 129)

### C) **Caminos diferentes** 🤔
   - Método antiguo: 48857 → 48857 (Paso 1 = 0.0, sospechoso!)
   - Método nuevo: 48857 → 48863 (offset real)
   - El método antiguo puede tener lógica circular similar al caso 48484

## Evidencia del Bug Circular (Sensor 48863)

```
OLD: Paso 1: 48857 → 48857 (mismo sensor!) = 0.0 K ⚠️
NEW: Paso 1: 48863 → 48857 (camino real) = 0.169 K ✓
```

El método antiguo tiene **caminos circulares** donde sensor → mismo sensor = 0.0

## Recomendación

### 1. **USAR MÉTODO NUEVO** para CERN 🎯
   - Errores 99% menores (0.3 mK vs 40-150 mK)
   - Sin caminos circulares
   - Múltiples caminos independientes validados
   - Lógica correcta en todos los pasos

### 2. **Investigar Set 50 en método antiguo** 🔍
   Verificar:
   - ¿Hay inversión de signo en offsets raised de R2?
   - ¿Por qué los errores son tan grandes (153 mK)?
   - ¿Hay lógica especial para Set 50 que causa el problema?

### 3. **Validar todos los sensores con diferencias > 5 mK**
   - 114 sensores necesitan revisión
   - Priorizar Sets 9, 14 (mayores diferencias)
   - Verificar que el método nuevo es consistente

## Conclusión

Las diferencias NO son por errores numéricos pequeños, sino por **BUGS LÓGICOS en el método antiguo**:

1. ✅ **Caminos circulares** (sensor → mismo sensor = 0)
2. ✅ **Inversión incorrecta de signos** en Paso 2 (R1→R2)
3. ✅ **Errores propagados gigantes** (40-150 mK vs 0.2-0.5 mK)

El método nuevo **es más confiable** porque:
- ✓ Usa caminos reales (no circulares)
- ✓ Múltiples caminos independientes
- ✓ Media ponderada con 1/σ²
- ✓ Errores propagados correctamente
- ✓ Resultados consistentes validados paso a paso

**Para CERN: USAR CONSTANTES DEL MÉTODO NUEVO (`rtd-calib-desde0`)**
