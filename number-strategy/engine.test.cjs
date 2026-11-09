"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const E = require("./engine.js");
const place = (s, to, digit) => E.applyAction(s, { type: "place", to, digit });
const move = (s, from, to) => E.applyAction(s, { type: "move", from, to });
const fixture = (cells, digits, owner = 0) => {
  const board = Array(144).fill(null);
  cells.forEach((cell, i) => { board[cell] = { owner, digit: digits[i] }; });
  return board;
};
test("initial inventory is 162, 81 per player, nine copies of each digit", () => {
  const s = E.createGame();
  assert.equal(s.board.length, 144); assert.equal(s.turn, 0);
  assert.deepEqual(s.reserves, [Array(9).fill(9), Array(9).fill(9)]);
  assert.equal(Object.values(s.positions)[0], 1);
});
for (const family of [[3, 6, 9], [1, 5, 7], [2, 4, 8]]) {
  for (const [dr, dc] of [[0, 1], [1, 0], [1, 1], [1, -1], [0, -1], [-1, 0], [-1, -1], [-1, 1]]) {
    for (const owner of [0, 1]) {
      test(`${family.join("-")} wins in direction ${dr},${dc}, player ${owner}`, () => {
        const cells = [0, 1, 2].map(k => (5 + dr * k) * 12 + 5 + dc * k);
        assert.deepEqual(E.findWin(fixture(cells, family, owner), owner)?.cells, cells);
      });
    }
  }
}
test("no mixed ownership, gaps, unordered family or bent lines", () => {
  const mixed = fixture([0, 1, 2], [3, 6, 9]); mixed[1].owner = 1;
  assert.equal(E.findWin(mixed, 0), null);
  assert.equal(E.findWin(fixture([0, 2, 4], [3, 6, 9]), 0), null);
  assert.equal(E.findWin(fixture([0, 1, 2], [1, 7, 5]), 0), null);
  assert.equal(E.findWin(fixture([0, 1, 13], [2, 4, 8]), 0), null);
});
test("horizontal and diagonal lines cannot wrap at any board edge", () => {
  for (const cells of [[10, 11, 12], [11, 12, 13], [11, 24, 37], [12, 23, 34]])
    assert.equal(E.findWin(fixture(cells, [3, 6, 9]), 0), null);
  assert.deepEqual(E.findWin(fixture([132, 120, 108], [3, 6, 9]), 0)?.cells, [132, 120, 108]);
  assert.equal(E.adjacent(11, 12), false);
  assert.equal(E.adjacent(0, 143), false);
  assert.equal(E.adjacent(0, 13), true);
});
test("placement is immutable, consumes correct reserve and alternates turns", () => {
  const before = E.createGame(), after = place(before, 0, 3);
  assert.equal(before.board[0], null); assert.equal(before.reserves[0][2], 9);
  assert.deepEqual(after.board[0], { owner: 0, digit: 3 });
  assert.equal(after.reserves[0][2], 8); assert.equal(after.reserves[1][2], 9);
  assert.equal(after.turn, 1); assert.equal(after.ply, 1);
});
test("all eight adjacent movements are legal and preserve reserves", () => {
  const center = 65;
  for (const offset of [-13, -12, -11, -1, 1, 11, 12, 13]) {
    let s = place(E.createGame(), center, 5); s = place(s, 143, 5);
    const next = move(s, center, center + offset);
    assert.equal(next.board[center], null);
    assert.deepEqual(next.board[center + offset], { owner: 0, digit: 5 });
    assert.deepEqual(next.reserves, s.reserves); assert.equal(next.turn, 1);
  }
});
test("invalid actions do not change state or turn", () => {
  const s = place(E.createGame(), 0, 3), before = JSON.stringify(s);
  for (const a of [
    { type: "place", to: 0, digit: 9 }, { type: "place", to: 1, digit: 10 },
    { type: "place", to: -1, digit: 3 }, { type: "place", to: 144, digit: 3 },
    { type: "place", to: 1.5, digit: 3 }, { type: "place", to: 1, digit: "3" },
    { type: "move", from: 0, to: 1 }, { type: "move", from: 99, to: 100 },
    { type: "unknown", to: 1 }
  ]) assert.throws(() => E.applyAction(s, a));
  assert.equal(JSON.stringify(s), before);
  const own = { ...s, turn: 0 };
  assert.throws(() => move(own, 0, 2), /one square/);
  assert.throws(() => move(own, 0, 0), /occupied/);
});
test("exhausted reserve cannot place, but player can still move", () => {
  let s = E.createGame();
  for (let i = 0; i < 9; i++) { s = place(s, i, 1); s = place(s, 120 + i, 1); }
  assert.equal(s.reserves[0][0], 0); assert.throws(() => place(s, 30, 1), /No copies/);
  const next = move(s, 0, 12); assert.equal(next.reserves[0][0], 0);
});
test("actual placements win, postgame input rejected, replay/undo recover previous turn", () => {
  const actions = [
    { type: "place", to: 0, digit: 3 }, { type: "place", to: 120, digit: 1 },
    { type: "place", to: 1, digit: 6 }, { type: "place", to: 121, digit: 1 },
    { type: "place", to: 2, digit: 9 }
  ];
  const s = E.restoreGame({ version: 1, actions }).game;
  assert.equal(s.result.type, "win"); assert.equal(s.result.owner, 0);
  assert.throws(() => place(s, 3, 1), /ended/);
  const undone = E.restoreGame({ version: 1, actions: actions.slice(0, -1) }).game;
  assert.equal(undone.result, null); assert.equal(undone.turn, 0);
  assert.equal(undone.reserves[0][8], 9); assert.equal(undone.board[2], null);
});
test("moving can complete a win", () => {
  let s = E.createGame();
  s.board = fixture([0, 1, 14], [2, 4, 8]);
  s = move(s, 14, 2); assert.equal(s.result.type, "win");
});
test("restore rejects corrupt, excessive, impossible and postgame saves", () => {
  for (const value of [null, {}, { version: 2, actions: [] }, { version: 1, actions: "bad" },
    { version: 1, actions: Array(4097).fill(null) },
    { version: 1, actions: [{ type: "place", to: 0, digit: 1, owner: 1 }] },
    { version: 1, actions: [{ type: "move", from: 0, to: 1 }] },
    { version: 1, actions: [{ type: "place", to: 0, digit: 1 }, { type: "place", to: 0, digit: 2 }] }
  ]) assert.throws(() => E.restoreGame(value));
  const winning = [
    { type: "place", to: 0, digit: 1 }, { type: "place", to: 120, digit: 1 },
    { type: "place", to: 1, digit: 5 }, { type: "place", to: 121, digit: 1 },
    { type: "place", to: 2, digit: 7 }, { type: "place", to: 122, digit: 1 }
  ];
  assert.throws(() => E.restoreGame({ version: 1, actions: winning }), /ended/);
});
test("replay round trip exactly reconstructs state and counters", () => {
  const actions = [{ type: "place", to: 0, digit: 3 }, { type: "place", to: 143, digit: 1 }, { type: "move", from: 0, to: 13 }];
  let s = E.createGame(); for (const a of actions) s = E.applyAction(s, a);
  assert.deepEqual(E.restoreGame(JSON.parse(JSON.stringify({ version: 1, actions }))).game, s);
});
test("third identical position with same turn draws; undo removes final repetition", () => {
  const actions = [{ type: "place", to: 0, digit: 1 }, { type: "place", to: 143, digit: 1 }];
  for (let i = 0; i < 2; i++) actions.push(
    { type: "move", from: 0, to: 1 }, { type: "move", from: 143, to: 142 },
    { type: "move", from: 1, to: 0 }, { type: "move", from: 142, to: 143 });
  const s = E.restoreGame({ version: 1, actions }).game;
  assert.equal(s.result.type, "draw"); assert.match(s.result.reason, /three times/);
  assert.equal(E.restoreGame({ version: 1, actions: actions.slice(0, -1) }).game.result, null);
  assert.throws(() => move(s, 0, 1), /ended/);
});
test("full board and no-action stalemate draw; win takes precedence", () => {
  const s = E.createGame();
  s.board = Array.from({ length: 144 }, () => ({ owner: 0, digit: 1 }));
  s.board[143] = null;
  assert.match(place(s, 143, 1).result.reason, /no legal action/);
  const blocked = E.createGame(); blocked.reserves[1] = Array(9).fill(0);
  assert.match(place(blocked, 0, 1).result.reason, /no legal action/);
  s.board[140] = { owner: 0, digit: 3 }; s.board[141] = { owner: 0, digit: 6 }; s.board[142] = null;
  assert.equal(place(s, 142, 9).result.type, "win");
});
test("200 quiet moves and 4096 actions draw; placement resets quiet counter", () => {
  let s = E.createGame(); s = place(s, 0, 1); s = place(s, 143, 1);
  s.quiet = 199; assert.match(move(s, 0, 1).result.reason, /200/);
  assert.equal(place(s, 2, 2).quiet, 0);
  s.ply = 4095; s.quiet = 0; assert.match(move(s, 0, 1).result.reason, /4096/);
});
