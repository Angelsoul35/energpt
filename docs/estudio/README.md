# Guía de estudio — EnerGPT

Una guía en español para entender el proyecto a fondo y poder defenderlo en una
entrevista. El código, los comentarios y la documentación técnica están en inglés
(como en un entorno profesional real); esta guía explica el *porqué* de cada
decisión.

## Orden sugerido

1. [01 — El consumo y la serie horaria](01-consumo-y-series.md)
   Qué medimos, las dos fuentes de series (sintética determinista y datos reales de
   Low Carbon London) y cómo se valida el motor sobre contadores reales.
2. [02 — El análisis determinista](02-analisis-determinista.md)
   Horas punta, carga base, factor de carga y por qué el dinero son enteros en céntimos.
3. [03 — La tarifa y los ahorros](03-tarifa-y-ahorros.md)
   La tarifa por tramos horarios y cómo se calcula cada oportunidad de ahorro.
4. [04 — Sustancia determinista vs. redacción del LLM](04-llm-sustancia-vs-redaccion.md)
   La decisión clave de confianza: el LLM redacta, no calcula.
5. [05 — Preguntas de entrevista](05-preguntas-de-entrevista.md)
   Preguntas típicas y cómo responderlas con este proyecto.

## La idea en una frase

Un motor **determinista** calcula todo lo que importa de una serie de consumo
eléctrico (horas punta, carga base, factor de carga, coste con tarifa por tramos y
ahorros cuantificados), y un LLM **solo redacta** esos números. Sin clave de API
funciona totalmente offline: una plantilla determinista redacta el mismo consejo.
