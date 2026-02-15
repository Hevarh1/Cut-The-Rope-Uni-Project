"""
Level definitions for Cut The Rope.

Each level is a dict with:
  candy       - (x, y) start position
  target      - (x, y, radius) of Om Nom
  anchors     - list of static anchor dicts  {x, y, letter, length}
  magnets     - list of auto-attach anchors  {x, y, radius, letter}
  sliders     - list of slider anchors       {x, y, track_start, track_end, letter, start_t}
  winches     - list of winch anchors        {x, y, letter, length}
  platforms   - list of platforms            {x1, y1, x2, y2, thickness}
  spikes      - list of spike hazards       {x, y, width, height, direction}
  teleports   - list of teleport pairs      {ax, ay, bx, by, angle_a, angle_b}
  spiders     - list of spiders             {rope_index, start_t, speed}

Coordinates are in Pymunk space (origin bottom-left, Y up).
Canvas: 720 x 1280
"""

from .config import SPIDER_SPEED


def _default(d, key, val):
    if key not in d:
        d[key] = val


# =====================================================================
#  Campaign Levels
# =====================================================================

CAMPAIGN_LEVELS = [
    # ------------------------------------------------------------------
    # Level 1: Single static rope. Intro to cutting.
    # ------------------------------------------------------------------
    {
        "name": "First Cut",
        "candy": (360, 1100),
        "target": (360, 200, 30),
        "star_times": [3, 6, 15],
        "anchors": [
            {"x": 360, "y": 1200, "letter": "A", "length": 180},
        ],
        "magnets": [],
        "sliders": [],
        "winches": [],
        "platforms": [],
        "spikes": [],
        "teleports": [],
        "spiders": [],
    },
    # ------------------------------------------------------------------
    # Level 2: Two ropes. Cut the right one to swing candy into target.
    # ------------------------------------------------------------------
    {
        "name": "Double Swing",
        "candy": (360, 900),
        "target": (200, 250, 30),
        "star_times": [4, 8, 18],
        "anchors": [
            {"x": 260, "y": 1100, "letter": "A", "length": 250},
            {"x": 460, "y": 1050, "letter": "B", "length": 200},
        ],
        "magnets": [],
        "sliders": [],
        "winches": [],
        "platforms": [],
        "spikes": [],
        "teleports": [],
        "spiders": [],
    },
    # ------------------------------------------------------------------
    # Level 3: Single rope, drop candy into target.
    # ------------------------------------------------------------------
    {
        "name": "Bungee Drop",
        "candy": (360, 1000),
        "target": (360, 300, 30),
        "star_times": [4, 8, 18],
        "anchors": [
            {"x": 360, "y": 1150, "letter": "A", "length": 150},
        ],
        "magnets": [],
        "sliders": [],
        "winches": [],
        "platforms": [],
        "spikes": [],
        "teleports": [],
        "spiders": [],
    },
    # ------------------------------------------------------------------
    # Level 4: Magnet anchor. Candy swings, gets caught, new rope forms.
    # ------------------------------------------------------------------
    {
        "name": "Magnetic Pull",
        "candy": (200, 1000),
        "target": (550, 250, 30),
        "star_times": [5, 10, 20],
        "anchors": [
            {"x": 200, "y": 1150, "letter": "A", "length": 200},
        ],
        "magnets": [
            {"x": 500, "y": 800, "radius": 100, "letter": "B"},
        ],
        "sliders": [],
        "winches": [],
        "platforms": [],
        "spikes": [],
        "teleports": [],
        "spiders": [],
    },
    # ------------------------------------------------------------------
    # Level 5: Slider anchor. Drag hook to position candy over target.
    # ------------------------------------------------------------------
    {
        "name": "Slide & Drop",
        "candy": (300, 950),
        "target": (500, 250, 30),
        "star_times": [5, 10, 22],
        "anchors": [],
        "magnets": [],
        "sliders": [
            {"x": 300, "y": 1100, "track_start": (150, 1100), "track_end": (570, 1100),
             "letter": "A", "start_t": 0.3},
        ],
        "winches": [],
        "platforms": [],
        "spikes": [],
        "teleports": [],
        "spiders": [],
    },
    # ------------------------------------------------------------------
    # Level 6: Winch anchor. Extend rope to lower candy to target.
    # ------------------------------------------------------------------
    {
        "name": "Winch Down",
        "candy": (360, 1050),
        "target": (360, 300, 30),
        "star_times": [6, 12, 25],
        "anchors": [],
        "magnets": [],
        "sliders": [],
        "winches": [
            {"x": 360, "y": 1200, "letter": "A", "length": 120},
        ],
        "platforms": [],
        "spikes": [],
        "teleports": [],
        "spiders": [],
    },
    # ------------------------------------------------------------------
    # Level 7: Teleportation intro. Cut rope, candy falls into hat.
    # ------------------------------------------------------------------
    {
        "name": "Hat Trick",
        "candy": (200, 1000),
        "target": (550, 300, 30),
        "star_times": [6, 12, 25],
        "anchors": [
            {"x": 200, "y": 1150, "letter": "A", "length": 180},
        ],
        "magnets": [],
        "sliders": [],
        "winches": [],
        "platforms": [],
        "spikes": [],
        "teleports": [
            {"ax": 200, "ay": 500, "bx": 550, "by": 600,
             "angle_a": 1.5708, "angle_b": -1.5708},
        ],
        "spiders": [],
    },
    # ------------------------------------------------------------------
    # Level 8: Spider! Cut rope before spider reaches candy.
    # ------------------------------------------------------------------
    {
        "name": "Spider Escape",
        "candy": (360, 800),
        "target": (360, 200, 30),
        "star_times": [5, 10, 20],
        "anchors": [
            {"x": 360, "y": 1100, "letter": "A", "length": 350},
        ],
        "magnets": [],
        "sliders": [],
        "winches": [],
        "platforms": [],
        "spikes": [],
        "teleports": [],
        "spiders": [
            {"rope_index": 0, "start_t": 0.0, "speed": 55},
        ],
    },
    # ------------------------------------------------------------------
    # Level 9: Spikes hazard. Swing candy around spikes.
    # ------------------------------------------------------------------
    {
        "name": "Spike Dodge",
        "candy": (250, 950),
        "target": (500, 250, 30),
        "star_times": [7, 14, 28],
        "anchors": [
            {"x": 250, "y": 1150, "letter": "A", "length": 250},
            {"x": 500, "y": 1100, "letter": "B", "length": 200},
        ],
        "magnets": [],
        "sliders": [],
        "winches": [],
        "platforms": [],
        "spikes": [
            {"x": 360, "y": 550, "width": 120, "height": 25, "direction": "up"},
        ],
        "teleports": [],
        "spiders": [],
    },
    # ------------------------------------------------------------------
    # Level 10: Combo level - slider + spikes + teleport.
    # ------------------------------------------------------------------
    {
        "name": "Grand Finale",
        "candy": (180, 1000),
        "target": (550, 200, 30),
        "star_times": [8, 16, 30],
        "anchors": [
            {"x": 180, "y": 1150, "letter": "A", "length": 200},
        ],
        "magnets": [],
        "sliders": [
            {"x": 500, "y": 900, "track_start": (350, 900), "track_end": (620, 900),
             "letter": "B", "start_t": 0.5},
        ],
        "winches": [],
        "platforms": [
            {"x1": 300, "y1": 650, "x2": 500, "y2": 650, "thickness": 8},
        ],
        "spikes": [
            {"x": 400, "y": 450, "width": 80, "height": 20, "direction": "up"},
        ],
        "teleports": [
            {"ax": 180, "ay": 400, "bx": 550, "by": 500,
             "angle_a": 1.5708, "angle_b": 1.5708},
        ],
        "spiders": [],
    },
]


def get_level(index: int) -> dict:
    """Return level dict by 0-based index, with defaults filled in."""
    if index < 0 or index >= len(CAMPAIGN_LEVELS):
        return None
    lvl = dict(CAMPAIGN_LEVELS[index])
    for key in ("anchors", "magnets", "sliders", "winches",
                "platforms", "spikes", "teleports", "spiders"):
        _default(lvl, key, [])
    _default(lvl, "name", f"Level {index + 1}")
    return lvl


def total_levels() -> int:
    return len(CAMPAIGN_LEVELS)
