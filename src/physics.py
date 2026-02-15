"""
Physics world for Cut The Rope.

Manages the Pymunk space, rope creation (PinJoint chains),
collision handlers, walls, and rope topology changes.
"""

import math
import pymunk

from .config import (
    WIDTH, HEIGHT, PYMUNK_HEIGHT, GRAVITY, PHYSICS_STEPS,
    ROPE_SEGMENT_LENGTH, ROPE_SEGMENT_MASS, ROPE_SEGMENT_MOMENT,
    ROPE_DAMPING, ROPE_ERROR_BIAS,
    TARGET_WALL_FRICTION, TARGET_WALL_ELASTICITY,
    TARGET_FLOOR_FRICTION, TARGET_FLOOR_ELASTICITY,
    WINCH_MIN_LENGTH, WINCH_MAX_LENGTH,
)
from .utils import distance


# Collision types (must match entities)
CT_CANDY   = 1
CT_TARGET  = 2
CT_PLATFORM = 3
CT_SPIKE   = 4
CT_TELE_A  = 5
CT_TELE_B  = 6


class RopeData:
    """Stores all physics objects for a single rope chain."""

    def __init__(self):
        self.bodies = []       # list of pymunk.Body (segment bodies)
        self.shapes = []       # list of pymunk.Shape (segment shapes)
        self.joints = []       # list of joints (PinJoint)
        self.anchor_joint = None  # joint linking first segment to anchor
        self.candy_joint = None   # joint linking last segment to candy
        self.letter = ""
        self.anchor_body = None  # reference to the anchor's body

    def all_objects(self):
        """Return flat list of everything in the space for removal."""
        objs = []
        objs.extend(self.bodies)
        objs.extend(self.shapes)
        objs.extend(self.joints)
        if self.anchor_joint:
            objs.append(self.anchor_joint)
        if self.candy_joint:
            objs.append(self.candy_joint)
        return objs


class PhysicsWorld:
    """Wraps pymunk.Space and provides rope creation / destruction."""

    def __init__(self, level_height: int = PYMUNK_HEIGHT):
        self.space = pymunk.Space()
        self.space.gravity = (0, GRAVITY)
        self.space.damping = 0.92
        self.space.iterations = 30
        self.level_height = level_height

        # Post-step action queue: callbacks that must NOT run during space.step()
        self._post_step_actions: list = []

        # Walls (invisible boundaries)
        self._walls = []
        self._create_walls()

        # Ropes managed by this world
        self.ropes: list[RopeData] = []

        # Collision callbacks (set by Game)
        self._on_target_hit = None
        self._on_spike_hit = None
        self._on_teleport_a = None
        self._on_teleport_b = None

    # -- walls ---------------------------------------------------------

    def _create_walls(self):
        h = self.level_height
        walls = [
            # left
            pymunk.Segment(self.space.static_body, (-10, 0), (-10, h), 10),
            # right
            pymunk.Segment(self.space.static_body, (WIDTH + 10, 0), (WIDTH + 10, h), 10),
            # floor
            pymunk.Segment(self.space.static_body, (0, -10), (WIDTH, -10), 10),
        ]
        for w in walls:
            if w.a[1] == w.b[1]:  # horizontal = floor
                w.friction = TARGET_FLOOR_FRICTION
                w.elasticity = TARGET_FLOOR_ELASTICITY
            else:
                w.friction = TARGET_WALL_FRICTION
                w.elasticity = TARGET_WALL_ELASTICITY
        self.space.add(*walls)
        self._walls = walls

    # -- collision setup -----------------------------------------------

    def setup_collisions(self, on_target, on_spike, on_tele_a, on_tele_b):
        self._on_target_hit = on_target
        self._on_spike_hit = on_spike
        self._on_teleport_a = on_tele_a
        self._on_teleport_b = on_tele_b

        # Pymunk 7.x uses space.on_collision() instead of add_collision_handler()
        self.space.on_collision(
            CT_CANDY, CT_TARGET,
            begin=self._cb_target,
        )
        self.space.on_collision(
            CT_CANDY, CT_SPIKE,
            begin=self._cb_spike,
        )
        self.space.on_collision(
            CT_CANDY, CT_TELE_A,
            begin=self._cb_tele_a,
        )
        self.space.on_collision(
            CT_CANDY, CT_TELE_B,
            begin=self._cb_tele_b,
        )

    def _cb_target(self, arbiter, space, data):
        if self._on_target_hit:
            self._post_step_actions.append(self._on_target_hit)

    def _cb_spike(self, arbiter, space, data):
        if self._on_spike_hit:
            self._post_step_actions.append(self._on_spike_hit)

    def _cb_tele_a(self, arbiter, space, data):
        if self._on_teleport_a:
            self._post_step_actions.append(self._on_teleport_a)

    def _cb_tele_b(self, arbiter, space, data):
        if self._on_teleport_b:
            self._post_step_actions.append(self._on_teleport_b)

    # -- rope creation -------------------------------------------------

    def create_rope(self, anchor_body, candy_body, length: float,
                    letter: str = "",
                    group: int = 0) -> RopeData:
        """Create a chain of PinJoint segments from anchor_body to candy_body."""
        rd = RopeData()
        rd.letter = letter.upper()
        rd.anchor_body = anchor_body

        num_segs = max(2, int(length / ROPE_SEGMENT_LENGTH))
        seg_len = length / num_segs

        # direction from anchor → candy
        ax, ay = anchor_body.position
        cx, cy = candy_body.position
        dx, dy = cx - ax, cy - ay
        d = math.sqrt(dx * dx + dy * dy)
        if d < 1e-3:
            dx, dy = 0, -1
            d = 1
        ux, uy = dx / d, dy / d

        grp = group if group else id(rd) % (2**30)

        prev_body = anchor_body
        for i in range(num_segs):
            frac = (i + 1) / (num_segs + 1)
            bx = ax + dx * frac
            by = ay + dy * frac

            body = pymunk.Body(ROPE_SEGMENT_MASS, ROPE_SEGMENT_MOMENT)
            body.position = (bx, by)

            shape = pymunk.Segment(body, (0, -seg_len / 2), (0, seg_len / 2), 2)
            shape.sensor = True
            shape.filter = pymunk.ShapeFilter(group=grp)

            # joint
            local_a = (0, 0) if prev_body is anchor_body else (0, -seg_len / 2)
            local_b = (0, seg_len / 2)

            joint = pymunk.PinJoint(prev_body, body, local_a, local_b)
            joint.error_bias = pow(1.0 - ROPE_ERROR_BIAS, 60)

            # damping (low stiffness: don't force alignment, just damp rotation)
            dj = pymunk.DampedRotarySpring(prev_body, body, 0, 100, ROPE_DAMPING)

            self.space.add(body, shape, joint, dj)
            rd.bodies.append(body)
            rd.shapes.append(shape)
            rd.joints.append(joint)
            rd.joints.append(dj)

            if prev_body is anchor_body:
                rd.anchor_joint = joint

            prev_body = body

        # Link last segment to candy
        local_a_last = (0, -seg_len / 2)
        candy_link = pymunk.PinJoint(prev_body, candy_body, local_a_last, (0, 0))
        candy_link.error_bias = pow(1.0 - ROPE_ERROR_BIAS, 60)

        self.space.add(candy_link)
        rd.candy_joint = candy_link

        self.ropes.append(rd)
        return rd

    # -- rope destruction (cut) ----------------------------------------

    def cut_rope(self, rope_data: RopeData):
        """Remove all physics objects of a rope from the space."""
        if rope_data not in self.ropes:
            return
        for obj in rope_data.all_objects():
            try:
                self.space.remove(obj)
            except Exception:
                pass
        self.ropes.remove(rope_data)

    def cut_rope_by_letter(self, letter: str) -> RopeData | None:
        """Find rope with matching letter and cut it. Returns the cut RopeData."""
        letter = letter.upper()
        for rd in list(self.ropes):
            if rd.letter == letter:
                self.cut_rope(rd)
                return rd
        return None

    # -- winch rope length adjustment ----------------------------------

    def adjust_winch_rope(self, rope_data: RopeData, target_length: float):
        """Adjust a winch rope to *target_length* by rescaling every
        PinJoint distance **and** its local anchor offsets so that the
        constraint geometry stays self-consistent and pymunk doesn't
        generate spurious forces that fling the candy upward.

        Also stiffens the rotary springs at short lengths to keep the
        rope taut and prevent it from folding over itself.
        """
        if not rope_data or not rope_data.bodies:
            return

        num_segs = len(rope_data.bodies)
        if num_segs == 0:
            return

        # Minimum per-segment length – prevents total collapse.
        MIN_SEG = 8.0
        new_seg_len = max(MIN_SEG, target_length / num_segs)
        half = new_seg_len * 0.5

        # How "retracted" the rope is (0 = fully extended, 1 = fully retracted)
        retract_ratio = 1.0 - min(1.0, target_length / max(1.0, WINCH_MAX_LENGTH))

        # --- internal joints (stored in rd.joints) ---
        for joint in rope_data.joints:
            if isinstance(joint, pymunk.PinJoint):
                if joint is rope_data.anchor_joint:
                    # anchor (0,0) → first-segment top (0, half)
                    joint.anchor_a = (0, 0)
                    joint.anchor_b = (0, half)
                    joint.distance = half
                else:
                    # segment-to-segment: bottom of A → top of B
                    joint.anchor_a = (0, -half)
                    joint.anchor_b = (0, half)
                    joint.distance = new_seg_len
            elif isinstance(joint, pymunk.DampedRotarySpring):
                joint.stiffness = 100 + 400 * retract_ratio
                joint.damping = ROPE_DAMPING + 80 * retract_ratio

        # --- candy joint (stored separately) ---
        cj = rope_data.candy_joint
        if cj and isinstance(cj, pymunk.PinJoint):
            cj.anchor_a = (0, -half)
            cj.anchor_b = (0, 0)
            cj.distance = half

        # --- update segment shapes so they match the new length ---
        for body, shape in zip(rope_data.bodies, rope_data.shapes):
            if isinstance(shape, pymunk.Segment):
                shape.unsafe_set_endpoints((0, -half), (0, half))

    # -- step ----------------------------------------------------------

    def step(self, dt: float):
        sub_dt = dt / PHYSICS_STEPS
        for _ in range(PHYSICS_STEPS):
            self.space.step(sub_dt)

        # Flush deferred collision callbacks (safe: space is no longer locked)
        actions = self._post_step_actions
        self._post_step_actions = []
        for action in actions:
            action()

        # Clamp rope-segment velocity to prevent explosive behaviour
        for rd in self.ropes:
            for body in rd.bodies:
                vx, vy = body.velocity
                speed_sq = vx * vx + vy * vy
                max_speed = 1500.0
                if speed_sq > max_speed * max_speed:
                    scale = max_speed / (speed_sq ** 0.5)
                    body.velocity = (vx * scale, vy * scale)

    # -- helpers -------------------------------------------------------

    def get_rope_bodies_with_endpoints(self, rope_data: RopeData, candy_body):
        """Return [anchor_body] + segment_bodies + [candy_body] for drawing."""
        if not rope_data:
            return []
        result = []
        if rope_data.anchor_body:
            result.append(rope_data.anchor_body)
        result.extend(rope_data.bodies)
        if candy_body:
            result.append(candy_body)
        return result
