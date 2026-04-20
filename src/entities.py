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
import pymunk

from .config import (
    CANDY_MASS, CANDY_RADIUS, CANDY_FRICTION, CANDY_ELASTICITY,
    BALL_ROTATION_VISUAL_SPEED,
    MAGNET_RADIUS,
    SLIDER_SNAP_DIST,
    WINCH_EXTEND_SPEED, WINCH_MIN_LENGTH, WINCH_MAX_LENGTH,
    TELEPORT_RADIUS, TELEPORT_COOLDOWN, TELEPORT_OFFSET,
    SPIDER_SPEED, SPIDER_CATCH_DIST,
    SQUASH_RECOVERY_SPEED, SQUASH_MIN, SQUASH_INTENSITY,
    PLATFORM_FRICTION, PLATFORM_ELASTICITY,
    SPIKE_FRICTION, SPIKE_ELASTICITY,
)
from .types import CT_CANDY, CT_TARGET, CT_PLATFORM, CT_SPIKE, CT_TELE_A, CT_TELE_B
from .utils import pymunk_to_pygame, lerp, clamp, distance


# =====================================================================
#  Candy
# =====================================================================

class Candy:
    """Physics-driven candy body the player must deliver to the target."""

    COLLISION_TYPE = CT_CANDY

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


# =====================================================================
#  Target (Om Nom's mouth) - with swallow animation
# =====================================================================

class Target:
    """The collection zone for the candy. Plays a swallow animation on win."""

    COLLISION_TYPE = CT_TARGET

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


# =====================================================================
#  Platform
# =====================================================================

class Platform:
    """Static collision surface."""

    COLLISION_TYPE = CT_PLATFORM

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


# =====================================================================
#  Spike
# =====================================================================

class Spike:
    """Instant-kill obstacle. Triangular spikes on a base."""

    COLLISION_TYPE = CT_SPIKE

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


# =====================================================================
#  Teleport Pair (Magic Hats)
# =====================================================================

class TeleportPair:
    """Two magic hats. Candy entering hat A exits hat B (and vice-versa).
    Velocity preserved; direction rotated by delta_theta = theta_B - theta_A + pi.
    """

    COLLISION_TYPE_A = CT_TELE_A
    COLLISION_TYPE_B = CT_TELE_B

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
