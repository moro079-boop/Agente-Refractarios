# Preguntas abiertas

Registro vivo. Cada pregunta lleva estado y qué haría falta para cerrarla.
Actualizar al cerrar o al abrir una nueva.

---

## P1 — ¿Cuál es el criterio correcto de "olla lista"? `[ABIERTA — decisión del usuario]`

El criterio de partida es **cara caliente ≥ 1100 °C**. El modelo muestra que ese
criterio, solo, es frágil: bajo el quemador la cara se recupera en minutos
mientras la masa detrás sigue fría, porque la piel térmica tiene muy poca
energía. Cuantificado (bitácora 2026-08-24): el criterio elegido cambia el tiempo de
precalentador por un factor de **1.4 a 2.5**, creciente con la espera. Una olla
parada 24 h "cumple" en 41 min con el criterio de cara y necesita 104 min con el
criterio de masa térmica. **La elección del criterio pesa más que cualquier
parámetro del modelo.**

**Para cerrarla hace falta**: saber de dónde viene el 1100 °C. Si es una norma
interna basada en medición con pirómetro de la cara, el criterio de cara es el
correcto y el de profundidad es información adicional. Si es un valor heredado
sin trazabilidad, conviene redefinirlo contra la caída de temperatura del acero
(Medición 4 del plan de validación).

---

## P2 — ¿Cuánto vale realmente tapar la olla? `[PARCIALMENTE RESPONDIDA]`

El modelo dice que con `lid_factor = 0.35` la tapa ahorra entre 5 y 15 min de
precalentador según la espera, y reduce mucho la amplitud del ciclo térmico. Lo
segundo probablemente vale más que lo primero, vía vida de campaña.

**Para cerrarla hace falta**: `lid_factor` medido (Medición 1) y un análisis del
efecto sobre la vida de campaña, que el modelo puede alimentar pero no decidir.

---

## P3 — ¿El precalentamiento largo cuesta campaña? `[ABIERTA — fuera del modelo actual]`

Una olla a 1000-1400 °C con aire dentro oxida el carbono del refractario de
forma continua. Un precalentamiento largo con exceso de aire puede costar más
campaña de la que ahorra en temperatura de colada. El modelo actual no incluye
oxidación de carbono.

**Para cerrarla hace falta**: decidir si merece la pena añadir un submodelo de
descarburación (profundidad de la capa descarburada frente a tiempo y
temperatura), o si basta con reportar el tiempo por encima de temperaturas
críticas como indicador. **Lo segundo ya es posible con el modelo actual y
cuesta poco.**

---

## P4 — ¿MgO-C o castable de alúmina-espinela en pared? `[ABIERTA — estudio pendiente]`

MgO-C conduce 3-5 veces más. Eso significa más pérdidas, más caída de
temperatura del acero, enfriamiento más rápido en espera y más precalentamiento,
a cambio de mejor resistencia a escoria y a choque térmico.

**Para cerrarla hace falta**: correr el estudio base con `mgo_c_brick` en la capa
de trabajo y cuantificar el coste térmico. Es un cambio de una línea en el YAML.

---

## P5 — ¿Cómo cambia todo al final de campaña? `[ABIERTA — estudio pendiente]`

Una olla al final de campaña tiene menos espesor de trabajo: menos masa térmica,
se enfría antes y se calienta antes, pero pierde más. El tiempo de precalentador
óptimo probablemente no es el mismo al principio que al final de campaña.

**Para cerrarla hace falta**: correr el estudio con el espesor de trabajo
reducido al remanente típico de final de campaña. Requiere saber cuál es ese
remanente.

---

## P6 — ¿Cuál es la potencia real del precalentador? `[ABIERTA — dato de planta]`

El estudio usa 4 MW supuestos. La potencia de placa rara vez coincide con la
entregada, y el resultado es sensible a ella.

**Para cerrarla hace falta**: caudal de gas y poder calorífico durante un
precalentamiento (Medición 2).
