# 01 — El consumo y la serie horaria

## Qué medimos

Un contador inteligente emite una lectura por hora: cuánta energía ha consumido la
vivienda en esa hora. La unidad es el **vatio-hora (Wh)**: 1000 Wh = 1 kWh, que es
la unidad que aparece en la factura. En EnerGPT cada lectura es un **entero en
Wh**, para que las sumas sean exactas (el dinero, más adelante, también será
entero, en céntimos).

Una serie de 14 días son `14 * 24 = 336` lecturas, empezando a medianoche.

## Dos fuentes de series: sintética y real

EnerGPT trabaja con series de dos orígenes, y las dos importan:

1. **Serie sintética (`generate.py`)** para los demos y las pruebas. Es
   **determinista**: con la misma semilla (`seed`) siempre sale la misma serie. Esa
   reproducibilidad es lo que permite testear el análisis con números exactos (ver
   capítulo 02), sin depender de una descarga.
2. **Serie real (`real_data.py`)**: un tramo real del ensayo *Low Carbon London*
   (contadores inteligentes del Reino Unido), vendoreado en
   `datasets/london_real.npz`. Son 10 viviendas reales, 14 días, lectura horaria.
   El motor es el mismo; solo cambia de dónde salen los números.

El ensayo publicó lecturas **cada media hora en kWh**. Como el motor trabaja en
**Wh por hora**, sumamos cada par de medias horas y pasamos a Wh entero
(`kWh * 1000`, redondeado). Es una conversión exacta de unidades, no una estimación.

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

## Validación con datos reales (Low Carbon London)

El motor es **determinista** (aritmética de tarifa y desplazamiento de carga, no un
modelo entrenado). Por eso aquí no hay "exactitud" ni over/underfitting que medir:
la pregunta correcta para un motor determinista es otra —*¿produce consejos
correctos y sensatos sobre viviendas reales, no solo sobre el generador?*—.

Para responderla, `python -m energpt.real_benchmark` corre el análisis y el asesor
offline sobre las 10 viviendas reales y resume:

```
mean energy / home    : 259.2 kWh en el periodo
mean projected saving : $14.31 / mes
median saving / cost  : 12.8% de la factura
pico de uso por hogar : 19:00 (5), 20:00 (8), 21:00 (7)  -> tarde-noche
```

Lo revelador es el **pico de la tarde-noche**: sin que nadie se lo diga, el motor
reconstruye a partir de contadores reales que la mayoría de hogares consume más
entre las 19:00 y las 21:00 —exactamente la curva residencial clásica—. Sobre la
vivienda `T1` (189,37 kWh en 14 días) el motor cuesta la factura en $32,99, ve que
sus tres horas pico caen dentro de la ventana cara (17:00–21:00) y propone un ahorro
de ~$5,50 en el periodo (desplazar carga + recortar espera), sin reducir la energía
total. Es el **mismo** consejo que da sobre las muestras sintéticas, ahora anclado en
medidores reales.

`tests/test_real_benchmark.py` lo comprueba de forma **funcional**: verifica las
invariantes del motor en las 10 viviendas (identidad contable `total_wh == suma`,
factor de carga en `(0, 1]`, horas pico en `0..23`, ahorro no negativo y acotado por
la factura) y que las métricas **reaccionan al dato** —la misma energía colocada
dentro de la ventana pico cuesta más y se aconseja desplazarla, mientras que fuera de
ella no—. Un test que no mirara el dato fallaría.

## Para fijar la idea

- Una lectura por hora, en Wh enteros, empezando a medianoche.
- Dos fuentes: una serie **sintética determinista** (semilla fija) para demos/tests,
  y una serie **real** (Low Carbon London) vendoreada para validar sobre contadores
  de verdad.
- Forma de la serie sintética = carga base + curva diaria + fin de semana + ruido.
- Al ser el motor determinista, "datos reales" significa **correr el motor sobre
  consumo real** y comprobar que el resultado es correcto y sensato, no medir una
  exactitud de modelo.
