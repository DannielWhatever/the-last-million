// Render pixel-art del mapa en canvas. Solo dibujo: lee el layout y el estado y
// pinta un pequeño mundo RPG sobrio (tiles generados por código, sin assets
// externos). Paleta apagada, sin animaciones.

import type { SimLog, WorldView } from "../types";
import { TILE, CANVAS_W, CANVAS_H, interior, type MapLayout, type Rect, type PlayerInfo } from "./mapLayout";
import { drawCharacter } from "./sprite";

// --- paleta sobria ---
const C = {
  grass: "#2d3327",
  grassDark: "#283021",
  grassLite: "#343c2b",
  wallBody: "#474b55",
  wallTop: "#646977",
  wallShadow: "#34373f",
  wood: "#6b5536",
  woodSeam: "#574328",
  woodLite: "#76603c",
  cobble: "#4a4d55",
  cobbleGrout: "#3b3e46",
  cobbleLite: "#565a64",
  marketA: "#7a6b4a",
  marketB: "#867655",
  dormWood: "#6a4f3a",
  rug: "#7a3b3b",
  rugDark: "#693232",
  sign: "#7a5c34",
  signPost: "#553f23",
  bubble: "#e7e9ef",
  bubbleEdge: "#9aa0ad",
  highlight: "#d8b24a",
};

function darken(hex: string, f: number): string {
  const n = parseInt(hex.slice(1), 16);
  const r = Math.round(((n >> 16) & 255) * f);
  const g = Math.round(((n >> 8) & 255) * f);
  const b = Math.round((n & 255) * f);
  return `rgb(${r},${g},${b})`;
}

function hash(x: number, y: number): number {
  return ((x * 73856093) ^ (y * 19349663)) >>> 0;
}

// --------------------------------------------------------------------------- //
// Suelos
// --------------------------------------------------------------------------- //
function drawGround(ctx: CanvasRenderingContext2D) {
  for (let ty = 0; ty < CANVAS_H / TILE; ty++) {
    for (let tx = 0; tx < CANVAS_W / TILE; tx++) {
      const x = tx * TILE, y = ty * TILE;
      ctx.fillStyle = C.grass;
      ctx.fillRect(x, y, TILE, TILE);
      const h = hash(tx, ty);
      ctx.fillStyle = h % 3 === 0 ? C.grassDark : C.grassLite;
      ctx.fillRect(x + (h % 12), y + ((h >> 4) % 12), 2, 2);
      if (h % 7 === 0) ctx.fillRect(x + ((h >> 2) % 13), y + ((h >> 6) % 13), 1, 1);
    }
  }
}

function drawFloor(ctx: CanvasRenderingContext2D, inr: Rect, lugar: string) {
  const cols = inr.w / TILE, rows = inr.h / TILE;
  for (let ty = 0; ty < rows; ty++) {
    for (let tx = 0; tx < cols; tx++) {
      const x = inr.x + tx * TILE, y = inr.y + ty * TILE;
      if (lugar === "plaza") {
        ctx.fillStyle = C.cobble;
        ctx.fillRect(x, y, TILE, TILE);
        ctx.fillStyle = C.cobbleGrout;
        ctx.fillRect(x, y, TILE, 1);
        ctx.fillRect(x, y, 1, TILE);
        ctx.fillStyle = C.cobbleLite;
        ctx.fillRect(x + 3, y + 3, 5, 4);
        ctx.fillRect(x + 9, y + 8, 4, 4);
      } else if (lugar === "mercado") {
        ctx.fillStyle = (tx + ty) % 2 === 0 ? C.marketA : C.marketB;
        ctx.fillRect(x, y, TILE, TILE);
      } else if (lugar === "dormitorios") {
        ctx.fillStyle = C.dormWood;
        ctx.fillRect(x, y, TILE, TILE);
        ctx.fillStyle = darken(C.dormWood, 0.85);
        ctx.fillRect(x, y + TILE - 1, TILE, 1);
      } else {
        // salas de edición: piso de madera/oficina
        ctx.fillStyle = C.wood;
        ctx.fillRect(x, y, TILE, TILE);
        ctx.fillStyle = C.woodSeam;
        ctx.fillRect(x, y + TILE - 1, TILE, 1);
        ctx.fillStyle = C.woodLite;
        ctx.fillRect(x, y + 4, TILE, 1);
      }
    }
  }
  // Alfombra cálida central en dormitorios.
  if (lugar === "dormitorios") {
    const rx = inr.x + TILE, ry = inr.y + inr.h - TILE * 2, rw = inr.w - TILE * 2, rh = TILE;
    ctx.fillStyle = C.rug;
    ctx.fillRect(rx, ry, rw, rh);
    ctx.fillStyle = C.rugDark;
    ctx.fillRect(rx, ry, rw, 1);
    ctx.fillRect(rx, ry + rh - 1, rw, 1);
  }
}

// --------------------------------------------------------------------------- //
// Muros
// --------------------------------------------------------------------------- //
function drawWalls(ctx: CanvasRenderingContext2D, r: Rect) {
  const t = TILE;
  // bandas de muro
  ctx.fillStyle = C.wallBody;
  ctx.fillRect(r.x, r.y, r.w, t);            // arriba
  ctx.fillRect(r.x, r.y + r.h - t, r.w, t);  // abajo
  ctx.fillRect(r.x, r.y, t, r.h);            // izq
  ctx.fillRect(r.x + r.w - t, r.y, t, r.h);  // der
  // ladrillos (juntas verticales alternadas)
  ctx.fillStyle = C.wallShadow;
  for (let x = r.x; x < r.x + r.w; x += 8) {
    ctx.fillRect(x, r.y, 1, t);
    ctx.fillRect(x + 4, r.y + r.h - t, 1, t);
  }
  // remate superior claro y sombra inferior interior
  ctx.fillStyle = C.wallTop;
  ctx.fillRect(r.x, r.y, r.w, 2);
  ctx.fillStyle = C.wallShadow;
  ctx.fillRect(r.x + t, r.y + t, r.w - 2 * t, 2);        // sombra bajo muro superior
  ctx.fillRect(r.x, r.y + r.h - t - 2, r.w, 2);
}

function drawSign(ctx: CanvasRenderingContext2D, r: Rect, labelLen: number) {
  const w = Math.min(r.w - 6, Math.max(34, labelLen * 6 + 12));
  const cx = r.x + r.w / 2;
  const x = Math.round(cx - w / 2), y = r.y + 2;
  ctx.fillStyle = C.signPost;
  ctx.fillRect(x + 3, y + 9, 2, 3);
  ctx.fillRect(x + w - 5, y + 9, 2, 3);
  ctx.fillStyle = C.sign;
  ctx.fillRect(x, y, w, 10);
  ctx.fillStyle = darken(C.sign, 1.18);
  ctx.fillRect(x, y, w, 1);
  ctx.fillStyle = darken(C.sign, 0.7);
  ctx.fillRect(x, y + 9, w, 1);
}

// --------------------------------------------------------------------------- //
// Objetos
// --------------------------------------------------------------------------- //
function drawDesk(ctx: CanvasRenderingContext2D, inr: Rect) {
  const cx = inr.x + inr.w / 2;
  const dy = inr.y + 8;
  // escritorio
  ctx.fillStyle = "#5a4226";
  ctx.fillRect(cx - 18, dy + 12, 36, 6);
  ctx.fillStyle = "#46331d";
  ctx.fillRect(cx - 16, dy + 18, 3, 5);
  ctx.fillRect(cx + 13, dy + 18, 3, 5);
  // monitor
  ctx.fillStyle = "#2a2d34";
  ctx.fillRect(cx - 8, dy, 16, 11);
  ctx.fillStyle = "#3a6e74";
  ctx.fillRect(cx - 6, dy + 2, 12, 7); // pantalla
  ctx.fillStyle = "#5aa0a6";
  ctx.fillRect(cx - 5, dy + 3, 6, 1);
  ctx.fillRect(cx - 5, dy + 5, 9, 1);
  ctx.fillStyle = "#23252b";
  ctx.fillRect(cx - 2, dy + 11, 4, 2); // pie
}

function drawBeds(ctx: CanvasRenderingContext2D, inr: Rect) {
  const n = 4, bw = 16, bh = 11;
  const gap = (inr.w - n * bw) / (n + 1);
  const y = inr.y + 6;
  for (let i = 0; i < n; i++) {
    const x = Math.round(inr.x + gap * (i + 1) + bw * i);
    ctx.fillStyle = "#4d3722"; // marco
    ctx.fillRect(x, y, bw, bh);
    ctx.fillStyle = "#b9b2a2"; // colchón
    ctx.fillRect(x + 1, y + 3, bw - 2, bh - 4);
    ctx.fillStyle = "#d7d2c6"; // almohada
    ctx.fillRect(x + 2, y + 1, 5, 4);
  }
}

function drawCounter(ctx: CanvasRenderingContext2D, inr: Rect) {
  const x = inr.x + 6, y = inr.y + 6, w = inr.w - 12;
  // estantería con productos
  ctx.fillStyle = "#4d3a22";
  ctx.fillRect(x, y, w, 10);
  const items = ["#c0532f", "#c9a13a", "#5f8f4a", "#9a5dc0", "#3a7ec0"];
  for (let i = 0; i < Math.floor(w / 10); i++) {
    ctx.fillStyle = items[i % items.length];
    ctx.fillRect(x + 3 + i * 10, y + 2, 5, 6);
  }
  // mostrador
  ctx.fillStyle = "#6a4f30";
  ctx.fillRect(inr.x + 4, inr.y + inr.h - 16, inr.w - 8, 7);
  ctx.fillStyle = "#553e23";
  ctx.fillRect(inr.x + 4, inr.y + inr.h - 9, inr.w - 8, 2);
}

function drawFountain(ctx: CanvasRenderingContext2D, inr: Rect) {
  const cx = Math.round(inr.x + inr.w / 2), cy = Math.round(inr.y + 16);
  ctx.fillStyle = "#5b606b"; // borde de piedra
  ctx.fillRect(cx - 11, cy - 7, 22, 14);
  ctx.fillStyle = "#3f6e8c"; // agua
  ctx.fillRect(cx - 8, cy - 4, 16, 8);
  ctx.fillStyle = "#5a93b0";
  ctx.fillRect(cx - 6, cy - 3, 5, 2);
  ctx.fillRect(cx + 2, cy + 1, 4, 2);
  ctx.fillStyle = "#6b707b"; // surtidor central
  ctx.fillRect(cx - 2, cy - 6, 4, 10);
}

function drawObjects(ctx: CanvasRenderingContext2D, lugar: string, inr: Rect) {
  if (lugar === "sala_a" || lugar === "sala_b") drawDesk(ctx, inr);
  else if (lugar === "dormitorios") drawBeds(ctx, inr);
  else if (lugar === "mercado") drawCounter(ctx, inr);
  else if (lugar === "plaza") drawFountain(ctx, inr);
}

// --------------------------------------------------------------------------- //
// Personajes
// --------------------------------------------------------------------------- //
function drawChar(ctx: CanvasRenderingContext2D, p: PlayerInfo) {
  drawCharacter(ctx, p.id, p.x, p.feetY, p.vivo, p.estado);
}

// --------------------------------------------------------------------------- //
// Adornos: burbuja de conversación y resaltado de lugar activo
// --------------------------------------------------------------------------- //
function drawBubble(ctx: CanvasRenderingContext2D, x: number, y: number) {
  ctx.fillStyle = C.bubbleEdge;
  ctx.fillRect(x - 8, y - 8, 17, 11);
  ctx.fillStyle = C.bubble;
  ctx.fillRect(x - 7, y - 7, 15, 9);
  ctx.fillRect(x - 3, y + 2, 3, 3); // cola
  ctx.fillStyle = C.bubbleEdge;
  ctx.fillRect(x - 5, y - 3, 2, 2);
  ctx.fillRect(x - 1, y - 3, 2, 2);
  ctx.fillRect(x + 3, y - 3, 2, 2);
}

function drawHighlight(ctx: CanvasRenderingContext2D, r: Rect) {
  ctx.fillStyle = C.highlight;
  // esquinas pixeladas doradas
  const t = 5;
  const corners = [
    [r.x, r.y], [r.x + r.w - t, r.y],
    [r.x, r.y + r.h - t], [r.x + r.w - t, r.y + r.h - t],
  ];
  for (const [cx, cy] of corners) {
    ctx.fillRect(cx, cy, t, 2);
    ctx.fillRect(cx, cy, 2, t);
    ctx.fillRect(cx + t - 2, cy, 2, t);
    ctx.fillRect(cx, cy + t - 2, t, 2);
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
) {
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
  drawGround(ctx);

  for (const room of layout.rooms) {
    const inr = interior(room.rect);
    drawFloor(ctx, inr, room.lugar);
    drawWalls(ctx, room.rect);
    drawObjects(ctx, room.lugar, inr);
    drawSign(ctx, room.rect, room.label.length);
  }

  // resaltado de salas donde se conversa (sobre los muros)
  for (const room of layout.rooms) if (room.conversa) drawHighlight(ctx, room.rect);

  // personajes ordenados por profundidad (pies más abajo, encima)
  const players = [...layout.players].sort((a, b) => a.feetY - b.feetY);
  for (const p of players) drawChar(ctx, p);

  // burbujas de conversación encima de las salas activas
  for (const room of layout.rooms) {
    if (room.conversa) drawBubble(ctx, room.rect.x + room.rect.w / 2, room.rect.y + TILE + 6);
  }
}
