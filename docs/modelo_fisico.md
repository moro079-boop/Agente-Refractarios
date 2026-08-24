# Modelo físico y discretización

## Ecuación resuelta

Conducción transitoria 1D en el espesor, con propiedades dependientes de la
temperatura:

```
rho(T) * cp(T) * dT/dt = div( k(T) * grad T )
```

En coordenadas cilíndricas (pared):

```
rho*cp * dT/dt = (1/r) * d/dr ( r * k(T) * dT/dr )
```

En coordenadas planas (fondo), la forma cartesiana equivalente.

## Discretización

Volúmenes finitos sobre celdas contiguas desde la cara caliente (índice 0) a la
cara fría. Para cada celda se precalcula un factor geométrico `g` tal que la
resistencia térmica de media celda vale `R = g/k` [K/W]:

| Geometría | Factor |
|---|---|
| Cilíndrica | `g = ln(r2/r1) / (2*pi*H)` |
| Plana | `g = (x2 - x1) / A` |

Esto unifica ambos casos: el solver es idéntico y solo cambia `g`. La
conductancia entre dos celdas contiguas se obtiene sumando resistencias en
serie, incluida la resistencia de contacto de la interfaz:

```
G_cara = 1 / ( g_plus[i-1]/k[i-1] + g_minus[i]/k[i] + R_contacto )
```

**Integración temporal**: Euler implícito, incondicionalmente estable. El sistema
resultante es tridiagonal y se resuelve con el algoritmo de Thomas.

**No linealidades**: k(T), cp(T) y la radiación en las fronteras se tratan con
iteraciones de punto fijo dentro de cada paso de tiempo, hasta que el cambio
máximo baja de 1e-4 K.

**Evaluación de propiedades**: `cp` en el punto medio `(T_old + T_new)/2`
(segundo orden, conserva energía); `k` en `T_new` (consistente con el flujo
implícito).

**Paso de tiempo adaptativo**: cada segmento arranca con `dt_initial` (0.5 s por
defecto) y crece geométricamente hasta `dt`. Al cambiar de condición de frontera
—llenar con acero, vaciar, encender el quemador— hay un transitorio de segundos
en la cara que un paso de 30 s no resuelve.

## Recuperación de la temperatura de cara

La temperatura de la **cara** no es la del primer nodo. El solver combina en
serie la resistencia de media celda con la resistencia de película y despeja:

```
q      = G_cara * (T_medio - T_nodo)
T_cara = T_medio - q / (h * A)
```

Esto importa porque el criterio del proyecto (≥ 1100 °C) es sobre la cara. En un
transitorio fuerte la diferencia entre cara y primer nodo llega a decenas de
grados.

## Condiciones de frontera

Todas se expresan como `q'' = h_eff(T_s, t) * (T_env(t) - T_s)`, con la
radiación linealizada de forma **exacta**:

```
sigma*(Te^4 - Ts^4) = sigma*(Te^2 + Ts^2)*(Te + Ts)*(Te - Ts)
```

### Acero líquido (`LiquidSteelBath`)
Convección con coeficiente alto (1500 W/m²K por defecto): el baño está agitado y
la cara alcanza casi la temperatura del acero en segundos. Admite una tasa de
enfriamiento del baño durante la retención.

### Olla vacía (`EmptyLadleCavity`)
La cavidad se trata como aproximadamente isoterma —hipótesis razonable en una
olla recién vaciada, donde pared y fondo salen del mismo ciclo. La pérdida
radiativa escapa por la boca con la emisividad aparente de cavidad y se reparte
sobre el área interior:

```
eps_app = eps / ( eps + (1-eps) * A_boca/A_cavidad )
q''_rad = eps_app * (A_boca/A_cavidad) * sigma * (T_amb^4 - T_s^4)
```

**Contraste independiente**: `wall_to_mouth_view_factor()` calcula el factor de
vista geométrico pared→boca con la relación clásica entre discos coaxiales y
reciprocidad. Para la geometría de referencia los dos modelos dan 0.157 y 0.171
(8 % de diferencia), lo que da confianza en el orden de magnitud. La
comprobación está automatizada en `cli validate`.

`lid_factor` ∈ [0,1] multiplica ese intercambio cuando la olla lleva tapa. **Es
un parámetro libre**, no un dato.

### Precalentador (`PreheaterBurner`)
Dos modos, y la elección cambia el resultado por un factor de 5 a 10:

**Temperatura de gas impuesta** (sin `burner_power_MW`): potencia infinita. Cota
inferior teórica del tiempo.

**Potencia finita** (horno bien agitado): la temperatura de gas sale del balance
de energía sobre los gases de combustión:

```
m_cp * (T_ad - T_g)  =  A * [ h_conv*(Tg - Ts) + eps*sigma*(Tg^4 - Ts^4) ]
```

con `m_cp = P_quemador / (T_ad - T_ambiente)`. Lo que no absorbe el revestimiento
sale por la chimenea a T_g. Se resuelve con Newton salvaguardado por bisección.

Comportamiento resultante con 4 MW sobre 45.7 m²:

| Cara caliente | T de gas | Flujo | Rendimiento |
|---:|---:|---:|---:|
| 200 °C | 751 °C | 58 kW/m² | 61 % |
| 600 °C | 868 °C | 52 kW/m² | 55 % |
| 1000 °C | 1101 °C | 40 kW/m² | 43 % |
| 1200 °C | 1257 °C | 33 kW/m² | 34 % |

La caída de rendimiento al calentarse el revestimiento es el comportamiento real
de un precalentador y es exactamente lo que el modo de temperatura impuesta no
puede reproducir.

### Carcasa (`AmbientShell`)
Convección natural por Churchill-Chu (cilindro/placa vertical) o McAdams (placa
horizontal), más radiación al taller. Admite convección forzada por corriente de
aire. Propiedades del aire tabuladas a 1 atm.

## Verificación

`cli validate` ejecuta siete comprobaciones contra soluciones analíticas:

| Comprobación | Error relativo |
|---|---|
| Estacionario plano multicapa (resistencias en serie) | 3e-7 |
| Estacionario cilíndrico (fórmula logarítmica y perfil) | 8e-7 |
| Sólido semi-infinito (función error) | 3e-4 |
| Conservación de energía (flujo vs entalpía) | 9e-4 |
| Enfriamiento agrupado (Biot pequeño) | 6e-4 |
| Independencia de malla y paso de tiempo | 1.5e-3 |
| Coherencia de los dos modelos de cavidad | 8e-2 |

Esto es **verificación**: el código resuelve bien las ecuaciones que dice
resolver. La **validación** —que esas ecuaciones describan la olla real—
requiere datos de planta y está pendiente. Ver `plan_validacion.md`.

## Hipótesis y limitaciones

1. **1D radial sobre la pared.** No hay gradientes axiales, línea de escoria,
   zona de impacto, fondo, buza ni tapón poroso. Los tiempos son de la pared.
2. **Cavidad isoterma** durante el enfriamiento. Falla si pared y fondo salen de
   historias térmicas muy distintas.
3. **Sin desgaste ni adelgazamiento.** Se puede estudiar cambiando el espesor en
   el YAML, pero el modelo no lo evoluciona solo.
4. **Sin cambio de fase ni reacciones.** No se modela la deshidratación de un
   castable nuevo (que consume energía y limita la rampa) ni la oxidación del
   carbono en MgO-C.
5. **Sin costra ni escoria residual** adherida a la cara. Una capa de escoria
   solidificada cambia la emisividad efectiva y añade resistencia térmica.
6. **Propiedades isótropas** y sin histéresis con el ciclado.
