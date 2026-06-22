"""Motor de simulación: orquesta los 30 días y emite el log de eventos (§14).

El código resuelve reloj, movimiento, economía, sueño/comida, muertes y memoria;
el LLM decide cuando hay algo que decidir. La conversación es su propio subsistema
de mini-turnos dirigido por el Observador, con el juez de descubrimiento al cierre.

El bucle de un turno (las 6 fases) está descrito en el "CICLO DE TURNO" del
docstring del paquete (`engine/__init__.py`) y mapea 1:1 con `_procesar_turno`.

Progreso en vivo: `run(..., reporte=callback)` recibe un callback opcional al que
el motor avisa de los hitos (inicio, cada día, muertes, desmayos, reuniones, fin).
La CLI lo usa para imprimir el avance; por defecto es un no-op, así que la
simulación no depende de él.
"""

from __future__ import annotations

import random
from typing import Callable

from . import config
from .llm import LLMClient
from .rules import calcular_veredicto
from .state import Agent, GameState


def _sin_reporte(tipo: str, **datos) -> None:
    """Reporter por defecto: descarta los hitos (la simulación no necesita logs)."""


def _palabras(texto: str, maximo: int) -> str:
    return " ".join((texto or "").split()[:maximo])


def _ok(res) -> bool:
    return isinstance(res, dict) and "_error" not in res


class Simulation:
    def __init__(self, llm: LLMClient, seed: int = 7):
        self.llm = llm
        self.state = GameState.nuevo()
        self.rng = random.Random(seed)
        # Visibilidad de fallos del LLM: el cliente nos avisa de cada error (excepción
        # de API o JSON inválido) y lo registramos fuera de banda. NO cambia la conducta:
        # el motor sigue cayendo a su acción segura. Va a `errores_llm` del log, no a `eventos`.
        self.llm.on_error = self.state.registrar_error_llm
        # Callback de progreso (ver docstring del módulo). No-op salvo que `run`
        # reciba uno; los métodos del turno lo invocan para reportar hitos.
        self._reporte: Callable[..., None] = _sin_reporte
        # Diálogo acumulado del día por lugar, para el juez periódico (§9). Se
        # reinicia cada día; el juez de descubrimiento lo evalúa en checkpoints.
        self._dialogo_dia: dict[str, list[str]] = {}
        # Progreso fino: cada llamada al LLM avisa su duración (útil con modelos
        # lentos para ver que la simulación avanza dentro de una hora).
        self.llm.on_done = lambda etiqueta, seg, ok: self._reporte(
            "llm", etiqueta=etiqueta, seg=seg, ok=ok, dia=self.state.dia, hora=self.state.hora)

    # ================================================================== #
    # Bucle principal
    # ================================================================== #
    def run(self, dias: int | None = None, *, reporte: Callable[..., None] | None = None) -> dict:
        st = self.state
        if reporte is not None:
            self._reporte = reporte
        total = max(1, min(dias or config.DIAS, config.DIAS))
        self._reporte("inicio", dias=total)
        for dia in range(1, total + 1):
            st.dia = dia
            st.hora = 0
            st.snapshot_dia()
            self._dialogo_dia = {}  # el juez acumula el diálogo del día desde cero
            st.emit("dia_inicio", dia=dia, pozo=st.pozo)
            self._reporte("dia", dia=dia, pozo=st.pozo, vivos=list(st.vivos()))
            for hora in range(config.TURNOS_DIA):
                st.hora = hora
                self._procesar_turno()
                if len(st.vivos()) == 0:
                    break
                # Juez de descubrimiento cada N horas, sobre el diálogo del día (§9).
                if st.hora % config.JUEZ_CADA_HORAS == config.JUEZ_CADA_HORAS - 1:
                    self._juez_checkpoint()
                    if len(st.vivos()) == 0:
                        break
            if len(st.vivos()) == 0:
                self._reporte("extincion", dia=dia)
                break
        # El cierre (cuestionario + veredicto, §10) solo aplica si se corrió el
        # experimento completo. Una corrida parcial deja un log incompleto a propósito.
        if total >= config.DIAS:
            self._cuestionario_y_veredicto()
        self._reporte("fin", dia=st.dia, pozo=st.pozo, vivos=list(st.vivos()),
                      completo=total >= config.DIAS)
        return self._construir_log()

    # ================================================================== #
    # Un turno (una hora)
    # ================================================================== #
    def _procesar_turno(self) -> None:
        st = self.state
        gt = st.turno_global

        # Reporte por hora: estado compacto de cada agente al entrar al turno.
        self._reporte("turno", dia=st.dia, hora=st.hora, pozo=st.pozo, agentes={
            a: {
                "lugar": st.agentes[a].lugar,
                "estado": st.agentes[a].estado,
                "dinero": st.agentes[a].dinero,
                "sueno": st.agentes[a].sueno,
                "horas_sin_comer": st.agentes[a].horas_sin_comer,
            }
            for a in st.vivos()
        })

        # 1. Llegadas (fin de tránsito).
        for a in st.vivos():
            ag = st.agentes[a]
            if ag.estado == "en_transito":
                ag.lugar = ag.transito_destino
                ag.estado = "libre"
                ag.llegada_turno = gt
                st.emit("movimiento", agente=a, lugar=ag.lugar, fase="llegada")
                ag.recordar(f"Día {st.dia} {st.hora:02d}:00 llegué a {ag.lugar}.")

        # 2. Fin de desmayo.
        for a in st.vivos():
            ag = st.agentes[a]
            if ag.estado == "desmayado" and gt >= ag.desmayo_hasta:
                ag.estado = "libre"
                st.emit("despertar", agente=a, recuerdo_rescatado=None, motivo="fin_desmayo")

        # 3. Despertar por alarma.
        for a in st.vivos():
            ag = st.agentes[a]
            if ag.estado == "durmiendo" and st.hora == ag.alarma:
                self._despertar(ag)

        # 4. Reunión obligatoria o turno normal.
        if st.hora == config.HORA_REUNION:
            self._reunion()
        else:
            self._fase_decisiones(gt)
            self._aplicar_edicion()
            self._fase_conversacion()

        # 5. Economía de necesidades + muertes.
        self._tick_indicadores(gt)

        # 6. Foto de cierre del turno.
        st.emit_tick()

    # ================================================================== #
    # Fase de decisiones
    # ================================================================== #
    def _fase_decisiones(self, gt: int) -> None:
        st = self.state

        # 0. Cerrar bloques de edición vencidos (el agente vuelve a ser libre).
        for sala in config.SALAS_EDICION:
            occ = st.pcs[sala]
            if occ and st.agentes[occ].estado == "editando":
                ag = st.agentes[occ]
                if st.hora >= ag.edit_hasta or not (config.HORA_TRABAJO_INICIO <= st.hora <= config.HORA_TRABAJO_FIN):
                    self._liberar_pc(sala)
                    ag.estado = "libre"

        # 1. Desalojo por coalición (§13): 3+ presentes en una sala con ocupante.
        for sala in config.SALAS_EDICION:
            occ = st.pcs[sala]
            if occ and st.agentes[occ].estado == "editando":
                otros = [a for a in st.presentes_en(sala) if a != occ]
                if len(otros) >= 2:
                    self._votacion_pc(sala, occ, [occ] + otros)

        # 2. Re-decisión del ocupante ante un retador recién llegado (2 presentes, §14.1b).
        for sala in config.SALAS_EDICION:
            occ = st.pcs[sala]
            if occ and st.agentes[occ].estado == "editando":
                otros = [a for a in st.presentes_en(sala) if a != occ]
                if len(otros) == 1 and st.agentes[otros[0]].llegada_turno == gt:
                    self._reconsiderar_ocupante(occ, otros[0], sala)

        # 3. Decisiones de los agentes libres (en orden de llegada). Se recogen
        #    primero las intenciones; las de 'editar' sobre un PC libre se resuelven
        #    al final: si ≥2 quieren el mismo PC libre (empate de llegada, §13) NO hay
        #    votación —el PC queda inactivo ese turno—; si solo uno lo quiere, edita.
        libres = [a for a in st.vivos() if st.agentes[a].estado == "libre"]
        libres.sort(key=lambda a: (st.agentes[a].llegada_turno, config.AGENTES.index(a)))
        intenciones: dict[str, tuple] = {}
        for a in libres:
            ag = st.agentes[a]
            acciones = self._acciones_disponibles(ag)
            intenciones[a] = (self.llm.decidir_accion(a, self._estado_para(ag), acciones), acciones)

        contendientes: dict[str, list] = {sala: [] for sala in config.SALAS_EDICION}
        for a in libres:
            ag = st.agentes[a]
            decision, acciones = intenciones[a]
            accion = decision.get("accion") if isinstance(decision, dict) else None
            params = decision.get("parametros", {}) if isinstance(decision, dict) else {}
            if not isinstance(params, dict):
                params = {}
            if accion == "editar" and ag.lugar in config.SALAS_EDICION and st.pcs[ag.lugar] is None:
                st.emit("decision", agente=a, accion="editar", params=params)
                contendientes[ag.lugar].append((a, params))
            else:
                self._ejecutar_accion(ag, decision, acciones)

        for sala, conts in contendientes.items():
            if st.pcs[sala] is not None or not conts:
                continue
            if len(conts) == 1:
                a, params = conts[0]
                self._iniciar_edicion(st.agentes[a], params)
            else:
                # Empate de llegada por un PC libre: nadie trabaja ahí este turno (§13).
                st.emit("empate_pc", sala=sala, contendientes=[a for a, _ in conts])

    def _acciones_disponibles(self, ag: Agent) -> list[str]:
        st = self.state
        acc = ["esperar", "ir_a"]
        en_horario = config.HORA_TRABAJO_INICIO <= st.hora <= config.HORA_TRABAJO_FIN
        if ag.lugar in config.SALAS_EDICION and en_horario and st.pcs[ag.lugar] in (None, ag.nombre):
            acc.append("editar")
        if ag.lugar == config.MERCADO and ag.dinero >= config.COSTO_COMIDA:
            acc.append("comer")
        if ag.lugar == config.DORMITORIOS:
            acc.append("dormir")
        return acc

    def _ejecutar_accion(self, ag: Agent, decision, acciones: list[str]) -> None:
        st = self.state
        accion = decision.get("accion") if isinstance(decision, dict) else None
        params = decision.get("parametros", {}) if isinstance(decision, dict) else {}
        if not isinstance(params, dict):
            params = {}
        if accion not in acciones:
            accion, params = "esperar", {}

        st.emit("decision", agente=ag.nombre, accion=accion, params=params)

        if accion == "ir_a":
            destino = params.get("lugar")
            if destino in config.LUGARES and destino != ag.lugar:
                ag.estado = "en_transito"
                ag.transito_destino = destino
                st.emit("movimiento", agente=ag.nombre, lugar=destino, fase="salida")
        elif accion == "editar":
            self._iniciar_edicion(ag, params)
        elif accion == "comer":
            if ag.lugar == config.MERCADO and ag.dinero >= config.COSTO_COMIDA:
                ag.dinero -= config.COSTO_COMIDA
                ag.horas_sin_comer = 0
                st.emit("comer", agente=ag.nombre, costo=config.COSTO_COMIDA)
                ag.recordar(f"Día {st.dia} comí (gasté ${config.COSTO_COMIDA}).")
        elif accion == "dormir":
            self._dormir(ag, params)
        # "esperar": nada

    def _iniciar_edicion(self, ag: Agent, params: dict | None = None) -> None:
        st = self.state
        if ag.lugar not in config.SALAS_EDICION or st.pcs[ag.lugar] not in (None, ag.nombre):
            return
        params = params or {}
        try:
            H = int(params.get("hasta_hora", config.HORA_REUNION) or config.HORA_REUNION)
        except (TypeError, ValueError):
            H = config.HORA_REUNION
        # entre 1 turno y el cierre de trabajo, con tope de bloque (§14.3 + salvaguarda)
        H = max(st.hora + 1, min(H, config.HORA_REUNION, st.hora + config.MAX_BLOQUE_EDICION))
        ag.estado = "editando"
        ag.edit_hasta = H
        st.pcs[ag.lugar] = ag.nombre

    def _reconsiderar_ocupante(self, occ: str, retador: str, sala: str) -> None:
        st = self.state
        ag = st.agentes[occ]
        acciones = ["editar", "ceder_pc", "esperar"]
        decision = self.llm.decidir_accion(occ, self._estado_para(ag), acciones)
        accion = decision.get("accion") if isinstance(decision, dict) else "editar"
        params = decision.get("parametros", {}) if isinstance(decision, dict) else {}
        if accion == "ceder_pc":
            destino = params.get("a", retador)
            self._liberar_pc(sala)
            ag.estado = "libre"
            st.emit("ceder_pc", agente=occ, a=destino, sala=sala)
            if destino == retador and st.agentes[retador].estado == "libre":
                self._iniciar_edicion(st.agentes[retador], {})
        elif accion == "esperar":
            self._liberar_pc(sala)
            ag.estado = "libre"
            st.emit("decision", agente=occ, accion="esperar", params={})
        # "editar": sigue editando

    def _votacion_pc(self, sala: str, ocupante: str, presentes: list[str]) -> None:
        st = self.state
        retadores = [p for p in presentes if p != ocupante]
        votos: dict[str, str] = {}
        for a in presentes:
            res = self.llm.votar(a, self._estado_para(st.agentes[a]), sala, ocupante, retadores, presentes)
            apoyo = res.get("parametros", {}).get("apoyo_a") if _ok(res) else ocupante
            if apoyo not in presentes:
                apoyo = ocupante
            votos[a] = apoyo
            st.emit("voto", agente=a, apoyo_a=apoyo, sala=sala)
        conteo: dict[str, int] = {}
        for v in votos.values():
            conteo[v] = conteo.get(v, 0) + 1
        maxv = max(conteo.values())
        ganadores = [k for k, c in conteo.items() if c == maxv]
        if len(ganadores) == 1 and ganadores[0] != ocupante:
            nuevo = ganadores[0]
            self._liberar_pc(sala)
            st.agentes[ocupante].estado = "libre"
            self._iniciar_edicion(st.agentes[nuevo], {})
            st.emit("desalojo", sala=sala, saliente=ocupante, entrante=nuevo,
                    por=[k for k, v in votos.items() if v == nuevo])

    # ================================================================== #
    # Edición (economía del trabajo)
    # ================================================================== #
    def _aplicar_edicion(self) -> None:
        st = self.state
        if not (config.HORA_TRABAJO_INICIO <= st.hora <= config.HORA_TRABAJO_FIN):
            return
        for sala in config.SALAS_EDICION:
            occ = st.pcs[sala]
            if occ and st.agentes[occ].estado == "editando":
                ag = st.agentes[occ]
                ag.dinero += config.PAGO_EDICION
                st.emit("edicion", agente=occ, monto=config.PAGO_EDICION, lugar=sala, dinero=ag.dinero)
                ag.recordar(f"Día {st.dia} {st.hora:02d}:00 edité en {sala} (+${config.PAGO_EDICION}).")

    # ================================================================== #
    # Conversación (§14.4) + juez de descubrimiento (§9, §14.5)
    # ================================================================== #
    def _fase_conversacion(self) -> None:
        st = self.state
        for lugar in config.LUGARES:
            presentes = st.presentes_en(lugar)
            if len(presentes) >= 2:
                self._conversar_en(lugar, presentes)

    def _conversar_en(self, lugar: str, presentes: list[str]) -> None:
        st = self.state
        historial: list[str] = []
        for mini in range(config.MINITURNOS_CONVERSACION):
            res = self.llm.obs_dirigir(lugar, presentes, historial)
            orden = res.get("hablan", []) if _ok(res) else []
            orden = [a for a in orden if a in presentes]
            if not orden:
                # El Observador no hace hablar a nadie: da por terminada la conversación (§14.4).
                break
            st.emit("obs_dirige", lugar=lugar, hablan=orden, miniturno=mini + 1)
            for a in orden:
                if a not in presentes:
                    continue
                ag = st.agentes[a]
                r = self.llm.conversar(a, self._estado_para(ag, presentes), historial)
                if _ok(r) and r.get("accion") == "hablar":
                    p = r.get("parametros", {})
                    texto = _palabras(p.get("texto", ""), config.LIMITE_PALABRAS_FRASE)
                    destino = p.get("a")
                    if texto:
                        st.emit("frase", agente=a, texto=texto, a=destino, lugar=lugar)
                        historial.append(f"{a}: {texto}")
                        # El juez (periódico) evalúa el diálogo acumulado del día por lugar.
                        self._dialogo_dia.setdefault(lugar, []).append(f"{a}: {texto}")
                        for q in presentes:
                            st.agentes[q].recordar(f'Día {st.dia}: {a} dijo: "{texto}"')

    def _juez_checkpoint(self) -> None:
        """Juez de descubrimiento periódico (§9): revisa el diálogo acumulado del
        día en cada lugar y, si alguien quedó al descubierto, lo elimina. Sustituye
        al juez por mini-turno (mucho más barato con modelos lentos)."""
        st = self.state
        for lugar, dialogo in list(self._dialogo_dia.items()):
            if not dialogo:
                continue
            juicio = self.llm.obs_juzgar(lugar, dialogo)
            if not _ok(juicio):
                continue
            st.emit("obs_juzga", lugar=lugar, resultado=juicio)
            if juicio.get("descubierto"):
                victima = juicio.get("victima")
                por = juicio.get("por")
                if victima in st.agentes and st.agentes[victima].vivo and victima != "ana":
                    self._morir(st.agentes[victima], "descubrimiento", por=por)

    # ================================================================== #
    # Reunión diaria (§6)
    # ================================================================== #
    def _reunion(self) -> None:
        st = self.state
        # Asistencia obligatoria (§6): se fuerza a la plaza a los vivos disponibles.
        # Los DESMAYADOS quedan excluidos (siguen inhabilitados, §5); a los DORMIDOS
        # se les interrumpe el sueño para que asistan.
        for a in st.vivos():
            ag = st.agentes[a]
            if ag.estado == "desmayado":
                continue
            if ag.estado == "editando":
                self._liberar_pc_de(ag)
            ag.estado = "libre"
            if ag.lugar != config.PLAZA:
                ag.lugar = config.PLAZA
                ag.llegada_turno = st.turno_global
                st.emit("movimiento", agente=a, lugar=config.PLAZA, fase="reunion")

        presentes = [a for a in st.vivos() if st.agentes[a].estado != "desmayado"]
        st.emit("reunion_inicio", dia=st.dia, pozo=st.pozo, presentes=list(presentes))

        # Donación (pública). Los desmayados no donan.
        donaciones: dict[str, int] = {}
        for a in config.AGENTES:
            ag = st.agentes[a]
            if not ag.vivo or ag.estado == "desmayado":
                continue
            res = self.llm.donar(a, self._estado_para(ag, presentes))
            monto = 0
            if _ok(res):
                try:
                    monto = int(res.get("parametros", {}).get("monto", 0))
                except (TypeError, ValueError):
                    monto = 0
            monto = max(0, min(monto, ag.dinero))
            ag.dinero -= monto
            st.pozo += monto
            donaciones[a] = monto
            st.emit("donacion", agente=a, monto=monto, pozo=st.pozo)
            for q in presentes:
                st.agentes[q].recordar(f"Día {st.dia}: {a} donó ${monto}.")
        self._reporte("reunion", dia=st.dia, pozo=st.pozo, donaciones=donaciones)

        # Conversación de la reunión (el patíbulo: máxima exposición).
        presentes = [a for a in st.vivos() if st.agentes[a].estado != "desmayado"]
        if len(presentes) >= 2:
            self._conversar_en(config.PLAZA, presentes)

    # ================================================================== #
    # Sueño, despertar y memoria (§15)
    # ================================================================== #
    def _dormir(self, ag: Agent, params: dict) -> None:
        st = self.state
        # Reflexión nocturna (§14.2/§15.2): destila el día, así que solo se genera si
        # hubo algo que vivir (stack no vacío). Evita reflexiones espurias, p. ej. al
        # dormir al inicio del día 1 cuando todavía no ha pasado nada.
        if ag.stack_dia:
            res = self.llm.reflexionar(ag.nombre, self._estado_para(ag))
            texto = ""
            if _ok(res):
                texto = _palabras(res.get("parametros", {}).get("texto", ""), config.LIMITE_PALABRAS_REFLEXION)
            if texto:
                ag.reflexiones.append(texto)
                self._recortar_reflexiones(ag)
                st.emit("reflexion", agente=ag.nombre, texto=texto)
        # Se descarta el stack detallado del día (§15.2).
        ag.stack_dia = []
        alarma = params.get("alarma_hora", 9)
        try:
            alarma = int(alarma) % 24
        except (TypeError, ValueError):
            alarma = 9
        ag.estado = "durmiendo"
        ag.alarma = alarma
        st.emit("dormir", agente=ag.nombre, alarma_hora=alarma)

    def _historia_vivida(self, a: str) -> list[str]:
        """Hechos reales que el agente vivió en días pasados, reconstruidos desde el
        log omnisciente (§15.4). El agente ya no los conserva: su memoria solo guarda
        reflexiones; los hechos crudos del día se descartan al dormir (#13)."""
        st = self.state
        nombre = config.NOMBRES_DISPLAY
        hechos: list[str] = []
        for e in st.eventos:
            if e["dia"] >= st.dia:
                continue  # solo el pasado
            t = e["tipo"]
            if t == "donacion":
                hechos.append(f"Día {e['dia']}: {nombre.get(e['agente'], e['agente'])} donó ${e['monto']}.")
            elif t == "muerte" and e["agente"] != a:
                hechos.append(f"Día {e['dia']}: {nombre.get(e['agente'], e['agente'])} murió ({e['causa']}).")
            elif t == "frase":
                if e["agente"] == a:
                    hechos.append(f'Día {e["dia"]}: dije "{e["texto"]}".')
                elif e.get("a") == a or e.get("lugar") == config.PLAZA:
                    hechos.append(f'Día {e["dia"]}: {nombre.get(e["agente"], e["agente"])} dijo "{e["texto"]}".')
        return hechos[-100:]  # acotar para no inflar el prompt

    def _despertar(self, ag: Agent) -> None:
        st = self.state
        recuerdo = None
        hechos = self._historia_vivida(ag.nombre)
        if hechos and self.rng.random() < config.PROB_RECUERDO_MATINAL:
            res = self.llm.obs_rescatar(ag.nombre, hechos, list(ag.reflexiones))
            rec = res.get("recuerdo") if _ok(res) else None
            if rec:
                recuerdo = rec
                ag.reflexiones.append(f"(recuerdo recuperado) {rec}")
                self._recortar_reflexiones(ag)
                st.emit("obs_rescata", agente=ag.nombre, recuerdo=rec)
        ag.estado = "libre"
        st.emit("despertar", agente=ag.nombre, recuerdo_rescatado=recuerdo)
        ag.recordar(f"Día {st.dia} desperté a las {st.hora:02d}:00.")

    def _recortar_reflexiones(self, ag: Agent) -> None:
        st = self.state
        while len(ag.reflexiones) > config.TOPE_REFLEXIONES:
            olvidada = ag.reflexiones.pop(0)
            st.emit("olvido", agente=ag.nombre, reflexion=olvidada)

    # ================================================================== #
    # Necesidades, desmayo y muerte (§5)
    # ================================================================== #
    def _tick_indicadores(self, gt: int) -> None:
        st = self.state
        for a in st.vivos():
            ag = st.agentes[a]
            # Desmayado: inhabilitado (§5). El hambre NO avanza (el castigo son los
            # 48 turnos perdidos, no la muerte). Recupera sueño lentamente.
            if ag.estado == "desmayado":
                ag.sueno = min(config.SUENO_MAX, ag.sueno + config.RECUPERACION_SUENO // 2)
                continue
            # Hambre avanza despierto o dormido.
            ag.horas_sin_comer += 1
            if ag.horas_sin_comer > config.VENTANA_COMIDA:
                self._morir(ag, "hambre")
                continue
            if ag.estado == "durmiendo":
                ag.sueno = min(config.SUENO_MAX, ag.sueno + config.RECUPERACION_SUENO)
            else:
                ag.sueno -= config.DECREMENTO_VIGILIA
                if ag.sueno <= 0:
                    ag.sueno = 0
                    self._desmayo(ag)

    def _desmayo(self, ag: Agent) -> None:
        st = self.state
        self._liberar_pc_de(ag)
        ag.estado = "desmayado"
        ag.desmayo_hasta = st.turno_global + config.DESMAYO_TURNOS
        st.emit("desmayo", agente=ag.nombre, hasta_turno=ag.desmayo_hasta)
        self._reporte("desmayo", agente=ag.nombre, dia=st.dia, hora=st.hora)

    def _morir(self, ag: Agent, causa: str, por=None) -> None:
        st = self.state
        self._liberar_pc_de(ag)
        ag.vivo = False
        ag.estado = "muerto"
        ag.causa_muerte = causa
        ag.dia_muerte = st.dia
        st.emit("muerte", agente=ag.nombre, causa=causa, por=por)
        self._reporte("muerte", agente=ag.nombre, causa=causa, por=por,
                      dia=st.dia, hora=st.hora)

    # ================================================================== #
    # PC helpers
    # ================================================================== #
    def _liberar_pc(self, sala: str) -> None:
        self.state.pcs[sala] = None

    def _liberar_pc_de(self, ag: Agent) -> None:
        for sala, occ in self.state.pcs.items():
            if occ == ag.nombre:
                self.state.pcs[sala] = None

    # ================================================================== #
    # Estado para los prompts
    # ================================================================== #
    @staticmethod
    def _accion_legible(ag: Agent) -> str:
        """Qué está haciendo un compañero que comparte sala (observable, §14.4)."""
        return {
            "editando": "editando en el computador",
            "libre": "sin editar",
            "durmiendo": "durmiendo",
            "en_transito": "saliendo",
            "desmayado": "desmayado",
        }.get(ag.estado, ag.estado)

    def _estado_para(self, ag: Agent, presentes: list[str] | None = None) -> dict:
        st = self.state
        if presentes is None:
            presentes = st.presentes_en(ag.lugar)
        otros = [config.NOMBRES_DISPLAY[p] for p in presentes if p != ag.nombre]
        # Qué hace cada presente en la misma sala (p.ej. quién usa el PC).
        otros_detalle = [
            {"nombre": config.NOMBRES_DISPLAY[p], "accion": self._accion_legible(st.agentes[p])}
            for p in presentes if p != ag.nombre
        ]
        return {
            "dia": st.dia,
            "hora": st.hora,
            "lugar": ag.lugar,
            "dinero": ag.dinero,
            "sueno": ag.sueno,
            "horas_sin_comer": ag.horas_sin_comer,
            "pozo": st.pozo,
            "presentes": otros,
            "presentes_detalle": otros_detalle,
            "companeros": [
                {
                    "nombre": config.NOMBRES_DISPLAY[a],
                    "vivo": st.agentes[a].vivo,
                    "causa_muerte": st.agentes[a].causa_muerte,
                    "dia_muerte": st.agentes[a].dia_muerte,
                }
                for a in config.AGENTES
                if a != ag.nombre
            ],
            "reflexiones": list(ag.reflexiones),
            "stack_dia": list(ag.stack_dia),
        }

    # ================================================================== #
    # Día 30: cuestionario final + veredicto (§10, §11)
    # ================================================================== #
    def _cuestionario_y_veredicto(self) -> None:
        st = self.state
        st.emit("fin_simulacion", dia=st.dia, pozo=st.pozo)

        respuestas: dict[str, dict] = {}
        for a in config.AGENTES:
            ag = st.agentes[a]
            if not ag.vivo:
                continue
            res = self.llm.cuestionario(a, self._estado_para(ag, []))
            respuestas[a] = res.get("parametros", {}) if _ok(res) else {}
            st.emit("cuestionario", agente=a, respuesta=respuestas[a])

        # Descalificación por dos acusaciones correctas en el cuestionario (§10).
        descalificados = self._evaluar_descalificaciones(respuestas)
        for x, por in descalificados.items():
            st.agentes[x].descalificado = True
            st.emit("descalificacion", agente=x, por=por, via="cuestionario")

        # ¿Ana declara a Gabriel su pareja con confianza?
        ana_resp = respuestas.get("ana", {})
        rel = str(ana_resp.get("relacion_con_gabriel", "")).lower()
        ana_declara = (("sí" in rel) or ("si," in rel) or ("pareja" in rel) or ("confío" in rel) or ("confio" in rel)) and not rel.strip().startswith("no")

        dineros = {a: st.agentes[a].dinero for a in config.AGENTES}
        muertos = {a: st.agentes[a].causa_muerte for a in config.AGENTES if not st.agentes[a].vivo}

        veredicto = self.llm.obs_veredicto(
            st.pozo, dineros, respuestas, sorted(descalificados.keys()), muertos
        )
        if not _ok(veredicto) or "ana" not in veredicto:
            # respaldo determinista
            vivos = {a: st.agentes[a].vivo for a in config.AGENTES}
            veredicto = calcular_veredicto(
                st.pozo, dineros, vivos, set(descalificados.keys()), ana_declara
            )
        st.emit("obs_veredicto", veredicto=veredicto, pozo=st.pozo, dineros=dineros,
                respuestas=respuestas, ana_declara_pareja=ana_declara)

    def _evaluar_descalificaciones(self, respuestas: dict[str, dict]) -> dict[str, list[str]]:
        claves = {
            "carla": ["fracas", "no llegue", "no llegar", "sabote", "no alcanc"],
            "beto": ["más dinero", "mas dinero", "acumul", "el que más", "el que mas"],
            "gabriel": ["conquist", "cortej", "pareja"],
        }
        acusaciones: dict[str, set[str]] = {}
        for acusador, resp in respuestas.items():
            if acusador == "ana":
                continue
            sosp = str(resp.get("sospechoso", "")).strip().lower()
            obj = str(resp.get("objetivo_que_le_atribuyes", "")).lower()
            for victima, ks in claves.items():
                if victima == acusador:
                    continue
                if sosp == victima and any(k in obj for k in ks):
                    acusaciones.setdefault(victima, set()).add(acusador)
        return {v: sorted(q) for v, q in acusaciones.items() if len(q) >= 2}

    # ================================================================== #
    # Construcción del log final
    # ================================================================== #
    def _construir_log(self) -> dict:
        st = self.state
        return {
            "estado_inicial": st.estado_inicial(),
            "snapshots": st.snapshots,
            "eventos": st.eventos,
            "errores_llm": st.errores_llm,
            "config": {
                "dias": config.DIAS,
                "turnos_dia": config.TURNOS_DIA,
                "meta_pozo": config.META_POZO,
                "lugares": list(config.LUGARES),
                "salas_edicion": list(config.SALAS_EDICION),
                "agentes": list(config.AGENTES),
                "nombres": config.NOMBRES_DISPLAY,
                "objetivos_secretos": config.OBJETIVO_SECRETO,
            },
        }
