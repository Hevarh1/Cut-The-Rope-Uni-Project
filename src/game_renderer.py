"""
Game-level rendering: main frame, HUD, win/lose overlays.

Extracted from game.py so that game.py focuses on logic/physics,
while all screen painting lives here.
"""

import math
import pygame

from .config import (
    WIDTH, HEIGHT,
    COLOR_PARTICLE_SUCCESS,
    FONT_FAMILY, FONT_SIZE_SMALL, FONT_SIZE_NORMAL,
    COLOR_TEXT, COLOR_TEXT_SHADOW,
)
from .entity_renderer import (
    draw_candy, draw_target, draw_anchor, draw_magnet, draw_slider,
    draw_winch, draw_platform, draw_spike, draw_teleport, draw_spider,
    draw_rope,
)
from .types import GameState
from .savedata import get_star_times


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


def draw_game_frame(game, window_surface):
    """Draw everything. Returns (scale, dest_rect) for input mapping."""
    surf = game.renderer.virtual_surface
    game.renderer.begin_frame()

    t = game.time_elapsed

    # Platforms
    for p in game.platforms:
        draw_platform(p, surf, t)

    # Spikes
    for s in game.spikes_list:
        draw_spike(s, surf, t)

    # Teleports
    for tp in game.teleports:
        draw_teleport(tp, surf, t)

    # Ropes
    for rd in game.rope_datas:
        bodies = game.physics.get_rope_bodies_with_endpoints(rd, game.candy.body)
        draw_rope(surf, bodies, time=t)

    # Anchors
    for a in game.anchors:
        draw_anchor(a, surf, t)
    for m in game.magnets:
        draw_magnet(m, surf, t)
    for sl in game.sliders:
        draw_slider(sl, surf, t)
    for w in game.winches:
        draw_winch(w, surf, t)

    # Spiders
    for sp in game.spiders:
        draw_spider(sp, surf, t)

    # Target
    draw_target(game.target, surf, t)

    # Candy (hidden during/after swallow - target draws it)
    if not game.target.collected:
        draw_candy(game.candy, surf, t)

    # HUD
    draw_hud(surf, game)

    # Win/Lose overlay
    if game.state == GameState.WON:
        draw_win_overlay(surf, game)
    elif game.state == GameState.LOST:
        draw_lose_overlay(surf, game)

    return game.renderer.end_frame(window_surface)


def draw_hud(surface, game):
    """Draw time and controls info."""
    # Time
    t_str = f"Time: {game.time_elapsed:.1f}s"
    txt = game._font_sm.render(t_str, True, COLOR_TEXT)
    shadow = game._font_sm.render(t_str, True, COLOR_TEXT_SHADOW)
    surface.blit(shadow, (16, 16))
    surface.blit(txt, (15, 15))

    # Level name
    name = game.level_data.get("name", f"Level {game.level_index + 1}")
    ntxt = game._font_sm.render(name, True, COLOR_TEXT)
    surface.blit(ntxt, (WIDTH - ntxt.get_width() - 15, 15))

    # Controls hints at bottom
    hints = []
    letters_used = set()
    for a in game.anchors:
        if a.letter and a.active:
            letters_used.add(a.letter)
    for rd in game.rope_datas:
        if rd.letter:
            letters_used.add(rd.letter)
    for w in game.winches:
        if w.letter and w.active:
            hints.append(f"Shift+{w.letter}=Retract  Ctrl+{w.letter}=Extend  {w.letter}=Cut")
    for sl in game.sliders:
        if sl.letter:
            hints.append(f"Drag {sl.letter} slider  {sl.letter}=Cut")

    # Show cut keys
    cut_letters = sorted(letters_used)
    if cut_letters and not hints:
        hints.append("Press " + "/".join(cut_letters) + " to cut rope")
    if game.sliders:
        hints.append("Click+drag slider handle to move")

    y = HEIGHT - 20
    for h in reversed(hints):
        htxt = game._font_sm.render(h, True, (*COLOR_TEXT[:3],))
        surface.blit(htxt, (WIDTH // 2 - htxt.get_width() // 2, y - htxt.get_height()))
        y -= htxt.get_height() + 4


def draw_win_overlay(surface, game):
    alpha = min(1.0, game.win_timer * 2)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(120 * alpha)))
    surface.blit(overlay, (0, 0))

    txt = game._font_md.render("Level Complete!", True, COLOR_PARTICLE_SUCCESS)
    tw, th = txt.get_size()
    surface.blit(txt, (WIDTH // 2 - tw // 2, HEIGHT // 2 - 100))

    t_str = f"Time: {game.time_elapsed:.2f}s"
    ttxt = game._font_sm.render(t_str, True, COLOR_TEXT)
    surface.blit(ttxt, (WIDTH // 2 - ttxt.get_width() // 2, HEIGHT // 2 - 50))

    # Star rating – use level_data star_times first (works for custom levels too)
    st = game.level_data.get("star_times") or get_star_times(game.level_index)
    if st and len(st) >= 3:
        stars_earned = 3 if game.time_elapsed <= st[0] else (2 if game.time_elapsed <= st[1] else 1)
    else:
        stars_earned = 1
    star_y = HEIGHT // 2 - 5
    star_size = 24
    gap = 60
    start_x = WIDTH // 2 - gap
    for i in range(3):
        sx = start_x + i * gap
        filled = i < stars_earned
        _draw_star_shape(surface, sx, star_y, star_size, filled)

    # Star time thresholds
    if st and len(st) >= 3:
        info = f"\u2605\u2605\u2605 < {st[0]}s   \u2605\u2605 < {st[1]}s   \u2605 < {st[2]}s"
        itxt = game._font_sm.render(info, True, (180, 180, 140))
        surface.blit(itxt, (WIDTH // 2 - itxt.get_width() // 2, star_y + 35))

    if game.win_timer > 1.0:
        hint = game._font_sm.render("SPACE = Next  |  R = Retry  |  ESC = Menu",
                                    True, COLOR_TEXT)
        surface.blit(hint, (WIDTH // 2 - hint.get_width() // 2, star_y + 70))


def draw_lose_overlay(surface, game):
    alpha = min(1.0, game.lose_timer * 2)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(120 * alpha)))
    surface.blit(overlay, (0, 0))

    txt = game._font_md.render(game.lose_reason or "Level Failed!", True, (255, 100, 100))
    tw, th = txt.get_size()
    surface.blit(txt, (WIDTH // 2 - tw // 2, HEIGHT // 2 - 40))

    if game.lose_timer > 1.0:
        hint = game._font_sm.render("Press R to retry  |  ESC for menu", True, COLOR_TEXT)
        surface.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 20))
