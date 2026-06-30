// Carga de imágenes (lámina de sprites, mapa) servidas desde public/.
// La carga es asíncrona; los canvas dibujan un respaldo hasta que la imagen
// está lista y, al terminar, avisan a los suscriptores para repintarse.

import { useEffect, useState } from "react";

export interface ImageAsset {
  // Imagen si ya cargó, o null (usar respaldo mientras tanto).
  get(): HTMLImageElement | null;
  ready(): boolean;
  // Suscribe un callback que se llama cuando la imagen termina de cargar.
  subscribe(cb: () => void): () => void;
}

export function loadImage(path: string): ImageAsset {
  let img: HTMLImageElement | null = null;
  let ready = false;
  const listeners = new Set<() => void>();

  function start() {
    if (img) return;
    const el = new Image();
    el.onload = () => {
      ready = true;
      listeners.forEach((l) => l());
    };
    el.src = `${import.meta.env.BASE_URL}${path}`;
    img = el;
  }

  return {
    get() {
      if (!img) start();
      return ready ? img : null;
    },
    ready: () => ready,
    subscribe(cb) {
      start();
      listeners.add(cb);
      return () => {
        listeners.delete(cb);
      };
    },
  };
}

// Hook React: re-renderiza el componente cuando cualquiera de las imágenes
// indicadas termina de cargar. Devuelve true cuando todas están listas.
export function useAssetsReady(...assets: ImageAsset[]): boolean {
  const [, force] = useState(0);
  useEffect(() => {
    const cb = () => force((v) => v + 1);
    const unsubs = assets.map((a) => a.subscribe(cb));
    return () => unsubs.forEach((u) => u());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return assets.every((a) => a.ready());
}
