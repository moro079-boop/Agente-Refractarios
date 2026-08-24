# Propiedades de materiales: estado de los datos

## Situación actual

**Toda la biblioteca es [LIT]**: valores típicos de literatura para la familia
de material indicada, no datos del refractario concreto instalado en la olla.

Consecuencia práctica: los resultados actuales son **órdenes de magnitud
defendibles**, útiles para comparar escenarios entre sí (con tapa vs sin tapa,
espera corta vs larga, castable vs MgO-C). **No son números operativos** para
fijar un tiempo de precalentador en planta.

Esta advertencia se repite en cada `REPORTE.md` generado. No es una formalidad:
es la diferencia entre un modelo que ayuda y un modelo que hace daño.

## Clasificación del origen de un valor

Al añadir o revisar un material, clasificar cada propiedad:

| Etiqueta | Significado |
|---|---|
| `[FICHA]` | Ficha técnica del proveedor. Indicar proveedor, producto y fecha |
| `[NORMA]` | Medido según norma. Indicar norma y laboratorio |
| `[LIT]` | Valor típico de literatura para la familia |
| `[AJUSTE]` | Ajustado contra medición propia. Indicar contra qué y con qué error |

## Biblioteca actual

Archivo: `src/ladle_thermal/data/materials.yaml`

| Material | Uso | rho [kg/m³] | k a 1000 °C [W/mK] | Origen |
|---|---|---:|---:|---|
| `alumina_spinel_castable` | Revestimiento de trabajo (defecto) | 3050 | 1.95 | [LIT] |
| `mgo_c_brick` | Trabajo / línea de escoria | 2950 | 6.2 | [LIT] |
| `high_alumina_brick_70` | Revestimiento de seguridad | 2600 | 1.60 | [LIT] |
| `andalusite_brick` | Seguridad (alternativa) | 2450 | 1.52 | [LIT] |
| `microporous_board` | Aislante | 320 | 0.045 | [LIT] |
| `ceramic_fiber_blanket` | Aislante (alternativa) | 128 | 0.34 | [LIT] |
| `carbon_steel_shell` | Carcasa | 7850 | — | [LIT], forma de EN 1993-1-2 |
| `liquid_steel`, `slag_layer` | Referencia | — | — | [LIT] |

Nota sobre el acero de carcasa: se usa la forma funcional de k(T) y cp(T) del
Eurocódigo 3 parte 1-2, **omitiendo deliberadamente el pico de cp en la
transformación a ~735 °C**. La carcasa de una olla en servicio se mueve entre
150 y 400 °C; el pico introduce una no linealidad fuerte sin valor para este
problema.

## Qué sustituir primero

Por impacto sobre el resultado:

1. **Espesores reales de cada capa** (geometría, no propiedad, pero es el dato
   peor entrado). Plano de la olla y medición de olla nueva.
2. **k(T) del revestimiento de trabajo**, curva completa, no un valor único.
3. **k(T) del aislante**. Ojo con la degradación en servicio: una placa
   microporosa compactada o penetrada puede duplicar su k de ficha.
4. **rho y cp del revestimiento de trabajo** (masa térmica).
5. Emisividad de la cara caliente, si hay pirómetro.

## Cómo pedirlo al proveedor

Pedir explícitamente, para el **producto concreto instalado**:

- Análisis químico completo (no solo el óxido principal).
- Densidad aparente **y** porosidad abierta.
- k(T) tabulada, con método de medida declarado (hilo caliente / placa).
- cp(T) o al menos entalpía acumulada.
- Expansión térmica, RUL, HMOR.
- Propiedades **tras la primera cocción**, no del material curado.

Si el proveedor solo ofrece datos de un producto "equivalente", eso es `[LIT]`,
no `[FICHA]`, y hay que anotarlo así.

Normas aplicables a cada ensayo: ver la skill `propiedades-refractarios`.

## Procedimiento para incorporar un dato nuevo

1. Editar `src/ladle_thermal/data/materials.yaml` con el campo `source` completo.
2. `PYTHONPATH=src python3 -m pytest tests/test_materials.py -q`
3. Correr el estudio base **antes y después** y cuantificar el delta. Si no se
   mueve nada, sospechar que la propiedad no se está usando.
4. Registrar en `experiments/BITACORA.md`.
5. Actualizar la tabla de este documento.
