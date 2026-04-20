"""
Shared types, collision constants, and enums.

Single source of truth for the collision-type contract between
entities.py and physics.py, and for game-state values used by
game.py, input_handler.py, and game_renderer.py.
"""

# Collision types — contract between entities and physics
CT_CANDY    = 1
CT_TARGET   = 2
CT_PLATFORM = 3
CT_SPIKE    = 4
CT_TELE_A   = 5
CT_TELE_B   = 6


class GameState:
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"
