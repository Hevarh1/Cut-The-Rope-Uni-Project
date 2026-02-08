"""
Level data and management.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class LevelData:
    """Data structure for a single level."""
    candy_pos: Tuple[float, float]
    anchors: List[Tuple[float, float]]
    target_pos: Tuple[float, float]
    target_size: Tuple[float, float]
    platforms: List[Tuple[float, float, float, float]]  # x, y, w, h
    spikes: List[Tuple[float, float, float, float]]
    name: str = ""
    difficulty: int = 1


class LevelManager:
    """Manages game levels."""
    
    def __init__(self):
        self.levels = self._create_levels()
        self.current_index = 0
    
    @property
    def current_level(self) -> LevelData:
        return self.levels[self.current_index]
    
    @property
    def level_count(self) -> int:
        return len(self.levels)
    
    def select_level(self, index: int) -> bool:
        """Select a level by index. Returns True if valid."""
        if 0 <= index < len(self.levels):
            self.current_index = index
            return True
        return False
    
    def next_level(self) -> bool:
        """Go to next level. Returns True if there is one."""
        if self.current_index < len(self.levels) - 1:
            self.current_index += 1
            return True
        return False
    
    def _create_levels(self) -> List[LevelData]:
        """Create all game levels."""
        # Note: In Pymunk, Y increases UPWARD. Higher Y = higher on screen.
        
        levels = [
            # Level 1: Simple drop
            LevelData(
                name="First Drop",
                difficulty=1,
                candy_pos=(640, 520),
                anchors=[(640, 670)],
                target_pos=(640, 120),
                target_size=(120, 80),
                platforms=[],
                spikes=[]
            ),
            
            # Level 2: Two ropes swing
            LevelData(
                name="Double Trouble",
                difficulty=1,
                candy_pos=(400, 470),
                anchors=[(300, 670), (500, 670)],
                target_pos=(800, 120),
                target_size=(140, 80),
                platforms=[(650, 270, 200, 20)],
                spikes=[]
            ),
            
            # Level 3: Path with obstacles
            LevelData(
                name="Obstacle Course",
                difficulty=2,
                candy_pos=(300, 520),
                anchors=[(200, 670), (400, 640)],
                target_pos=(950, 120),
                target_size=(150, 80),
                platforms=[
                    (500, 320, 150, 20),
                    (750, 240, 150, 20)
                ],
                spikes=[(600, 90, 100, 20)]
            ),
            
            # Level 4: Platform puzzle
            LevelData(
                name="Platform Puzzle",
                difficulty=2,
                candy_pos=(162, 522),
                anchors=[(242, 525), (337, 518)],
                target_pos=(544, 223),
                target_size=(137, 51),
                platforms=[(242, 279, 161, 82)],
                spikes=[]
            ),
            
            # Level 5: Multi-anchor challenge
            LevelData(
                name="Triple Threat",
                difficulty=3,
                candy_pos=(190, 425),
                anchors=[(326, 514), (333, 314), (623, 616)],
                target_pos=(919, 158),
                target_size=(161, 72),
                platforms=[(522, 203, 242, 35), (1038, 221, 50, 209)],
                spikes=[(328, 220, 171, 36), (976, 405, 37, 119)]
            ),
            
            # Level 6: Expert level
            LevelData(
                name="The Gauntlet",
                difficulty=4,
                candy_pos=(236, 489),
                anchors=[(134, 537), (353, 623), (533, 605)],
                target_pos=(1154, 113),
                target_size=(180, 63),
                platforms=[(453, 233, 277, 31), (796, 175, 171, 34)],
                spikes=[(1221, 154, 25, 253), (974, 118, 78, 27)]
            ),
        ]
        
        return levels
