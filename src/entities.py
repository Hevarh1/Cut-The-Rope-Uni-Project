"""
Game entities: Payload, Target, and visual game objects.
"""

import math
from typing import Tuple, Optional
import pygame

from .config import *
from .utils import pymunk_to_pygame, ease_out_elastic
from .renderer import Renderer


class Candy:
    """The candy ball that the player guides to the target."""
    
    def __init__(self):
        self.rotation = 0.0
    
    def update(self, dt: float, angular_velocity: float):
        """Update visual state."""
        self.rotation += angular_velocity * dt
    
    def on_impact(self, intensity: float):
        """Called when candy hits something."""
        pass  # Simplified - no visual effects
    
    def reset(self):
        """Reset to initial state."""
        self.rotation = 0.0
    
    def draw(self, renderer: Renderer, pos: Tuple[int, int], radius: int):
        """Draw the candy simply."""
        screen = renderer.screen
        
        # Simple circle
        pygame.draw.circle(screen, COLOR_CANDY, pos, radius)
        pygame.draw.circle(screen, COLOR_CANDY_SHADOW, pos, radius, 2)
        
        # Rotation indicator (stripe)
        angle = self.rotation
        end_x = pos[0] + math.cos(angle) * radius * 0.7
        end_y = pos[1] + math.sin(angle) * radius * 0.7
        pygame.draw.line(screen, COLOR_CANDY_SHADOW, pos, 
                       (int(end_x), int(end_y)), 3)


class Target:
    """The target box where the candy needs to land."""
    
    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = x
        self.y = y
        self.width = w
        self.height = h
    
    @property
    def rect(self) -> pygame.Rect:
        """Get pygame rect for drawing."""
        return pygame.Rect(
            self.x - self.width / 2,
            PYMUNK_HEIGHT - self.y - self.height / 2,
            self.width,
            self.height
        )
    
    def contains_point(self, px: float, py: float) -> bool:
        """Check if a point is inside the target."""
        in_x = (self.x - self.width / 2) <= px <= (self.x + self.width / 2)
        in_y = (self.y - self.height / 2) <= py <= (self.y + self.height / 2)
        return in_x and in_y
    
    def update(self, dt: float, has_candy: bool, settle_progress: float):
        """Update animation state."""
        pass  # Simplified
    
    def draw(self, renderer: Renderer, has_candy: bool):
        """Draw the target simply."""
        screen = renderer.screen
        rect = self.rect
        
        # Color based on state
        color = COLOR_TARGET_GLOW if has_candy else COLOR_TARGET
        
        # Inner fill
        inner = rect.inflate(-8, -8)
        pygame.draw.rect(screen, COLOR_TARGET_DARK, inner)
        
        # Three walls (open top box)
        wall_width = 4
        pygame.draw.line(screen, color, 
                        (rect.left, rect.top), (rect.left, rect.bottom), wall_width)
        pygame.draw.line(screen, color, 
                        (rect.right, rect.top), (rect.right, rect.bottom), wall_width)
        pygame.draw.line(screen, color, 
                        (rect.left, rect.bottom), (rect.right, rect.bottom), wall_width)
        
        # Top edge highlights
        pygame.draw.line(screen, COLOR_TARGET_GLOW,
                        (rect.left, rect.top), (rect.left, rect.top + 8), wall_width)
        pygame.draw.line(screen, COLOR_TARGET_GLOW,
                        (rect.right, rect.top), (rect.right, rect.top + 8), wall_width)


class Anchor:
    """Visual anchor point for ropes."""
    
    def __init__(self, pos: Tuple[float, float], letter: str = ""):
        self.pymunk_pos = pos
        self.pygame_pos = pymunk_to_pygame(pos)
        self.letter = letter
    
    def draw(self, renderer: Renderer):
        """Draw anchor simply."""
        pos = self.pygame_pos
        
        # Main body
        pygame.draw.circle(renderer.screen, COLOR_ANCHOR, pos, 10)
        pygame.draw.circle(renderer.screen, COLOR_ANCHOR_RING, pos, 10, 2)
        
        # Draw letter label if assigned
        if self.letter:
            label_pos = (pos[0], pos[1] - 20)
            pygame.draw.circle(renderer.screen, (50, 50, 50), label_pos, 12)
            pygame.draw.circle(renderer.screen, (200, 200, 200), label_pos, 12, 2)
            
            # Draw letter
            font = pygame.font.Font(None, 20)
            text_surf = font.render(self.letter, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=label_pos)
            renderer.screen.blit(text_surf, text_rect)


class Platform:
    """Visual platform."""
    
    def __init__(self, x: float, y: float, w: float, h: float):
        self.rect = pygame.Rect(x, PYMUNK_HEIGHT - y - h, w, h)
    
    def draw(self, renderer: Renderer):
        """Draw platform simply."""
        # Fill
        pygame.draw.rect(renderer.screen, COLOR_PLATFORM, self.rect)
        
        # Border
        pygame.draw.rect(renderer.screen, COLOR_PLATFORM_HIGHLIGHT, 
                        self.rect, width=2)


class Spike:
    """Deadly spike obstacle."""
    
    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.rect = pygame.Rect(x, PYMUNK_HEIGHT - y - h, w, h)
    
    def draw(self, renderer: Renderer):
        """Draw spikes simply."""
        screen = renderer.screen
        
        # Draw spike triangles
        spike_width = 20
        num_spikes = max(1, int(self.width / spike_width))
        actual_width = self.width / num_spikes
        
        for i in range(num_spikes):
            x = self.rect.x + i * actual_width
            points = [
                (x, self.rect.top),
                (x + actual_width / 2, self.rect.bottom),
                (x + actual_width, self.rect.top)
            ]
            
            # Spike body
            pygame.draw.polygon(screen, COLOR_SPIKE, points)
            pygame.draw.polygon(screen, COLOR_SPIKE_DARK, points, width=2)
