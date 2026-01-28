"""
Physics components: Rope chains and payload physics.
"""

import math
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
import pymunk

from .config import *
from .utils import pymunk_to_pygame


@dataclass
class Rope:
    """A rope made of connected chain segments."""
    segments: List[pymunk.Body] = field(default_factory=list)
    constraints: List[pymunk.Constraint] = field(default_factory=list)
    anchor_body: pymunk.Body = None
    payload_body: pymunk.Body = None
    color: Tuple[int, int, int] = COLOR_ROPE
    width: int = ROPE_WIDTH
    letter: str = ""  # Letter identifier for keyboard cutting
    
    def get_points(self) -> List[Tuple[int, int]]:
        """Get all rope points for drawing."""
        points = []
        
        if self.anchor_body:
            points.append(pymunk_to_pygame(self.anchor_body.position))
        
        for segment in self.segments:
            points.append(pymunk_to_pygame(segment.position))
        
        if self.payload_body:
            points.append(pymunk_to_pygame(self.payload_body.position))
        
        return points


class RopeFactory:
    """Factory for creating physics-based ropes."""
    
    @staticmethod
    def create_rope(space: pymunk.Space, anchor_body: pymunk.Body, 
                    end_body: pymunk.Body, anchor_pos: Tuple[float, float],
                    end_pos: Tuple[float, float]) -> Rope:
        """Create a realistic rope chain between two bodies."""
        segments = []
        constraints = []
        
        # Calculate rope parameters
        dx = end_pos[0] - anchor_pos[0]
        dy = end_pos[1] - anchor_pos[1]
        rope_length = math.sqrt(dx * dx + dy * dy)
        
        # Calculate number of segments
        num_segments = max(2, int(rope_length / ROPE_SEGMENT_LENGTH))
        segment_length = rope_length / (num_segments + 1)
        
        # Create chain segments
        prev_body = anchor_body
        
        for i in range(num_segments):
            # Position along the rope
            t = (i + 1) / (num_segments + 1)
            seg_x = anchor_pos[0] + dx * t
            seg_y = anchor_pos[1] + dy * t
            
            # Create segment body
            segment_body = pymunk.Body(mass=ROPE_SEGMENT_MASS, 
                                       moment=ROPE_SEGMENT_MOMENT)
            segment_body.position = (seg_x, seg_y)
            
            # Sensor shape for cutting detection
            segment_shape = pymunk.Circle(segment_body, 2)
            segment_shape.sensor = True
            segment_shape.filter = pymunk.ShapeFilter(categories=0x10)
            
            space.add(segment_body, segment_shape)
            segments.append(segment_body)
            
            # Pin joint for fixed distance
            pin = pymunk.PinJoint(prev_body, segment_body, (0, 0), (0, 0))
            pin.distance = segment_length
            pin.error_bias = ROPE_ERROR_BIAS
            space.add(pin)
            constraints.append(pin)
            
            # Damping to reduce oscillation
            damping = pymunk.DampedRotarySpring(prev_body, segment_body, 0, 0, ROPE_DAMPING)
            space.add(damping)
            constraints.append(damping)
            
            prev_body = segment_body
        
        # Connect to end body
        final_pin = pymunk.PinJoint(prev_body, end_body, (0, 0), (0, 0))
        final_pin.distance = segment_length
        final_pin.error_bias = ROPE_ERROR_BIAS
        space.add(final_pin)
        constraints.append(final_pin)
        
        final_damping = pymunk.DampedRotarySpring(prev_body, end_body, 0, 0, ROPE_DAMPING)
        space.add(final_damping)
        constraints.append(final_damping)
        
        return Rope(
            segments=segments,
            constraints=constraints,
            anchor_body=anchor_body,
            payload_body=end_body
        )
    
    @staticmethod
    def destroy_rope(space: pymunk.Space, rope: Rope):
        """Remove a rope from the physics space."""
        for constraint in rope.constraints:
            if constraint in space.constraints:
                space.remove(constraint)
        
        for segment in rope.segments:
            for shape in segment.shapes:
                if shape in space.shapes:
                    space.remove(shape)
            if segment in space.bodies:
                space.remove(segment)


class PhysicsWorld:
    """Manages the pymunk physics space and world objects."""
    
    def __init__(self):
        self.space = pymunk.Space()
        self.space.gravity = (0, GRAVITY)
        
        self.payload_body: Optional[pymunk.Body] = None
        self.payload_shape: Optional[pymunk.Shape] = None
        self.ropes: List[Rope] = []
        
        self._should_reset = False
        
    def clear(self):
        """Clear all physics objects."""
        # Remove ropes
        for rope in self.ropes:
            RopeFactory.destroy_rope(self.space, rope)
        self.ropes.clear()
        
        # Remove all bodies and shapes
        for body in list(self.space.bodies):
            for shape in body.shapes:
                self.space.remove(shape)
            self.space.remove(body)
        
        for constraint in list(self.space.constraints):
            self.space.remove(constraint)
        
        self.payload_body = None
        self.payload_shape = None
    
    def create_payload(self, pos: Tuple[float, float]) -> Tuple[pymunk.Body, pymunk.Shape]:
        """Create the payload ball."""
        moment = pymunk.moment_for_circle(PAYLOAD_MASS, 0, PAYLOAD_RADIUS)
        body = pymunk.Body(PAYLOAD_MASS, moment)
        body.position = pos
        
        shape = pymunk.Circle(body, PAYLOAD_RADIUS)
        shape.friction = PAYLOAD_FRICTION
        shape.elasticity = PAYLOAD_ELASTICITY
        shape.collision_type = 1  # Payload collision type
        
        self.space.add(body, shape)
        self.payload_body = body
        self.payload_shape = shape
        
        return body, shape
    
    def create_anchor(self, pos: Tuple[float, float]) -> pymunk.Body:
        """Create a static anchor point."""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = pos
        
        shape = pymunk.Circle(body, 8)
        self.space.add(body, shape)
        
        return body
    
    def create_rope(self, anchor_pos: Tuple[float, float], letter: str = "") -> Rope:
        """Create a rope from anchor to payload."""
        anchor = self.create_anchor(anchor_pos)
        rope = RopeFactory.create_rope(
            self.space, anchor, self.payload_body,
            anchor_pos, self.payload_body.position
        )
        rope.letter = letter
        self.ropes.append(rope)
        return rope
    
    def create_platform(self, x: float, y: float, w: float, h: float):
        """Create a static platform."""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (x + w/2, y + h/2)
        
        shape = pymunk.Poly.create_box(body, (w, h))
        shape.friction = PLATFORM_FRICTION
        shape.elasticity = PLATFORM_ELASTICITY
        
        self.space.add(body, shape)
    
    def create_spike(self, x: float, y: float, w: float, h: float):
        """Create a deadly spike."""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (x + w/2, y + h/2)
        
        shape = pymunk.Poly.create_box(body, (w, h))
        shape.collision_type = 3  # Spike collision type
        shape.friction = SPIKE_FRICTION
        shape.elasticity = SPIKE_ELASTICITY
        
        self.space.add(body, shape)
    
    def create_target_box(self, x: float, y: float, w: float, h: float):
        """Create target box with three walls."""
        wall_thickness = 5
        
        # Left wall
        left = pymunk.Body(body_type=pymunk.Body.STATIC)
        left.position = (x - w/2, y)
        left_shape = pymunk.Segment(left, (0, -h/2), (0, h/2), wall_thickness)
        left_shape.friction = TARGET_WALL_FRICTION
        left_shape.elasticity = TARGET_WALL_ELASTICITY
        self.space.add(left, left_shape)
        
        # Right wall
        right = pymunk.Body(body_type=pymunk.Body.STATIC)
        right.position = (x + w/2, y)
        right_shape = pymunk.Segment(right, (0, -h/2), (0, h/2), wall_thickness)
        right_shape.friction = TARGET_WALL_FRICTION
        right_shape.elasticity = TARGET_WALL_ELASTICITY
        self.space.add(right, right_shape)
        
        # Bottom
        bottom = pymunk.Body(body_type=pymunk.Body.STATIC)
        bottom.position = (x, y - h/2)
        bottom_shape = pymunk.Segment(bottom, (-w/2, 0), (w/2, 0), wall_thickness)
        bottom_shape.friction = TARGET_FLOOR_FRICTION
        bottom_shape.elasticity = TARGET_FLOOR_ELASTICITY
        self.space.add(bottom, bottom_shape)
    
    def create_boundaries(self):
        """Create screen boundary walls."""
        thickness = 10
        
        # Floor
        floor = pymunk.Body(body_type=pymunk.Body.STATIC)
        floor_shape = pymunk.Segment(floor, (0, 0), (WIDTH, 0), thickness)
        floor_shape.friction = 0.5
        self.space.add(floor, floor_shape)
        
        # Walls
        left = pymunk.Body(body_type=pymunk.Body.STATIC)
        left_shape = pymunk.Segment(left, (0, 0), (0, PYMUNK_HEIGHT), thickness)
        left_shape.friction = 0.5
        self.space.add(left, left_shape)
        
        right = pymunk.Body(body_type=pymunk.Body.STATIC)
        right_shape = pymunk.Segment(right, (WIDTH, 0), (WIDTH, PYMUNK_HEIGHT), thickness)
        right_shape.friction = 0.5
        self.space.add(right, right_shape)
    
    def setup_collision_handlers(self, on_spike_hit, on_impact):
        """Setup collision handlers for game events."""
        # Spike collision
        self.space.on_collision(
            collision_type_a=1,
            collision_type_b=3,
            begin=on_spike_hit
        )
        
        # Generic impact for visual effects
        self.space.on_collision(
            collision_type_a=1,
            collision_type_b=0,
            post_solve=on_impact
        )
    
    def step(self, dt: float):
        """Step the physics simulation."""
        for _ in range(PHYSICS_STEPS):
            self.space.step(dt / PHYSICS_STEPS)
    
    def cut_rope_at(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Rope]:
        """Check for rope cuts and return cut ropes."""
        from .utils import line_segment_intersection
        
        cut_ropes = []
        
        for rope in self.ropes:
            cut = False
            
            # Check anchor to first segment
            if rope.segments:
                if line_segment_intersection(
                    start, end,
                    rope.anchor_body.position, rope.segments[0].position
                ):
                    cut = True
            
            # Check between segments
            if not cut:
                for i in range(len(rope.segments) - 1):
                    if line_segment_intersection(
                        start, end,
                        rope.segments[i].position, rope.segments[i + 1].position
                    ):
                        cut = True
                        break
            
            # Check last segment to payload
            if not cut and rope.segments:
                if line_segment_intersection(
                    start, end,
                    rope.segments[-1].position, rope.payload_body.position
                ):
                    cut = True
            
            if cut:
                cut_ropes.append(rope)
        
        # Remove cut ropes
        for rope in cut_ropes:
            RopeFactory.destroy_rope(self.space, rope)
            self.ropes.remove(rope)
        
        return cut_ropes
    
    def cut_rope_by_index(self, index: int):
        """Cut a specific rope by its index."""
        if 0 <= index < len(self.ropes):
            rope = self.ropes[index]
            RopeFactory.destroy_rope(self.space, rope)
            self.ropes.pop(index)
    
    def cut_rope_by_letter(self, letter: str):
        """Cut a specific rope by its letter identifier."""
        for i, rope in enumerate(self.ropes):
            if rope.letter == letter:
                RopeFactory.destroy_rope(self.space, rope)
                self.ropes.pop(i)
                break
