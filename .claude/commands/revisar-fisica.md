---
description: Revisión crítica de la física de un cambio en el modelo antes de darlo por bueno
argument-hint: [archivo, función o cambio a revisar]
---

Revisa críticamente la física de: **$ARGUMENTS**

No es una revisión de estilo de código. Busca errores de modelado, que son los
que sobreviven a los tests y acaban en un reporte.

Comprueba, en este orden:

1. **Unidades y convención de signos.** ¿Kelvin dentro, Celsius solo en la
   frontera con el usuario? ¿El flujo positivo entra a la pared?
2. **Conservación.** ¿El cambio puede crear o destruir energía? ¿Sigue pasando
   `check_energy_conservation`?
3. **Casos límite.** ¿Qué hace con h → 0, con espesor → 0, con una sola celda,
   con temperaturas iguales a ambos lados, con dt muy grande?
4. **Linealización de la radiación.** ¿Sigue siendo exacta o alguien metió un
   h_rad constante?
5. **Temperatura de cara vs temperatura de nodo.** El error más fácil de
   cometer y el más caro: el criterio de 1100 °C es sobre la cara.
6. **Parámetros nuevos.** ¿Alguno es un parámetro libre disfrazado? ¿Tiene
   rango físico declarado? ¿Está documentado como calibrable?
7. **Órdenes de magnitud.** Contrasta contra la tabla de la skill
   `modelado-termico`.

Corre `cli validate` y la suite completa. Si algo falla, di qué invariante se
rompió y qué significa físicamente, no solo que el test está en rojo.

Termina con un veredicto claro: **correcto**, **correcto con reservas** (y
cuáles), o **incorrecto** (y por qué).
