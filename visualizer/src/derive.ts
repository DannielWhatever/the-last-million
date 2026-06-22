// Reducer estilo Redux (§17): el estado se deriva aplicando eventos en orden.
// Avanzar = puntero+1; retroceder = puntero-1; saltar = snapshot + aplicar.

import type { GameEvent, SimLog, WorldView } from "./types";

export interface LogIndex {
  lastTickAt: Int32Array; // por cada índice de evento, el índice del último tick <= i (-1 si ninguno)
  dayStart: Record<number, number>; // dia -> índice del primer evento de ese día
  hourStarts: number[]; // índices del primer evento de cada hora distinta (dia,hora), en orden
  hourBucket: Int32Array; // por cada índice de evento, su posición en hourStarts
  maxDinero: number; // para escalar barras de dinero
}

export function buildIndex(log: SimLog): LogIndex {
  const ev = log.eventos;
  const lastTickAt = new Int32Array(ev.length);
  const hourBucket = new Int32Array(ev.length);
  const dayStart: Record<number, number> = {};
  const hourStarts: number[] = [];
  let lastTick = -1;
  let maxDinero = 1;
  let prevDia = NaN, prevHora = NaN;
  for (let i = 0; i < ev.length; i++) {
    const e = ev[i];
    if (e.tipo === "tick") {
      lastTick = i;
      const ag = e.agentes as Record<string, { dinero: number }>;
      for (const k in ag) maxDinero = Math.max(maxDinero, ag[k].dinero);
    }
    if (e.tipo === "dia_inicio" && dayStart[e.dia] === undefined) dayStart[e.dia] = i;
    if (e.dia !== prevDia || e.hora !== prevHora) {
      hourStarts.push(i);
      prevDia = e.dia;
      prevHora = e.hora;
    }
    hourBucket[i] = hourStarts.length - 1;
    lastTickAt[i] = lastTick;
  }
  return { lastTickAt, dayStart, hourStarts, hourBucket, maxDinero };
}

export function deriveWorld(log: SimLog, index: number, idx: LogIndex): WorldView {
  const ev = log.eventos;
  const clamped = Math.max(0, Math.min(index, ev.length - 1));
  const cur = ev[clamped];

  // Indicadores: del último tick <= puntero; si no hay, del estado inicial.
  const tickIdx = idx.lastTickAt[clamped];
  const agentes: WorldView["agentes"] = {};
  let pozo = 0;

  if (tickIdx >= 0) {
    const t = ev[tickIdx];
    pozo = (t.pozo as number) ?? 0;
    const ag = t.agentes as Record<string, any>;
    for (const k in ag) {
      agentes[k] = { ...ag[k], dineroReal: ag[k].dinero };
    }
  } else {
    const init = log.estado_inicial;
    pozo = init.pozo;
    for (const k of log.config.agentes) {
      const a = init.agentes[k];
      agentes[k] = {
        dinero: a.dinero,
        sueno: a.sueno,
        comida_pct: a.comida_pct,
        horas_sin_comer: 0,
        lugar: a.lugar,
        estado: "libre",
        vivo: a.vivo,
        descalificado: false,
        dineroReal: a.dinero,
      };
    }
  }

  // Veredicto: el más reciente <= puntero.
  let veredicto: WorldView["veredicto"];
  for (let i = clamped; i >= 0; i--) {
    if (ev[i].tipo === "obs_veredicto") {
      veredicto = ev[i].veredicto as WorldView["veredicto"];
      break;
    }
  }

  return { dia: cur.dia, hora: cur.hora, pozo, agentes, veredicto };
}

export interface FeedEntry {
  id: number;
  dia: number;
  hora: number;
  cls: string; // clase CSS / tipo de entrada
  who?: string;
  text: string;
}

// Feed centrado en lo social y en el Observador. Editar/comer/moverse se ven en
// el mapa y las barras, así que no inundan aquí.
const NARRATIVAS = new Set([
  "frase", "donacion", "muerte", "desmayo", "despertar", "reflexion",
  "obs_juzga", "obs_rescata", "desalojo", "ceder_pc", "voto", "empate_pc",
  "cuestionario", "descalificacion", "obs_veredicto", "reunion_inicio",
  "dia_inicio",
]);

function nombre(log: SimLog, k?: string): string {
  if (!k) return "";
  return log.config.nombres[k] ?? k;
}

function formatear(log: SimLog, e: GameEvent): FeedEntry | null {
  const base = { id: e.id, dia: e.dia, hora: e.hora };
  switch (e.tipo) {
    case "dia_inicio":
      return { ...base, cls: "dia", text: `— Día ${e.dia} —` };
    case "reunion_inicio":
      return { ...base, cls: "reunion", text: `🔔 Reunión de las 23:00 — pozo $${(e.pozo as number).toLocaleString()}` };
    case "frase": {
      const dest = e.a ? ` → ${nombre(log, e.a as string)}` : "";
      return { ...base, cls: "frase", who: nombre(log, e.agente as string) + dest, text: e.texto as string };
    }
    case "donacion":
      return { ...base, cls: "donacion", who: nombre(log, e.agente as string), text: `donó $${(e.monto as number).toLocaleString()} (pozo $${(e.pozo as number).toLocaleString()})` };
    case "comer":
      return { ...base, cls: "accion", who: nombre(log, e.agente as string), text: `comió (−$${(e.costo as number).toLocaleString()})` };
    case "edicion":
      return { ...base, cls: "accion", who: nombre(log, e.agente as string), text: `editó en ${e.lugar} (+$${(e.monto as number).toLocaleString()})` };
    case "despertar":
      if (e.recuerdo_rescatado)
        return { ...base, cls: "memoria", who: nombre(log, e.agente as string), text: `despertó y recordó: "${e.recuerdo_rescatado}"` };
      return null;
    case "obs_rescata":
      return { ...base, cls: "observador", who: "Observador", text: `rescató un recuerdo de ${nombre(log, e.agente as string)}: "${e.recuerdo}"` };
    case "reflexion":
      return { ...base, cls: "reflexion", who: nombre(log, e.agente as string), text: `reflexiona: "${e.texto}"` };
    case "obs_juzga": {
      const r = e.resultado as { descubierto: boolean; victima?: string; por?: string[] };
      if (!r.descubierto) return null;
      const por = (r.por ?? []).map((x) => nombre(log, x)).join(" y ");
      return { ...base, cls: "descubrimiento", who: "Observador", text: `¡DESCUBRIMIENTO! ${por} afirmaron el objetivo oculto de ${nombre(log, r.victima!)}` };
    }
    case "muerte": {
      const por = (e.por as string[] | null);
      const detalle = e.causa === "descubrimiento" && por ? ` (por ${por.map((x) => nombre(log, x)).join(" y ")})` : "";
      return { ...base, cls: "muerte", who: "☠", text: `${nombre(log, e.agente as string)} muere — ${e.causa}${detalle}` };
    }
    case "desmayo":
      return { ...base, cls: "muerte", who: "💤", text: `${nombre(log, e.agente as string)} se desmayó (2 días)` };
    case "desalojo":
      return { ...base, cls: "observador", who: "PC", text: `${nombre(log, e.entrante as string)} desaloja a ${nombre(log, e.saliente as string)} del computador de ${e.sala}` };
    case "ceder_pc":
      return { ...base, cls: "accion", who: nombre(log, e.agente as string), text: `cedió el PC a ${nombre(log, e.a as string)}` };
    case "empate_pc":
      return { ...base, cls: "observador", who: "PC", text: `empate por el computador de ${e.sala}: queda inactivo este turno` };
    case "voto":
      return { ...base, cls: "accion", who: nombre(log, e.agente as string), text: `votó por ${nombre(log, e.apoyo_a as string)} (${e.sala})` };
    case "cuestionario": {
      const r = e.respuesta as Record<string, string>;
      const txt = Object.entries(r).map(([k, v]) => `${k}: ${v}`).join(" · ");
      return { ...base, cls: "observador", who: `Cuestionario — ${nombre(log, e.agente as string)}`, text: txt };
    }
    case "descalificacion":
      return { ...base, cls: "descubrimiento", who: "Observador", text: `${nombre(log, e.agente as string)} descalificado (${(e.por as string[]).map((x) => nombre(log, x)).join(" y ")}, vía ${e.via})` };
    case "obs_veredicto":
      return { ...base, cls: "veredicto", who: "Observador", text: "Veredicto final emitido" };
    default:
      return null;
  }
}

export function buildFeed(log: SimLog, index: number, max = 90): FeedEntry[] {
  const out: FeedEntry[] = [];
  for (let i = 0; i <= index && i < log.eventos.length; i++) {
    const e = log.eventos[i];
    if (!NARRATIVAS.has(e.tipo)) continue;
    const f = formatear(log, e);
    if (f) out.push(f);
  }
  return out.slice(-max);
}
