import type { SimLog } from "../types";

// Controles modelo Redux (§18.3): play/pausa, paso, salto a día, velocidad y
// línea de tiempo con el puntero.
export function Controls({
  log, index, total, playing, speed,
  onIndex, onPlay, onSpeed, onStep, onHourStep, onJumpDay,
}: {
  log: SimLog;
  index: number;
  total: number;
  playing: boolean;
  speed: number;
  onIndex: (i: number) => void;
  onPlay: () => void;
  onSpeed: (s: number) => void;
  onStep: (d: number) => void;
  onHourStep: (d: number) => void;
  onJumpDay: (dia: number) => void;
}) {
  const dias = Array.from({ length: log.config.dias }, (_, i) => i + 1);
  return (
    <div className="controls">
      <div className="ctrl-row">
        <button onClick={() => onIndex(0)} title="Inicio">⏮</button>
        <button onClick={() => onHourStep(-1)} title="Retroceder 1 hora">⏪ −1h</button>
        <button onClick={() => onStep(-1)} title="Evento anterior">◀</button>
        <button className="play" onClick={onPlay}>{playing ? "⏸ Pausa" : "▶ Play"}</button>
        <button onClick={() => onStep(1)} title="Evento siguiente">▶</button>
        <button onClick={() => onHourStep(1)} title="Avanzar 1 hora">+1h ⏩</button>
        <button onClick={() => onIndex(total - 1)} title="Fin">⏭</button>

        <label className="ctrl-day">
          Saltar a día:
          <select value="" onChange={(e) => e.target.value && onJumpDay(Number(e.target.value))}>
            <option value="">—</option>
            {dias.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>

        <label className="ctrl-speed">
          Velocidad
          <input
            type="range" min={1} max={60} value={speed}
            onChange={(e) => onSpeed(Number(e.target.value))}
          />
          <span>{speed}×</span>
        </label>
      </div>

      <div className="ctrl-row timeline">
        <input
          type="range" min={0} max={total - 1} value={index}
          onChange={(e) => onIndex(Number(e.target.value))}
        />
        <span className="ctrl-counter">evento {index + 1} / {total}</span>
      </div>
    </div>
  );
}
