---
description: Revisa el estado del proyecto y la bitácora de I+D, y propone el siguiente paso
---

Ponme al día del proyecto.

1. Lee `experiments/BITACORA.md` y `docs/preguntas_abiertas.md`.
2. Revisa `git log --oneline -15` y qué hay en `results/`.
3. Corre `PYTHONPATH=src python3 -m pytest tests/ -q` para confirmar que el
   modelo sigue sano.

Después dime, en este orden y sin rodeos:

- **Dónde estamos**: qué está resuelto y con qué nivel de confianza.
- **Qué está bloqueado**: qué conclusión no se puede cerrar y qué dato falta
  exactamente para cerrarla.
- **Qué haría yo ahora**: una sola recomendación, con su justificación en una
  línea. No una lista de opciones.

Distingue siempre entre lo que está calculado, lo que está medido y lo que es
hipótesis. Si algo que se dio por bueno en una sesión anterior ha quedado
invalidado por trabajo posterior, dilo aunque nadie lo haya preguntado.
