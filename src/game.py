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

import pygame
import pymunk

from .config import (
    WIDTH,
    COLOR_PARTICLE_SUCCESS,
    FONT_FAMILY, FONT_SIZE_SMALL, FONT_SIZE_NORMAL,
)
from .entities import (
    Candy, Target, Anchor, MagnetAnchor, SliderAnchor, WinchAnchor,
    Platform, Spike, TeleportPair, Spider,
)
from .game_renderer import draw_game_frame
from .input_handler import InputHandler
from .physics import PhysicsWorld
from .renderer import Renderer
from .types import GameState
from .utils import pymunk_to_pygame, distance
from .savedata import save_level_score


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
        self.input_handler = InputHandler()

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
        """Delegate input handling to InputHandler."""
        self.input_handler.handle_event(self, event, scale, dest_rect)

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
        """Draw everything. Delegates to game_renderer."""
        return draw_game_frame(self, window_surface)
