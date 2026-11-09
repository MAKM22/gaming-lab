/* global NumberStrategy, NumberRules */
(() => {
  "use strict";
  const E = NumberStrategy, $ = id => document.getElementById(id), KEY = "gaming-lab-144-v1";
  let game = E.createGame(), actions = [], selection = null, focusIndex = 0;
  let storageProblem = "";
  function storageMessage(text, error = false) {
    $("storage").textContent = text;
    $("storage").classList.toggle("error", error);
  }
  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify({ version: 1, actions }));
      storageProblem = "";
      storageMessage("Saved on this device.");
    } catch (error) {
      storageProblem = `Save failed: ${error.message}. Keep this page open; your game is only in memory.`;
      storageMessage(storageProblem, true);
    }
  }
  try {
    const raw = localStorage.getItem(KEY);
    if (raw !== null) {
      const restored = E.restoreGame(JSON.parse(raw));
      game = restored.game; actions = restored.actions;
      storageMessage("Saved game restored.");
    } else storageMessage("Turns will be saved on this device.");
  } catch (error) {
    storageProblem = `Cannot restore save: ${error.message}. A fresh game is shown; the old save is unchanged until you play or restart.`;
    storageMessage(storageProblem, true);
  }
  function describe(i) {
    const p = game.board[i], coordinate = `${String.fromCharCode(65 + i % 12)}${Math.floor(i / 12) + 1}`;
    return `${coordinate}: ${p ? `Player ${p.owner ? "B" : "A"}, number ${p.digit}` : "empty"}`;
  }
  function render(message) {
    const ended = !!game.result, owner = game.result?.type === "win" ? game.result.owner : game.turn;
    const player = owner ? "B" : "A";
    $("turn-label").textContent = ended ? (game.result.type === "win" ? `Player ${player} wins` : "Draw") : `Player ${player}'s turn`;
    $("turn-count").textContent = `${game.ply} turns played`;
    $("player-name").textContent = ended ? "Game complete" : `Player ${player}`;
    $("player-mark").textContent = ended && game.result.type === "draw" ? "=" : player;
    $("player-mark").classList.toggle("b", !!owner);
    $("status").textContent = message || (ended ? (game.result.type === "win"
      ? `Player ${player} connected ${game.result.family.join(" - ")}. Undo or start a new game.`
      : `Draw: ${game.result.reason} Undo or start a new game.`)
      : "Choose a reserve number to place, or your own board piece to move.");
    const board = $("board");
    board.replaceChildren();
    game.board.forEach((p, i) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "square";
      b.dataset.index = i; b.tabIndex = i === focusIndex ? 0 : -1;
      b.classList.toggle("checker", (Math.floor(i / 12) + i % 12) % 2 === 1);
      if (p) {
        b.classList.add(p.owner ? "owner-b" : "owner-a");
        const digit = document.createElement("span"); digit.textContent = p.digit;
        const mark = document.createElement("span"); mark.className = "owner"; mark.textContent = p.owner ? "B" : "A";
        b.append(digit, mark);
      } else {
        const coord = document.createElement("span"); coord.className = "coordinate";
        coord.textContent = `${String.fromCharCode(65 + i % 12)}${Math.floor(i / 12) + 1}`; b.append(coord);
      }
      b.classList.toggle("selected", selection?.type === "move" && selection.from === i);
      b.classList.toggle("legal", !ended && !p && selection?.type === "move" && E.adjacent(selection.from, i));
      b.classList.toggle("winning", !!game.result?.cells?.includes(i));
      b.setAttribute("aria-label", describe(i) + (game.result?.cells?.includes(i) ? ", winning piece" : ""));
      b.setAttribute("aria-disabled", String(ended));
      b.addEventListener("focus", () => { focusIndex = i; });
      b.addEventListener("click", () => chooseSquare(i));
      b.addEventListener("keydown", event => {
        const moves = { ArrowRight: [0, 1], ArrowLeft: [0, -1], ArrowUp: [-1, 0], ArrowDown: [1, 0] };
        if (!moves[event.key]) return;
        event.preventDefault();
        const [dr, dc] = moves[event.key], r = Math.max(0, Math.min(11, Math.floor(i / 12) + dr)), c = Math.max(0, Math.min(11, i % 12 + dc));
        board.children[focusIndex].tabIndex = -1; focusIndex = r * 12 + c;
        board.children[focusIndex].tabIndex = 0; board.children[focusIndex].focus();
      });
      board.append(b);
    });
    $("reserve").replaceChildren();
    $("reserve-owner").textContent = `Player ${game.turn ? "B" : "A"}'s reserve`;
    game.reserves[game.turn].forEach((count, index) => {
      const b = document.createElement("button");
      b.type = "button"; b.disabled = ended || !count;
      b.setAttribute("aria-label", `Place number ${index + 1}, ${count} remaining for Player ${game.turn ? "B" : "A"}`);
      b.setAttribute("aria-pressed", String(selection?.type === "place" && selection.digit === index + 1));
      const digit = document.createElement("strong"); digit.textContent = index + 1;
      const remaining = document.createElement("small"); remaining.textContent = `${count} left`;
      b.append(digit, remaining);
      b.addEventListener("click", () => {
        selection = { type: "place", digit: index + 1 };
        render(`Number ${index + 1} selected. Choose an empty square.`);
        $("reserve").children[index].focus();
      });
      $("reserve").append(b);
    });
    $("reserve-total").textContent = `${game.reserves[game.turn].reduce((a, b) => a + b, 0)} pieces`;
    $("selection").textContent = !selection ? "No piece selected" : selection.type === "place"
      ? `Placing ${player}-${selection.digit}` : `Moving ${describe(selection.from)}. Dashed squares are legal.`;
    $("cancel").disabled = !selection; $("undo").disabled = !actions.length;
  }
  function chooseSquare(i) {
    focusIndex = i;
    if (game.result) { render(); $("board").children[i].focus(); return; }
    const p = game.board[i];
    if (p?.owner === game.turn) {
      selection = { type: "move", from: i };
      render(`Your ${p.digit} is selected. Choose an adjacent empty square.`);
    } else {
      try {
        if (!selection) throw new Error("Choose a reserve number or one of your own pieces first.");
        const action = { ...selection, to: i };
        game = E.applyAction(game, action);
        actions.push(action); selection = null; save(); render();
      } catch (error) { render(error.message); }
    }
    $("board").children[i].focus({ preventScroll: true });
  }
  $("cancel").addEventListener("click", () => { selection = null; render(); $("reserve").children[0].focus(); });
  $("undo").addEventListener("click", () => {
    if (!actions.length) return;
    actions = actions.slice(0, -1); game = E.restoreGame({ version: 1, actions }).game;
    selection = null; save(); render("Last turn undone. The previous player can choose again.");
    if (!$("undo").disabled) $("undo").focus(); else $("reserve").children[0].focus();
  });
  $("restart").addEventListener("click", () => { $("restart-confirm").hidden = false; $("restart-yes").focus(); });
  $("restart-no").addEventListener("click", () => { $("restart-confirm").hidden = true; $("restart").focus(); });
  $("restart-yes").addEventListener("click", () => {
    game = E.createGame(); actions = []; selection = null; focusIndex = 0; save(); render("New game. Player A starts.");
    $("restart-confirm").hidden = true; $("reserve").children[0].focus();
  });
  $("zoom").addEventListener("input", event => {
    document.documentElement.style.setProperty("--cell", `${event.target.value}px`);
    $("zoom-value").textContent = `${event.target.value}px`;
  });
  $("center").addEventListener("click", () => {
    const scroller = $("board-scroll");
    scroller.scrollLeft = (scroller.scrollWidth - scroller.clientWidth) / 2;
    scroller.scrollTop = (scroller.scrollHeight - scroller.clientHeight) / 2;
  });
  NumberRules.mount($("rules"), $("math")); render();
  if (storageProblem) storageMessage(storageProblem, true);
  if ("serviceWorker" in navigator && /^(https?:)$/.test(location.protocol)) {
    $("platform").textContent = "Preparing offline files...";
    navigator.serviceWorker.register("./sw.js").then(async registration => {
      if (!registration) throw new Error("This browser has blocked offline setup. Allow service workers and reload to retry.");
      if (!registration.active) {
        const worker = registration.installing || registration.waiting;
        if (!worker) throw new Error("No offline worker is available.");
        await new Promise((resolve, reject) => {
          const timer = setTimeout(() => reject(new Error("Offline setup timed out. Reload to retry.")), 15000);
          const check = () => {
            if (worker.state === "activated" || worker.state === "redundant") {
              clearTimeout(timer); worker.removeEventListener("statechange", check);
              if (worker.state === "activated") resolve();
              else reject(new Error("Offline files could not be downloaded. Reload online to retry."));
            }
          };
          worker.addEventListener("statechange", check); check();
        });
      }
      $("platform").textContent = "Offline game and printable kit ready. Use your browser menu to install.";
    }).catch(error => {
      $("platform").textContent = `Offline setup failed: ${error.message}. Online play still works.`;
      $("platform").classList.add("error");
    });
  } else $("platform").textContent = "Direct-file mode: play works; installation and offline caching need HTTPS or localhost.";
})();
