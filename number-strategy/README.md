# 144 / Number strategy prototype

A dependency-free, local two-player web game and printable board game. This is
not deployed, not an App Store release and not a claim of proven game balance.

## Play

Run `node .\number-strategy\server.cjs` from the repository root, then open
http://127.0.0.1:4173/ on that computer. Set `PORT` to change the port.
The preview binds to loopback, not your network. To use a real phone, serve
this folder through a trusted HTTPS host; deployment is intentionally not
configured. Opening `index.html` directly also supports desktop play but not
PWA installation or service-worker caching.

Choose a reserve number then an empty square. Select your own piece to move it
one square, diagonals included. Player A uses circles and B uses squares, with
letters as well as colors. The scrollable board keeps targets at least 44 px.
Arrow keys navigate the board, Enter/Space act, Tab leaves it. On phones the
reserve stays in a bottom tray; swipe the tray sideways to reach every digit.

Local saves contain a versioned action log. Restoration replays every action,
rejecting illegal or incompatible saves. Invalid saves are left intact until
you take an action or explicitly restart. A visible warning explains failures.
Undo reconstructs the earlier state, including inventory and draw counters.
No external fonts, telemetry or backend dependencies.

## Paper kit

- `printable-kit.pdf`: ready-to-print board, all 162 pieces, rule sheet and math
  reference.
- `print.html`, `print.css`, `print.js`: editable print source, rendered locally.
- `rules.js`: shared rules and reference used by the app and paper layout.

Print single-sided, actual size / 100%, on A4 or Letter. Disable automatic
headers/footers for HTML printing. Check the 100 mm bar. Cut and join four
150 mm board tiles to make a 300 mm board, with 25 mm squares. Two token sheets
provide 81 tokens each, at 20 mm per cut square. Tokens have readable digits,
owner letters and distinct borders/shapes even in black and white.

Confirmed rules: 144 squares; 162 pieces; alternating placements or one-square
moves; first ordered own-piece line of 3-6-9, 1-5-7 or 2-4-8 wins.
The shared rule sheet explicitly labels prototype defaults: nine copies per
digit per player, A starts, no captures, diagonal empty-square moves, both
reading directions, no wrapping, draw thresholds and undo.

The full mathematical catalogue and explanatory mapping are in the in-app
reference and print kit, separate from gameplay. The earlier voxel proposal
does not replace this 12 by 12 game.

## Checks and maintenance

Run `node --test .\number-strategy\engine.test.cjs` from the repository root.
The engine uses the same rules for all UI actions and save reconstruction.
`ui-check.cjs` contains bounded browser checks and regenerates the PDF/icons;
it requires Playwright and a Chromium installation (validation tooling only).
Install development tools with `npm.cmd install` in this folder on Windows,
then `npx.cmd playwright install chromium`. Run it while the preview server
is listening on port 4173. Gameplay itself needs no npm installation.

Service-worker assets are scoped to this game. Change the cache version in
`sw.js` whenever releasing changed files, so old installations do not keep
the old cache. Reload an installed app after a new worker activates.
