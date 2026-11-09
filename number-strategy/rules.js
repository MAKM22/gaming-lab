(function (root) {
  "use strict";
  const rulesHTML = `
    <h3>Confirmed game rules</h3>
    <p>Two players share a 12 by 12 board (144 squares) and 162 numbered pieces.
    Alternate turns: place a number from your reserve, or move one of your own
    pieces one square. First to make an adjacent ordered <strong>3-6-9,
    1-5-7, or 2-4-8</strong> sequence of their own pieces wins. The three
    squares must be in a straight horizontal, vertical, or diagonal line.</p>
    <h3>Prototype choices, not additional user-confirmed rules</h3>
    <p>Player A starts. Each player has 81 pieces: nine copies of each digit 1
    through 9. A uses circle pieces; B uses square pieces. Start with an empty
    board and keep unused pieces off the board as your reserve.</p>
    <p>On a turn, do exactly one action: place one reserve piece on any empty
    square, or move your piece to an empty adjacent square (including diagonals).
    Moving does not consume a reserve piece. There is no capture, swapping,
    overwriting, skipping a turn, or movement beyond one square.</p>
    <p>Read winning sequences in either direction. For example, 9-6-3 also
    wins when read backwards. No gaps, corners, board-edge wrapping, or mixed
    ownership. 1-7-5 is not 1-5-7. Check for a win immediately after each action;
    if it wins, stop before any draw check.</p>
    <p>A draw occurs if the next player has no legal action (including a full
    board), the same board and player-to-move occur three times, or 200
    consecutive moves occur without placing a piece. A placement resets that
    200-move counter. There is also a 4096-turn prototype safety limit.</p>
    <p>For paper play, keep a turn tally and a consecutive-move tally. Either
    player may request a position record before a suspected repetition: note
    occupied coordinates, owner and digit plus the next player. A disputed
    repetition without records is not a verified draw. You may agree to a
    draw at the table; that social agreement is outside the app's automatic
    rules.</p>
    <p>The app lets you undo one completed turn at a time, including the final
    turn. Undo restores reserves, player-to-move and draw counters. For paper
    play, record each action (for example A: place 3 at C4; B: move D5 to E6)
    and reverse the last action only with both players' agreement.</p>
    <h3>Screen controls</h3>
    <p>Choose a reserve number, then touch an empty square. To move, select your
    own board piece, then a dashed adjacent square. Clear selection cancels
    without using a turn. Swipe or scroll to explore; square size never falls
    below 44 pixels. Keyboard: Tab into the board, arrow keys to navigate,
    Enter or Space to select or act. On phones the reserve stays at the bottom;
    swipe it sideways to reach every digit. Invalid actions do not change the turn.
    New game asks for confirmation. Saves belong to this device and browser;
    storage failures appear below the controls.</p>`;
  const mathHTML = `
    <h3>What maps to gameplay</h3>
    <p>12 x 12 = 144 supplies the board size. 3 x 3 x 3 x 6 = 162 supplies
    the total inventory; the equal 81-piece sets and nine copies per digit
    are prototype choices. 369, 157 and 248 supply the three ordered winning
    families. The earlier 19 x 19 x 19 = 6859 voxel concept is separate.</p>
    <h3>Reference only: not game mechanics</h3>
    <table><thead><tr><th>Material</th><th>Values and relationship</th></tr></thead><tbody>
    <tr><td>Governors / anchor</td><td>PRIMARY_GOVERNOR 0.062483; SECONDARY_GOVERNOR
    0.061573; rounded reciprocal MASTER_ANCHOR 16.0044.</td></tr>
    <tr><td>Love scalars</td><td>11.0454 x 3.2413 x 1.7177 = 61.496159287854;
    catalogue rounds to 61.496159.</td></tr>
    <tr><td>Signatures</td><td>248 and 157: difference 91, sum 405.</td></tr>
    <tr><td>Keys</td><td>23297 and 97322 are digit permutations, not literal
    reversal. 23297 is prime; 97322 is composite. Difference 74025; sum 120619.</td></tr>
    <tr><td>Relay</td><td>29, 23, 27, 37, 97, 39, 29 closes a six-node cycle.</td></tr>
    <tr><td>Progression / macro</td><td>7 + 13 + 19 = 39; 384 = 6 x 4^3;
    384 x 39 = 14976.</td></tr>
    <tr><td>Earlier volume ladder</td><td>8, 144, 1728, 20736, 248832, 82944,
    13824, 1536, origin (0 or 1), 162.</td></tr>
    </tbody></table>
    <p>Decade families ending in 1, 5, 7 and 2, 4, 8 are selected residue
    classes, not a complete grid and not all prime numbers. The reference is
    the user's mathematical context, not established physics or evidence of
    game balance.</p>
    <h3>Full 45-value catalogue</h3>
    <p>0.000910, 0.0025, 0.061573, 0.062483, 1.7177, 2, 3, 3.2413, 6, 7, 8,
    9, 10, 11.0454, 12, 13, 16.0044, 19, 23, 24, 27, 29, 37, 39, 61.496159,
    81, 91, 97, 144, 157, 162, 248, 384, 405, 1536, 1728, 13824, 14976,
    20736, 23297, 74025, 82944, 97322, 120619, 248832.</p>`;
  const api = {
    rulesHTML, mathHTML,
    mount(rules, math) {
      if (rules) rules.innerHTML = rulesHTML;
      if (math) math.innerHTML = mathHTML;
    }
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.NumberRules = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
