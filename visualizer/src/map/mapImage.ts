// Imagen de fondo del mapa (mapa_v1.png). El mapa ya trae dibujados y
// rotulados los 5 lugares; el visualizador solo lo pinta de fondo y coloca
// encima a los Player (ver mapRenderer). Las posiciones de las salas en píxeles
// de esta imagen están en mapLayout (ROOM_RECTS).

import { loadImage, type ImageAsset } from "./assets";

export const mapImg: ImageAsset = loadImage("mapa_v1.png");
