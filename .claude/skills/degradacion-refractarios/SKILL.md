---
name: degradacion-refractarios
description: Análisis de mecanismos de desgaste y degradación de refractarios en la industria del acero — corrosión por escoria, penetración, spalling térmico y estructural, oxidación de carbono, hidratación, fatiga termomecánica, erosión. Usar al diagnosticar desgaste, interpretar una autopsia de revestimiento, explicar una campaña corta o evaluar una oportunidad de mejora.
---

# Mecanismos de degradación de refractarios

## Regla de diagnóstico

Un revestimiento casi nunca falla por un solo mecanismo. Falla porque uno
**inicia** el daño y otro lo **propaga**. El error de diagnóstico habitual es
nombrar el que se ve en la autopsia (normalmente el de propagación) y actuar
sobre él, dejando intacto el iniciador.

Antes de proponer una causa, pedir siempre estos cinco datos. Sin ellos el
diagnóstico es especulación:

1. **Dónde** exactamente (línea de escoria, zona de impacto, fondo, buza, cambio
   de sección) y **perfil** de espesor remanente.
2. **Cuándo** en la campaña (infantil, régimen, final) y número de coladas.
3. **Química de escoria**: basicidad binaria/cuaternaria, %FeO+MnO, %Al₂O₃,
   %MgO, saturación en MgO/CaO.
4. **Historia térmica**: temperatura de colada, tiempo de retención, número y
   duración de los ciclos frío-caliente, práctica de precalentamiento.
5. **Aspecto de la superficie**: vitrificada, descarburada, con capa de escoria
   adherida, agrietada en red, exfoliada en capas paralelas a la cara.

## Mecanismos, señal característica y palanca

### Químicos / termoquímicos

**Corrosión por disolución en escoria.** El refractario se disuelve hasta que la
escoria se satura. Señal: cara lisa, vitrificada, desgaste uniforme y
proporcional al tiempo de contacto y a la temperatura. Acelerada por baja
basicidad frente a un refractario básico, alto FeO+MnO, alta temperatura y
agitación. Palanca principal: **saturar la escoria** en el óxido del
refractario (MgO para MgO-C, MgO·Al₂O₃ para alúmina-espinela). Añadir dolomita
calcinada o MgO a la escoria suele ser más barato que cambiar de refractario.

**Penetración + spalling estructural.** La escoria entra por la porosidad
abierta y las juntas, altera la zona penetrada y crea una banda con distinta
expansión térmica. Al ciclar, esa banda se desprende **en placas paralelas a la
cara**. Señal inequívoca: desprendimiento laminar con una capa alterada visible
en corte. Es el mecanismo más subestimado, porque el daño aparece de golpe.
Palancas: menor porosidad abierta y menor tamaño de poro, antioxidantes que
cierren poros, aditivos que formen espinela in situ, y —crítico— reducir los
ciclos térmicos.

**Oxidación del carbono (MgO-C, Al₂O₃-C, ZrO₂-C).** El grafite se oxida por O₂
del aire (directa, dominante durante el precalentamiento y la espera vacía) y
por FeO/SiO₂ de la escoria (indirecta). Al perder el carbono, el refractario
pierde su resistencia al mojado por escoria y su conductividad, y queda una capa
descarburada porosa que se erosiona sola. Señal: banda gris/blanca en la cara,
friable. **Este mecanismo conecta directamente con el proyecto de
precalentamiento**: una olla vacía a 1000-1400 °C con aire dentro está oxidando
carbono continuamente, y un precalentador con exceso de aire lo acelera. Un
precalentamiento largo mal regulado puede costar más campaña de la que ahorra
en temperatura de colada.

**Hidratación de MgO y CaO.** MgO + H₂O → Mg(OH)₂ con fuerte expansión de
volumen; agrieta y disgrega. Ocurre con refractarios básicos almacenados sin
protección, con humedad de la nave o con agua de refrigeración. Señal:
disgregación pulverulenta sin haber estado en servicio caliente.

**Ataque por álcalis (K, Na) y por zinc.** Típico de alto horno y de hornos que
reciben carga con recirculados. Los álcalis condensan en el interior del
ladrillo y forman leucita/kaliofilita con expansión, o catalizan la
desintegración por CO. El zinc penetra y oxida. Señal: expansión y agrietamiento
en zonas de temperatura intermedia, no en la cara más caliente.

**Desintegración por CO.** 2CO → C + CO₂ catalizada por hierro metálico
finamente disperso; el carbono depositado en los poros revienta la estructura.
Señal: disgregación en la banda de 400-600 °C. Palanca: minimizar el hierro
libre en la matriz.

### Térmicos

**Spalling térmico (choque térmico).** Gradientes fuertes generan tracción en la
cara. Señal: red de grietas y desprendimiento de fragmentos angulares en los
primeros ciclos. Depende del parámetro de resistencia al choque térmico
R = σ_r·(1−ν)/(E·α) y, para propagación, de R'''' (energía de fractura frente a
energía elástica). **Esto es lo que limita la velocidad de rampa del
precalentador.** Un material tenaz (MgO-C) tolera rampas mucho más agresivas que
un castable denso de alúmina.

**Fatiga térmica.** Ciclado repetido por debajo del umbral de fractura
inmediata. Es el modo dominante en una olla con muchas coladas al día y esperas
largas. Señal: degradación progresiva sin evento único identificable.

### Termomecánicos

**Fluencia (creep) y cierre de juntas.** Bajo carga a temperatura, el
refractario fluye; las juntas se cierran y aparecen tensiones de compresión que
pueden pandear el revestimiento o abombar la carcasa. Palanca: diseño de juntas
de expansión, no material.

**Desajuste de expansión entre capas.** Trabajo, seguridad, aislante y carcasa
expanden distinto. Es un factor de diseño del sistema, no del ladrillo.

### Mecánicos

**Erosión y abrasión** por el chorro de llenado, por agitación con argón y por
flujo de escoria. Señal: desgaste localizado en la zona de impacto y frente al
tapón poroso, con superficie rugosa.

**Daño de operación**: desescoriado, retirada de costras, choques del carro,
manipulación. A menudo es una fracción del desgaste mucho mayor de lo que se
reconoce; se detecta comparando ollas de la misma campaña con distinta
tripulación o distinto turno.

## Cómo conectar un mecanismo con este proyecto

El modelo térmico da la historia térmica: perfiles T(x,t), número y amplitud de
los ciclos, velocidad de rampa, tiempo por encima de temperaturas críticas.
Preguntas que el modelo ya puede responder y que tocan directamente al desgaste:

- ¿Cuánto tiempo por colada pasa la cara caliente por encima de 1200 °C con aire
  dentro? (→ oxidación de carbono)
- ¿Cuál es el gradiente máximo en la cara al llenar, y cómo cambia si la olla
  entra más fría? (→ choque térmico)
- ¿Cuántos ciclos completos frío-caliente ve el revestimiento al mes con la
  práctica actual? (→ fatiga y spalling estructural)
- ¿Cuánto baja la amplitud del ciclo si se tapa la olla durante la espera?
  (→ vida de campaña)

Ese último es probablemente el resultado de mayor valor económico del proyecto,
y sale del mismo modelo sin trabajo adicional.
