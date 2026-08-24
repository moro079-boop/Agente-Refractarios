# Agente de I+D en Refractarios — Modelado térmico 1D de ollas de acería

Agente especializado en investigación y desarrollo de materiales refractarios
para la industria del acero: propiedades, degradación, fenómenos termoquímicos y
termomecánicos, mecanismos de desgaste, selección de materiales, estándares
aplicables y oportunidades de mejora en alto horno, reducción directa, acería
eléctrica, horno olla, colada continua, laminación y galvanizado.

Este repositorio contiene, además, el **proyecto activo**: un modelo térmico 1D
radial de la pared de una olla de acería, construido para responder una pregunta
concreta:

> Tras vaciar el acero, la olla se enfría sin aporte energético durante un
> tiempo variable. ¿Cuánto tiempo necesita en el precalentador para que el
> revestimiento refractario vuelva a estar en condiciones de recibir colada
> (cara caliente ≥ 1100 °C)?

## Estado

- Modelo construido y **verificado**: 7/7 comprobaciones contra soluciones
  analíticas cerradas, 66 tests.
- Corriendo con **propiedades de literatura**. Los resultados son órdenes de
  magnitud defendibles y comparaciones fiables entre escenarios, **no números
  operativos**. Ver `docs/plan_validacion.md`.

## Instalación

```bash
pip install -e .
# o, sin instalar:
pip install numpy PyYAML matplotlib pytest
export PYTHONPATH=src
```

## Uso

```bash
# Verificar que el solver resuelve bien sus ecuaciones
python3 -m ladle_thermal.cli validate

# Ver qué hace un estudio antes de correrlo
python3 -m ladle_thermal.cli describe config/studies/precalentamiento_base.yaml

# Solo las curvas de enfriamiento sin aporte energético
python3 -m ladle_thermal.cli cool config/studies/precalentamiento_base.yaml

# Estudio completo: mapa espera → precalentador, figuras y reporte
python3 -m ladle_thermal.cli run config/studies/precalentamiento_base.yaml \
    --out results/precalentamiento_base

# Un caso puntual
python3 -m ladle_thermal.cli preheat config/studies/precalentamiento_base.yaml \
    --scenario sin_tapa --after 120
```

## Resultado actual (propiedades de literatura)

Olla de 150 t, pared de 160 mm de castable alúmina-espinela, quemador de 4 MW,
criterio cara ≥ 1100 °C y media de los primeros 50 mm ≥ 1000 °C:

| Espera vacía | Sin tapa | Con tapa | Tapa ajustada |
|---:|---:|---:|---:|
| 30 min | 3 min | 0 min | 1 min |
| 120 min | 16 min | 9 min | 6 min |
| 480 min | 45 min | 36 min | 31 min |
| 24 h | 104 min | 93 min | 87 min |

La cara caliente cae de 1259 °C a 870 °C en los **primeros 15 minutos** de
espera sin tapa. Esa caída es la piel térmica y casi no lleva energía: los
primeros minutos de espera cuestan poco precalentador, las horas siguientes sí.

## Estructura

```
src/ladle_thermal/       motor de simulación
  materials.py           k(T), cp(T), rho, emisividad — fuente obligatoria
  geometry.py, mesh.py   pila de capas y discretización por volúmenes finitos
  boundary.py            acero líquido, olla vacía, precalentador, carcasa
  solver.py              implícito, tridiagonal, no lineal
  cycle.py, study.py     ciclos, estado periódico, mapa espera → precalentador
  preheat.py             criterio de "olla lista" y tiempo requerido
  validation.py          verificación contra soluciones analíticas
config/                  geometría de la olla y estudios (YAML) — aquí entran tus datos
docs/                    física, propiedades, plan de validación, preguntas abiertas
.claude/skills/          base de conocimiento: modelado, desgaste, selección, normas
.claude/commands/        /experimento /calibrar /sensibilidad /bitacora /revisar-fisica
experiments/BITACORA.md  registro cronológico de I+D
tests/                   66 tests: verificación analítica + invariantes físicos
```

## Dónde entran tus datos reales

El código es la maquinaria; los datos entran por YAML sin tocar Python.

1. **`config/olla_acero_150t.yaml`** — dimensiones y espesores reales de tu olla.
   Es el dato de mayor impacto y el que más se entra mal.
2. **`src/ladle_thermal/data/materials.yaml`** — fichas técnicas de tu proveedor
   en lugar de los valores de literatura.
3. **Una curva medida de enfriamiento** — calibra los dos parámetros libres del
   modelo (`lid_factor`, `eps_eff`) y lo convierte en herramienta operativa.
   Procedimiento completo en `docs/plan_validacion.md`.

## Alcance

El modelo es 1D radial sobre la **pared**. No representa la línea de escoria, la
zona de impacto, el fondo, la buza ni el tapón poroso — que es donde está el
desgaste. Tampoco modela oxidación de carbono ni evolución del desgaste. Estas
limitaciones están listadas en `docs/modelo_fisico.md` y se repiten en cada
reporte generado.
