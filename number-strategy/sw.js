"use strict";
const CACHE = "number-strategy-v3";
const FILES = ["./", "./index.html", "./engine.js", "./rules.js", "./app.js", "./style.css",
  "./print.html", "./print.js", "./print.css", "./manifest.webmanifest", "./icon.svg",
  "./icon-192.png", "./icon-512.png", "./printable-kit.pdf"];
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith("number-strategy-") && key !== CACHE).map(key => caches.delete(key))
  )).then(() => self.clients.claim()));
});
self.addEventListener("fetch", event => {
  if (event.request.method !== "GET" || new URL(event.request.url).origin !== self.location.origin) return;
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
});
