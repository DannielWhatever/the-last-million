// Smoke test del render: ejecuta drawWorld contra un contexto-canvas simulado
// para confirmar que no lanza excepciones ni genera coordenadas NaN. También
// ejercita derive.ts con el log real. No reemplaza la inspección visual.
import fs from "node:fs";
import { buildIndex, deriveWorld } from "../src/derive";
import { computeLayout } from "../src/map/mapLayout";
import { drawWorld } from "../src/map/mapRenderer";
import type { SimLog } from "../src/types";

const log: SimLog = JSON.parse(fs.readFileSync("public/log.json", "utf-8"));
const idx = buildIndex(log);

let fillRects = 0;
let clears = 0;
const ctx: any = {
  imageSmoothingEnabled: false,
  fillStyle: "#000",
  clearRect() { clears++; },
  fillRect(x: number, y: number, w: number, h: number) {
    if ([x, y, w, h].some((n) => Number.isNaN(n) || !Number.isFinite(n))) {
      throw new Error(`fillRect con valor inválido: ${x},${y},${w},${h}`);
    }
    fillRects++;
  },
};

const puntos = [0, Math.floor(log.eventos.length / 2), log.eventos.length - 1];
let players = 0;
let rooms = 0;
for (const i of puntos) {
  const world = deriveWorld(log, i, idx);
  const layout = computeLayout(log, world);
  players += layout.players.length;
  rooms = layout.rooms.length;
  drawWorld(ctx, log, world, layout);
}
console.log("OK smoke render:", { fillRects, clears, rooms, playersAcum: players, eventos: log.eventos.length });
