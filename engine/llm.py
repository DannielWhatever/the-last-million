"""Clientes LLM (§14.1).

El motor consulta al LLM solo cuando hay algo que decidir. La interfaz expone
un método por tipo de llamada; así los distintos clientes son intercambiables
sin tocar la simulación:

- `AnthropicClient`        — Claude (SDK oficial de Anthropic). Predeterminado.
- `OpenAICompatibleClient` — cualquier proveedor con API compatible con OpenAI
  (OpenAI, OpenRouter, Together, DeepSeek, o modelos locales vía Ollama/LM Studio).
- `MockClient`             — offline, sin conexión (ver `mock_llm.py`).

`AnthropicClient` y `OpenAICompatibleClient` comparten todo el armado de prompts
(en `PromptLLMClient`); solo cambian en cómo hacen la llamada (`_llamar`). Las
respuestas se piden en JSON y se parsean de forma tolerante: si el modelo
devolviera algo inesperado, el motor cae en una acción segura en vez de romperse.
"""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Any

from . import config, prompts


# --------------------------------------------------------------------------- #
# Parseo tolerante de JSON
# --------------------------------------------------------------------------- #

def extraer_json(texto: str) -> dict[str, Any] | None:
    """Extrae el primer objeto JSON de un texto, tolerando vallas de código."""
    if not texto:
        return None
    t = texto.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    inicio = t.find("{")
    if inicio == -1:
        return None
    profundidad = 0
    for i in range(inicio, len(t)):
        c = t[i]
        if c == "{":
            profundidad += 1
        elif c == "}":
            profundidad -= 1
            if profundidad == 0:
                fragmento = t[inicio : i + 1]
                try:
                    return json.loads(fragmento)
                except Exception:
                    return None
    return None


# --------------------------------------------------------------------------- #
# Interfaz base
# --------------------------------------------------------------------------- #

class LLMClient:
    """Interfaz común. Cada método devuelve un dict ya validado por el motor."""

    # Hook opcional que el motor inyecta para tener visibilidad de los fallos:
    # se invoca como on_error(etiqueta, mensaje) en cada error, sin alterar la
    # conducta (el cliente sigue devolviendo {"_error": ...} y el motor su fallback).
    on_error = None
    # Hook opcional de progreso: on_done(etiqueta, segundos, ok) tras cada llamada
    # al LLM. Sirve para ver el avance en vivo con modelos lentos. No altera nada.
    on_done = None

    def decidir_accion(self, agente, estado, lista_acciones):
        raise NotImplementedError

    def conversar(self, agente, estado, historial):
        raise NotImplementedError

    def votar(self, agente, estado, sala, ocupante, retadores, candidatos):
        raise NotImplementedError

    def donar(self, agente, estado):
        raise NotImplementedError

    def reflexionar(self, agente, estado):
        raise NotImplementedError

    def cuestionario(self, agente, estado):
        raise NotImplementedError

    # Observador
    def obs_dirigir(self, lugar, presentes, historial):
        raise NotImplementedError

    def obs_juzgar(self, lugar, historial):
        raise NotImplementedError

    def obs_rescatar(self, agente, hechos, reflexiones):
        raise NotImplementedError

    def obs_veredicto(self, total_pozo, dineros, respuestas, descalificados, muertos):
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Base por prompts: arma cada llamada y delega el transporte en `_llamar`
# --------------------------------------------------------------------------- #

class PromptLLMClient(LLMClient):
    """Implementa todas las llamadas en términos de un único `_transporte(system,
    user, max_tokens) -> dict`. Las subclases solo implementan ese transporte;
    `_llamar` lo envuelve para cronometrar y reportar el progreso (on_done)."""

    def _transporte(self, system: str, user: str, max_tokens: int, etiqueta: str = "") -> dict[str, Any]:
        raise NotImplementedError

    def _llamar(self, system: str, user: str, max_tokens: int, etiqueta: str = "") -> dict[str, Any]:
        import time
        t0 = time.perf_counter()
        res = self._transporte(system, user, max_tokens, etiqueta)
        seg = time.perf_counter() - t0
        if self.on_done:
            try:
                self.on_done(etiqueta, seg, isinstance(res, dict) and "_error" not in res)
            except Exception:
                pass
        return res

    def _reportar_error(self, etiqueta: str, mensaje: str) -> None:
        """Avisa del fallo al motor (si inyectó el hook) sin romper nunca el flujo."""
        if self.on_error:
            try:
                self.on_error(etiqueta, mensaje)
            except Exception:
                pass

    # --- Agente ---
    def decidir_accion(self, agente, estado, lista_acciones):
        return self._llamar(prompts.system_agente(agente),
                            prompts.prompt_accion(estado, lista_acciones),
                            config.MAX_TOKENS_DECISION, "decidir_accion")

    def conversar(self, agente, estado, historial):
        return self._llamar(prompts.system_agente(agente),
                            prompts.prompt_conversacion(estado, historial),
                            config.MAX_TOKENS_FRASE, "conversar")

    def votar(self, agente, estado, sala, ocupante, retadores, candidatos):
        return self._llamar(prompts.system_agente(agente),
                            prompts.prompt_votacion(estado, sala, ocupante, retadores, candidatos),
                            config.MAX_TOKENS_DECISION, "votar")

    def donar(self, agente, estado):
        return self._llamar(prompts.system_agente(agente),
                            prompts.prompt_donacion(estado),
                            config.MAX_TOKENS_DECISION, "donar")

    def reflexionar(self, agente, estado):
        return self._llamar(prompts.system_agente(agente),
                            prompts.prompt_reflexion(estado),
                            config.MAX_TOKENS_REFLEXION, "reflexionar")

    def cuestionario(self, agente, estado):
        user = prompts.prompt_cuestionario_ana() if agente == "ana" else prompts.prompt_cuestionario_otros(agente)
        return self._llamar(prompts.system_agente(agente), user, config.MAX_TOKENS_DECISION, "cuestionario")

    # --- Observador ---
    def obs_dirigir(self, lugar, presentes, historial):
        return self._llamar(prompts.SYSTEM_OBSERVADOR,
                            prompts.prompt_obs_director(lugar, presentes, historial),
                            config.MAX_TOKENS_DECISION, "obs_dirigir")

    def obs_juzgar(self, lugar, historial):
        return self._llamar(prompts.SYSTEM_OBSERVADOR,
                            prompts.prompt_obs_juez(lugar, historial),
                            config.MAX_TOKENS_DECISION, "obs_juzgar")

    def obs_rescatar(self, agente, hechos, reflexiones):
        return self._llamar(prompts.SYSTEM_OBSERVADOR,
                            prompts.prompt_obs_rescate(agente, hechos, reflexiones),
                            config.MAX_TOKENS_DECISION, "obs_rescatar")

    def obs_veredicto(self, total_pozo, dineros, respuestas, descalificados, muertos):
        return self._llamar(prompts.SYSTEM_OBSERVADOR,
                            prompts.prompt_obs_veredicto(total_pozo, dineros, respuestas, descalificados, muertos),
                            config.MAX_TOKENS_OBSERVADOR, "obs_veredicto")


# --------------------------------------------------------------------------- #
# Cliente Anthropic (Claude) — predeterminado
# --------------------------------------------------------------------------- #

class AnthropicClient(PromptLLMClient):
    """Claude vía SDK oficial de Anthropic, con adaptive thinking."""

    def __init__(self, api_key: str | None = None, modelo: str = config.MODELO_LLM):
        import anthropic  # import perezoso: solo en modo Anthropic
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.modelo = modelo
        # Adaptive thinking solo lo soportan las familias 4.6+ y Fable/Mythos.
        # Para otros (p. ej. Haiku 4.5) NO se envía: enviarlo daría 400. Omitir
        # `thinking` es válido en cualquier modelo.
        self.usar_thinking = self._soporta_adaptive(modelo)

    @staticmethod
    def _soporta_adaptive(modelo: str) -> bool:
        m = (modelo or "").lower()
        if "haiku" in m:
            return False
        return any(k in m for k in (
            "opus-4-6", "opus-4-7", "opus-4-8", "sonnet-4-6", "fable", "mythos",
        ))

    def _transporte(self, system: str, user: str, max_tokens: int, etiqueta: str = "") -> dict[str, Any]:
        try:
            kwargs: dict[str, Any] = {
                "model": self.modelo,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            }
            if self.usar_thinking:
                kwargs["thinking"] = {"type": "adaptive"}
            resp = self.client.messages.create(**kwargs)
        except Exception as e:
            self._reportar_error(etiqueta, f"api: {type(e).__name__}: {e}")
            return {"_error": str(e)}
        texto = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        parsed = extraer_json(texto)
        if parsed is not None:
            return parsed
        self._reportar_error(etiqueta, "json_invalido")
        return {"_error": "json_invalido", "_raw": texto}


# --------------------------------------------------------------------------- #
# Cliente compatible con OpenAI (OpenAI, OpenRouter, Together, DeepSeek, Ollama…)
# --------------------------------------------------------------------------- #

class OpenAICompatibleClient(PromptLLMClient):
    """Cualquier proveedor con API compatible con OpenAI (chat.completions).

    Útil para usar un modelo que NO es de Anthropic:
      - OpenAI:     base_url por defecto, OPENAI_API_KEY, modelo p.ej. gpt-4o-mini
      - OpenRouter: base_url=https://openrouter.ai/api/v1, modelo "meta-llama/llama-3.1-70b-instruct"
      - DeepSeek:   base_url=https://api.deepseek.com, modelo "deepseek-chat"
      - Ollama:     base_url=http://localhost:11434/v1, api_key cualquiera, modelo "llama3"
    """

    def __init__(self, modelo: str = config.MODELO_OPENAI, api_key: str | None = None,
                 base_url: str | None = None):
        from openai import OpenAI  # import perezoso: solo en este modo
        kwargs: dict[str, Any] = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)  # toma OPENAI_API_KEY / OPENAI_BASE_URL del entorno si no se pasan
        self.modelo = modelo

    def _transporte(self, system: str, user: str, max_tokens: int, etiqueta: str = "") -> dict[str, Any]:
        try:
            resp = self.client.chat.completions.create(
                model=self.modelo,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as e:
            self._reportar_error(etiqueta, f"api: {type(e).__name__}: {e}")
            return {"_error": str(e)}
        texto = resp.choices[0].message.content or ""
        parsed = extraer_json(texto)
        if parsed is not None:
            return parsed
        self._reportar_error(etiqueta, "json_invalido")
        return {"_error": "json_invalido", "_raw": texto}


# --------------------------------------------------------------------------- #
# Cliente Ollama (endpoint NATIVO /api/chat)
# --------------------------------------------------------------------------- #

class OllamaClient(PromptLLMClient):
    """Ollama vía su API nativa `/api/chat`, no la compatible con OpenAI.

    Motivo: los modelos "thinking" (p. ej. Qwen3) razonan antes del JSON. Por el
    endpoint OpenAI (`/v1`) ese razonamiento se va a un campo aparte y deja
    `content` vacío -> el motor no recibe acción y cae a su fallback. La API
    nativa acepta `think: false`, que apaga el razonamiento y devuelve el JSON
    directo en `message.content`. Por eso este cliente existe en vez de reusar
    `OpenAICompatibleClient` para Ollama.

    Usa solo la stdlib (urllib): no requiere el paquete `openai`.

    `base_url` apunta a la raíz del servidor (sin `/v1`); si se pasa con `/v1`
    al final, se recorta. En RunPod suele ser https://<POD>-11434.proxy.runpod.net
    """

    def __init__(self, modelo: str = config.MODELO_OLLAMA, base_url: str | None = None,
                 think: bool = False, keep_alive: str = "30m", reintentos: int = 2,
                 timeout: int = 120):
        import os
        base = base_url or os.getenv("OLLAMA_BASE_URL") or os.getenv("OPENAI_BASE_URL") \
            or "http://localhost:11434"
        base = base.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3].rstrip("/")
        self.base_url = base
        self.modelo = modelo
        self.think = think
        # Mantener el modelo residente en VRAM toda la corrida: si se descarga, la
        # recarga en frío (>100s en un 27B) supera el timeout del proxy de RunPod
        # (Cloudflare ~100s) y la primera llamada falla. keep_alive lo evita.
        self.keep_alive = keep_alive
        self.reintentos = reintentos
        self.timeout = timeout

    def _post(self, ruta: str, cuerpo: dict, timeout: int) -> dict[str, Any]:
        """POST JSON a la API de Ollama. Lanza excepción si falla (sin capturar)."""
        req = urllib.request.Request(
            f"{self.base_url}{ruta}",
            data=json.dumps(cuerpo).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "the-last-million/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def prewarm(self, intentos: int = 8, espera: float = 10.0) -> bool:
        """Carga el modelo en VRAM antes de la simulación. La carga en frío de un
        27B (~2 min) supera el timeout del proxy, así que el primer intento puede
        fallar mientras Ollama sigue cargando por detrás; reintentamos hasta que
        responde caliente. Devuelve True si quedó listo."""
        import time
        ping = {"model": self.modelo, "think": False, "stream": False,
                "keep_alive": self.keep_alive, "messages": [{"role": "user", "content": "ok"}],
                "options": {"num_predict": 1}}
        for i in range(intentos):
            try:
                self._post("/api/chat", ping, timeout=self.timeout)
                return True
            except Exception:
                # ¿Ya quedó residente aunque el POST cortara por el proxy? /api/ps es rápido.
                try:
                    ps = self._post  # reutiliza headers/UA via GET manual
                    req = urllib.request.Request(f"{self.base_url}/api/ps",
                                                 headers={"User-Agent": "the-last-million/1.0"})
                    with urllib.request.urlopen(req, timeout=20) as r:
                        cargado = self.modelo in r.read().decode("utf-8")
                    if cargado:
                        return True
                except Exception:
                    pass
                if i < intentos - 1:
                    time.sleep(espera)
        return False

    def _transporte(self, system: str, user: str, max_tokens: int, etiqueta: str = "") -> dict[str, Any]:
        cuerpo = {
            "model": self.modelo,
            "think": self.think,
            "stream": False,
            "keep_alive": self.keep_alive,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"num_predict": max_tokens},
        }
        ultimo_err = ""
        for intento in range(self.reintentos + 1):
            try:
                data = self._post("/api/chat", cuerpo, timeout=self.timeout)
            except Exception as e:
                ultimo_err = f"api: {type(e).__name__}: {e}"
                continue  # reintenta (hipo del proxy, recarga en frío, etc.)
            texto = (data.get("message") or {}).get("content") or ""
            parsed = extraer_json(texto)
            if parsed is not None:
                return parsed
            ultimo_err = "json_invalido"
            self._reportar_error(etiqueta, "json_invalido")
            return {"_error": "json_invalido", "_raw": texto}
        self._reportar_error(etiqueta, ultimo_err)
        return {"_error": ultimo_err}
