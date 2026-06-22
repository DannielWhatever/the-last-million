import type { SimLog, WorldView } from "../types";
import { COLOR_AGENTE } from "../theme";
import { Sprite } from "./Sprite";

function Bar({ pct, color }: { pct: number; color: string }) {
  return (
    <div className="bar">
      <div className="bar-fill" style={{ width: `${Math.max(0, Math.min(100, pct))}%`, background: color }} />
    </div>
  );
}

// Panel lateral omnisciente (§18.3): el espectador ve lo oculto —objetivo
// secreto y dinero real— además de las barras de cada Player.
export function PlayersPanel({ log, world, maxDinero }: { log: SimLog; world: WorldView; maxDinero: number }) {
  return (
    <div className="players">
      {log.config.agentes.map((a) => {
        const ag = world.agentes[a];
        if (!ag) return null;
        const muerto = !ag.vivo;
        const objetivo = log.config.objetivos_secretos[a];
        return (
          <div key={a} className={`player-card ${muerto ? "muerto" : ""}`} style={{ borderColor: COLOR_AGENTE[a] }}>
            <div className="player-head">
              <Sprite id={a} vivo={ag.vivo} estado={ag.estado} />
              <span className="player-name">Player {log.config.nombres[a]}</span>
              <span className={`player-estado ${muerto ? "dead" : "alive"}`}>
                {muerto ? "☠ muerto" : ag.descalificado ? "descalificado" : ag.estado}
              </span>
            </div>

            <div className="metric">
              <span className="metric-label">💰 dinero real</span>
              <span className="metric-val">${ag.dineroReal.toLocaleString()}</span>
            </div>
            <Bar pct={(ag.dineroReal / maxDinero) * 100} color="#d8b24a" />

            <div className="metric">
              <span className="metric-label">😴 sueño</span>
              <span className="metric-val">{ag.sueno}/100</span>
            </div>
            <Bar pct={ag.sueno} color="#6fa8dc" />

            <div className="metric">
              <span className="metric-label">🍽️ comida</span>
              <span className="metric-val">{Math.round(ag.comida_pct * 100)}%</span>
            </div>
            <Bar pct={ag.comida_pct * 100} color="#8bc34a" />

            <div className="objetivo-secreto">
              <span className="secreto-label">🔒 objetivo secreto</span>
              <span className="secreto-text">{objetivo}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
