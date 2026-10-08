# 05 — Preguntas de entrevista

Preguntas típicas sobre este proyecto y cómo responderlas.

### "¿Por qué no dejas que el LLM dé directamente los consejos y los números?"
Porque un LLM inventa cifras plausibles pero sin base ("ahorrarías un 15%") que no
se pueden auditar. Aquí la **sustancia se calcula de forma determinista** en
`analysis.py` y el LLM **solo redacta** esos números. Al modelo no se le hace
ninguna pregunta cuantitativa: recibe la respuesta y la escribe en prosa.

### "¿Cómo garantizas que la recomendación no se inventa números?"
La plantilla se arma solo con un diccionario de *hechos* calculados. Un test
extrae todas las cifras de dinero, energía y porcentaje del texto y comprueba que
cada una está entre los hechos. Si escribiera una cifra a mano, el test fallaría. Y
siempre devuelvo el análisis estructurado junto a la prosa para poder contrastarlo.

### "¿Por qué enteros en céntimos y no `float`?"
`float` no representa decimales exactos y acumula error (`0,1 + 0,2 ≠ 0,3`).
Enteros en céntimos dan sumas exactas. El coste es `(energia_wh * tarifa + 500) //
1000`, redondeo al céntimo en aritmética entera, aplicado una vez por bloque de
energía para que el redondeo no se acumule.

### "¿De dónde salen los ahorros? ¿No son inventados?"
De la estructura de la tarifa por tramos. **Desplazar carga** ahorra la diferencia
de precio punta-valle sobre la energía que se mueve (la energía total no baja).
**Reducir standby** quita potencia de todas las horas, cada una a su precio. Los
porcentajes (30%, 25%) son supuestos de configuración, expuestos como ajustes para
que quede claro que son parámetros; la aritmética sobre ellos es exacta.

### "¿Qué es el factor de carga y por qué lo calculas?"
Es `consumo medio / consumo máximo`. Cerca de 1 la demanda es plana (barata de
servir); cerca de 0 tiene picos (cara, porque la red se dimensiona para el pico).
Es un indicador clásico del sector eléctrico y contextualiza el ahorro por
desplazamiento de carga.

### "¿Funciona sin conexión ni claves de API?"
Sí, ese es el modo por defecto. Si no hay clave de proveedor en el entorno, el
servicio no construye ningún cliente LLM y una plantilla determinista redacta el
consejo, sin ninguna llamada de red. Con clave, el LLM redacta los **mismos**
números. El campo `source` dice qué camino se usó.

### "¿Cómo cambiarías de proveedor de LLM?"
El LLM es una interfaz `LLMClient` con una cascada (Anthropic, OpenAI, Gemini,
DeepSeek, Ollama). Cambiar el orden en `EP_LLM_SPEC` o añadir un adaptador basta;
el asesor y el motor no se tocan. Si todos fallan, cae a la plantilla.

### "¿Qué harías para llevarlo a producción?"
Ingerir datos reales de contador en vez de la serie sintética; modelar una tarifa
completa (término de potencia, término fijo, excedentes de autoconsumo); y sacar
los porcentajes de desplazable/standby de una **desagregación por
electrodoméstico** real, en vez de supuestos fijos. La arquitectura —calcular la
sustancia y que el LLM solo la redacte— se mantiene.
