// Layout del mapa sobre la imagen de fondo (mapa_v1.png). NO cambia la lógica
// del experimento: solo traduce el mismo conjunto de lugares/players a posiciones
// en píxeles de la imagen para colocarlos encima. Los rectángulos de cada sala
// se midieron sobre mapa_v1.png (1488×716).

import type { SimLog, WorldView } from "../types";
import { LUGAR_POS } from "../theme";

// Tamaño nativo de la imagen del mapa (= tamaño del canvas lógico).
export const CANVAS_W = 1488;
export const CANVAS_H = 716;

// Alto en px con que se dibuja el sprite del Player sobre el mapa.
export const SPRITE_H = 84;

// Grosor aproximado de los muros, para meter a los Player dentro del suelo.
const WALL = 32;
// Fracción del alto interior donde quedan los pies (mitad-baja, sobre el suelo).
const FEET_FRAC = 0.6;

export interface Rect { x: number; y: number; w: number; h: number; }

// Rectángulos exteriores (muros incluidos) de cada lugar en píxeles de la imagen.
export const ROOM_RECTS: Record<string, Rect> = {
  sala_a: { x: 43, y: 37, w: 422, h: 297 },
  plaza: { x: 552, y: 37, w: 423, h: 297 },
  sala_b: { x: 1061, y: 37, w: 422, h: 297 },
  mercado: { x: 43, y: 417, w: 423, h: 298 },
  dormitorios: { x: 1061, y: 417, w: 422, h: 298 },
};

export function interior(r: Rect): Rect {
  return { x: r.x + WALL, y: r.y + WALL, w: r.w - 2 * WALL, h: r.h - 2 * WALL };
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
  x: number; // centro (pies) en px de la imagen
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
    const rect = ROOM_RECTS[lugar] ?? { x: 0, y: 0, w: 200, h: 200 };
    const label = LUGAR_POS[lugar]?.label ?? lugar;
    const ocupantes = porLugar[lugar] ?? [];
    const vivosPresentes = ocupantes.filter(
      (a) => world.agentes[a]?.vivo && world.agentes[a]?.estado !== "en_transito",
    );
    rooms.push({ lugar, label, rect, conversa: vivosPresentes.length >= 2 });

    // Players alineados en una fila en la mitad-baja del interior.
    const inr = interior(rect);
    const n = ocupantes.length;
    ocupantes.forEach((a, i) => {
      const ag = world.agentes[a];
      const cx = inr.x + (inr.w * (i + 1)) / (n + 1);
      const feetY = inr.y + inr.h * FEET_FRAC;
      players.push({
        id: a,
        name: log.config.nombres[a] ?? a,
        lugar,
        estado: ag.estado,
        vivo: ag.vivo,
        x: Math.round(cx),
        feetY: Math.round(feetY),
        headTopY: Math.round(feetY - SPRITE_H),
      });
    });
  }

  return { rooms, players };
}
