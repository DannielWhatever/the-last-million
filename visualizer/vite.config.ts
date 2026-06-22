import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Visualizador desacoplado: solo lee log.json (el contrato con el motor).
export default defineConfig({
  plugins: [react()],
  base: "./",
});
