"""
All game entities for Cut The Rope.

Entity list (per design docs):
  Candy          - the physics body the player must deliver
  Target         - the "mouth" that eats the candy
  Anchor         - static hook (rope origin)
  MagnetAnchor   - auto-attach when candy enters radius
  SliderAnchor   - mouse-draggable hook on a track
  WinchAnchor    - keyboard-controlled extend / retract rope
  Platform       - static collision surface
  Spike          - instant-kill obstacle
  TeleportPair   - magic hat portals (momentum-preserving)
  Spider         - rope-crawling antagonist (lose condition)
"""

import math
import pygame
import pymunk

from .config import (
    WIDTH, HEIGHT, PYMUNK_HEIGHT,
    CANDY_MASS, CANDY_RADIUS, CANDY_FRICTION, CANDY_ELASTICITY,
    ROPE_SEGMENT_LENGTH, ROPE_WIDTH,
    COLOR_CANDY, COLOR_CANDY_HIGHLIGHT, COLOR_CANDY_SHADOW,
    COLOR_CANDY_STRIPE, COLOR_CANDY_SHINE, COLOR_CANDY_DEEP,
    COLOR_ANCHOR, COLOR_ANCHOR_CORE, COLOR_ANCHOR_GLOW, COLOR_ANCHOR_RING,
    COLOR_ROPE, COLOR_ROPE_SHADOW,
    COLOR_TARGET, COLOR_TARGET_GLOW, COLOR_TARGET_DARK, COLOR_TARGET_INNER,
    COLOR_PLATFORM, COLOR_PLATFORM_HIGHLIGHT, COLOR_PLATFORM_SHADOW, COLOR_PLATFORM_TOP,
    COLOR_SPIKE, COLOR_SPIKE_DARK, COLOR_SPIKE_TIP, COLOR_SPIKE_BASE,
    COLOR_SPIKE_GLOW, COLOR_SPIKE_METAL, COLOR_SPIKE_HIGHLIGHT,
    MAGNET_RADIUS, MAGNET_COLOR, MAGNET_COLOR_ACTIVE, MAGNET_PULSE_SPEED,
    SLIDER_COLOR, SLIDER_COLOR_ACTIVE, SLIDER_HANDLE_RADIUS, SLIDER_TRACK_WIDTH, SLIDER_SNAP_DIST,
    WINCH_COLOR, WINCH_COLOR_ACTIVE, WINCH_EXTEND_SPEED, WINCH_MIN_LENGTH, WINCH_MAX_LENGTH,
    TELEPORT_RADIUS, TELEPORT_COOLDOWN, TELEPORT_OFFSET,
    TELEPORT_COLOR_A, TELEPORT_COLOR_B, TELEPORT_PULSE_SPEED,
    SPIDER_SPEED, SPIDER_RADIUS, SPIDER_CATCH_DIST,
    SPIDER_COLOR, SPIDER_COLOR_BODY, SPIDER_COLOR_EYE, SPIDER_LEG_COLOR,
    SPIDER_GLOW_COLOR,
    SQUASH_RECOVERY_SPEED, SQUASH_MIN, SQUASH_INTENSITY,
    BALL_SHADOW_OFFSET, BALL_SHINE_OFFSET, BALL_ROTATION_VISUAL_SPEED,
    PLATFORM_FRICTION, PLATFORM_ELASTICITY,
    SPIKE_FRICTION, SPIKE_ELASTICITY,
    FONT_FAMILY, FONT_SIZE_SMALL,
    COLOR_TEXT, COLOR_TEXT_SHADOW,
)
from .utils import pymunk_to_pygame, lerp, lerp_color, clamp, distance, catmull_rom_spline


# =====================================================================
#  Candy
# =====================================================================

class Candy:
    """Physics-driven candy body the player must deliver to the target."""

    COLLISION_TYPE = 1

    def __init__(self, x: float, y: float):
        moment = pymunk.moment_for_circle(CANDY_MASS, 0, CANDY_RADIUS)
        self.body = pymunk.Body(CANDY_MASS, moment)
        self.body.position = (x, y)
        self.shape = pymunk.Circle(self.body, CANDY_RADIUS)
        self.shape.friction = CANDY_FRICTION
        self.shape.elasticity = CANDY_ELASTICITY
        self.shape.collision_type = self.COLLISION_TYPE

        # Visual state
        self.squash_x = 1.0
        self.squash_y = 1.0
        self.visual_angle = 0.0
        self._prev_vel = (0.0, 0.0)

    def add_to_space(self, space: pymunk.Space):
        space.add(self.body, self.shape)

    def remove_from_space(self, space: pymunk.Space):
        if self.shape in space.shapes:
            space.remove(self.body, self.shape)

    def update(self, dt: float):
        vx, vy = self.body.velocity
        speed = math.sqrt(vx * vx + vy * vy)
        target_sy = max(SQUASH_MIN, 1.0 - speed * SQUASH_INTENSITY)
        target_sx = 1.0 / target_sy
        self.squash_x = lerp(self.squash_x, target_sx, SQUASH_RECOVERY_SPEED * dt)
        self.squash_y = lerp(self.squash_y, target_sy, SQUASH_RECOVERY_SPEED * dt)
        self.visual_angle += vx * BALL_ROTATION_VISUAL_SPEED * dt * 0.01
        self._prev_vel = (vx, vy)

    def get_pygame_pos(self):
        return pymunk_to_pygame(self.body.position)

    def draw(self, surface: pygame.Surface, time: float):
        px, py = self.get_pygame_pos()
        r = CANDY_RADIUS

        # shadow
        shadow_surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(shadow_surf, (0, 0, 0, 40),
                           (r * 2, r * 2 + BALL_SHADOW_OFFSET), int(r * 1.1))
        surface.blit(shadow_surf, (px - r * 2, py - r * 2))

        rx = max(4, int(r * self.squash_x))
        ry = max(4, int(r * self.squash_y))

        pygame.draw.ellipse(surface, COLOR_CANDY_DEEP,
                            (px - rx, py - ry, rx * 2, ry * 2))
        pygame.draw.ellipse(surface, COLOR_CANDY,
                            (px - rx + 1, py - ry + 1, rx * 2 - 2, ry * 2 - 2))
        stripe_w = max(2, rx // 3)
        pygame.draw.ellipse(surface, COLOR_CANDY_STRIPE,
                            (px - stripe_w, py - ry + 2, stripe_w * 2, ry * 2 - 4))
        hx = int(px + r * BALL_SHINE_OFFSET[0])
        hy = int(py + r * BALL_SHINE_OFFSET[1])
        pygame.draw.circle(surface, COLOR_CANDY_SHINE, (hx, hy), max(2, r // 3))

        pulse = 0.5 + 0.5 * math.sin(time * 3)
        glow_r = int(r + 2 + pulse * 2)
        glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*COLOR_CANDY_HIGHLIGHT, int(30 * pulse)),
                           (glow_r + 2, glow_r + 2), glow_r, 1)
        surface.blit(glow_surf, (px - glow_r - 2, py - glow_r - 2))


# =====================================================================
#  Target (Om Nom's mouth) - with swallow animation
# =====================================================================

class Target:
    """The collection zone for the candy. Plays a swallow animation on win."""

    COLLISION_TYPE = 2

    # Animation states
    STATE_IDLE = 0
    STATE_SWALLOWING = 1
    STATE_DONE = 2

    def __init__(self, x: float, y: float, radius: int = 30):
        self.x = x
        self.y = y
        self.radius = radius
        self.collected = False
        self._anim_time = 0.0
        self._anim_state = self.STATE_IDLE
        self._swallow_timer = 0.0
        self._swallow_duration = 0.6  # total swallow animation time
        self._candy_draw_pos = None  # where to draw candy during swallow
        self._candy_draw_scale = 1.0

        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = (x, y)
        self.shape = pymunk.Circle(self.body, radius)
        self.shape.sensor = True
        self.shape.collision_type = self.COLLISION_TYPE

    def add_to_space(self, space: pymunk.Space):
        space.add(self.body, self.shape)

    def start_swallow(self):
        """Call when candy hits target to begin the swallow animation."""
        self._anim_state = self.STATE_SWALLOWING
        self._swallow_timer = 0.0
        self.collected = True

    def update(self, dt: float):
        self._anim_time += dt
        if self._anim_state == self.STATE_SWALLOWING:
            self._swallow_timer += dt
            t = min(1.0, self._swallow_timer / self._swallow_duration)
            # Candy shrinks into target center
            self._candy_draw_scale = max(0.0, 1.0 - t * 1.2)
            if self._swallow_timer >= self._swallow_duration:
                self._anim_state = self.STATE_DONE
                self._candy_draw_scale = 0.0

    @property
    def is_swallowing(self):
        return self._anim_state == self.STATE_SWALLOWING

    @property
    def swallow_progress(self):
        """0.0 → 1.0 progress of swallow animation."""
        if self._anim_state != self.STATE_SWALLOWING:
            return 0.0 if self._anim_state == self.STATE_IDLE else 1.0
        return min(1.0, self._swallow_timer / self._swallow_duration)

    def get_pygame_pos(self):
        return pymunk_to_pygame(self.body.position)

    def draw(self, surface: pygame.Surface, time: float):
        px, py = self.get_pygame_pos()
        r = self.radius
        pulse = 0.5 + 0.5 * math.sin(time * 2.5)

        # Glow ring
        glow_r = int(r + 4 + pulse * 4)
        glow_surf = pygame.Surface((glow_r * 2 + 8, glow_r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*COLOR_TARGET_GLOW, int(40 + 20 * pulse)),
                           (glow_r + 4, glow_r + 4), glow_r, 2)
        surface.blit(glow_surf, (px - glow_r - 4, py - glow_r - 4))

        if self._anim_state == self.STATE_SWALLOWING:
            # Animated swallow: mouth opens wide, then closes
            t = self.swallow_progress
            if t < 0.3:
                # Mouth opens wide
                mouth_open = 0.15 + 0.35 * (t / 0.3)
            elif t < 0.7:
                # Mouth stays open (candy going in)
                mouth_open = 0.5
            else:
                # Mouth closes
                close_t = (t - 0.7) / 0.3
                mouth_open = 0.5 * (1.0 - close_t)

            # Draw body (circle with mouth gap)
            pygame.draw.circle(surface, COLOR_TARGET_DARK, (px, py), r, 3)
            pygame.draw.circle(surface, COLOR_TARGET_INNER, (px, py), r - 3)
            pygame.draw.circle(surface, COLOR_TARGET, (px, py), r, 2)

            # Mouth as arc on top
            start_angle = math.pi * (0.5 - mouth_open)
            end_angle = math.pi * (0.5 + mouth_open)
            rect = pygame.Rect(px - r + 4, py - r + 4, (r - 4) * 2, (r - 4) * 2)
            pygame.draw.arc(surface, COLOR_TARGET_GLOW, rect, start_angle, end_angle, 3)

            # Draw candy shrinking into the mouth
            if self._candy_draw_scale > 0.01:
                candy_r = max(1, int(CANDY_RADIUS * self._candy_draw_scale))
                # Candy slides toward center
                slide_t = min(1.0, t * 1.5)
                if self._candy_draw_pos:
                    cx = int(lerp(self._candy_draw_pos[0], px, slide_t))
                    cy = int(lerp(self._candy_draw_pos[1], py, slide_t))
                else:
                    cx, cy = px, py - r // 2
                pygame.draw.circle(surface, COLOR_CANDY, (cx, cy), candy_r)
                pygame.draw.circle(surface, COLOR_CANDY_HIGHLIGHT,
                                   (cx - candy_r // 3, cy - candy_r // 3),
                                   max(1, candy_r // 3))

            # Happy eyes after halfway
            if t > 0.4:
                eye_y = py - r // 3
                # Left eye - happy arc
                pygame.draw.arc(surface, (255, 255, 255),
                                (px - r // 2 - 4, eye_y - 4, 8, 8),
                                0.2, math.pi - 0.2, 2)
                # Right eye - happy arc
                pygame.draw.arc(surface, (255, 255, 255),
                                (px + r // 2 - 4, eye_y - 4, 8, 8),
                                0.2, math.pi - 0.2, 2)

        elif self._anim_state == self.STATE_DONE:
            # Satisfied face - full circle, happy eyes, smile
            pygame.draw.circle(surface, COLOR_TARGET_DARK, (px, py), r, 3)
            pygame.draw.circle(surface, COLOR_TARGET_INNER, (px, py), r - 3)
            pygame.draw.circle(surface, COLOR_TARGET, (px, py), r, 2)

            # Happy eyes
            eye_y = py - r // 3
            pygame.draw.arc(surface, (255, 255, 255),
                            (px - r // 2 - 5, eye_y - 5, 10, 10),
                            0.2, math.pi - 0.2, 2)
            pygame.draw.arc(surface, (255, 255, 255),
                            (px + r // 2 - 5, eye_y - 5, 10, 10),
                            0.2, math.pi - 0.2, 2)

            # Satisfied smile
            smile_rect = pygame.Rect(px - r // 2, py, r, r // 2)
            pygame.draw.arc(surface, (255, 255, 255), smile_rect,
                            math.pi + 0.3, 2 * math.pi - 0.3, 2)

        else:
            # Idle: gentle mouth bobbing
            pygame.draw.circle(surface, COLOR_TARGET_DARK, (px, py), r, 3)
            pygame.draw.circle(surface, COLOR_TARGET_INNER, (px, py), r - 3)
            pygame.draw.circle(surface, COLOR_TARGET, (px, py), r, 2)

            mouth_open = 0.3 + 0.15 * math.sin(time * 4)
            start_angle = math.pi * (0.5 - mouth_open)
            end_angle = math.pi * (0.5 + mouth_open)
            rect = pygame.Rect(px - r + 4, py - r + 4, (r - 4) * 2, (r - 4) * 2)
            pygame.draw.arc(surface, COLOR_TARGET_GLOW, rect, start_angle, end_angle, 2)


# =====================================================================
#  Anchor (Static Hook)
# =====================================================================

class Anchor:
    """A simple static anchor point where a rope attaches."""

    def __init__(self, x: float, y: float, letter: str = ""):
        self.x = x
        self.y = y
        self.letter = letter.upper()
        self.active = True

        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = (x, y)

    def get_pygame_pos(self):
        return pymunk_to_pygame(self.body.position)

    def draw(self, surface: pygame.Surface, time: float):
        if not self.active:
            return
        px, py = self.get_pygame_pos()

        pulse = 0.5 + 0.5 * math.sin(time * 2)
        gr = 12 + int(pulse * 2)
        gs = pygame.Surface((gr * 2 + 4, gr * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*COLOR_ANCHOR_GLOW, int(40 + 20 * pulse)),
                           (gr + 2, gr + 2), gr, 1)
        surface.blit(gs, (px - gr - 2, py - gr - 2))

        pygame.draw.circle(surface, COLOR_ANCHOR_RING, (px, py), 10, 2)
        pygame.draw.circle(surface, COLOR_ANCHOR_CORE, (px, py), 7)
        pygame.draw.circle(surface, COLOR_ANCHOR_GLOW, (px, py), 4)
        pygame.draw.circle(surface, COLOR_ANCHOR, (px, py), 2)

        if self.letter:
            try:
                font = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_SMALL, bold=True)
            except Exception:
                font = pygame.font.Font(None, FONT_SIZE_SMALL)
            txt = font.render(self.letter, True, COLOR_TEXT)
            shadow = font.render(self.letter, True, COLOR_TEXT_SHADOW)
            tw, th = txt.get_size()
            surface.blit(shadow, (px - tw // 2 + 1, py - 22 + 1))
            surface.blit(txt, (px - tw // 2, py - 22))


# =====================================================================
#  Magnet Anchor (Automatic / Auto-Attach)
# =====================================================================

class MagnetAnchor:
    """Anchor that auto-creates a rope when candy enters its radius."""

    def __init__(self, x: float, y: float, radius: float = MAGNET_RADIUS,
                 letter: str = ""):
        self.x = x
        self.y = y
        self.radius = radius
        self.letter = letter.upper()
        self.state = "inactive"
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = (x, y)
        self.rope_data = None

    def get_pygame_pos(self):
        return pymunk_to_pygame(self.body.position)

    def check_candy(self, candy_pos) -> bool:
        if self.state != "inactive":
            return False
        d = distance((self.x, self.y), candy_pos)
        return d < self.radius

    def activate(self):
        self.state = "active"

    def deactivate(self):
        self.state = "inactive"
        self.rope_data = None

    def draw(self, surface: pygame.Surface, time: float):
        px, py = self.get_pygame_pos()
        r = int(self.radius)
        pulse = 0.5 + 0.5 * math.sin(time * MAGNET_PULSE_SPEED)
        is_active = self.state == "active"
        color = MAGNET_COLOR_ACTIVE if is_active else MAGNET_COLOR

        num_dashes = 24
        for i in range(num_dashes):
            if i % 2 == 0:
                angle1 = (i / num_dashes) * math.pi * 2 + time * 0.5
                angle2 = ((i + 1) / num_dashes) * math.pi * 2 + time * 0.5
                p1 = (px + int(r * math.cos(angle1)), py + int(r * math.sin(angle1)))
                p2 = (px + int(r * math.cos(angle2)), py + int(r * math.sin(angle2)))
                alpha = int(60 + 40 * pulse) if not is_active else int(120 + 60 * pulse)
                ds = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.line(ds, (*color, alpha), p1, p2, 2)
                surface.blit(ds, (0, 0))

        cr = 8 if not is_active else 10
        pygame.draw.circle(surface, color, (px, py), cr, 2)
        pygame.draw.circle(surface, color, (px, py), 4)

        if self.letter:
            try:
                font = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_SMALL, bold=True)
            except Exception:
                font = pygame.font.Font(None, FONT_SIZE_SMALL)
            txt = font.render(self.letter, True, color)
            tw, th = txt.get_size()
            surface.blit(txt, (px - tw // 2, py - 24))


# =====================================================================
#  Slider Anchor (Mouse-Draggable Hook on a Track)
# =====================================================================

class SliderAnchor:
    """A hook that slides along a fixed linear track via mouse drag."""

    def __init__(self, x: float, y: float,
                 track_start: tuple, track_end: tuple,
                 letter: str = "", start_t: float = 0.5):
        self.track_start = track_start
        self.track_end = track_end
        self.letter = letter.upper()
        self.t = clamp(start_t, 0.0, 1.0)
        self.dragging = False

        self.body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self._update_position()
        self.rope_data = None

    def _update_position(self):
        sx, sy = self.track_start
        ex, ey = self.track_end
        self.body.position = (lerp(sx, ex, self.t), lerp(sy, ey, self.t))
        self.x = self.body.position.x
        self.y = self.body.position.y

    def _project_on_track(self, point):
        sx, sy = self.track_start
        ex, ey = self.track_end
        dx, dy = ex - sx, ey - sy
        length_sq = dx * dx + dy * dy
        if length_sq < 1e-6:
            return 0.5
        t = ((point[0] - sx) * dx + (point[1] - sy) * dy) / length_sq
        return clamp(t, 0.0, 1.0)

    def start_drag(self, mouse_pymunk_pos):
        d = distance(self.body.position, mouse_pymunk_pos)
        if d < SLIDER_SNAP_DIST:
            self.dragging = True
            return True
        return False

    def update_drag(self, mouse_pymunk_pos):
        if not self.dragging:
            return
        self.t = self._project_on_track(mouse_pymunk_pos)
        self._update_position()

    def end_drag(self):
        self.dragging = False
        self.body.velocity = (0, 0)

    def get_pygame_pos(self):
        return pymunk_to_pygame(self.body.position)

    def draw(self, surface: pygame.Surface, time: float):
        ts = pymunk_to_pygame(self.track_start)
        te = pymunk_to_pygame(self.track_end)
        pygame.draw.line(surface, (80, 80, 100), ts, te, SLIDER_TRACK_WIDTH)
        pygame.draw.circle(surface, (100, 100, 120), ts, 4)
        pygame.draw.circle(surface, (100, 100, 120), te, 4)

        px, py = self.get_pygame_pos()
        color = SLIDER_COLOR_ACTIVE if self.dragging else SLIDER_COLOR
        pygame.draw.circle(surface, color, (px, py), SLIDER_HANDLE_RADIUS)
        pygame.draw.circle(surface, (255, 255, 255), (px, py), SLIDER_HANDLE_RADIUS, 2)
        pygame.draw.circle(surface, (255, 255, 255), (px, py), 3)

        if self.letter:
            try:
                font = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_SMALL, bold=True)
            except Exception:
                font = pygame.font.Font(None, FONT_SIZE_SMALL)
            txt = font.render(self.letter, True, color)
            tw, th = txt.get_size()
            surface.blit(txt, (px - tw // 2, py - SLIDER_HANDLE_RADIUS - 18))


# =====================================================================
#  Winch Anchor (Keyboard Extend / Retract)
# =====================================================================

class WinchAnchor:
    """Anchor with keyboard-controlled rope length.
    Shift+Letter = retract,  Ctrl+Letter = extend,  Letter = cut.
    """

    def __init__(self, x: float, y: float, letter: str = "",
                 initial_length: float = 200):
        self.x = x
        self.y = y
        self.letter = letter.upper()
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = (x, y)
        self.current_length = clamp(initial_length, WINCH_MIN_LENGTH, WINCH_MAX_LENGTH)
        self.target_length = self.current_length
        self.active = True
        self.rope_data = None

    def extend(self, dt):
        self.target_length = min(self.target_length + WINCH_EXTEND_SPEED * dt,
                                 WINCH_MAX_LENGTH)

    def retract(self, dt):
        self.target_length = max(self.target_length - WINCH_EXTEND_SPEED * dt,
                                 WINCH_MIN_LENGTH)

    def update(self, dt):
        diff = self.target_length - self.current_length
        self.current_length += diff * 6.0 * dt
        self.current_length = clamp(self.current_length, WINCH_MIN_LENGTH, WINCH_MAX_LENGTH)

    def get_length_fraction(self):
        return (self.current_length - WINCH_MIN_LENGTH) / (WINCH_MAX_LENGTH - WINCH_MIN_LENGTH)

    def get_pygame_pos(self):
        return pymunk_to_pygame(self.body.position)

    def draw(self, surface: pygame.Surface, time: float):
        if not self.active:
            return
        px, py = self.get_pygame_pos()

        pulse = 0.5 + 0.5 * math.sin(time * 2)
        color = WINCH_COLOR_ACTIVE if abs(self.target_length - self.current_length) > 2 else WINCH_COLOR

        gear_r = 14
        pygame.draw.circle(surface, color, (px, py), gear_r, 2)
        teeth = 8
        for i in range(teeth):
            angle = (i / teeth) * math.pi * 2 + time * 1.5
            ix = px + int((gear_r - 2) * math.cos(angle))
            iy = py + int((gear_r - 2) * math.sin(angle))
            ox = px + int((gear_r + 3) * math.cos(angle))
            oy = py + int((gear_r + 3) * math.sin(angle))
            pygame.draw.line(surface, color, (ix, iy), (ox, oy), 2)
        pygame.draw.circle(surface, color, (px, py), 5)
        pygame.draw.circle(surface, (40, 40, 40), (px, py), 3)

        bar_w = 30
        bar_h = 4
        frac = self.get_length_fraction()
        bar_x = px - bar_w // 2
        bar_y = py + gear_r + 6
        pygame.draw.rect(surface, (60, 60, 80), (bar_x, bar_y, bar_w, bar_h), border_radius=2)
        fill_w = max(1, int(bar_w * frac))
        pygame.draw.rect(surface, color, (bar_x, bar_y, fill_w, bar_h), border_radius=2)

        if self.letter:
            try:
                font = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_SMALL, bold=True)
            except Exception:
                font = pygame.font.Font(None, FONT_SIZE_SMALL)
            txt = font.render(self.letter, True, color)
            tw, th = txt.get_size()
            surface.blit(txt, (px - tw // 2, py - gear_r - 20))


# =====================================================================
#  Platform
# =====================================================================

class Platform:
    """Static collision surface."""

    COLLISION_TYPE = 3

    def __init__(self, x1: float, y1: float, x2: float, y2: float,
                 thickness: int = 8):
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.shape = pymunk.Segment(self.body, (x1, y1), (x2, y2), thickness)
        self.shape.friction = PLATFORM_FRICTION
        self.shape.elasticity = PLATFORM_ELASTICITY
        self.shape.collision_type = self.COLLISION_TYPE
        self.p1 = (x1, y1)
        self.p2 = (x2, y2)
        self.thickness = thickness

    def add_to_space(self, space: pymunk.Space):
        space.add(self.body, self.shape)

    def draw(self, surface: pygame.Surface, time: float):
        pp1 = pymunk_to_pygame(self.p1)
        pp2 = pymunk_to_pygame(self.p2)
        t = self.thickness
        pygame.draw.line(surface, COLOR_PLATFORM_SHADOW,
                         (pp1[0], pp1[1] + 2), (pp2[0], pp2[1] + 2), t + 2)
        pygame.draw.line(surface, COLOR_PLATFORM, pp1, pp2, t)
        pygame.draw.line(surface, COLOR_PLATFORM_TOP, pp1, pp2, max(1, t // 3))


# =====================================================================
#  Spike
# =====================================================================

class Spike:
    """Instant-kill obstacle. Triangular spikes on a base."""

    COLLISION_TYPE = 4

    def __init__(self, x: float, y: float, width: float = 60,
                 height: float = 20, direction: str = "up"):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.direction = direction

        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = (x, y)

        self.shapes = []
        num_spikes = max(1, int(width // 16))
        spike_w = width / num_spikes
        for i in range(num_spikes):
            cx = -width / 2 + spike_w * (i + 0.5)
            if direction == "up":
                verts = [(cx - spike_w / 2, 0), (cx + spike_w / 2, 0), (cx, height)]
            elif direction == "down":
                verts = [(cx - spike_w / 2, 0), (cx + spike_w / 2, 0), (cx, -height)]
            elif direction == "left":
                verts = [(0, cx - spike_w / 2), (0, cx + spike_w / 2), (-height, cx)]
            else:
                verts = [(0, cx - spike_w / 2), (0, cx + spike_w / 2), (height, cx)]
            s = pymunk.Poly(self.body, verts)
            s.sensor = True
            s.collision_type = self.COLLISION_TYPE
            s.friction = SPIKE_FRICTION
            s.elasticity = SPIKE_ELASTICITY
            self.shapes.append(s)

    def add_to_space(self, space: pymunk.Space):
        space.add(self.body, *self.shapes)

    def get_pygame_pos(self):
        return pymunk_to_pygame(self.body.position)

    def draw(self, surface: pygame.Surface, time: float):
        px, py = self.get_pygame_pos()
        w = self.width
        h = self.height
        num_spikes = max(1, int(w // 16))
        spike_w = w / num_spikes
        pulse = 0.5 + 0.5 * math.sin(time * 3)

        for i in range(num_spikes):
            cx = px - w / 2 + spike_w * (i + 0.5)
            if self.direction == "up":
                base_l = (int(cx - spike_w / 2), py)
                base_r = (int(cx + spike_w / 2), py)
                tip = (int(cx), py - h)
            elif self.direction == "down":
                base_l = (int(cx - spike_w / 2), py)
                base_r = (int(cx + spike_w / 2), py)
                tip = (int(cx), py + h)
            elif self.direction == "left":
                base_l = (px, int(cx - spike_w / 2))
                base_r = (px, int(cx + spike_w / 2))
                tip = (px - h, int(cx))
            else:
                base_l = (px, int(cx - spike_w / 2))
                base_r = (px, int(cx + spike_w / 2))
                tip = (px + h, int(cx))

            pygame.draw.polygon(surface, COLOR_SPIKE_DARK, [base_l, base_r, tip])
            inner_pts = [
                (int(lerp(base_l[0], tip[0], 0.15)), int(lerp(base_l[1], tip[1], 0.15))),
                (int(lerp(base_r[0], tip[0], 0.15)), int(lerp(base_r[1], tip[1], 0.15))),
                tip
            ]
            pygame.draw.polygon(surface, COLOR_SPIKE, inner_pts)
            tc = lerp_color(COLOR_SPIKE_TIP, COLOR_SPIKE_GLOW, pulse)
            pygame.draw.circle(surface, tc, tip, 3)

        if self.direction in ("up", "down"):
            pygame.draw.line(surface, COLOR_SPIKE_BASE,
                             (int(px - w / 2), py), (int(px + w / 2), py), 3)


# =====================================================================
#  Teleport Pair (Magic Hats)
# =====================================================================

class TeleportPair:
    """Two magic hats. Candy entering hat A exits hat B (and vice-versa).
    Velocity preserved; direction rotated by delta_theta = theta_B - theta_A + pi.
    """

    COLLISION_TYPE_A = 5
    COLLISION_TYPE_B = 6

    def __init__(self, ax, ay, bx, by,
                 angle_a: float = 0, angle_b: float = 0):
        self.cooldown_timer = 0.0
        self.angle_a = angle_a
        self.angle_b = angle_b

        self.body_a = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body_a.position = (ax, ay)
        self.shape_a = pymunk.Circle(self.body_a, TELEPORT_RADIUS)
        self.shape_a.sensor = True
        self.shape_a.collision_type = self.COLLISION_TYPE_A

        self.body_b = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body_b.position = (bx, by)
        self.shape_b = pymunk.Circle(self.body_b, TELEPORT_RADIUS)
        self.shape_b.sensor = True
        self.shape_b.collision_type = self.COLLISION_TYPE_B

    def add_to_space(self, space: pymunk.Space):
        space.add(self.body_a, self.shape_a)
        space.add(self.body_b, self.shape_b)

    def update(self, dt):
        if self.cooldown_timer > 0:
            self.cooldown_timer -= dt

    def can_teleport(self):
        return self.cooldown_timer <= 0

    def teleport(self, candy_body, entry_is_a: bool):
        if not self.can_teleport():
            return False

        if entry_is_a:
            exit_body = self.body_b
            delta_theta = self.angle_b - self.angle_a + math.pi
        else:
            exit_body = self.body_a
            delta_theta = self.angle_a - self.angle_b + math.pi

        vx, vy = candy_body.velocity
        cos_d = math.cos(delta_theta)
        sin_d = math.sin(delta_theta)
        new_vx = vx * cos_d - vy * sin_d
        new_vy = vx * sin_d + vy * cos_d

        ex, ey = exit_body.position
        speed = math.sqrt(new_vx ** 2 + new_vy ** 2)
        if speed > 1e-3:
            off_x = (new_vx / speed) * TELEPORT_OFFSET
            off_y = (new_vy / speed) * TELEPORT_OFFSET
        else:
            off_x, off_y = 0, TELEPORT_OFFSET

        candy_body.position = (ex + off_x, ey + off_y)
        candy_body.velocity = (new_vx, new_vy)
        self.cooldown_timer = TELEPORT_COOLDOWN
        return True

    def draw(self, surface: pygame.Surface, time: float):
        for body, color, angle in [
            (self.body_a, TELEPORT_COLOR_A, self.angle_a),
            (self.body_b, TELEPORT_COLOR_B, self.angle_b),
        ]:
            px, py = pymunk_to_pygame(body.position)
            r = TELEPORT_RADIUS
            pulse = 0.5 + 0.5 * math.sin(time * TELEPORT_PULSE_SPEED)

            ring_r = int(r + 3 + pulse * 4)
            rs = pygame.Surface((ring_r * 2 + 8, ring_r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(rs, (*color, int(50 + 30 * pulse)),
                               (ring_r + 4, ring_r + 4), ring_r, 2)
            surface.blit(rs, (px - ring_r - 4, py - ring_r - 4))

            # Build hat shape relative to center, then rotate by angle
            hw = r
            hh = int(r * 0.8)
            # Base (unrotated) hat points relative to (0,0) center.
            # Opening (wide brim) faces DOWN in screen coords (+y).
            local_pts = [
                (-hw, hh // 2),
                (hw, hh // 2),
                (int(hw * 0.6), -hh // 2),
                (-int(hw * 0.6), -hh // 2),
            ]
            # Rotate so opening faces the hat's angle direction.
            # angle is standard math convention (CCW from +x).
            # The base hat shape has its opening (wide brim) facing DOWN (+y) in screen coords.
            #   pts = [(-w, h/2), (w, h/2), ...]
            #
            # We want angle=0 (Right, +x) to have opening facing Right.
            # Currently opening is Down (+y).
            # To rotate Down (0, 1) to Right (1, 0), we need -90 deg (-pi/2).
            #   (0, 1) rotated -90 -> (1, 0).
            # So rot = angle - pi/2.
            #
            # But wait, y-axis is flipped between math and screen?
            # Standard rotation matrix:
            #   x' = x cos(r) - y sin(r)
            #   y' = x sin(r) + y cos(r)
            #
            # If we want visual Angle 0 to be Right.
            # Base shape opening is Down (+y).
            #   Start vector (0, 1).
            #   Target vector (1, 0).
            #   Apply matrix with r:
            #     1 = 0 - 1*sin(r)  => sin(r) = -1
            #     0 = 0 + 1*cos(r)  => cos(r) = 0
            #   r = -pi/2.
            #
            # If we want Angle 90 (Up, -y) to be Up.
            #   Target vector (0, -1).
            #   Apply matrix with r:
            #     0 = 0 - 1*sin(r)
            #     -1 = 0 + 1*cos(r) => cos(r) = -1
            #   r = pi.
            #
            # So if angle=0 gives r=-pi/2, and angle=pi/2 gives r=0 (wait).
            # My previous logic: rot = -(angle + pi/2) was wrong?
            #
            # Let's use the arrow direction logic from Editor.
            # Editor draws an arrow pointing in `angle` direction.
            # Hat should receive the candy from that direction (opening faces geometric vector `angle`).
            #
            # If `angle` points INTO the hat (entry vector):
            #   Then the hat mouth should face OPPOSITE to `angle`.
            #   If entry angle is 0 (Right), candy moves Right to enter.
            #   Hat mouth should face Left.
            #
            # Teleport logic:
            #   Enters hat A. Exits hat B.
            #   Velocity is rotated by (angle_b - angle_a + pi).
            #
            # If I enter hat A moving Right (0), and angle_a is 0.
            # Then I exit hat B (angle_b=0) moving Left (pi).
            # So angle defines the "outward facing normal" of the hat mouth?
            # Or the direction of "flow"?
            #
            # Convention: The angle represents the direction the hat points *towards*.
            # Like a cannon.
            # So if angle=0 (Right), the hat mouth faces Right.
            #
            # If base mouth faces Down (+y).
            # We need to rotate Down to Right.
            # Rot = -pi/2.
            # So rot = angle - pi/2.
            #
            # Let's try `rot = -angle - math.pi / 2` because Pymunk angle is CCW,
            # but screen y is down (so standard rotation is CW visually for +angle... wait).
            # Screen coords: +y is Down.
            # clockwise rotation moves +x -> +y.
            # Pymunk angle: +angle is CCW (x -> y is Up).
            # So Pymunk Angle theta corresponds to Screen Angle -theta.
            #
            # Let's assume `angle` is Screen Space Angle (CCW visually? No Pymunk is math space).
            # If Pymunk Angle is 0 (Right). Screen Angle is 0 (Right).
            # If Pymunk Angle is pi/2 (Up). Screen Angle is -pi/2 (Up).
            #
            # So effective screen rotation `r_screen = -angle`.
            #
            # We want to map:
            #   angle=0 (Right)  -> Hat Mouth Right.
            #   angle=pi/2 (Up)  -> Hat Mouth Up.
            #
            # Base Hat Mouth is Down (+y).
            #
            # Map Base (Down) to Target (Right, when angle=0).
            #   Down (0, 1) -> Right (1, 0).
            #   CCW Rotation of -90 (-pi/2). [Visual on screen: Down to Right is CCW... wait. Clockwise is Down to Left (0,1)->(-1,0)? No.]
            #   Standard grid: (0,1) is up. (1,0) is right. -90 deg is right.
            #   Screen grid: (0,1) is down. (1,0) is right.
            #     To go Down -> Right is -90 deg (Counter-Clockwise).
            #     x' = x cos - y sin ...
            #     1 = 0 - 1(-1) = 1.
            #
            # So we need a rotation of -pi/2 to get from Base to Right.
            # So `rot_base = -pi/2`.
            #
            # Now add the object rotation `angle`.
            # Since Pymunk `angle` is CCW (Up), and Screen `angle` is CW (Down).
            # We use `-angle`.
            #
            # Result: `rot = -angle - pi/2`.
            #
            # Let's trace:
            #   angle = 0. rot = -pi/2. Base(Down) -> Right. CORRECT.
            #   angle = pi/2 (Up). rot = -pi/2 - pi/2 = -pi. Base(Down) -> Up. CORRECT.
            #   angle = -pi/2 (Down). rot = pi/2 - pi/2 = 0. Base(Down) -> Down. CORRECT.
            #
            
            rot = -angle - math.pi / 2
            cos_r = math.cos(rot)
            sin_r = math.sin(rot)
            pts = [(px + int(lx * cos_r - ly * sin_r),
                    py + int(lx * sin_r + ly * cos_r))
                   for lx, ly in local_pts]
            pygame.draw.polygon(surface, color, pts)
            # Rotated brim line
            brim_l = (-hw - 4, hh // 2)
            brim_r = (hw + 4, hh // 2)
            bl = (px + int(brim_l[0] * cos_r - brim_l[1] * sin_r),
                  py + int(brim_l[0] * sin_r + brim_l[1] * cos_r))
            br = (px + int(brim_r[0] * cos_r - brim_r[1] * sin_r),
                  py + int(brim_r[0] * sin_r + brim_r[1] * cos_r))
            pygame.draw.line(surface, color, bl, br, 3)
            pygame.draw.circle(surface, color, (px, py), int(r * 0.3))

            if self.cooldown_timer <= 0:
                # Sparkle at top of hat (rotated)
                tip = (0, -hh // 2 - 6)
                sp = (px + int(tip[0] * cos_r - tip[1] * sin_r),
                      py + int(tip[0] * sin_r + tip[1] * cos_r))
                pygame.draw.circle(surface, (255, 255, 255), sp, 3)


# =====================================================================
#  Spider (Rope-Crawling Antagonist)
# =====================================================================

class Spider:
    """Crawls along a rope toward the candy.
    If it reaches the candy, player loses.
    """

    def __init__(self, rope_index: int, start_t: float = 0.0,
                 speed: float = SPIDER_SPEED):
        self.rope_index = rope_index
        self.segment_index = 0
        self.t = start_t
        self.speed = speed
        self.alive = True
        self.x = 0.0
        self.y = 0.0
        self._leg_phase = 0.0

    def update(self, dt, rope_bodies):
        if not self.alive or not rope_bodies:
            return None

        self._leg_phase += dt * 12

        if self.segment_index >= len(rope_bodies) - 1:
            if rope_bodies:
                pos = rope_bodies[-1].position
                self.x, self.y = pos.x, pos.y
            return "caught"

        cur = rope_bodies[self.segment_index].position
        nxt = rope_bodies[self.segment_index + 1].position
        seg_len = distance(cur, nxt)
        if seg_len < 1e-3:
            seg_len = 1.0

        self.t += (self.speed * dt) / seg_len

        while self.t >= 1.0 and self.segment_index < len(rope_bodies) - 2:
            self.t -= 1.0
            self.segment_index += 1
            cur = rope_bodies[self.segment_index].position
            nxt = rope_bodies[self.segment_index + 1].position
            seg_len = distance(cur, nxt)
            if seg_len < 1e-3:
                seg_len = 1.0

        if self.segment_index >= len(rope_bodies) - 1:
            pos = rope_bodies[-1].position
            self.x, self.y = pos.x, pos.y
            return "caught"

        cur = rope_bodies[self.segment_index].position
        nxt = rope_bodies[self.segment_index + 1].position
        self.x = lerp(cur.x, nxt.x, clamp(self.t, 0, 1))
        self.y = lerp(cur.y, nxt.y, clamp(self.t, 0, 1))
        return None

    def check_catch(self, candy_pos):
        if not self.alive:
            return False
        d = distance((self.x, self.y), candy_pos)
        return d < SPIDER_CATCH_DIST

    def get_pygame_pos(self):
        return pymunk_to_pygame((self.x, self.y))

    def draw(self, surface: pygame.Surface, time: float):
        if not self.alive:
            return
        px, py = self.get_pygame_pos()
        r = SPIDER_RADIUS

        # Red danger glow (pulsing)
        glow_pulse = 0.6 + 0.4 * math.sin(time * 5)
        glow_r = int(r * 2.2 + glow_pulse * 4)
        glow_surf = pygame.Surface((glow_r * 2 + 8, glow_r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*SPIDER_GLOW_COLOR, int(35 * glow_pulse)),
                           (glow_r + 4, glow_r + 4), glow_r)
        pygame.draw.circle(glow_surf, (*SPIDER_GLOW_COLOR, int(60 * glow_pulse)),
                           (glow_r + 4, glow_r + 4), int(glow_r * 0.7))
        surface.blit(glow_surf, (px - glow_r - 4, py - glow_r - 4))

        # Legs (thicker, longer, more visible)
        for side in [-1, 1]:
            for i in range(4):
                angle_base = (i / 4) * math.pi * 0.8 - 0.3
                wobble = math.sin(self._leg_phase + i * 1.2) * 0.3
                angle = angle_base + wobble
                lx = px + side * int((r + 12) * math.cos(angle))
                ly = py + int((r + 12) * math.sin(angle))
                mx = px + side * int(r * 0.6 * math.cos(angle + 0.2 * side))
                my = py + int(r * 0.6 * math.sin(angle + 0.2 * side))
                pygame.draw.line(surface, SPIDER_LEG_COLOR, (px + side * 4, py), (mx, my), 3)
                pygame.draw.line(surface, SPIDER_LEG_COLOR, (mx, my), (lx, ly), 3)
                # Leg tip highlights
                pygame.draw.circle(surface, (90, 70, 90), (lx, ly), 2)

        # Body (larger, with marking)
        pygame.draw.circle(surface, SPIDER_COLOR, (px, py), r)
        pygame.draw.circle(surface, SPIDER_COLOR_BODY, (px, py), r - 2)
        # Abdomen marking (hourglass shape)
        pygame.draw.circle(surface, (80, 30, 30), (px, py + 3), max(2, r // 3))

        # Eyes (much bigger, bright, visible)
        eye_sep = max(4, r // 3)
        eye_r = max(4, r // 4)
        # White sclera
        pygame.draw.circle(surface, (240, 240, 240), (px - eye_sep, py - r // 4), eye_r)
        pygame.draw.circle(surface, (240, 240, 240), (px + eye_sep, py - r // 4), eye_r)
        # Red pupils
        pygame.draw.circle(surface, SPIDER_COLOR_EYE, (px - eye_sep, py - r // 4), eye_r - 1)
        pygame.draw.circle(surface, SPIDER_COLOR_EYE, (px + eye_sep, py - r // 4), eye_r - 1)
        # Bright center
        pygame.draw.circle(surface, (255, 200, 200), (px - eye_sep - 1, py - r // 4 - 1), max(1, eye_r // 2))
        pygame.draw.circle(surface, (255, 200, 200), (px + eye_sep - 1, py - r // 4 - 1), max(1, eye_r // 2))

        # Outline ring
        pygame.draw.circle(surface, SPIDER_GLOW_COLOR, (px, py), r + 1, 2)


# =====================================================================
#  Rope Visual Helper
# =====================================================================

def draw_rope(surface, bodies, time=0.0):
    """Draw a rope through the bodies list using Catmull-Rom spline."""
    if len(bodies) < 2:
        return

    points = [pymunk_to_pygame(b.position) for b in bodies]

    color = COLOR_ROPE
    width = ROPE_WIDTH

    if len(points) >= 3:
        smooth = catmull_rom_spline(points, 6)
    else:
        smooth = points

    shadow = [(p[0] + 1, p[1] + 2) for p in smooth]
    if len(shadow) >= 2:
        pygame.draw.lines(surface, COLOR_ROPE_SHADOW, False, shadow, width)
    if len(smooth) >= 2:
        pygame.draw.lines(surface, color, False, smooth, width)
