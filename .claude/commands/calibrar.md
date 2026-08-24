---
description: Calibra los parámetros libres del modelo contra una curva medida en planta
argument-hint: [ruta al CSV de medición]
---

Calibra el modelo contra los datos de: **$ARGUMENTS**

El modelo tiene exactamente dos parámetros libres relevantes, y solo se ajustan
estos. Cualquier otra cosa es un dato, no un parámetro:

- `lid_factor` de `EmptyLadleCavity` (rango físico defendible 0.10 - 0.60)
- `eps_eff` de `PreheaterBurner` (rango físico defendible 0.50 - 0.85)

Procedimiento:

1. Lee el CSV y dime qué contiene: qué se midió, dónde estaba el sensor, con qué
   frecuencia, en qué olla y en qué punto de campaña. Si no se puede
   determinar, dilo — una calibración contra datos de procedencia desconocida es
   peor que no calibrar.
2. Identifica qué escenario del modelo corresponde a esa medición.
3. Barre el parámetro relevante y busca el que minimiza el error cuadrático
   medio contra la curva medida. Reporta también el error del mejor ajuste, no
   solo el parámetro.
4. **Comprueba que el valor ajustado cae en el rango físico.** Si el mejor ajuste
   exige `lid_factor = 0.02`, el problema no es el parámetro: es que falta
   física en el modelo o el dato no es lo que se cree. Dilo en vez de aceptarlo.
5. Comprueba el ajuste contra una curva distinta de la usada para ajustar. Un
   parámetro que solo funciona en la curva con la que se ajustó no está calibrado.
6. Actualiza el YAML del estudio con el valor calibrado y **anota en el propio
   YAML** contra qué medición se calibró y con qué error.
7. Registra en `experiments/BITACORA.md` y vuelve a correr el estudio base para
   cuantificar cuánto se movieron las conclusiones anteriores.
