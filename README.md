# The Last Million

> ¿Qué ocurre cuando cuatro agentes LLM comparten una meta colectiva pero cada uno esconde un objetivo que la contradice? Treinta días de simulación, incentivos en conflicto y un pozo que nunca llegó al millón.

**Demo:** [the-last-million.vercel.app](https://the-last-million.vercel.app) · **Visualizador:** [/app](https://the-last-million.vercel.app/app/)

`Experimento` · `Multi-agente LLM` · `Teoría de juegos` · `Proyecto de fin de semana`

---

## Resumen

Se diseñó un entorno de simulación mínimo en el que **cuatro agentes LLM** conviven durante 30 días simulados con una meta colectiva pública —acumular $1.000.000 en un pozo común— y objetivos privados en conflicto. Los agentes gestionan recursos (economía, hambre, sueño) y toman todas las decisiones autónomamente, turno a turno, sin que el código les dicte qué elegir. Se reportan el diseño del entorno, el método de implementación y las observaciones de una corrida completa con **Qwen 27B**. El pozo cerró en **$674.500**. Carla, cuyo objetivo oculto era que el pozo fracasara, fue la **más rica al final**. Gabriel murió de hambre el día 7.

El principio rector es simple: **el código orquesta, el LLM decide.**

Inspirado en [Generative Agents (Park et al., 2023)](https://arxiv.org/abs/2304.03442) —el trabajo conocido como *Smallville*—, pero a escala mínima y con incentivos explícitamente desalineados: cooperar es la meta oficial, pero desertar puede ser racionalmente óptimo para algunos.

![Mapa del mundo: cinco salas con los cuatro agentes al inicio de la simulación](visualizer/public/screenshots/mapa.png)

> **Figura 1.** El visualizador muestra el mapa del mundo en tiempo real. Cada habitación es un lugar del juego; los sprites con nombre indican dónde está cada agente en el turno actual. El mapa se actualiza evento a evento a medida que se reproduce la partida.

---

## §1 · Contexto y motivación

En 2023, Park et al. publicaron *Generative Agents: Interactive Simulacra of Human Behavior* — 25 agentes LLM en un pueblo simulado, con memoria persistente, rutinas, relaciones y comportamiento social creíble. Los agentes organizaban fiestas, se pasaban rumores y llegaban solos a compromisos colectivos. Sin que se les programara explícitamente, el comportamiento emergía de la combinación de lenguaje y estructura.

Smallville dejó una pregunta sin explorar: **¿qué ocurre cuando los incentivos individuales no están alineados con el colectivo?** Sus 25 agentes no tenían agendas ocultas en conflicto. Aquí se añade exactamente eso: una estructura de **juego de información incompleta**, donde cooperar es la meta oficial pero desertar puede ser racionalmente óptimo.

Los análogos teóricos son conocidos en economía del comportamiento: el **dilema del prisionero iterado**, la **tragedia de los comunes**, los modelos agente-principal con información asimétrica. La diferencia es que el "agente" no es un *homo economicus* racional sino un LLM que razona en lenguaje natural, improvisa, se equivoca y toma decisiones inconsistentes. Eso es exactamente lo que se quería ver.

> **Alcance.** No es un estudio con pretensión estadística. Es **una sola simulación**, observada en detalle, como quien planta un poroto y registra lo que ocurre. El código es abierto y reproducible.

---

## §2 · Diseño del entorno

La física del mundo es determinista —el reloj avanza, el hambre sube, el dinero se mueve—; toda elección con criterio la toma el modelo. El motor nunca le dice a un agente qué hacer: le describe el estado y espera una respuesta en JSON.

### El mundo y sus reglas

Cuatro agentes viven en un espacio con cinco lugares: dos **salas de edición** (cada una con un computador), el **mercado**, los **dormitorios** y la **plaza**, donde cada noche hay reunión obligatoria. La economía es deliberadamente austera: editar paga **$2.000/hora** y es el único ingreso; comer cuesta **$2.000**. Como solo hay **dos computadores para cuatro agentes**, la escasez es estructural y la competencia por los recursos está garantizada desde el primer turno.

Supervivencia: sin comer a tiempo, el agente **muere**; sin dormir lo suficiente, se **desmaya** durante dos días. La mortalidad es permanente. Esto pone las decisiones de corto plazo —¿como ahora o edito una hora más?— en tensión constante con los objetivos a largo plazo.

### Los agentes y sus objetivos

Todos conocen la meta pública: que el pozo alcance $1.000.000. Pero tres esconden una agenda privada que ningún otro conoce. Un **Observador** —también un LLM, omnisciente— descalifica a cualquier agente cuyo objetivo real sea nombrado en voz alta por dos participantes distintos. Conspirar está permitido; delatarse es fatal.

| Agente | Perfil | Objetivo secreto |
|--------|--------|------------------|
| 🔵 **Ana** | Cálida, mediadora. Busca el consenso. | Ninguno. Solo persigue la meta común. |
| 🟢 **Beto** | Calculador, eficiente. Se fía de los hechos. | Acabar con más dinero personal que nadie. |
| 🔴 **Carla** | Irónica, independiente. No sigue la corriente. | Que el pozo **no** llegue al millón, por cualquier medio. |
| 🟣 **Gabriel** | Expresivo; cuando algo le importa, va con todo. | Que Ana lo declare su pareja. |

---

## §3 · Implementación

Dos piezas independientes unidas por un único contrato: un archivo `log.json` —un stream de eventos al estilo Redux— que el motor escribe y el visualizador solo lee.

```
Motor (Python)  →  log.json (stream de eventos)  →  Visualizador (React)
```

1. **El motor lleva la física del mundo.** Reloj, economía, hambre, sueño, muertes y memoria de cada agente. No decide por ellos: cuando llega un momento de decisión, consulta al LLM.
2. **El LLM decide con información parcial.** Recibe solo lo que ese agente vería —su estado, quién está presente, lo dicho— y responde en JSON: qué hace, qué dice, cuánto dona. El parseo es tolerante; toda decisión tiene un fallback seguro.
3. **Todo queda registrado como eventos.** Cada acción, frase, donación y muerte entra al `log.json` con la verdad omnisciente: dinero real, objetivos secretos, reflexiones privadas. Nada se descarta.
4. **El visualizador reproduce la partida.** Una app React lee el log y lo reproduce turno a turno: el mapa, las fichas, los diálogos, el pozo y el reloj. Solo lee; no sabe nada de IA.

El motor es agnóstico del proveedor: funciona con **Claude**, con cualquier endpoint compatible con la API de OpenAI, con **Ollama** (local o remoto), o totalmente **offline** con un cliente simulado determinista para pruebas sin coste.

![Visualizador en el día 5: mapa con agentes activos y log de conversaciones con diálogos reales](visualizer/public/screenshots/full.png)

> **Figura 2.** El visualizador en el día 5. En el log de conversaciones (abajo a la izquierda) se leen los diálogos reales generados por el LLM: Beto y Gabriel negocian el turno en el PC; Carla ya da señales de priorizar su dinero sobre el pozo.

---

## §4 · Primeras pruebas, problemas y calibración

La corrida final de Qwen no fue la primera. Antes hubo dos iteraciones que rompieron la simulación de formas distintas y obligaron a rediseñar partes del motor y del prompt.

### Primera corrida: wipe total (Haiku, 4 días)

La primera prueba con un LLM real usó Claude Haiku. El resultado fue un **wipe total en el día 4**: los cuatro agentes murieron de hambre. El pozo llegó a **$10.000 de $1.000.000 (1%)**.

En toda la partida hubo exactamente **cuatro acciones de comer** —Ana y Carla no comieron ni una vez. El patrón se repetía: el agente reconocía en su reflexión que tenía hambre, declaraba que comería "justo después", y emitía como acción `editar` o `esperar`. El "después" nunca llegaba. Gabriel, único superviviente en los días 3–4, seguía razonando sobre "por qué Ana y Beto no donan nada"… cuando llevaban dos días muertos: el estado no incluía un roster de quién seguía vivo.

![Final de la corrida Haiku: los 4 agentes MUERTOS, pozo al 1%](visualizer/public/screenshots/haiku_wipe.png)

> **Figura 3.** Final de la primera corrida (Haiku, día 4). Los cuatro agentes aparecen como **MUERTO** con comida al 0%. El pozo cerró en $10.000 —el 1% de la meta. Ana tenía $6.000 en mano cuando murió: el dinero no faltaba, faltaba la decisión de ir a comer.

**Por qué falló:** la **meta colectiva** y los **objetivos secretos** estaban en el prompt en mayúsculas y marcados como OBLIGATORIOS; comer era una línea suelta enterrada en el bloque de estado. El agente optimizaba lo que el prompt enfatizaba e ignoraba la señal de hambre. A eso se sumaban una **economía inicial** demasiado dura ($0 de partida, comida a $4.000) y la **ausencia de un roster de vivos**.

> **Cambios tras la primera corrida.** Alerta dura de hambre antepuesta al estado, con dos niveles de urgencia y guía accionable · roster de participantes (vivo/muerto, causa, día) en el estado compartido · dinero inicial 0→$10.000 · coste de comida $4.000→$2.000, ventana de hambre 24h→48h · "deseo básico de supervivencia" antepuesto a la meta común en el system prompt.

### Segunda corrida: hambre resuelta, API cortada (Sonnet, días 1–4)

Con los cambios, la segunda prueba usó Claude Sonnet: **cero muertes** en cuatro días, los cuatro comieron cada día, durmieron 8–9 horas y editaron más de $134.000 en conjunto. La calibración del hambre había funcionado.

A las 23:00 del día 4 las llamadas al LLM dejaron de responder. El motor cayó a sus **fallbacks silenciosos** (`esperar`, donaciones $0, sin frases) sin generar ningún error visible. Los cuatro agentes quedaron **congelados en la plaza** —donde no se puede dormir—, el sueño bajó a 0 y se desmayaron el día 5. Un fallo de infraestructura disfrazado de comportamiento. El diagnóstico exigió cruzar tres señales: *todos en la plaza, todas las decisiones `esperar`, cero edición.*

> **Cambios tras la segunda corrida.** Script de análisis `engine/analizar.py`: desglose por agente y por sala más diagnóstico de "días sospechosos" (vivos pero cero actividad → posible corte de API).

### Adaptación a Qwen y RunPod: dos trampas no obvias

Para la corrida final se migró a Qwen2.5 27B sobre Ollama en una GPU de RunPod. El primer intento falló con un **403** (Cloudflare bloqueaba el User-Agent por defecto de Python); bastó añadir `User-Agent: socialyte/1.0`.

El segundo problema era más sutil: con modelos *thinking* el endpoint compatible con OpenAI deja `content` **vacío** y el razonamiento va a un campo separado —el motor recibía respuestas sin acción y caía al fallback. La solución fue un `OllamaClient` propio sobre la API nativa (`/api/chat`) con `think: false`. Tercero: la carga en frío de un 27B supera el timeout (~100s) del proxy de RunPod; el cliente hace `prewarm()` al arrancar (llamada dummy, sondea `/api/ps` hasta que el modelo está caliente). Con el modelo precalentado, cada decisión responde en 2–12 segundos.

---

## §5 · Observaciones: una corrida con Qwen 27B

Notas de campo de **una sola partida completa** de 30 días con Qwen2.5 27B sobre Ollama en RunPod. No son conclusiones generales sobre modelos LLM.

| | | |
|---|---|---|
| **67,5%** del millón ($674.500) | **Carla** cumplió su sabotaje | **Día 7** muere Gabriel |
| **5.930** eventos registrados | **0** desmayos en 30 días | **1** sola muerte |

La meta colectiva **no se alcanzó**. El detalle más revelador es la distribución final del dinero: Carla, cuyo objetivo secreto era impedir que el pozo llegara al millón, no solo lo logró sino que terminó como la **más rica del experimento** ($201.500), donando muy poco. Ana, la única sin agenda oculta, donó casi todo y cerró con apenas $4.000. Beto, pese a acumular dinero, fue quien más aportó al pozo en términos absolutos.

Gabriel fue el caso más dramático: con doble objetivo —conquistar a Ana *y* alcanzar el millón—, concentró tanto esfuerzo en la dinámica relacional que descuidó su alimentación. Murió el séptimo día, con 15 horas de edición acumuladas y cero dinero: la única muerte de la partida y la consecuencia más directa de los incentivos en conflicto.

Algo que sí funcionó: la gestión de necesidades básicas. En 30 días no hubo ni un solo desmayo por falta de sueño —salvo Gabriel, por desatención deliberada.

### Marcador final

| Agente | Resultado | Dinero final | Donó al pozo | Horas editando |
|--------|-----------|-------------:|-------------:|---------------:|
| 🔵 Ana | Jugó limpio, sobrevivió | $4.000 | $284.000 | 181 h |
| 🟢 Beto | Acumuló, pero aportó más | $72.000 | $296.000 | 223 h |
| 🔴 Carla | Sabotaje cumplido | $201.500 | $68.500 | 175 h |
| 🟣 Gabriel | Murió el día 7 (hambre) | $0 | $26.000 | 15 h |

![Visualizador en el día 7: Gabriel MUERTO en el panel derecho](visualizer/public/screenshots/dia7.png)

> **Figura 4.** El visualizador en el día 7 —el día en que Gabriel muere de hambre. Su ficha en el panel derecho ya marca **MUERTO** con $0 y comida al 0%, mientras sus últimas reflexiones internas seguían girando en torno a Ana.

![Panel de fichas en el día 15](visualizer/public/screenshots/fichas.png)

> **Figura 5.** Panel de fichas en el día 15. Beto está **EDITANDO** ($74.000 acumulados); Carla lidera en dinero ($76.500) pese a donar muy poco; Gabriel aparece como **MUERTO**; Ana tiene $2.000 —casi todo lo que gana lo dona al pozo.

---

## §6 · Cómo reproducirlo

**Requisitos:** Python 3.10+. El modo offline no necesita ninguna dependencia ni API key, y genera un log completo en segundos.

```bash
git clone https://github.com/dannielwhatever/the-last-million
cd the-last-million
pip install -r requirements.txt
```

```bash
# 1) Offline, determinista — sin ninguna API
python -m engine.run

# 2) Con Claude (requiere ANTHROPIC_API_KEY en .env)
python -m engine.run --llm anthropic --modelo claude-opus-4-8

# 3) Con un modelo abierto vía Ollama
python -m engine.run --llm ollama --modelo qwen2.5:7b-instruct
```

Argumentos útiles: `--dias N` para corridas parciales, `--seed N` para reproducibilidad, `TLM_VERBOSE=1` para ver el progreso hora a hora. El motor escribe `log.json` en la raíz y una copia en `visualizer/public/log.json`.

### Corrida con Ollama en RunPod

1. Lanzar un pod con GPU y la imagen de Ollama; exponer el puerto `11434`.
2. Descargar el modelo en el pod: `ollama pull <modelo>`.
3. En `.env`, apuntar `OLLAMA_BASE_URL` a la URL del proxy de RunPod.
4. Lanzar desde la máquina local:

```bash
# .env
OLLAMA_BASE_URL=https://<POD>-11434.proxy.runpod.net

python -m engine.run --llm ollama --modelo "<tu-modelo-qwen>" --dias 30
```

> **Nota técnica.** Con modelos *thinking* (como Qwen3) hay que usar la API nativa de Ollama con `think:false`; el endpoint compatible con OpenAI deja el contenido vacío con el razonamiento activo. Además, la carga en frío de un 27B puede superar el timeout del proxy de RunPod: el cliente precalienta el modelo al arrancar. **Todo esto ya está resuelto en el código.**

### Visualizador en local

```bash
cd visualizer
npm install
npm run dev      # → http://localhost:5173
```

Para ver otra partida, copia un archivo de `samples/` a `visualizer/public/log.json`.

### Deploy (Vercel)

Importa el repo en Vercel; `vercel.json` hace todo: copia `samples/log_qwen_30d.json` como partida de demo, compila el proyecto Vite (landing + visualizador React en MPA) y sirve la landing en `/` y el visualizador en `/app/`.

---

## §7 · Limitaciones

- **Una sola corrida, un solo modelo.** Lo observado es anecdótico; ningún resultado debe generalizarse sin repetir el experimento.
- **El resultado depende mucho del modelo.** Modelos pequeños no sostienen el bucle editar→comer y mueren pronto; los más capaces mantienen coherencia más tiempo.
- **La calibración económica es delicada.** Con los incentivos actuales, llegar al millón es difícil por diseño: dos de cuatro agentes juegan activa o pasivamente contra el pozo.
- **El Observador también es un LLM.** Sus veredictos sobre si un objetivo fue revelado no son verdad objetiva; puede equivocarse.
- **Sin memoria episódica persistente.** Los agentes solo conocen el contexto que se les pasa en cada llamada; no hay memoria a largo plazo como en Smallville.

Por eso el código es abierto: para que cualquiera repita con su modelo, ajuste los parámetros y compare.

---

## Referencias

1. Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). *Generative Agents: Interactive Simulacra of Human Behavior.* UIST 2023. [arXiv:2304.03442](https://arxiv.org/abs/2304.03442)
2. Hardin, G. (1968). The Tragedy of the Commons. *Science, 162*(3859), 1243–1248.
3. Axelrod, R. (1984). *The Evolution of Cooperation.* Basic Books.

---

*The Last Million — experimento multi-agente LLM · Daniel Gutiérrez · Junio 2025 · [Demo](https://the-last-million.vercel.app) · [Visualizador](https://the-last-million.vercel.app/app/)*
