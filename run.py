#!/usr/bin/env python3
"""
Cut The Rope - A Physics Puzzle Game
Entry point and main application loop.

Manages screen transitions between:
  Title -> Level Select -> Game -> (Win/Lose) -> Level Select
                        -> Guide -> Title
"""

import sys
import pygame

from src.config import WIDTH, HEIGHT, FPS, GAME_TITLE
from src.ui import TitleScreen, LevelSelect, GuideScreen, CustomLevelScreen
from src.game import Game
from src.types import GameState
from src.levels import get_level, total_levels
from src.savedata import load_custom_levels


class App:
    """Top-level application managing screen flow."""

    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.window = pygame.display.set_mode(
            (WIDTH, HEIGHT), pygame.RESIZABLE
        )
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()

        self.screen = "title"  # title | level_select | guide | custom_levels | game
        self.title = TitleScreen()
        self.level_select = LevelSelect()
        self.guide = GuideScreen()
        self.custom_levels_screen = CustomLevelScreen()
        self.game = None
        self.current_level = 0

        # Scaling info (updated each frame)
        self._scale = 1.0
        self._dest = pygame.Rect(0, 0, WIDTH, HEIGHT)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # clamp for lag spikes

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                self._handle_event(event)

            self._update(dt)
            self._draw()
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def _handle_event(self, event):
        if self.screen == "title":
            result = self.title.handle_event(event, self._scale, self._dest)
            if result == "level_select":
                self.screen = "level_select"
                self.level_select = LevelSelect()
            elif result == "guide":
                self.screen = "guide"
                self.guide = GuideScreen()
            elif result == "custom_levels":
                self.screen = "custom_levels"
                self.custom_levels_screen = CustomLevelScreen()

        elif self.screen == "level_select":
            result = self.level_select.handle_event(event, self._scale, self._dest)
            if result:
                if result[0] == "play":
                    self._start_level(result[1])
                elif result[0] == "back":
                    self.screen = "title"
                    self.title = TitleScreen()

        elif self.screen == "guide":
            result = self.guide.handle_event(event, self._scale, self._dest)
            if result == "back":
                self.screen = "title"
                self.title = TitleScreen()

        elif self.screen == "custom_levels":
            result = self.custom_levels_screen.handle_event(event, self._scale, self._dest)
            if result:
                if result[0] == "play_custom":
                    self._start_custom_level(result[1])
                elif result[0] == "back":
                    self.screen = "title"
                    self.title = TitleScreen()

        elif self.screen == "game" and self.game:
            # Game-level events
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.screen = "level_select"
                    self.level_select = LevelSelect()
                    self.game = None
                    return
                if event.key == pygame.K_r:
                    # R resets level at any time
                    self._start_level(self.current_level)
                    return
                if self.game.state == GameState.WON:
                    if event.key == pygame.K_SPACE:
                        # Next level
                        next_idx = self.current_level + 1
                        if next_idx < total_levels():
                            self._start_level(next_idx)
                        else:
                            self.screen = "level_select"
                            self.level_select = LevelSelect()
                            self.game = None
                        return

            self.game.handle_event(event, self._scale, self._dest)

    def _start_level(self, index):
        level_data = get_level(index)
        if level_data:
            self.current_level = index
            self.game = Game(level_data, index)
            self.screen = "game"

    def _start_custom_level(self, index):
        levels = load_custom_levels()
        if 0 <= index < len(levels):
            level_data = levels[index]
            # Fill in defaults
            for key in ("anchors", "magnets", "sliders", "winches",
                        "platforms", "spikes", "teleports", "spiders"):
                if key not in level_data:
                    level_data[key] = []
            if "name" not in level_data:
                level_data["name"] = f"Custom {index + 1}"
            self.current_level = -1  # custom, no campaign index
            self.game = Game(level_data, -1)
            self.screen = "game"

    def _update(self, dt):
        if self.screen == "title":
            self.title.update(dt)
        elif self.screen == "level_select":
            self.level_select.update(dt)
        elif self.screen == "guide":
            self.guide.update(dt)
        elif self.screen == "custom_levels":
            self.custom_levels_screen.update(dt)
        elif self.screen == "game" and self.game:
            self.game.update(dt)

    def _draw(self):
        if self.screen == "title":
            self._scale, self._dest = self.title.draw(self.window)
        elif self.screen == "level_select":
            self._scale, self._dest = self.level_select.draw(self.window)
        elif self.screen == "guide":
            self._scale, self._dest = self.guide.draw(self.window)
        elif self.screen == "custom_levels":
            self._scale, self._dest = self.custom_levels_screen.draw(self.window)
        elif self.screen == "game" and self.game:
            self._scale, self._dest = self.game.draw(self.window)


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
