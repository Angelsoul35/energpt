# 02 — El análisis determinista

Este es el **motor** y el verdadero valor del proyecto (`analysis.py`). Calcula,
con aritmética sencilla y reproducible, todo lo que luego se aconseja. El LLM no
interviene aquí en absoluto.

## Horas punta de consumo

Calculamos la lectura **media por hora del día** (las 24 horas) y nos quedamos con
las que más consumen. No es lo mismo que la "hora punta de la tarifa": aquí es
*cuándo gasta la vivienda*. Si esas horas caen dentro del tramo caro de la tarifa,
hay un problema caro (y una oportunidad clara de ahorro).

Los empates se rompen por la hora más temprana, para que el resultado sea
determinista.

## Carga base (mínimo nocturno)

La **carga base** es el suelo que la vivienda siempre consume. La leemos como el
**mínimo** de las lecturas dentro de la ventana nocturna (por defecto, de 00:00 a
06:00): a esa hora no hay actividad, así que lo que quede es lo que está "siempre
encendido" (nevera, router, aparatos en espera). Es la base del ahorro por standby.

## Factor de carga

El **factor de carga** es `consumo medio / consumo máximo`, un número entre 0 y 1:

- cerca de **1** → demanda plana (fácil y barata de servir);
- cerca de **0** → demanda con picos (cara: la red tiene que dimensionarse para el
  pico aunque dure poco).

Es un ratio, no dinero, así que es un `float` redondeado a cuatro decimales. Nunca
entra en un cálculo monetario.

## Por qué el dinero son enteros en céntimos

Los ordenadores no representan `0,1 + 0,2` exactamente en coma flotante (da
`0,30000000000000004`). Un sistema de dinero sobre `float` acumula error. Por eso
**todo el dinero es `int` en céntimos** y las tarifas son céntimos por kWh. El
coste de una energía es:

```
coste_cent(energia_wh, tarifa_cent_por_kwh) = (energia_wh * tarifa + 500) // 1000
```

Eso es redondeo al céntimo "a la mitad hacia arriba", en aritmética entera pura. Y
se redondea **una sola vez por bloque** de energía (toda la energía punta, toda la
valle…), nunca hora a hora, para que el error de redondeo no se acumule.

## Determinista de punta a punta

Dada la serie y la configuración, cada número de salida está determinado. Por eso
el test `test_analysis.py` construye una serie a mano y comprueba cada cifra al
céntimo: si el motor fuera "casi" correcto, el test lo cazaría.

## Para fijar la idea

- Horas punta de consumo = medias por hora del día; carga base = mínimo nocturno.
- Factor de carga = medio/máximo (plano vs. con picos).
- Dinero en céntimos enteros; un solo redondeo por bloque.
