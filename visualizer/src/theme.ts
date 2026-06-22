// Paleta sobria para los 4 Player y los lugares del mapa.

export const COLOR_AGENTE: Record<string, string> = {
  ana: "#4f9dde",
  beto: "#5fbf7a",
  carla: "#d96a6a",
  gabriel: "#b07bd1",
};

export const INICIAL: Record<string, string> = {
  ana: "A",
  beto: "B",
  carla: "C",
  gabriel: "G",
};

// Género de cada Player, solo para dibujar el sprite (Ana y Carla mujeres;
// Beto y Gabriel hombres).
export const GENERO_AGENTE: Record<string, "f" | "m"> = {
  ana: "f",
  beto: "m",
  carla: "f",
  gabriel: "m",
};

// Color de pelo del sprite por Player. Si no está aquí se usa el castaño por
// defecto (PELO_DEFECTO en sprite.ts). Carla es rubia.
export const PELO_AGENTE: Record<string, string> = {
  carla: "#e3c463",
};

// Posición de cada lugar en la cuadrícula del mapa (columna/fila, 1-based).
export const LUGAR_POS: Record<string, { col: number; row: number; label: string }> = {
  sala_a: { col: 1, row: 1, label: "Sala de edición A" },
  plaza: { col: 2, row: 1, label: "Plaza / Reunión" },
  sala_b: { col: 3, row: 1, label: "Sala de edición B" },
  mercado: { col: 1, row: 2, label: "Mercado" },
  dormitorios: { col: 3, row: 2, label: "Dormitorios" },
};
