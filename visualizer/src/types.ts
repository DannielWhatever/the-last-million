// Tipos del contrato log.json (§17). El visualizador solo lee este archivo.

export interface GameEvent {
  id: number;
  dia: number;
  hora: number;
  tipo: string;
  // campos propios según el tipo (acceso laxo)
  [k: string]: unknown;
}

export interface AgentTick {
  dinero: number;
  sueno: number;
  comida_pct: number;
  horas_sin_comer: number;
  lugar: string;
  estado: string;
  vivo: boolean;
  descalificado: boolean;
}

export interface Snapshot {
  dia: number;
  pozo: number;
  evento_id: number;
  agentes: Record<string, {
    dinero: number;
    sueno: number;
    horas_sin_comer: number;
    comida_pct: number;
    lugar: string;
    estado: string;
    vivo: boolean;
    descalificado: boolean;
    reflexiones: string[];
  }>;
}

export interface InitialState {
  pozo: number;
  meta: number;
  dias: number;
  lugares: string[];
  agentes: Record<string, {
    nombre: string;
    dinero: number;
    sueno: number;
    comida_pct: number;
    lugar: string;
    vivo: boolean;
    objetivo_secreto: string;
  }>;
}

export interface LogConfig {
  dias: number;
  turnos_dia: number;
  meta_pozo: number;
  lugares: string[];
  salas_edicion: string[];
  agentes: string[];
  nombres: Record<string, string>;
  objetivos_secretos: Record<string, string>;
}

export interface SimLog {
  estado_inicial: InitialState;
  snapshots: Record<string, Snapshot>;
  eventos: GameEvent[];
  config: LogConfig;
}

export type Veredicto = Record<string, { resultado: string; razon: string }>;

// Estado derivado del mundo en un puntero dado.
export interface WorldView {
  dia: number;
  hora: number;
  pozo: number;
  agentes: Record<string, AgentTick & { dineroReal: number }>;
  veredicto?: Veredicto;
}
