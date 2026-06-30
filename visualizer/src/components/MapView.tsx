import { useEffect, useMemo, useRef } from "react";
import type { SimLog, WorldView } from "../types";
import { COLOR_AGENTE } from "../theme";
import { CANVAS_W, CANVAS_H, computeLayout } from "../map/mapLayout";
import { drawWorld } from "../map/mapRenderer";
import { sheet } from "../map/spriteSheet";
import { mapImg } from "../map/mapImage";
import { useAssetsReady } from "../map/assets";

// Mapa del mundo: la imagen mapa_v1.png de fondo con los Player dibujados encima
// en un canvas (§18). Los rótulos de los lugares ya vienen en la imagen; solo se
// superponen en HTML los nombres de los Player para que queden nítidos.
export function MapView({ log, world }: { log: SimLog; world: WorldView }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const layout = useMemo(() => computeLayout(log, world), [log, world]);
  const ready = useAssetsReady(sheet, mapImg);

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    drawWorld(ctx, log, world, layout, mapImg.get());
  }, [log, world, layout, ready]);

  const pct = (x: number, total: number) => `${(x / total) * 100}%`;

  return (
    <div className="mapa-wrap" style={{ aspectRatio: `${CANVAS_W} / ${CANVAS_H}` }}>
      <canvas ref={canvasRef} width={CANVAS_W} height={CANVAS_H} className="mapa-canvas" />
      <div className="mapa-overlay">
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
