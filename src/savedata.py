"""
Save data management for Cut The Rope.

Handles:
  - High scores per level (with star ratings)
  - Custom levels (load / save)
"""

import json
import os
from typing import Optional

from .levels import CAMPAIGN_LEVELS

SCORES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "scores.json")
CUSTOM_LEVELS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "custom_levels.json")


def _ensure_data_dir():
    d = os.path.dirname(SCORES_FILE)
    os.makedirs(d, exist_ok=True)


# =====================================================================
#  Scores
# =====================================================================

def load_scores() -> dict:
    """Load scores dict from file. Returns {} on failure."""
    try:
        with open(SCORES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_scores(scores: dict):
    _ensure_data_dir()
    with open(SCORES_FILE, "w") as f:
        json.dump(scores, f, indent=2)


def get_best_time(level_index: int) -> Optional[float]:
    scores = load_scores()
    key = str(level_index)
    entry = scores.get(key)
    if entry and "time" in entry:
        return entry["time"]
    return None


def save_level_score(level_index: int, time_taken: float):
    scores = load_scores()
    key = str(level_index)
    current = scores.get(key)
    if current is None or time_taken < current.get("time", float("inf")):
        scores[key] = {"time": round(time_taken, 2)}
    save_scores(scores)


def get_completed_count() -> int:
    scores = load_scores()
    return len(scores)


def get_star_times(level_index: int) -> Optional[list]:
    """Return [3-star, 2-star, 1-star] time thresholds for a campaign level."""
    if 0 <= level_index < len(CAMPAIGN_LEVELS):
        return CAMPAIGN_LEVELS[level_index].get("star_times")
    return None


def get_star_count(level_index: int) -> int:
    """Return 0-3 stars earned for a campaign level based on best time."""
    bt = get_best_time(level_index)
    if bt is None:
        return 0
    st = get_star_times(level_index)
    if not st or len(st) < 3:
        return 1  # completed but no star thresholds defined
    # st = [3-star threshold, 2-star threshold, 1-star threshold]
    if bt <= st[0]:
        return 3
    elif bt <= st[1]:
        return 2
    else:
        return 1


def get_total_stars() -> int:
    """Return sum of all stars earned across campaign levels."""
    total = 0
    for i in range(len(CAMPAIGN_LEVELS)):
        total += get_star_count(i)
    return total


# =====================================================================
#  Custom Levels
# =====================================================================

def load_custom_levels() -> list:
    try:
        with open(CUSTOM_LEVELS_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []


def save_custom_levels(levels: list):
    _ensure_data_dir()
    with open(CUSTOM_LEVELS_FILE, "w") as f:
        json.dump(levels, f, indent=2)


def add_custom_level(level_data: dict):
    levels = load_custom_levels()
    levels.append(level_data)
    save_custom_levels(levels)


def delete_custom_level(index: int):
    levels = load_custom_levels()
    if 0 <= index < len(levels):
        levels.pop(index)
        save_custom_levels(levels)


def level_to_json(level_dict: dict) -> str:
    """Serialize a level dict to JSON string."""
    return json.dumps(level_dict, indent=2)


def level_from_json(json_str: str) -> Optional[dict]:
    """Deserialize a level from JSON string."""
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return None
