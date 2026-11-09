/* global NumberRules */
(() => {
  "use strict";
  const pages = document.getElementById("pages");
  function page(title, className = "") {
    const section = document.createElement("section"); section.className = `page ${className}`;
    const heading = document.createElement("h1"); heading.textContent = title;
    section.append(heading); pages.append(section); return section;
  }
  function paragraph(section, text) {
    const p = document.createElement("p"); p.textContent = text; section.append(p);
  }
  function scale(section) {
    const bar = document.createElement("div"); bar.className = "scale"; bar.textContent = "This line must measure 100 mm."; section.append(bar);
  }
  const tiles = [
    ["Top left", 0, 0, "Join right edge to top right; bottom edge to bottom left."],
    ["Top right", 0, 6, "Join left edge to top left; bottom edge to bottom right."],
    ["Bottom left", 6, 0, "Join top edge to top left; right edge to bottom right."],
    ["Bottom right", 6, 6, "Join top edge to top right; left edge to bottom left."]
  ];
  tiles.forEach(([name, row, col, join]) => {
    const section = page(`144 / Board tile: ${name}`);
    paragraph(section, "Cut around the outer grid boundary. Tape the four tiles together on the back. Each square is 25 x 25 mm; the assembled board is 300 x 300 mm.");
    paragraph(section, join);
    const board = document.createElement("div"); board.className = "board-tile";
    for (let r = row; r < row + 6; r++) for (let c = col; c < col + 6; c++) {
      const square = document.createElement("div"); square.className = `print-square ${(r + c) % 2 ? "alternate" : ""}`;
      square.textContent = `${String.fromCharCode(65 + c)}${r + 1}`; board.append(square);
    }
    section.append(board); scale(section);
  });
  ["A", "B"].forEach(owner => {
    const section = page(`144 / Player ${owner}: 81 pieces`);
    paragraph(section, `Nine copies each of 1 through 9. Cut the dashed 20 mm squares, then optionally trim A's circles. Player A has circular single-border marks; B has square double-border marks. Both sets work in black and white. Glue to card if desired.`);
    const tokens = document.createElement("div"); tokens.className = "tokens";
    for (let copy = 0; copy < 9; copy++) for (let digit = 1; digit <= 9; digit++) {
      const cut = document.createElement("div"); cut.className = "token-cut";
      const token = document.createElement("div"); token.className = `token ${owner.toLowerCase()}`;
      const label = document.createElement("span"); label.textContent = owner;
      token.append(label, document.createTextNode(String(digit))); cut.append(token); tokens.append(cut);
    }
    section.append(tokens); scale(section);
  });
  const rules = page("144 / Shared rule sheet", "rule-page");
  const ruleBody = document.createElement("div"); rules.append(ruleBody);
  const math = page("144 / Mathematical reference", "rule-page");
  const mathBody = document.createElement("div"); math.append(mathBody);
  NumberRules.mount(ruleBody, mathBody);
  document.getElementById("print-button").addEventListener("click", () => window.print());
})();
