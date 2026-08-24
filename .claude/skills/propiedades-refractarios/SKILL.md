---
name: propiedades-refractarios
description: Añadir, revisar o cuestionar propiedades termofísicas de refractarios en la biblioteca del modelo, y las normas aplicables para medirlas (ASTM, EN, ISO, DIN). Usar al incorporar una ficha técnica de proveedor, al dudar de un valor, o al preparar una especificación de ensayo.
---

# Propiedades termofísicas y normas de ensayo

## Regla de oro

Todo material de `src/ladle_thermal/data/materials.yaml` lleva campo `source`
obligatorio — el cargador lo rechaza si falta. Al añadir un material, clasificar
explícitamente el origen de cada valor:

- **[FICHA]** ficha técnica del proveedor (indicar proveedor, producto, fecha)
- **[NORMA]** medido según norma (indicar norma y laboratorio)
- **[LIT]** valor típico de literatura para esa familia de material
- **[AJUSTE]** ajustado contra medición propia (indicar contra qué y error)

La biblioteca actual es **toda [LIT]**. Eso está declarado en el propio YAML y
debe repetirse en cada reporte que la use.

## Qué propiedades importan y cuánto

Para este modelo, por orden de impacto sobre el resultado:

1. **k(T) del revestimiento de trabajo.** Controla todo: pérdidas, velocidad de
   enfriamiento, profundidad de penetración térmica. Un ±25 % aquí mueve el
   tiempo de precalentamiento de forma comparable a duplicar la espera.
2. **Espesor de cada capa.** Técnicamente geometría, pero es el dato que más se
   entra mal. Confirmarlo con plano y con medición de olla nueva.
3. **k(T) del aislante.** Domina la temperatura de carcasa. Ojo: la placa
   microporosa se degrada en servicio (compactación, penetración) y su k real a
   media campaña puede duplicar la de ficha.
4. **rho·cp del revestimiento de trabajo.** Es la masa térmica; controla cuánto
   tarda en calentarse y cuánto calor le roba a la colada.
5. **Emisividad de la cara caliente.** Entra a la cuarta potencia en la
   radiación, pero el rango real de un refractario sucio es estrecho (0.8-0.9).
6. **Emisividad de la carcasa.** Cambia poco el resultado interior; cambia la
   temperatura de carcasa que se compara contra medición.

## Trampas frecuentes en fichas técnicas

- **Un solo valor de k sin temperatura.** Suele ser a 1000 °C o "media". Para un
  castable de alúmina la k a 200 °C puede ser un 30 % mayor que a 1000 °C.
  Pedir la curva.
- **k medida por hilo caliente vs placa caliente.** Dan resultados distintos en
  materiales porosos y anisótropos. Anotar el método.
- **Densidad "aparente" vs "volumétrica" vs "real".** Para masa térmica se
  necesita la aparente (bulk), que incluye la porosidad.
- **Propiedades del material curado vs del material tras primera cocción.** Un
  castable cambia mucho tras el primer calentamiento; el modelo debe usar el
  estado en servicio.
- **Datos de un producto "equivalente".** Si el proveedor no da el producto
  concreto instalado, es [LIT], no [FICHA].

## Normas de ensayo aplicables

Referencia de trabajo. **Verificar número y edición vigente antes de citarla en
un documento formal o en una especificación de compra** — las normas se revisan
y se retiran.

### Propiedades térmicas
| Propiedad | Norma |
|---|---|
| Conductividad térmica, hilo caliente | ASTM C1113; ISO 8894-1 / -2; EN 993-14 / -15 |
| Conductividad térmica, ladrillo (panel) | ASTM C201 / C202 |
| Conductividad térmica, monolíticos | ASTM C417 |
| Expansión térmica y fluencia en compresión | ASTM C832 |
| Cambio dimensional permanente por recalentamiento | ASTM C113 |

### Propiedades físicas y mecánicas
| Propiedad | Norma |
|---|---|
| Porosidad aparente, densidad aparente, absorción | ASTM C20; EN 993-1 |
| Resistencia a la compresión en frío (CCS) | ASTM C133; EN 993-5 |
| Módulo de rotura, ambiente | ASTM C133; EN 993-6 |
| Módulo de rotura, en caliente (HMOR) | EN 993-7 |
| Refractariedad bajo carga (RUL) | ISO 1893; EN 993-8 |
| Fluencia bajo compresión | EN 993-9 |
| Cono pirométrico equivalente (PCE) | ASTM C24; ISO 528; EN 993-12 |
| Resistencia a la abrasión a temperatura ambiente | ASTM C704 |
| Módulo elástico por método sónico | ASTM C1419 |

### Comportamiento en servicio
| Ensayo | Norma |
|---|---|
| Choque térmico / ciclado térmico | ASTM C1171; EN 993-11 |
| Ataque por escoria, método del crisol | DIN 51069 (referencia clásica) |
| Productos monolíticos (familia de métodos) | ISO 1927 (partes); EN 1402 (partes) |

Para ataque por escoria no basta la norma: **el ensayo debe hacerse con la
escoria real del cliente**, con su basicidad y su %FeO. Un ensayo con escoria de
referencia compara materiales entre sí, pero no predice el comportamiento en
planta.

## Al incorporar una ficha técnica al modelo

1. Añadir el material a `src/ladle_thermal/data/materials.yaml` con `source`
   completo: proveedor, producto, fecha de la ficha, método de medida.
2. Correr `PYTHONPATH=src python3 -m pytest tests/test_materials.py -q`.
3. Correr el estudio base **antes y después** y reportar el delta. Si un cambio
   de propiedades no mueve nada, sospechar: probablemente no se está usando.
4. Registrar en `experiments/BITACORA.md` qué cambió y cuánto movió el resultado.
5. Actualizar `docs/propiedades_materiales.md` con la nueva clasificación de
   origen.
