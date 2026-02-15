"""
Main game loop for Cut The Rope.

Integrates physics, entities, rendering, and input handling for:
  - Letter-key rope cutting (A/B/C)
  - Slider anchor mouse drag
  - Winch anchor keyboard extend/retract (Shift/Ctrl + letter)
  - Magnet anchor auto-attach
  - Teleportation (magic hats)
  - Spiders (rope-crawling lose condition)
  - Spikes (instant lose)
"""

import math
import time as _time
import pygame
import pymunk

from .config import (
    WIDTH, HEIGHT, PYMUNK_HEIGHT, FPS,
    COLOR_PARTICLE_CUT, COLOR_PARTICLE_SUCCESS, COLOR_PARTICLE_STAR,
    WINCH_MIN_LENGTH, WINCH_MAX_LENGTH,
    FONT_FAMILY, FONT_SIZE_SMALL, FONT_SIZE_NORMAL,
    COLOR_TEXT, COLOR_TEXT_SHADOW, COLOR_TEXT_HIGHLIGHT,
    ROPE_SEGMENT_LENGTH,
)
from .entities import (
    Candy, Target, Anchor, MagnetAnchor, SliderAnchor, WinchAnchor,
    Platform, Spike, TeleportPair, Spider, draw_rope,
)
from .physics import PhysicsWorld
from .renderer import Renderer
from .utils import pymunk_to_pygame, pygame_to_pymunk, distance, clamp
from .savedata import save_level_score, get_star_times


def _draw_star_shape(surface, cx, cy, size, filled=True):
    """Draw a 5-pointed star centered at (cx, cy)."""
    points = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        r = size if i % 2 == 0 else size * 0.4
        points.append((cx + r * math.cos(angle), cy - r * math.sin(angle)))
    if filled:
        pygame.draw.polygon(surface, (255, 220, 50), points)
        pygame.draw.polygon(surface, (200, 170, 30), points, 2)
    else:
        pygame.draw.polygon(surface, (80, 80, 80), points)
        pygame.draw.polygon(surface, (120, 120, 120), points, 2)


class GameState:
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


class Game:
    """Manages a single level of Cut The Rope."""

    def __init__(self, level_data: dict, level_index: int = 0):
        self.level_data = level_data
        self.level_index = level_index
        self.state = GameState.PLAYING
        self.time_elapsed = 0.0
        self.win_timer = 0.0
        self.lose_timer = 0.0
        self.lose_reason = ""

        self.renderer = Renderer()

        # Physics
        self.physics = PhysicsWorld()

        # Create entities from level data
        self._create_entities()

        # Setup collision callbacks
        self.physics.setup_collisions(
            on_target=self._on_candy_target,
            on_spike=self._on_candy_spike,
            on_tele_a=self._on_teleport_a,
            on_tele_b=self._on_teleport_b,
        )

        # Input state
        self._mouse_down = False
        self._mouse_pos = (0, 0)
        self._mouse_pymunk = (0.0, 0.0)
        self._dragging_slider = None

        # HUD font
        try:
            self._font_sm = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_SMALL)
            self._font_md = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_NORMAL)
        except Exception:
            self._font_sm = pygame.font.Font(None, FONT_SIZE_SMALL)
            self._font_md = pygame.font.Font(None, FONT_SIZE_NORMAL)

    # -- entity creation -----------------------------------------------

    def _create_entities(self):
        ld = self.level_data

        # Candy
        cx, cy = ld["candy"]
        self.candy = Candy(cx, cy)
        self.candy.add_to_space(self.physics.space)

        # Target
        tx, ty, tr = ld["target"]
        self.target = Target(tx, ty, tr)
        self.target.add_to_space(self.physics.space)

        # Build all anchor types and their ropes
        self.anchors = []
        self.magnets = []
        self.sliders = []
        self.winches = []
        self.platforms = []
        self.spikes_list = []
        self.teleports = []
        self.spiders = []
        self.rope_datas = []  # all RopeData objects

        # Static anchors
        for i, ad in enumerate(ld.get("anchors", [])):
            a = Anchor(ad["x"], ad["y"], ad.get("letter", ""))
            self.anchors.append(a)
            length = ad.get("length", 200)
            rd = self.physics.create_rope(
                a.body, self.candy.body, length,
                letter=ad.get("letter", ""),
                group=i + 1,
            )
            self.rope_datas.append(rd)

        # Magnet anchors
        for ad in ld.get("magnets", []):
            m = MagnetAnchor(ad["x"], ad["y"], ad.get("radius", 90), ad.get("letter", ""))
            self.magnets.append(m)

        # Slider anchors
        for i, sd in enumerate(ld.get("sliders", [])):
            s = SliderAnchor(
                sd["x"], sd["y"],
                tuple(sd["track_start"]), tuple(sd["track_end"]),
                sd.get("letter", ""), sd.get("start_t", 0.5),
            )
            self.sliders.append(s)
            length = sd.get("length", 200)
            rd = self.physics.create_rope(
                s.body, self.candy.body, length,
                letter=sd.get("letter", ""),
                group=100 + i,
            )
            s.rope_data = rd
            self.rope_datas.append(rd)

        # Winch anchors
        for i, wd in enumerate(ld.get("winches", [])):
            w = WinchAnchor(wd["x"], wd["y"], wd.get("letter", ""),
                            wd.get("length", 200))
            self.winches.append(w)
            rd = self.physics.create_rope(
                w.body, self.candy.body, w.current_length,
                letter=wd.get("letter", ""),
                group=200 + i,
            )
            w.rope_data = rd
            self.rope_datas.append(rd)

        # Platforms
        for pd in ld.get("platforms", []):
            p = Platform(pd["x1"], pd["y1"], pd["x2"], pd["y2"],
                         pd.get("thickness", 8))
            p.add_to_space(self.physics.space)
            self.platforms.append(p)

        # Spikes
        for sd in ld.get("spikes", []):
            s = Spike(sd["x"], sd["y"], sd.get("width", 60),
                      sd.get("height", 20), sd.get("direction", "up"))
            s.add_to_space(self.physics.space)
            self.spikes_list.append(s)

        # Teleports
        for td in ld.get("teleports", []):
            tp = TeleportPair(
                td["ax"], td["ay"], td["bx"], td["by"],
                td.get("angle_a", 0), td.get("angle_b", 0),
            )
            tp.add_to_space(self.physics.space)
            self.teleports.append(tp)

        # Spiders
        for sd in ld.get("spiders", []):
            sp = Spider(sd["rope_index"], sd.get("start_t", 0.0),
                        sd.get("speed", 55))
            self.spiders.append(sp)

    # -- collision callbacks -------------------------------------------

    def _on_candy_target(self):
        if self.state == GameState.PLAYING:
            self.state = GameState.WON
            # Store candy position for swallow animation, then start it
            self.target._candy_draw_pos = self.candy.get_pygame_pos()
            self.target.start_swallow()
            # Hide candy from physics (move off-screen or freeze)
            self.candy.body.body_type = pymunk.Body.STATIC
            px, py = self.target.get_pygame_pos()
            self.renderer.particle_system.emit_burst(
                px, py, COLOR_PARTICLE_SUCCESS, count=30, speed=300)
            save_level_score(self.level_index, self.time_elapsed)

    def _on_candy_spike(self):
        if self.state == GameState.PLAYING:
            self.state = GameState.LOST
            self.lose_reason = "Hit spikes!"
            px, py = self.candy.get_pygame_pos()
            self.renderer.particle_system.emit_burst(
                px, py, (255, 100, 100), count=25, speed=250)

    def _on_teleport_a(self):
        if self.state != GameState.PLAYING:
            return
        for tp in self.teleports:
            if tp.can_teleport():
                # Check candy is near hat A
                d = distance(self.candy.body.position, tp.body_a.position)
                if d < 60:
                    tp.teleport(self.candy.body, entry_is_a=True)
                    pa = pymunk_to_pygame(tp.body_a.position)
                    pb = pymunk_to_pygame(tp.body_b.position)
                    self.renderer.particle_system.emit_burst(
                        pa[0], pa[1], (180, 100, 255), 15, 200)
                    self.renderer.particle_system.emit_burst(
                        pb[0], pb[1], (100, 220, 255), 15, 200)
                    break

    def _on_teleport_b(self):
        if self.state != GameState.PLAYING:
            return
        for tp in self.teleports:
            if tp.can_teleport():
                d = distance(self.candy.body.position, tp.body_b.position)
                if d < 60:
                    tp.teleport(self.candy.body, entry_is_a=False)
                    pa = pymunk_to_pygame(tp.body_a.position)
                    pb = pymunk_to_pygame(tp.body_b.position)
                    self.renderer.particle_system.emit_burst(
                        pb[0], pb[1], (100, 220, 255), 15, 200)
                    self.renderer.particle_system.emit_burst(
                        pa[0], pa[1], (180, 100, 255), 15, 200)
                    break

    # -- input ---------------------------------------------------------

    def handle_event(self, event: pygame.event.Event, scale: float,
                     dest_rect: pygame.Rect):
        if self.state != GameState.PLAYING:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._mouse_down = True
            vpos = self.renderer.window_to_virtual(event.pos, scale, dest_rect)
            self._mouse_pos = vpos
            self._mouse_pymunk = pygame_to_pymunk(vpos)
            self.renderer.update_trail(vpos)

            # Check slider drag start
            for sl in self.sliders:
                if sl.start_drag(self._mouse_pymunk):
                    self._dragging_slider = sl
                    break

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse_down = False
            self.renderer.clear_trail()
            if self._dragging_slider:
                self._dragging_slider.end_drag()
                self._dragging_slider = None

        elif event.type == pygame.MOUSEMOTION:
            vpos = self.renderer.window_to_virtual(event.pos, scale, dest_rect)
            self._mouse_pos = vpos
            self._mouse_pymunk = pygame_to_pymunk(vpos)

            if self._mouse_down:
                self.renderer.update_trail(vpos)

            # Slider dragging
            if self._dragging_slider:
                self._dragging_slider.update_drag(self._mouse_pymunk)

        elif event.type == pygame.KEYDOWN:
            self._handle_key(event)

    def _handle_key(self, event):
        """Handle letter-key cutting + winch extend/retract."""
        key_name = pygame.key.name(event.key).upper()

        # Only handle single letter keys A-Z
        if len(key_name) != 1 or not key_name.isalpha():
            return

        mods = pygame.key.get_mods()
        shift = mods & pygame.KMOD_SHIFT
        ctrl = mods & (pygame.KMOD_CTRL | pygame.KMOD_META)

        # Check winch anchors first for Shift/Ctrl + letter
        for w in self.winches:
            if w.letter == key_name and w.active:
                if shift:
                    return  # Retract handled continuously in update
                elif ctrl:
                    return  # Extend handled continuously in update
                else:
                    # Plain letter = cut the winch rope
                    self._cut_by_letter(key_name)
                    w.active = False
                    return

        # Plain letter = cut rope
        self._cut_by_letter(key_name)

    def _cut_by_letter(self, letter: str):
        """Cut rope by letter and emit particles."""
        rd = self.physics.cut_rope_by_letter(letter)
        if rd:
            if rd in self.rope_datas:
                self.rope_datas.remove(rd)
            # Particles at anchor position
            if rd.anchor_body:
                px, py = pymunk_to_pygame(rd.anchor_body.position)
                self.renderer.particle_system.emit(
                    px, py, COLOR_PARTICLE_CUT, count=15, speed=150)
            # Deactivate magnet anchors with this letter
            for m in self.magnets:
                if m.letter == letter.upper() and m.state == "active":
                    m.deactivate()

    # -- update --------------------------------------------------------

    def update(self, dt: float):
        if self.state == GameState.WON:
            self.win_timer += dt
            self.renderer.update(dt)
            return
        if self.state == GameState.LOST:
            self.lose_timer += dt
            self.renderer.update(dt)
            return

        self.time_elapsed += dt

        # Winch keyboard hold (continuous)
        keys = pygame.key.get_pressed()
        mods = pygame.key.get_mods()
        for w in self.winches:
            if not w.active or not w.letter:
                continue
            key_code = getattr(pygame, f"K_{w.letter.lower()}", None)
            if key_code and keys[key_code]:
                if mods & pygame.KMOD_SHIFT:
                    w.retract(dt)
                elif mods & (pygame.KMOD_CTRL | pygame.KMOD_META):
                    w.extend(dt)
            w.update(dt)
            # Adjust rope physics
            if w.rope_data and w.rope_data in self.rope_datas:
                self.physics.adjust_winch_rope(w.rope_data, w.current_length)

        # Physics step
        self.physics.step(dt)

        # Candy update
        self.candy.update(dt)

        # Target update
        self.target.update(dt)

        # Teleports
        for tp in self.teleports:
            tp.update(dt)

        # Magnet auto-attach check
        candy_pos = self.candy.body.position
        for m in self.magnets:
            if m.check_candy(candy_pos):
                # Create rope dynamically
                d = distance((m.x, m.y), candy_pos)
                rd = self.physics.create_rope(
                    m.body, self.candy.body, d,
                    letter=m.letter,
                    group=300 + self.magnets.index(m),
                )
                m.activate()
                m.rope_data = rd
                self.rope_datas.append(rd)
                # Particle effect
                px, py = m.get_pygame_pos()
                self.renderer.particle_system.emit(
                    px, py, (100, 180, 255), count=12, speed=120)

        # Spiders
        for sp in self.spiders:
            if sp.rope_index < len(self.rope_datas):
                rd = self.rope_datas[sp.rope_index] if sp.rope_index < len(self.rope_datas) else None
                if rd:
                    result = sp.update(dt, rd.bodies)
                    if result == "caught" or sp.check_catch(candy_pos):
                        if self.state == GameState.PLAYING:
                            self.state = GameState.LOST
                            self.lose_reason = "Spider caught the candy!"
                            spx, spy = sp.get_pygame_pos()
                            self.renderer.particle_system.emit_burst(
                                spx, spy, (100, 50, 50), 20, 200)

        # Check if candy fell off screen
        if candy_pos.y < -100 or candy_pos.x < -100 or candy_pos.x > WIDTH + 100:
            if self.state == GameState.PLAYING:
                self.state = GameState.LOST
                self.lose_reason = "Candy fell off!"

        # Renderer
        self.renderer.update(dt)

    # -- draw ----------------------------------------------------------

    def draw(self, window_surface: pygame.Surface) -> tuple:
        """Draw everything. Returns (scale, dest_rect) for input mapping."""
        surf = self.renderer.virtual_surface
        self.renderer.begin_frame()

        t = self.time_elapsed

        # Platforms
        for p in self.platforms:
            p.draw(surf, t)

        # Spikes
        for s in self.spikes_list:
            s.draw(surf, t)

        # Teleports
        for tp in self.teleports:
            tp.draw(surf, t)

        # Ropes
        for rd in self.rope_datas:
            bodies = self.physics.get_rope_bodies_with_endpoints(rd, self.candy.body)
            draw_rope(surf, bodies, time=t)

        # Anchors
        for a in self.anchors:
            a.draw(surf, t)
        for m in self.magnets:
            m.draw(surf, t)
        for sl in self.sliders:
            sl.draw(surf, t)
        for w in self.winches:
            w.draw(surf, t)

        # Spiders
        for sp in self.spiders:
            sp.draw(surf, t)

        # Target
        self.target.draw(surf, t)

        # Candy (hidden during/after swallow - target draws it)
        if not self.target.collected:
            self.candy.draw(surf, t)

        # HUD
        self._draw_hud(surf)

        # Win/Lose overlay
        if self.state == GameState.WON:
            self._draw_win_overlay(surf)
        elif self.state == GameState.LOST:
            self._draw_lose_overlay(surf)

        return self.renderer.end_frame(window_surface)

    def _draw_hud(self, surface):
        """Draw time and controls info."""
        # Time
        t_str = f"Time: {self.time_elapsed:.1f}s"
        txt = self._font_sm.render(t_str, True, COLOR_TEXT)
        shadow = self._font_sm.render(t_str, True, COLOR_TEXT_SHADOW)
        surface.blit(shadow, (16, 16))
        surface.blit(txt, (15, 15))

        # Level name
        name = self.level_data.get("name", f"Level {self.level_index + 1}")
        ntxt = self._font_sm.render(name, True, COLOR_TEXT)
        surface.blit(ntxt, (WIDTH - ntxt.get_width() - 15, 15))

        # Controls hints at bottom
        hints = []
        letters_used = set()
        for a in self.anchors:
            if a.letter and a.active:
                letters_used.add(a.letter)
        for rd in self.rope_datas:
            if rd.letter:
                letters_used.add(rd.letter)
        for w in self.winches:
            if w.letter and w.active:
                hints.append(f"Shift+{w.letter}=Retract  Ctrl+{w.letter}=Extend  {w.letter}=Cut")
        for sl in self.sliders:
            if sl.letter:
                hints.append(f"Drag {sl.letter} slider  {sl.letter}=Cut")

        # Show cut keys
        cut_letters = sorted(letters_used)
        if cut_letters and not hints:
            hints.append("Press " + "/".join(cut_letters) + " to cut rope")
        if self.sliders:
            hints.append("Click+drag slider handle to move")

        y = HEIGHT - 20
        for h in reversed(hints):
            htxt = self._font_sm.render(h, True, (*COLOR_TEXT[:3],))
            surface.blit(htxt, (WIDTH // 2 - htxt.get_width() // 2, y - htxt.get_height()))
            y -= htxt.get_height() + 4

    def _draw_win_overlay(self, surface):
        alpha = min(1.0, self.win_timer * 2)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(120 * alpha)))
        surface.blit(overlay, (0, 0))

        txt = self._font_md.render("Level Complete!", True, COLOR_PARTICLE_SUCCESS)
        tw, th = txt.get_size()
        surface.blit(txt, (WIDTH // 2 - tw // 2, HEIGHT // 2 - 100))

        t_str = f"Time: {self.time_elapsed:.2f}s"
        ttxt = self._font_sm.render(t_str, True, COLOR_TEXT)
        surface.blit(ttxt, (WIDTH // 2 - ttxt.get_width() // 2, HEIGHT // 2 - 50))

        # Star rating – use level_data star_times first (works for custom levels too)
        st = self.level_data.get("star_times") or get_star_times(self.level_index)
        if st and len(st) >= 3:
            stars_earned = 3 if self.time_elapsed <= st[0] else (2 if self.time_elapsed <= st[1] else 1)
        else:
            stars_earned = 1
        star_y = HEIGHT // 2 - 5
        star_size = 24
        gap = 60
        start_x = WIDTH // 2 - gap
        for i in range(3):
            sx = start_x + i * gap
            filled = i < stars_earned
            _draw_star_shape(surface, sx, star_y, star_size, filled)

        # Star time thresholds
        if st and len(st) >= 3:
            info = f"★★★ < {st[0]}s   ★★ < {st[1]}s   ★ < {st[2]}s"
            itxt = self._font_sm.render(info, True, (180, 180, 140))
            surface.blit(itxt, (WIDTH // 2 - itxt.get_width() // 2, star_y + 35))

        if self.win_timer > 1.0:
            hint = self._font_sm.render("SPACE = Next  |  R = Retry  |  ESC = Menu",
                                        True, COLOR_TEXT)
            surface.blit(hint, (WIDTH // 2 - hint.get_width() // 2, star_y + 70))

    def _draw_lose_overlay(self, surface):
        alpha = min(1.0, self.lose_timer * 2)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(120 * alpha)))
        surface.blit(overlay, (0, 0))

        txt = self._font_md.render(self.lose_reason or "Level Failed!", True, (255, 100, 100))
        tw, th = txt.get_size()
        surface.blit(txt, (WIDTH // 2 - tw // 2, HEIGHT // 2 - 40))

        if self.lose_timer > 1.0:
            hint = self._font_sm.render("Press R to retry  |  ESC for menu", True, COLOR_TEXT)
            surface.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 20))
