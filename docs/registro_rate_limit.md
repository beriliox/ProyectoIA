## Registro del ensayo de rate limit

- Fecha: 2026-10-27
- Peticiones enviadas: 10
- Petición donde apareció el primer 429: la número 1 (la número 0 respondió directo)
- Esperas observadas: 0.0s, 2.0–2.2s, 6.1–6.5s (backoff con jitter, pero mal calculado: debería ser 2s, 4s, 8s)
- Costo total del ensayo: $0.00130
- Resultado: 2 peticiones con éxito (0 directa con 381 tokens; 1 tras reintentar, 271 tokens) y 8 fallaron tras agotar reintentos (2 a 9)

### Observaciones
- Límite topado: `GenerateRequestsPerDayPerProjectPerModel-FreeTier` = 20 peticiones por día. El proveedor pidió
  esperar ~7900s (`retryDelay`), mucho más que los ~8.5s que suma el backoff, por eso los reintentos no alcanzan
- Cada reintento cuenta como petición contra la cuota diaria: 10 preguntas con hasta 4 intentos cada una agotan las 20 rápidamente
- El costo se registró solo en las 2 peticiones completadas; las fallidas no sumaron nada
- Las fallidas terminaron en `RuntimeError` con mensaje claro, sin excepciones de `requests`
- `con_reintento` calcula mal el backoff (`2 ** intento - 1` → 0s, 2s, 6s) y hace 4 intentos aunque el mensaje dice "3 de 3"
- Mismo ensayo con otra API key: 2 éxitos (peticiones 1 y 4), 8 fallos, $0.00126. La clave activa en `.env` ya estaba en 429 desde la primera petición
