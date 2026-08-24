---
description: Corre un estudio del modelo térmico de punta a punta y lo registra en la bitácora
argument-hint: [nombre-del-estudio o descripción de la pregunta]
---

Ejecuta el protocolo completo de experimento numérico para: **$ARGUMENTS**

Sigue la skill `experimento-numerico`. Concretamente:

1. Si `$ARGUMENTS` nombra un estudio existente en `config/studies/`, úsalo. Si
   describe una pregunta nueva, crea el archivo de estudio copiando
   `config/studies/precalentamiento_base.yaml` y cambiando **una sola cosa**.
   Dime qué cambiaste antes de correr.
2. Corre `PYTHONPATH=src python3 -m ladle_thermal.cli run <estudio> --out results/<nombre>`.
3. Lee el `REPORTE.md` generado e interpreta el resultado: número con su
   condición, cuál es el criterio limitante, y qué significa físicamente.
4. Añade la entrada a `experiments/BITACORA.md` con el formato de la skill,
   incluyendo el campo "qué lo invalidaría".
5. Resúmeme el hallazgo en 4-6 líneas, dejando claro si el resultado se apoya en
   propiedades de literatura o en datos medidos.

Si la corrida falla o da algo fuera de los rangos creíbles de la skill
`modelado-termico`, para y dime qué está mal en vez de reportar el número.
