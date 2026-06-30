import puppeteer from "puppeteer";
import path from "path";
import fs from "fs";

const OUT = "docs/screenshots";
const PUB_LOG = "visualizer/public/log.json";
const BACKUP = "visualizer/public/log.json.bak";

// Backup log actual, poner haiku
fs.copyFileSync(PUB_LOG, BACKUP);
fs.copyFileSync("samples/log_haiku_7d.json", PUB_LOG);
console.log("Log swapped → haiku (710 eventos)");

const browser = await puppeteer.launch({
  headless: true,
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  args: ["--no-sandbox", "--disable-setuid-sandbox"],
});

async function jumpToEvent(page, index) {
  await page.evaluate((idx) => {
    const inputs = [...document.querySelectorAll("input[type=range]")];
    const t = inputs.find((i) => parseInt(i.max) > 100);
    if (!t) return;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(t, String(idx));
    t.dispatchEvent(new Event("input", { bubbles: true }));
    t.dispatchEvent(new Event("change", { bubbles: true }));
  }, index);
  await new Promise((r) => setTimeout(r, 700));
}

try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 860, deviceScaleFactor: 2 });

  await page.goto("http://localhost:5173/app/?nocache=" + Date.now(), {
    waitUntil: "networkidle2", timeout: 15000,
  });
  await page.waitForSelector("canvas.mapa-canvas", { timeout: 10000 });
  await new Promise((r) => setTimeout(r, 800));

  // Último evento = todos muertos (evento 709 = índice 709)
  await jumpToEvent(page, 709);
  await page.screenshot({ path: path.join(OUT, "haiku_wipe.png"), fullPage: false });
  console.log("✓ haiku_wipe.png  (todos muertos)");

  // Panel fichas con 4×MUERTO
  const right = await page.$(".right");
  if (right) {
    await right.screenshot({ path: path.join(OUT, "haiku_fichas.png") });
    console.log("✓ haiku_fichas.png");
  }

  // Día 2 hora 22 = primeras muertes (Ana y Beto) — evento ~575
  await jumpToEvent(page, 576);
  await page.screenshot({ path: path.join(OUT, "haiku_dia2.png"), fullPage: false });
  console.log("✓ haiku_dia2.png  (primera muerte)");

} finally {
  await browser.close();
  // Restaurar log original
  fs.copyFileSync(BACKUP, PUB_LOG);
  fs.unlinkSync(BACKUP);
  console.log("Log restaurado → qwen 30d");
}
