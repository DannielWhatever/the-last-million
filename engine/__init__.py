"""Motor de simulación de The Last Million — un reality show de agentes autónomos.

Cuatro agentes (Ana, Beto, Carla, Gabriel) conviven 30 días intentando juntar
$1.000.000 en un pozo común; cada uno tiene además un objetivo secreto. El motor
corre los 30 días por adelantado y produce un `log.json` (modelo Redux de
eventos) que el visualizador React reproduce turno a turno. Diseño completo en
`docs/biblia_experimento.md` (las referencias §N de los docstrings apuntan ahí).


PRINCIPIO RECTOR
----------------
**El código orquesta; el LLM decide.** El motor resuelve toda la "física" del
mundo (reloj, movimiento, economía, sueño/comida, muertes, memoria) y solo
consulta al LLM cuando un agente tiene algo que *decidir* o *decir*. Así la
lógica es testeable y determinista, y el modelo es intercambiable.


FLUJO DE DATOS
--------------
    run.py  ──crea──>  Simulation(LLMClient)
                            │  corre 30 días
                            ▼
                       log.json  (estado_inicial + snapshots + eventos + config)
                            │
                            ▼
                  visualizador React (solo lee el log)

El `log.json` es el ÚNICO contrato con el visualizador: el motor no sabe nada de
la UI y la UI no sabe nada del LLM.


MAPA DE MÓDULOS  (por dónde empezar a leer, en orden)
-----------------------------------------------------
    config.py      Todos los parámetros calibrables (economía, reloj, sueño,
                   memoria, umbrales de hambre, modelo). Empieza aquí: define el
                   vocabulario y las constantes que usan los demás módulos.
    state.py       El estado del mundo (`GameState`, `Agent`) y la emisión de
                   eventos/snapshots que componen el log. El estado es mutable
                   mientras se simula; el log es la fuente de verdad reproducible.
    simulation.py  EL CORAZÓN. El bucle de 30 días y la orquestación de cada
                   turno (ver "CICLO DE TURNO" abajo). Si vas a entender una sola
                   cosa, que sea `Simulation._procesar_turno`.
    prompts.py     System prompts y el prompt de cada tipo de llamada (§16). Lo
                   que el agente "ve": su estado, el roster de vivos/muertos y las
                   alertas (p. ej. la de hambre).
    llm.py         Interfaz `LLMClient` (un método por tipo de decisión) y los
                   clientes reales (Claude, compatible-OpenAI). Transporte e
                   intercambiabilidad; el armado de prompts vive en `prompts.py`.
    mock_llm.py    `MockClient`: heurísticas deterministas para correr offline,
                   sin red ni API key. Útil para desarrollo y para tests.
    rules.py       Condiciones de victoria deterministas (§11). Respaldo si el
                   Observador-LLM falla, y juez del cliente mock.
    run.py         Punto de entrada CLI (`python -m engine.run`). Construye el
                   cliente, corre la simulación y escribe el log.


CICLO DE TURNO  (Simulation._procesar_turno — 1 turno = 1 hora)
---------------------------------------------------------------
    1. Llegadas        — quienes estaban en tránsito llegan a su destino.
    2. Fin de desmayo  — quien cumplió su castigo de 2 días vuelve a estar libre.
    3. Despertar       — quien tenía alarma a esta hora despierta (y puede
                         recuperar un recuerdo vía el Observador).
    4. Acción del turno:
         · si son las 23:00 → REUNIÓN (donación pública + conversación), o
         · turno normal → decisiones de los agentes → se aplica la edición →
           conversación dirigida por el Observador (con juez de descubrimiento).
    5. Necesidades     — avanza el hambre y el sueño; aquí ocurren desmayos y
                         muertes (tick de indicadores).
    6. Cierre          — se emite un evento `tick`: foto de indicadores y
                         posiciones de todos, para que el visualizador derive el
                         estado sin reimplementar la física.


GLOSARIO  (la jerga del dominio, en español)
--------------------------------------------
    pozo          Bote común; la meta pública es llevarlo a $1.000.000.
    editar        Única forma de ganar dinero: editar videos en un PC de una sala.
    salas (a/b)   Los 2 lugares con computador (1 cada uno) donde se edita.
    mercado       Donde se compra la comida ($2.000/ración).
    dormitorios   Donde se duerme.
    plaza         Punto de encuentro; ahí ocurre la reunión diaria.
    comida/hambre Hay que comer antes de 48h sin comer o se muere de hambre.
    sueño/desmayo Si el sueño llega a 0, el agente se desmaya 2 días (inhabilitado).
    reunión       23:00 de cada día: cada quien dona (en público) lo que quiera.
    donación      Aporte (público) del bolsillo de un agente al pozo.
    Observador    LLM omnisciente que dirige las conversaciones, juzga los
                  descubrimientos y rescata recuerdos. No actúa en el mundo.
    descubrimiento Si dos agentes nombran el objetivo secreto real de un tercero,
                  ese tercero queda fuera (descalificado/"muere").
    reflexión     Resumen nocturno que el agente conserva como memoria de largo
                  plazo (lo crudo del día se olvida al dormir).
    tick          Foto de indicadores al cierre de cada turno (evento del log).
    snapshot      Punto de control con el estado al inicio de un día (para saltar
                  rápido en el visualizador).
    evento        Unidad atómica del log (id, dia, hora, tipo, datos).
"""
