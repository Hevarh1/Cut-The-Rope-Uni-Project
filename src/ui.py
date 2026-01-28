"""
UI screens: Title, Level Select, Win, and HUD.
"""

import math
import time
from typing import List, Tuple, Callable
import pygame

from .config import *
from .renderer import Renderer, StarField


class FontManager:
    """Manages game fonts."""
    
    def __init__(self):
        self.small = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_SMALL)
        self.normal = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_NORMAL)
        self.large = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_LARGE)
        self.huge = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_HUGE)


class TitleScreen:
    """Animated title screen."""
    
    def __init__(self, renderer: Renderer, fonts: FontManager, star_field: StarField):
        self.renderer = renderer
        self.fonts = fonts
        self.star_field = star_field
        self._time = 0.0
    
    def update(self, dt: float):
        self._time += dt
    
    def draw(self):
        screen = self.renderer.screen
        current_time = time.time()
        
        # Background gradient
        self.renderer.draw_gradient_rect(COLOR_BG_GRADIENT_TOP, COLOR_BG_GRADIENT_BOTTOM,
                                        pygame.Rect(0, 0, WIDTH, HEIGHT))
        
        # Stars
        self.star_field.draw(screen, current_time)
        
        # Title with glow
        title_text = "Payload Drop"
        title_surf = self.fonts.large.render(title_text, True, COLOR_TEXT)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        
        # Animated glow
        glow_intensity = (math.sin(current_time * 1.5) + 1) / 2 * 0.5 + 0.5
        for i in range(6, 0, -1):
            alpha = int(50 * glow_intensity / i)
            glow_surf = self.fonts.large.render(title_text, True, (*COLOR_TARGET_GLOW[:3], alpha))
            offset = i * 1.5
            screen.blit(glow_surf, (title_rect.x + offset, title_rect.y + offset))
        
        # Shadow and text
        shadow_surf = self.fonts.large.render(title_text, True, COLOR_TEXT_SHADOW)
        screen.blit(shadow_surf, (title_rect.x + 3, title_rect.y + 3))
        screen.blit(title_surf, title_rect)
        
        # Subtitle with pulse
        pulse = (math.sin(current_time * 2.5) + 1) / 2
        alpha = int(180 * pulse + 75)
        subtitle_text = "Click to Start"
        subtitle_surf = self.fonts.normal.render(subtitle_text, True, COLOR_TEXT)
        subtitle_surf.set_alpha(alpha)
        subtitle_rect = subtitle_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
        screen.blit(subtitle_surf, subtitle_rect)
        
        # Version
        version_text = "v1.0"
        version_surf = self.fonts.small.render(version_text, True, (100, 110, 130))
        screen.blit(version_surf, (WIDTH - 60, HEIGHT - 30))


class LevelSelectScreen:
    """Level selection screen with animated buttons."""
    
    def __init__(self, renderer: Renderer, fonts: FontManager, 
                 level_count: int, star_field: StarField):
        self.renderer = renderer
        self.fonts = fonts
        self.level_count = level_count
        self.star_field = star_field
        
        self._hovered_level = -1
        self._button_rects: List[pygame.Rect] = []
        self._time = 0.0
    
    def update(self, dt: float, mouse_pos: Tuple[int, int]):
        self._time += dt
        
        # Check hover
        self._hovered_level = -1
        for i, rect in enumerate(self._button_rects):
            if rect.collidepoint(mouse_pos):
                self._hovered_level = i
                break
    
    def get_clicked_level(self, mouse_pos: Tuple[int, int]) -> int:
        """Return level index if a level was clicked, -1 otherwise."""
        for i, rect in enumerate(self._button_rects):
            if rect.collidepoint(mouse_pos):
                return i
        return -1
    
    def draw(self):
        screen = self.renderer.screen
        current_time = time.time()
        
        # Background
        self.renderer.draw_gradient_rect(COLOR_BG_GRADIENT_TOP, COLOR_BG_GRADIENT_BOTTOM,
                                        pygame.Rect(0, 0, WIDTH, HEIGHT))
        
        # Stars (dimmer)
        for star in self.star_field.stars:
            twinkle = (math.sin(current_time * star['speed'] + star['offset']) + 1) / 2
            alpha = int(100 * twinkle)
            size = max(1, int(star['size'] * 0.8))
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 255, 255, alpha), (size, size), size)
            screen.blit(surf, (star['x'] - size, star['y'] - size))
        
        # Title
        self.renderer.draw_text_centered("Select Level", self.fonts.large, 
                                        (WIDTH // 2, 80))
        
        # Level buttons
        margin_x = 200
        margin_y = 180
        cols = 4
        button_size = 80
        gap = 30
        
        self._button_rects.clear()
        
        for i in range(self.level_count):
            row = i // cols
            col = i % cols
            
            x = margin_x + col * (button_size + gap)
            y = margin_y + row * (button_size + gap)
            rect = pygame.Rect(x, y, button_size, button_size)
            self._button_rects.append(rect)
            
            # Animation for hovered button
            is_hovered = (i == self._hovered_level)
            scale = 1.1 if is_hovered else 1.0
            
            if is_hovered:
                # Expand rect
                expand = int((scale - 1) * button_size / 2)
                rect = rect.inflate(expand * 2, expand * 2)
            
            # Shadow
            shadow_offset = 2 if is_hovered else 4
            shadow_rect = rect.copy()
            shadow_rect.y += shadow_offset
            pygame.draw.rect(screen, (25, 30, 45), shadow_rect, border_radius=12)
            
            # Button gradient with rounded corners
            color_top = COLOR_TARGET_GLOW if is_hovered else COLOR_PLATFORM_HIGHLIGHT
            color_bottom = COLOR_TARGET if is_hovered else COLOR_PLATFORM
            self.renderer.draw_gradient_rect(color_top, color_bottom, rect, 
                                            border_radius=12)
            
            # Border
            border_color = COLOR_TARGET_GLOW if is_hovered else COLOR_ANCHOR_GLOW
            pygame.draw.rect(screen, border_color, rect, width=2, border_radius=12)
            
            # Level number
            text_color = COLOR_TEXT if is_hovered else COLOR_TEXT
            self.renderer.draw_text_centered(str(i + 1), self.fonts.normal, 
                                            rect.center, text_color)
        
        # Instructions
        self.renderer.draw_text_centered("Click a level or press 1-6", 
                                        self.fonts.small, (WIDTH // 2, HEIGHT - 50),
                                        color=(120, 130, 150))


class WinScreen:
    """Victory celebration screen."""
    
    def __init__(self, renderer: Renderer, fonts: FontManager, star_field: StarField):
        self.renderer = renderer
        self.fonts = fonts
        self.star_field = star_field
        self._time = 0.0
    
    def update(self, dt: float):
        self._time += dt
    
    def draw(self, level_num: int):
        screen = self.renderer.screen
        current_time = time.time()
        
        # Background
        self.renderer.draw_gradient_rect(COLOR_BG_GRADIENT_TOP, COLOR_BG_GRADIENT_BOTTOM,
                                        pygame.Rect(0, 0, WIDTH, HEIGHT))
        
        # Celebration particles
        for i in range(80):
            offset = i * 0.15
            orbit_x = math.sin(current_time * 2 + offset) * (150 + i * 3)
            orbit_y = math.cos(current_time * 2.5 + offset) * (100 + i * 2)
            x = WIDTH // 2 + orbit_x
            y = HEIGHT // 2 + orbit_y
            
            size = int(3 + math.sin(current_time * 3 + offset) * 2)
            alpha = int(220 - i * 2.5)
            
            if alpha > 0 and 0 < x < WIDTH and 0 < y < HEIGHT:
                # Alternate colors
                if i % 3 == 0:
                    color = COLOR_PARTICLE_SUCCESS
                elif i % 3 == 1:
                    color = COLOR_TARGET_GLOW
                else:
                    color = COLOR_PARTICLE_STAR
                
                surf = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*color[:3], alpha), (size + 1, size + 1), size)
                screen.blit(surf, (int(x) - size - 1, int(y) - size - 1))
        
        # Title with rainbow glow
        title_text = "Level Complete!"
        title_surf = self.fonts.large.render(title_text, True, COLOR_TARGET_GLOW)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        
        # Animated glow
        for i in range(8, 0, -1):
            hue_shift = (current_time * 50 + i * 20) % 360
            glow_color = pygame.Color(0)
            glow_color.hsva = (hue_shift, 50, 100, 30 // i)
            glow_surf = self.fonts.large.render(title_text, True, glow_color)
            screen.blit(glow_surf, (title_rect.x + i, title_rect.y + i))
        
        # Shadow and text
        shadow_surf = self.fonts.large.render(title_text, True, COLOR_TEXT_SHADOW)
        screen.blit(shadow_surf, (title_rect.x + 3, title_rect.y + 3))
        screen.blit(title_surf, title_rect)
        
        # Level info
        level_text = f"Level {level_num + 1} Completed"
        self.renderer.draw_text_centered(level_text, self.fonts.normal,
                                        (WIDTH // 2, HEIGHT // 2 + 10),
                                        COLOR_TEXT)
        
        # Continue prompt
        pulse = (math.sin(current_time * 2) + 1) / 2
        alpha = int(150 * pulse + 100)
        continue_surf = self.fonts.normal.render("Click to continue", True, COLOR_TEXT)
        continue_surf.set_alpha(alpha)
        continue_rect = continue_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
        screen.blit(continue_surf, continue_rect)


class HUD:
    """In-game heads-up display."""
    
    def __init__(self, renderer: Renderer, fonts: FontManager):
        self.renderer = renderer
        self.fonts = fonts
        self.show_instructions = True
    
    def draw(self, level_num: int, rope_count: int, in_target: bool,
             settle_timer: float, settle_time: float, 
             velocity: float = 0, position: Tuple[float, float] = (0, 0)):
        """Draw the HUD elements."""
        screen = self.renderer.screen
        
        # Level indicator
        self.renderer.draw_text_with_shadow(f"Level {level_num + 1}", 
                                           self.fonts.normal, (20, 20))
        
        # Rope count
        self.renderer.draw_text_with_shadow(f"Ropes: {rope_count}",
                                           self.fonts.small, (20, 55))
        
        # Status
        status = "IN TARGET" if in_target else "Outside"
        status_color = COLOR_TARGET_GLOW if in_target else (120, 130, 150)
        self.renderer.draw_text_with_shadow(f"Status: {status}",
                                           self.fonts.small, (20, 80),
                                           color=status_color)
        
        # Progress bar when settling
        if in_target and settle_timer > 0:
            progress = min(1.0, settle_timer / settle_time)
            bar_width = 200
            bar_height = 20
            bar_rect = pygame.Rect(WIDTH // 2 - bar_width // 2, 50, 
                                  bar_width, bar_height)
            
            self.renderer.draw_progress_bar(bar_rect, progress)
            
            # Timer text
            timer_text = f"Settling... {settle_timer:.1f}s / {settle_time:.1f}s"
            self.renderer.draw_text_with_shadow(timer_text, self.fonts.small,
                                               (bar_rect.x, bar_rect.bottom + 8))
        
        # Instructions panel
        if self.show_instructions:
            self._draw_instructions()
    
    def _draw_instructions(self):
        """Draw the instructions panel."""
        instructions = [
            "Press A, B, C... to cut ropes",
            "Get payload into the target",
            f"Stay for {TARGET_SETTLE_TIME:.0f} seconds to win",
            "",
            "R - Restart | I - Toggle Help | Esc - Menu"
        ]
        
        # Panel
        panel_width = 380
        panel_height = len(instructions) * 24 + 20
        panel_rect = pygame.Rect(10, HEIGHT - panel_height - 10, 
                                panel_width, panel_height)
        
        self.renderer.draw_panel(panel_rect)
        
        # Text
        y = panel_rect.y + 10
        for line in instructions:
            if line:
                self.renderer.draw_text_with_shadow(line, self.fonts.small, 
                                                   (panel_rect.x + 15, y),
                                                   shadow_offset=1)
            y += 24
    
    def toggle_instructions(self):
        """Toggle instructions visibility."""
        self.show_instructions = not self.show_instructions
