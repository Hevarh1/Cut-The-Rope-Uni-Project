import sys
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pygame
import pymunk
import pymunk.pygame_util

# Constants
WIDTH, HEIGHT = 1280, 720
FPS = 60
PYMUNK_HEIGHT = 720

# Colors
COLOR_BG = (15, 18, 25)
COLOR_PAYLOAD = (220, 60, 60)
COLOR_ANCHOR = (100, 100, 120)
COLOR_ROPE = (139, 90, 60)
COLOR_TARGET = (60, 200, 100)
COLOR_SLASH = (255, 255, 255)
COLOR_PLATFORM = (80, 80, 100)
COLOR_TEXT = (230, 230, 240)
COLOR_SPIKE = (180, 40, 40)


def pymunk_to_pygame(pos: Tuple[float, float]) -> Tuple[int, int]:
    """Convert pymunk coordinates (bottom-left origin) to pygame (top-left origin)."""
    return int(pos[0]), int(PYMUNK_HEIGHT - pos[1])


def pygame_to_pymunk(pos: Tuple[int, int]) -> Tuple[float, float]:
    """Convert pygame coordinates to pymunk coordinates."""
    return float(pos[0]), float(PYMUNK_HEIGHT - pos[1])


def line_segment_intersection(p1, p2, p3, p4) -> bool:
    """
    Check if line segment p1-p2 intersects with line segment p3-p4.
    Returns True if they intersect, False otherwise.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    
    if abs(denom) < 1e-10:
        return False
    
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    
    return 0 <= t <= 1 and 0 <= u <= 1


@dataclass
class Rope:
    joint: pymunk.PinJoint
    anchor_body: pymunk.Body
    payload_body: pymunk.Body
    color: Tuple[int, int, int] = COLOR_ROPE
    width: int = 3


@dataclass
class LevelData:
    payload_pos: Tuple[float, float]
    anchors: List[Tuple[float, float]]
    target_pos: Tuple[float, float]
    target_size: Tuple[float, float]
    platforms: List[Tuple[float, float, float, float]]  # x, y, w, h
    spikes: List[Tuple[float, float, float, float]]


class PayloadDropGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Payload Drop")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Avenir", 24)
        self.big_font = pygame.font.SysFont("Avenir", 56)
        self.small_font = pygame.font.SysFont("Avenir", 18)
        
        # Pymunk setup
        self.space = pymunk.Space()
        self.space.gravity = (0, -900)  # NEGATIVE Y = downward in pymunk!
        
        # Game state
        self.state = "title"
        self.levels = self.create_levels()
        self.level_index = 0
        self.ropes: List[Rope] = []
        self.payload_body: Optional[pymunk.Body] = None
        self.payload_shape: Optional[pymunk.Shape] = None
        self.target_sensor: Optional[pymunk.Shape] = None
        self.in_target = False
        self.target_timer = 0.0
        self.win_time = 2.0
        
        # Mouse trail for cutting
        self.mouse_trail: List[Tuple[int, int]] = []
        self.mouse_down = False
        self.max_trail_length = 15
        
        # Visual effects
        self.impact_effects: List[dict] = []  # Store bounce/impact visual effects
        self.payload_squash = 1.0  # Squash and stretch effect
        self.last_collision_time = 0
        
        # Debug
        self.show_instructions = True
        
    def create_levels(self) -> List[LevelData]:
        # Remember: In Pymunk, Y increases UPWARD. Higher Y = higher on screen.
        # So anchors should have HIGH Y values, targets LOW Y values
        
        # Level 1: Simple drop from above
        level_1 = LevelData(
            payload_pos=(640, 520),  # Start high up
            anchors=[(640, 670)],     # Anchor even higher
            target_pos=(640, 120),    # Target at bottom
            target_size=(120, 80),
            platforms=[],
            spikes=[]
        )
        
        # Level 2: Swing from two ropes
        level_2 = LevelData(
            payload_pos=(400, 470),
            anchors=[(300, 670), (500, 670)],
            target_pos=(800, 120),
            target_size=(140, 80),
            platforms=[(650, 270, 200, 20)],
            spikes=[]
        )
        
        # Level 3: Complex path with obstacles
        level_3 = LevelData(
            payload_pos=(300, 520),
            anchors=[(200, 670), (400, 640)],
            target_pos=(950, 120),
            target_size=(150, 80),
            platforms=[
                (500, 320, 150, 20),
                (750, 240, 150, 20)
            ],
            spikes=[(600, 90, 100, 20)]
        )

        level_4 = LevelData(
            payload_pos=(162, 522),
            anchors=[(242, 525), (337, 518)],
            target_pos=(544, 223),
            target_size=(137, 51),
            platforms=[(242, 279, 161, 82)],
            spikes=[]
        )
        
        level_5 = LevelData(
            payload_pos=(190, 425),
            anchors=[(326, 514), (333, 314), (623, 616)],
            target_pos=(919, 158),
            target_size=(161, 72),
            platforms=[(522, 203, 242, 35), (1038, 221, 50, 209)],
            spikes=[(328, 220, 171, 36), (976, 405, 37, 119)]
        )
        level_6 = LevelData(
            payload_pos=(236, 489),
            anchors=[(134, 537), (353, 623), (533, 605)],
            target_pos=(1154, 113),
            target_size=(180, 63),
            platforms=[(453, 233, 277, 31), (796, 175, 171, 34)],
            spikes=[(1221, 154, 25, 253), (974, 118, 78, 27)]
        )
        
        
        return [level_1, level_2, level_3, level_4, level_5, level_6]
    
    def reset_level(self):
        # Clear physics space
        for rope in self.ropes:
            if rope.joint in self.space.constraints:
                self.space.remove(rope.joint)
        self.ropes.clear()
        
        for body in list(self.space.bodies):
            for shape in body.shapes:
                self.space.remove(shape)
            self.space.remove(body)
        
        for shape in list(self.space.shapes):
            if shape not in [s for b in self.space.bodies for s in b.shapes]:
                self.space.remove(shape)
        
        # Get level data
        level = self.levels[self.level_index]
        
        # Create payload with better physics
        mass = 15
        radius = 20
        moment = pymunk.moment_for_circle(mass, 0, radius)
        self.payload_body = pymunk.Body(mass, moment)
        self.payload_body.position = level.payload_pos
        self.payload_shape = pymunk.Circle(self.payload_body, radius)
        self.payload_shape.friction = 0.7
        self.payload_shape.elasticity = 0.4  # Bounce factor (0=no bounce, 1=perfect bounce)
        self.payload_shape.collision_type = 1
        self.space.add(self.payload_body, self.payload_shape)
        
        # Create anchors and ropes
        for anchor_pos in level.anchors:
            anchor_body = pymunk.Body(body_type=pymunk.Body.STATIC)
            anchor_body.position = anchor_pos
            anchor_shape = pymunk.Circle(anchor_body, 8)
            self.space.add(anchor_body, anchor_shape)
            
            # Create rope (PinJoint)
            rope_joint = pymunk.PinJoint(anchor_body, self.payload_body, (0, 0), (0, 0))
            rope_joint.error_bias = 0.1
            self.space.add(rope_joint)
            
            rope = Rope(
                joint=rope_joint,
                anchor_body=anchor_body,
                payload_body=self.payload_body
            )
            self.ropes.append(rope)
        
        # Create target box with physical walls to catch the payload
        target_x, target_y = level.target_pos
        target_w, target_h = level.target_size
        
        # Store target bounds for manual checking
        self.target_bounds = {
            'x': target_x,
            'y': target_y,
            'w': target_w,
            'h': target_h
        }
        
        # Create physical walls for the target box (3 sides: left, right, bottom)
        wall_thickness = 5
        
        # Left wall
        left_wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        left_wall_body.position = (target_x - target_w/2, target_y)
        left_wall_shape = pymunk.Segment(
            left_wall_body,
            (0, -target_h/2),
            (0, target_h/2),
            wall_thickness
        )
        left_wall_shape.friction = 0.6
        left_wall_shape.elasticity = 0.3  # Target walls have some bounce
        self.space.add(left_wall_body, left_wall_shape)
        
        # Right wall
        right_wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        right_wall_body.position = (target_x + target_w/2, target_y)
        right_wall_shape = pymunk.Segment(
            right_wall_body,
            (0, -target_h/2),
            (0, target_h/2),
            wall_thickness
        )
        right_wall_shape.friction = 0.6
        right_wall_shape.elasticity = 0.3
        self.space.add(right_wall_body, right_wall_shape)
        
        # Bottom wall
        bottom_wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        bottom_wall_body.position = (target_x, target_y - target_h/2)
        bottom_wall_shape = pymunk.Segment(
            bottom_wall_body,
            (-target_w/2, 0),
            (target_w/2, 0),
            wall_thickness
        )
        bottom_wall_shape.friction = 0.7
        bottom_wall_shape.elasticity = 0.25  # Bottom has less bounce to help settling
        bottom_wall_shape.elasticity = 0.2
        self.space.add(bottom_wall_body, bottom_wall_shape)
        
        # Create platforms with bounce
        for px, py, pw, ph in level.platforms:
            platform_body = pymunk.Body(body_type=pymunk.Body.STATIC)
            platform_body.position = (px + pw/2, py + ph/2)
            platform_shape = pymunk.Poly.create_box(platform_body, (pw, ph))
            platform_shape.friction = 0.7
            platform_shape.elasticity = 0.5  # Platforms bounce more
            self.space.add(platform_body, platform_shape)
        
        # Create spikes
        for sx, sy, sw, sh in level.spikes:
            spike_body = pymunk.Body(body_type=pymunk.Body.STATIC)
            spike_body.position = (sx + sw/2, sy + sh/2)
            spike_shape = pymunk.Poly.create_box(spike_body, (sw, sh))
            spike_shape.collision_type = 3
            spike_shape.friction = 0.3
            spike_shape.elasticity = 0.1  # Spikes don't bounce much
            self.space.add(spike_body, spike_shape)
        
        # Create screen boundaries (invisible walls)
        boundary_thickness = 10
        
        # Floor (at y=0 in pymunk)
        floor_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        floor_shape = pymunk.Segment(floor_body, (0, 0), (WIDTH, 0), boundary_thickness)
        floor_shape.friction = 0.5
        self.space.add(floor_body, floor_shape)
        
        # Left wall
        left_bound_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        left_bound_shape = pymunk.Segment(left_bound_body, (0, 0), (0, PYMUNK_HEIGHT), boundary_thickness)
        left_bound_shape.friction = 0.5
        self.space.add(left_bound_body, left_bound_shape)
        
        # Right wall
        right_bound_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        right_bound_shape = pymunk.Segment(right_bound_body, (WIDTH, 0), (WIDTH, PYMUNK_HEIGHT), boundary_thickness)
        right_bound_shape.friction = 0.5
        self.space.add(right_bound_body, right_bound_shape)
        
        # Setup collision handlers
        def on_spike_hit(arbiter, space, data):
            # Mark for reset (can't reset directly in callback)
            self.should_reset = True
            return True
        
        def on_impact(arbiter, space, data):
            # Visual effect on any collision
            if self.payload_body:
                impact_velocity = arbiter.total_impulse.length
                if impact_velocity > 100:  # Only show for significant impacts
                    contact_point = arbiter.contact_point_set.points[0].point_a
                    self.create_impact_effect(contact_point, impact_velocity)
                    self.payload_squash = 0.7  # Squash on impact
            return True
        
        self.space.on_collision(
            collision_type_a=1,
            collision_type_b=3,
            begin=on_spike_hit
        )
        
        # Generic collision handler for visual effects (payload with anything)
        def on_any_collision(arbiter, space, data):
            if self.payload_body:
                impact_velocity = arbiter.total_impulse.length
                if impact_velocity > 150:
                    try:
                        contact_point = arbiter.contact_point_set.points[0].point_a
                        self.create_impact_effect(contact_point, impact_velocity)
                        self.payload_squash = max(0.6, 1.0 - impact_velocity / 2000)
                        self.last_collision_time = pygame.time.get_ticks()
                    except:
                        pass
            return True
        
        # Add generic collision handler (collision_type 0 is default for objects without type)
        self.space.on_collision(
            collision_type_a=1,
            collision_type_b=0,
            post_solve=on_any_collision
        )
        
        self.in_target = False
        self.target_timer = 0.0
        self.should_reset = False
        self.mouse_trail.clear()
        self.impact_effects.clear()
        self.payload_squash = 1.0
    
    def create_impact_effect(self, position: Tuple[float, float], intensity: float):
        """Create visual impact effect at collision point."""
        num_particles = min(int(intensity / 100), 8)
        for _ in range(num_particles):
            import random
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(20, 60)
            self.impact_effects.append({
                'x': position[0],
                'y': position[1],
                'vx': speed * math.cos(angle),
                'vy': speed * math.sin(angle),
                'life': 1.0,
                'size': random.uniform(2, 4)
            })
    
    def check_payload_in_target(self):
        """Check if payload is inside target box using position."""
        if not self.payload_body or not hasattr(self, 'target_bounds'):
            return False
        
        target_x = self.target_bounds['x']
        target_y = self.target_bounds['y']
        target_w = self.target_bounds['w']
        target_h = self.target_bounds['h']
        
        px, py = self.payload_body.position
        
        # Check if payload center is inside the box
        in_x = (target_x - target_w/2) <= px <= (target_x + target_w/2)
        in_y = (target_y - target_h/2) <= py <= (target_y + target_h/2)
        
        return in_x and in_y
    
    def update_effects(self, dt):
        """Update visual effects like squash/stretch and particles."""
        # Recover squash effect
        if self.payload_squash < 1.0:
            self.payload_squash = min(1.0, self.payload_squash + dt * 3)
        
        # Update impact particles
        for effect in self.impact_effects[:]:
            effect['life'] -= dt * 2
            effect['x'] += effect['vx'] * dt
            effect['y'] += effect['vy'] * dt
            effect['vy'] += 500 * dt  # Gravity on particles (pymunk coords)
            
            if effect['life'] <= 0:
                self.impact_effects.remove(effect)
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if self.state == "title":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.state = "level_select"
            
            elif self.state == "level_select":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_level_select_click(event.pos)
                if event.type == pygame.KEYDOWN:
                    if event.unicode.isdigit():
                        index = int(event.unicode) - 1
                        if 0 <= index < len(self.levels):
                            self.level_index = index
                            self.state = "playing"
                            self.reset_level()
            
            elif self.state == "playing":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.reset_level()
                    if event.key == pygame.K_ESCAPE:
                        self.state = "level_select"
                    if event.key == pygame.K_i:
                        self.show_instructions = not self.show_instructions
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_down = True
                    self.mouse_trail = [event.pos]
                
                if event.type == pygame.MOUSEBUTTONUP:
                    self.mouse_down = False
                    self.mouse_trail.clear()
                
                if event.type == pygame.MOUSEMOTION and self.mouse_down:
                    self.mouse_trail.append(event.pos)
                    if len(self.mouse_trail) > self.max_trail_length:
                        self.mouse_trail.pop(0)
                    self.check_rope_cuts()
            
            elif self.state == "win":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.state = "level_select"
    
    def handle_level_select_click(self, mouse_pos):
        margin = 120
        cols = 5
        size = 70
        for i in range(len(self.levels)):
            row = i // cols
            col = i % cols
            x = margin + col * (size + 20)
            y = margin + row * (size + 20)
            rect = pygame.Rect(x, y, size, size)
            if rect.collidepoint(mouse_pos):
                self.level_index = i
                self.state = "playing"
                self.reset_level()
    
    def check_rope_cuts(self):
        if len(self.mouse_trail) < 2:
            return
        
        mouse_start = pygame_to_pymunk(self.mouse_trail[-2])
        mouse_end = pygame_to_pymunk(self.mouse_trail[-1])
        
        ropes_to_remove = []
        for rope in self.ropes:
            rope_start = rope.anchor_body.position
            rope_end = rope.payload_body.position
            
            if line_segment_intersection(mouse_start, mouse_end, rope_start, rope_end):
                ropes_to_remove.append(rope)
        
        for rope in ropes_to_remove:
            if rope.joint in self.space.constraints:
                self.space.remove(rope.joint)
            self.ropes.remove(rope)
    
    def update_playing(self, dt):
        # Check if we should reset (from spike collision)
        if self.should_reset:
            self.should_reset = False
            self.reset_level()
            return
        
        # Update visual effects
        self.update_effects(dt)
        
        # Step physics
        steps = 4
        for _ in range(steps):
            self.space.step(dt / steps)
        
        # Check if payload fell way off screen (shouldn't happen with boundaries, but just in case)
        if self.payload_body.position.y < -100 or self.payload_body.position.y > PYMUNK_HEIGHT + 100:
            self.reset_level()
            return
        
        # Check if payload is in target (position-based)
        currently_in_target = self.check_payload_in_target()
        
        # Update in_target state
        if currently_in_target:
            if not self.in_target:
                self.in_target = True
        else:
            if self.in_target:
                self.in_target = False
                self.target_timer = 0.0
        
        # Check win condition
        if self.in_target:
            # Check if payload is mostly settled (low velocity)
            velocity_magnitude = self.payload_body.velocity.length
            if velocity_magnitude < 80:
                self.target_timer += dt
                if self.target_timer >= self.win_time:
                    self.state = "win"
            else:
                # Moving too fast, decay timer
                self.target_timer = max(0, self.target_timer - dt * 0.5)
        else:
            self.target_timer = 0.0
    
    def draw_playing(self):
        self.screen.fill(COLOR_BG)
        
        level = self.levels[self.level_index]
        
        # Draw platforms
        for px, py, pw, ph in level.platforms:
            rect = pygame.Rect(px, PYMUNK_HEIGHT - py - ph, pw, ph)
            pygame.draw.rect(self.screen, COLOR_PLATFORM, rect)
        
        # Draw spikes
        for sx, sy, sw, sh in level.spikes:
            rect = pygame.Rect(sx, PYMUNK_HEIGHT - sy - sh, sw, sh)
            pygame.draw.rect(self.screen, COLOR_SPIKE, rect)
            # Draw spike triangles
            for i in range(int(sw // 20)):
                x = sx + i * 20
                points = [
                    (x, PYMUNK_HEIGHT - sy - sh),
                    (x + 10, PYMUNK_HEIGHT - sy),
                    (x + 20, PYMUNK_HEIGHT - sy - sh)
                ]
                pygame.draw.polygon(self.screen, (220, 60, 60), points)
        
        # Draw target box (using stored bounds)
        target_x = self.target_bounds['x']
        target_y = self.target_bounds['y']
        target_w = self.target_bounds['w']
        target_h = self.target_bounds['h']
        
        target_rect = pygame.Rect(
            target_x - target_w/2,
            PYMUNK_HEIGHT - target_y - target_h/2,
            target_w,
            target_h
        )
        
        # Color changes based on state
        if self.in_target and self.target_timer > 0:
            progress = self.target_timer / self.win_time
            target_color = (
                int(60 + 140 * progress),
                int(200 + 55 * progress),
                int(100 - 50 * progress)
            )
        elif self.in_target:
            target_color = (100, 255, 150)
        else:
            target_color = COLOR_TARGET
        
        # Draw open-top box
        pygame.draw.rect(self.screen, target_color, target_rect, 4)
        pygame.draw.line(self.screen, target_color, 
                        (target_rect.left, target_rect.top),
                        (target_rect.left, target_rect.bottom), 4)
        pygame.draw.line(self.screen, target_color,
                        (target_rect.right, target_rect.top),
                        (target_rect.right, target_rect.bottom), 4)
        pygame.draw.line(self.screen, target_color,
                        (target_rect.left, target_rect.bottom),
                        (target_rect.right, target_rect.bottom), 4)
        
        # Draw ropes
        for rope in self.ropes:
            start_pos = pymunk_to_pygame(rope.anchor_body.position)
            end_pos = pymunk_to_pygame(rope.payload_body.position)
            pygame.draw.line(self.screen, rope.color, start_pos, end_pos, rope.width)
        
        # Draw anchors
        for anchor_pos in level.anchors:
            pos = pymunk_to_pygame(anchor_pos)
            pygame.draw.circle(self.screen, COLOR_ANCHOR, pos, 10)
            pygame.draw.circle(self.screen, (60, 60, 80), pos, 6)
        
        # Draw impact particles
        for effect in self.impact_effects:
            particle_pos = pymunk_to_pygame((effect['x'], effect['y']))
            # Fade alpha based on remaining life
            alpha = int(255 * effect['life'])
            color = (255, 200, 100, alpha)
            size = int(effect['size'])
            if alpha > 0 and size > 0:
                particle_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(particle_surf, color, (size, size), size)
                self.screen.blit(particle_surf, (particle_pos[0] - size, particle_pos[1] - size))
        
        # Draw payload with squash effect
        if self.payload_body:
            pos = pymunk_to_pygame(self.payload_body.position)
            radius = int(self.payload_shape.radius)
            
            # Apply squash/stretch effect (squash vertically on impact)
            width = radius
            height = int(radius * self.payload_squash)
            
            # Draw as ellipse for squash effect
            if abs(self.payload_squash - 1.0) > 0.05:
                rect = pygame.Rect(pos[0] - width, pos[1] - height, width * 2, height * 2)
                pygame.draw.ellipse(self.screen, COLOR_PAYLOAD, rect)
                pygame.draw.ellipse(self.screen, (180, 50, 50), rect, 2)
            else:
                # Draw normal circle when not squashed
                pygame.draw.circle(self.screen, COLOR_PAYLOAD, pos, radius)
                pygame.draw.circle(self.screen, (180, 50, 50), pos, radius, 2)
        
        # Draw mouse trail
        if len(self.mouse_trail) > 1:
            for i in range(len(self.mouse_trail) - 1):
                alpha = int(255 * (i + 1) / len(self.mouse_trail))
                pygame.draw.line(self.screen, (*COLOR_SLASH, alpha), 
                               self.mouse_trail[i], self.mouse_trail[i + 1], 3)
        
        # Draw HUD
        self.draw_hud()
    
    def draw_hud(self):
        # Level indicator
        level_text = self.font.render(f"Level {self.level_index + 1}", True, COLOR_TEXT)
        self.screen.blit(level_text, (20, 20))
        
        # Rope count
        rope_text = self.small_font.render(f"Ropes: {len(self.ropes)}", True, COLOR_TEXT)
        self.screen.blit(rope_text, (20, 55))
        
        # Debug info
        if self.payload_body:
            vel = int(self.payload_body.velocity.length)
            pos_x, pos_y = int(self.payload_body.position.x), int(self.payload_body.position.y)
            debug_text = self.small_font.render(
                f"Pos: ({pos_x}, {pos_y}) | Vel: {vel}",
                True, (150, 150, 170)
            )
            self.screen.blit(debug_text, (20, 80))
            
            status = "IN TARGET" if self.in_target else "Outside"
            status_color = (100, 255, 100) if self.in_target else (150, 150, 170)
            status_text = self.small_font.render(f"Status: {status}", True, status_color)
            self.screen.blit(status_text, (20, 100))
        
        # Win timer
        if self.in_target and self.target_timer > 0:
            progress = min(1.0, self.target_timer / self.win_time)
            bar_width = 200
            bar_height = 20
            bar_x = WIDTH // 2 - bar_width // 2
            bar_y = 50
            
            pygame.draw.rect(self.screen, (40, 40, 60), 
                           (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(self.screen, COLOR_TARGET,
                           (bar_x, bar_y, int(bar_width * progress), bar_height))
            
            timer_text = self.small_font.render(
                f"Settling... {self.target_timer:.1f}s / {self.win_time:.1f}s",
                True, COLOR_TEXT
            )
            self.screen.blit(timer_text, (bar_x, bar_y + 25))
        
        # Instructions
        if self.show_instructions:
            instructions = [
                "Drag mouse to cut ropes",
                "Get payload into green box",
                "Stay for 2 seconds to win",
                "",
                "R - Restart | I - Toggle Help | Esc - Menu"
            ]
            y = HEIGHT - 130
            for line in instructions:
                surf = self.small_font.render(line, True, (150, 150, 170))
                self.screen.blit(surf, (20, y))
                y += 22
    
    def draw_title(self):
        self.screen.fill(COLOR_BG)
        title = self.big_font.render("Payload Drop", True, COLOR_TEXT)
        subtitle = self.font.render("Click to Start", True, COLOR_TEXT)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20)))
    
    def draw_level_select(self):
        self.screen.fill(COLOR_BG)
        title = self.big_font.render("Select Level", True, COLOR_TEXT)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 80)))
        
        margin = 120
        cols = 5
        size = 70
        for i in range(len(self.levels)):
            row = i // cols
            col = i % cols
            x = margin + col * (size + 20)
            y = margin + row * (size + 20)
            rect = pygame.Rect(x, y, size, size)
            pygame.draw.rect(self.screen, (60, 60, 80), rect)
            label = self.font.render(str(i + 1), True, COLOR_TEXT)
            self.screen.blit(label, label.get_rect(center=rect.center))
    
    def draw_win(self):
        self.screen.fill(COLOR_BG)
        title = self.big_font.render("Delivery Complete!", True, COLOR_TEXT)
        subtitle = self.font.render("Click to continue", True, COLOR_TEXT)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20)))
    
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            
            if self.state == "playing":
                self.update_playing(dt)
                self.draw_playing()
            elif self.state == "title":
                self.draw_title()
            elif self.state == "level_select":
                self.draw_level_select()
            elif self.state == "win":
                self.draw_win()
            
            pygame.display.flip()


if __name__ == "__main__":
    PayloadDropGame().run()
