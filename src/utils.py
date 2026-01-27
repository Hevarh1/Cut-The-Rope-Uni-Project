"""
Utility functions for rendering and coordinate conversion.
"""

import math
from typing import Tuple
import pygame
from .config import PYMUNK_HEIGHT


def pymunk_to_pygame(pos: Tuple[float, float]) -> Tuple[int, int]:
    """Convert pymunk coordinates (bottom-left origin) to pygame (top-left origin)."""
    return int(pos[0]), int(PYMUNK_HEIGHT - pos[1])


def pygame_to_pymunk(pos: Tuple[int, int]) -> Tuple[float, float]:
    """Convert pygame coordinates to pymunk coordinates."""
    return float(pos[0]), float(PYMUNK_HEIGHT - pos[1])


def line_segment_intersection(p1, p2, p3, p4) -> bool:
    """
    Check if line segment p1-p2 intersects with line segment p3-p4.
    Uses parametric line intersection formula.
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


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b."""
    return a + (b - a) * t


def lerp_color(color1: Tuple[int, int, int], color2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    """Interpolate between two colors."""
    return (
        int(lerp(color1[0], color2[0], t)),
        int(lerp(color1[1], color2[1], t)),
        int(lerp(color1[2], color2[2], t))
    )


def ease_out_quad(t: float) -> float:
    """Quadratic ease-out for smooth animations."""
    return 1 - (1 - t) * (1 - t)


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease-in-out for smooth animations."""
    if t < 0.5:
        return 2 * t * t
    else:
        return 1 - pow(-2 * t + 2, 2) / 2


def ease_out_elastic(t: float) -> float:
    """Elastic ease-out for bouncy animations."""
    if t == 0 or t == 1:
        return t
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1


def ease_out_bounce(t: float) -> float:
    """Bounce ease-out animation."""
    n1 = 7.5625
    d1 = 2.75
    
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate distance between two points."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def normalize_angle(angle: float) -> float:
    """Normalize angle to range [0, 2*pi]."""
    while angle < 0:
        angle += 2 * math.pi
    while angle >= 2 * math.pi:
        angle -= 2 * math.pi
    return angle
