# 03 — La tarifa y los ahorros

## Tarifa por tramos horarios (time-of-use)

Modelamos una tarifa de **dos precios**: las horas dentro de la ventana punta
(por defecto 17:00-21:00) se cobran a la tarifa punta; el resto, a la tarifa valle
(más barata). La ventana puede cruzar la medianoche (p. ej. 22:00-02:00).

Con una tarifa plana solo se puede ahorrar **consumiendo menos**. Con una tarifa
por tramos, además importa **cuándo** consumes: el mismo kWh cuesta más en punta.
Ese es el mecanismo del que salen los ahorros.

Repartimos la energía en dos cubos —punta y valle—, y ponemos precio a cada uno:

```
coste_punta  = coste_cent(energia_punta, tarifa_punta)
coste_valle  = coste_cent(energia_valle, tarifa_valle)
factura      = coste_punta + coste_valle
```

## Oportunidad 1: desplazar carga de punta a valle

Si movemos un `EP_SHIFTABLE_PCT` (30% por defecto) de la energía de la ventana
punta a horas valle, **consumimos lo mismo** pero pagando la tarifa barata. El
ahorro es la diferencia de precio aplicada a la energía desplazada:

```
energia_desplazada = energia_punta * 30 // 100
ahorro = coste_cent(energia_desplazada, tarifa_punta)
       - coste_cent(energia_desplazada, tarifa_valle)
```

Ejemplo (del test a mano): 8000 Wh en punta → se desplazan 2400 Wh → ahorro
`72 - 29 = 43` céntimos. La energía total no baja: solo cambia de hora.

## Oportunidad 2: reducir el standby (carga base)

La carga base está presente **todas las horas**. Si recortamos un
`EP_STANDBY_REDUCTION_PCT` (25% por defecto) de ella, ahorramos esa potencia en
cada hora, y cada hora se valora **a su propio precio**: las horas punta a tarifa
punta, las valle a tarifa valle.

```
recorte_por_hora = carga_base * 25 // 100
ahorro = coste_cent(recorte_por_hora * horas_punta,  tarifa_punta)
       + coste_cent(recorte_por_hora * horas_valle,  tarifa_valle)
```

Ejemplo: carga base 100 Wh → recorte 25 Wh/h; con 8 horas punta y 40 valle →
`coste_cent(200, 30) + coste_cent(1000, 12) = 6 + 12 = 18` céntimos.

## Qué son esos porcentajes

El 30% y el 25% son **supuestos de configuración**, no una auditoría medida de una
vivienda concreta. Están expuestos como ajustes (`EP_...`) precisamente para que
sea evidente que son parámetros, no verdades. Un sistema de producción los sacaría
de datos reales por electrodoméstico. Lo que sí es exacto es la aritmética que se
aplica a esos supuestos.

## Para fijar la idea

- Dos precios; lo que importa es *cuándo* consumes.
- Desplazar carga = ahorrar la diferencia de precio sobre la energía movida.
- Reducir standby = quitar potencia de todas las horas, cada una a su precio.
- Los porcentajes son supuestos configurables; la aritmética, exacta.
