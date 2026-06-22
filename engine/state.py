"""Estado del mundo y log de eventos (§17).

El log de eventos es la única fuente de verdad; el estado se deriva aplicándolos.
El motor mantiene un estado mutable mientras simula y, en paralelo, emite los
eventos que el visualizador necesita para reconstruir todo turno a turno.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import config


@dataclass
class Agent:
    nombre: str
    dinero: int = config.DINERO_INICIAL
    sueno: int = config.SUENO_INICIAL
    horas_sin_comer: int = 0
    lugar: str = config.LUGAR_INICIAL
    estado: str = "libre"  # libre|editando|durmiendo|en_transito|desmayado|muerto
    vivo: bool = True
    # estado de acciones en curso
    edit_hasta: int = 0          # hora exclusiva hasta la que edita
    alarma: int = 0              # hora a la que despertar
    transito_destino: str = ""   # destino mientras está en tránsito
    desmayo_hasta: int = 0       # turno global en que termina el desmayo
    llegada_turno: int = 0       # turno global en que llegó a su lugar actual
    # memoria (§15)
    reflexiones: list[str] = field(default_factory=list)
    stack_dia: list[str] = field(default_factory=list)
    # final
    descalificado: bool = False
    causa_muerte: str | None = None
    dia_muerte: int | None = None

    def comida_pct(self) -> float:
        return max(0.0, (config.VENTANA_COMIDA - self.horas_sin_comer) / config.VENTANA_COMIDA)

    def recordar(self, hecho: str) -> None:
        """Apila un recuerdo crudo en el stack del día (se descarta al dormir, §15).
        Para conservarlo el agente debe re-anclarlo en su reflexión nocturna."""
        self.stack_dia.append(hecho)


@dataclass
class GameState:
    agentes: dict[str, Agent]
    dia: int = 1
    hora: int = 0
    pozo: int = 0
    pcs: dict[str, str | None] = field(default_factory=lambda: {s: None for s in config.SALAS_EDICION})
    eventos: list[dict] = field(default_factory=list)
    snapshots: dict[str, dict] = field(default_factory=dict)
    errores_llm: list[dict] = field(default_factory=list)
    _next_id: int = 1

    # --- construcción ---
    @classmethod
    def nuevo(cls) -> "GameState":
        agentes = {a: Agent(nombre=a) for a in config.AGENTES}
        return cls(agentes=agentes)

    # --- utilidades de tiempo ---
    @property
    def turno_global(self) -> int:
        return (self.dia - 1) * config.TURNOS_DIA + self.hora

    # --- eventos ---
    def emit(self, tipo: str, **datos) -> dict:
        ev = {"id": self._next_id, "dia": self.dia, "hora": self.hora, "tipo": tipo, **datos}
        self._next_id += 1
        self.eventos.append(ev)
        return ev

    # --- diagnóstico de fallos del LLM (fuera de banda) ---
    def registrar_error_llm(self, llamada: str, error: str) -> None:
        """Registra un fallo de una llamada al LLM (excepción de API o JSON inválido)
        para tener visibilidad fuera de banda. NO afecta la simulación: el motor
        sigue cayendo a su acción segura. No va en `eventos` porque no es parte del
        mundo que el visualizador reproduce, solo diagnóstico para nosotros."""
        self.errores_llm.append({
            "dia": self.dia,
            "hora": self.hora,
            "turno_global": self.turno_global,
            "llamada": llamada,
            "error": error,
        })

    # --- presencia ---
    def vivos(self) -> list[str]:
        return [a for a, ag in self.agentes.items() if ag.vivo]

    def presentes_en(self, lugar: str, *, conversables: bool = True) -> list[str]:
        """Agentes vivos físicamente en un lugar. Si `conversables`, excluye a
        quienes duermen, están desmayados o en tránsito (no pueden oír/hablar)."""
        out = []
        for a in config.AGENTES:
            ag = self.agentes[a]
            if not ag.vivo or ag.lugar != lugar:
                continue
            if conversables and ag.estado in ("durmiendo", "desmayado", "en_transito"):
                continue
            out.append(a)
        return out

    # --- snapshot por día (punto de control, §17.1) ---
    def snapshot_dia(self) -> None:
        self.snapshots[f"dia_{self.dia}"] = {
            "dia": self.dia,
            "pozo": self.pozo,
            "evento_id": self._next_id,  # primer id de eventos de este día
            "agentes": {
                a: {
                    "dinero": ag.dinero,
                    "sueno": ag.sueno,
                    "horas_sin_comer": ag.horas_sin_comer,
                    "comida_pct": round(ag.comida_pct(), 3),
                    "lugar": ag.lugar,
                    "estado": ag.estado,
                    "vivo": ag.vivo,
                    "descalificado": ag.descalificado,
                    "reflexiones": list(ag.reflexiones),
                }
                for a, ag in self.agentes.items()
            },
        }

    # --- tick: foto de indicadores al cierre de cada turno ---
    def emit_tick(self) -> None:
        self.emit(
            "tick",
            pozo=self.pozo,
            agentes={
                a: {
                    "dinero": ag.dinero,
                    "sueno": ag.sueno,
                    "comida_pct": round(ag.comida_pct(), 3),
                    "horas_sin_comer": ag.horas_sin_comer,
                    "lugar": ag.lugar,
                    "estado": ag.estado,
                    "vivo": ag.vivo,
                    "descalificado": ag.descalificado,
                }
                for a, ag in self.agentes.items()
            },
        )

    # --- estado inicial para el log (§17.2) ---
    def estado_inicial(self) -> dict:
        return {
            "pozo": 0,
            "meta": config.META_POZO,
            "dias": config.DIAS,
            "lugares": list(config.LUGARES),
            "agentes": {
                a: {
                    "nombre": config.NOMBRES_DISPLAY[a],
                    "dinero": config.DINERO_INICIAL,
                    "sueno": config.SUENO_INICIAL,
                    "comida_pct": 1.0,
                    "lugar": config.LUGAR_INICIAL,
                    "vivo": True,
                    "objetivo_secreto": config.OBJETIVO_SECRETO[a],
                }
                for a in config.AGENTES
            },
        }
