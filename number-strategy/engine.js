(function (root) {
  "use strict";
  const SIZE = 12;
  const FAMILIES = [[3, 6, 9], [1, 5, 7], [2, 4, 8]];
  const DIRECTIONS = [[0, 1], [1, 0], [1, 1], [1, -1], [0, -1], [-1, 0], [-1, -1], [-1, 1]];
  const MAX_ACTIONS = 4096;
  const isIndex = n => Number.isInteger(n) && n >= 0 && n < SIZE * SIZE;
  const adjacent = (a, b) => isIndex(a) && isIndex(b) && a !== b &&
    Math.abs(Math.floor(a / SIZE) - Math.floor(b / SIZE)) <= 1 &&
    Math.abs(a % SIZE - b % SIZE) <= 1;
  const positionKey = s => `${s.turn}|${s.board.map(p => p ? `${p.owner}${p.digit}` : "..").join("")}`;
  function createGame() {
    const s = { board: Array(144).fill(null), reserves: [Array(9).fill(9), Array(9).fill(9)],
      turn: 0, result: null, ply: 0, quiet: 0, positions: {} };
    s.positions[positionKey(s)] = 1;
    return s;
  }
  function findWin(board, owner) {
    for (let i = 0; i < board.length; i++) {
      for (const family of FAMILIES) {
        if (board[i]?.owner !== owner || board[i].digit !== family[0]) continue;
        for (const [dr, dc] of DIRECTIONS) {
          const cells = [i];
          for (let k = 1; k < 3; k++) {
            const r = Math.floor(i / SIZE) + dr * k, c = i % SIZE + dc * k;
            if (r < 0 || c < 0 || r >= SIZE || c >= SIZE) break;
            const j = r * SIZE + c;
            if (board[j]?.owner !== owner || board[j].digit !== family[k]) break;
            cells.push(j);
          }
          if (cells.length === 3) return { type: "win", owner, cells, family: [...family] };
        }
      }
    }
    return null;
  }
  function hasLegalAction(s) {
    const empties = s.board.flatMap((p, i) => p ? [] : [i]);
    if (!empties.length) return false;
    if (s.reserves[s.turn].some(n => n > 0)) return true;
    return s.board.some((p, i) => p?.owner === s.turn && empties.some(j => adjacent(i, j)));
  }
  function applyAction(s, action) {
    if (s.result) throw new Error("This game has ended. Undo or start a new game.");
    if (!action || !isIndex(action.to)) throw new Error("Choose a square on the board.");
    if (s.board[action.to]) throw new Error("That square is occupied. No capturing or overwriting.");
    if (action.type === "place") {
      if (!Number.isInteger(action.digit) || action.digit < 1 || action.digit > 9)
        throw new Error("Choose a number from 1 to 9.");
      if (s.reserves[s.turn][action.digit - 1] <= 0) throw new Error("No copies of that number remain.");
    } else if (action.type === "move") {
      if (!isIndex(action.from) || s.board[action.from]?.owner !== s.turn)
        throw new Error("Select one of your own pieces to move.");
      if (!adjacent(action.from, action.to)) throw new Error("Move only one square, including diagonally.");
    } else throw new Error("Unknown action.");
    const next = { ...s, board: [...s.board], reserves: s.reserves.map(r => [...r]),
      positions: { ...s.positions }, ply: s.ply + 1, quiet: action.type === "place" ? 0 : s.quiet + 1 };
    if (action.type === "place") {
      next.board[action.to] = { owner: s.turn, digit: action.digit };
      next.reserves[s.turn][action.digit - 1]--;
    } else {
      next.board[action.to] = next.board[action.from];
      next.board[action.from] = null;
    }
    next.result = findWin(next.board, s.turn);
    next.turn = 1 - s.turn;
    const key = positionKey(next);
    next.positions[key] = (next.positions[key] || 0) + 1;
    if (!next.result) {
      if (!hasLegalAction(next)) next.result = { type: "draw", reason: "The next player has no legal action." };
      else if (next.positions[key] >= 3) next.result = { type: "draw", reason: "The same position and turn occurred three times." };
      else if (next.quiet >= 200) next.result = { type: "draw", reason: "200 consecutive moves without a placement." };
      else if (next.ply >= MAX_ACTIONS) next.result = { type: "draw", reason: "The prototype's 4096-turn limit was reached." };
    }
    return next;
  }
  function restoreGame(value) {
    if (!value || value.version !== 1 || !Array.isArray(value.actions) || value.actions.length > MAX_ACTIONS)
      throw new Error("Saved game format is invalid or unsupported.");
    let game = createGame();
    const actions = [];
    for (const a of value.actions) {
      if (!a || typeof a !== "object" || Array.isArray(a)) throw new Error("Saved action is invalid.");
      const allowed = a.type === "place" ? ["type", "to", "digit"] : ["type", "to", "from"];
      if (Object.keys(a).length !== 3 || Object.keys(a).some(k => !allowed.includes(k)))
        throw new Error("Saved action has unexpected fields.");
      game = applyAction(game, a);
      actions.push({ ...a });
    }
    return { game, actions };
  }
  const api = { SIZE, FAMILIES, DIRECTIONS, MAX_ACTIONS, adjacent, positionKey, createGame, findWin, hasLegalAction, applyAction, restoreGame };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.NumberStrategy = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
