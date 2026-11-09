"use strict";
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const URL = "http://127.0.0.1:4173";
const ARTIFACTS = path.join(__dirname, "test-results");
const KEY = "gaming-lab-144-v1";
const square = (page, index) => page.locator(`.square[data-index="${index}"]`);
const choose = (page, digit) => page.locator("#reserve button").nth(digit - 1).click();
async function place(page, digit, index) { await choose(page, digit); await square(page, index).click(); }
async function check() {
  await fs.mkdir(ARTIFACTS, { recursive: true });
  const browser = await chromium.launch();
  try {
    const errors = [];
    const desktopContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 });
    const desktop = await desktopContext.newPage(), mobile = await mobileContext.newPage();
    for (const page of [desktop, mobile]) page.on("pageerror", error => errors.push(error.message));
    await Promise.all([desktop.goto(URL), mobile.goto(URL)]);
    for (const page of [desktop, mobile]) {
      await page.waitForFunction(() => document.getElementById("platform").textContent.startsWith("Offline game and printable kit ready"));
      assert.equal(await page.locator(".square").count(), 144);
      const measurements = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > innerWidth,
        cells: [...document.querySelectorAll(".square")].every(b => b.offsetWidth >= 44 && b.offsetHeight >= 44),
        reserves: [...document.querySelectorAll("#reserve button")].every(b => b.offsetWidth >= 44 && b.offsetHeight >= 44)
      }));
      assert.deepEqual(measurements, { overflow: false, cells: true, reserves: true });
    }
    await Promise.all([place(desktop, 3, 0), place(mobile, 3, 0)]);
    await Promise.all([
      desktop.screenshot({ path: path.join(ARTIFACTS, "desktop.png"), fullPage: true }),
      mobile.screenshot({ path: path.join(ARTIFACTS, "mobile.png"), fullPage: true })
    ]);
    await place(desktop, 1, 120);
    await choose(desktop, 6);
    await square(desktop, 120).click();
    assert.match(await desktop.locator("#status").innerText(), /occupied/);
    assert.equal(await desktop.locator("#turn-count").innerText(), "2 turns played");
    await square(desktop, 1).click();
    await place(desktop, 1, 121); await place(desktop, 9, 2);
    assert.equal(await desktop.locator(".winning").count(), 3);
    assert.match(await desktop.locator("#status").innerText(), /Player A connected 3 - 6 - 9/);
    await square(desktop, 3).click({ force: true });
    assert.equal(await desktop.locator("#turn-count").innerText(), "5 turns played");
    assert.equal(await desktop.locator("#reserve button:disabled").count(), 9);
    await desktop.reload();
    assert.equal(await desktop.locator(".winning").count(), 3);
    assert.match(await desktop.locator("#storage").innerText(), /restored/);
    await desktop.locator("#undo").click();
    assert.equal(await desktop.locator(".winning").count(), 0);
    assert.equal(await desktop.locator("#turn-count").innerText(), "4 turns played");
    await square(desktop, 0).click();
    assert.equal(await desktop.locator(".legal").count(), 2);
    await square(desktop, 12).click();
    assert.match(await square(desktop, 12).getAttribute("aria-label"), /Player A, number 3/);
    assert.match(await square(desktop, 0).getAttribute("aria-label"), /empty/);
    await desktop.locator("#restart").click(); await desktop.locator("#restart-no").click();
    assert.equal(await desktop.locator("#turn-count").innerText(), "5 turns played");
    await desktop.locator("#restart").click(); await desktop.locator("#restart-yes").click();
    assert.equal(await desktop.locator("#turn-count").innerText(), "0 turns played");
    await square(desktop, 0).focus(); await desktop.keyboard.press("ArrowRight");
    assert.equal(await desktop.evaluate(() => document.activeElement.dataset.index), "1");
    await choose(desktop, 5); await square(desktop, 1).focus(); await desktop.keyboard.press("Enter");
    assert.match(await square(desktop, 1).getAttribute("aria-label"), /number 5/);
    await desktop.locator("#cancel").isDisabled().then(disabled => assert.equal(disabled, true));
    await mobile.locator("#zoom").evaluate(el => { el.value = "72"; el.dispatchEvent(new Event("input", { bubbles: true })); });
    assert.equal(await square(mobile, 0).evaluate(el => el.offsetWidth), 72);
    await mobile.locator("#center").click();
    assert.ok(await mobile.locator("#board-scroll").evaluate(el => el.scrollLeft > 0 && el.scrollTop > 0));
    await place(mobile, 1, 143);
    assert.match(await square(mobile, 143).getAttribute("aria-label"), /Player B/);
    await mobile.setViewportSize({ width: 320, height: 740 });
    assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    // Corrupt storage is rejected visibly, without silently overwriting the old save.
    await desktop.evaluate(key => localStorage.setItem(key, "{bad JSON"), KEY);
    await desktop.reload();
    assert.match(await desktop.locator("#storage").innerText(), /Cannot restore save/);
    assert.equal(await desktop.evaluate(key => localStorage.getItem(key), KEY), "{bad JSON");
    const failureContext = await browser.newContext({ serviceWorkers: "block" });
    await failureContext.addInitScript(() => {
      Storage.prototype.setItem = () => { throw new DOMException("Storage is full", "QuotaExceededError"); };
    });
    const failure = await failureContext.newPage(); await failure.goto(URL);
    await place(failure, 1, 0);
    assert.match(await failure.locator("#storage").innerText(), /Save failed.*only in memory/);
    assert.equal(await failure.locator("#turn-count").innerText(), "1 turns played");
    const print = await desktopContext.newPage(); await print.goto(`${URL}/print.html`);
    assert.equal(await print.locator(".print-square").count(), 144);
    assert.equal(await print.locator(".token").count(), 162);
    for (const owner of ["a", "b"]) for (let digit = 1; digit <= 9; digit++) {
      const count = await print.locator(`.token.${owner}`).evaluateAll((tokens, d) => tokens.filter(t => t.childNodes[1].textContent === String(d)).length, digit);
      assert.equal(count, 9);
    }
    assert.equal(await print.locator("#pages > section").count(), 8);
    await print.emulateMedia({ media: "print" });
    const scales = await print.evaluate(() => ({
      board: document.querySelector(".print-square").getBoundingClientRect().width,
      token: document.querySelector(".token-cut").getBoundingClientRect().width,
      bar: document.querySelector(".scale").getBoundingClientRect().width,
      heights: [...document.querySelectorAll(".page")].map(p => p.getBoundingClientRect().height)
    }));
    assert.ok(Math.abs(scales.board - 25 * 96 / 25.4) < 1);
    assert.ok(Math.abs(scales.token - 20 * 96 / 25.4) < 1);
    assert.ok(Math.abs(scales.bar - 100 * 96 / 25.4) < 1);
    assert.ok(scales.heights.every(h => h < 250 * 96 / 25.4), JSON.stringify(scales.heights));
    await print.pdf({ path: path.join(__dirname, "printable-kit.pdf"), preferCSSPageSize: true, printBackground: true });
    await print.screenshot({ path: path.join(ARTIFACTS, "paper.png"), fullPage: true });
    // Raster icons are generated from our own SVG, not from external imagery.
    const icon = await desktopContext.newPage();
    await icon.goto(`${URL}/icon.svg`);
    for (const size of [192, 512]) {
      await icon.setViewportSize({ width: size, height: size });
      await icon.evaluate(size => {
        document.documentElement.style.width = `${size}px`;
        document.documentElement.style.height = `${size}px`;
      }, size);
      await icon.screenshot({ path: path.join(__dirname, `icon-${size}.png`), clip: { x: 0, y: 0, width: size, height: size } });
    }
    const offlineContext = await browser.newContext();
    const offline = await offlineContext.newPage(); await offline.goto(URL);
    await offline.waitForFunction(() => navigator.serviceWorker.controller !== null);
    await offlineContext.setOffline(true); await offline.reload();
    assert.equal(await offline.locator(".square").count(), 144);
    await place(offline, 3, 0);
    await offline.goto(`${URL}/print.html`);
    assert.equal(await offline.locator(".token").count(), 162);
    const cachedPDF = await offline.evaluate(async () => {
      const response = await fetch("./printable-kit.pdf");
      return { ok: response.ok, size: (await response.arrayBuffer()).byteLength };
    });
    assert.equal(cachedPDF.ok, true); assert.ok(cachedPDF.size > 10000);
    await offlineContext.close();
    assert.deepEqual(errors, []);
    console.log("PASS: desktop/mobile targets, 320px layout, win/postgame/undo/reload, moves, keyboard, restart, storage errors, offline app/print, 144 print squares, 162 tokens, physical scale. PDF and PNG icons generated.");
  } finally { await browser.close(); }
}
check().catch(error => { console.error(error); process.exitCode = 1; });
