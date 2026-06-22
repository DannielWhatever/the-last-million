// Dibujo del personaje pixel-art de cada Player. Compartido por el mapa
// (mapRenderer) y el panel lateral (componente Sprite), para que el sprite sea
// idéntico en ambos sitios. Solo dibujo: recibe id, posición de los pies y
// estado, y pinta. Paleta apagada, sin assets externos.

import { COLOR_AGENTE, GENERO_AGENTE, PELO_AGENTE } from "../theme";

const PIEL = "#d9a86c";
const PELO_DEFECTO = "#3a2e22";
const PIERNAS = "#2f3340";
const OJO = "#22242c";
const SOMBRA = "rgba(0,0,0,0.28)";

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
  ctx.fillRect(x, y, size, 1);                       // barra superior
  ctx.fillRect(x, y + size - 1, size, 1);            // barra inferior
  for (let k = 1; k < size - 1; k++) {
    ctx.fillRect(x + (size - 1) - k, y + k, 1, 1);   // diagonal de arriba-dcha a abajo-izq
  }
}

// Dibuja el sprite de `id` con los pies centrados en (cx, feetY).
// vivo=false pinta una lápida. estado añade adornos (zZ al dormir, polvo en tránsito).
export function drawCharacter(
  ctx: CanvasRenderingContext2D,
  id: string,
  cx: number,
  feetY: number,
  vivo: boolean,
  estado: string,
): void {
  const fy = feetY, left = cx - 5;
  ctx.fillStyle = SOMBRA;
  ctx.fillRect(left + 1, fy - 1, 8, 2);

  if (!vivo) {
    // lápida
    ctx.fillStyle = "#6b6f78";
    ctx.fillRect(left + 1, fy - 12, 8, 12);
    ctx.fillRect(left + 2, fy - 14, 6, 3);
    ctx.fillStyle = "#4a4e56";
    ctx.fillRect(cx - 1, fy - 10, 2, 7);
    ctx.fillRect(cx - 3, fy - 8, 6, 2);
    return;
  }

  const color = COLOR_AGENTE[id] ?? "#888";
  const pelo = PELO_AGENTE[id] ?? PELO_DEFECTO;
  const mujer = (GENERO_AGENTE[id] ?? "m") === "f";
  const headTop = fy - 16, bodyTop = fy - 10;

  if (mujer) {
    // vestido con falda acampanada
    for (let i = 0; i < 4; i++) {
      const w = 8 + i * 2;
      ctx.fillStyle = i >= 2 ? darken(color, 0.82) : color;
      ctx.fillRect(Math.round(cx - w / 2), fy - 5 + i, w, 1);
    }
    // piernas cortas bajo la falda
    ctx.fillStyle = PIEL;
    ctx.fillRect(left + 3, fy - 2, 1, 2);
    ctx.fillRect(left + 6, fy - 2, 1, 2);
    // torso
    ctx.fillStyle = color;
    ctx.fillRect(left + 1, bodyTop, 8, 5);
  } else {
    // piernas
    ctx.fillStyle = PIERNAS;
    ctx.fillRect(left + 2, fy - 4, 2, 4);
    ctx.fillRect(left + 6, fy - 4, 2, 4);
    // cuerpo (camiseta = color del Player)
    ctx.fillStyle = color;
    ctx.fillRect(left + 1, bodyTop, 8, 6);
    ctx.fillStyle = darken(color, 0.72);
    ctx.fillRect(left + 1, bodyTop + 4, 8, 2);
  }

  // brazos
  ctx.fillStyle = darken(color, 0.85);
  ctx.fillRect(left, bodyTop + 1, 1, 4);
  ctx.fillRect(left + 9, bodyTop + 1, 1, 4);
  // cabeza
  ctx.fillStyle = PIEL;
  ctx.fillRect(left + 2, headTop, 6, 6);
  // pelo
  ctx.fillStyle = pelo;
  ctx.fillRect(left + 2, headTop, 6, 2);
  if (mujer) {
    // melena: laterales hasta los hombros + flequillo
    ctx.fillRect(left + 1, headTop, 1, 8);
    ctx.fillRect(left + 8, headTop, 1, 8);
    ctx.fillRect(left + 2, headTop, 6, 3);
  }
  // ojos (bajo el flequillo si es melena)
  ctx.fillStyle = OJO;
  const eyeY = mujer ? headTop + 4 : headTop + 3;
  ctx.fillRect(left + 3, eyeY, 1, 1);
  ctx.fillRect(left + 6, eyeY, 1, 1);

  if (estado === "durmiendo") {
    // "Z" grande de dormir, blanca con borde oscuro para que resalte.
    const zx = cx + 2, zy = headTop - 8, s = 7;
    ctx.fillStyle = "rgba(0,0,0,0.5)";
    drawZ(ctx, zx + 1, zy + 1, s);  // sombra/borde
    ctx.fillStyle = "#ffffff";
    drawZ(ctx, zx, zy, s);          // Z
  } else if (estado === "en_transito") {
    ctx.fillStyle = "#cfd6e6";
    ctx.fillRect(cx + 5, headTop + 1, 1, 5);
    ctx.fillRect(cx + 6, headTop + 2, 1, 3);
    ctx.fillRect(cx + 7, headTop + 3, 1, 1);
  }
}
