# Resumen Ejecutivo: TREE vs TREE_CALIBRATION

## 🎯 Diferencias Clave

### TREE.ipynb
**Objetivo**: Entender la ARQUITECTURA (cómo funciona por dentro)

**Qué muestra**:
- ✅ Qué es un TreeEntry (nodo)
- ✅ Qué es un Tree (contenedor)
- ✅ Cómo crear Tree vacío: `tree = Tree()`
- ✅ Cómo añadir entries: `tree.add_entry(entry)`
- ✅ Cómo ver estructura: `print(tree)`

**Resultado**: Entiendes cómo funciona

---

### TREE_CALIBRATION.ipynb
**Objetivo**: USAR el Tree para CALCULAR constantes

**Qué hace**:
- 🔬 Construye Tree completo (60 sets)
- 🔬 Busca múltiples caminos R1 → R3
- 🔬 Calcula media ponderada (1/σ²)
- 🔬 Genera CSV con constantes

**Resultado**: Obtienes constantes de calibración

---

## 📊 Analogía Simple

**TREE.ipynb** = Manual de cómo construir un coche
- Te explica cada pieza (motor, ruedas, etc.)
- Te muestra cómo ensamblar
- Puedes ver el resultado final

**TREE_CALIBRATION.ipynb** = Conducir el coche
- Ya tienes el coche construido
- Lo usas para llegar a tu destino
- Obtienes resultados (llegas a donde quieres)

---

## ✅ Errores Corregidos

### Ambos notebooks tenían:
```python
# ❌ Error anterior
from set import CalibSet

# ✅ Ahora correcto
from calibset import CalibSet
```

### Ahora funcionan:
1. ✅ TREE.ipynb ejecuta sin errores
2. ✅ TREE_CALIBRATION.ipynb ejecuta sin errores
3. ✅ `print(tree)` muestra estructura completa
4. ✅ Tree se puede crear vacío y rellenar

---

## 🚀 Cómo Usar

1. **Primero**: Lee **TREE.ipynb** para entender arquitectura
2. **Segundo**: Lee **TREE_CALIBRATION.ipynb** para ver calibración
3. **Tercero**: Ejecuta **main.py** para producción

---

**Fecha**: 15 de enero de 2026
