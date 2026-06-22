import { useEffect, useRef } from "react";
import { drawCharacter } from "../map/sprite";

// Sprite del Player dibujado en un canvas pequeño (mismo dibujo que el mapa).
// Reemplaza el cuadrito de color en el panel lateral. `scale` agranda el
// pixel-art sin difuminarlo (image-rendering: pixelated).
const W = 22;
const H = 26;

export function Sprite({
  id, vivo, estado, scale = 1,
}: {
  id: string;
  vivo: boolean;
  estado: string;
  scale?: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, W, H);
    drawCharacter(ctx, id, W / 2, H - 2, vivo, estado);
  }, [id, vivo, estado]);

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
