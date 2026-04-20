"""
Entity rendering functions for Cut The Rope.

All visual drawing logic extracted from entity classes so that
entities.py remains a pure model layer (data + physics + logic).
Each function takes the entity as its first argument.
"""

import math
import pygame

from .config import (
    WIDTH, HEIGHT,
    CANDY_RADIUS,
    COLOR_CANDY, COLOR_CANDY_HIGHLIGHT, COLOR_CANDY_SHADOW,
    COLOR_CANDY_STRIPE, COLOR_CANDY_SHINE, COLOR_CANDY_DEEP,
    COLOR_ANCHOR, COLOR_ANCHOR_CORE, COLOR_ANCHOR_GLOW, COLOR_ANCHOR_RING,
    COLOR_ROPE, COLOR_ROPE_SHADOW,
    COLOR_TARGET, COLOR_TARGET_GLOW, COLOR_TARGET_DARK, COLOR_TARGET_INNER,
    COLOR_PLATFORM, COLOR_PLATFORM_HIGHLIGHT, COLOR_PLATFORM_SHADOW, COLOR_PLATFORM_TOP,
    COLOR_SPIKE, COLOR_SPIKE_DARK, COLOR_SPIKE_TIP, COLOR_SPIKE_BASE,
    COLOR_SPIKE_GLOW,
    MAGNET_COLOR, MAGNET_COLOR_ACTIVE, MAGNET_PULSE_SPEED,
    SLIDER_COLOR, SLIDER_COLOR_ACTIVE, SLIDER_HANDLE_RADIUS, SLIDER_TRACK_WIDTH,
    WINCH_COLOR, WINCH_COLOR_ACTIVE,
    WINCH_MIN_LENGTH, WINCH_MAX_LENGTH,
    TELEPORT_RADIUS, TELEPORT_COLOR_A, TELEPORT_COLOR_B, TELEPORT_PULSE_SPEED,
    SPIDER_RADIUS, SPIDER_COLOR, SPIDER_COLOR_BODY, SPIDER_COLOR_EYE,
    SPIDER_LEG_COLOR, SPIDER_GLOW_COLOR,
    ROPE_WIDTH,
    BALL_SHADOW_OFFSET, BALL_SHINE_OFFSET,
    FONT_FAMILY, FONT_SIZE_SMALL,
    COLOR_TEXT, COLOR_TEXT_SHADOW,
)
from .utils import pymunk_to_pygame, lerp, lerp_color, clamp, catmull_rom_spline


# =====================================================================
#  Candy
# =====================================================================

def draw_candy(candy, surface, time):
    px, py = candy.get_pygame_pos()
    r = CANDY_RADIUS

    shadow_surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
    pygame.draw.circle(shadow_surf, (0, 0, 0, 40),
                       (r * 2, r * 2 + BALL_SHADOW_OFFSET), int(r * 1.1))
    surface.blit(shadow_surf, (px - r * 2, py - r * 2))

    rx = max(4, int(r * candy.squash_x))
    ry = max(4, int(r * candy.squash_y))

    pygame.draw.ellipse(surface, COLOR_CANDY_DEEP,
                        (px - rx, py - ry, rx * 2, ry * 2))
    pygame.draw.ellipse(surface, COLOR_CANDY,
                        (px - rx + 1, py - ry + 1, rx * 2 - 2, ry * 2 - 2))
    stripe_w = max(2, rx // 3)
    pygame.draw.ellipse(surface, COLOR_CANDY_STRIPE,
                        (px - stripe_w, py - ry + 2, stripe_w * 2, ry * 2 - 4))
    hx = int(px + r * BALL_SHINE_OFFSET[0])
    hy = int(py + r * BALL_SHINE_OFFSET[1])
    pygame.draw.circle(surface, COLOR_CANDY_SHINE, (hx, hy), max(2, r // 3))

    pulse = 0.5 + 0.5 * math.sin(time * 3)
    glow_r = int(r + 2 + pulse * 2)
    glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (*COLOR_CANDY_HIGHLIGHT, int(30 * pulse)),
                       (glow_r + 2, glow_r + 2), glow_r, 1)
    surface.blit(glow_surf, (px - glow_r - 2, py - glow_r - 2))


# =====================================================================
#  Target
# =====================================================================

def draw_target(target, surface, time):
    px, py = target.get_pygame_pos()
    r = target.radius
    pulse = 0.5 + 0.5 * math.sin(time * 2.5)

    glow_r = int(r + 4 + pulse * 4)
    glow_surf = pygame.Surface((glow_r * 2 + 8, glow_r * 2 + 8), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (*COLOR_TARGET_GLOW, int(40 + 20 * pulse)),
                       (glow_r + 4, glow_r + 4), glow_r, 2)
    surface.blit(glow_surf, (px - glow_r - 4, py - glow_r - 4))

    if target._anim_state == target.STATE_SWALLOWING:
        t = target.swallow_progress
        if t < 0.3:
            mouth_open = 0.15 + 0.35 * (t / 0.3)
        elif t < 0.7:
            mouth_open = 0.5
        else:
            close_t = (t - 0.7) / 0.3
            mouth_open = 0.5 * (1.0 - close_t)

        pygame.draw.circle(surface, COLOR_TARGET_DARK, (px, py), r, 3)
        pygame.draw.circle(surface, COLOR_TARGET_INNER, (px, py), r - 3)
        pygame.draw.circle(surface, COLOR_TARGET, (px, py), r, 2)

        start_angle = math.pi * (0.5 - mouth_open)
        end_angle = math.pi * (0.5 + mouth_open)
        rect = pygame.Rect(px - r + 4, py - r + 4, (r - 4) * 2, (r - 4) * 2)
        pygame.draw.arc(surface, COLOR_TARGET_GLOW, rect, start_angle, end_angle, 3)

        if target._candy_draw_scale > 0.01:
            candy_r = max(1, int(CANDY_RADIUS * target._candy_draw_scale))
            slide_t = min(1.0, t * 1.5)
            if target._candy_draw_pos:
                cx = int(lerp(target._candy_draw_pos[0], px, slide_t))
                cy = int(lerp(target._candy_draw_pos[1], py, slide_t))
            else:
                cx, cy = px, py - r // 2
            pygame.draw.circle(surface, COLOR_CANDY, (cx, cy), candy_r)
            pygame.draw.circle(surface, COLOR_CANDY_HIGHLIGHT,
                               (cx - candy_r // 3, cy - candy_r // 3),
                               max(1, candy_r // 3))

        if t > 0.4:
            eye_y = py - r // 3
            pygame.draw.arc(surface, (255, 255, 255),
                            (px - r // 2 - 4, eye_y - 4, 8, 8),
                            0.2, math.pi - 0.2, 2)
            pygame.draw.arc(surface, (255, 255, 255),
                            (px + r // 2 - 4, eye_y - 4, 8, 8),
                            0.2, math.pi - 0.2, 2)

    elif target._anim_state == target.STATE_DONE:
        pygame.draw.circle(surface, COLOR_TARGET_DARK, (px, py), r, 3)
        pygame.draw.circle(surface, COLOR_TARGET_INNER, (px, py), r - 3)
        pygame.draw.circle(surface, COLOR_TARGET, (px, py), r, 2)

        eye_y = py - r // 3
        pygame.draw.arc(surface, (255, 255, 255),
                        (px - r // 2 - 5, eye_y - 5, 10, 10),
                        0.2, math.pi - 0.2, 2)
        pygame.draw.arc(surface, (255, 255, 255),
                        (px + r // 2 - 5, eye_y - 5, 10, 10),
                        0.2, math.pi - 0.2, 2)

        smile_rect = pygame.Rect(px - r // 2, py, r, r // 2)
        pygame.draw.arc(surface, (255, 255, 255), smile_rect,
                        math.pi + 0.3, 2 * math.pi - 0.3, 2)

    else:
        pygame.draw.circle(surface, COLOR_TARGET_DARK, (px, py), r, 3)
        pygame.draw.circle(surface, COLOR_TARGET_INNER, (px, py), r - 3)
        pygame.draw.circle(surface, COLOR_TARGET, (px, py), r, 2)

        mouth_open = 0.3 + 0.15 * math.sin(time * 4)
        start_angle = math.pi * (0.5 - mouth_open)
        end_angle = math.pi * (0.5 + mouth_open)
        rect = pygame.Rect(px - r + 4, py - r + 4, (r - 4) * 2, (r - 4) * 2)
        pygame.draw.arc(surface, COLOR_TARGET_GLOW, rect, start_angle, end_angle, 2)


# =====================================================================
#  Anchor
# =====================================================================

def draw_anchor(anchor, surface, time):
    if not anchor.active:
        return
    px, py = anchor.get_pygame_pos()

    pulse = 0.5 + 0.5 * math.sin(time * 2)
    gr = 12 + int(pulse * 2)
    gs = pygame.Surface((gr * 2 + 4, gr * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(gs, (*COLOR_ANCHOR_GLOW, int(40 + 20 * pulse)),
                       (gr + 2, gr + 2), gr, 1)
    surface.blit(gs, (px - gr - 2, py - gr - 2))

    pygame.draw.circle(surface, COLOR_ANCHOR_RING, (px, py), 10, 2)
    pygame.draw.circle(surface, COLOR_ANCHOR_CORE, (px, py), 7)
    pygame.draw.circle(surface, COLOR_ANCHOR_GLOW, (px, py), 4)
    pygame.draw.circle(surface, COLOR_ANCHOR, (px, py), 2)

    if anchor.letter:
        try:
            font = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_SMALL, bold=True)
        except Exception:
            font = pygame.font.Font(None, FONT_SIZE_SMALL)
        txt = font.render(anchor.letter, True, COLOR_TEXT)
        shadow = font.render(anchor.letter, True, COLOR_TEXT_SHADOW)
        tw, th = txt.get_size()
        surface.blit(shadow, (px - tw // 2 + 1, py - 22 + 1))
        surface.blit(txt, (px - tw // 2, py - 22))


# =====================================================================
#  Magnet Anchor
# =====================================================================

def draw_magnet(magnet, surface, time):
    px, py = magnet.get_pygame_pos()
    r = int(magnet.radius)
    pulse = 0.5 + 0.5 * math.sin(time * MAGNET_PULSE_SPEED)
    is_active = magnet.state == "active"
    color = MAGNET_COLOR_ACTIVE if is_active else MAGNET_COLOR

    num_dashes = 24
    for i in range(num_dashes):
        if i % 2 == 0:
            angle1 = (i / num_dashes) * math.pi * 2 + time * 0.5
            angle2 = ((i + 1) / num_dashes) * math.pi * 2 + time * 0.5
            p1 = (px + int(r * math.cos(angle1)), py + int(r * math.sin(angle1)))
            p2 = (px + int(r * math.cos(angle2)), py + int(r * math.sin(angle2)))
            alpha = int(60 + 40 * pulse) if not is_active else int(120 + 60 * pulse)
            ds = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(ds, (*color, alpha), p1, p2, 2)
            surface.blit(ds, (0, 0))

    cr = 8 if not is_active else 10
    pygame.draw.circle(surface, color, (px, py), cr, 2)
    pygame.draw.circle(surface, color, (px, py), 4)

    if magnet.letter:
        try:
            font = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_SMALL, bold=True)
        except Exception:
            font = pygame.font.Font(None, FONT_SIZE_SMALL)
        txt = font.render(magnet.letter, True, color)
        tw, th = txt.get_size()
        surface.blit(txt, (px - tw // 2, py - 24))


# =====================================================================
#  Slider Anchor
# =====================================================================

def draw_slider(slider, surface, time):
    ts = pymunk_to_pygame(slider.track_start)
    te = pymunk_to_pygame(slider.track_end)
    pygame.draw.line(surface, (80, 80, 100), ts, te, SLIDER_TRACK_WIDTH)
    pygame.draw.circle(surface, (100, 100, 120), ts, 4)
    pygame.draw.circle(surface, (100, 100, 120), te, 4)

    px, py = slider.get_pygame_pos()
    color = SLIDER_COLOR_ACTIVE if slider.dragging else SLIDER_COLOR
    pygame.draw.circle(surface, color, (px, py), SLIDER_HANDLE_RADIUS)
    pygame.draw.circle(surface, (255, 255, 255), (px, py), SLIDER_HANDLE_RADIUS, 2)
    pygame.draw.circle(surface, (255, 255, 255), (px, py), 3)

    if slider.letter:
        try:
            font = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_SMALL, bold=True)
        except Exception:
            font = pygame.font.Font(None, FONT_SIZE_SMALL)
        txt = font.render(slider.letter, True, color)
        tw, th = txt.get_size()
        surface.blit(txt, (px - tw // 2, py - SLIDER_HANDLE_RADIUS - 18))


# =====================================================================
#  Winch Anchor
# =====================================================================

def draw_winch(winch, surface, time):
    if not winch.active:
        return
    px, py = winch.get_pygame_pos()

    pulse = 0.5 + 0.5 * math.sin(time * 2)
    color = WINCH_COLOR_ACTIVE if abs(winch.target_length - winch.current_length) > 2 else WINCH_COLOR

    gear_r = 14
    pygame.draw.circle(surface, color, (px, py), gear_r, 2)
    teeth = 8
    for i in range(teeth):
        angle = (i / teeth) * math.pi * 2 + time * 1.5
        ix = px + int((gear_r - 2) * math.cos(angle))
        iy = py + int((gear_r - 2) * math.sin(angle))
        ox = px + int((gear_r + 3) * math.cos(angle))
        oy = py + int((gear_r + 3) * math.sin(angle))
        pygame.draw.line(surface, color, (ix, iy), (ox, oy), 2)
    pygame.draw.circle(surface, color, (px, py), 5)
    pygame.draw.circle(surface, (40, 40, 40), (px, py), 3)

    bar_w = 30
    bar_h = 4
    frac = winch.get_length_fraction()
    bar_x = px - bar_w // 2
    bar_y = py + gear_r + 6
    pygame.draw.rect(surface, (60, 60, 80), (bar_x, bar_y, bar_w, bar_h), border_radius=2)
    fill_w = max(1, int(bar_w * frac))
    pygame.draw.rect(surface, color, (bar_x, bar_y, fill_w, bar_h), border_radius=2)

    if winch.letter:
        try:
            font = pygame.font.SysFont(FONT_FAMILY, FONT_SIZE_SMALL, bold=True)
        except Exception:
            font = pygame.font.Font(None, FONT_SIZE_SMALL)
        txt = font.render(winch.letter, True, color)
        tw, th = txt.get_size()
        surface.blit(txt, (px - tw // 2, py - gear_r - 20))


# =====================================================================
#  Platform
# =====================================================================

def draw_platform(platform, surface, time):
    pp1 = pymunk_to_pygame(platform.p1)
    pp2 = pymunk_to_pygame(platform.p2)
    t = platform.thickness
    pygame.draw.line(surface, COLOR_PLATFORM_SHADOW,
                     (pp1[0], pp1[1] + 2), (pp2[0], pp2[1] + 2), t + 2)
    pygame.draw.line(surface, COLOR_PLATFORM, pp1, pp2, t)
    pygame.draw.line(surface, COLOR_PLATFORM_TOP, pp1, pp2, max(1, t // 3))


# =====================================================================
#  Spike
# =====================================================================

def draw_spike(spike, surface, time):
    px, py = spike.get_pygame_pos()
    w = spike.width
    h = spike.height
    num_spikes = max(1, int(w // 16))
    spike_w = w / num_spikes
    pulse = 0.5 + 0.5 * math.sin(time * 3)

    for i in range(num_spikes):
        cx = px - w / 2 + spike_w * (i + 0.5)
        if spike.direction == "up":
            base_l = (int(cx - spike_w / 2), py)
            base_r = (int(cx + spike_w / 2), py)
            tip = (int(cx), py - h)
        elif spike.direction == "down":
            base_l = (int(cx - spike_w / 2), py)
            base_r = (int(cx + spike_w / 2), py)
            tip = (int(cx), py + h)
        elif spike.direction == "left":
            base_l = (px, int(cx - spike_w / 2))
            base_r = (px, int(cx + spike_w / 2))
            tip = (px - h, int(cx))
        else:
            base_l = (px, int(cx - spike_w / 2))
            base_r = (px, int(cx + spike_w / 2))
            tip = (px + h, int(cx))

        pygame.draw.polygon(surface, COLOR_SPIKE_DARK, [base_l, base_r, tip])
        inner_pts = [
            (int(lerp(base_l[0], tip[0], 0.15)), int(lerp(base_l[1], tip[1], 0.15))),
            (int(lerp(base_r[0], tip[0], 0.15)), int(lerp(base_r[1], tip[1], 0.15))),
            tip
        ]
        pygame.draw.polygon(surface, COLOR_SPIKE, inner_pts)
        tc = lerp_color(COLOR_SPIKE_TIP, COLOR_SPIKE_GLOW, pulse)
        pygame.draw.circle(surface, tc, tip, 3)

    if spike.direction in ("up", "down"):
        pygame.draw.line(surface, COLOR_SPIKE_BASE,
                         (int(px - w / 2), py), (int(px + w / 2), py), 3)


# =====================================================================
#  Teleport Pair
# =====================================================================

def draw_teleport(tp, surface, time):
    for body, color, angle in [
        (tp.body_a, TELEPORT_COLOR_A, tp.angle_a),
        (tp.body_b, TELEPORT_COLOR_B, tp.angle_b),
    ]:
        px, py = pymunk_to_pygame(body.position)
        r = TELEPORT_RADIUS
        pulse = 0.5 + 0.5 * math.sin(time * TELEPORT_PULSE_SPEED)

        ring_r = int(r + 3 + pulse * 4)
        rs = pygame.Surface((ring_r * 2 + 8, ring_r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(rs, (*color, int(50 + 30 * pulse)),
                           (ring_r + 4, ring_r + 4), ring_r, 2)
        surface.blit(rs, (px - ring_r - 4, py - ring_r - 4))

        hw = r
        hh = int(r * 0.8)
        local_pts = [
            (-hw, hh // 2),
            (hw, hh // 2),
            (int(hw * 0.6), -hh // 2),
            (-int(hw * 0.6), -hh // 2),
        ]

        rot = -angle - math.pi / 2
        cos_r = math.cos(rot)
        sin_r = math.sin(rot)
        pts = [(px + int(lx * cos_r - ly * sin_r),
                py + int(lx * sin_r + ly * cos_r))
               for lx, ly in local_pts]
        pygame.draw.polygon(surface, color, pts)

        brim_l = (-hw - 4, hh // 2)
        brim_r = (hw + 4, hh // 2)
        bl = (px + int(brim_l[0] * cos_r - brim_l[1] * sin_r),
              py + int(brim_l[0] * sin_r + brim_l[1] * cos_r))
        br = (px + int(brim_r[0] * cos_r - brim_r[1] * sin_r),
              py + int(brim_r[0] * sin_r + brim_r[1] * cos_r))
        pygame.draw.line(surface, color, bl, br, 3)
        pygame.draw.circle(surface, color, (px, py), int(r * 0.3))

        if tp.cooldown_timer <= 0:
            tip = (0, -hh // 2 - 6)
            sp = (px + int(tip[0] * cos_r - tip[1] * sin_r),
                  py + int(tip[0] * sin_r + tip[1] * cos_r))
            pygame.draw.circle(surface, (255, 255, 255), sp, 3)


# =====================================================================
#  Spider
# =====================================================================

def draw_spider(spider, surface, time):
    if not spider.alive:
        return
    px, py = spider.get_pygame_pos()
    r = SPIDER_RADIUS

    glow_pulse = 0.6 + 0.4 * math.sin(time * 5)
    glow_r = int(r * 2.2 + glow_pulse * 4)
    glow_surf = pygame.Surface((glow_r * 2 + 8, glow_r * 2 + 8), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (*SPIDER_GLOW_COLOR, int(35 * glow_pulse)),
                       (glow_r + 4, glow_r + 4), glow_r)
    pygame.draw.circle(glow_surf, (*SPIDER_GLOW_COLOR, int(60 * glow_pulse)),
                       (glow_r + 4, glow_r + 4), int(glow_r * 0.7))
    surface.blit(glow_surf, (px - glow_r - 4, py - glow_r - 4))

    for side in [-1, 1]:
        for i in range(4):
            angle_base = (i / 4) * math.pi * 0.8 - 0.3
            wobble = math.sin(spider._leg_phase + i * 1.2) * 0.3
            angle = angle_base + wobble
            lx = px + side * int((r + 12) * math.cos(angle))
            ly = py + int((r + 12) * math.sin(angle))
            mx = px + side * int(r * 0.6 * math.cos(angle + 0.2 * side))
            my = py + int(r * 0.6 * math.sin(angle + 0.2 * side))
            pygame.draw.line(surface, SPIDER_LEG_COLOR, (px + side * 4, py), (mx, my), 3)
            pygame.draw.line(surface, SPIDER_LEG_COLOR, (mx, my), (lx, ly), 3)
            pygame.draw.circle(surface, (90, 70, 90), (lx, ly), 2)

    pygame.draw.circle(surface, SPIDER_COLOR, (px, py), r)
    pygame.draw.circle(surface, SPIDER_COLOR_BODY, (px, py), r - 2)
    pygame.draw.circle(surface, (80, 30, 30), (px, py + 3), max(2, r // 3))

    eye_sep = max(4, r // 3)
    eye_r = max(4, r // 4)
    pygame.draw.circle(surface, (240, 240, 240), (px - eye_sep, py - r // 4), eye_r)
    pygame.draw.circle(surface, (240, 240, 240), (px + eye_sep, py - r // 4), eye_r)
    pygame.draw.circle(surface, SPIDER_COLOR_EYE, (px - eye_sep, py - r // 4), eye_r - 1)
    pygame.draw.circle(surface, SPIDER_COLOR_EYE, (px + eye_sep, py - r // 4), eye_r - 1)
    pygame.draw.circle(surface, (255, 200, 200), (px - eye_sep - 1, py - r // 4 - 1), max(1, eye_r // 2))
    pygame.draw.circle(surface, (255, 200, 200), (px + eye_sep - 1, py - r // 4 - 1), max(1, eye_r // 2))

    pygame.draw.circle(surface, SPIDER_GLOW_COLOR, (px, py), r + 1, 2)


# =====================================================================
#  Rope
# =====================================================================

def draw_rope(surface, bodies, time=0.0):
    """Draw a rope through the bodies list using Catmull-Rom spline."""
    if len(bodies) < 2:
        return

    points = [pymunk_to_pygame(b.position) for b in bodies]
    color = COLOR_ROPE
    width = ROPE_WIDTH

    if len(points) >= 3:
        smooth = catmull_rom_spline(points, 6)
    else:
        smooth = points

    shadow = [(p[0] + 1, p[1] + 2) for p in smooth]
    if len(shadow) >= 2:
        pygame.draw.lines(surface, COLOR_ROPE_SHADOW, False, shadow, width)
    if len(smooth) >= 2:
        pygame.draw.lines(surface, color, False, smooth, width)
