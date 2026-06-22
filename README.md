# The Last Million

**Demo:** [the-last-million.vercel.app](https://the-last-million.vercel.app) · **Visualizador:** [/app](https://the-last-million.vercel.app/app/)

Cuatro agentes LLM conviven 30 días con una meta colectiva —reunir $1.000.000 en un pozo común— y objetivos privados en conflicto. Nadie programa su conducta: **el código orquesta, el LLM decide.**

Inspirado en [Generative Agents (Park et al., 2023)](https://arxiv.org/abs/2304.03442), pero a escala mínima y con incentivos explícitamente desalineados: cooperar es la meta oficial, pero desertar puede ser racionalmente óptimo para algunos.

---

## El experimento

Cuatro agentes en un mundo con cinco lugares (dos salas de edición, un mercado, dormitorios y una plaza). Editar es el único ingreso ($2.000/hora); comer cuesta $2.000. Sin comer se muere; sin dormir se desmaya. Solo hay dos computadores para cuatro agentes, así que la competencia por recursos está garantizada desde el primer turno.

| Agente | Perfil | Objetivo secreto |
|--------|--------|------------------|
| Ana | Cálida, mediadora | Ninguno. Juega limpio. |
| Beto | Calculador, eficiente | Acabar con más dinero personal que nadie. |
| Carla | Irónica, independiente | Que el pozo **no** llegue al millón. |
| Gabriel | Expresivo, todo o nada | Que Ana lo declare su pareja *y* llegar al millón. |

Un **Observador** omnisciente dirige las conversaciones. Si dos agentes nombran en voz alta el objetivo real de un tercero, ese tercero queda descalificado. Conspirar está permitido; delatarse, no.

## Resultados (corrida completa con Qwen 27B)

- El pozo cerró en **$674.500 — 67,5% de la meta**. El objetivo común fracasó.
- **Carla** cumplió su sabotaje y terminó como **la más rica** ($201.500), donando muy poco.
- **Ana** lo dio casi todo y acabó con $4.000.
- **Gabriel** murió de hambre el día 7, demasiado centrado en Ana para alimentarse.
- **0 desmayos** en 30 días: la gestión de sueño y hambre funcionó.

---

## Arquitectura

Dos piezas desacopladas unidas por un único contrato: `log.json`.

```
Motor (Python)  →  log.json (stream de eventos)  →  Visualizador (React)
```

El motor lleva el reloj, la economía, el hambre, el sueño y las muertes. Cuando hay algo que decidir, consulta al LLM y registra todo en `log.json`. El visualizador solo lee ese archivo y lo reproduce turno a turno: no sabe nada de IA.

---

## Correrlo

**Requisitos:** Python 3.10+. El modo offline no necesita ninguna dependencia ni API key.

```bash
git clone https://github.com/dannielwhatever/the-last-million
cd the-last-million
pip install -r requirements.txt
```

```bash
# Offline, determinista (sin ninguna API)
python -m engine.run

# Con Claude
python -m engine.run --llm anthropic --modelo claude-opus-4-8

# Con Ollama (local o remoto)
python -m engine.run --llm ollama --modelo qwen2.5:7b-instruct
```

Opciones útiles: `--dias N` para corridas parciales, `--seed N` para reproducibilidad, `TLM_VERBOSE=1` para ver el avance hora a hora.

El motor escribe `log.json` en la raíz y una copia en `visualizer/public/log.json`.

### Ollama en RunPod

La corrida principal usó Qwen 27B en RunPod. Dos detalles no obvios:

- Los modelos *thinking* (Qwen3) deben usarse por la API nativa de Ollama (`/api/chat` con `think:false`); el endpoint compatible con OpenAI deja `content` vacío con razonamiento activo.
- La carga en frío de un 27B supera el timeout del proxy de RunPod. El cliente hace `prewarm()` antes de arrancar la simulación. Todo esto ya está resuelto en el código.

```bash
# .env
OLLAMA_BASE_URL=https://<POD>-11434.proxy.runpod.net

python -m engine.run --llm ollama --modelo "<modelo-qwen>" --dias 30
```

### Visualizador en local

```bash
cd visualizer
npm install
npm run dev      # → http://localhost:5173
```

Para ver otra partida, copia un archivo de `samples/` a `visualizer/public/log.json`.

---

## Deploy (Vercel)

Importa el repo en Vercel. La configuración en `vercel.json` hace todo:

- Copia `samples/log_qwen_30d.json` como partida de demo.
- Compila el proyecto Vite (landing + visualizador React en MPA).
- Sirve la landing en `/` y el visualizador en `/app/`.

---

## Limitaciones

- Una sola corrida con un solo modelo: lo observado es anecdótico, no generalizable.
- El resultado depende mucho del modelo. Modelos pequeños mueren de hambre pronto.
- La calibración económica es delicada: con dos agentes jugando activa o pasivamente contra el pozo, llegar al millón es difícil por diseño.
- El Observador es también un LLM: sus veredictos no son verdad objetiva.
