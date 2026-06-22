import { useEffect, useRef } from "react";
import type { FeedEntry } from "../derive";

// Log narrativo (§18.3): las frases como un chat más los momentos del Observador.
export function ConversationLog({ feed }: { feed: FeedEntry[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [feed]);

  return (
    <div className="conv">
      <div className="conv-titulo">Conversación y observador</div>
      <div className="conv-feed" ref={ref}>
        {feed.map((f, i) => {
          const prev = feed[i - 1];
          const nuevaHora = !prev || prev.dia !== f.dia || prev.hora !== f.hora;
          return (
          <div key={f.id} className={`feed-item feed-${f.cls} ${nuevaHora ? "feed-hour-break" : ""}`}>
            <span className="feed-time">{f.dia}·{String(f.hora).padStart(2, "0")}h</span>
            {f.who && <span className="feed-who">{f.who}:</span>}
            <span className="feed-text">{f.text}</span>
          </div>
          );
        })}
      </div>
    </div>
  );
}
