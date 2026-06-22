import type { SimLog, WorldView } from "../types";

// Pozo + reloj (§18.3): barra de progreso del bote común y día/hora actual.
export function Header({ log, world }: { log: SimLog; world: WorldView }) {
  const meta = log.config.meta_pozo;
  const pct = Math.min(100, (world.pozo / meta) * 100);
  return (
    <header className="header">
      <div className="reloj">
        <div className="reloj-dia">DÍA {world.dia}<span className="reloj-de"> / {log.config.dias}</span></div>
        <div className="reloj-hora">{String(world.hora).padStart(2, "0")}:00</div>
      </div>
      <div className="pozo">
        <div className="pozo-top">
          <span>POZO COMÚN</span>
          <span className="pozo-cifra">${world.pozo.toLocaleString()} / ${meta.toLocaleString()}</span>
        </div>
        <div className="pozo-bar">
          <div className="pozo-fill" style={{ width: `${pct}%` }} />
          <div className="pozo-pct">{pct.toFixed(1)}%</div>
        </div>
      </div>
    </header>
  );
}
