# Plan de validación con datos de planta

El modelo está **verificado** (resuelve bien sus ecuaciones, 7/7 comprobaciones
analíticas) pero **no validado** (no se ha comprobado que sus ecuaciones
describan esta olla). Este documento dice exactamente qué medir para cerrar esa
brecha, ordenado por relación valor/esfuerzo.

## Los dos parámetros libres

Todo el resto del modelo son datos o física cerrada. Estos dos son ajustables:

| Parámetro | Qué representa | Rango físico | Valor actual |
|---|---|---|---|
| `lid_factor` | Reducción del intercambio radiativo con tapa | 0.10 - 0.60 | 0.35 (supuesto) |
| `eps_eff` | Emisividad efectiva gases + re-radiación en el precalentador | 0.50 - 0.85 | 0.70 (supuesto) |

Un ajuste que caiga fuera de esos rangos no es una calibración: es una señal de
que falta física o de que el dato no es lo que se cree.

## Medición 1 — Curva de enfriamiento de olla vacía (la más rentable)

**Qué**: temperatura frente al tiempo durante una espera vacía normal, de al
menos 2 h, registrando desde el momento del vaciado.

**Cómo**, por orden de preferencia:
1. Pirómetro apuntando al interior de la pared (no al fondo, no a la boca), cada
   5 min. Da directamente la variable que el modelo predice.
2. Termopares de contacto en la carcasa, al menos 3 alturas, registro continuo.
   Es más fácil de instalar y suficiente para calibrar, porque la carcasa
   integra lo que pasa dentro.
3. Cámara termográfica de la carcasa a intervalos fijos. Requiere control de
   emisividad.

**Registrar además**: si llevaba tapa y cómo estaba ajustada, temperatura de
nave, si había corriente de aire, punto de campaña de la olla, y el ciclo previo
(tiempo con acero, temperatura de colada).

**Formato**: CSV con columnas `t_min, T_C` y una cabecera de comentarios con lo
anterior. Guardar en `data/mediciones/`.

**Qué se obtiene**: calibración de `lid_factor` y verificación de que las
pérdidas globales del modelo son correctas. Con una sola curva buena el modelo
pasa de orden de magnitud a número utilizable.

## Medición 2 — Curva de precalentamiento

**Qué**: temperatura frente al tiempo durante un precalentamiento completo,
desde olla fría o tibia hasta el estado en que se declara lista.

**Registrar además**: potencia real del quemador (caudal de gas y poder
calorífico, no la potencia de placa), exceso de aire, temperatura de gases de
chimenea si está instrumentada, y el criterio real que usa el operador para
declarar la olla lista.

**Qué se obtiene**: calibración de `eps_eff`, y —más importante— contraste del
**rendimiento** del precalentador predicho contra el real. Si el modelo predice
45 % y la medición da 25 %, hay una pérdida no modelada que vale dinero
identificar.

## Medición 3 — Temperatura de carcasa en régimen

**Qué**: temperatura de carcasa en varios puntos, en una olla en rotación
normal, a lo largo de un turno.

**Qué se obtiene**: comprobación del estado cíclico periódico y del aislante. Es
la medición más fácil de todas y la que más rápido delata un aislante degradado.

## Medición 4 — Caída de temperatura del acero

**Qué**: temperatura del acero al inicio y al final de la retención, cruzada con
el tiempo que la olla estuvo vacía y con su tiempo de precalentador.

**Qué se obtiene**: la validación que de verdad importa para el negocio. El
modelo predice cuánto calor le roba el revestimiento a la colada; esta medición
lo comprueba en la variable que se paga.

## Criterio de aceptación

El modelo se considerará validado para la pared cuando, sin reajustar
parámetros entre casos:

- Reproduzca la curva de enfriamiento de olla vacía con error < 40 °C en la
  carcasa y < 80 °C en la cara caliente, durante al menos 2 h.
- Reproduzca la temperatura de carcasa en régimen con error < 30 °C.
- Prediga el tiempo de precalentamiento con error < 20 % en al menos tres casos
  con distinta espera previa.

**Un parámetro ajustado a una curva y comprobado en esa misma curva no está
validado.** Siempre reservar al menos un caso para comprobación independiente.

## Lo que este plan NO valida

La pared. No valida la línea de escoria, la zona de impacto, el fondo, la buza
ni el tapón poroso, que es donde está el desgaste. Para eso hace falta otro
modelo, y conviene decirlo antes de que alguien extrapole.
