// Dibujo del personaje de cada Player. Compartido por el mapa (mapRenderer) y el
// panel lateral (componente Sprite), para que el sprite sea idéntico en ambos
// sitios. Si la lámina de sprites ya cargó, se dibuja la figura desde la imagen;
// si no, se usa un personaje pixel-art de respaldo. La sombra, la lápida (muerto)
// y los adornos de estado (zZ al dormir, polvo en tránsito) se dibujan por código
// y escalan con `targetH`.

import { COLOR_AGENTE, GENERO_AGENTE, PELO_AGENTE } from "../theme";
import { FRAMES, SHEET_REF_H, getSheet } from "./spriteSheet";

const PIEL = "#d9a86c";
const PELO_DEFECTO = "#3a2e22";
const PIERNAS = "#2f3340";
const OJO = "#22242c";
const SOMBRA = "rgba(0,0,0,0.28)";

// Alto de diseño de los elementos procedurales (sombra, lápida, cuerpo de
// respaldo, adornos). Todo se dibuja en coordenadas locales con los pies en el
// origen y luego se escala por `targetH / BASE_H`.
const BASE_H = 26;

function darken(hex: string, f: number): string {
  const n = parseInt(hex.slice(1), 16);
  const r = Math.round(((n >> 16) & 255) * f);
  const g = Math.round(((n >> 8) & 255) * f);
  const b = Math.round((n & 255) * f);
  return `rgb(${r},${g},${b})`;
}

// "Z" pixel-art (cuadrada, lado `size`): barra superior, diagonal ↙ y barra
// inferior. Usa el fillStyle activo.
function drawZ(ctx: CanvasRenderingContext2D, x: number, y: number, size: number): void {
  ctx.fillRect(x, y, size, 1);
  ctx.fillRect(x, y + size - 1, size, 1);
  for (let k = 1; k < size - 1; k++) {
    ctx.fillRect(x + (size - 1) - k, y + k, 1, 1);
  }
}

// Adornos de estado en coordenadas locales (origen = pies). `headTop` es la Y
// local del techo de la cabeza (negativa).
function drawEstado(ctx: CanvasRenderingContext2D, headTop: number, estado: string): void {
  if (estado === "durmiendo") {
    const zx = 2, zy = headTop - 8, s = 7;
    ctx.fillStyle = "rgba(0,0,0,0.5)";
    drawZ(ctx, zx + 1, zy + 1, s); // sombra/borde
    ctx.fillStyle = "#ffffff";
    drawZ(ctx, zx, zy, s);
  } else if (estado === "en_transito") {
    ctx.fillStyle = "#cfd6e6";
    ctx.fillRect(5, headTop + 1, 1, 5);
    ctx.fillRect(6, headTop + 2, 1, 3);
    ctx.fillRect(7, headTop + 3, 1, 1);
  }
}

// Cuerpo pixel-art de respaldo (coordenadas locales, origen = pies), usado solo
// mientras la lámina no ha cargado.
function drawProcedural(ctx: CanvasRenderingContext2D, id: string): void {
  const color = COLOR_AGENTE[id] ?? "#888";
  const pelo = PELO_AGENTE[id] ?? PELO_DEFECTO;
  const mujer = (GENERO_AGENTE[id] ?? "m") === "f";
  const headTop = -16, bodyTop = -10;

  if (mujer) {
    for (let i = 0; i < 4; i++) {
      const w = 8 + i * 2;
      ctx.fillStyle = i >= 2 ? darken(color, 0.82) : color;
      ctx.fillRect(Math.round(-w / 2), -5 + i, w, 1);
    }
    ctx.fillStyle = PIEL;
    ctx.fillRect(-2, -2, 1, 2);
    ctx.fillRect(1, -2, 1, 2);
    ctx.fillStyle = color;
    ctx.fillRect(-4, bodyTop, 8, 5);
  } else {
    ctx.fillStyle = PIERNAS;
    ctx.fillRect(-3, -4, 2, 4);
    ctx.fillRect(1, -4, 2, 4);
    ctx.fillStyle = color;
    ctx.fillRect(-4, bodyTop, 8, 6);
    ctx.fillStyle = darken(color, 0.72);
    ctx.fillRect(-4, bodyTop + 4, 8, 2);
  }

  ctx.fillStyle = darken(color, 0.85);
  ctx.fillRect(-5, bodyTop + 1, 1, 4);
  ctx.fillRect(4, bodyTop + 1, 1, 4);
  ctx.fillStyle = PIEL;
  ctx.fillRect(-3, headTop, 6, 6);
  ctx.fillStyle = pelo;
  ctx.fillRect(-3, headTop, 6, 2);
  if (mujer) {
    ctx.fillRect(-4, headTop, 1, 8);
    ctx.fillRect(3, headTop, 1, 8);
    ctx.fillRect(-3, headTop, 6, 3);
  }
  ctx.fillStyle = OJO;
  const eyeY = mujer ? headTop + 4 : headTop + 3;
  ctx.fillRect(-2, eyeY, 1, 1);
  ctx.fillRect(1, eyeY, 1, 1);
}

// Dibuja el sprite de `id` con los pies centrados en (cx, feetY). vivo=false pinta
// una lápida. `targetH` es el alto en px de la figura viva (de los pies hacia
// arriba): el mapa usa ~84, el panel lateral menos.
export function drawCharacter(
  ctx: CanvasRenderingContext2D,
  id: string,
  cx: number,
  feetY: number,
  vivo: boolean,
  estado: string,
  targetH = BASE_H,
): void {
  const s = targetH / BASE_H;

  // Sombra y lápida en coordenadas locales escaladas.
  ctx.save();
  ctx.translate(cx, feetY);
  ctx.scale(s, s);
  ctx.fillStyle = SOMBRA;
  ctx.fillRect(-4, -1, 8, 2);
  if (!vivo) {
    ctx.fillStyle = "#6b6f78";
    ctx.fillRect(-4, -12, 8, 12);
    ctx.fillRect(-3, -14, 6, 3);
    ctx.fillStyle = "#4a4e56";
    ctx.fillRect(-1, -10, 2, 7);
    ctx.fillRect(-3, -8, 6, 2);
    ctx.restore();
    return;
  }
  ctx.restore();

  const sheet = getSheet();
  const fr = FRAMES[id];
  if (sheet && fr) {
    // Figura desde la lámina (alto exacto = targetH). Con remuestreo activado se
    // ve nítida al reducirla; es seguro porque cada figura tiene un margen
    // transparente amplio y no se cuela el vecino.
    const k = targetH / SHEET_REF_H;
    const dw = fr.sw * k, dh = fr.sh * k;
    const dx = cx - dw / 2, dy = feetY - dh;
    const prevSmooth = ctx.imageSmoothingEnabled;
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(sheet, fr.sx, fr.sy, fr.sw, fr.sh, dx, dy, dw, dh);
    ctx.imageSmoothingEnabled = prevSmooth;
    // Adornos sobre la cabeza (techo de la figura en local = -BASE_H).
    ctx.save();
    ctx.translate(cx, feetY);
    ctx.scale(s, s);
    drawEstado(ctx, -BASE_H, estado);
    ctx.restore();
    return;
  }

  // Respaldo procedural (mientras carga la lámina).
  ctx.save();
  ctx.translate(cx, feetY);
  ctx.scale(s, s);
  drawProcedural(ctx, id);
  drawEstado(ctx, -16, estado);
  ctx.restore();
}
