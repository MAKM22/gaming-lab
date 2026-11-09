---
name: Gaming Lab / 144
description: A clean shared tabletop for number strategy
colors:
  paper: "#f0f3f7"
  ink: "#20304e"
  muted: "#50617a"
  line: "#bfcbd8"
  player-a: "#223c78"
  player-b: "#126158"
  white: "#ffffff"
  focus: "#a05000"
  highlight: "#e9a32e"
typography:
  display:
    fontFamily: "system-ui, sans-serif"
    fontSize: "clamp(36px, 5vw, 56px)"
    fontWeight: 800
    letterSpacing: "-.035em"
  body:
    fontFamily: "system-ui, sans-serif"
  title:
    fontSize: "24px"
  label:
    fontSize: "12px"
rounded:
  control: "5px"
  circle: "50%"
spacing:
  compact: "8px"
  normal: "16px"
  section: "24px"
  desktop-gap: "32px"
components:
  button:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 14px"
  player-a-piece:
    backgroundColor: "{colors.player-a}"
    textColor: "{colors.white}"
    rounded: "{rounded.circle}"
  player-b-piece:
    backgroundColor: "{colors.player-b}"
    textColor: "{colors.white}"
    rounded: "{rounded.control}"
---

# Design System: Gaming Lab / 144

## Overview

**Creative North Star: "The shared tabletop"**

This system describes the number-strategy app, not every future Gaming Lab
project. The user approved a clean tabletop interface for casual phone
pass-and-play and a matching large-print kit. A readable grid and explicit turn
state carry the work; the interface uses no external typography or imagery.

**Key Characteristics:**
- Cool white surfaces and dark readable numbers.
- A circles and B squares, labeled independently of color.
- Touch-sized cells rather than a shrunken whole-board overview.

## Colors

Midnight blue identifies A, teal identifies B, and cool neutrals separate the
board, controls and explanatory text. Amber outlines selected and winning
pieces. Muted blue-gray text remains readable against the light ground.
The paper kit uses black borders, labels and shapes, not color alone.

## Typography

The system UI stack is used throughout. The display heading is heavy, 36-56 px;
player headings are 24 px. Reserve digits are 25 px desktop / 22 px mobile.
Body explanations use natural sentence case and a maximum 75-character measure.
Small square coordinates are secondary navigation cues, not the pieces' digits.

## Layout

The container caps at 1200 px with 32 px desktop padding. A flexible board column
and 320 px control column have a 32 px gap. Below 760 px, the board and supporting
controls stack with 16 px page padding. The reserve becomes a fixed bottom tray
with horizontally scrollable 44 px buttons and safe-area padding.
The board scrolls in both axes; its 12 columns retain a user-selected 44-72 px
square size. Default squares are 48 px. Desktop grids center in the board frame.
The print layout uses four 150 mm tiles, 25 mm squares, and two 81-token sheets
with 20 mm cut squares.

## Elevation & Depth

Most surfaces are flat, separated by tone and thin borders. The only structural
shadow is the mobile reserve tray: `0 -4px 12px #20304e15`, distinguishing fixed
controls from the scrolling board.

## Shapes

A pieces are circles; B pieces are softly squared. Both have owner letters.
Other controls use 5 px corners; empty board cells are square. Printed A pieces
have circular single borders; B pieces have square double borders.

## Components

Buttons have at least 44 px height, pale unselected backgrounds, darker hover
tones, and 3 px offset focus outlines. Selected reserve buttons use an ink fill
and white text; disabled controls reduce opacity. Board buttons use roving
keyboard focus. Movable destinations have dashed borders and winning cells
have thick amber outlines.

The reserve tray includes the current owner's name, number of pieces remaining,
counts per digit and the selection description. Inline status text explains
invalid actions, storage problems and offline setup. Rules and mathematical
context live in expandable sections; restart confirmation is inline.

## Do's and Don'ts

### Do:
- Do keep owner letters and shapes alongside color.
- Do preserve touch-sized cells and scroll navigation.
- Do keep paper scale explicit and check the 100 mm bar.

### Don't:
- Don't shrink 144 cells into tiny phone touch targets.
- Don't hide failed saves or failed offline setup.
- Don't turn reference constants into decorative gameplay claims.
