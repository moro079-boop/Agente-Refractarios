---
description: Barrido de sensibilidad de una conclusión frente a los parámetros inseguros
argument-hint: [parámetro o conclusión a poner a prueba]
---

Pon a prueba la robustez de: **$ARGUMENTS**

Antes de refinar un número hay que saber cuánto lo mueven los parámetros que no
están medidos. Corre el barrido mínimo de la skill `experimento-numerico`:

| Parámetro | Rango |
|---|---|
| `lid_factor` | 0.15 - 0.50 |
| `eps_eff` del quemador | 0.50 - 0.85 |
| `burner_power_MW` | ±30 % del nominal |
| `k` del revestimiento de trabajo | ±25 % |
| Espesor de trabajo | nuevo vs final de campaña |

Para cada uno, corre el estudio y reporta el rango resultante de la conclusión.

Preséntame el resultado ordenado **por cuánto mueve la conclusión**, no por
orden alfabético ni por orden de la tabla. El objetivo es responder una sola
pregunta: *¿qué habría que ir a medir primero para que este número deje de ser
un orden de magnitud y pase a ser un número operativo?*

Si algún parámetro mueve la conclusión menos de un 5 %, dilo explícitamente:
saber qué NO hay que medir vale tanto como saber qué sí.
