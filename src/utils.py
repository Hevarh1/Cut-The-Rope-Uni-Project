"""
Utility functions for rendering and coordinate conversion.
"""

import math
from typing import Tuple
import pygame
from .config import PYMUNK_HEIGHT


def pymunk_to_pygame(pos: Tuple[float, float], level_height: int = None) -> Tuple[int, int]:
    """Convert pymunk coordinates (bottom-left origin) to pygame (top-left origin).
    
    If *level_height* is given it is used as the Y-axis size instead of
    the default PYMUNK_HEIGHT (720).  This is essential for custom-sized
    levels so that objects placed at e.g. Y=1200 in a 1500-tall level
    end up at the correct pygame pixel row.
    """
    h = level_height if level_height is not None else PYMUNK_HEIGHT
    return int(pos[0]), int(h - pos[1])


def pygame_to_pymunk(pos: Tuple[int, int], level_height: int = None) -> Tuple[float, float]:
    """Convert pygame coordinates to pymunk coordinates."""
    h = level_height if level_height is not None else PYMUNK_HEIGHT
    return float(pos[0]), float(h - pos[1])


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


def catmull_rom_spline(points: list, num_interpolated: int = 8) -> list:
    """Generate smooth curve points using Catmull-Rom spline interpolation.
    
    Takes a list of control points and returns a much smoother list of points.
    """
    if len(points) < 2:
        return points
    if len(points) == 2:
        return points
    
    result = []
    
    # Duplicate first and last points for endpoint handling
    extended = [points[0]] + list(points) + [points[-1]]
    
    for i in range(1, len(extended) - 2):
        p0 = extended[i - 1]
        p1 = extended[i]
        p2 = extended[i + 1]
        p3 = extended[i + 2]
        
        for t_step in range(num_interpolated):
            t = t_step / num_interpolated
            t2 = t * t
            t3 = t2 * t
            
            # Catmull-Rom matrix multiplication
            x = 0.5 * (
                (2 * p1[0]) +
                (-p0[0] + p2[0]) * t +
                (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                (2 * p1[1]) +
                (-p0[1] + p2[1]) * t +
                (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            result.append((int(x), int(y)))
    
    # Add the last point
    result.append(points[-1])
    
    return result
