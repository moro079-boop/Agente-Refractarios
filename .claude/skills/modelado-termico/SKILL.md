---
name: modelado-termico
description: Trabajar sobre el modelo térmico 1D de la olla — extender el solver, añadir condiciones de frontera, cambiar geometría o capas, interpretar resultados de temperatura. Usar siempre que se toque src/ladle_thermal/ o se interprete una curva de enfriamiento o precalentamiento.
---

# Modelo térmico 1D de olla

## Qué resuelve

Conducción transitoria 1D en el espesor de la pared (o el fondo), multicapa,
con propiedades dependientes de la temperatura:

    rho(T) * cp(T) * dT/dt = div( k(T) * grad T )

Volúmenes finitos, Euler implícito, sistema tridiagonal (Thomas), iteraciones de
punto fijo para k(T), cp(T) y la radiación en las fronteras. Detalle completo en
`docs/modelo_fisico.md`.

## Decisiones de diseño que hay que respetar

- **La temperatura de CARA no es la del primer nodo.** El solver combina en
  serie la resistencia de media celda con la película superficial y recupera la
  temperatura de la cara. El criterio de 1100 °C es sobre la cara. Si alguien
  reporta `temperatures[0]` como "cara caliente", está reportando el centro de
  la primera celda, que puede diferir decenas de grados.
- **La radiación se linealiza de forma exacta**, no aproximada:
  `sigma*(Te^4 - Ts^4) = sigma*(Te^2+Ts^2)*(Te+Ts)*(Te-Ts)`. El coeficiente
  depende de Ts y el solver itera. No sustituir por un h_rad constante.
- **`cp` se evalúa en el punto medio** `(T_old + T_new)/2` y `k` en `T_new`. Eso
  conserva la energía; evaluar cp en T_new no lo hace.
- **El tiempo que ven las condiciones de frontera es local al segmento.** Una
  rampa de quemador empieza en 0 al inicio de su segmento, no en el tiempo
  global.

## Estado inicial: la decisión que más sesga el resultado

Tres modos, y elegir mal invalida la conclusión:

| Modo | Qué representa | Sesgo |
|---|---|---|
| `cyclic` | Estado periódico de la olla en rotación real | **El correcto** |
| `steady_with_steel` | Olla infinitamente en servicio con acero dentro | Sobreestima el calor almacenado → subestima el precalentamiento |
| `uniform` | Campo uniforme | Normalmente subestima el calor almacenado |

`cyclic_steady_state` repite el ciclo hasta que el campo se vuelve periódico
(típicamente 15-25 ciclos). Si no converge, el ciclo declarado no es estable:
eso ya es un hallazgo sobre la operación, no un problema numérico.

## El quemador: potencia finita o resultado sin sentido

`PreheaterBurner` tiene dos modos:

- Sin `burner_power_MW`: temperatura de gas impuesta = **potencia infinita**.
  Solo sirve como cota inferior teórica del tiempo.
- Con `burner_power_MW`: balance de energía sobre los gases (horno bien
  agitado). La temperatura de gas es un resultado. Reproduce el comportamiento
  real: con revestimiento frío el rendimiento es alto (~60 %) y el flujo se
  autolimita; con revestimiento caliente el rendimiento cae (~35-40 %).

Usar siempre el segundo salvo justificación explícita en el reporte.

## Interpretar una curva: los tres tiempos característicos

1. **Segundos-minutos**: la piel térmica (primeros milímetros). Explica por qué
   la cara caliente cae ~500 °C en los primeros 15 minutos de espera y por qué
   se recupera en minutos bajo el quemador. Casi no lleva energía.
2. **Decenas de minutos-horas**: los primeros 50-100 mm de revestimiento de
   trabajo. Es la masa térmica que realmente le roba calor a la colada
   siguiente. Es lo que controla el tiempo de precalentador útil.
3. **Muchas horas-días**: el conjunto revestimiento + carcasa. Explica que una
   olla parada 24 h necesite un tratamiento distinto.

Si una conclusión depende solo del tiempo (1), es una conclusión frágil.

## Antes de dar por bueno un cambio en la física

```bash
PYTHONPATH=src python3 -m ladle_thermal.cli validate   # 7 comprobaciones analíticas
PYTHONPATH=src python3 -m pytest tests/ -q             # invariantes físicos
```

Y comprobar a mano estos órdenes de magnitud:

| Magnitud | Rango creíble |
|---|---|
| Pérdida radiante de olla vacía abierta a 1500 °C | 3-6 MW (boca de ~8 m²) |
| Flujo por la carcasa a 300 °C | 4-12 kW/m² |
| Temperatura de carcasa en servicio | 150-400 °C |
| Rendimiento del precalentador | 30-65 % |
| Difusividad del refractario denso | 1e-7 a 1e-6 m²/s |

Un resultado fuera de estos rangos es un error hasta que se demuestre lo
contrario.

## Alcance: lo que este modelo NO puede responder

Es 1D radial sobre la pared. No representa la línea de escoria (que es el punto
de mayor desgaste), la zona de impacto, el fondo, la buza, el tapón poroso ni
los gradientes axiales. Tampoco el desgaste: una olla al final de campaña tiene
menos espesor de trabajo y se comporta de forma distinta —eso se puede simular
cambiando el espesor en el YAML, y es un estudio que vale la pena hacer.
