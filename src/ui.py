"""
UI system for Cut The Rope.

Screens:
  - Title Screen (smooth animated)
  - Level Select (grid with progress)
  - Guide (covers ALL mechanics with visual examples)
  - Game HUD (integrated in game.py)
  - Win / Lose overlays (integrated in game.py)

All UI is drawn onto the 720x1280 virtual canvas and scaled.
"""

import math
import pygame

from .config import (
    WIDTH, HEIGHT, FPS, GAME_TITLE,
    FONT_FAMILY, FONT_SIZE_SMALL, FONT_SIZE_NORMAL, FONT_SIZE_LARGE, FONT_SIZE_HUGE,
    COLOR_TEXT, COLOR_TEXT_SHADOW, COLOR_TEXT_HIGHLIGHT,
    COLOR_BG, COLOR_BG_GRADIENT_TOP, COLOR_BG_GRADIENT_BOTTOM,
    COLOR_CANDY, COLOR_CANDY_HIGHLIGHT,
    COLOR_TARGET, COLOR_TARGET_GLOW,
    COLOR_ANCHOR, COLOR_ANCHOR_GLOW,
    COLOR_ROPE, COLOR_SPIKE, COLOR_SPIKE_GLOW,
    MAGNET_COLOR, SLIDER_COLOR, WINCH_COLOR,
    TELEPORT_COLOR_A, TELEPORT_COLOR_B,
    SPIDER_COLOR, SPIDER_COLOR_EYE,
    COLOR_PANEL_BG, COLOR_PANEL_BORDER,
    COLOR_PARTICLE_STAR,
)
from .utils import lerp, lerp_color, ease_out_quad, ease_in_out_quad, clamp
from .levels import total_levels
from .savedata import load_scores, get_best_time, load_custom_levels, delete_custom_level, get_star_count, get_total_stars
from .renderer import Renderer, StarField


# =====================================================================
#  Helpers
# =====================================================================

def _get_font(size, bold=False):
    try:
        return pygame.font.SysFont(FONT_FAMILY, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


def _draw_text(surface, text, font, color, x, y, anchor="topleft", shadow=True):
    """Draw text with optional shadow. Returns text rect."""
    txt = font.render(text, True, color)
    rect = txt.get_rect(**{anchor: (x, y)})
    if shadow:
        sh = font.render(text, True, COLOR_TEXT_SHADOW)
        surface.blit(sh, (rect.x + 1, rect.y + 2))
    surface.blit(txt, rect)
    return rect


def _draw_button(surface, text, font, x, y, w, h, hover=False, color=None):
    """Draw a smooth rounded button. Returns rect."""
    rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
    base_color = color or (60, 70, 100)
    if hover:
        base_color = tuple(min(255, c + 30) for c in base_color)

    # Shadow
    shadow_rect = rect.inflate(0, 0).move(2, 3)
    sr = pygame.Surface((shadow_rect.w, shadow_rect.h), pygame.SRCALPHA)
    pygame.draw.rect(sr, (0, 0, 0, 60), (0, 0, shadow_rect.w, shadow_rect.h),
                     border_radius=12)
    surface.blit(sr, shadow_rect.topleft)

    # Main
    btn = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(btn, (*base_color, 220), (0, 0, w, h), border_radius=12)
    # Border
    border_c = tuple(min(255, c + 40) for c in base_color)
    pygame.draw.rect(btn, (*border_c, 180), (0, 0, w, h), width=2, border_radius=12)
    surface.blit(btn, rect.topleft)

    # Text
    txt = font.render(text, True, COLOR_TEXT)
    tx = rect.centerx - txt.get_width() // 2
    ty = rect.centery - txt.get_height() // 2
    surface.blit(txt, (tx, ty))

    return rect


def _draw_gradient_bg(surface):
    for y in range(HEIGHT):
        t = y / HEIGHT
        c = lerp_color(COLOR_BG_GRADIENT_TOP, COLOR_BG_GRADIENT_BOTTOM, t)
        pygame.draw.line(surface, c, (0, y), (WIDTH, y))


def _draw_star_shape(surface, cx, cy, size, filled=True):
    """Draw a 5-pointed star centered at (cx, cy)."""
    points = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        r = size if i % 2 == 0 else size * 0.4
        points.append((cx + r * math.cos(angle), cy - r * math.sin(angle)))
    if filled:
        pygame.draw.polygon(surface, (255, 220, 50), points)
        pygame.draw.polygon(surface, (200, 170, 30), points, 2)
    else:
        pygame.draw.polygon(surface, (80, 80, 80), points)
        pygame.draw.polygon(surface, (120, 120, 120), points, 2)


# =====================================================================
#  Title Screen
# =====================================================================

class TitleScreen:
    def __init__(self):
        self._time = 0.0
        self._font_title = _get_font(FONT_SIZE_HUGE, bold=True)
        self._font_sub = _get_font(FONT_SIZE_NORMAL)
        self._font_btn = _get_font(FONT_SIZE_NORMAL, bold=True)
        self._stars = StarField(80)
        self._hover_play = False
        self._hover_guide = False
        self._hover_custom = False
        self._btn_play = None
        self._btn_guide = None
        self._btn_custom = None
        self._renderer = Renderer()

    def handle_event(self, event, scale, dest_rect):
        if event.type == pygame.MOUSEMOTION:
            vx, vy = self._renderer.window_to_virtual(event.pos, scale, dest_rect)
            self._hover_play = self._btn_play.collidepoint(vx, vy) if self._btn_play else False
            self._hover_guide = self._btn_guide.collidepoint(vx, vy) if self._btn_guide else False
            self._hover_custom = self._btn_custom.collidepoint(vx, vy) if self._btn_custom else False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            vx, vy = self._renderer.window_to_virtual(event.pos, scale, dest_rect)
            if self._btn_play and self._btn_play.collidepoint(vx, vy):
                return "level_select"
            if self._btn_guide and self._btn_guide.collidepoint(vx, vy):
                return "guide"
            if self._btn_custom and self._btn_custom.collidepoint(vx, vy):
                return "custom_levels"

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                return "level_select"
            if event.key == pygame.K_g:
                return "guide"
            if event.key == pygame.K_c:
                return "custom_levels"

        return None

    def update(self, dt):
        self._time += dt
        self._stars.update(dt)

    def draw(self, window_surface):
        surf = self._renderer.virtual_surface
        _draw_gradient_bg(surf)
        self._stars.draw(surf)

        t = self._time

        # Animated title
        y_bob = math.sin(t * 1.5) * 8
        title_y = 300 + y_bob

        # Title shadow
        _draw_text(surf, GAME_TITLE, self._font_title, COLOR_TEXT_SHADOW,
                   WIDTH // 2 + 2, int(title_y) + 3, anchor="midtop", shadow=False)
        _draw_text(surf, GAME_TITLE, self._font_title, COLOR_CANDY,
                   WIDTH // 2, int(title_y), anchor="midtop", shadow=False)

        # Subtitle
        sub_alpha = clamp((t - 0.5) * 2, 0, 1)
        if sub_alpha > 0:
            sub = self._font_sub.render("A Physics Puzzle Game", True,
                                        lerp_color(COLOR_BG, COLOR_TEXT, sub_alpha))
            surf.blit(sub, (WIDTH // 2 - sub.get_width() // 2, int(title_y) + 90))

        # Animated candy icon
        candy_y = int(title_y) - 60
        candy_x = WIDTH // 2
        pulse = 0.5 + 0.5 * math.sin(t * 3)
        r = 18 + int(pulse * 3)
        pygame.draw.circle(surf, COLOR_CANDY, (candy_x, candy_y), r)
        pygame.draw.circle(surf, COLOR_CANDY_HIGHLIGHT, (candy_x - 4, candy_y - 4), r // 3)

        # Buttons
        btn_y = 580
        self._btn_play = _draw_button(surf, "Play", self._font_btn,
                                      WIDTH // 2, btn_y, 260, 56,
                                      self._hover_play, (60, 140, 90))
        self._btn_custom = _draw_button(surf, "Custom Levels", self._font_btn,
                                        WIDTH // 2, btn_y + 76, 260, 56,
                                        self._hover_custom, (90, 80, 140))
        self._btn_guide = _draw_button(surf, "Guide", self._font_btn,
                                       WIDTH // 2, btn_y + 152, 260, 56,
                                       self._hover_guide, (80, 80, 140))

        # Footer
        _draw_text(surf, "ENTER = Play  |  C = Custom  |  G = Guide", self._font_sub,
                   (120, 130, 160), WIDTH // 2, HEIGHT - 60, anchor="midbottom")

        # Scale to window
        w, h = window_surface.get_size()
        scale, dest = self._renderer.get_scale_rect(w, h)
        window_surface.fill((0, 0, 0))
        scaled = pygame.transform.smoothscale(surf, (dest.width, dest.height))
        window_surface.blit(scaled, dest)
        return scale, dest


# =====================================================================
#  Level Select
# =====================================================================

class LevelSelect:
    def __init__(self):
        self._font_title = _get_font(FONT_SIZE_LARGE, bold=True)
        self._font_btn = _get_font(FONT_SIZE_NORMAL, bold=True)
        self._font_sm = _get_font(FONT_SIZE_SMALL)
        self._stars = StarField(50)
        self._time = 0.0
        self._hover_idx = -1
        self._btn_rects = []
        self._btn_back = None
        self._hover_back = False
        self._renderer = Renderer()

    def handle_event(self, event, scale, dest_rect):
        if event.type == pygame.MOUSEMOTION:
            vx, vy = self._renderer.window_to_virtual(event.pos, scale, dest_rect)
            self._hover_idx = -1
            for i, r in enumerate(self._btn_rects):
                if r.collidepoint(vx, vy):
                    self._hover_idx = i
                    break
            self._hover_back = self._btn_back.collidepoint(vx, vy) if self._btn_back else False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            vx, vy = self._renderer.window_to_virtual(event.pos, scale, dest_rect)
            for i, r in enumerate(self._btn_rects):
                if r.collidepoint(vx, vy):
                    return ("play", i)
            if self._btn_back and self._btn_back.collidepoint(vx, vy):
                return ("back",)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return ("back",)
            # Number keys 1-9 for quick select
            if pygame.K_1 <= event.key <= pygame.K_9:
                idx = event.key - pygame.K_1
                if idx < total_levels():
                    return ("play", idx)

        return None

    def update(self, dt):
        self._time += dt
        self._stars.update(dt)

    def draw(self, window_surface):
        surf = self._renderer.virtual_surface
        _draw_gradient_bg(surf)
        self._stars.draw(surf)

        # Total stars earned
        total_s = get_total_stars()
        max_s = total_levels() * 3
        _draw_text(surf, "Select Level", self._font_title, COLOR_TEXT,
                   WIDTH // 2, 60, anchor="midtop")
        star_txt = f"★ {total_s} / {max_s}"
        _draw_text(surf, star_txt, self._font_btn, (255, 220, 50),
                   WIDTH // 2, 120, anchor="midtop", shadow=False)

        scores = load_scores()
        n = total_levels()
        cols = 3
        btn_w = 180
        btn_h = 80
        gap_x = 20
        gap_y = 40
        start_x = WIDTH // 2 - (cols * btn_w + (cols - 1) * gap_x) // 2 + btn_w // 2
        start_y = 200

        self._btn_rects = []
        for i in range(n):
            col = i % cols
            row = i // cols
            bx = start_x + col * (btn_w + gap_x)
            by = start_y + row * (btn_h + gap_y)

            completed = str(i) in scores
            hover = (i == self._hover_idx)
            color = (50, 120, 80) if completed else (60, 70, 100)

            label = f"Level {i + 1}"
            rect = _draw_button(surf, label, self._font_btn,
                                bx, by, btn_w, btn_h, hover, color)
            self._btn_rects.append(rect)

            # Best time + stars
            bt = get_best_time(i)
            if bt is not None:
                ts = f"{bt:.1f}s"
                _draw_text(surf, ts, self._font_sm, (180, 220, 180),
                           bx, by + btn_h // 2 + 4, anchor="midtop", shadow=False)
                # Draw stars
                sc = get_star_count(i)
                star_sz = 10
                star_gap = 24
                sx_start = bx - star_gap
                for s in range(3):
                    _draw_star_shape(surf, sx_start + s * star_gap,
                                     by + btn_h // 2 + 28, star_sz, s < sc)

        # Back button
        self._btn_back = _draw_button(surf, "Back", self._font_btn,
                                      WIDTH // 2, HEIGHT - 100, 200, 50,
                                      self._hover_back, (100, 60, 60))

        _draw_text(surf, "ESC = Back  |  1-9 = Quick Select", self._font_sm,
                   (120, 130, 160), WIDTH // 2, HEIGHT - 40, anchor="midbottom")

        w, h = window_surface.get_size()
        scale, dest = self._renderer.get_scale_rect(w, h)
        window_surface.fill((0, 0, 0))
        scaled = pygame.transform.smoothscale(surf, (dest.width, dest.height))
        window_surface.blit(scaled, dest)
        return scale, dest


# =====================================================================
#  Guide Screen (covers ALL mechanics)
# =====================================================================

class GuideScreen:
    def __init__(self):
        self._font_title = _get_font(FONT_SIZE_LARGE, bold=True)
        self._font_heading = _get_font(FONT_SIZE_NORMAL, bold=True)
        self._font_body = _get_font(FONT_SIZE_SMALL)
        self._font_btn = _get_font(FONT_SIZE_NORMAL, bold=True)
        self._stars = StarField(40)
        self._time = 0.0
        self._scroll_y = 0
        self._max_scroll = 2200
        self._btn_back = None
        self._hover_back = False
        self._renderer = Renderer()

    def handle_event(self, event, scale, dest_rect):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # scroll up
                self._scroll_y = max(0, self._scroll_y - 60)
            elif event.button == 5:  # scroll down
                self._scroll_y = min(self._max_scroll, self._scroll_y + 60)
            elif event.button == 1:
                vx, vy = self._renderer.window_to_virtual(event.pos, scale, dest_rect)
                if self._btn_back and self._btn_back.collidepoint(vx, vy):
                    return "back"

        if event.type == pygame.MOUSEMOTION:
            vx, vy = self._renderer.window_to_virtual(event.pos, scale, dest_rect)
            self._hover_back = self._btn_back.collidepoint(vx, vy) if self._btn_back else False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back"
            if event.key == pygame.K_UP:
                self._scroll_y = max(0, self._scroll_y - 80)
            if event.key == pygame.K_DOWN:
                self._scroll_y = min(self._max_scroll, self._scroll_y + 80)

        return None

    def update(self, dt):
        self._time += dt
        self._stars.update(dt)

    def draw(self, window_surface):
        surf = self._renderer.virtual_surface
        _draw_gradient_bg(surf)
        self._stars.draw(surf)

        # Scrollable content surface
        content_h = 2400
        content = pygame.Surface((WIDTH, content_h), pygame.SRCALPHA)

        y = 20
        y = self._section_title(content, y, "How To Play")
        y = self._text(content, y, "Deliver the candy to Om Nom by cutting ropes")
        y = self._text(content, y, "and using various mechanics!")
        y += 20

        # -- Rope Types --
        y = self._section_heading(content, y, "Rope Types")
        y = self._draw_rope_guide(content, y)
        y += 10

        # -- Anchors --
        y = self._section_heading(content, y, "Anchor Types")
        y = self._draw_anchor_guide(content, y)
        y += 10

        # -- Teleportation --
        y = self._section_heading(content, y, "Teleportation (Magic Hats)")
        y = self._draw_teleport_guide(content, y)
        y += 10

        # -- Spiders --
        y = self._section_heading(content, y, "Spiders")
        y = self._draw_spider_guide(content, y)
        y += 10

        # -- Spikes --
        y = self._section_heading(content, y, "Spikes")
        y = self._draw_spike_guide(content, y)
        y += 10

        # -- Controls --
        y = self._section_heading(content, y, "Controls")
        y = self._draw_controls_guide(content, y)

        self._max_scroll = max(0, y - HEIGHT + 150)

        # Blit scrolled content
        src_rect = pygame.Rect(0, self._scroll_y, WIDTH, HEIGHT - 80)
        surf.blit(content, (0, 0), src_rect)

        # Scroll indicator
        if self._max_scroll > 0:
            frac = self._scroll_y / self._max_scroll
            bar_h = max(30, int((HEIGHT - 80) * (HEIGHT - 80) / content_h))
            bar_y = int(frac * (HEIGHT - 80 - bar_h))
            bar_surf = pygame.Surface((6, bar_h), pygame.SRCALPHA)
            pygame.draw.rect(bar_surf, (255, 255, 255, 80), (0, 0, 6, bar_h), border_radius=3)
            surf.blit(bar_surf, (WIDTH - 12, bar_y))

        # Back button (fixed at bottom)
        self._btn_back = _draw_button(surf, "Back", self._font_btn,
                                      WIDTH // 2, HEIGHT - 45, 200, 50,
                                      self._hover_back, (100, 60, 60))

        w, h = window_surface.get_size()
        scale, dest = self._renderer.get_scale_rect(w, h)
        window_surface.fill((0, 0, 0))
        scaled = pygame.transform.smoothscale(surf, (dest.width, dest.height))
        window_surface.blit(scaled, dest)
        return scale, dest

    # -- section helpers -----------------------------------------------

    def _section_title(self, surf, y, text):
        _draw_text(surf, text, self._font_title, COLOR_CANDY,
                   WIDTH // 2, y, anchor="midtop")
        return y + self._font_title.get_height() + 10

    def _section_heading(self, surf, y, text):
        _draw_text(surf, text, self._font_heading, COLOR_TEXT_HIGHLIGHT,
                   40, y, anchor="topleft")
        pygame.draw.line(surf, (80, 90, 120), (40, y + self._font_heading.get_height() + 2),
                         (WIDTH - 40, y + self._font_heading.get_height() + 2), 1)
        return y + self._font_heading.get_height() + 12

    def _text(self, surf, y, text, color=None):
        _draw_text(surf, text, self._font_body, color or COLOR_TEXT,
                   60, y, anchor="topleft", shadow=False)
        return y + self._font_body.get_height() + 4

    def _draw_panel(self, surf, x, y, w, h):
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(panel, COLOR_PANEL_BG, (0, 0, w, h), border_radius=10)
        pygame.draw.rect(panel, COLOR_PANEL_BORDER, (0, 0, w, h), width=1, border_radius=10)
        surf.blit(panel, (x, y))

    # -- guide sections ------------------------------------------------

    def _draw_rope_guide(self, surf, y):
        self._draw_panel(surf, 30, y, WIDTH - 60, 70)

        # Standard Rope
        _draw_text(surf, "Rope", self._font_body,
                   COLOR_ROPE, 60, y + 10, shadow=False)
        _draw_text(surf, "Fixed length. Press letter key to cut.", self._font_body,
                   COLOR_TEXT, 60, y + 32, shadow=False)
        # Visual: brown line
        pygame.draw.line(surf, COLOR_ROPE, (500, y + 15), (640, y + 35), 3)

        return y + 80

    def _draw_anchor_guide(self, surf, y):
        self._draw_panel(surf, 30, y, WIDTH - 60, 310)

        items = [
            ("Static Anchor", COLOR_ANCHOR_GLOW,
             "Fixed point. Rope hangs from it. Press letter to cut."),
            ("Automatic Anchor (Magnet)", MAGNET_COLOR,
             "Auto-attaches rope when candy enters its blue radius."),
            ("Slider Anchor", SLIDER_COLOR,
             "Drag the handle along a track with mouse to reposition."),
            ("Winch Anchor", WINCH_COLOR,
             "Shift+Key = retract, Ctrl+Key = extend, Key = cut rope."),
        ]

        for i, (name, color, desc) in enumerate(items):
            iy = y + 10 + i * 75
            # Icon
            pygame.draw.circle(surf, color, (80, iy + 20), 10, 2)
            pygame.draw.circle(surf, color, (80, iy + 20), 5)
            # Name
            _draw_text(surf, name, self._font_body, color, 105, iy + 5, shadow=False)
            # Description
            _draw_text(surf, desc, self._font_body, COLOR_TEXT, 105, iy + 28, shadow=False)

        return y + 320

    def _draw_teleport_guide(self, surf, y):
        self._draw_panel(surf, 30, y, WIDTH - 60, 110)

        # Hat A icon
        pygame.draw.polygon(surf, TELEPORT_COLOR_A,
                            [(70, y + 60), (110, y + 60), (105, y + 30), (75, y + 30)])
        pygame.draw.line(surf, TELEPORT_COLOR_A, (65, y + 60), (115, y + 60), 3)

        # Arrow
        pygame.draw.line(surf, COLOR_TEXT, (130, y + 45), (170, y + 45), 2)
        pygame.draw.polygon(surf, COLOR_TEXT, [(170, y + 40), (180, y + 45), (170, y + 50)])

        # Hat B icon
        pygame.draw.polygon(surf, TELEPORT_COLOR_B,
                            [(195, y + 60), (235, y + 60), (230, y + 30), (200, y + 30)])
        pygame.draw.line(surf, TELEPORT_COLOR_B, (190, y + 60), (240, y + 60), 3)

        _draw_text(surf, "Candy enters one hat, exits the other.", self._font_body,
                   COLOR_TEXT, 260, y + 20, shadow=False)
        _draw_text(surf, "Speed is preserved, direction is rotated.", self._font_body,
                   COLOR_TEXT, 260, y + 44, shadow=False)
        _draw_text(surf, "Cooldown prevents instant re-trigger.", self._font_body,
                   COLOR_TEXT, 260, y + 68, shadow=False)

        return y + 120

    def _draw_spider_guide(self, surf, y):
        self._draw_panel(surf, 30, y, WIDTH - 60, 100)

        # Spider icon
        cx, cy = 80, y + 50
        r = 12
        pygame.draw.circle(surf, SPIDER_COLOR, (cx, cy), r)
        pygame.draw.circle(surf, (200, 200, 200), (cx - 4, cy - 2), 3)
        pygame.draw.circle(surf, (200, 200, 200), (cx + 4, cy - 2), 3)
        pygame.draw.circle(surf, SPIDER_COLOR_EYE, (cx - 4, cy - 2), 2)
        pygame.draw.circle(surf, SPIDER_COLOR_EYE, (cx + 4, cy - 2), 2)
        # Legs
        for side in [-1, 1]:
            for j in range(3):
                angle = (j / 3) * 0.8 - 0.2
                lx = cx + side * int(18 * math.cos(angle))
                ly = cy + int(18 * math.sin(angle))
                pygame.draw.line(surf, (40, 40, 40), (cx + side * 5, cy), (lx, ly), 2)

        _draw_text(surf, "Crawls down ropes toward the candy.", self._font_body,
                   COLOR_TEXT, 120, y + 20, shadow=False)
        _draw_text(surf, "If it catches the candy, you LOSE!", self._font_body,
                   (255, 100, 100), 120, y + 44, shadow=False)
        _draw_text(surf, "Cut the rope before it reaches the candy.", self._font_body,
                   COLOR_TEXT, 120, y + 68, shadow=False)

        return y + 110

    def _draw_spike_guide(self, surf, y):
        self._draw_panel(surf, 30, y, WIDTH - 60, 80)

        # Spike icon
        sx = 60
        for i in range(4):
            bx = sx + i * 16
            pygame.draw.polygon(surf, COLOR_SPIKE,
                                [(bx, y + 55), (bx + 16, y + 55), (bx + 8, y + 25)])
            pygame.draw.circle(surf, COLOR_SPIKE_GLOW, (bx + 8, y + 25), 2)
        pygame.draw.line(surf, (100, 20, 20), (sx, y + 55), (sx + 64, y + 55), 3)

        _draw_text(surf, "Instant death! Avoid at all costs.", self._font_body,
                   (255, 100, 100), 150, y + 20, shadow=False)
        _draw_text(surf, "Candy touching spikes = Level Failed.", self._font_body,
                   COLOR_TEXT, 150, y + 44, shadow=False)

        return y + 90

    def _draw_controls_guide(self, surf, y):
        self._draw_panel(surf, 30, y, WIDTH - 60, 200)

        controls = [
            ("A / B / C", "Cut the corresponding rope"),
            ("Shift + Letter", "Retract winch rope (shorten)"),
            ("Ctrl + Letter", "Extend winch rope (lengthen)"),
            ("Mouse Drag", "Move slider anchor along track"),
            ("Scroll / Arrows", "Scroll this guide"),
            ("R", "Retry / Reset level"),
            ("SPACE", "Next level (on win)"),
            ("ESC", "Back to menu"),
        ]

        for i, (key, desc) in enumerate(controls):
            iy = y + 10 + i * 23
            _draw_text(surf, key, self._font_body, COLOR_TEXT_HIGHLIGHT,
                       60, iy, shadow=False)
            _draw_text(surf, desc, self._font_body, COLOR_TEXT,
                       250, iy, shadow=False)

        return y + 210


# =====================================================================
#  Custom Levels Screen
# =====================================================================

class CustomLevelScreen:
    """Browse and play custom levels created with the level editor."""

    def __init__(self):
        self._font_title = _get_font(FONT_SIZE_LARGE, bold=True)
        self._font_btn = _get_font(FONT_SIZE_NORMAL, bold=True)
        self._font_sm = _get_font(FONT_SIZE_SMALL)
        self._stars = StarField(50)
        self._time = 0.0
        self._hover_idx = -1
        self._hover_del_idx = -1
        self._btn_rects = []
        self._del_rects = []
        self._btn_back = None
        self._hover_back = False
        self._scroll_y = 0
        self._renderer = Renderer()
        self._levels = load_custom_levels()

    def handle_event(self, event, scale, dest_rect):
        if event.type == pygame.MOUSEMOTION:
            vx, vy = self._renderer.window_to_virtual(event.pos, scale, dest_rect)
            self._hover_idx = -1
            self._hover_del_idx = -1
            for i, r in enumerate(self._btn_rects):
                if r.collidepoint(vx, vy):
                    self._hover_idx = i
                    break
            for i, r in enumerate(self._del_rects):
                if r.collidepoint(vx, vy):
                    self._hover_del_idx = i
                    break
            self._hover_back = self._btn_back.collidepoint(vx, vy) if self._btn_back else False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # scroll up
                self._scroll_y = max(0, self._scroll_y - 60)
                return None
            elif event.button == 5:  # scroll down
                self._scroll_y = min(max(0, len(self._levels) * 90 - 600), self._scroll_y + 60)
                return None
            elif event.button == 1:
                vx, vy = self._renderer.window_to_virtual(event.pos, scale, dest_rect)
                # Check delete buttons first
                for i, r in enumerate(self._del_rects):
                    if r.collidepoint(vx, vy):
                        delete_custom_level(i)
                        self._levels = load_custom_levels()
                        self._btn_rects = []
                        self._del_rects = []
                        return None
                for i, r in enumerate(self._btn_rects):
                    if r.collidepoint(vx, vy):
                        return ("play_custom", i)
                if self._btn_back and self._btn_back.collidepoint(vx, vy):
                    return ("back",)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return ("back",)
            if event.key == pygame.K_UP:
                self._scroll_y = max(0, self._scroll_y - 60)
            if event.key == pygame.K_DOWN:
                self._scroll_y = min(max(0, len(self._levels) * 90 - 600), self._scroll_y + 60)

        return None

    def update(self, dt):
        self._time += dt
        self._stars.update(dt)

    def draw(self, window_surface):
        surf = self._renderer.virtual_surface
        _draw_gradient_bg(surf)
        self._stars.draw(surf)

        _draw_text(surf, "Custom Levels", self._font_title, COLOR_TEXT,
                   WIDTH // 2, 60, anchor="midtop")

        levels = self._levels
        self._btn_rects = []
        self._del_rects = []

        if not levels:
            _draw_text(surf, "No custom levels found.", self._font_sm,
                       (160, 160, 180), WIDTH // 2, 300, anchor="midtop")
            _draw_text(surf, "Use the Level Editor (level_editor.py)", self._font_sm,
                       (120, 130, 160), WIDTH // 2, 340, anchor="midtop")
            _draw_text(surf, "to create and save custom levels.", self._font_sm,
                       (120, 130, 160), WIDTH // 2, 370, anchor="midtop")
        else:
            btn_w = 500
            btn_h = 64
            start_y = 180
            for i, lvl in enumerate(levels):
                by = start_y + i * 80 - self._scroll_y
                if by < 120 or by > HEIGHT - 160:
                    # Off screen, still track rects for indexing
                    self._btn_rects.append(pygame.Rect(-999, -999, 1, 1))
                    self._del_rects.append(pygame.Rect(-999, -999, 1, 1))
                    continue

                name = lvl.get("name", f"Custom {i + 1}")
                hover = (i == self._hover_idx)
                rect = _draw_button(surf, name, self._font_btn,
                                    WIDTH // 2 - 30, by, btn_w, btn_h,
                                    hover, (60, 80, 120))
                self._btn_rects.append(rect)

                # Delete button (small red X)
                del_x = WIDTH // 2 + btn_w // 2 - 10
                del_rect = pygame.Rect(del_x, by - 16, 32, 32)
                del_hover = (i == self._hover_del_idx)
                del_color = (180, 60, 60) if not del_hover else (220, 80, 80)
                ds = pygame.Surface((32, 32), pygame.SRCALPHA)
                pygame.draw.rect(ds, (*del_color, 200), (0, 0, 32, 32), border_radius=6)
                x_font = _get_font(FONT_SIZE_SMALL, bold=True)
                xt = x_font.render("X", True, (255, 255, 255))
                ds.blit(xt, (32 // 2 - xt.get_width() // 2, 32 // 2 - xt.get_height() // 2))
                surf.blit(ds, del_rect.topleft)
                self._del_rects.append(del_rect)

            # Level count
            _draw_text(surf, f"{len(levels)} custom level(s)", self._font_sm,
                       (140, 150, 170), WIDTH // 2, 140, anchor="midtop", shadow=False)

        # Back button
        self._btn_back = _draw_button(surf, "Back", self._font_btn,
                                      WIDTH // 2, HEIGHT - 80, 200, 50,
                                      self._hover_back, (100, 60, 60))

        _draw_text(surf, "ESC = Back", self._font_sm,
                   (120, 130, 160), WIDTH // 2, HEIGHT - 40, anchor="midbottom")

        w, h = window_surface.get_size()
        scale, dest = self._renderer.get_scale_rect(w, h)
        window_surface.fill((0, 0, 0))
        scaled = pygame.transform.smoothscale(surf, (dest.width, dest.height))
        window_surface.blit(scaled, dest)
        return scale, dest
