---
name: seleccion-refractarios
description: Selección y comparación de materiales refractarios por zona y por proceso siderúrgico — alto horno, reducción directa, acería eléctrica, horno olla, colada continua, laminación, galvanizado. Usar al elegir o comparar un material, evaluar una alternativa de proveedor, o justificar un diseño de revestimiento.
---

# Selección de refractarios por proceso y zona

## Método

Seleccionar por **la solicitación dominante de la zona**, no por la propiedad
más vistosa de la ficha técnica. Orden de trabajo:

1. Identificar el mecanismo de desgaste dominante en esa zona concreta
   (ver la skill `degradacion-refractarios`).
2. Traducirlo a la propiedad que lo controla.
3. Comprobar la compatibilidad química con la escoria y la atmósfera reales.
4. Comprobar las consecuencias térmicas del cambio: un refractario más
   conductor cambia las pérdidas, la temperatura de carcasa, la velocidad de
   enfriamiento y el tiempo de precalentamiento. **Ese acoplamiento se cuantifica
   con el modelo de este repositorio: cambiar el material en el YAML y correr.**
5. Comparar coste por tonelada de acero producida, no coste por tonelada de
   refractario.

## Traducción mecanismo → propiedad

| Mecanismo dominante | Propiedad que lo controla | Lo que NO ayuda |
|---|---|---|
| Disolución en escoria | Compatibilidad química, saturación de la escoria | Más densidad |
| Penetración / spalling estructural | Porosidad abierta y tamaño de poro | Resistencia en frío |
| Choque térmico | R = σ_r(1−ν)/(Eα); tenacidad | Alta resistencia mecánica sola |
| Oxidación de carbono | Antioxidantes, atmósfera, práctica de precalentamiento | Cambiar de grafito |
| Erosión / abrasión | Dureza en caliente, resistencia a la abrasión | Porosidad baja sola |
| Fluencia / carga en caliente | Refractariedad bajo carga (RUL), diseño de juntas | Cono pirométrico (PCE) |

Nota recurrente: el **PCE** (cono pirométrico) mide refractariedad sin carga y
casi nunca es el criterio útil. La **RUL** sí lo es.

## Mapa por proceso

### Alto horno
- **Crisol y solera**: bloques de carbono/grafito con microporosidad, a veces con
  "cerámic cup" de corindón-mullita. Solicitación: penetración de arrabio,
  disolución de carbono en hierro insaturado, desgaste en "pata de elefante" por
  flujo periférico. La refrigeración es parte del diseño refractario.
- **Etalajes y vientre**: SiC ligado a nitruro, con refrigeración. Álcalis y Zn.
- **Cuba**: alta alúmina / andalucita; abrasión de la carga y ataque alcalino.
- **Toberas y piqueras**: masas de taponado, ciclado severo.
- **Estufas Cowper**: sílice y alta alúmina en cámara de combustión; ciclado.

### Reducción directa (DRI / HBI)
- **Reformador**: tubos y aislamiento; atmósfera fuertemente reductora rica en
  H₂ y CO. Riesgo específico: **deposición de carbono** (Boudouard) y reducción
  de óxidos de hierro presentes como impureza en el refractario — exigir
  contenido de Fe₂O₃ bajo.
- **Cuba de reducción**: abrasión intensa por pelets descendentes; alta alúmina
  densa o carburo de silicio en zonas críticas.
- Diferencia clave frente a la vía alto horno: temperaturas más bajas pero
  atmósfera mucho más reductora y abrasión continua.

### Acería eléctrica (EAF)
- **Puntos calientes y línea de escoria**: MgO-C de alto carbono (14-18 %) con
  antioxidantes. Radiación directa del arco.
- **Solera**: masa seca de magnesita sinterizada, reparada por proyección.
- **EBT (sangrado excéntrico)**: manguito de MgO-C, altísimo ciclado y erosión.
- **Bóveda y delta**: alta alúmina o precast; choque térmico severo.
- Palancas de proceso que valen más que el material: práctica de escoria
  espumosa (protege del arco), posición de quemadores e inyectores, y evitar
  operar con escoria insaturada en MgO.

### Horno olla / olla de acería — **proyecto activo**
- **Línea de escoria**: MgO-C. Es la zona que decide la campaña.
- **Pared y fondo**: alúmina-espinela (castable o prefabricado) o AMC. El
  castable de alúmina-espinela forma espinela in situ que atrapa el FeO
  penetrado.
- **Revestimiento de seguridad**: alta alúmina o andalucita.
- **Aislante**: placa microporosa o fibra. Domina la temperatura de carcasa y,
  por tanto, las pérdidas y el tiempo de precalentamiento.
- **Buza, tapón poroso, well block**: piezas de ciclo propio y desgaste propio;
  su vida suele ser la que fija la parada, no la del revestimiento.
- Trade-off central que este repositorio permite cuantificar: **MgO-C conduce
  3-5 veces más que un castable de alúmina**. Eso significa más pérdidas, más
  caída de temperatura del acero, enfriamiento más rápido en la espera y más
  precalentamiento — a cambio de mejor resistencia a escoria y a choque térmico.
  No es una decisión que se pueda tomar solo con la tabla de propiedades.

### Colada continua
- **Cuchara de reparto (tundish)**: revestimiento permanente de alta alúmina más
  masa de proyección básica (MgO) o placas de trabajo. Objetivo doble: aislar y
  no contaminar el acero.
- **Buza sumergida (SEN)**: Al₂O₃-C con banda de ZrO₂-C en la línea de escoria.
  Problema dominante: **obstrucción por Al₂O₃** en aceros calmados al aluminio.
  Palancas: inyección de argón, buzas de "calcia estabilizada" o sin sílice,
  tratamiento con calcio del acero.
- **Tapón y placas de válvula de corredera**: alta alúmina-carbono / espinela.
  Erosión por flujo y ciclado.

### Laminación (hornos de recalentamiento)
- **Solera y vigas galopantes**: alta alúmina y aislamiento; ataque por cascarilla
  (FeO) fundida, que es una escoria muy agresiva y fluida.
- **Bóveda y paredes**: fibra cerámica o módulos, por su baja masa térmica —
  aquí la prioridad es el rendimiento energético y el arranque rápido, no la
  resistencia química.
- **Skid pipes**: aislamiento de tubos refrigerados; su fallo sale directamente
  en marcas frías en el producto.

### Galvanizado y líneas de recubrimiento
- **Crisol de zinc**: cerámicas y aceros resistentes al zinc fundido; el zinc
  líquido ataca casi todo metal. Piezas cerámicas para rodillos y cojinetes.
- **Tubos radiantes y horno de recocido**: aleaciones y refractarios de baja
  masa térmica; atmósfera H₂/N₂.
- **Hearth rolls**: acumulación de depósitos (pick-up) que marca la banda; es un
  problema de recubrimiento cerámico más que de refractario másico.

## Al comparar dos materiales, pedir siempre

- Análisis químico completo, no solo el óxido principal.
- Densidad aparente **y** porosidad abierta (la porosidad abierta predice
  penetración; la densidad sola no).
- k(T) y cp(T) con el método de medida declarado, no un valor único.
- RUL y expansión térmica.
- Resistencia al choque térmico con el número de ciclos y el criterio de fallo.
- Ensayo de ataque por escoria **con la escoria del cliente**, no con una
  escoria de referencia.
- Comportamiento tras reducción, si la atmósfera es reductora.

Y correr el modelo con el material nuevo antes de decidir: el efecto sobre
temperatura de carcasa, pérdidas y tiempo de precalentamiento suele ser mayor de
lo que la ficha técnica sugiere.
