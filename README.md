# Cut The Rope

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Pygame](https://img.shields.io/badge/Pygame-ce-2.4+-green.svg)
![Pymunk](https://img.shields.io/badge/Pymunk-6.5+-orange.svg)

A physics puzzle game built with Python, pygame-ce, and pymunk.

</div>

---

## Overview

Cut The Rope is a 2D physics puzzle game where you guide a candy into Om Nom by cutting labeled ropes and using level mechanics like magnets, sliders, winches, teleports, spikes, and spiders.

Current implementation highlights:

- 10 campaign levels in `src/levels.py`
- 10 entity types in `src/entities.py`
- 5 app screens: title, level_select, guide, custom_levels, game
- Built-in fullscreen level editor (`level_editor.py`, v7 rewrite)
- Persistent best-time + star tracking in `data/scores.json`
- Custom level save/load in `data/custom_levels.json`

---

## Quick Start

### Requirements

- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/Hevarh1/Cut-The-Rope-Uni-Project.git
cd Cut-The-Rope-Uni-Project
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
# Start game
python run.py

# Start level editor
python level_editor.py
```

---

## Controls

### Title Screen

| Input | Action |
|---|---|
| Enter or Space | Open Level Select |
| G | Open Guide |
| C | Open Custom Levels |
| Mouse click | Use menu buttons |

### Level Select

| Input | Action |
|---|---|
| Mouse click | Start selected campaign level |
| 1-9 | Quick select level |
| Esc | Back to Title |

### In Game

| Input | Action |
|---|---|
| A-Z | Cut rope with matching letter |
| Shift + Letter | Retract matching winch rope (hold) |
| Ctrl/Cmd + Letter | Extend matching winch rope (hold) |
| Mouse drag on slider handle | Move slider anchor along track |
| R | Restart current level |
| Space (after win) | Next campaign level |
| Esc | Return to level select |

### Guide and Custom Levels Screens

| Input | Action |
|---|---|
| Scroll wheel / Up / Down | Scroll content |
| Esc | Back |

---

## Campaign Levels

All levels are defined as dictionaries in `src/levels.py`.

| # | Name | Main mechanic introduced |
|---|---|---|
| 1 | First Cut | Static anchor + basic rope cutting |
| 2 | Double Swing | Multi-rope timing |
| 3 | Bungee Drop | Precision drop timing |
| 4 | Magnetic Pull | Magnet auto-attach |
| 5 | Slide & Drop | Slider anchor |
| 6 | Winch Down | Winch rope extension/retraction |
| 7 | Hat Trick | Teleport pair |
| 8 | Spider Escape | Spider chase on rope |
| 9 | Spike Dodge | Spike hazard routing |
| 10 | Grand Finale | Combined mechanics |

---

## Level Editor (v7)

The editor is a standalone fullscreen tool that saves directly to `data/custom_levels.json` in game-compatible format.

Layout:

- Left panel (160px): tool palette, New, Save, Play Test
- Center panel: zoomable/pannable 720x1280 canvas
- Right panel (250px): level metadata, property editors, saved levels

### Tool Hotkeys

| Key | Tool |
|---|---|
| S | Select |
| C | Candy |
| T | Target |
| A | Anchor |
| M | Magnet |
| L | Slider |
| W | Winch |
| P | Platform |
| K | Spike |
| O | Teleport |
| D | Spider |

### Editor Interaction

| Input | Action |
|---|---|
| Left click | Place/select entity |
| Right click | Delete entity under cursor |
| Drag (Select mode) | Move selected entity |
| Scroll wheel | Zoom canvas |
| Middle mouse drag | Pan canvas |
| R | Reset camera |
| Delete/Backspace | Remove selected entity |
| F5 | Play test current level |
| Esc | Quit editor |

Play test mode supports:

- Esc: return to editor
- R: restart play test
- Space: return to editor after winning

---

## Project Structure

```text
cut-the-rope/
    run.py
    level_editor.py
    requirements.txt
    data/
        scores.json
        custom_levels.json
    src/
        __init__.py
        config.py
        entities.py
        entity_renderer.py
        game.py
        game_renderer.py
        input_handler.py
        levels.py
        physics.py
        renderer.py
        savedata.py
        types.py
        ui.py
        utils.py
```

Module roles:

- `run.py`: application state machine and screen routing
- `src/game.py`: per-level gameplay runtime
- `src/physics.py`: pymunk world, rope creation/cutting, collision callbacks
- `src/input_handler.py`: gameplay input handling
- `src/entities.py`: game entity logic and state
- `src/renderer.py`: virtual canvas, particles, starfield, scaling
- `src/entity_renderer.py`: per-entity drawing
- `src/game_renderer.py`: frame composition, HUD, win/lose overlays
- `src/ui.py`: title/level-select/guide/custom-level screens
- `src/savedata.py`: score and custom-level persistence

---

## Technical Notes

- Virtual canvas: 720x1280
- Physics: gravity -900, 20 substeps/frame, space damping 0.92
- Rope simulation: PinJoint chains + DampedRotarySpring per segment
- Rope segments are sensors and use shape-filter groups
- Collision callbacks are deferred until after physics stepping
- Win condition is immediate candy-target collision (with swallow animation)

Coordinate systems:

- Pymunk uses bottom-left origin
- Pygame uses top-left origin
- Conversion helpers are in `src/utils.py`

---

## Data and Persistence

- `data/scores.json`
    - Campaign best times are saved by numeric level key (for example, `"0": {"time": 3.42}`)
    - Stars are calculated from each level's `star_times`
- `data/custom_levels.json`
    - List of editor-created level dictionaries

Note: existing `scores.json` may contain older key formats from previous versions alongside current keys.

---

## Dependencies

| Package | Version |
|---|---|
| pygame-ce | >= 2.4.1 |
| pymunk | >= 6.5.0 |

---

## Testing

There is currently no formal automated test suite configured for the refactored game modules.

- `uniTest/` contains small experimental scripts.
- Level checks are currently done through play testing in the editor (`F5`) and in-game testing.

---

## Team

Developed by:

- Muhammad Yaseen
- Hevar Hemin
- Revar Azim

Supervisor: Mrs. Rina D. Zarro

Course: Game Design, University of Salahaddin, Erbil

---

## Repository Resources

- `PROJECT_SUMMARY.html`
- `architecture-presentation.html`
- `game_doc.md`
- `game_components.md`

