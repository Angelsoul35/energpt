# 01 — El consumo y la serie horaria

## Qué medimos

Un contador inteligente emite una lectura por hora: cuánta energía ha consumido la
vivienda en esa hora. La unidad es el **vatio-hora (Wh)**: 1000 Wh = 1 kWh, que es
la unidad que aparece en la factura. En EnerGPT cada lectura es un **entero en
Wh**, para que las sumas sean exactas (el dinero, más adelante, también será
entero, en céntimos).

Una serie de 14 días son `14 * 24 = 336` lecturas, empezando a medianoche.

## Por qué sintetizamos la serie

No tenemos un contador real conectado, así que **generamos** una serie plausible
(`generate.py`). Esto permite tener algo que analizar sin depender de datos
externos, y —muy importante— hacerlo **determinista**: con la misma semilla
(`seed`) siempre sale la misma serie. Esa reproducibilidad es la que hace que el
análisis posterior se pueda testear con números exactos.

## La forma de la serie

Imitamos cómo consume de verdad un hogar, sumando varias componentes:

- **Carga base:** un suelo constante que siempre está encendido (nevera, router,
  aparatos en espera). La vivienda nunca baja de ahí.
- **Patrón diario:** un valle de madrugada, un repunte por la mañana y un **pico
  fuerte por la tarde-noche** (cocinar, luz, calefacción). Es una curva por hora
  del día.
- **Patrón semanal:** algo más de consumo de día los fines de semana.
- **Ruido:** una pequeña variación aleatoria para que no haya dos horas idénticas.

Cada lectura se recorta a un valor positivo (el consumo nunca es negativo).

## Muestras con nombre

Definimos varias viviendas de ejemplo (`SAMPLES`): `home` (hogar de dos personas),
`apartment` (piso pequeño, carga base baja) y `house` (casa grande con calefacción
eléctrica y pico de tarde muy marcado). Cada una tiene su carga base, su escala de
pico, su repunte de fin de semana, su ruido y su semilla. Así se ve que el análisis
reacciona de forma distinta a perfiles distintos.

## Para fijar la idea

- Una lectura por hora, en Wh enteros, empezando a medianoche.
- La serie es sintética pero **determinista** (semilla fija).
- Su forma = carga base + curva diaria + fin de semana + ruido.
