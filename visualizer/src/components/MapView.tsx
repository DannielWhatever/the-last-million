import { useEffect, useMemo, useRef } from "react";
import type { SimLog, WorldView } from "../types";
import { COLOR_AGENTE } from "../theme";
import { CANVAS_W, CANVAS_H, computeLayout } from "../map/mapLayout";
import { drawWorld } from "../map/mapRenderer";

// Mapa del mundo como un pequeño RPG pixel-art (§18.2/§18.3). Mismo layout, mismos
// lugares y mismos datos que antes: solo cambia el render. El texto (carteles y
// nombres) va en un overlay HTML para que quede nítido y no pixelado.
export function MapView({ log, world }: { log: SimLog; world: WorldView }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const layout = useMemo(() => computeLayout(log, world), [log, world]);

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    drawWorld(ctx, log, world, layout);
  }, [log, world, layout]);

  const pct = (x: number, total: number) => `${(x / total) * 100}%`;

  return (
    <div className="mapa-wrap" style={{ aspectRatio: `${CANVAS_W} / ${CANVAS_H}` }}>
      <canvas ref={canvasRef} width={CANVAS_W} height={CANVAS_H} className="mapa-canvas" />
      <div className="mapa-overlay">
        {layout.rooms.map((room) => (
          <span
            key={room.lugar}
            className="lugar-cartel"
            style={{
              left: pct(room.rect.x + room.rect.w / 2, CANVAS_W),
              top: pct(room.rect.y + 7, CANVAS_H),
            }}
          >
            {room.label}
          </span>
        ))}
        {layout.players.map((p) => (
          <span
            key={p.id}
            className={`player-tag ${p.vivo ? "" : "muerto"}`}
            style={{
              left: pct(p.x, CANVAS_W),
              top: pct(p.headTopY - 4, CANVAS_H),
              color: p.vivo ? COLOR_AGENTE[p.id] : "#9aa0ad",
            }}
          >
            {p.name}
          </span>
        ))}
      </div>
    </div>
  );
}
