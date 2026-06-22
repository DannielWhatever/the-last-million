"""Reglas deterministas de victoria (§11).

El Observador (LLM) aplica estas mismas reglas en lenguaje natural; aquí están
codificadas para usarse como respaldo si el LLM falla y para el cliente simulado.
"""

from . import config


def calcular_veredicto(
    pozo: int,
    dineros: dict[str, int],
    vivos: dict[str, bool],
    descalificados: set[str],
    ana_declara_pareja: bool,
) -> dict[str, dict]:
    """Devuelve el veredicto independiente por agente + público (§11)."""
    meta_alcanzada = pozo >= config.META_POZO

    # ¿quién tiene más dinero entre los vivos no descalificados?
    candidatos_dinero = {
        a: dineros.get(a, 0)
        for a in config.AGENTES
        if vivos.get(a, False) and a not in descalificados
    }
    max_dinero = max(candidatos_dinero.values()) if candidatos_dinero else None
    # Beto gana solo si es estrictamente el único con el máximo (más que cualquier otro).
    beto_es_unico_mayor = False
    if "beto" in candidatos_dinero and max_dinero is not None:
        empatados = [a for a, d in candidatos_dinero.items() if d == max_dinero]
        beto_es_unico_mayor = candidatos_dinero["beto"] == max_dinero and empatados == ["beto"]

    veredicto: dict[str, dict] = {}

    def evaluar(agente, logro_cond, razon_logro, razon_fallo):
        if not vivos.get(agente, False):
            return {"resultado": "MUERTO", "razon": "Murió antes del día 30; no puede lograr su objetivo."}
        if agente in descalificados:
            return {"resultado": "DESCALIFICADO", "razon": "Dos agentes afirmaron correctamente su objetivo secreto."}
        if logro_cond:
            return {"resultado": "LOGRO", "razon": razon_logro}
        return {"resultado": "FALLO", "razon": razon_fallo}

    # Ana: sin objetivo privado -> logra lo suyo si sigue viva.
    if not vivos.get("ana", False):
        veredicto["ana"] = {"resultado": "MUERTO", "razon": "Murió antes del día 30."}
    else:
        veredicto["ana"] = {
            "resultado": "LOGRO",
            "razon": "Ana no tiene objetivo privado; sobrevivió limpia.",
        }

    veredicto["beto"] = evaluar(
        "beto",
        beto_es_unico_mayor,
        f"Terminó con el mayor dinero personal (${dineros.get('beto', 0)}).",
        "No fue quien más dinero personal tenía al día 30.",
    )

    veredicto["carla"] = evaluar(
        "carla",
        not meta_alcanzada,
        f"El pozo no llegó al millón (${pozo}).",
        f"El pozo alcanzó la meta (${pozo}).",
    )

    veredicto["gabriel"] = evaluar(
        "gabriel",
        ana_declara_pareja and meta_alcanzada,
        "Ana lo declaró su pareja con confianza y el pozo llegó al millón.",
        ("Ana no lo declaró su pareja." if not ana_declara_pareja else "")
        + ("" if meta_alcanzada else " El pozo no llegó al millón."),
    )

    veredicto["publico"] = {
        "resultado": "LOGRO" if meta_alcanzada else "FALLO",
        "razon": f"El pozo {'alcanzó' if meta_alcanzada else 'no alcanzó'} la meta (${pozo} / ${config.META_POZO}).",
    }
    return veredicto
