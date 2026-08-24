---
name: experimento-numerico
description: Protocolo para correr, registrar y reportar un experimento numérico del modelo térmico. Usar cada vez que se lance un estudio, se compare un escenario o se vaya a reportar una cifra al usuario.
---

# Protocolo de experimento numérico

Una cifra sin corrida detrás no se reporta. Una corrida sin registro se pierde.

## 1. Declarar la pregunta antes de correr

Escribir en una frase qué se quiere saber y qué respuesta cambiaría una
decisión. Si no cambia ninguna decisión, no es un experimento: es curiosidad, y
conviene decirlo.

Ejemplos de preguntas bien planteadas:
- ¿Cuánto precalentador ahorra tapar la olla durante la espera?
- ¿Cuánto cambia el tiempo si el revestimiento es MgO-C en vez de castable?
- ¿A partir de qué espera deja de compensar mantener el quemador encendido?

## 2. Un archivo de estudio por pregunta

Copiar `config/studies/precalentamiento_base.yaml`, cambiar **una sola cosa** y
darle un nombre que diga qué cambia. Un estudio que cambia tres variables a la
vez no permite atribuir el efecto.

## 3. Correr

```bash
PYTHONPATH=src python3 -m ladle_thermal.cli run config/studies/<nombre>.yaml --out results/<nombre>
```

Salidas: `REPORTE.md`, `mapa_precalentamiento.csv`, y cuatro figuras.

Si la corrida tarda: el coste está dominado por `max_preheat_h` y por el número
de puntos del mapa. La parada temprana ya evita simular más allá del cruce del
criterio.

## 4. Registrar en la bitácora

Añadir una entrada a `experiments/BITACORA.md` con esta forma:

```markdown
## [AAAA-MM-DD] <título corto>

- **Pregunta**: ...
- **Estudio**: `config/studies/<nombre>.yaml` (commit `<sha corto>`)
- **Resultado**: `results/<nombre>/REPORTE.md`
- **Hallazgo**: 2-4 líneas. Números concretos.
- **Confianza**: alta / media / baja, y por qué.
- **Qué lo invalidaría**: la condición concreta que tiraría abajo la conclusión.
- **Siguiente paso**: ...
```

El campo **"qué lo invalidaría"** no es adorno: obliga a nombrar el supuesto más
frágil. Si no se puede rellenar, la conclusión no está entendida.

## 5. Reportar

Al dar el resultado:

- Dar el número **con su condición**: "45 min tras 8 h de espera sin tapa, con
  quemador de 4 MW" — no "45 minutos".
- Decir **qué criterio manda** (`limiting`). Si manda `cara_caliente_C`, el
  resultado es frágil: la cara se recupera en minutos. Si manda el criterio de
  profundidad, el resultado tiene sustancia.
- Decir el **estado de los datos**: con propiedades de literatura, el resultado
  es un orden de magnitud defendible, no un número operativo. Repetirlo cada
  vez, no una sola vez al principio del proyecto.
- Nunca redondear hacia el lado cómodo.

## 6. Sensibilidad antes que precisión

Antes de refinar un número, comprobar cuánto lo mueven los parámetros inseguros.
Si `lid_factor` entre 0.2 y 0.5 mueve el resultado un 40 %, no tiene sentido
discutir si son 44 o 46 minutos: tiene sentido ir a medir.

Barrido mínimo recomendado para cualquier conclusión importante:

| Parámetro | Rango a barrer | Por qué |
|---|---|---|
| `lid_factor` | 0.15 - 0.50 | Parámetro libre, no medido |
| `eps_eff` del quemador | 0.50 - 0.85 | Parámetro libre, no medido |
| `burner_power_MW` | ±30 % del nominal | La potencia real rara vez es la de placa |
| `k` del revestimiento de trabajo | ±25 % | Varía con el proveedor y con el uso |
| Espesor de trabajo | nuevo vs final de campaña | Cambia la masa térmica |
