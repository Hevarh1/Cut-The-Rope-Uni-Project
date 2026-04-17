#!/usr/bin/env python3
"""
Cut The Rope - Level Editor  (v7 - Fresh Rewrite)

Fullscreen, intuitive editor with every tool visible at all times.
Saves to data/custom_levels.json in game-compatible format.

Layout
------
  [LEFT 160px]  Tool palette + New/Save buttons + help
  [CENTER]       Zoomable / pannable game canvas
  [RIGHT 250px]  Properties panel + saved-level list

Controls
--------
  Left Click     Place entity / select entity
  Right Click    Delete entity under cursor
  Drag           Move selected entity (select mode)
  Scroll Wheel   Zoom canvas in/out
  Middle Drag    Pan canvas
  R              Reset zoom & pan
  Delete / Bksp  Remove selected entity
  ESC            Quit
"""

import os
import sys
import json
import math
import pygame
from typing import List, Tuple, Optional

# Allow importing from src/ package
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

# -- paths -------------------------------------------------------------------
DATA_DIR  = os.path.join(_BASE_DIR, "data")
CUSTOM_FILE = os.path.join(DATA_DIR, "custom_levels.json")

# -- game canvas size --------------------------------------------------------
GAME_W, GAME_H = 720, 1280

# -- colour palette ----------------------------------------------------------
C_BG          = (15, 18, 25)
C_PANEL       = (22, 26, 38)
C_PANEL_EDGE  = (45, 50, 65)
C_CANVAS_BG   = (20, 24, 32)
C_GRID        = (30, 36, 48)
C_GRID_MAJ    = (40, 48, 62)
C_TEXT        = (220, 225, 240)
C_DIM         = (130, 135, 155)
C_ACCENT      = (100, 140, 255)
C_HOVER       = (70, 90, 140)
C_SEL         = (120, 160, 255)
C_OK          = (80, 220, 120)
C_BAD         = (220, 80, 80)
C_STAR_FILL   = (255, 220, 50)
C_STAR_EMPTY  = (60, 65, 80)

# entity colours
EC = {
    "candy":    (230, 60, 60),
    "target":   (60, 200, 100),
    "anchor":   (100, 110, 140),
    "magnet":   (100, 180, 255),
    "slider":   (180, 130, 255),
    "winch":    (255, 180, 60),
    "platform": (90, 95, 120),
    "spike":    (200, 50, 50),
    "teleport": (180, 100, 255),
    "spider":   (60, 50, 60),
}

# tool list shown in left panel  (id, label, colour, shortcut)
TOOLS = [
    ("select",   "Select",    (180, 180, 200), "S"),
    ("candy",    "Candy",     EC["candy"],      "C"),
    ("target",   "Target",    EC["target"],     "T"),
    ("anchor",   "Anchor",    EC["anchor"],     "A"),
    ("magnet",   "Magnet",    EC["magnet"],     "M"),
    ("slider",   "Slider",    EC["slider"],     "L"),
    ("winch",    "Winch",     EC["winch"],      "W"),
    ("platform", "Platform",  EC["platform"],   "P"),
    ("spike",    "Spike",     EC["spike"],      "K"),
    ("teleport", "Teleport",  EC["teleport"],   "O"),
    ("spider",   "Spider",    EC["spider"],     "D"),
]

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

ANGLE_NAMES = {
    0: "Right", 45: "Up-Right", 90: "Up", 135: "Up-Left",
    180: "Left", 225: "Down-Left", 270: "Down", 315: "Down-Right",
}

# ============================================================================
#  Helpers
# ============================================================================

def _ensure_data():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_custom_levels() -> list:
    if os.path.exists(CUSTOM_FILE):
        try:
            with open(CUSTOM_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []

def save_custom_levels(levels: list):
    _ensure_data()
    with open(CUSTOM_FILE, "w") as f:
        json.dump(levels, f, indent=2)

def pymunk_y(py_y: float) -> float:
    return float(GAME_H - py_y)

def to_pygame_y(pm_y: float) -> float:
    return float(GAME_H - pm_y)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def deg_name(rad: float) -> str:
    d = int(math.degrees(rad)) % 360
    best = min(ANGLE_NAMES, key=lambda k: abs((d - k + 180) % 360 - 180))
    return ANGLE_NAMES.get(best, f"{d}deg")

def draw_star(surf, cx, cy, size, filled=True):
    pts = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5
        r = size if k % 2 == 0 else size * 0.4
        pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
    if filled:
        pygame.draw.polygon(surf, C_STAR_FILL, pts)
        pygame.draw.polygon(surf, (200, 170, 30), pts, 2)
    else:
        pygame.draw.polygon(surf, C_STAR_EMPTY, pts)
        pygame.draw.polygon(surf, (90, 95, 110), pts, 2)

# ============================================================================
#  TextInput widget
# ============================================================================

class TextInput:
    def __init__(self, x, y, w, h, font, label="", default="", numeric=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.font = font
        self.label = label
        self.text = str(default)
        self.numeric = numeric
        self.active = False
        self._blink = True
        self._bt = 0.0

    def handle_event(self, ev) -> bool:
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            was = self.active
            self.active = self.rect.collidepoint(ev.pos)
            return self.active or was
        if ev.type == pygame.KEYDOWN and self.active:
            if ev.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return True
            if ev.key in (pygame.K_RETURN, pygame.K_TAB):
                self.active = False
                return True
            ch = ev.unicode
            if ch:
                if self.numeric:
                    if ch in "0123456789.-":
                        self.text += ch
                else:
                    self.text += ch
                return True
        return False

    def update(self, dt):
        self._bt += dt
        if self._bt > 0.5:
            self._bt = 0.0
            self._blink = not self._blink

    def draw(self, surf):
        if self.label:
            lbl = self.font.render(self.label, True, C_DIM)
            surf.blit(lbl, (self.rect.x, self.rect.y - 16))
        bg = (50, 55, 72) if self.active else (38, 42, 55)
        pygame.draw.rect(surf, bg, self.rect, border_radius=5)
        brd = C_ACCENT if self.active else C_PANEL_EDGE
        pygame.draw.rect(surf, brd, self.rect, width=2, border_radius=5)
        txt = self.font.render(self.text, True, C_TEXT)
        surf.blit(txt, (self.rect.x + 5, self.rect.y + 3))
        if self.active and self._blink:
            cx = self.rect.x + 7 + txt.get_width()
            pygame.draw.line(surf, C_TEXT, (cx, self.rect.y + 4),
                             (cx, self.rect.bottom - 4))

    @property
    def fval(self):
        try:
            return float(self.text)
        except ValueError:
            return 0.0

    @property
    def ival(self):
        try:
            return int(float(self.text))
        except ValueError:
            return 0


# ============================================================================
#  EditorEntity
# ============================================================================

class EditorEntity:
    def __init__(self, etype: str, x: float, y: float, **kw):
        self.type      = etype
        self.x         = x
        self.y         = y
        self.letter    = kw.get("letter", "A")
        self.length    = kw.get("length", 180)
        self.radius    = kw.get("radius", 30)
        self.x2        = kw.get("x2", x + 120)
        self.y2        = kw.get("y2", y)
        self.thickness = kw.get("thickness", 8)
        self.width     = kw.get("width", 80)
        self.height    = kw.get("height", 20)
        self.direction = kw.get("direction", "up")
        self.track_x1  = kw.get("track_x1", x - 100)
        self.track_y1  = kw.get("track_y1", y)
        self.track_x2  = kw.get("track_x2", x + 100)
        self.track_y2  = kw.get("track_y2", y)
        self.start_t   = kw.get("start_t", 0.5)
        self.bx        = kw.get("bx", x + 200)
        self.by        = kw.get("by", y)
        self.angle_a   = kw.get("angle_a", 0.0)
        self.angle_b   = kw.get("angle_b", 0.0)
        self.rope_index = kw.get("rope_index", 0)
        self.speed     = kw.get("speed", 55)

    # -- hit testing ---------------------------------------------------------

    def rope_end(self) -> Tuple[float, float]:
        return (self.x, self.y + self.length)

    def hit_rope_handle(self, mx, my, zoom=1.0) -> bool:
        if self.type not in ("anchor", "winch"):
            return False
        ex, ey = self.rope_end()
        return math.hypot(mx - ex, my - ey) < max(12, 16 / zoom)

    def hit(self, mx, my, zoom=1.0) -> bool:
        r = max(14, 18 / zoom)
        if self.type == "platform":
            dx, dy = self.x2 - self.x, self.y2 - self.y
            L = math.hypot(dx, dy)
            if L < 1:
                return math.hypot(mx - self.x, my - self.y) < r
            t = clamp(((mx - self.x) * dx + (my - self.y) * dy) / (L * L), 0, 1)
            px = self.x + t * dx
            py = self.y + t * dy
            return math.hypot(mx - px, my - py) < r
        if self.type == "teleport":
            return (math.hypot(mx - self.x, my - self.y) < r or
                    math.hypot(mx - self.bx, my - self.by) < r)
        if self.type == "spike":
            return (abs(mx - self.x) < self.width / 2 + 5 and
                    abs(my - self.y) < self.height / 2 + 5)
        if self.type in ("anchor", "winch"):
            ex, ey = self.rope_end()
            return (math.hypot(mx - self.x, my - self.y) < r or
                    math.hypot(mx - ex, my - ey) < r)
        return math.hypot(mx - self.x, my - self.y) < r

    # -- serialise to game format --------------------------------------------

    def to_game_dict(self) -> Optional[dict]:
        t = self.type
        if t in ("candy", "target"):
            return None
        if t == "anchor":
            return dict(x=round(self.x), y=round(pymunk_y(self.y)),
                        letter=self.letter, length=round(self.length))
        if t == "magnet":
            return dict(x=round(self.x), y=round(pymunk_y(self.y)),
                        radius=round(self.radius), letter=self.letter)
        if t == "slider":
            return dict(x=round(self.x), y=round(pymunk_y(self.y)),
                        track_start=(round(self.track_x1), round(pymunk_y(self.track_y1))),
                        track_end=(round(self.track_x2), round(pymunk_y(self.track_y2))),
                        letter=self.letter, start_t=round(self.start_t, 2))
        if t == "winch":
            return dict(x=round(self.x), y=round(pymunk_y(self.y)),
                        letter=self.letter, length=round(self.length))
        if t == "platform":
            return dict(x1=round(self.x), y1=round(pymunk_y(self.y)),
                        x2=round(self.x2), y2=round(pymunk_y(self.y2)),
                        thickness=round(self.thickness))
        if t == "spike":
            return dict(x=round(self.x), y=round(pymunk_y(self.y)),
                        width=round(self.width), height=round(self.height),
                        direction=self.direction)
        if t == "teleport":
            return dict(ax=round(self.x), ay=round(pymunk_y(self.y)),
                        bx=round(self.bx), by=round(pymunk_y(self.by)),
                        angle_a=round(self.angle_a, 4),
                        angle_b=round(self.angle_b, 4))
        if t == "spider":
            return dict(rope_index=self.rope_index,
                        start_t=round(self.start_t, 2),
                        speed=round(self.speed))
        return None


# ============================================================================
#  Main editor
# ============================================================================

class LevelEditor:
    LEFT_W  = 160
    RIGHT_W = 250

    def __init__(self):
        pygame.init()
        info = pygame.display.Info()
        self.W = info.current_w
        self.H = info.current_h
        self.screen = pygame.display.set_mode((self.W, self.H), pygame.FULLSCREEN)
        pygame.display.set_caption("Cut The Rope - Level Editor")
        self.clock = pygame.time.Clock()

        self.font    = pygame.font.SysFont("Arial", 16)
        self.font_sm = pygame.font.SysFont("Arial", 13)
        self.font_md = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_lg = pygame.font.SysFont("Arial", 22, bold=True)

        # state
        self.mode = "select"
        self.entities: List[EditorEntity] = []
        self.sel = -1
        self.levels = load_custom_levels()
        self.edit_idx = -1

        # camera
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.zoom  = 1.0
        self._pan  = False
        self._pan_last: Optional[Tuple[int, int]] = None

        # dragging
        self._drag      = False
        self._drag_kind = ""
        self._drag_off  = (0.0, 0.0)

        # two-click placement
        self._step = 0
        self._step_ent: Optional[EditorEntity] = None

        # toast
        self._toast_msg = ""
        self._toast_t   = 0.0

        # property inputs (rebuilt when selection changes)
        self._pins: List[TextInput] = []

        # always-visible global inputs
        rx = self.W - self.RIGHT_W + 15
        self.inp_name  = TextInput(rx, 0, self.RIGHT_W - 30, 24,
                                   self.font, "Level Name", "My Level")
        self.inp_star3 = TextInput(rx, 0, 55, 24, self.font, "3-star", "5",
                                   numeric=True)
        self.inp_star2 = TextInput(rx + 70, 0, 55, 24, self.font, "2-star", "10",
                                   numeric=True)
        self.inp_star1 = TextInput(rx + 140, 0, 55, 24, self.font, "1-star", "20",
                                   numeric=True)
        self._global_inputs = [self.inp_name, self.inp_star3,
                               self.inp_star2, self.inp_star1]

        # clickable rects built every frame
        self._rope_btns: List[Tuple[pygame.Rect, int]]  = []
        self._angle_btns: List[Tuple[pygame.Rect, str]] = []
        self._saved_btns: List[Tuple[pygame.Rect, int]] = []
        self._saved_del:  List[Tuple[pygame.Rect, int]] = []
        self._saved_scroll = 0

        self._reset_cam()

    # -- coordinate helpers --------------------------------------------------

    def _canvas_rect(self) -> pygame.Rect:
        return pygame.Rect(self.LEFT_W, 0,
                           self.W - self.LEFT_W - self.RIGHT_W, self.H)

    def _reset_cam(self):
        cr = self._canvas_rect()
        sx, sy = cr.width / GAME_W, cr.height / GAME_H
        self.zoom = min(sx, sy) * 0.9
        self.cam_x = -(cr.width / self.zoom - GAME_W) / 2
        self.cam_y = -(cr.height / self.zoom - GAME_H) / 2

    def s2w(self, sx, sy) -> Tuple[float, float]:
        cr = self._canvas_rect()
        return ((sx - cr.x) / self.zoom + self.cam_x,
                (sy - cr.y) / self.zoom + self.cam_y)

    def w2s(self, wx, wy) -> Tuple[int, int]:
        cr = self._canvas_rect()
        return (int((wx - self.cam_x) * self.zoom) + cr.x,
                int((wy - self.cam_y) * self.zoom) + cr.y)

    # -- utilities -----------------------------------------------------------

    def _next_letter(self) -> str:
        used = {e.letter for e in self.entities
                if e.type in ("anchor", "magnet", "slider", "winch")}
        for ch in LETTERS:
            if ch not in used:
                return ch
        return "Z"

    def _get_ropes(self) -> List[Tuple[int, str, str]]:
        out = []
        for e in self.entities:
            if e.type in ("anchor", "magnet", "slider", "winch"):
                out.append((len(out), e.letter, e.type.title()))
        return out

    def _rope_letter(self, idx: int) -> str:
        ropes = self._get_ropes()
        return ropes[idx][1] if 0 <= idx < len(ropes) else "?"

    def _any_input_active(self) -> bool:
        for inp in self._global_inputs:
            if inp.active:
                return True
        for inp in self._pins:
            if inp.active:
                return True
        return False

    def _toast(self, msg: str):
        self._toast_msg = msg
        self._toast_t = 2.5

    # ========================================================================
    #  Events
    # ========================================================================

    def _events(self) -> bool:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False

            eaten = False
            for inp in self._global_inputs:
                if inp.handle_event(ev):
                    eaten = True
            for inp in self._pins:
                if inp.handle_event(ev):
                    eaten = True
            if eaten:
                continue

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return False
                if ev.key == pygame.K_F5:
                    self._play_test()
                if not self._any_input_active():
                    if ev.key == pygame.K_r:
                        self._reset_cam()
                    for etype, _, _, sc in TOOLS:
                        if ev.unicode.upper() == sc:
                            self.mode = etype
                            self._step = 0
                            self._step_ent = None
                            break
                    if ev.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                        if 0 <= self.sel < len(self.entities):
                            self.entities.pop(self.sel)
                            self.sel = -1
                            self._rebuild_pins()

            cr = self._canvas_rect()

            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                if cr.collidepoint(mx, my):
                    wx, wy = self.s2w(mx, my)
                    if ev.button == 2:
                        self._pan = True
                        self._pan_last = (mx, my)
                    elif ev.button == 3:
                        self._right_click_delete(wx, wy)
                    elif ev.button == 1:
                        if self.mode == "select":
                            self._select_click(wx, wy)
                        else:
                            self._place(wx, wy)
                elif mx < self.LEFT_W and ev.button == 1:
                    self._left_click(mx, my)
                elif mx >= self.W - self.RIGHT_W and ev.button == 1:
                    self._right_panel_click(mx, my)

            elif ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 2:
                    self._pan = False
                    self._pan_last = None
                if ev.button == 1:
                    self._drag = False
                    self._drag_kind = ""

            elif ev.type == pygame.MOUSEMOTION:
                mx, my = ev.pos
                if self._pan and self._pan_last:
                    self.cam_x -= (mx - self._pan_last[0]) / self.zoom
                    self.cam_y -= (my - self._pan_last[1]) / self.zoom
                    self._pan_last = (mx, my)
                elif self._drag and 0 <= self.sel < len(self.entities):
                    wx, wy = self.s2w(mx, my)
                    e = self.entities[self.sel]
                    if self._drag_kind == "rope_handle":
                        e.length = max(20, wy - e.y)
                        self._rebuild_pins()
                    elif self._drag_kind == "end":
                        if e.type == "platform":
                            e.x2 = wx + self._drag_off[0]
                            e.y2 = wy + self._drag_off[1]
                        elif e.type == "teleport":
                            e.bx = wx + self._drag_off[0]
                            e.by = wy + self._drag_off[1]
                    else:
                        e.x = wx + self._drag_off[0]
                        e.y = wy + self._drag_off[1]

            elif ev.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if cr.collidepoint(mx, my):
                    f = 1.15 if ev.y > 0 else 1.0 / 1.15
                    self.cam_x += (mx - cr.x) / self.zoom * (1 - 1 / f)
                    self.cam_y += (my - cr.y) / self.zoom * (1 - 1 / f)
                    self.zoom = clamp(self.zoom * f, 0.15, 5.0)
                elif mx >= self.W - self.RIGHT_W:
                    self._saved_scroll = max(0, self._saved_scroll - ev.y * 30)

        return True

    # -- canvas click actions ------------------------------------------------

    def _right_click_delete(self, wx, wy):
        for i in range(len(self.entities) - 1, -1, -1):
            if self.entities[i].hit(wx, wy, self.zoom):
                self.entities.pop(i)
                if self.sel == i:
                    self.sel = -1
                elif self.sel > i:
                    self.sel -= 1
                self._rebuild_pins()
                break

    def _select_click(self, wx, wy):
        hit = -1
        for i in range(len(self.entities) - 1, -1, -1):
            if self.entities[i].hit(wx, wy, self.zoom):
                hit = i
                break
        if hit >= 0:
            self.sel = hit
            self._drag = True
            e = self.entities[hit]
            if e.type in ("anchor", "winch") and e.hit_rope_handle(wx, wy, self.zoom):
                self._drag_kind = "rope_handle"
                self._drag_off = (0, 0)
            elif (e.type == "platform" and
                  math.hypot(wx - e.x2, wy - e.y2) < 20 / self.zoom):
                self._drag_kind = "end"
                self._drag_off = (e.x2 - wx, e.y2 - wy)
            elif (e.type == "teleport" and
                  math.hypot(wx - e.bx, wy - e.by) < 20 / self.zoom):
                self._drag_kind = "end"
                self._drag_off = (e.bx - wx, e.by - wy)
            else:
                self._drag_kind = "main"
                self._drag_off = (e.x - wx, e.y - wy)
            self._rebuild_pins()
        else:
            self.sel = -1
            self._rebuild_pins()

    def _place(self, wx, wy):
        m = self.mode
        if m == "candy":
            self.entities = [e for e in self.entities if e.type != "candy"]
            self.entities.insert(0, EditorEntity("candy", wx, wy))
            self._toast("Candy placed")
        elif m == "target":
            self.entities = [e for e in self.entities if e.type != "target"]
            self.entities.append(EditorEntity("target", wx, wy, radius=30))
            self._toast("Target placed")
        elif m == "anchor":
            self.entities.append(EditorEntity("anchor", wx, wy,
                                 letter=self._next_letter(), length=180))
            self._toast("Anchor placed")
        elif m == "magnet":
            self.entities.append(EditorEntity("magnet", wx, wy,
                                 letter=self._next_letter(), radius=100))
            self._toast("Magnet placed")
        elif m == "slider":
            self.entities.append(EditorEntity("slider", wx, wy,
                                 letter=self._next_letter(),
                                 track_x1=wx - 100, track_y1=wy,
                                 track_x2=wx + 100, track_y2=wy,
                                 start_t=0.5))
            self._toast("Slider placed")
        elif m == "winch":
            self.entities.append(EditorEntity("winch", wx, wy,
                                 letter=self._next_letter(), length=120))
            self._toast("Winch placed")
        elif m == "platform":
            if self._step == 0:
                self._step_ent = EditorEntity("platform", wx, wy, x2=wx, y2=wy)
                self._step = 1
                self._toast("Click second endpoint...")
                return
            else:
                self._step_ent.x2 = wx
                self._step_ent.y2 = wy
                self.entities.append(self._step_ent)
                self._step_ent = None
                self._step = 0
                self._toast("Platform placed")
        elif m == "spike":
            self.entities.append(EditorEntity("spike", wx, wy,
                                 width=80, height=20, direction="up"))
            self._toast("Spike placed")
        elif m == "teleport":
            if self._step == 0:
                self._step_ent = EditorEntity("teleport", wx, wy, bx=wx, by=wy)
                self._step = 1
                self._toast("Click exit point...")
                return
            else:
                self._step_ent.bx = wx
                self._step_ent.by = wy
                self.entities.append(self._step_ent)
                self._step_ent = None
                self._step = 0
                self._toast("Teleport placed")
        elif m == "spider":
            ropes = self._get_ropes()
            if not ropes:
                self._toast("Place a rope anchor first!")
                return
            self.entities.append(EditorEntity("spider", wx, wy,
                                 rope_index=0, speed=55, start_t=0.0))
            self._toast("Spider placed (on rope " + ropes[0][1] + ")")
        self.sel = len(self.entities) - 1
        self._rebuild_pins()

    # -- left panel clicks ---------------------------------------------------

    def _left_click(self, mx, my):
        y = 60
        for etype, _, _, _ in TOOLS:
            if pygame.Rect(10, y, self.LEFT_W - 20, 36).collidepoint(mx, my):
                self.mode = etype
                self._step = 0
                self._step_ent = None
                return
            y += 42
        y += 20
        if pygame.Rect(10, y, self.LEFT_W - 20, 32).collidepoint(mx, my):
            self._new_level()
            return
        y += 40
        if pygame.Rect(10, y, self.LEFT_W - 20, 32).collidepoint(mx, my):
            self._save_level()
            return
        y += 40
        if pygame.Rect(10, y, self.LEFT_W - 20, 32).collidepoint(mx, my):
            self._play_test()
            return

    # -- right panel clicks --------------------------------------------------

    def _right_panel_click(self, mx, my):
        for rect, ri in self._rope_btns:
            if rect.collidepoint(mx, my):
                if (0 <= self.sel < len(self.entities)
                        and self.entities[self.sel].type == "spider"):
                    self.entities[self.sel].rope_index = ri
                    self._toast("Spider -> rope " + self._rope_letter(ri))
                return
        for rect, act in self._angle_btns:
            if rect.collidepoint(mx, my):
                if (0 <= self.sel < len(self.entities)
                        and self.entities[self.sel].type == "teleport"):
                    e = self.entities[self.sel]
                    step = math.pi / 4
                    if act == "a+":
                        e.angle_a = (e.angle_a + step) % (2 * math.pi)
                    elif act == "a-":
                        e.angle_a = (e.angle_a - step) % (2 * math.pi)
                    elif act == "b+":
                        e.angle_b = (e.angle_b + step) % (2 * math.pi)
                    elif act == "b-":
                        e.angle_b = (e.angle_b - step) % (2 * math.pi)
                return
        for rect, idx in self._saved_btns:
            if rect.collidepoint(mx, my):
                self._load_level(idx)
                return
        for rect, idx in self._saved_del:
            if rect.collidepoint(mx, my):
                self._delete_level(idx)
                return

    # ========================================================================
    #  Property inputs
    # ========================================================================

    def _rebuild_pins(self):
        self._pins = []
        if not (0 <= self.sel < len(self.entities)):
            return
        e = self.entities[self.sel]
        rx = self.W - self.RIGHT_W + 15
        sw = 90

        if e.type in ("anchor", "magnet", "slider", "winch"):
            self._pins.append(
                TextInput(rx, 0, 40, 24, self.font, "Letter", e.letter))
        if e.type in ("anchor", "winch"):
            self._pins.append(
                TextInput(rx, 0, sw, 24, self.font, "Rope Length",
                          str(int(e.length)), numeric=True))
        if e.type == "magnet":
            self._pins.append(
                TextInput(rx, 0, sw, 24, self.font, "Pull Radius",
                          str(int(e.radius)), numeric=True))
        if e.type == "target":
            self._pins.append(
                TextInput(rx, 0, sw, 24, self.font, "Radius",
                          str(int(e.radius)), numeric=True))
        if e.type == "slider":
            self._pins.append(
                TextInput(rx, 0, sw, 24, self.font, "Start pos (0-1)",
                          str(e.start_t), numeric=True))
        if e.type == "spike":
            self._pins.append(
                TextInput(rx, 0, sw, 24, self.font, "Width",
                          str(int(e.width)), numeric=True))
            self._pins.append(
                TextInput(rx, 0, sw, 24, self.font, "Height",
                          str(int(e.height)), numeric=True))
            self._pins.append(
                TextInput(rx, 0, self.RIGHT_W - 30, 24, self.font,
                          "Dir (up/down/left/right)", e.direction))
        if e.type == "platform":
            self._pins.append(
                TextInput(rx, 0, sw, 24, self.font, "Thickness",
                          str(int(e.thickness)), numeric=True))
        if e.type == "spider":
            self._pins.append(
                TextInput(rx, 0, sw, 24, self.font, "Speed",
                          str(int(e.speed)), numeric=True))
            self._pins.append(
                TextInput(rx, 0, sw, 24, self.font, "Start pos (0-1)",
                          str(e.start_t), numeric=True))

    def _apply_pins(self):
        if not (0 <= self.sel < len(self.entities)):
            return
        e = self.entities[self.sel]
        i = 0
        if e.type in ("anchor", "magnet", "slider", "winch") and i < len(self._pins):
            v = self._pins[i].text.strip().upper()
            if v and v[0] in LETTERS:
                e.letter = v[0]
            i += 1
        if e.type in ("anchor", "winch") and i < len(self._pins):
            e.length = max(20, self._pins[i].fval)
            i += 1
        if e.type == "magnet" and i < len(self._pins):
            e.radius = max(10, self._pins[i].fval)
            i += 1
        if e.type == "target" and i < len(self._pins):
            e.radius = max(10, self._pins[i].fval)
            i += 1
        if e.type == "slider" and i < len(self._pins):
            e.start_t = clamp(self._pins[i].fval, 0, 1)
            i += 1
        if e.type == "spike":
            if i < len(self._pins):
                e.width = max(10, self._pins[i].fval)
                i += 1
            if i < len(self._pins):
                e.height = max(5, self._pins[i].fval)
                i += 1
            if i < len(self._pins):
                d = self._pins[i].text.strip().lower()
                if d in ("up", "down", "left", "right"):
                    e.direction = d
                i += 1
        if e.type == "platform" and i < len(self._pins):
            e.thickness = max(2, self._pins[i].fval)
            i += 1
        if e.type == "spider":
            if i < len(self._pins):
                e.speed = max(1, self._pins[i].fval)
                i += 1
            if i < len(self._pins):
                e.start_t = clamp(self._pins[i].fval, 0, 1)
                i += 1

    # ========================================================================
    #  Level management
    # ========================================================================

    def _new_level(self):
        self.entities.clear()
        self.sel = -1
        self.edit_idx = -1
        self.inp_name.text = "My Level"
        self.inp_star3.text = "5"
        self.inp_star2.text = "10"
        self.inp_star1.text = "20"
        self._rebuild_pins()
        self._reset_cam()
        self._toast("New level")

    def _build_dict(self) -> Optional[dict]:
        candy = target = None
        anchors, magnets, sliders, winches = [], [], [], []
        platforms, spikes, teleports, spiders = [], [], [], []
        for e in self.entities:
            if e.type == "candy":
                candy = (round(e.x), round(pymunk_y(e.y)))
            elif e.type == "target":
                target = (round(e.x), round(pymunk_y(e.y)), round(e.radius))
            else:
                d = e.to_game_dict()
                if d:
                    {"anchor": anchors, "magnet": magnets, "slider": sliders,
                     "winch": winches, "platform": platforms, "spike": spikes,
                     "teleport": teleports, "spider": spiders}[e.type].append(d)
        if not candy:
            self._toast("Place a candy first!")
            return None
        if not target:
            self._toast("Place a target first!")
            return None
        if not anchors and not magnets and not sliders and not winches:
            self._toast("Need at least one rope anchor!")
            return None
        return dict(
            name=self.inp_name.text.strip() or "Custom Level",
            candy=candy, target=target,
            star_times=[max(1, self.inp_star3.fval),
                        max(1, self.inp_star2.fval),
                        max(1, self.inp_star1.fval)],
            anchors=anchors, magnets=magnets, sliders=sliders,
            winches=winches, platforms=platforms, spikes=spikes,
            teleports=teleports, spiders=spiders,
        )

    def _save_level(self):
        d = self._build_dict()
        if not d:
            return
        self.levels = load_custom_levels()
        if 0 <= self.edit_idx < len(self.levels):
            self.levels[self.edit_idx] = d
        else:
            self.levels.append(d)
            self.edit_idx = len(self.levels) - 1
        save_custom_levels(self.levels)
        self._toast("Level saved!")

    def _load_level(self, idx):
        self.levels = load_custom_levels()
        if not (0 <= idx < len(self.levels)):
            return
        ld = self.levels[idx]
        self.edit_idx = idx
        self.entities.clear()
        self.sel = -1

        self.inp_name.text = ld.get("name", "Custom Level")
        st = ld.get("star_times", [5, 10, 20])
        if len(st) >= 3:
            self.inp_star3.text = str(st[0])
            self.inp_star2.text = str(st[1])
            self.inp_star1.text = str(st[2])

        c = ld.get("candy")
        if c:
            self.entities.append(EditorEntity("candy", c[0], to_pygame_y(c[1])))
        t = ld.get("target")
        if t:
            self.entities.append(EditorEntity("target", t[0], to_pygame_y(t[1]),
                                 radius=t[2] if len(t) > 2 else 30))
        for a in ld.get("anchors", []):
            self.entities.append(EditorEntity("anchor", a["x"], to_pygame_y(a["y"]),
                letter=a.get("letter", "A"), length=a.get("length", 180)))
        for m in ld.get("magnets", []):
            self.entities.append(EditorEntity("magnet", m["x"], to_pygame_y(m["y"]),
                letter=m.get("letter", "A"), radius=m.get("radius", 100)))
        for s in ld.get("sliders", []):
            ts = s.get("track_start", (s["x"] - 100, s["y"]))
            te = s.get("track_end", (s["x"] + 100, s["y"]))
            self.entities.append(EditorEntity("slider", s["x"], to_pygame_y(s["y"]),
                letter=s.get("letter", "A"),
                track_x1=ts[0], track_y1=to_pygame_y(ts[1]),
                track_x2=te[0], track_y2=to_pygame_y(te[1]),
                start_t=s.get("start_t", 0.5)))
        for w in ld.get("winches", []):
            self.entities.append(EditorEntity("winch", w["x"], to_pygame_y(w["y"]),
                letter=w.get("letter", "A"), length=w.get("length", 120)))
        for p in ld.get("platforms", []):
            self.entities.append(EditorEntity("platform",
                p["x1"], to_pygame_y(p["y1"]),
                x2=p["x2"], y2=to_pygame_y(p["y2"]),
                thickness=p.get("thickness", 8)))
        for s in ld.get("spikes", []):
            self.entities.append(EditorEntity("spike", s["x"], to_pygame_y(s["y"]),
                width=s.get("width", 80), height=s.get("height", 20),
                direction=s.get("direction", "up")))
        for tp in ld.get("teleports", []):
            self.entities.append(EditorEntity("teleport",
                tp["ax"], to_pygame_y(tp["ay"]),
                bx=tp["bx"], by=to_pygame_y(tp["by"]),
                angle_a=tp.get("angle_a", 0), angle_b=tp.get("angle_b", 0)))
        for sp in ld.get("spiders", []):
            self.entities.append(EditorEntity("spider", GAME_W // 2, GAME_H // 2,
                rope_index=sp.get("rope_index", 0),
                start_t=sp.get("start_t", 0.0), speed=sp.get("speed", 55)))

        self._rebuild_pins()
        self._reset_cam()
        self._toast("Loaded: " + ld.get("name", "level"))

    def _delete_level(self, idx):
        self.levels = load_custom_levels()
        if 0 <= idx < len(self.levels):
            self.levels.pop(idx)
            save_custom_levels(self.levels)
            if self.edit_idx == idx:
                self.edit_idx = -1
            elif self.edit_idx > idx:
                self.edit_idx -= 1
            self._toast("Level deleted")

    # ========================================================================
    #  Play Test
    # ========================================================================

    def _play_test(self):
        """Build the level and run it in-place. ESC / R / SPACE return to editor."""
        level_data = self._build_dict()
        if not level_data:
            return

        # Fill defaults expected by Game
        for key in ("anchors", "magnets", "sliders", "winches",
                    "platforms", "spikes", "teleports", "spiders"):
            if key not in level_data:
                level_data[key] = []

        try:
            from src.game import Game
            from src.types import GameState
        except ImportError as e:
            self._toast(f"Cannot import game: {e}")
            return

        self._toast("Starting play test...")
        pygame.display.set_caption("Cut The Rope - Play Test  (ESC = back to editor)")

        game = Game(level_data, -1)

        # We run a mini event loop inside the editor
        testing = True
        clock = pygame.time.Clock()
        scale = 1.0
        dest = pygame.Rect(0, 0, self.W, self.H)

        while testing:
            dt = min(clock.tick(60) / 1000.0, 0.05)

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    testing = False
                    pygame.display.set_caption("Cut The Rope - Level Editor")
                    return  # quit completely

                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        testing = False
                        break
                    if ev.key == pygame.K_r:
                        # Restart play test
                        game = Game(level_data, -1)
                        continue
                    if game.state == GameState.WON and ev.key == pygame.K_SPACE:
                        testing = False
                        break

                game.handle_event(ev, scale, dest)

            if not testing:
                break

            game.update(dt)
            scale, dest = game.draw(self.screen)
            pygame.display.flip()

        pygame.display.set_caption("Cut The Rope - Level Editor")
        self._toast("Back to editor")

    # ========================================================================
    #  Update
    # ========================================================================

    def _update(self, dt):
        if self._toast_t > 0:
            self._toast_t -= dt
        for inp in self._global_inputs:
            inp.update(dt)
        for inp in self._pins:
            inp.update(dt)
        self._apply_pins()

    # ========================================================================
    #  Drawing
    # ========================================================================

    def _draw(self):
        self.screen.fill(C_BG)
        self._draw_left()
        self._draw_canvas()
        self._draw_right()
        self._draw_toast()

    # -- left panel ----------------------------------------------------------

    def _draw_left(self):
        pygame.draw.rect(self.screen, C_PANEL, (0, 0, self.LEFT_W, self.H))
        pygame.draw.line(self.screen, C_PANEL_EDGE,
                         (self.LEFT_W - 1, 0), (self.LEFT_W - 1, self.H))

        t = self.font_lg.render("TOOLS", True, C_TEXT)
        self.screen.blit(t, (self.LEFT_W // 2 - t.get_width() // 2, 15))

        y = 60
        mx, my = pygame.mouse.get_pos()
        for etype, name, color, sc in TOOLS:
            btn = pygame.Rect(10, y, self.LEFT_W - 20, 36)
            active = self.mode == etype
            hover = btn.collidepoint(mx, my)
            if active:
                pygame.draw.rect(self.screen, C_ACCENT, btn, border_radius=8)
            elif hover:
                pygame.draw.rect(self.screen, C_HOVER, btn, border_radius=8)
            else:
                pygame.draw.rect(self.screen, (32, 36, 48), btn, border_radius=8)
            pygame.draw.circle(self.screen, color, (btn.x + 18, btn.centery), 7)
            lbl = self.font.render(f"{name} [{sc}]", True,
                                   C_TEXT if active else C_DIM)
            self.screen.blit(lbl, (btn.x + 32,
                                   btn.centery - lbl.get_height() // 2))
            y += 42

        y += 10
        pygame.draw.line(self.screen, C_PANEL_EDGE,
                         (15, y), (self.LEFT_W - 15, y))
        y += 15

        for label, col in [("New Level", C_ACCENT), ("Save Level", C_OK),
                           ("▶ Play Test", (220, 160, 50))]:
            btn = pygame.Rect(10, y, self.LEFT_W - 20, 32)
            hover = btn.collidepoint(mx, my)
            bc = tuple(min(255, c + 30) for c in col) if hover else col
            pygame.draw.rect(self.screen, bc, btn, border_radius=8)
            lbl = self.font.render(label, True, (255, 255, 255))
            self.screen.blit(lbl, (btn.centerx - lbl.get_width() // 2,
                                   btn.centery - lbl.get_height() // 2))
            y += 40

        y += 20
        for h in ["LClick: Place / Select",
                   "RClick: Delete entity",
                   "MidDrag: Pan canvas",
                   "Scroll: Zoom",
                   "Drag handle: Resize rope",
                   "R: Reset view",
                   "Del: Remove selected",
                   "F5: Play Test",
                   "ESC: Quit"]:
            self.screen.blit(self.font_sm.render(h, True, C_DIM), (15, y))
            y += 17

        y += 16
        self.screen.blit(
            self.font_md.render("Mode: " + self.mode.title(), True, C_ACCENT),
            (15, y))
        if self._step == 1:
            y += 22
            self.screen.blit(
                self.font_sm.render("Click 2nd point...", True, C_STAR_FILL),
                (15, y))

    # -- canvas --------------------------------------------------------------

    def _draw_canvas(self):
        cr = self._canvas_rect()
        pygame.draw.rect(self.screen, C_CANVAS_BG, cr)
        self.screen.set_clip(cr)

        step = 50
        wx0, wy0 = self.s2w(cr.x, cr.y)
        wx1, wy1 = self.s2w(cr.right, cr.bottom)
        gx0 = int(wx0 // step) * step
        gy0 = int(wy0 // step) * step
        for gx in range(gx0, int(wx1) + step, step):
            sx, _ = self.w2s(gx, 0)
            c = C_GRID_MAJ if gx % 200 == 0 else C_GRID
            pygame.draw.line(self.screen, c, (sx, cr.y), (sx, cr.bottom))
        for gy in range(gy0, int(wy1) + step, step):
            _, sy = self.w2s(0, gy)
            c = C_GRID_MAJ if gy % 200 == 0 else C_GRID
            pygame.draw.line(self.screen, c, (cr.x, sy), (cr.right, sy))

        bx0, by0 = self.w2s(0, 0)
        bx1, by1 = self.w2s(GAME_W, GAME_H)
        pygame.draw.rect(self.screen, (60, 70, 100),
                         pygame.Rect(bx0, by0, bx1 - bx0, by1 - by0), 2)
        self.screen.blit(self.font_sm.render(f"{GAME_W}x{GAME_H}", True, C_DIM),
                         (bx0 + 4, by0 + 2))

        for i, e in enumerate(self.entities):
            self._draw_ent(e, i == self.sel)

        if self._step == 1 and self._step_ent:
            mx, my = pygame.mouse.get_pos()
            if cr.collidepoint(mx, my):
                sx1, sy1 = self.w2s(self._step_ent.x, self._step_ent.y)
                if self._step_ent.type == "platform":
                    pygame.draw.line(self.screen, EC["platform"],
                                     (sx1, sy1), (mx, my), 4)
                elif self._step_ent.type == "teleport":
                    pygame.draw.line(self.screen, EC["teleport"],
                                     (sx1, sy1), (mx, my), 2)
                    pygame.draw.circle(self.screen, EC["teleport"],
                                       (mx, my), 12, 2)

        self.screen.set_clip(None)

    def _draw_ent(self, e, sel):
        sx, sy = self.w2s(e.x, e.y)
        r = max(6, int(14 * self.zoom))
        Z = self.zoom

        if e.type == "candy":
            pygame.draw.circle(self.screen, EC["candy"], (sx, sy), r)
            if sel:
                pygame.draw.circle(self.screen, C_SEL, (sx, sy), r + 3, 2)
            self.screen.blit(self.font_sm.render("Candy", True, C_TEXT),
                             (sx - 16, sy + r + 2))

        elif e.type == "target":
            tr = max(8, int(e.radius * Z))
            pygame.draw.circle(self.screen, EC["target"], (sx, sy), tr, 3)
            pygame.draw.circle(self.screen, EC["target"], (sx, sy),
                               max(3, tr // 3))
            if sel:
                pygame.draw.circle(self.screen, C_SEL, (sx, sy), tr + 3, 2)
            self.screen.blit(self.font_sm.render("Target", True, C_TEXT),
                             (sx - 18, sy + tr + 2))

        elif e.type in ("anchor", "winch"):
            col = EC[e.type]
            pygame.draw.circle(self.screen, col, (sx, sy), r)
            ey = sy + int(e.length * Z)
            pygame.draw.line(self.screen, col, (sx, sy), (sx, ey), 2)
            hr = max(5, int(7 * Z))
            pygame.draw.circle(self.screen, (255, 200, 100), (sx, ey), hr)
            pygame.draw.circle(self.screen, (200, 150, 60), (sx, ey), hr, 2)
            self.screen.blit(
                self.font_sm.render(f"{int(e.length)}px", True, C_DIM),
                (sx + hr + 4, ey - 6))
            if sel:
                pygame.draw.circle(self.screen, C_SEL, (sx, sy), r + 3, 2)
                pygame.draw.circle(self.screen, C_SEL, (sx, ey), hr + 3, 2)
            tag = e.letter
            if e.type == "winch":
                tag = "Wnc " + tag
            self.screen.blit(self.font_sm.render(tag, True, C_TEXT),
                             (sx - 12, sy - r - 16))

        elif e.type == "magnet":
            pygame.draw.circle(self.screen, EC["magnet"], (sx, sy), r)
            mr = max(8, int(e.radius * Z))
            pygame.draw.circle(self.screen, EC["magnet"], (sx, sy), mr, 1)
            if sel:
                pygame.draw.circle(self.screen, C_SEL, (sx, sy), r + 3, 2)
            self.screen.blit(self.font_sm.render("Mag " + e.letter, True, C_TEXT),
                             (sx - 18, sy - r - 16))

        elif e.type == "slider":
            tx1, ty1 = self.w2s(e.track_x1, e.track_y1)
            tx2, ty2 = self.w2s(e.track_x2, e.track_y2)
            pygame.draw.line(self.screen, EC["slider"],
                             (tx1, ty1), (tx2, ty2), 3)
            pygame.draw.circle(self.screen, EC["slider"], (sx, sy), r)
            pygame.draw.circle(self.screen, (120, 80, 180), (tx1, ty1), 5)
            pygame.draw.circle(self.screen, (120, 80, 180), (tx2, ty2), 5)
            if sel:
                pygame.draw.circle(self.screen, C_SEL, (sx, sy), r + 3, 2)
            self.screen.blit(
                self.font_sm.render("Sld " + e.letter, True, C_TEXT),
                (sx - 18, sy - r - 16))

        elif e.type == "platform":
            sx2, sy2 = self.w2s(e.x2, e.y2)
            th = max(2, int(e.thickness * Z))
            pygame.draw.line(self.screen, EC["platform"],
                             (sx, sy), (sx2, sy2), th)
            pygame.draw.circle(self.screen, (140, 145, 170), (sx, sy), 5)
            pygame.draw.circle(self.screen, (140, 145, 170), (sx2, sy2), 5)
            if sel:
                pygame.draw.circle(self.screen, C_SEL, (sx, sy), 8, 2)
                pygame.draw.circle(self.screen, C_SEL, (sx2, sy2), 8, 2)

        elif e.type == "spike":
            hw = max(5, int(e.width / 2 * Z))
            hh = max(3, int(e.height / 2 * Z))
            if e.direction == "up":
                pts = [(sx - hw, sy + hh), (sx + hw, sy + hh), (sx, sy - hh)]
            elif e.direction == "down":
                pts = [(sx - hw, sy - hh), (sx + hw, sy - hh), (sx, sy + hh)]
            elif e.direction == "left":
                pts = [(sx + hh, sy - hw), (sx + hh, sy + hw), (sx - hh, sy)]
            else:
                pts = [(sx - hh, sy - hw), (sx - hh, sy + hw), (sx + hh, sy)]
            pygame.draw.polygon(self.screen, EC["spike"], pts)
            if sel:
                pygame.draw.polygon(self.screen, C_SEL, pts, 2)

        elif e.type == "teleport":
            bsx, bsy = self.w2s(e.bx, e.by)
            pr = max(8, int(16 * Z))
            col_a = EC["teleport"]
            col_b = (220, 150, 255)
            pygame.draw.circle(self.screen, col_a, (sx, sy), pr, 3)
            pygame.draw.circle(self.screen, col_b, (bsx, bsy), pr, 3)
            pygame.draw.line(self.screen, (80, 60, 120),
                             (sx, sy), (bsx, bsy), 1)
            alen = max(10, int(22 * Z))
            for px, py, ang, col, lab in [
                (sx, sy, e.angle_a, col_a, "IN"),
                (bsx, bsy, e.angle_b, col_b, "OUT"),
            ]:
                ax = px + alen * math.cos(ang)
                ay = py - alen * math.sin(ang)
                pygame.draw.line(self.screen, col, (px, py),
                                 (int(ax), int(ay)), 3)
                hs = max(5, int(8 * Z))
                for s in (-1, 1):
                    hx = ax - hs * math.cos(ang + s * math.pi / 6)
                    hy = ay + hs * math.sin(ang + s * math.pi / 6)
                    pygame.draw.line(self.screen, col,
                                     (int(ax), int(ay)), (int(hx), int(hy)), 2)
                lbl = self.font_sm.render(lab, True, col)
                self.screen.blit(lbl, (px - lbl.get_width() // 2,
                                       py + pr + 2))
            if sel:
                pygame.draw.circle(self.screen, C_SEL, (sx, sy), pr + 2, 2)
                pygame.draw.circle(self.screen, C_SEL, (bsx, bsy), pr + 2, 2)

        elif e.type == "spider":
            pygame.draw.circle(self.screen, (50, 40, 50), (sx, sy), r)
            for side in (-1, 1):
                for j in range(3):
                    a = -0.5 + j * 0.5
                    lx = sx + side * int((r + 6) * math.cos(a))
                    ly = sy + int((r + 6) * math.sin(a))
                    pygame.draw.line(self.screen, (70, 60, 70),
                                     (sx + side * 3, sy), (lx, ly), 2)
            pygame.draw.circle(self.screen, (220, 40, 40),
                               (sx - 4, sy - 3), 3)
            pygame.draw.circle(self.screen, (220, 40, 40),
                               (sx + 4, sy - 3), 3)
            if sel:
                pygame.draw.circle(self.screen, C_SEL, (sx, sy), r + 3, 2)
            ropes = self._get_ropes()
            rl = "?"
            if 0 <= e.rope_index < len(ropes):
                _, rl, _ = ropes[e.rope_index]
                rope_ents = [ent for ent in self.entities
                             if ent.type in ("anchor", "magnet",
                                             "slider", "winch")]
                if e.rope_index < len(rope_ents):
                    re = rope_ents[e.rope_index]
                    rsx, rsy = self.w2s(re.x, re.y)
                    dx, dy = rsx - sx, rsy - sy
                    dist = math.hypot(dx, dy)
                    if dist > 1:
                        segs = max(1, int(dist / 12))
                        for si in range(0, segs, 2):
                            t1 = si / segs
                            t2 = min(1.0, (si + 1) / segs)
                            pygame.draw.line(self.screen, (180, 80, 80),
                                (int(sx + dx * t1), int(sy + dy * t1)),
                                (int(sx + dx * t2), int(sy + dy * t2)), 1)
            lbl = self.font_sm.render(f"Spider -> {rl}", True, C_TEXT)
            self.screen.blit(lbl, (sx - lbl.get_width() // 2, sy + r + 2))

    # -- right panel ---------------------------------------------------------

    def _draw_right(self):
        rx = self.W - self.RIGHT_W
        pw = self.RIGHT_W
        M = 15                       # horizontal margin inside panel
        inner = pw - 2 * M           # usable width

        pygame.draw.rect(self.screen, C_PANEL, (rx, 0, pw, self.H))
        pygame.draw.line(self.screen, C_PANEL_EDGE, (rx, 0), (rx, self.H))

        # ── running Y cursor ──
        py = 10

        # ── LEVEL INFO section ────────────────────────────────
        hdr = self.font_lg.render("LEVEL", True, C_ACCENT)
        self.screen.blit(hdr, (rx + pw // 2 - hdr.get_width() // 2, py))
        py += hdr.get_height() + 8

        # Level name
        lbl = self.font_sm.render("Level Name", True, C_DIM)
        self.screen.blit(lbl, (rx + M, py))
        py += lbl.get_height() + 3
        self.inp_name.rect = pygame.Rect(rx + M, py, inner, 24)
        self.inp_name.draw(self.screen)
        py += 30

        # Star times
        lbl = self.font_sm.render("Star Times (seconds)", True, C_DIM)
        self.screen.blit(lbl, (rx + M, py))
        py += lbl.get_height() + 3

        col_w = (inner - 10) // 3    # width per star column
        gap = 5
        star_labels = [("★★★", self.inp_star3),
                       ("★★", self.inp_star2),
                       ("★", self.inp_star1)]
        for idx, (sym, inp) in enumerate(star_labels):
            cx = rx + M + idx * (col_w + gap)
            sl = self.font_sm.render(sym, True, C_STAR_FILL)
            self.screen.blit(sl, (cx + 2, py))
            inp.rect = pygame.Rect(cx, py + sl.get_height() + 2, col_w, 22)
            inp.draw(self.screen)
        py += 16 + 22 + 6   # star label + input + padding

        # ── divider ───────────────────────────────────────────
        py += 4
        pygame.draw.line(self.screen, C_PANEL_EDGE,
                         (rx + 10, py), (rx + pw - 10, py))
        py += 8

        # ── SELECTION / PROPERTIES ────────────────────────────
        self._rope_btns = []
        self._angle_btns = []

        # Reserve bottom 1/3 for saved levels (at least 160px)
        SAVED_MIN_H = 160
        saved_top = self.H - SAVED_MIN_H

        if 0 <= self.sel < len(self.entities):
            e = self.entities[self.sel]

            # Type header badge
            type_col = EC.get(e.type, C_ACCENT)
            hdr_rect = pygame.Rect(rx + 10, py, inner + 10, 24)
            # Draw a tinted background
            hdr_s = pygame.Surface((hdr_rect.w, hdr_rect.h), pygame.SRCALPHA)
            hdr_s.fill((*type_col, 45))
            self.screen.blit(hdr_s, hdr_rect.topleft)
            pygame.draw.rect(self.screen, type_col, hdr_rect, 1, border_radius=5)
            tl = self.font_md.render(e.type.upper(), True, C_TEXT)
            self.screen.blit(tl, (hdr_rect.x + 8, hdr_rect.centery - tl.get_height() // 2))
            py += 30

            # Coordinates
            cl = self.font_sm.render(
                f"Position: ({int(e.x)}, {int(e.y)})", True, C_DIM)
            self.screen.blit(cl, (rx + M, py))
            py += cl.get_height() + 8

            # ── Property inputs ───────────────────────────────
            if self._pins:
                sl = self.font.render("Properties", True, C_TEXT)
                self.screen.blit(sl, (rx + M, py))
                py += sl.get_height() + 6
                for inp in self._pins:
                    # Label above the input
                    if inp.label:
                        ll = self.font_sm.render(inp.label, True, C_DIM)
                        self.screen.blit(ll, (rx + M, py))
                        py += ll.get_height() + 2
                    inp.rect = pygame.Rect(rx + M, py, inner, 22)
                    # Don't let TextInput.draw re-draw label (set to empty temporarily)
                    saved_label = inp.label
                    inp.label = ""
                    inp.draw(self.screen)
                    inp.label = saved_label
                    py += 28
                py += 4

            # ── Spider rope picker ────────────────────────────
            if e.type == "spider":
                ropes = self._get_ropes()
                if ropes:
                    sl = self.font.render("Attach to Rope", True, C_TEXT)
                    self.screen.blit(sl, (rx + M, py))
                    py += sl.get_height() + 6
                    bx = rx + M
                    mx2, my2 = pygame.mouse.get_pos()
                    for ri, rletter, rtype in ropes:
                        active = e.rope_index == ri
                        btn = pygame.Rect(bx, py, 40, 26)
                        hov = btn.collidepoint(mx2, my2)
                        bc = C_ACCENT if active else (C_HOVER if hov else (38, 42, 55))
                        pygame.draw.rect(self.screen, bc, btn, border_radius=5)
                        pygame.draw.rect(self.screen, C_PANEL_EDGE, btn, 1,
                                         border_radius=5)
                        t = self.font.render(rletter, True,
                                             (255, 255, 255) if active else C_TEXT)
                        self.screen.blit(t, (btn.centerx - t.get_width() // 2,
                                             btn.centery - t.get_height() // 2))
                        self._rope_btns.append((btn, ri))
                        bx += 46
                        if bx + 40 > rx + pw - 10:
                            bx = rx + M
                            py += 32
                    py += 32
                    if 0 <= e.rope_index < len(ropes):
                        _, sl_l, st_l = ropes[e.rope_index]
                        il = self.font_sm.render(
                            f"Attached to: {sl_l} ({st_l})", True, C_OK)
                        self.screen.blit(il, (rx + M, py))
                        py += il.get_height() + 4
                else:
                    wl = self.font_sm.render(
                        "⚠ No ropes! Place an anchor.", True, C_BAD)
                    self.screen.blit(wl, (rx + M, py))
                    py += wl.get_height() + 4

            # ── Teleport angle controls ───────────────────────
            if e.type == "teleport":
                py += 4
                mx2, my2 = pygame.mouse.get_pos()
                for label, col, ang, prefix in [
                    ("Entry (IN)", EC["teleport"], e.angle_a, "a"),
                    ("Exit (OUT)", (220, 150, 255), e.angle_b, "b"),
                ]:
                    sl = self.font.render(label, True, col)
                    self.screen.blit(sl, (rx + M, py))
                    py += sl.get_height() + 4

                    # Direction name + rotate buttons on same row
                    dn = deg_name(ang)
                    dl = self.font_md.render(dn, True, C_TEXT)
                    self.screen.blit(dl, (rx + M, py))

                    btn_w, btn_h = 34, 24
                    rb = pygame.Rect(rx + pw - M - btn_w, py, btn_w, btn_h)
                    lb = pygame.Rect(rb.x - btn_w - 4, py, btn_w, btn_h)
                    for btn, sym, act in [(lb, "◀", prefix + "+"),
                                          (rb, "▶", prefix + "-")]:
                        hov = btn.collidepoint(mx2, my2)
                        pygame.draw.rect(
                            self.screen,
                            C_HOVER if hov else (38, 42, 55),
                            btn, border_radius=5)
                        pygame.draw.rect(self.screen, col, btn, 1,
                                         border_radius=5)
                        st = self.font_md.render(sym, True, col)
                        self.screen.blit(st,
                            (btn.centerx - st.get_width() // 2,
                             btn.centery - st.get_height() // 2))
                        self._angle_btns.append((btn, act))
                    py += max(dl.get_height(), btn_h) + 8

                # Short help
                for h in ["IN = where candy enters",
                           "OUT = where candy exits"]:
                    hl = self.font_sm.render(h, True, C_DIM)
                    self.screen.blit(hl, (rx + M, py))
                    py += hl.get_height() + 2
                py += 4

            # ── Context tips ──────────────────────────────────
            hints = {
                "anchor":   ["Drag orange handle to resize rope."],
                "winch":    ["Drag handle to resize.",
                              "Shift+Key = Retract.",
                              "Ctrl+Key = Extend.",
                              "Key alone = Cut."],
                "candy":    ["The ball the player must",
                              "feed to the target."],
                "target":   ["Feed the candy in here!"],
                "platform": ["Drag endpoints to reshape.",
                              "Candy bounces off walls."],
                "spike":    ["Direction: up/down/left/right.",
                              "Candy pops on contact!"],
                "magnet":   ["Pulls candy when in range."],
                "slider":   ["Rope slides along a track.",
                              "Drag track ends in select mode."],
                "spider":   ["Crawls down rope toward candy.",
                              "Choose which rope above."],
                "teleport": ["Drag each portal separately.",
                              "Set entry/exit angles above."],
            }
            if e.type in hints and py < saved_top - 30:
                pygame.draw.line(self.screen, C_PANEL_EDGE,
                                 (rx + 10, py), (rx + pw - 10, py))
                py += 6
                tl = self.font_sm.render("💡 Tips", True, C_DIM)
                self.screen.blit(tl, (rx + M, py))
                py += tl.get_height() + 4
                for h in hints[e.type]:
                    if py >= saved_top - 14:
                        break
                    hl = self.font_sm.render(h, True, C_DIM)
                    self.screen.blit(hl, (rx + M + 4, py))
                    py += hl.get_height() + 2
        else:
            nl = self.font.render("No selection", True, C_DIM)
            self.screen.blit(nl, (rx + M, py + 4))
            sl = self.font_sm.render("Click an entity or place one", True, C_DIM)
            self.screen.blit(sl, (rx + M, py + 24))
            py += 50

        # ── SAVED LEVELS section (always at bottom) ───────────
        # Ensure a divider between properties and saved levels
        saved_y = max(py + 12, saved_top)
        pygame.draw.line(self.screen, C_PANEL_EDGE,
                         (rx + 10, saved_y - 6),
                         (rx + pw - 10, saved_y - 6))

        sl = self.font_md.render("Saved Levels", True, C_TEXT)
        self.screen.blit(sl, (rx + M, saved_y))
        saved_y += sl.get_height() + 6

        self._saved_btns = []
        self._saved_del = []
        self.levels = load_custom_levels()

        list_top = saved_y
        list_h = self.H - list_top - 8
        clip = pygame.Rect(rx, list_top, pw, list_h)
        self.screen.set_clip(clip)

        iy = list_top - self._saved_scroll
        mx, my = pygame.mouse.get_pos()
        ROW_H = 32

        for i, cl in enumerate(self.levels):
            name = cl.get("name", f"Level {i + 1}")
            btn = pygame.Rect(rx + 10, iy, inner - 36, ROW_H - 4)
            hov = btn.collidepoint(mx, my)
            act = i == self.edit_idx
            bc = C_ACCENT if act else (C_HOVER if hov else (38, 42, 55))
            pygame.draw.rect(self.screen, bc, btn, border_radius=5)
            tl = self.font_sm.render(name[:22], True, C_TEXT)
            self.screen.blit(tl, (btn.x + 6, btn.centery - tl.get_height() // 2))
            self._saved_btns.append((btn, i))

            db = pygame.Rect(rx + pw - M - 28, iy, 28, ROW_H - 4)
            dh = db.collidepoint(mx, my)
            pygame.draw.rect(self.screen,
                             C_BAD if dh else (80, 40, 40),
                             db, border_radius=5)
            xt = self.font_sm.render("X", True, C_TEXT)
            self.screen.blit(xt, (db.centerx - xt.get_width() // 2,
                                  db.centery - xt.get_height() // 2))
            self._saved_del.append((db, i))
            iy += ROW_H

        if not self.levels:
            nl = self.font_sm.render("No saved levels yet", True, C_DIM)
            self.screen.blit(nl, (rx + M, list_top + 4))

        # Clamp scroll
        max_scroll = max(0, len(self.levels) * ROW_H - list_h)
        self._saved_scroll = clamp(self._saved_scroll, 0, max_scroll)

        self.screen.set_clip(None)

    # -- toast ---------------------------------------------------------------

    def _draw_toast(self):
        if self._toast_t > 0 and self._toast_msg:
            alpha = min(1.0, self._toast_t * 3)
            txt = self.font_md.render(self._toast_msg, True, C_OK)
            tw = txt.get_width()
            tx = self.W // 2 - tw // 2
            ty = self.H - 50
            bg = pygame.Surface((tw + 24, 32), pygame.SRCALPHA)
            bg.fill((0, 0, 0, int(160 * alpha)))
            self.screen.blit(bg, (tx - 12, ty - 4))
            txt.set_alpha(int(255 * alpha))
            self.screen.blit(txt, (tx, ty))

    # ========================================================================
    #  Main loop
    # ========================================================================

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            running = self._events()
            self._update(dt)
            self._draw()
            pygame.display.flip()
        pygame.quit()


if __name__ == "__main__":
    LevelEditor().run()
