#!/usr/bin/env python3
"""
Cut The Rope - A physics puzzle game
Entry point for the game.
"""

from src.game import CutTheRopeGame


def main():
    """Main entry point."""
    game = CutTheRopeGame()
    game.run()


if __name__ == "__main__":
    main()
