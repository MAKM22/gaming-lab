"use strict";
const http = require("node:http");
const fs = require("node:fs/promises");
const path = require("node:path");
const ROOT = __dirname;
const PORT = Number(process.env.PORT || 4173);
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
  ".svg": "image/svg+xml", ".png": "image/png", ".webmanifest": "application/manifest+json", ".pdf": "application/pdf" };
const server = http.createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
    const relative = pathname.replace(/^\/+/, "") || "index.html";
    const filename = path.resolve(ROOT, relative);
    if (!filename.startsWith(ROOT + path.sep) || /(^|[\\/])\./.test(relative)) {
      response.writeHead(403); response.end("Forbidden"); return;
    }
    const body = await fs.readFile(filename);
    response.writeHead(200, { "Content-Type": TYPES[path.extname(filename)] || "application/octet-stream", "Cache-Control": "no-cache" });
    response.end(body);
  } catch (error) {
    if (error.code === "ENOENT" || error.code === "EISDIR") {
      response.writeHead(404); response.end("Not found");
    } else if (error instanceof URIError) {
      response.writeHead(400); response.end("Invalid URL");
    } else {
      console.error(error); response.writeHead(500); response.end("Server error");
    }
  }
});
server.listen(PORT, "127.0.0.1", () => console.log(`144 preview: http://127.0.0.1:${PORT}/`));
server.on("error", error => { console.error(error.message); process.exitCode = 1; });
