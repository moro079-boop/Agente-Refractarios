# Bitácora de I+D

Registro cronológico. Entrada más reciente arriba. Formato en la skill
`experimento-numerico`. Distinguir siempre calculado / medido / hipótesis.

---

## [2026-08-24] Cuánto cambia el resultado según el criterio de "olla lista"

- **Pregunta**: el criterio de partida es cara caliente ≥ 1100 °C. ¿Cuánto
  cambia el tiempo de precalentador si se añade un criterio de masa térmica?
- **Estudio**: `config/studies/criterio_solo_cara.yaml` frente a
  `config/studies/precalentamiento_base.yaml` (idénticos salvo el criterio).
- **Hallazgo** (calculado): escenario sin tapa, minutos de precalentador

  | Espera vacía | Solo cara ≥ 1100 °C | + media 50 mm ≥ 1000 °C | Factor |
  |---:|---:|---:|---:|
  | 60 min | 5 | 7 | 1.4× |
  | 120 min | 9 | 16 | 1.8× |
  | 240 min | 13 | 28 | 2.2× |
  | 480 min | 20 | 45 | 2.3× |
  | 24 h | 41 | 104 | 2.5× |

  El criterio elegido cambia el resultado por un factor de 1.4 a 2.5, y la
  divergencia crece con la espera. **La elección del criterio pesa más que
  cualquier parámetro del modelo.** Físicamente: bajo el quemador la cara se
  recupera en minutos porque la piel térmica tiene muy poca energía; lo que
  tarda horas es reponer la masa térmica que hay detrás, que es la que le roba
  calor a la colada siguiente.

- **Confianza**: alta en el factor y en la tendencia (es un efecto estructural,
  no depende de los valores concretos de las propiedades). Media en los valores
  absolutos.
- **Qué lo invalidaría**: que el criterio real de planta ya incorpore de hecho
  una medida de masa térmica (por ejemplo, un tiempo mínimo de permanencia
  además del criterio de temperatura).
- **Siguiente paso**: cerrar P1 — averiguar de dónde viene el 1100 °C y con qué
  se mide. Si es un pirómetro apuntando a la cara, el criterio de cara es el
  correcto por definición y el de profundidad queda como información adicional.

---

## [2026-08-24] Mapa espera vacía → tiempo de precalentador (estudio base)

- **Pregunta**: tras vaciar el acero, ¿cuánto precalentador hace falta para que
  el revestimiento vuelva a estar en condiciones de recibir colada, según cuánto
  haya esperado la olla y si llevaba tapa?
- **Estudio**: `config/studies/precalentamiento_base.yaml`
- **Resultado**: `results/precalentamiento_base/REPORTE.md`
- **Configuración**: olla de 150 t, pared de 160 mm de castable alúmina-espinela
  + 70 mm alta alúmina + 15 mm microporoso + 30 mm carcasa. Estado de partida:
  ciclo periódico (convergido en 19 ciclos de 180 min). Quemador de 4 MW con
  potencia finita. Criterio: cara ≥ 1100 °C **y** media de los primeros 50 mm
  ≥ 1000 °C.

- **Hallazgo** (calculado, propiedades de literatura):

  | Espera vacía | Sin tapa | Con tapa (0.35) | Tapa ajustada (0.15) |
  |---:|---:|---:|---:|
  | 30 min | 3 min | 0 min | 1 min |
  | 60 min | 7 min | 2 min | 2 min |
  | 120 min | 16 min | 9 min | 6 min |
  | 240 min | 28 min | 20 min | 16 min |
  | 480 min | 45 min | 36 min | 31 min |
  | 24 h | 104 min | 93 min | 87 min |

  La cara caliente cae de 1259 °C a 870 °C en los **primeros 15 minutos** de
  espera sin tapa, y a partir de ahí el enfriamiento se hace lento (720 °C a la
  hora, 557 °C a las 4 h). Esa caída inicial es la piel térmica, que casi no
  lleva energía. Consecuencia operativa: **los primeros 15 min de espera cuestan
  casi nada de precalentador; las horas siguientes sí.**

  Pérdida radiante inicial de la olla vacía: 4.2 MW sin tapa, 1.9 MW con tapa.

  A partir de 60 min de espera el criterio limitante deja de ser la cara y pasa
  a ser la masa térmica de los primeros 50 mm, en todos los escenarios.

- **Confianza**: media-baja para valores absolutos, media-alta para las
  tendencias y las comparaciones entre escenarios. Todas las propiedades son de
  literatura y los dos parámetros libres (`lid_factor`, `eps_eff`) están
  supuestos.
- **Qué lo invalidaría**: (a) que la potencia real entregada por el
  precalentador difiera mucho de 4 MW; (b) que `lid_factor` real esté fuera de
  0.15-0.50; (c) que los espesores reales de la olla difieran de la plantilla;
  (d) que el criterio de "olla lista" no sea el supuesto — ver P1.
- **Siguiente paso**: Medición 1 del plan de validación (curva de enfriamiento
  de olla vacía). Con una sola curva buena, este mapa pasa de orden de magnitud
  a número operativo.

---

## [2026-08-24] Corrección: el quemador necesita potencia finita

- **Pregunta**: la primera versión del estudio daba 17 min de precalentador tras
  8 h de espera. ¿Es creíble?
- **Hallazgo**: no. El quemador estaba modelado como **temperatura de gas
  impuesta**, lo que equivale a potencia infinita: los gases se mantenían a
  1250 °C por mucho calor que absorbiera el revestimiento. Un precalentador real
  tiene potencia finita y su temperatura de gas es un **resultado** del balance
  de energía, no un dato.

  Se sustituyó por un modelo de horno bien agitado: los gases ceden calor al
  revestimiento enfriándose desde la llama adiabática, y lo que no se absorbe
  sale por la chimenea. Comportamiento resultante con 4 MW:

  | Cara caliente | T de gas | Flujo | Rendimiento |
  |---:|---:|---:|---:|
  | 200 °C | 751 °C | 58 kW/m² | 61 % |
  | 1000 °C | 1101 °C | 40 kW/m² | 43 % |
  | 1200 °C | 1257 °C | 33 kW/m² | 34 % |

  La caída de rendimiento al calentarse el revestimiento es el comportamiento
  real de un precalentador. El modo de temperatura impuesta se conserva, pero
  documentado como **cota inferior teórica**, no como predicción.

- **Efecto sobre las conclusiones previas**: los tiempos de precalentamiento se
  multiplicaron por un factor de 2 a 6 según el caso. Cualquier número anterior
  a este cambio queda invalidado.
- **Confianza**: alta en la estructura del modelo; el balance de energía cierra
  a 1e-5 (test automatizado). Media en `eps_eff = 0.70`, que sigue siendo
  supuesto.
- **Qué lo invalidaría**: que el precalentador tenga recuperación de calor de
  gases, o que la potencia entregada difiera mucho de la de placa.

---

## [2026-08-24] Construcción y verificación del modelo

- **Qué se hizo**: modelo térmico 1D radial multicapa por volúmenes finitos,
  implícito, con k(T), cp(T) y radiación no lineal en las fronteras. Ver
  `docs/modelo_fisico.md`.
- **Verificación**: 7/7 comprobaciones contra soluciones analíticas cerradas,
  con errores relativos entre 3e-7 y 8e-2:

  | Comprobación | Error |
  |---|---|
  | Estacionario plano multicapa | 3e-7 |
  | Estacionario cilíndrico (flujo y perfil) | 8e-7 |
  | Sólido semi-infinito (función error) | 3e-4 |
  | Conservación de energía | 9e-4 |
  | Enfriamiento agrupado (Biot pequeño) | 6e-4 |
  | Independencia de malla y paso de tiempo | 1.5e-3 |
  | Coherencia de los dos modelos de cavidad | 8e-2 |

  Los dos modelos radiativos de la boca de la olla —factor de vista geométrico y
  emisividad aparente de cavidad— se desarrollaron de forma independiente y
  coinciden dentro de un 8 %. Eso da confianza en que la pérdida por la boca,
  que domina el enfriamiento, está bien planteada.

- **Errores corregidos durante la construcción**:
  - La entalpía se calculaba interpolando linealmente la integral acumulada de
    cp; como cp es lineal a trozos, su integral es **cuadrática** a trozos y la
    interpolación introducía un 0.14 % de error. Detectado por un test contra
    integración numérica fina; corregido con integración exacta del subintervalo.
  - La bisección del balance del quemador (60 iteraciones dentro del bucle de
    Picard) hacía la corrida inviable. Sustituida por Newton salvaguardado:
    coincide con la bisección a 1e-9 K y es 30× más rápido.

- **Confianza**: alta. Esto es **verificación**, no validación: el código
  resuelve bien sus ecuaciones. Que esas ecuaciones describan la olla real está
  pendiente de datos de planta.
