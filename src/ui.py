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
    """Simple title screen."""
    
    def __init__(self, renderer: Renderer, fonts: FontManager, star_field: StarField):
        self.renderer = renderer
        self.fonts = fonts
        self.star_field = star_field
        self._time = 0.0
    
    def update(self, dt: float):
        self._time += dt
    
    def draw(self):
        screen = self.renderer.screen
        
        # Simple background
        screen.fill(COLOR_BG)
        
        # Title
        title_text = "Cut The Rope"
        title_surf = self.fonts.large.render(title_text, True, COLOR_TEXT)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        screen.blit(title_surf, title_rect)
        
        # Subtitle
        subtitle_text = "Click to Start"
        subtitle_surf = self.fonts.normal.render(subtitle_text, True, COLOR_TEXT)
        subtitle_rect = subtitle_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
        screen.blit(subtitle_surf, subtitle_rect)


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
    def draw(self):
        screen = self.renderer.screen
        
        # Simple background
        screen.fill(COLOR_BG)
        
        # Title
        title_surf = self.fonts.large.render("Select Level", True, COLOR_TEXT)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 80))
        screen.blit(title_surf, title_rect)
        
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
            
            is_hovered = (i == self._hovered_level)
            
            # Button background
            color = COLOR_PLATFORM if not is_hovered else COLOR_PLATFORM_HIGHLIGHT
            pygame.draw.rect(screen, color, rect)
            
            # Border
            border_color = COLOR_ANCHOR_GLOW if is_hovered else (100, 100, 120)
            pygame.draw.rect(screen, border_color, rect, width=2)
            
            # Level number
            text_surf = self.fonts.normal.render(str(i + 1), True, COLOR_TEXT)
            text_rect = text_surf.get_rect(center=rect.center)
            screen.blit(text_surf, text_rect)
        
        # Instructions
        inst_surf = self.fonts.small.render("Click a level or press 1-6", True, (120, 130, 150))
        inst_rect = inst_surf.get_rect(center=(WIDTH // 2, HEIGHT - 50))
        screen.blit(inst_surf, inst_rect)


class WinScreen:
    """Simple victory screen."""
    
    def __init__(self, renderer: Renderer, fonts: FontManager, star_field: StarField):
        self.renderer = renderer
        self.fonts = fonts
        self.star_field = star_field
        self._time = 0.0
    
    def update(self, dt: float):
        self._time += dt
    
    def draw(self, level_num: int):
        screen = self.renderer.screen
        
        # Simple background
        screen.fill(COLOR_BG)
        
        # Title
        title_text = "Level Complete!"
        title_surf = self.fonts.large.render(title_text, True, COLOR_TARGET_GLOW)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        screen.blit(title_surf, title_rect)
        
        # Level info
        level_text = f"Level {level_num + 1} Completed"
        level_surf = self.fonts.normal.render(level_text, True, COLOR_TEXT)
        level_rect = level_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
        screen.blit(level_surf, level_rect)
        
        # Continue prompt
        continue_text = "Click to continue"
        continue_surf = self.fonts.normal.render(continue_text, True, COLOR_TEXT)
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
        level_surf = self.fonts.normal.render(f"Level {level_num + 1}", True, COLOR_TEXT)
        screen.blit(level_surf, (20, 20))
        
        # Rope count
        rope_surf = self.fonts.small.render(f"Ropes: {rope_count}", True, COLOR_TEXT)
        screen.blit(rope_surf, (20, 55))
        
        # Status
        status = "IN TARGET" if in_target else "Outside"
        status_color = COLOR_TARGET_GLOW if in_target else (120, 130, 150)
        status_surf = self.fonts.small.render(f"Status: {status}", True, status_color)
        screen.blit(status_surf, (20, 80))
        
        # Progress bar when settling
        if in_target and settle_timer > 0:
            progress = min(1.0, settle_timer / settle_time)
            bar_width = 200
            bar_height = 20
            bar_x = WIDTH // 2 - bar_width // 2
            bar_y = 50
            
            # Background
            pygame.draw.rect(screen, (40, 45, 65), (bar_x, bar_y, bar_width, bar_height))
            
            # Fill
            fill_width = int(bar_width * progress)
            pygame.draw.rect(screen, COLOR_TARGET_GLOW, (bar_x, bar_y, fill_width, bar_height))
            
            # Border
            pygame.draw.rect(screen, COLOR_TARGET_GLOW, (bar_x, bar_y, bar_width, bar_height), 2)
            
            # Timer text
            timer_text = f"{settle_timer:.1f}s / {settle_time:.1f}s"
            timer_surf = self.fonts.small.render(timer_text, True, COLOR_TEXT)
            timer_rect = timer_surf.get_rect(center=(WIDTH // 2, bar_y + bar_height + 15))
            screen.blit(timer_surf, timer_rect)
        
        # Instructions panel
        if self.show_instructions:
            self._draw_instructions()
    
    def _draw_instructions(self):
        """Draw the instructions panel."""
        instructions = [
            "Press A, B, C... to cut ropes",
            "Get candy into the target",
            f"Stay for {TARGET_SETTLE_TIME:.0f} seconds to win",
            "",
            "R - Restart | I - Toggle Help | Esc - Menu"
        ]
        
        # Panel
        panel_width = 380
        panel_height = len(instructions) * 24 + 20
        panel_x = 10
        panel_y = HEIGHT - panel_height - 10
        
        # Background
        pygame.draw.rect(self.renderer.screen, (20, 25, 35, 220), 
                        (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.renderer.screen, (60, 70, 90), 
                        (panel_x, panel_y, panel_width, panel_height), 2)
        
        # Text
        y = panel_y + 10
        for line in instructions:
            if line:
                text_surf = self.fonts.small.render(line, True, COLOR_TEXT)
                self.renderer.screen.blit(text_surf, (panel_x + 15, y))
            y += 24
    
    def toggle_instructions(self):
        """Toggle instructions visibility."""
        self.show_instructions = not self.show_instructions
