"""
Configuration and constants for Cut The Rope game.
All game settings, colors, and physics constants are defined here.
"""

# =============================================================================
# WINDOW SETTINGS
# =============================================================================
WIDTH = 1280
HEIGHT = 720
FPS = 60
PYMUNK_HEIGHT = 720
GAME_TITLE = "Cut The Rope"

# =============================================================================
# PHYSICS SETTINGS
# =============================================================================
GRAVITY = -900  # Negative Y = downward in pymunk
PHYSICS_STEPS = 4  # Sub-steps per frame for smoother physics

# Payload
PAYLOAD_MASS = 15
PAYLOAD_RADIUS = 20
PAYLOAD_FRICTION = 0.7
PAYLOAD_ELASTICITY = 0.4

# Rope
ROPE_SEGMENT_LENGTH = 40  # Pixels between segments
ROPE_SEGMENT_MASS = 0.2
ROPE_SEGMENT_MOMENT = 0.3
ROPE_DAMPING = 5  # Higher = less oscillation
ROPE_ERROR_BIAS = 0.2  # Higher = faster correction
ROPE_WIDTH = 3

# Platform
PLATFORM_FRICTION = 0.7
PLATFORM_ELASTICITY = 0.5

# Target
TARGET_WALL_FRICTION = 0.6
TARGET_WALL_ELASTICITY = 0.3
TARGET_FLOOR_FRICTION = 0.7
TARGET_FLOOR_ELASTICITY = 0.2
TARGET_SETTLE_TIME = 2.0  # Seconds to win
TARGET_SETTLE_VELOCITY = 80  # Max velocity to count as "settled"

# Spikes
SPIKE_FRICTION = 0.3
SPIKE_ELASTICITY = 0.1

# =============================================================================
# COLOR PALETTE - Professional and smooth colors
# =============================================================================

# Background
COLOR_BG = (25, 28, 40)
COLOR_BG_GRADIENT_TOP = (35, 40, 58)
COLOR_BG_GRADIENT_BOTTOM = (20, 23, 35)

# Candy (ball)
CANDY_MASS = 15
CANDY_RADIUS = 20
CANDY_FRICTION = 0.7
CANDY_ELASTICITY = 0.4

COLOR_CANDY = (255, 107, 107)
COLOR_CANDY_HIGHLIGHT = (255, 160, 160)
COLOR_CANDY_SHADOW = (180, 60, 60)
COLOR_CANDY_STRIPE = (255, 80, 80)

# Anchor points
COLOR_ANCHOR = (120, 130, 150)
COLOR_ANCHOR_CORE = (80, 90, 110)
COLOR_ANCHOR_GLOW = (150, 160, 180)
COLOR_ANCHOR_RING = (90, 100, 120)

# Rope
COLOR_ROPE = (160, 120, 80)
COLOR_ROPE_SHADOW = (100, 70, 40)

# Target box
COLOR_TARGET = (80, 220, 140)
COLOR_TARGET_GLOW = (120, 255, 180)
COLOR_TARGET_DARK = (50, 180, 110)
COLOR_TARGET_INNER = (40, 150, 90)

# Platforms
COLOR_PLATFORM = (90, 100, 130)
COLOR_PLATFORM_HIGHLIGHT = (110, 120, 150)
COLOR_PLATFORM_SHADOW = (60, 70, 90)
COLOR_PLATFORM_TOP = (120, 130, 160)

# Spikes
COLOR_SPIKE = (220, 70, 70)
COLOR_SPIKE_DARK = (160, 40, 40)
COLOR_SPIKE_TIP = (255, 100, 100)

# UI
COLOR_TEXT = (240, 245, 255)
COLOR_TEXT_SHADOW = (40, 45, 60)
COLOR_TEXT_HIGHLIGHT = (255, 255, 255)
COLOR_SLASH = (255, 255, 255)
COLOR_SLASH_GLOW = (150, 200, 255)

# Particles
COLOR_PARTICLE_BOUNCE = (255, 200, 100)
COLOR_PARTICLE_STAR = (255, 255, 200)
COLOR_PARTICLE_SUCCESS = (120, 255, 180)
COLOR_PARTICLE_CUT = (255, 220, 150)

# UI Panels
COLOR_PANEL_BG = (25, 28, 40, 220)
COLOR_PANEL_BORDER = (80, 90, 120, 180)

# =============================================================================
# ANIMATION SETTINGS
# =============================================================================
SQUASH_RECOVERY_SPEED = 4.0  # How fast the ball recovers from squash
SQUASH_MIN = 0.6  # Minimum squash factor
PARTICLE_GRAVITY = 600  # Gravity for particles
PARTICLE_FADE_SPEED = 2.5  # How fast particles fade
GLOW_PULSE_SPEED = 0.08  # Target glow pulse speed
STAR_COUNT = 60  # Number of background stars

# Mouse trail
MOUSE_TRAIL_LENGTH = 15
MOUSE_TRAIL_WIDTH = 3
MOUSE_TRAIL_GLOW_WIDTH = 6

# =============================================================================
# FONTS
# =============================================================================
FONT_FAMILY = "Arial"  # More universal than Avenir
FONT_SIZE_SMALL = 18
FONT_SIZE_NORMAL = 24
FONT_SIZE_LARGE = 56
FONT_SIZE_HUGE = 72
