"""
Game entities: Payload, Target, and visual game objects.
"""

import math
from typing import Tuple, Optional
import pygame

from .config import *
from .utils import pymunk_to_pygame, ease_out_elastic
from .renderer import Renderer


class Payload:
    """The payload ball that the player guides to the target."""
    
    def __init__(self):
        self.rotation = 0.0
        self.squash = 1.0
        self.last_impact_time = 0
        
        # Smooth animation values
        self._target_squash = 1.0
        self._glow_intensity = 0.0
    
    def update(self, dt: float, angular_velocity: float):
        """Update visual state."""
        # Update rotation based on physics
        self.rotation += angular_velocity * dt
        
        # Smooth squash recovery with elastic easing
        if self.squash < self._target_squash:
            self.squash = min(self._target_squash, 
                            self.squash + dt * SQUASH_RECOVERY_SPEED)
        
        # Decay glow
        self._glow_intensity = max(0, self._glow_intensity - dt * 2)
    
    def on_impact(self, intensity: float):
        """Called when payload hits something."""
        # Calculate squash based on impact
        self.squash = max(SQUASH_MIN, 1.0 - intensity / 2000)
        self._target_squash = 1.0
        self._glow_intensity = min(1.0, intensity / 500)
    
    def reset(self):
        """Reset to initial state."""
        self.rotation = 0.0
        self.squash = 1.0
        self._target_squash = 1.0
        self._glow_intensity = 0.0
    
    def draw(self, renderer: Renderer, pos: Tuple[int, int], radius: int):
        """Draw the payload with all effects."""
        screen = renderer.screen
        
        # Apply squash
        width = radius
        height = int(radius * self.squash)
        
        # Shadow
        shadow_offset = 4
        shadow_surf = pygame.Surface((width * 2 + 10, height * 2 + 10), pygame.SRCALPHA)
        shadow_rect = pygame.Rect(5, 5, width * 2, height * 2)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 60), shadow_rect)
        screen.blit(shadow_surf, (pos[0] - width - 5, pos[1] - height - 5 + shadow_offset))
        
        # Glow effect
        glow_alpha = int(40 + 30 * self._glow_intensity)
        renderer.draw_glow(COLOR_PAYLOAD_HIGHLIGHT, pos, radius + 5, 
                          intensity=3, alpha_base=glow_alpha)
        
        if abs(self.squash - 1.0) > 0.05:
            # Squashed ellipse
            rect = pygame.Rect(pos[0] - width, pos[1] - height, width * 2, height * 2)
            pygame.draw.ellipse(screen, COLOR_PAYLOAD, rect)
            pygame.draw.ellipse(screen, COLOR_PAYLOAD_SHADOW, rect, 3)
        else:
            # Normal circle with gradient
            renderer.draw_gradient_circle(COLOR_PAYLOAD_HIGHLIGHT, COLOR_PAYLOAD, 
                                         pos, radius)
            pygame.draw.circle(screen, COLOR_PAYLOAD_SHADOW, pos, radius, 3)
            
            # Rotation indicator (stripe)
            angle = self.rotation
            end_x = pos[0] + math.cos(angle) * radius * 0.7
            end_y = pos[1] + math.sin(angle) * radius * 0.7
            pygame.draw.line(screen, COLOR_PAYLOAD_SHADOW, pos, 
                           (int(end_x), int(end_y)), 3)
            
            # Shine highlight that rotates
            highlight_angle = angle + math.pi * 0.75
            highlight_pos = (
                int(pos[0] + math.cos(highlight_angle) * radius * 0.4),
                int(pos[1] + math.sin(highlight_angle) * radius * 0.4)
            )
            pygame.draw.circle(screen, COLOR_PAYLOAD_HIGHLIGHT, highlight_pos, 
                             radius // 3)


class Target:
    """The target box where the payload needs to land."""
    
    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        
        # Animation state
        self._glow_pulse = 0.0
        self._fill_progress = 0.0
        self._target_fill = 0.0
    
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
    
    def update(self, dt: float, has_payload: bool, settle_progress: float):
        """Update animation state."""
        self._glow_pulse += dt * GLOW_PULSE_SPEED * 60
        
        # Smooth fill progress
        self._target_fill = settle_progress if has_payload else 0.0
        fill_speed = 3.0 if self._fill_progress < self._target_fill else 5.0
        
        if self._fill_progress < self._target_fill:
            self._fill_progress = min(self._target_fill, 
                                     self._fill_progress + dt * fill_speed)
        else:
            self._fill_progress = max(self._target_fill, 
                                     self._fill_progress - dt * fill_speed)
    
    def draw(self, renderer: Renderer, has_payload: bool):
        """Draw the target with effects."""
        screen = renderer.screen
        rect = self.rect
        
        # Calculate glow
        glow_intensity = (math.sin(self._glow_pulse) + 1) / 2
        
        # Color based on state
        if self._fill_progress > 0:
            progress = self._fill_progress
            color = (
                int(COLOR_TARGET[0] + (COLOR_TARGET_GLOW[0] - COLOR_TARGET[0]) * progress),
                int(COLOR_TARGET[1] + (COLOR_TARGET_GLOW[1] - COLOR_TARGET[1]) * progress),
                int(COLOR_TARGET[2] + (COLOR_TARGET_GLOW[2] - COLOR_TARGET[2]) * progress)
            )
            
            # Progress glow
            glow_size = int(25 * progress)
            for i in range(glow_size, 0, -3):
                alpha = int(100 * progress * (1 - i / glow_size))
                surf = pygame.Surface((rect.width + i*2, rect.height + i*2), pygame.SRCALPHA)
                pygame.draw.rect(surf, (*COLOR_TARGET_GLOW, alpha), 
                               surf.get_rect(), border_radius=12)
                screen.blit(surf, (rect.x - i, rect.y - i))
        elif has_payload:
            color = COLOR_TARGET_GLOW
        else:
            color = COLOR_TARGET
            
            # Subtle pulse glow when waiting
            glow_size = int(10 * glow_intensity + 5)
            for i in range(glow_size, 0, -3):
                alpha = int(50 * glow_intensity * (1 - i / glow_size))
                surf = pygame.Surface((rect.width + i*2, rect.height + i*2), pygame.SRCALPHA)
                pygame.draw.rect(surf, (*COLOR_TARGET_GLOW, alpha), 
                               surf.get_rect(), border_radius=12)
                screen.blit(surf, (rect.x - i, rect.y - i))
        
        # Three walls (open top box)
        wall_width = 5
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
        """Draw anchor with glow and gradient."""
        pos = self.pygame_pos
        
        # Outer glow
        renderer.draw_glow(COLOR_ANCHOR_GLOW, pos, 10, intensity=2, alpha_base=30)
        
        # Main body with gradient
        renderer.draw_gradient_circle(COLOR_ANCHOR, COLOR_ANCHOR_CORE, pos, 10)
        
        # Ring
        pygame.draw.circle(renderer.screen, COLOR_ANCHOR_RING, pos, 10, 2)
        
        # Highlight
        highlight_pos = (pos[0] - 3, pos[1] - 3)
        pygame.draw.circle(renderer.screen, COLOR_ANCHOR_GLOW, highlight_pos, 3)
        
        # Draw letter label if assigned
        if self.letter:
            # Background circle for letter
            label_radius = 12
            label_pos = (pos[0], pos[1] - 20)
            pygame.draw.circle(renderer.screen, (50, 50, 50), label_pos, label_radius)
            pygame.draw.circle(renderer.screen, (200, 200, 200), label_pos, label_radius, 2)
            
            # Draw letter
            font = pygame.font.Font(None, 20)
            text_surf = font.render(self.letter, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=label_pos)
            renderer.screen.blit(text_surf, text_rect)


class Platform:
    """Visual platform with 3D effect."""
    
    def __init__(self, x: float, y: float, w: float, h: float):
        self.rect = pygame.Rect(x, PYMUNK_HEIGHT - y - h, w, h)
    
    def draw(self, renderer: Renderer):
        """Draw platform with shadow and gradient."""
        # Shadow
        renderer.draw_soft_shadow(self.rect, offset=4, blur=2, alpha=50)
        
        # Gradient fill with rounded corners
        renderer.draw_gradient_rect(COLOR_PLATFORM_TOP, COLOR_PLATFORM, self.rect, 
                                   border_radius=6)
        
        # Border
        pygame.draw.rect(renderer.screen, COLOR_PLATFORM_HIGHLIGHT, 
                        self.rect, width=2, border_radius=6)


class Spike:
    """Deadly spike obstacle."""
    
    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.rect = pygame.Rect(x, PYMUNK_HEIGHT - y - h, w, h)
    
    def draw(self, renderer: Renderer):
        """Draw spikes with triangles."""
        screen = renderer.screen
        
        # Shadow
        renderer.draw_soft_shadow(self.rect, offset=3, blur=2, alpha=40)
        
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
            
            # Edge highlight
            pygame.draw.polygon(screen, COLOR_SPIKE_DARK, points, width=2)
            
            # Tip highlight
            tip_pos = (int(x + actual_width / 2), self.rect.bottom - 2)
            pygame.draw.circle(screen, COLOR_SPIKE_TIP, tip_pos, 2)
