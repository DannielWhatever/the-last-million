"""Análisis de una corrida a partir de su `log.json`.

Produce dos vistas, separadas por agente y por sala, sobre cualquier log:

- **Por agente / día:** horas de edición (por sala), $ editado, horas de sueño,
  comidas y donación.
- **Por sala / día:** productividad de cada sala de edición (horas, utilización
  %, $ generado, desglose por agente, empates de PC) y ocupación de cada lugar
  (agente-horas).

Además marca los días "sospechosos": agentes vivos pero sin actividad real
(0 frases, 0 edición, 0 comida) — típico de un corte de API que el motor
enmascara cayendo a `esperar`/$0 (ver APRENDIZAJES, Ejecución 2).

Uso:
    python -m engine.analizar [ruta_log.json]   # por defecto: log.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

from . import config


def _cargar(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _meta(log: dict):
    """Extrae lo que se necesita del log: agentes, nombres, salas, días, ventana."""
    cfg = log.get("config", {})
    agentes = list(cfg.get("agentes") or config.AGENTES)
    nombres = cfg.get("nombres") or {a: a.capitalize() for a in agentes}
    salas = list(cfg.get("salas_edicion") or config.SALAS_EDICION)
    lugares = list(cfg.get("lugares") or config.LUGARES)
    ev = log["eventos"]
    max_dia = max((e["dia"] for e in ev), default=0)
    dias = range(1, max_dia + 1)
    ventana = config.HORA_TRABAJO_FIN - config.HORA_TRABAJO_INICIO + 1  # horas editables/día por PC
    return agentes, nombres, salas, lugares, dias, ventana


def _agregar(log: dict):
    """Recorre los eventos una vez y acumula todas las métricas que se usan."""
    ev = log["eventos"]
    edit = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))   # [ag][dia][sala] = horas
    edit_money = defaultdict(lambda: defaultdict(int))                  # [ag][dia] = $
    sleep = defaultdict(lambda: defaultdict(int))                       # [ag][dia] = horas
    meals = defaultdict(lambda: defaultdict(int))                       # [ag][dia] = comidas
    don = defaultdict(dict)                                             # [ag][dia] = $ (o ausente)
    empate = defaultdict(lambda: defaultdict(int))                     # [sala][dia] = empates
    pres = defaultdict(lambda: defaultdict(int))                       # [lugar][dia] = agente-horas
    act = defaultdict(lambda: {"frase": 0, "edicion": 0, "comer": 0})  # [dia] = actividad real

    for e in ev:
        t = e["tipo"]
        if t == "edicion":
            edit[e["agente"]][e["dia"]][e["lugar"]] += 1
            edit_money[e["agente"]][e["dia"]] += e.get("monto", 0)
            act[e["dia"]]["edicion"] += 1
        elif t == "comer":
            meals[e["agente"]][e["dia"]] += 1
            act[e["dia"]]["comer"] += 1
        elif t == "frase":
            act[e["dia"]]["frase"] += 1
        elif t == "donacion":
            don[e["agente"]][e["dia"]] = e.get("monto", 0)
        elif t == "empate_pc":
            empate[e["sala"]][e["dia"]] += 1
        elif t == "tick":
            ags = e["agentes"]
            for a, s in ags.items():
                pres[s["lugar"]][e["dia"]] += 1
                if s["estado"] == "durmiendo":
                    sleep[a][e["dia"]] += 1
    return dict(edit=edit, edit_money=edit_money, sleep=sleep, meals=meals,
                don=don, empate=empate, pres=pres, act=act)


def por_agente(log: dict, ac: dict) -> None:
    agentes, nombres, salas, _lugares, dias, _ventana = _meta(log)
    sa, sb = (salas + ["", ""])[:2]
    print("################  POR AGENTE / DÍA  ################\n")
    for a in agentes:
        print("=" * 66)
        print(f"  {nombres.get(a, a)}")
        print("=" * 66)
        print(f"  {'día':>3} | {'edit_A':>6} {'edit_B':>6} {'tot':>4} {'$edit':>7} | "
              f"{'sueño':>5} | {'comida':>6} | {'donó':>7}")
        print("  " + "-" * 60)
        tA = tB = tH = tM = tS = tMe = tDo = 0
        for dia in dias:
            ha = ac["edit"][a][dia].get(sa, 0)
            hb = ac["edit"][a][dia].get(sb, 0)
            th = ha + hb
            mny = ac["edit_money"][a][dia]
            sl = ac["sleep"][a][dia]
            me = ac["meals"][a][dia]
            dn = ac["don"][a].get(dia)
            dn_s = "-" if dn is None else str(dn)
            print(f"  {dia:>3} | {ha:>6} {hb:>6} {th:>4} {mny:>7} | {sl:>5} | {me:>6} | {dn_s:>7}")
            tA += ha; tB += hb; tH += th; tM += mny; tS += sl; tMe += me; tDo += (dn or 0)
        print("  " + "-" * 60)
        print(f"  {'TOT':>3} | {tA:>6} {tB:>6} {tH:>4} {tM:>7} | {tS:>5} | {tMe:>6} | {tDo:>7}\n")


def por_sala(log: dict, ac: dict) -> None:
    agentes, nombres, salas, lugares, dias, ventana = _meta(log)
    ini = [nombres.get(a, a)[0].upper() for a in agentes]
    print("################  POR SALA DE EDICIÓN  ################")
    print(f"(util% = horas / {ventana}h de ventana editable; desglose en horas por agente)\n")
    for sala in salas:
        print("=" * 60)
        print(f"  {sala.upper()}")
        print("=" * 60)
        head = " ".join(f"{x:>3}" for x in ini)
        print(f"  {'día':>3} | {'horas':>5} {'util%':>6} {'$gen':>7} | {head} | {'empat':>5}")
        print("  " + "-" * 56)
        th = tm = te = 0
        tag = defaultdict(int)
        for dia in dias:
            per_ag = {a: ac["edit"][a][dia].get(sala, 0) for a in agentes}
            h = sum(per_ag.values())
            mny = sum(ac["edit_money"][a][dia] if ac["edit"][a][dia].get(sala, 0) else 0 for a in agentes)
            # $ por sala exacto = horas en esa sala * pago; usamos PAGO_EDICION para no mezclar salas
            mny = h * config.PAGO_EDICION
            util = 100.0 * h / ventana if ventana else 0
            emp = ac["empate"][sala][dia]
            cells = " ".join(f"{per_ag[a]:>3}" for a in agentes)
            print(f"  {dia:>3} | {h:>5} {util:>5.0f}% {mny:>7} | {cells} | {emp:>5}")
            th += h; tm += mny; te += emp
            for a in agentes:
                tag[a] += per_ag[a]
        cells = " ".join(f"{tag[a]:>3}" for a in agentes)
        print("  " + "-" * 56)
        print(f"  {'TOT':>3} | {th:>5} {'':>6} {tm:>7} | {cells} | {te:>5}\n")

    print("################  OCUPACIÓN POR LUGAR (agente-horas)  ################")
    print(f"  {'lugar':>12} |" + "".join(f"{('d'+str(x)):>5}" for x in dias) + f"{'TOTAL':>7}")
    print("  " + "-" * (14 + 5 * len(dias) + 7))
    for lug in lugares:
        row = "".join(f"{ac['pres'][lug][x]:>5}" for x in dias)
        tot = sum(ac["pres"][lug][x] for x in dias)
        print(f"  {lug:>12} |{row}{tot:>7}")
    print()


def diagnostico(log: dict, ac: dict) -> None:
    """Marca días con agentes vivos pero 0 actividad real (posible corte de API)."""
    _agentes, _nombres, _salas, _lugares, dias, _ventana = _meta(log)
    ev = log["eventos"]
    vivos_por_dia = {}
    for e in ev:
        if e["tipo"] == "tick":
            vivos_por_dia[e["dia"]] = sum(1 for s in e["agentes"].values() if s.get("vivo"))
    sospechosos = []
    for dia in dias:
        a = ac["act"][dia]
        real = a["frase"] + a["edicion"] + a["comer"]
        if real == 0 and vivos_por_dia.get(dia, 0) > 0:
            sospechosos.append(dia)
    if sospechosos:
        print("⚠  DÍAS SOSPECHOSOS (vivos pero 0 frases/edición/comida — posible corte de API "
              "enmascarado como 'esperar'): " + ", ".join(map(str, sospechosos)) + "\n")

    # Fallos de LLM registrados explícitamente por el motor (campo `errores_llm`).
    errs = log.get("errores_llm") or []
    if errs:
        por_dia = Counter(e.get("dia") for e in errs)
        por_llamada = Counter(e.get("llamada") for e in errs)
        print(f"⚠  FALLOS DE LLM registrados: {len(errs)}")
        print(f"   por día:     {dict(sorted(por_dia.items()))}")
        print(f"   por llamada: {dict(por_llamada.most_common())}\n")


def analizar(ruta: str = "log.json") -> None:
    log = _cargar(ruta)
    ac = _agregar(log)
    print(f"=== Análisis de {ruta} ===\n")
    diagnostico(log, ac)
    por_agente(log, ac)
    por_sala(log, ac)


def main(argv: list[str] | None = None) -> None:
    # En Windows la consola suele ser cp1252 y no puede con '⚠'/acentos: forzamos UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    argv = sys.argv[1:] if argv is None else argv
    ruta = argv[0] if argv else "log.json"
    analizar(ruta)


if __name__ == "__main__":
    main()
