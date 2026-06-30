// Lámina de sprites de los Player y recorte (bbox) de cada uno.
// La imagen es un único PNG con los 4 personajes en fila; de izquierda a
// derecha: ana, beto, carla, gabriel. El dibujo en sí está en sprite.ts.

import { loadImage, type ImageAsset } from "./assets";

export interface Frame {
  sx: number;
  sy: number;
  sw: number;
  sh: number;
}

// --- lámina activa (sprites_v3) -------------------------------------------- //
// Recuadros dentro de sprites_v3.png (1024×1024, fondo recortado a transparente).
// `sx/sw` es el recorte horizontal propio de cada figura; `sy/sh` es una banda
// vertical común (mismo techo y misma línea de pies) para que el cuerpo conserve
// la misma escala y se alineen los pies al dibujarlos.
export const sheet: ImageAsset = loadImage("sprites_v3.png");
const FEET_BASE = 907;
const TOP_BASE = 340;
const FRAME_X: Record<string, [number, number]> = {
  ana: [92, 184],
  beto: [296, 200],
  carla: [548, 200],
  gabriel: [776, 184],
};

// --- alternativa: sprites_v2 (por si volvemos a ella) ---------------------- //
// Para revolver a la lámina anterior, cambia el loadImage de arriba a
// "sprites_v2.png" y usa estos valores:
//   FEET_BASE = 691; TOP_BASE = 282;
//   ana:[190,264] beto:[476,265] carla:[803,248] gabriel:[1082,271]

const SH = FEET_BASE - TOP_BASE; // alto de banda común

export const FRAMES: Record<string, Frame> = Object.fromEntries(
  Object.entries(FRAME_X).map(([id, [sx, sw]]) => [id, { sx, sy: TOP_BASE, sw, sh: SH }]),
);

// Alto de referencia (= SH) para escalar todos los personajes con el mismo
// factor: así las diferencias reales de estatura se conservan.
export const SHEET_REF_H = SH;

// Devuelve la imagen si ya cargó; si no, null (se usa el respaldo).
export function getSheet(): HTMLImageElement | null {
  return sheet.get();
}
