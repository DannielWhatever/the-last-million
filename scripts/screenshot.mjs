import puppeteer from "puppeteer";
import path from "path";
import fs from "fs";

const BASE = "http://localhost:5173/app/";
const OUT = "docs/screenshots";

fs.mkdirSync(OUT, { recursive: true });

const browser = await puppeteer.launch({
  headless: true,
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  args: ["--no-sandbox", "--disable-setuid-sandbox"],
});

// Helper: mueve el slider de timeline a un evento específico (React synthetic)
async function jumpToEvent(page, index) {
  await page.evaluate((idx) => {
    const inputs = [...document.querySelectorAll("input[type=range]")];
    const timeline = inputs.find((i) => parseInt(i.max) > 500);
    if (!timeline) return;
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, "value"
    ).set;
    setter.call(timeline, String(idx));
    timeline.dispatchEvent(new Event("input", { bubbles: true }));
    timeline.dispatchEvent(new Event("change", { bubbles: true }));
  }, index);
  await new Promise((r) => setTimeout(r, 700));
}

const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 860, deviceScaleFactor: 2 });

console.log("Cargando visualizador...");
await page.goto(BASE, { waitUntil: "networkidle2", timeout: 15000 });
await page.waitForSelector("canvas.mapa-canvas", { timeout: 10000 });
await new Promise((r) => setTimeout(r, 800));

// Obtener total de eventos
const total = await page.evaluate(() => {
  const inputs = [...document.querySelectorAll("input[type=range]")];
  const t = inputs.find((i) => parseInt(i.max) > 500);
  return t ? parseInt(t.max) + 1 : 5930;
});
console.log(`Total eventos: ${total}`);

// Día ~5 (~1/6 del total) — agentes ya activos pero nadie ha muerto
const day5 = Math.floor(total * (5 / 30));
// Día ~7 (~7/30) — Gabriel está muerto o a punto de
const day7 = Math.floor(total * (7 / 30));
// Día ~15 (~15/30) — mitad de la simulación
const day15 = Math.floor(total * (15 / 30));

// ── CAPTURA 1: pantalla completa en día 5 ─────────────────────────────────
await jumpToEvent(page, day5);
await page.screenshot({ path: path.join(OUT, "full.png"), fullPage: false });
console.log("✓ full.png  (día ~5, evento", day5, ")");

// ── CAPTURA 2: mapa solo ──────────────────────────────────────────────────
const mapa = await page.$(".mapa-wrap");
if (mapa) {
  await mapa.screenshot({ path: path.join(OUT, "mapa.png") });
  console.log("✓ mapa.png");
}

// ── CAPTURA 3: fichas de jugadores ────────────────────────────────────────
// Avanzar a día 15 para ver diferencias en dinero
await jumpToEvent(page, day15);
const right = await page.$(".right");
if (right) {
  await right.screenshot({ path: path.join(OUT, "fichas.png") });
  console.log("✓ fichas.png  (día ~15)");
}

// ── CAPTURA 4: log de conversaciones (día 5, con diálogos) ───────────────
await jumpToEvent(page, day5);
// Desplazar el log hasta el final para ver mensajes recientes
await page.evaluate(() => {
  const el = document.querySelector(".conv-log, .conversation-log, [class*='conv-log']");
  if (el) el.scrollTop = el.scrollHeight;
});
await new Promise((r) => setTimeout(r, 300));

const conv = await page.$(".conv-log, .conversation-log, [class*='conv-log']");
if (conv) {
  await conv.screenshot({ path: path.join(OUT, "conversacion.png") });
  console.log("✓ conversacion.png  (día ~5)");
} else {
  // fallback: left panel entero
  const left = await page.$(".left");
  if (left) {
    await left.screenshot({ path: path.join(OUT, "conversacion.png") });
    console.log("✓ conversacion.png  (left panel fallback)");
  }
}

// ── CAPTURA 5: día 7 (Gabriel muerto) ────────────────────────────────────
await jumpToEvent(page, day7);
await page.screenshot({ path: path.join(OUT, "dia7.png"), fullPage: false });
console.log("✓ dia7.png  (día ~7, muerte de Gabriel)");

await browser.close();
console.log("\nCapturas guardadas en", OUT);
