#!/usr/bin/env python3
"""
Payload Drop - A physics puzzle game
Entry point for the game.
"""

from src.game import PayloadDropGame


def main():
    """Main entry point."""
    game = PayloadDropGame()
    game.run()


if __name__ == "__main__":
    main()
