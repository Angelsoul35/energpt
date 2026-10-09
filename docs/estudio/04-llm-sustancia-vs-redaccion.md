# 04 — Sustancia determinista vs. redacción del LLM

## La decisión clave de confianza

El fallo típico de un "asesor energético con IA" es dar un número con seguridad y
sin base: le preguntas cuánto ahorrarías y te suelta "un 15%" que no sale de tus
datos y no se puede comprobar. EnerGPT **saca al modelo del cálculo por completo**.

- **El análisis calcula la sustancia.** Qué hacer y cuánto ahorra se calcula en
  `analysis.py`, de forma determinista, a partir de la serie.
- **El LLM solo redacta.** El asesor (`advisor.py`) construye un diccionario fijo
  de *hechos* formateados a partir del análisis y redacta **solo** con esos
  hechos. Al LLM se le pasan esos mismos hechos y se le ordena ceñirse a ellos y
  no inventar ningún número.

Al LLM nunca se le hace una pregunta cuantitativa. Recibe la respuesta ya
calculada y la escribe en prosa.

## Offline y online dan la misma sustancia

- **Sin clave de API:** el asesor no construye ningún cliente LLM y una
  **plantilla determinista** redacta los hechos. Cero red.
- **Con clave:** el LLM redacta **los mismos hechos**. El consejo (qué hacer,
  cuánto se ahorra) no cambia; solo cambia la redacción.

El resultado guarda de dónde salió el texto: `source` es `"llm"` o `"template"`.
Así el lector sabe qué camino se usó.

## "No inventa números": cómo se garantiza

La plantilla se arma **solo** interpolando los hechos. Un test
(`test_template_invents_no_numbers`) extrae del texto todas las cifras de dinero,
energía y porcentaje y comprueba que cada una está entre los hechos calculados. Si
alguien escribiera "ahorra un 10%" a mano en la prosa, el test fallaría. El camino
del LLM lleva la misma instrucción y, además, siempre se devuelve el análisis
estructurado al lado, para poder contrastar la prosa con los números.

## Cascada de proveedores (agnóstica)

El LLM es una interfaz `LLMClient` con una **cascada** sobre Anthropic, OpenAI,
Gemini, DeepSeek y Ollama (cada uno un adaptador HTTP fino que lee su clave del
entorno). La cascada prueba los proveedores en orden y, si uno falla (sin clave,
error de red), pasa al siguiente; si fallan todos, el asesor cae a la plantilla.

La decisión de construir o no el cliente la toma el servicio: solo lo construye si
hay alguna clave de proveedor en el entorno. Sin clave → plantilla y sin llamadas
de red (ni siquiera a localhost). Es el valor por defecto seguro.

## Para fijar la idea

- El LLM redacta; **nunca** calcula.
- Mismos hechos offline y online; cambia la redacción, no el consejo.
- La plantilla no puede inventar cifras (lo verifica un test).
- Cascada agnóstica de proveedores con caída a plantilla.
