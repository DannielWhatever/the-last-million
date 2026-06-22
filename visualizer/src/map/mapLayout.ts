// Layout del mapa en coordenadas lógicas (pixel-art). NO cambia la lógica del
// experimento: solo traduce el mismo conjunto de lugares/players de antes a
// posiciones en un lienzo para dibujarlos como un pequeño mundo RPG.

import type { SimLog, WorldView } from "../types";
import { LUGAR_POS } from "../theme";

export const TILE = 16;
const ROOM_W = 10; // tiles (exterior, incl. muros)
const ROOM_H = 7;
const GAP = 2;
const MARGIN = 1;

export const CANVAS_W = (MARGIN + 3 * ROOM_W + 2 * GAP + MARGIN) * TILE; // 576
export const CANVAS_H = (MARGIN + 2 * ROOM_H + 1 * GAP + MARGIN) * TILE; // 288

export interface Rect { x: number; y: number; w: number; h: number; }

export function roomRect(col: number, row: number): Rect {
  return {
    x: (MARGIN + (col - 1) * (ROOM_W + GAP)) * TILE,
    y: (MARGIN + (row - 1) * (ROOM_H + GAP)) * TILE,
    w: ROOM_W * TILE,
    h: ROOM_H * TILE,
  };
}

export function interior(r: Rect): Rect {
  return { x: r.x + TILE, y: r.y + TILE, w: r.w - 2 * TILE, h: r.h - 2 * TILE };
}

export interface RoomInfo {
  lugar: string;
  label: string;
  rect: Rect;
  conversa: boolean;
}

export interface PlayerInfo {
  id: string;
  name: string;
  lugar: string;
  estado: string;
  vivo: boolean;
  x: number; // centro (pies) en px lógicos
  feetY: number;
  headTopY: number;
}

export interface MapLayout {
  rooms: RoomInfo[];
  players: PlayerInfo[];
}

export function computeLayout(log: SimLog, world: WorldView): MapLayout {
  const porLugar: Record<string, string[]> = {};
  for (const l of log.config.lugares) porLugar[l] = [];
  for (const a of log.config.agentes) {
    const ag = world.agentes[a];
    if (!ag) continue;
    (porLugar[ag.lugar] ??= []).push(a);
  }

  const rooms: RoomInfo[] = [];
  const players: PlayerInfo[] = [];

  for (const lugar of log.config.lugares) {
    const pos = LUGAR_POS[lugar] ?? { col: 1, row: 1, label: lugar };
    const rect = roomRect(pos.col, pos.row);
    const ocupantes = porLugar[lugar] ?? [];
    const vivosPresentes = ocupantes.filter(
      (a) => world.agentes[a]?.vivo && world.agentes[a]?.estado !== "en_transito",
    );
    rooms.push({ lugar, label: pos.label, rect, conversa: vivosPresentes.length >= 2 });

    // Players alineados en una fila en la mitad-baja del interior.
    const inr = interior(rect);
    const n = ocupantes.length;
    ocupantes.forEach((a, i) => {
      const ag = world.agentes[a];
      const cx = inr.x + (inr.w * (i + 1)) / (n + 1);
      const feetY = inr.y + inr.h * 0.66;
      players.push({
        id: a,
        name: log.config.nombres[a] ?? a,
        lugar,
        estado: ag.estado,
        vivo: ag.vivo,
        x: Math.round(cx),
        feetY: Math.round(feetY),
        headTopY: Math.round(feetY - 16),
      });
    });
  }

  return { rooms, players };
}
