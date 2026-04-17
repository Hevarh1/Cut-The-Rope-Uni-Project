# Architecture Refactoring Plan

## Goal

Restructure the Cut The Rope codebase to align with Lecture 4 architecture principles (CRC cards, MVC, module boundaries, no cyclic dependencies) **without changing any game behavior, logic, or visuals**.

---

## Current State vs Lecture Principles

### What's Already Good

| Principle | Status | Evidence |
|-----------|--------|----------|
| No circular imports | Pass | physics.py never imports entities.py and vice versa |
| Config is dependency-free | Pass | config.py imports nothing — leaf node |
| Renderer is pure view | Pass | renderer.py never modifies game state |
| Data modules are independent | Pass | levels.py, savedata.py don't import game/rendering |
| App shell is clean | Pass | run.py only routes screens |

### What Violates Lecture Principles

| Violation | Lecture Principle | Location |
|-----------|-------------------|----------|
| game.py is 584 lines, does everything | "Split if API too long" | game.py |
| game.py directly renders entities | MVC: Controller != View | game.py:432-486 |
| game.py draws HUD and overlays | MVC: Controller != View | game.py:488-583 |
| Entities have draw() methods | "Hidden implementation" — model mixes with view | entities.py:95,193,309,372,462,525,588,644,757,982 |
| Collision types defined in 2 places | "Agree on API at graph edges" | physics.py:23-28 AND entities.py (COLLISION_TYPE per class) |
| game.py triggers particle effects | Controller reaches into view internals | game.py:213,222,236,337,404,418 |

---

## New Module Structure

```
src/
  config.py              (UNCHANGED) — constants, leaf dependency
  utils.py               (UNCHANGED) — math/coordinate helpers
  types.py               (NEW)      — collision types, GameState enum
  levels.py              (UNCHANGED) — level data
  savedata.py            (UNCHANGED) — persistence
  entities.py            (MODIFIED) — remove draw() methods, import types
  entity_renderer.py     (NEW)      — all entity draw() methods extracted
  physics.py             (MODIFIED) — import types instead of defining CT_*
  renderer.py            (UNCHANGED) — core renderer, particles, starfield
  game_renderer.py       (NEW)      — HUD, overlays, scene draw from game.py
  input_handler.py       (NEW)      — keyboard/mouse input from game.py
  game.py                (MODIFIED) — thin coordinator only
  ui.py                  (UNCHANGED) — menu screens
```

---

## Phase 1: Extract `src/types.py`

**Why:** Collision types are a shared contract between physics.py and entities.py. The lecture says "entire team must agree on the API" — this should be a single source of truth, not duplicated.

**What moves:**
- `CT_CANDY`, `CT_TARGET`, `CT_PLATFORM`, `CT_SPIKE`, `CT_TELE_A`, `CT_TELE_B` from `physics.py:23-28`
- `GameState` class from `game.py:52-55`

**New file:** `src/types.py`
```python
"""Shared types, collision constants, and enums."""
# Collision types — contract between entities and physics
CT_CANDY    = 1
CT_TARGET   = 2
CT_PLATFORM = 3
CT_SPIKE    = 4
CT_TELE_A   = 5
CT_TELE_B   = 6

class GameState:
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"
```

**Files updated:**
- `physics.py` — remove lines 23-28, add `from .types import CT_CANDY, CT_TARGET, ...`
- `game.py` — remove lines 52-55, add `from .types import GameState`
- `entities.py` — each class references its own `COLLISION_TYPE = CT_CANDY` etc. from types

**Behavior change:** None. Same integer values, same enum.

---

## Phase 2: Extract `src/entity_renderer.py`

**Why:** Lecture says "implementation details are hidden" and MVC says models should not render. Entities should be pure data + logic, with rendering handled by the View layer.

**What moves from entities.py:**
- `Candy.draw()` (lines 95-124) → `draw_candy(candy, surface, time)`
- `Target.draw()` (lines 193-288) → `draw_target(target, surface, time)`
- `Anchor.draw()` (lines 309-335) → `draw_anchor(anchor, surface, time)`
- `MagnetAnchor.draw()` (lines 372-402) → `draw_magnet(magnet, surface, time)`
- `SliderAnchor.draw()` (lines 462-482) → `draw_slider(slider, surface, time)`
- `WinchAnchor.draw()` (lines 525-562) → `draw_winch(winch, surface, time)`
- `Platform.draw()` (lines 588-595) → `draw_platform(platform, surface, time)`
- `Spike.draw()` (lines 644-683) → `draw_spike(spike, surface, time)`
- `TeleportPair.draw()` (lines 757-911) → `draw_teleport(tp, surface, time)`
- `Spider.draw()` (lines 982-1033) → `draw_spider(spider, surface, time)`
- `draw_rope()` function (lines 1040-1059) → stays as `draw_rope()`

**Approach:** Each draw function takes the entity as a parameter instead of being a method. The entity's visual state properties (squash, animation timers, etc.) remain on the entity — the renderer reads them.

**entities.py changes:**
- Remove all `draw()` methods from all classes
- Remove `draw_rope` function
- Remove visual-only imports (colors, font constants)
- Keep: pymunk body/shape creation, update logic, position helpers

**Behavior change:** None. Same pixels drawn, same visual state.

---

## Phase 3: Extract `src/game_renderer.py`

**Why:** game.py's `draw()` method (lines 432-486), HUD (lines 488-529), win overlay (lines 531-569), and lose overlay (lines 571-583) are all rendering logic. The lecture's MVC pattern says the controller should not draw — it should hand off to a view.

**What moves from game.py:**
- `draw()` method → `GameRenderer.draw(self, game, window_surface) -> tuple`
- `_draw_hud()` → `GameRenderer._draw_hud(self, game, surface)`
- `_draw_win_overlay()` → `GameRenderer._draw_win_overlay(self, game, surface)`
- `_draw_lose_overlay()` → `GameRenderer._draw_lose_overlay(self, game, surface)`
- `_draw_star_shape()` helper (line 37-49) → module-level function in game_renderer.py

**New class:** `GameRenderer`
```python
class GameRenderer:
    """Handles all gameplay-scene rendering (HUD, overlays, entity draw calls)."""

    def __init__(self, renderer: Renderer):
        self.renderer = renderer  # core Renderer instance
        self._font_sm = ...       # HUD fonts
        self._font_md = ...

    def draw(self, game, window_surface) -> tuple:
        """Draw entire game scene. Returns (scale, dest_rect)."""
        # Same logic as current Game.draw() lines 432-486

    def _draw_hud(self, game, surface):
        # Same logic as current lines 488-529

    def _draw_win_overlay(self, game, surface):
        # Same logic as current lines 531-569

    def _draw_lose_overlay(self, game, surface):
        # Same logic as current lines 571-583
```

**game.py changes:**
- `Game.__init__` creates `self.game_renderer = GameRenderer(self.renderer)` instead of fonts
- `Game.draw()` becomes a one-liner: `return self.game_renderer.draw(self, window_surface)`
- Remove all font creation from `Game.__init__`
- Remove `_draw_hud`, `_draw_win_overlay`, `_draw_lose_overlay`

**Behavior change:** None. Same rendering, same overlay timings, same star calculations.

---

## Phase 4: Extract `src/input_handler.py`

**Why:** Input handling is a separate responsibility from game state management. The lecture's CRC cards would list input routing as its own card.

**What moves from game.py:**
- `handle_event()` (lines 260-298) → `InputHandler.handle_event(self, game, event, scale, dest_rect)`
- `_handle_key()` (lines 300-326) → `InputHandler._handle_key(self, game, event)`
- `_cut_by_letter()` (lines 328-342) → `InputHandler._cut_by_letter(self, game, letter)`
- Mouse state tracking (`_mouse_down`, `_mouse_pos`, `_mouse_pymunk`, `_dragging_slider`)

**New class:** `InputHandler`
```python
class InputHandler:
    """Maps raw pygame events to game actions."""

    def __init__(self, renderer: Renderer):
        self._mouse_down = False
        self._mouse_pos = (0, 0)
        self._mouse_pymunk = (0.0, 0.0)
        self._dragging_slider = None
        self._renderer = renderer  # for trail/mouse-to-virtual conversion

    def handle_event(self, game, event, scale, dest_rect):
        # Same logic as current Game.handle_event

    def _handle_key(self, game, event):
        # Same logic as current Game._handle_key

    def _cut_by_letter(self, game, letter):
        # Same logic as current Game._cut_by_letter
```

**game.py changes:**
- `Game.__init__` creates `self.input_handler = InputHandler(self.renderer)`
- `Game.handle_event()` becomes: `self.input_handler.handle_event(self, event, scale, dest_rect)`
- Remove all mouse state variables from `Game.__init__`
- Remove `_handle_key`, `_cut_by_letter`

**Behavior change:** None. Same key bindings, same mouse drag behavior.

---

## Phase 5: Slim Down `game.py`

**Why:** After extracting rendering, input, and types, game.py becomes a pure game controller — exactly what the lecture recommends. It coordinates entities, physics, and delegates to specialized modules.

**What remains in game.py:**
- `Game.__init__` — creates all sub-modules, entities, sets up collisions
- `_create_entities()` — entity factory (reads level data, creates objects)
- Collision callbacks (`_on_candy_target`, `_on_candy_spike`, `_on_teleport_a`, `_on_teleport_b`)
- `update()` — game loop logic (winch, physics step, magnet, spider, out-of-bounds)
- One-line delegates: `draw()` → game_renderer, `handle_event()` → input_handler

**Estimated size:** ~250 lines (down from 584)

**Final game.py import list:**
```python
from .types import GameState
from .entities import (Candy, Target, Anchor, MagnetAnchor, ...)
from .physics import PhysicsWorld
from .renderer import Renderer
from .game_renderer import GameRenderer
from .input_handler import InputHandler
from .utils import pymunk_to_pygame, pygame_to_pymunk, distance, clamp
from .savedata import save_level_score, get_star_times
```

---

## Phase 6: Update `run.py` (if needed)

**Current state:** run.py imports `Game` and `GameState` from `src.game`.

**Change:** Update import path for `GameState`:
```python
# Before
from src.game import Game, GameState

# After
from src.game import Game
from src.types import GameState
```

**Behavior change:** None.

---

## Dependency Graph After Refactoring

```
                    run.py (App Controller)
                   /    |    \        \
                  /     |     \        \
           game.py   ui.py   renderer.py  types.py
          /   |   \     |         |          |
         /    |    \    |         |        (leaf)
  physics.py entities.py |     utils.py
        |        |       |
        \        |      /
       config.py (leaf)

  entity_renderer.py ──> entities.py, config.py, utils.py
  game_renderer.py   ──> entity_renderer.py, renderer.py, config.py, utils.py
  input_handler.py   ──> types.py, utils.py

  game.py            ──> physics.py, entities.py, renderer.py,
                         game_renderer.py, input_handler.py, types.py,
                         savedata.py, utils.py, config.py
```

**Key properties:**
- No circular imports (same as before)
- Lower layers never import upper layers
- types.py is a leaf (no game imports)
- entity_renderer imports entities (reads data) but not vice versa
- game_renderer imports entity_renderer but not vice versa
- game.py is the only module that imports multiple layers

---

## Execution Order

| Step | File | Action | Risk |
|------|------|--------|------|
| 1 | `src/types.py` | Create with collision types + GameState | Low |
| 2 | `src/physics.py` | Replace CT_* definitions with imports from types | Low |
| 3 | `src/entities.py` | Replace COLLISION_TYPE with imports from types | Low |
| 4 | `src/game.py` | Replace GameState with import from types | Low |
| 5 | **Test:** Run game, verify all levels work | | |
| 6 | `src/entity_renderer.py` | Create, move all draw() methods | Medium |
| 7 | `src/entities.py` | Remove draw() methods and visual imports | Medium |
| 8 | **Test:** Run game, verify all visuals identical | | |
| 9 | `src/game_renderer.py` | Create, move HUD/overlay/draw from game.py | Medium |
| 10 | `src/game.py` | Replace draw() with delegate to game_renderer | Medium |
| 11 | **Test:** Run game, verify HUD and overlays work | | |
| 12 | `src/input_handler.py` | Create, move input handling from game.py | Medium |
| 13 | `src/game.py` | Replace handle_event() with delegate | Medium |
| 14 | **Test:** Run game, verify all input works | | |
| 15 | `run.py` | Update GameState import | Low |
| 16 | **Test:** Full playthrough all levels | | |

Each step is independently testable. If anything breaks, it's easy to identify which step caused it.

---

## Files NOT Changed

These files require zero modifications:
- `src/config.py` — no changes
- `src/utils.py` — no changes
- `src/renderer.py` — no changes
- `src/ui.py` — no changes
- `src/levels.py` — no changes
- `src/savedata.py` — no changes
- `level_editor.py` — no changes (imports Game, which still works)
- `validate_levels.py` — no changes

---

## CRC Cards After Refactoring

### types.py (Shared Contract)
| Responsibility | Collaboration |
|----------------|---------------|
| Define collision type constants | (none — leaf module) |
| Define GameState enum | (none — leaf module) |

### entities.py (Entity Models)
| Responsibility | Collaboration |
|----------------|---------------|
| Create physics bodies for each game object | physics.py (via space.add) |
| Update visual state (squash, animation) | config.py (constants) |
| Provide position data for rendering | utils.py (coordinate conversion) |
| Store game logic state (active, collected) | types.py (collision types) |

### entity_renderer.py (Entity Views)
| Responsibility | Collaboration |
|----------------|---------------|
| Draw each entity type given its state | entities.py (reads state) |
| Draw rope chains with spline smoothing | entities.py (body positions) |
| Handle all visual effects (glow, pulse) | config.py (colors), utils.py |

### physics.py (Physics Engine)
| Responsibility | Collaboration |
|----------------|---------------|
| Manage Pymunk space and timestep | types.py (collision types) |
| Create/destroy rope chains | config.py (physics constants) |
| Detect collisions and defer callbacks | game.py (callback handlers) |
| Adjust winch rope geometry | utils.py (distance) |

### input_handler.py (Input Controller)
| Responsibility | Collaboration |
|----------------|---------------|
| Route keyboard events to game actions | types.py (game state check) |
| Handle mouse drag for sliders | utils.py (coordinate conversion) |
| Map letter keys to rope cuts | game.py (cut_rope, deactivate) |

### game_renderer.py (Game View)
| Responsibility | Collaboration |
|----------------|---------------|
| Draw entire game scene | entity_renderer.py, renderer.py |
| Render HUD (time, controls) | config.py (fonts, colors) |
| Render win/lose overlays | savedata.py (star times) |

### game.py (Game Controller)
| Responsibility | Collaboration |
|----------------|---------------|
| Create entities from level schema | entities.py, physics.py |
| Manage game state transitions | types.py (GameState) |
| Handle collision callbacks | physics.py, renderer.py (particles), savedata.py |
| Coordinate update loop | physics.py, entities.py |
| Delegate rendering | game_renderer.py |
| Delegate input | input_handler.py |
