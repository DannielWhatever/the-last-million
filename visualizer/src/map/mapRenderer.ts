// Render del mapa: pinta la imagen de fondo (mapa_v1.png) y coloca encima a los
// Player, más los adornos (resaltado de salas donde se conversa y burbujas). El
// dibujo de cada personaje vive en sprite.ts; el layout (rectángulos de salas y
// posiciones) en mapLayout. Aquí no se generan tiles: el mundo es la imagen.

import type { SimLog, WorldView } from "../types";
import { CANVAS_W, CANVAS_H, SPRITE_H, type MapLayout, type Rect, type PlayerInfo } from "./mapLayout";
import { drawCharacter } from "./sprite";

const C = {
  bubble: "#e7e9ef",
  bubbleEdge: "#9aa0ad",
  highlight: "#d8b24a",
  fallback: "#2d3327",
};

// --------------------------------------------------------------------------- //
// Personajes
// --------------------------------------------------------------------------- //
function drawChar(ctx: CanvasRenderingContext2D, p: PlayerInfo) {
  drawCharacter(ctx, p.id, p.x, p.feetY, p.vivo, p.estado, SPRITE_H);
}

// --------------------------------------------------------------------------- //
// Adornos: burbuja de conversación y resaltado de sala activa
// (dimensiones a escala de la imagen grande, ~1488×716)
// --------------------------------------------------------------------------- //
function drawBubble(ctx: CanvasRenderingContext2D, x: number, y: number) {
  ctx.fillStyle = C.bubbleEdge;
  ctx.fillRect(x - 24, y - 24, 51, 33);
  ctx.fillStyle = C.bubble;
  ctx.fillRect(x - 21, y - 21, 45, 27);
  ctx.fillRect(x - 9, y + 6, 9, 9); // cola
  ctx.fillStyle = C.bubbleEdge;
  ctx.fillRect(x - 15, y - 9, 6, 6);
  ctx.fillRect(x - 3, y - 9, 6, 6);
  ctx.fillRect(x + 9, y - 9, 6, 6);
}

function drawHighlight(ctx: CanvasRenderingContext2D, r: Rect) {
  ctx.fillStyle = C.highlight;
  const t = 16, w = 4; // largo y grosor de las esquinas doradas
  const corners = [
    [r.x, r.y], [r.x + r.w - t, r.y],
    [r.x, r.y + r.h - t], [r.x + r.w - t, r.y + r.h - t],
  ];
  for (const [cx, cy] of corners) {
    ctx.fillRect(cx, cy, t, w);
    ctx.fillRect(cx, cy, w, t);
    ctx.fillRect(cx + t - w, cy, w, t);
    ctx.fillRect(cx, cy + t - w, t, w);
  }
}

// --------------------------------------------------------------------------- //
// Render principal
// --------------------------------------------------------------------------- //
export function drawWorld(
  ctx: CanvasRenderingContext2D,
  _log: SimLog,
  _world: WorldView,
  layout: MapLayout,
  mapImage: HTMLImageElement | null,
) {
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);

  // Fondo: la imagen del mapa (o un verde liso mientras carga).
  if (mapImage) {
    ctx.drawImage(mapImage, 0, 0, CANVAS_W, CANVAS_H);
  } else {
    ctx.fillStyle = C.fallback;
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
  }

  // resaltado de salas donde se conversa
  for (const room of layout.rooms) if (room.conversa) drawHighlight(ctx, room.rect);

  // personajes ordenados por profundidad (pies más abajo, encima)
  const players = [...layout.players].sort((a, b) => a.feetY - b.feetY);
  for (const p of players) drawChar(ctx, p);

  // burbujas de conversación en la parte alta de las salas activas
  for (const room of layout.rooms) {
    if (room.conversa) drawBubble(ctx, room.rect.x + room.rect.w / 2, room.rect.y + 96);
  }
}
