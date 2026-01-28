"""
Professional rendering utilities with smooth animations and effects.
"""

import math
from typing import Tuple, List, Optional
import pygame

from .config import *
from .utils import lerp_color, ease_out_quad


class Renderer:
    """Handles all advanced rendering with caching for performance."""
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self._gradient_cache = {}
        self._glow_cache = {}
    
    def clear_cache(self):
        """Clear rendering caches."""
        self._gradient_cache.clear()
        self._glow_cache.clear()
    
    def draw_gradient_rect(self, color_top: Tuple, color_bottom: Tuple, 
                           rect: pygame.Rect, vertical: bool = True, 
                           border_radius: int = 0):
        """Draw a rectangle with smooth gradient and optional rounded corners."""
        # Create a surface for the gradient
        surf = pygame.Surface((rect.width, max(1, rect.height)), pygame.SRCALPHA)
        
        if vertical:
            for i in range(rect.height):
                t = i / max(1, rect.height - 1)
                color = lerp_color(color_top, color_bottom, t)
                pygame.draw.line(surf, color, (0, i), (rect.width, i))
        else:
            for i in range(rect.width):
                t = i / max(1, rect.width - 1)
                color = lerp_color(color_top, color_bottom, t)
                pygame.draw.line(surf, color, (i, 0), (i, rect.height))
        
        # If rounded corners, create a mask
        if border_radius > 0:
            # Create a mask surface with rounded rectangle
            mask_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(mask_surf, (255, 255, 255, 255), 
                           mask_surf.get_rect(), border_radius=border_radius)
            
            # Apply mask to gradient
            final_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            final_surf.blit(surf, (0, 0))
            final_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            
            self.screen.blit(final_surf, rect.topleft)
        else:
            self.screen.blit(surf, rect.topleft)
    
    def draw_gradient_circle(self, center_color: Tuple, edge_color: Tuple, 
                             pos: Tuple[int, int], radius: int):
        """Draw a circle with radial gradient for 3D effect."""
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        
        for i in range(radius, 0, -1):
            t = 1 - (i / radius)  # 0 at edge, 1 at center
            t = ease_out_quad(t)  # Smooth falloff
            color = lerp_color(edge_color, center_color, t)
            pygame.draw.circle(surf, color, (radius, radius), i)
        
        self.screen.blit(surf, (pos[0] - radius, pos[1] - radius))
    
    def draw_glow(self, color: Tuple, pos: Tuple[int, int], radius: int, 
                  intensity: int = 3, alpha_base: int = 40):
        """Draw a soft glow effect around a point."""
        for i in range(intensity, 0, -1):
            alpha = alpha_base * (intensity - i + 1) // intensity
            glow_radius = radius + i * 4
            
            surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*color[:3], alpha), 
                             (glow_radius, glow_radius), glow_radius)
            self.screen.blit(surf, (pos[0] - glow_radius, pos[1] - glow_radius))
    
    def draw_soft_shadow(self, rect: pygame.Rect, offset: int = 4, 
                         blur: int = 3, alpha: int = 60):
        """Draw a soft shadow under an object."""
        shadow_surf = pygame.Surface((rect.width + blur * 2, rect.height + blur * 2), 
                                     pygame.SRCALPHA)
        shadow_rect = pygame.Rect(blur, blur, rect.width, rect.height)
        
        # Multiple layers for soft shadow
        for i in range(blur, 0, -1):
            layer_alpha = alpha // blur
            expanded = shadow_rect.inflate(i * 2, i * 2)
            pygame.draw.rect(shadow_surf, (0, 0, 0, layer_alpha), expanded, 
                           border_radius=8)
        
        self.screen.blit(shadow_surf, 
                        (rect.x - blur + offset, rect.y - blur + offset))
    
    def draw_text_with_shadow(self, text: str, font: pygame.font.Font,
                              pos: Tuple[int, int], color: Tuple = COLOR_TEXT,
                              shadow_color: Tuple = COLOR_TEXT_SHADOW,
                              shadow_offset: int = 2):
        """Draw text with a drop shadow for better readability."""
        shadow_surf = font.render(text, True, shadow_color)
        text_surf = font.render(text, True, color)
        
        self.screen.blit(shadow_surf, (pos[0] + shadow_offset, pos[1] + shadow_offset))
        self.screen.blit(text_surf, pos)
    
    def draw_text_centered(self, text: str, font: pygame.font.Font,
                           center: Tuple[int, int], color: Tuple = COLOR_TEXT,
                           shadow: bool = True):
        """Draw text centered at a position."""
        text_surf = font.render(text, True, color)
        rect = text_surf.get_rect(center=center)
        
        if shadow:
            shadow_surf = font.render(text, True, COLOR_TEXT_SHADOW)
            self.screen.blit(shadow_surf, (rect.x + 2, rect.y + 2))
        
        self.screen.blit(text_surf, rect)
    
    def draw_panel(self, rect: pygame.Rect, alpha: int = 220, 
                   border_radius: int = 12):
        """Draw a semi-transparent UI panel."""
        panel_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        
        # Background
        bg_color = (*COLOR_BG[:3], alpha)
        pygame.draw.rect(panel_surf, bg_color, panel_surf.get_rect(), 
                        border_radius=border_radius)
        
        # Border
        border_color = (*COLOR_PANEL_BORDER[:3], alpha // 2)
        pygame.draw.rect(panel_surf, border_color, panel_surf.get_rect(), 
                        width=2, border_radius=border_radius)
        
        self.screen.blit(panel_surf, rect.topleft)
    
    def draw_progress_bar(self, rect: pygame.Rect, progress: float,
                          bg_color: Tuple = (40, 45, 65),
                          fill_color_start: Tuple = COLOR_TARGET_GLOW,
                          fill_color_end: Tuple = COLOR_TARGET,
                          border_radius: int = 10):
        """Draw an animated progress bar with gradient fill and proper rounded corners."""
        # Shadow
        shadow_rect = rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(self.screen, (20, 20, 30), shadow_rect, 
                        border_radius=border_radius)
        
        # Background with rounded corners
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=border_radius)
        
        # Fill with gradient and proper clipping
        if progress > 0:
            fill_width = int(rect.width * min(1.0, progress))
            if fill_width > 0:
                # Create fill surface
                fill_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                
                # Draw gradient on fill surface
                for i in range(fill_width):
                    t = i / max(1, rect.width - 1)
                    color = lerp_color(fill_color_start, fill_color_end, t)
                    pygame.draw.line(fill_surf, color, (i, 0), (i, rect.height))
                
                # Create mask for rounded corners
                mask_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                pygame.draw.rect(mask_surf, (255, 255, 255, 255), 
                               mask_surf.get_rect(), border_radius=border_radius)
                
                # Apply mask
                fill_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                
                # Draw to screen
                self.screen.blit(fill_surf, rect.topleft)
        
        # Border with rounded corners
        pygame.draw.rect(self.screen, fill_color_start, rect, 
                        width=2, border_radius=border_radius)
    
    def draw_button_3d(self, rect: pygame.Rect, text: str, font: pygame.font.Font,
                       color_top: Tuple = COLOR_PLATFORM_HIGHLIGHT,
                       color_bottom: Tuple = COLOR_PLATFORM,
                       pressed: bool = False,
                       border_radius: int = 10):
        """Draw a 3D-style button with proper rounded corners."""
        offset = 1 if pressed else 3
        
        # Shadow
        shadow_rect = rect.copy()
        shadow_rect.y += offset
        pygame.draw.rect(self.screen, (30, 35, 50), shadow_rect, border_radius=border_radius)
        
        # Button face with gradient and rounded corners
        button_rect = rect if pressed else rect
        self.draw_gradient_rect(color_top, color_bottom, button_rect, border_radius=border_radius)
        pygame.draw.rect(self.screen, COLOR_ANCHOR_GLOW, button_rect, 
                        width=2, border_radius=border_radius)
        
        # Text
        self.draw_text_centered(text, font, button_rect.center)


class ParticleSystem:
    """Manages particle effects for impacts, cuts, and celebrations."""
    
    def __init__(self):
        self.particles: List[dict] = []
    
    def emit(self, pos: Tuple[float, float], count: int = 5,
             color: Tuple = COLOR_PARTICLE_BOUNCE, 
             speed_range: Tuple[float, float] = (30, 80),
             size_range: Tuple[float, float] = (2, 5),
             life: float = 1.0, gravity: float = PARTICLE_GRAVITY):
        """Emit particles from a position."""
        import random
        
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(*speed_range)
            
            self.particles.append({
                'x': pos[0],
                'y': pos[1],
                'vx': speed * math.cos(angle),
                'vy': speed * math.sin(angle),
                'life': life,
                'max_life': life,
                'size': random.uniform(*size_range),
                'color': color,
                'gravity': gravity
            })
    
    def emit_burst(self, pos: Tuple[float, float], count: int = 20,
                   color: Tuple = COLOR_PARTICLE_SUCCESS):
        """Emit a burst of celebration particles."""
        import random
        
        for i in range(count):
            angle = (2 * math.pi * i / count) + random.uniform(-0.2, 0.2)
            speed = random.uniform(100, 200)
            
            self.particles.append({
                'x': pos[0],
                'y': pos[1],
                'vx': speed * math.cos(angle),
                'vy': speed * math.sin(angle),
                'life': random.uniform(0.8, 1.5),
                'max_life': 1.5,
                'size': random.uniform(3, 6),
                'color': color,
                'gravity': PARTICLE_GRAVITY * 0.5
            })
    
    def update(self, dt: float):
        """Update all particles."""
        for particle in self.particles[:]:
            particle['life'] -= dt * PARTICLE_FADE_SPEED
            particle['x'] += particle['vx'] * dt
            particle['y'] -= particle['vy'] * dt  # Pymunk coords
            particle['vy'] -= particle['gravity'] * dt
            
            # Shrink as it dies
            life_ratio = particle['life'] / particle['max_life']
            particle['current_size'] = particle['size'] * life_ratio
            
            if particle['life'] <= 0:
                self.particles.remove(particle)
    
    def draw(self, renderer: Renderer, convert_coords=None):
        """Draw all particles."""
        for particle in self.particles:
            if convert_coords:
                pos = convert_coords((particle['x'], particle['y']))
            else:
                pos = (int(particle['x']), int(particle['y']))
            
            life_ratio = max(0, particle['life'] / particle['max_life'])
            alpha = int(255 * life_ratio)
            size = max(1, int(particle.get('current_size', particle['size'])))
            
            if alpha > 0 and size > 0:
                color = particle['color']
                
                # Draw glow
                glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*color[:3], alpha // 3), 
                                 (size * 2, size * 2), size * 2)
                renderer.screen.blit(glow_surf, (pos[0] - size * 2, pos[1] - size * 2))
                
                # Draw particle
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*color[:3], alpha), (size, size), size)
                renderer.screen.blit(surf, (pos[0] - size, pos[1] - size))
    
    def clear(self):
        """Remove all particles."""
        self.particles.clear()


class StarField:
    """Animated twinkling star background."""
    
    def __init__(self, count: int = STAR_COUNT):
        import random
        self.stars = []
        
        for _ in range(count):
            self.stars.append({
                'x': random.randint(0, WIDTH),
                'y': random.randint(0, HEIGHT),
                'size': random.uniform(1, 3),
                'speed': random.uniform(0.5, 2.0),
                'offset': random.uniform(0, math.pi * 2)
            })
    
    def draw(self, screen: pygame.Surface, time: float):
        """Draw twinkling stars."""
        for star in self.stars:
            twinkle = (math.sin(time * star['speed'] + star['offset']) + 1) / 2
            twinkle = twinkle * 0.5 + 0.5  # Range: 0.5 to 1.0
            
            alpha = int(200 * twinkle)
            size = max(1, int(star['size'] * twinkle))
            
            surf = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
            
            # Star glow
            pygame.draw.circle(surf, (255, 255, 255, alpha // 3), 
                             (size + 1, size + 1), size + 1)
            # Star core
            pygame.draw.circle(surf, (255, 255, 255, alpha), 
                             (size + 1, size + 1), size)
            
            screen.blit(surf, (star['x'] - size - 1, star['y'] - size - 1))
