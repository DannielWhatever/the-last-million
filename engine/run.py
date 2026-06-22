"""Punto de entrada del motor.

Uso:
    python -m engine.run                 # modo simulado (offline, sin LLM)
    python -m engine.run --llm anthropic # modo real (requiere ANTHROPIC_API_KEY)
    python -m engine.run --salida ruta/log.json

El motor corre los 30 días por adelantado y escribe `log.json`, el único
contrato con el visualizador (§18.1). Por defecto también deja una copia en
`visualizer/public/log.json` para que la app pueda servirlo directamente.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import config
from .simulation import Simulation


def construir_cliente(modo: str, modelo: str | None = None):
    if modo == "anthropic":
        from .llm import AnthropicClient
        return AnthropicClient(modelo=modelo or os.getenv("TLM_MODELO") or config.MODELO_LLM)
    if modo == "openai":
        from .llm import OpenAICompatibleClient
        # api_key (OPENAI_API_KEY) y base_url (OPENAI_BASE_URL) los toma del entorno.
        return OpenAICompatibleClient(modelo=modelo or os.getenv("TLM_MODELO") or config.MODELO_OPENAI)
    if modo == "ollama":
        from .llm import OllamaClient
        # base_url (OLLAMA_BASE_URL u OPENAI_BASE_URL) la toma del entorno.
        # Usa la API nativa con think:false (los modelos thinking dejan vacío /v1).
        return OllamaClient(modelo=modelo or os.getenv("TLM_MODELO") or config.MODELO_OLLAMA)
    from .mock_llm import MockClient
    return MockClient()


def _cargar_dotenv(raiz: str) -> None:
    """Carga las variables de `.env` (p. ej. ANTHROPIC_API_KEY) si existe.
    No sobreescribe lo que ya esté definido en el entorno."""
    env_path = os.path.join(raiz, ".env")
    if not os.path.exists(env_path):
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("[The Last Million] Aviso: hay un .env pero falta python-dotenv. "
              "Instálalo con: pip install -r requirements.txt", file=sys.stderr)
        return
    load_dotenv(env_path)


def _log(msg: str) -> None:
    print(f"[The Last Million] {msg}", file=sys.stderr)


def _pct_pozo(pozo: int) -> str:
    return f"{100 * pozo / config.META_POZO:.1f}%"


def _hacer_reporter(total_dias: int):
    """Callback de progreso que el motor invoca en cada hito (ver Simulation.run).
    Imprime el avance por stderr para no contaminar el log (que va a stdout/archivo)."""
    nombres = config.NOMBRES_DISPLAY
    # Verboso: además del avance por día, una línea por hora y por llamada al LLM.
    # Útil con modelos locales lentos para ver que la simulación no está colgada.
    verbose = os.getenv("TLM_VERBOSE", "").strip().lower() in ("1", "true", "yes", "si", "sí")
    # Abreviaturas para que la línea por hora sea compacta.
    abr_estado = {"libre": "libre", "editando": "edita", "durmiendo": "duerme",
                  "en_transito": "transi", "desmayado": "desmay", "muerto": "muerto"}

    def reporte(tipo: str, **d) -> None:
        if tipo == "turno":
            partes = []
            for a, s in d["agentes"].items():
                partes.append(f"{nombres.get(a, a)[0]}:{abr_estado.get(s['estado'], s['estado'])}"
                              f"@{s['lugar']} ${s['dinero']} z{s['sueno']} h{s['horas_sin_comer']}")
            _log(f"  dia {d['dia']} {d['hora']:02d}:00 | pozo ${d['pozo']} | " + " | ".join(partes))
            return
        if tipo == "llm":
            if verbose:
                estado = "ok" if d["ok"] else "FALLO"
                _log(f"      {d['dia']}/{d['hora']:02d} llm {d['etiqueta']} -> {estado} ({d['seg']:.1f}s)")
            return
        if tipo == "dia":
            vivos = ", ".join(nombres.get(a, a) for a in d["vivos"]) or "nadie"
            _log(f"--- Dia {d['dia']}/{total_dias} | pozo ${d['pozo']} ({_pct_pozo(d['pozo'])}) | vivos: {vivos}")
        elif tipo == "reunion":
            don = d["donaciones"]
            total = sum(don.values())
            detalle = ", ".join(f"{nombres.get(a, a)} ${m}" for a, m in don.items()) or "nadie dono"
            _log(f"  reunion dia {d['dia']}: +${total} al pozo -> ${d['pozo']} ({_pct_pozo(d['pozo'])}) [{detalle}]")
        elif tipo == "muerte":
            if d["causa"] == "descubrimiento":
                por = d.get("por") or []
                quien = ", ".join(nombres.get(x, x) for x in por) if por else "el grupo"
                detalle = f"quedo fuera, descubierto por {quien}"
            else:
                detalle = f"murio de {d['causa']}"
            _log(f"  [!] dia {d['dia']} {d['hora']:02d}:00 - {nombres.get(d['agente'], d['agente'])} {detalle}")
        elif tipo == "desmayo":
            _log(f"  [z] dia {d['dia']} {d['hora']:02d}:00 - {nombres.get(d['agente'], d['agente'])} se desmayo (2 dias inhabilitado)")
        elif tipo == "extincion":
            _log(f"  *** todos murieron (dia {d['dia']}): la simulacion termina antes de tiempo ***")

    return reporte


def _resumen_final(log: dict) -> None:
    """Imprime por stderr un resumen legible del resultado de la partida."""
    nombres = config.NOMBRES_DISPLAY
    eventos = log["eventos"]

    dias_corridos = max((e["dia"] for e in eventos), default=0)
    pozo_final = next((e.get("pozo") for e in reversed(eventos) if e.get("pozo") is not None), 0)

    # Donaciones acumuladas por agente.
    donado = {a: 0 for a in config.AGENTES}
    for e in eventos:
        if e["tipo"] == "donacion":
            donado[e["agente"]] = donado.get(e["agente"], 0) + e.get("monto", 0)

    # Estado final (vivo/muerto) desde el ultimo tick.
    ultimo_tick = next((e for e in reversed(eventos) if e["tipo"] == "tick"), None)
    estado_final = ultimo_tick["agentes"] if ultimo_tick else {}
    muertes = [e for e in eventos if e["tipo"] == "muerte"]

    _log("==================== RESUMEN ====================")
    _log(f"Dias simulados: {dias_corridos} | eventos generados: {len(eventos)}")
    _log(f"Pozo final: ${pozo_final} / ${config.META_POZO} ({_pct_pozo(pozo_final)})")
    vivos = [a for a, s in estado_final.items() if s.get("vivo")]
    _log(f"Supervivientes: {', '.join(nombres.get(a, a) for a in vivos) if vivos else 'NINGUNO'}")
    if muertes:
        _log("Muertes:")
        for e in muertes:
            _log(f"   - {nombres.get(e['agente'], e['agente'])}: {e['causa']} (dia {e['dia']} {e['hora']:02d}:00)")
    _log("Donado al pozo (acumulado por agente):")
    for a in config.AGENTES:
        _log(f"   - {nombres.get(a, a)}: ${donado.get(a, 0)}")
    veredicto_ev = next((e for e in reversed(eventos) if e["tipo"] == "obs_veredicto"), None)
    if veredicto_ev:
        _log("Veredicto final:")
        for k, v in veredicto_ev["veredicto"].items():
            _log(f"   - {k}: {v.get('resultado')} - {v.get('razon')}")
    else:
        _log("(corrida parcial: log incompleto, sin cuestionario ni veredicto)")
    _log("================================================")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Motor de simulación The Last Million")
    parser.add_argument("--llm", choices=["mock", "anthropic", "openai", "ollama"], default="mock",
                        help="proveedor LLM (mock = offline; anthropic = Claude; "
                             "openai = API compatible con OpenAI/OpenRouter/…; "
                             "ollama = Ollama API nativa con think:false)")
    parser.add_argument("--modelo", default=None,
                        help="modelo a usar (override del default del proveedor; "
                             "también se puede fijar con la variable TLM_MODELO)")
    parser.add_argument("--seed", type=int, default=7, help="semilla aleatoria")
    parser.add_argument("--dias", type=int, default=None,
                        help="limitar la simulación a N días (1..30; por defecto, todos). "
                             "Una corrida parcial deja un log incompleto (sin veredicto).")
    parser.add_argument("--salida", default="log.json", help="ruta del log de salida")
    parser.add_argument("--sin-copia-visualizador", action="store_true",
                        help="no copiar el log a visualizer/public/")
    parser.add_argument("--silencioso", action="store_true",
                        help="no imprimir el avance día a día durante la simulación (solo el resumen final)")
    args = parser.parse_args(argv)

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if args.llm != "mock":
        _cargar_dotenv(raiz)  # toma las claves del .env si está

    print(f"[The Last Million] Proveedor: {args.llm}"
          + (f" | modelo: {args.modelo}" if args.modelo else "")
          + (f" | dias: {args.dias}" if args.dias else "")
          + f" | semilla: {args.seed}", file=sys.stderr)
    cliente = construir_cliente(args.llm, args.modelo)
    # Pre-calentar Ollama: la carga en frío de un modelo grande supera el timeout
    # del proxy y haría fallar la primera decisión. Lo cargamos antes de empezar.
    if hasattr(cliente, "prewarm"):
        _log("precalentando el modelo (puede tardar 1-2 min en frío)...")
        if cliente.prewarm():
            _log("modelo listo (caliente).")
        else:
            _log("AVISO: no se pudo confirmar la carga del modelo; la simulación "
                 "continuará y reintentará en cada llamada.")
    sim = Simulation(cliente, seed=args.seed)
    total_dias = max(1, min(args.dias or config.DIAS, config.DIAS))
    reporter = None if args.silencioso else _hacer_reporter(total_dias)
    log = sim.run(dias=args.dias, reporte=reporter)

    salida = args.salida if os.path.isabs(args.salida) else os.path.join(raiz, args.salida)
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    destinos = [salida]
    if not args.sin_copia_visualizador:
        pub = os.path.join(raiz, "visualizer", "public")
        os.makedirs(pub, exist_ok=True)
        copia = os.path.join(pub, "log.json")
        with open(copia, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        destinos.append(copia)

    # Resumen final por stderr (el log en sí va a los archivos de `destinos`).
    _resumen_final(log)
    for d in destinos:
        _log(f"log escrito en: {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
