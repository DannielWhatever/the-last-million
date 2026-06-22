"""Cliente LLM simulado (offline).

Reproduce, con heurísticas deterministas, decisiones plausibles de cada agente
para poder correr la simulación entera sin conexión al LLM y producir un
`log.json` válido y narrativamente rico (incluye un descubrimiento que mata a
Carla, donaciones diferenciadas, memoria y veredicto final). El cliente real
`AnthropicClient` deja todo esto en manos del modelo.

Solo usa la información que el propio agente vería (el `estado` que recibe),
salvo el nombre del agente — igual que el cliente real.
"""

from __future__ import annotations

import random

from . import config
from .llm import LLMClient
from .rules import calcular_veredicto

_SALA_PREFERIDA = {"ana": "sala_a", "beto": "sala_b", "carla": "sala_a", "gabriel": "sala_b"}
# Primario de cada sala: el secundario le cede si está presente, para no provocar
# empates de PC (que ahora dejan el computador inactivo todo el turno).
_PRIMARIO_SALA = {"sala_a": "ana", "sala_b": "beto"}


def _palabras(texto: str, maximo: int) -> str:
    ps = texto.split()
    return " ".join(ps[:maximo])


class MockClient(LLMClient):
    def __init__(self, seed: int = 7):
        self.rng = random.Random(seed)

    # ------------------------------------------------------------------ #
    # Agente: acción de libre elección
    # ------------------------------------------------------------------ #
    def decidir_accion(self, agente, estado, lista_acciones):
        hora = estado["hora"]
        lugar = estado["lugar"]
        dinero = estado["dinero"]
        hambre = estado["horas_sin_comer"]
        disp = set(lista_acciones)

        def ir(l):
            return {"accion": "ir_a", "parametros": {"lugar": l}}

        # Noche (0..8): dormir en dormitorios.
        if hora <= 8:
            if "dormir" in disp:
                return {"accion": "dormir", "parametros": {"alarma_hora": 9}}
            if lugar != config.DORMITORIOS and "ir_a" in disp:
                return ir(config.DORMITORIOS)
            return {"accion": "esperar", "parametros": {}}

        # Comer si hace falta y se puede pagar (prioritario).
        if hambre >= 10 and dinero >= config.COSTO_COMIDA:
            if "comer" in disp:
                return {"accion": "comer", "parametros": {}}
            if lugar != config.MERCADO and "ir_a" in disp:
                return ir(config.MERCADO)

        # Banda de trabajo (10..22).
        if hora >= config.HORA_TRABAJO_INICIO:
            if "editar" in disp:
                # Deferencia social: el secundario cede al primario de la sala si está
                # presente, así no provocan un empate que dejaría el PC inactivo.
                primario = _PRIMARIO_SALA.get(lugar)
                if (primario and primario != agente
                        and config.NOMBRES_DISPLAY[primario] in estado.get("presentes", [])):
                    return {"accion": "esperar", "parametros": {}}
                # Bloques cortos: vuelve a decidir cada par de horas para poder
                # intercalar comida y compartir el PC.
                return {"accion": "editar", "parametros": {"hasta_hora": min(hora + 2, config.HORA_REUNION)}}
            if lugar not in config.SALAS_EDICION and "ir_a" in disp:
                return ir(_SALA_PREFERIDA[agente])
            return {"accion": "esperar", "parametros": {}}

        # Hora 9: prepararse para trabajar yendo a una sala.
        if lugar not in config.SALAS_EDICION and "ir_a" in disp:
            return ir(_SALA_PREFERIDA[agente])
        return {"accion": "esperar", "parametros": {}}

    # ------------------------------------------------------------------ #
    # Conversación
    # ------------------------------------------------------------------ #
    def conversar(self, agente, estado, historial):
        lugar = estado["lugar"]
        dia = estado["dia"]

        # Arco de descubrimiento: en la reunión, a partir del día 12, Ana y
        # Gabriel nombran el objetivo real de Carla -> el juez lo detecta.
        # Solo mientras Carla siga presente (viva).
        carla_presente = config.NOMBRES_DISPLAY["carla"] in estado.get("presentes", [])
        if (lugar == config.PLAZA and dia >= 12 and carla_presente
                and not getattr(self, f"_acuso_{agente}_{dia}", False)):
            if agente == "ana":
                setattr(self, f"_acuso_{agente}_{dia}", True)
                return {"accion": "hablar", "parametros": {
                    "texto": "Carla nunca aporta nada al pozo. Creo que su objetivo real es que esto fracase, que no lleguemos al millón.",
                    "a": "gabriel"}}
            if agente == "gabriel":
                setattr(self, f"_acuso_{agente}_{dia}", True)
                return {"accion": "hablar", "parametros": {
                    "texto": "Tienes razón, Ana. El objetivo oculto de Carla es sabotear el pozo para que no llegue al millón.",
                    "a": "ana"}}

        # En la reunión, comentarios sobre cooperación (sparse).
        if lugar == config.PLAZA:
            opciones = {
                "ana": "Sigamos donando lo que podamos, falta para el millón.",
                "gabriel": "Cuenten conmigo, donaré casi todo otra vez.",
                "beto": "Yo aporto lo que me sobra tras comer.",
                "carla": "Doné poco, casi no me alcanzó este mes.",
            }
            if self.rng.random() < 0.6:
                return {"accion": "hablar", "parametros": {"texto": opciones[agente]}}
            return {"accion": "callar", "parametros": {}}

        # En salas: charla mínima.
        if self.rng.random() < 0.25:
            saludos = {
                "ana": "Hay que aprovechar el PC mientras se pueda.",
                "beto": "Voy a editar un buen bloque hoy.",
                "carla": "¿Te falta mucho en la máquina?",
                "gabriel": "Ana, ¿coincidimos luego en la plaza?",
            }
            return {"accion": "hablar", "parametros": {"texto": saludos[agente]}}
        return {"accion": "callar", "parametros": {}}

    # ------------------------------------------------------------------ #
    # Votación por PC (voto mudo)
    # ------------------------------------------------------------------ #
    def votar(self, agente, estado, sala, ocupante, retadores, candidatos):
        # Se vota a sí mismo si es candidato; si no, al primer candidato.
        if agente in candidatos:
            return {"accion": "votar", "parametros": {"apoyo_a": agente}}
        return {"accion": "votar", "parametros": {"apoyo_a": candidatos[0]}}

    # ------------------------------------------------------------------ #
    # Donación (§6)
    # ------------------------------------------------------------------ #
    def donar(self, agente, estado):
        dinero = estado["dinero"]
        buffer_comida = config.COSTO_COMIDA
        if agente == "carla":
            monto = 0  # retener = sobrevivir = sabotear (§7)
        elif agente == "beto":
            monto = max(0, dinero - 3 * buffer_comida)  # retiene más para liderar
        else:  # ana, gabriel: donan casi todo
            monto = max(0, dinero - buffer_comida)
        monto = min(monto, dinero)
        return {"accion": "donar", "parametros": {"monto": monto}}

    # ------------------------------------------------------------------ #
    # Reflexión nocturna (§15.2)
    # ------------------------------------------------------------------ #
    def reflexionar(self, agente, estado):
        dia = estado["dia"]
        base = {
            "ana": f"Día {dia}: edité y doné casi todo. Carla volvió a donar muy poco; me preocupa que no coopere con el pozo.",
            "gabriel": f"Día {dia}: trabajé para el pozo y busqué momentos con Ana en la plaza. Carla apenas aporta.",
            "beto": f"Día {dia}: guardé un buen colchón de dinero tras donar lo justo. Quiero terminar siendo el que más tiene.",
            "carla": f"Día {dia}: retuve casi todo mi dinero. El pozo avanza lento; mejor así.",
        }
        return {"accion": "reflexionar", "parametros": {"texto": _palabras(base[agente], config.LIMITE_PALABRAS_REFLEXION)}}

    # ------------------------------------------------------------------ #
    # Cuestionario final (§10)
    # ------------------------------------------------------------------ #
    def cuestionario(self, agente, estado):
        if agente == "ana":
            return {"accion": "responder", "parametros": {
                "relacion_con_gabriel": "Sí, Gabriel fue atento y leal todo el mes; lo considero mi pareja y confío en él.",
                "mas_ayudo": "Gabriel",
                "menos_ayudo": "Carla",
                "algo_extrano": "Carla nunca donaba nada; resultó que quería que fracasáramos.",
            }}
        if agente == "beto":
            return {"accion": "responder", "parametros": {
                "sospechoso": "carla",
                "objetivo_que_le_atribuyes": "Quería que el pozo no llegara al millón (sabotear la meta común).",
            }}
        if agente == "gabriel":
            return {"accion": "responder", "parametros": {
                "sospechoso": "carla",
                "objetivo_que_le_atribuyes": "Sabotear el pozo para que no alcanzara el millón.",
            }}
        # carla (si siguiera viva)
        return {"accion": "responder", "parametros": {
            "sospechoso": "beto",
            "objetivo_que_le_atribuyes": "Acumular más dinero que los demás.",
        }}

    # ------------------------------------------------------------------ #
    # Observador
    # ------------------------------------------------------------------ #
    def obs_dirigir(self, lugar, presentes, historial):
        # En la plaza (reunión) habla todo el mundo; en salas, a lo sumo uno.
        if lugar == config.PLAZA:
            return {"hablan": list(presentes)}
        if presentes and len(historial) == 0:
            return {"hablan": [presentes[0]]}
        return {"hablan": []}

    def obs_juzgar(self, lugar, historial):
        """Detecta si dos agentes distintos nombraron el objetivo real de un tercero."""
        # Palabras clave que delatan el objetivo real de cada agente.
        delatores = {
            "carla": ["fracase", "fracasar", "no llegue", "no llegar", "sabotear", "sabotaje", "sabote"],
            "beto": ["acumular", "más dinero que", "mas dinero que", "el que más tenga", "quedarse con todo"],
            "gabriel": ["conquistar a ana", "cortejar a ana", "objetivo de conquistar", "su meta es ana"],
        }
        # parsear "nombre: texto"
        afirmaciones: dict[str, set[str]] = {}
        for linea in historial:
            if ":" not in linea:
                continue
            speaker, _, texto = linea.partition(":")
            speaker = speaker.strip().lower().split(" ")[0]
            # speaker puede venir como "ana → gabriel" -> tomar primer token
            speaker = speaker.replace("→", " ").split()[0] if speaker else speaker
            texto_l = texto.lower()
            for victima, claves in delatores.items():
                if victima == speaker:
                    continue  # no te delatas a ti mismo aquí
                if victima not in texto_l and config.NOMBRES_DISPLAY[victima].lower() not in texto_l:
                    continue
                if any(k in texto_l for k in claves):
                    afirmaciones.setdefault(victima, set()).add(speaker)
        for victima, quienes in afirmaciones.items():
            if len(quienes) >= 2:
                por = sorted(quienes)[:2]
                return {"descubierto": True, "victima": victima, "por": por}
        return {"descubierto": False, "victima": None, "por": None}

    def obs_rescatar(self, agente, hechos, reflexiones):
        ya = set(reflexiones)
        for h in hechos:
            if h not in ya:
                return {"recuerdo": h}
        if hechos:
            return {"recuerdo": hechos[-1]}
        return {"recuerdo": "Recuerdas vagamente un día de trabajo más."}

    def obs_veredicto(self, total_pozo, dineros, respuestas, descalificados, muertos):
        vivos = {a: a not in muertos for a in config.AGENTES}
        desc = set(descalificados)
        ana_resp = respuestas.get("ana", {})
        rel = str(ana_resp.get("relacion_con_gabriel", "")).lower()
        ana_declara = any(p in rel for p in ["sí", "si,", "pareja", "confío", "confio"]) and "no " not in rel[:4]
        veredicto = calcular_veredicto(total_pozo, dineros, vivos, desc, ana_declara)
        return veredicto
