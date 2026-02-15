"""
Renderer, ParticleSystem, and StarField for Cut The Rope.
Handles all drawing utilities, particle effects, and background stars.
"""

import math
import random
import pygame
from .config import (
    WIDTH, HEIGHT, STAR_COUNT,
    PARTICLE_GRAVITY, PARTICLE_FADE_SPEED,
    COLOR_BG_GRADIENT_TOP, COLOR_BG_GRADIENT_BOTTOM,
    COLOR_PARTICLE_STAR, COLOR_SLASH, COLOR_SLASH_GLOW,
    MOUSE_TRAIL_LENGTH, MOUSE_TRAIL_WIDTH, MOUSE_TRAIL_GLOW_WIDTH,
    GLOW_PULSE_SPEED,
)
from .utils import lerp, lerp_color, clamp


# ── Particle ──────────────────────────────────────────────────

class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life",
                 "color", "size", "gravity", "fade_speed")

    def __init__(self, x, y, vx, vy, life, color, size=3,
                 gravity=PARTICLE_GRAVITY, fade_speed=PARTICLE_FADE_SPEED):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity
        self.fade_speed = fade_speed

    def update(self, dt):
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= self.fade_speed * dt
        return self.life > 0

    def draw(self, surface):
        alpha = clamp(self.life / self.max_life, 0, 1)
        r = max(1, int(self.size * alpha))
        c = (
            int(self.color[0] * alpha),
            int(self.color[1] * alpha),
            int(self.color[2] * alpha),
        )
        pygame.draw.circle(surface, c, (int(self.x), int(self.y)), r)


# ── ParticleSystem ────────────────────────────────────────────

class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []

    def emit(self, x, y, color, count=12, speed=180,
             life=0.8, size=3, gravity=PARTICLE_GRAVITY):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(speed * 0.3, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            p = Particle(x, y, vx, vy,
                         random.uniform(life * 0.5, life),
                         color, random.uniform(size * 0.5, size),
                         gravity)
            self.particles.append(p)

    def emit_burst(self, x, y, color, count=20, speed=250,
                   life=1.0, size=4, gravity=PARTICLE_GRAVITY):
        """Bigger burst for special events."""
        self.emit(x, y, color, count, speed, life, size, gravity)

    def emit_line(self, x1, y1, x2, y2, color, count=8, speed=60,
                  life=0.5, size=2):
        """Emit along a line (for rope cuts)."""
        for i in range(count):
            t = i / max(1, count - 1)
            px = lerp(x1, x2, t)
            py = lerp(y1, y2, t)
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(speed * 0.3, speed)
            self.particles.append(
                Particle(px, py,
                         math.cos(angle) * spd,
                         math.sin(angle) * spd,
                         random.uniform(life * 0.5, life),
                         color, random.uniform(size * 0.5, size))
            )

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)


# ── StarField ─────────────────────────────────────────────────

class Star:
    __slots__ = ("x", "y", "size", "speed", "phase", "brightness")

    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.size = random.uniform(0.5, 2.0)
        self.speed = random.uniform(0.5, 2.0)
        self.phase = random.uniform(0, math.pi * 2)
        self.brightness = random.uniform(0.3, 1.0)


class StarField:
    def __init__(self, count=STAR_COUNT):
        self.stars = [Star() for _ in range(count)]
        self._time = 0.0

    def update(self, dt):
        self._time += dt

    def draw(self, surface):
        for s in self.stars:
            twinkle = 0.5 + 0.5 * math.sin(self._time * s.speed + s.phase)
            alpha = s.brightness * twinkle
            c = (
                int(COLOR_PARTICLE_STAR[0] * alpha),
                int(COLOR_PARTICLE_STAR[1] * alpha),
                int(COLOR_PARTICLE_STAR[2] * alpha),
            )
            r = max(1, int(s.size * (0.6 + 0.4 * twinkle)))
            pygame.draw.circle(surface, c, (int(s.x), int(s.y)), r)


# ── Renderer ──────────────────────────────────────────────────

class Renderer:
    """Manages the virtual canvas, scaling, and background."""

    def __init__(self):
        self.virtual_surface = pygame.Surface((WIDTH, HEIGHT))
        self.star_field = StarField()
        self.particle_system = ParticleSystem()
        self._glow_time = 0.0
        # Mouse trail
        self._trail: list[tuple[int, int]] = []

    # ── background ────────────────────────────────────────────

    def draw_background(self, surface: pygame.Surface):
        """Draw the gradient background."""
        for y in range(HEIGHT):
            t = y / HEIGHT
            c = lerp_color(COLOR_BG_GRADIENT_TOP, COLOR_BG_GRADIENT_BOTTOM, t)
            pygame.draw.line(surface, c, (0, y), (WIDTH, y))

    # ── scaling ───────────────────────────────────────────────

    @staticmethod
    def get_scale_rect(window_w, window_h):
        """Return (scale, dest_rect) for letter-boxing."""
        scale = min(window_w / WIDTH, window_h / HEIGHT)
        sw = int(WIDTH * scale)
        sh = int(HEIGHT * scale)
        ox = (window_w - sw) // 2
        oy = (window_h - sh) // 2
        return scale, pygame.Rect(ox, oy, sw, sh)

    def window_to_virtual(self, pos, scale, dest_rect):
        """Convert window pixel → virtual canvas pixel."""
        x = (pos[0] - dest_rect.x) / scale
        y = (pos[1] - dest_rect.y) / scale
        return int(x), int(y)

    # ── mouse trail ───────────────────────────────────────────

    def update_trail(self, vpos):
        if vpos is not None:
            self._trail.append(vpos)
        if len(self._trail) > MOUSE_TRAIL_LENGTH:
            self._trail = self._trail[-MOUSE_TRAIL_LENGTH:]

    def clear_trail(self):
        self._trail.clear()

    def draw_trail(self, surface):
        if len(self._trail) < 2:
            return
        for i in range(1, len(self._trail)):
            t = i / len(self._trail)
            alpha = int(255 * t * t)
            # glow
            gc = (COLOR_SLASH_GLOW[0], COLOR_SLASH_GLOW[1],
                  COLOR_SLASH_GLOW[2])
            gw = max(1, int(MOUSE_TRAIL_GLOW_WIDTH * t))
            gsurf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(gsurf, (*gc, alpha // 2),
                             self._trail[i - 1], self._trail[i], gw)
            surface.blit(gsurf, (0, 0))
            # core
            cc = (COLOR_SLASH[0], COLOR_SLASH[1], COLOR_SLASH[2])
            w = max(1, int(MOUSE_TRAIL_WIDTH * t))
            csurf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(csurf, (*cc, alpha),
                             self._trail[i - 1], self._trail[i], w)
            surface.blit(csurf, (0, 0))

    # ── helpers ───────────────────────────────────────────────

    def glow_pulse(self):
        """Returns a 0-1 pulse value for glowing effects."""
        self._glow_time += GLOW_PULSE_SPEED
        return 0.5 + 0.5 * math.sin(self._glow_time)

    def update(self, dt):
        self.star_field.update(dt)
        self.particle_system.update(dt)

    def begin_frame(self):
        """Prepare the virtual surface for a new frame."""
        self.draw_background(self.virtual_surface)
        self.star_field.draw(self.virtual_surface)

    def end_frame(self, window_surface):
        """Draw trail / particles, then blit virtual → window."""
        self.draw_trail(self.virtual_surface)
        self.particle_system.draw(self.virtual_surface)

        w, h = window_surface.get_size()
        scale, dest = self.get_scale_rect(w, h)
        window_surface.fill((0, 0, 0))
        scaled = pygame.transform.smoothscale(self.virtual_surface,
                                              (dest.width, dest.height))
        window_surface.blit(scaled, dest)
        return scale, dest
