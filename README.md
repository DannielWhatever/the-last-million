# The Last Million

**Un reality show de agentes LLM.** Cuatro agentes autónomos (Ana, Beto, Carla y
Gabriel) conviven 30 días en un mundo cerrado con una meta común —reunir un millón
en un pozo compartido— y agendas secretas que pueden hundirla. Nadie programa su
conducta: **el código orquesta, el LLM decide.**

> 🎬 **Landing + visualizador** listos para desplegar en Vercel (ver §5).
> El diseño completo del experimento (la "biblia") y las notas de trabajo viven en
> `docs/` como material interno (no versionado).

Dos piezas **totalmente desacopladas**, unidas por un único contrato, `log.json`:

```
[ Motor (Python) ] → genera → [ log.json (eventos, modelo Redux) ]
                                        ↓
                       [ Visualizador (React + TypeScript) ]
                                        ↓
              reducer aplica eventos → estado → render turno a turno
```

- **El código orquesta; el LLM decide.** El motor resuelve reloj, movimiento,
  economía, sueño/comida, muertes y memoria; consulta al LLM solo cuando hay algo
  que decidir.
- El log registra **TODO**, incluida la verdad omnisciente (dinero real, objetivos
  secretos, reflexiones privadas y las decisiones del Observador). La interfaz
  decide qué mostrar.

---

## 0. El experimento en una línea

Editar vídeos es la única fuente de ingreso; el dinero solo sirve para comer o
donar al pozo. Si no comes mueres; si no duermes te desmayas. Todos quieren que el
pozo llegue a **$1.000.000**… pero **Beto** quiere acabar siendo el más rico,
**Carla** quiere que el pozo fracase y **Gabriel** quiere que Ana sea su pareja.
Un **Observador** omnisciente dirige las conversaciones y descalifica a quien se
delate. **Ana** es la única que juega limpio.

---

## 1. Motor (Python)

Corre los 30 días por adelantado y escribe `log.json`. **No requiere conexión al
LLM** gracias a un cliente simulado offline; con una API key (o un Ollama local)
usa un modelo real.

Requisitos: Python 3.10+. El modo simulado no necesita dependencias.

```bash
pip install -r requirements.txt   # para los modos reales (anthropic / openai)
```

### Correr la simulación

```bash
# Modo simulado (offline, determinista) — genera un log demostrativo completo:
python -m engine.run

# Modo real con Claude (claude-opus-4-8): requiere ANTHROPIC_API_KEY:
python -m engine.run --llm anthropic

# Modo Ollama (p. ej. un Qwen local o remoto): usa la API nativa con think:false:
python -m engine.run --llm ollama --modelo qwen2.5:7b-instruct
```

Opciones: `--seed N`, `--dias N` (corrida parcial 1..30), `--salida ruta/log.json`,
`--sin-copia-visualizador`, `--silencioso`.

Durante la corrida el motor reporta el avance por `stderr`: pozo y supervivientes
por día, donaciones, muertes/desmayos y un resumen final con el veredicto. Pon
`TLM_VERBOSE=1` para ver además una línea por hora y por llamada al LLM (útil
con modelos locales lentos).

Por defecto escribe `log.json` en la raíz **y** una copia en
`visualizer/public/log.json` para que la app la sirva directamente.

### Configuración (`.env`) y secretos

Copia `.env.example` a `.env` y rellena lo que uses. El `.env` está en `.gitignore`
y **no se sube**: ahí van la clave de API y la URL del pod. Las variables de entorno
tienen prioridad sobre el `.env`.

### Proveedores de LLM

El **proveedor** se elige con `--llm`; el **modelo** con `--modelo` (o la variable
`TLM_MODELO`, o el default del proveedor en `engine/config.py`).

- **`--llm anthropic`** — Claude. Usa `ANTHROPIC_API_KEY`. Con *adaptive thinking*.
- **`--llm openai`** — cualquier API **compatible con OpenAI** (OpenAI, OpenRouter,
  Together, DeepSeek…). Usa `OPENAI_API_KEY` y, si no es OpenAI directo, `OPENAI_BASE_URL`.
- **`--llm ollama`** — Ollama por su API **nativa** (`/api/chat`) con `think:false`.
  Necesario para modelos *thinking* (p. ej. Qwen3): por el endpoint `/v1` el
  razonamiento dejaría el contenido vacío. Lee `OLLAMA_BASE_URL` (o `OPENAI_BASE_URL`).
  Mantiene el modelo caliente (`keep_alive`) y reintenta para sobrevivir a la carga
  en frío y a los timeouts de proxies (p. ej. RunPod). Solo usa la stdlib.
- **`MockClient`** (`engine/mock_llm.py`) — heurísticas deterministas offline que
  producen una partida plausible y rica, sin ninguna API.

> Para añadir otro proveedor con API distinta, crea una subclase de `PromptLLMClient`
> en `engine/llm.py` que implemente solo `_transporte(system, user, max_tokens)`:
> todo el armado de prompts se hereda.

### Estructura

```
engine/
  __init__.py     MAPA DE ONBOARDING: flujo de datos, ciclo de turno y glosario
  config.py       parámetros de ajuste (economía, reloj, memoria, modelo, umbrales)
  prompts.py      system prompts y prompts por tipo de llamada
  llm.py          LLMClient + AnthropicClient / OpenAICompatibleClient / OllamaClient
  mock_llm.py     MockClient (offline)
  rules.py        condiciones de victoria deterministas
  state.py        estado del mundo + emisión de eventos/snapshots
  simulation.py   bucle principal y orquestación
  run.py          punto de entrada (escribe log.json)
```

> ¿Nuevo en el motor? Empieza por el docstring de **`engine/__init__.py`** (mapa del
> paquete, ciclo de turno y glosario), y luego `Simulation._procesar_turno`.

---

## 2. Visualizador (React + TypeScript)

Solo **lee** el log y lo reproduce. No sabe nada de LLM ni de simulación.

```bash
cd visualizer
npm install
npm run dev      # http://localhost:5173
# o
npm run build && npm run preview
```

Carga `public/log.json`. Para ver otra partida, regenera el log con el motor (la
copia es automática) o copia un sample de `samples/` a `visualizer/public/log.json`.

Pantalla: mapa con los 5 lugares y los 4 agentes como fichas que se mueven; panel
omnisciente con dinero/sueño/comida, **objetivo secreto y dinero real**; pozo +
reloj; log de conversación y momentos del Observador; y controles modelo Redux
(play/pausa, paso adelante/atrás, salto a día, velocidad y línea de tiempo).

---

## 3. Parámetros de ajuste rápido

En `engine/config.py`:

- `PAGO_EDICION` ($2.000), `COSTO_COMIDA` ($2.000), `DINERO_INICIAL` ($10.000), `META_POZO` ($1.000.000)
- `VENTANA_COMIDA` (48 turnos sin comer = muerte) y `UMBRAL_HAMBRE_*` (alertas de hambre)
- `SUENO_*`, `DESMAYO_TURNOS` y `UMBRAL_SUENO_*` (alertas de sueño)
- `MINITURNOS_CONVERSACION` y `JUEZ_CADA_HORAS` (ritmo y coste de la conversación)
- `MAX_BLOQUE_EDICION` (salvaguarda anti-inanición)
- `MODELO_LLM` / `MODELO_OPENAI` / `MODELO_OLLAMA` y los `MAX_TOKENS_*`

---

## 4. Resultados de ejemplo

Las partidas en `samples/` se versionan (son las demos de la web). De la corrida
completa de 30 días con **Qwen 27B** (`samples/log_qwen_30d.json`, la que muestra el
visualizador desplegado):

- El **objetivo común fracasó**: el pozo cerró en **$674.500 (67,5%)**.
- **Carla ganó**: su meta secreta era que el pozo NO llegara al millón… y encima
  acabó siendo **la más rica** ($201.500), donando casi nada.
- **Ana** (juego limpio) lo dio casi todo y sobrevivió con $4.000.
- **Gabriel** murió de hambre el día 7 (obsesionado con Ana, descuidó comer).
- **0 desmayos** en 30 días: las alertas de sueño/hambre del prompt funcionaron.

---

## 5. Web (landing + visualizador) — deploy en Vercel

La raíz incluye una **landing** estática (`index.html`) que explica el experimento y
enlaza al visualizador. El `vercel.json` arma el sitio:

- compila el visualizador (Vite) y lo publica en **`/app/`**,
- sirve la **landing en `/`**,
- copia `samples/log_qwen_30d.json` como partida de demostración.

En Vercel, importa el repo y despliega sin más configuración (todo está en
`vercel.json`). Para probar la build en local:

```bash
cd visualizer && npm ci && npm run build && cd ..
# la landing es index.html; el visualizador queda en visualizer/dist
```

---

## 6. Notas de implementación

- **Contrato `log.json`**: `estado_inicial`, `snapshots` (uno por día), `eventos`
  (cada uno con `id` contiguo, `dia`, `hora`, `tipo` y datos) y `config`. Cada turno
  cierra con un evento `tick` que fotografía indicadores y posiciones, para que el
  reducer del visualizador derive el estado sin re-implementar la física del motor.
- **Robustez sin LLM en vivo**: todo el parseo es tolerante y cada decisión tiene un
  fallback seguro; el motor nunca se cuelga aunque el modelo responda mal o falle la red.
- **Visibilidad de fallos**: cada error del LLM se registra en `errores_llm` del log
  sin alterar la conducta del motor.
