import { useEffect, useRef } from "react";
import { drawCharacter } from "../map/sprite";
import { sheet } from "../map/spriteSheet";
import { useAssetsReady } from "../map/assets";

// Sprite del Player dibujado en un canvas pequeño (mismo dibujo que el mapa).
// Reemplaza el cuadrito de color en el panel lateral. `scale` agranda el
// pixel-art sin difuminarlo (image-rendering: pixelated). El canvas deja
// holgura arriba para la figura completa y el adorno de dormir (zZ).
const W = 24;
const H = 34;
const FIG_H = 24; // alto de la figura dentro del canvas

export function Sprite({
  id, vivo, estado, scale = 1,
}: {
  id: string;
  vivo: boolean;
  estado: string;
  scale?: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const sheetReady = useAssetsReady(sheet);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, W, H);
    drawCharacter(ctx, id, W / 2, H - 3, vivo, estado, FIG_H);
  }, [id, vivo, estado, sheetReady]);

  return (
    <canvas
      ref={ref}
      width={W}
      height={H}
      className="player-sprite"
      style={{ width: W * scale, height: H * scale, imageRendering: "pixelated" }}
    />
  );
}
