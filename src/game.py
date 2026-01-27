"""
Main game class that ties everything together.
"""

import sys
import time
from typing import List, Tuple
import pygame

from .config import *
from .utils import pymunk_to_pygame, pygame_to_pymunk
from .renderer import Renderer, ParticleSystem, StarField
from .physics import PhysicsWorld
from .levels import LevelManager
from .entities import Payload, Target, Anchor, Platform, Spike
from .ui import FontManager, TitleScreen, LevelSelectScreen, WinScreen, HUD


class PayloadDropGame:
    """Main game class."""
    
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)
        
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        
        # Core systems
        self.renderer = Renderer(self.screen)
        self.fonts = FontManager()
        self.star_field = StarField()
        self.particles = ParticleSystem()
        self.physics = PhysicsWorld()
        self.levels = LevelManager()
        
        # Game state
        self.state = "title"
        self.running = True
        
        # Entities (created per level)
        self.payload = Payload()
        self.target: Target = None
        self.anchors: List[Anchor] = []
        self.platforms: List[Platform] = []
        self.spikes: List[Spike] = []
        
        # Target state
        self.in_target = False
        self.settle_timer = 0.0
        self._should_reset = False
        
        # Mouse input
        self.mouse_trail: List[Tuple[int, int]] = []
        self.mouse_down = False
        
        # UI screens
        self.title_screen = TitleScreen(self.renderer, self.fonts, self.star_field)
        self.level_select = LevelSelectScreen(self.renderer, self.fonts, 
                                             self.levels.level_count, self.star_field)
        self.win_screen = WinScreen(self.renderer, self.fonts, self.star_field)
        self.hud = HUD(self.renderer, self.fonts)
    
    def reset_level(self):
        """Reset current level."""
        level = self.levels.current_level
        
        # Clear physics
        self.physics.clear()
        
        # Reset state
        self.payload.reset()
        self.particles.clear()
        self.mouse_trail.clear()
        self.in_target = False
        self.settle_timer = 0.0
        self._should_reset = False
        
        # Create physics objects
        self.physics.create_payload(level.payload_pos)
        
        for anchor_pos in level.anchors:
            self.physics.create_rope(anchor_pos)
        
        self.physics.create_target_box(level.target_pos[0], level.target_pos[1],
                                       level.target_size[0], level.target_size[1])
        
        for px, py, pw, ph in level.platforms:
            self.physics.create_platform(px, py, pw, ph)
        
        for sx, sy, sw, sh in level.spikes:
            self.physics.create_spike(sx, sy, sw, sh)
        
        self.physics.create_boundaries()
        
        # Setup collision handlers
        self.physics.setup_collision_handlers(
            on_spike_hit=self._on_spike_hit,
            on_impact=self._on_impact
        )
        
        # Create visual entities
        self.target = Target(level.target_pos[0], level.target_pos[1],
                            level.target_size[0], level.target_size[1])
        
        self.anchors = [Anchor(pos) for pos in level.anchors]
        self.platforms = [Platform(*p) for p in level.platforms]
        self.spikes = [Spike(*s) for s in level.spikes]
    
    def _on_spike_hit(self, arbiter, space, data):
        """Called when payload hits a spike."""
        self._should_reset = True
        return True
    
    def _on_impact(self, arbiter, space, data):
        """Called on payload impact for visual effects."""
        try:
            impulse = arbiter.total_impulse.length
            if impulse > 150:
                contact = arbiter.contact_point_set.points[0].point_a
                self.payload.on_impact(impulse)
                self.particles.emit(contact, count=min(8, int(impulse / 100)))
        except:
            pass
        return True
    
    def handle_events(self):
        """Process input events."""
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if self.state == "title":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.state = "level_select"
            
            elif self.state == "level_select":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    level = self.level_select.get_clicked_level(mouse_pos)
                    if level >= 0:
                        self.levels.select_level(level)
                        self.state = "playing"
                        self.reset_level()
                
                if event.type == pygame.KEYDOWN:
                    if event.unicode.isdigit():
                        level = int(event.unicode) - 1
                        if self.levels.select_level(level):
                            self.state = "playing"
                            self.reset_level()
            
            elif self.state == "playing":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.reset_level()
                    elif event.key == pygame.K_ESCAPE:
                        self.state = "level_select"
                    elif event.key == pygame.K_i:
                        self.hud.toggle_instructions()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_down = True
                    self.mouse_trail = [mouse_pos]
                
                if event.type == pygame.MOUSEBUTTONUP:
                    self.mouse_down = False
                    self.mouse_trail.clear()
                
                if event.type == pygame.MOUSEMOTION and self.mouse_down:
                    self.mouse_trail.append(mouse_pos)
                    if len(self.mouse_trail) > MOUSE_TRAIL_LENGTH:
                        self.mouse_trail.pop(0)
                    self._check_rope_cuts()
            
            elif self.state == "win":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.state = "level_select"
        
        # Update hover states
        if self.state == "level_select":
            self.level_select.update(0, mouse_pos)
    
    def _check_rope_cuts(self):
        """Check if mouse trail cuts any ropes."""
        if len(self.mouse_trail) < 2:
            return
        
        start = pygame_to_pymunk(self.mouse_trail[-2])
        end = pygame_to_pymunk(self.mouse_trail[-1])
        
        cut_ropes = self.physics.cut_rope_at(start, end)
        
        # Emit particles at cut point
        for rope in cut_ropes:
            mid_point = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            self.particles.emit(mid_point, count=10, 
                              color=COLOR_PARTICLE_CUT,
                              speed_range=(50, 120))
    
    def update(self, dt: float):
        """Update game state."""
        if self.state == "title":
            self.title_screen.update(dt)
        
        elif self.state == "level_select":
            pass  # Handled in events
        
        elif self.state == "playing":
            self._update_playing(dt)
        
        elif self.state == "win":
            self.win_screen.update(dt)
    
    def _update_playing(self, dt: float):
        """Update gameplay."""
        # Check for spike death
        if self._should_reset:
            self._should_reset = False
            self.reset_level()
            return
        
        # Update payload visuals
        if self.physics.payload_body:
            self.payload.update(dt, self.physics.payload_body.angular_velocity)
        
        # Update particles
        self.particles.update(dt)
        
        # Step physics
        self.physics.step(dt)
        
        # Check bounds
        if self.physics.payload_body:
            py = self.physics.payload_body.position.y
            if py < -100 or py > PYMUNK_HEIGHT + 100:
                self.reset_level()
                return
        
        # Check target state
        if self.physics.payload_body:
            px, py = self.physics.payload_body.position
            currently_in = self.target.contains_point(px, py)
            
            if currently_in:
                self.in_target = True
                
                # Check velocity for settling
                velocity = self.physics.payload_body.velocity.length
                if velocity < TARGET_SETTLE_VELOCITY:
                    self.settle_timer += dt
                    if self.settle_timer >= TARGET_SETTLE_TIME:
                        self.state = "win"
                else:
                    self.settle_timer = max(0, self.settle_timer - dt * 0.5)
            else:
                self.in_target = False
                self.settle_timer = 0.0
        
        # Update target animation
        progress = self.settle_timer / TARGET_SETTLE_TIME if self.in_target else 0
        self.target.update(dt, self.in_target, progress)
    
    def draw(self):
        """Draw current state."""
        if self.state == "title":
            self.title_screen.draw()
        
        elif self.state == "level_select":
            self.level_select.draw()
        
        elif self.state == "playing":
            self._draw_playing()
        
        elif self.state == "win":
            self.win_screen.draw(self.levels.current_index)
        
        pygame.display.flip()
    
    def _draw_playing(self):
        """Draw gameplay."""
        # Background
        self.renderer.draw_gradient_rect(COLOR_BG_GRADIENT_TOP, COLOR_BG_GRADIENT_BOTTOM,
                                        pygame.Rect(0, 0, WIDTH, HEIGHT))
        
        # Stars
        self.star_field.draw(self.screen, time.time())
        
        # Platforms
        for platform in self.platforms:
            platform.draw(self.renderer)
        
        # Spikes
        for spike in self.spikes:
            spike.draw(self.renderer)
        
        # Target
        self.target.draw(self.renderer, self.in_target)
        
        # Ropes
        for rope in self.physics.ropes:
            points = rope.get_points()
            if len(points) > 1:
                # Shadow
                shadow_points = [(p[0] + 2, p[1] + 2) for p in points]
                pygame.draw.lines(self.screen, COLOR_ROPE_SHADOW, False, 
                                shadow_points, ROPE_WIDTH)
                # Main rope
                pygame.draw.lines(self.screen, COLOR_ROPE, False, 
                                points, ROPE_WIDTH)
        
        # Anchors
        for anchor in self.anchors:
            anchor.draw(self.renderer)
        
        # Particles
        self.particles.draw(self.renderer, pymunk_to_pygame)
        
        # Payload
        if self.physics.payload_body:
            pos = pymunk_to_pygame(self.physics.payload_body.position)
            self.payload.draw(self.renderer, pos, PAYLOAD_RADIUS)
        
        # Mouse trail
        self._draw_mouse_trail()
        
        # HUD
        rope_count = len(self.physics.ropes)
        self.hud.draw(self.levels.current_index, rope_count, self.in_target,
                     self.settle_timer, TARGET_SETTLE_TIME)
    
    def _draw_mouse_trail(self):
        """Draw the cutting mouse trail."""
        if len(self.mouse_trail) > 1:
            for i in range(len(self.mouse_trail) - 1):
                t = (i + 1) / len(self.mouse_trail)
                alpha = int(255 * t)
                
                # Glow
                pygame.draw.line(self.screen, (*COLOR_SLASH_GLOW[:3], alpha // 2),
                               self.mouse_trail[i], self.mouse_trail[i + 1],
                               MOUSE_TRAIL_GLOW_WIDTH)
                # Core
                pygame.draw.line(self.screen, (*COLOR_SLASH[:3], alpha),
                               self.mouse_trail[i], self.mouse_trail[i + 1],
                               MOUSE_TRAIL_WIDTH)
    
    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            
            self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()
        sys.exit()
