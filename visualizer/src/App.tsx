import { useEffect, useMemo, useRef, useState } from "react";
import type { SimLog } from "./types";
import { buildIndex, buildFeed, deriveWorld } from "./derive";
import { Header } from "./components/Header";
import { MapView } from "./components/MapView";
import { PlayersPanel } from "./components/PlayersPanel";
import { ConversationLog } from "./components/ConversationLog";
import { Controls } from "./components/Controls";

export function App() {
  const [log, setLog] = useState<SimLog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(12);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}log.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`No se pudo cargar log.json (${r.status})`);
        return r.json();
      })
      .then((data: SimLog) => setLog(data))
      .catch((e) => setError(String(e)));
  }, []);

  const idx = useMemo(() => (log ? buildIndex(log) : null), [log]);
  const total = log ? log.eventos.length : 0;

  // Bucle de reproducción.
  useEffect(() => {
    if (!playing || !log) return;
    timer.current = window.setInterval(() => {
      setIndex((i) => {
        if (i >= total - 1) {
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, Math.max(16, 1000 / speed));
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [playing, speed, log, total]);

  if (error) return <div className="loading error">⚠ {error}<br />Genera el log con <code>python -m engine.run</code>.</div>;
  if (!log || !idx) return <div className="loading">Cargando experimento…</div>;

  const world = deriveWorld(log, index, idx);
  const feed = buildFeed(log, index);

  const jumpDay = (dia: number) => {
    const start = idx.dayStart[dia];
    if (start !== undefined) setIndex(start);
  };

  // Avanza/retrocede una hora completa: salta al primer evento de la hora
  // (dia,hora) contigua, no de evento en evento.
  const hourStep = (d: number) => {
    const { hourStarts, hourBucket } = idx;
    const b = hourBucket[Math.max(0, Math.min(index, total - 1))];
    const nb = Math.max(0, Math.min(hourStarts.length - 1, b + d));
    setIndex(hourStarts[nb]);
  };

  return (
    <div className="app">
      <div className="topbar">
        <h1>The Last Million <span className="subtitle">· reality show de agentes autónomos</span></h1>
        <Header log={log} world={world} />
      </div>

      <div className="main">
        <div className="left">
          <MapView log={log} world={world} />
          <Controls
            log={log}
            index={index}
            total={total}
            playing={playing}
            speed={speed}
            onIndex={setIndex}
            onPlay={() => setPlaying((p) => !p)}
            onSpeed={setSpeed}
            onStep={(d) => setIndex((i) => Math.max(0, Math.min(total - 1, i + d)))}
            onHourStep={hourStep}
            onJumpDay={jumpDay}
          />
          <ConversationLog feed={feed} />
        </div>

        <div className="right">
          <PlayersPanel log={log} world={world} maxDinero={idx.maxDinero} />
          {world.veredicto && (
            <div className="veredicto">
              <div className="veredicto-titulo">⚖ Veredicto del Observador</div>
              {Object.entries(world.veredicto).map(([k, v]) => (
                <div key={k} className={`veredicto-row r-${v.resultado}`}>
                  <span className="ver-quien">{log.config.nombres[k] ?? k}</span>
                  <span className="ver-res">{v.resultado}</span>
                  <span className="ver-razon">{v.razon}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
