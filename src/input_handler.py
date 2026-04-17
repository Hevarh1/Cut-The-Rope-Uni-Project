"""
Input handling for Cut The Rope game.

Extracted from game.py so that input logic is isolated from
physics, rendering, and game state management.
"""

import pygame

from .config import COLOR_PARTICLE_CUT
from .types import GameState
from .utils import pymunk_to_pygame, pygame_to_pymunk


class InputHandler:
    """Handles mouse and keyboard input for a Game instance."""

    def __init__(self):
        self._mouse_down = False
        self._mouse_pos = (0, 0)
        self._mouse_pymunk = (0.0, 0.0)
        self._dragging_slider = None

    def handle_event(self, game, event, scale, dest_rect):
        if game.state != GameState.PLAYING:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._mouse_down = True
            vpos = game.renderer.window_to_virtual(event.pos, scale, dest_rect)
            self._mouse_pos = vpos
            self._mouse_pymunk = pygame_to_pymunk(vpos)
            game.renderer.update_trail(vpos)

            # Check slider drag start
            for sl in game.sliders:
                if sl.start_drag(self._mouse_pymunk):
                    self._dragging_slider = sl
                    break

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse_down = False
            game.renderer.clear_trail()
            if self._dragging_slider:
                self._dragging_slider.end_drag()
                self._dragging_slider = None

        elif event.type == pygame.MOUSEMOTION:
            vpos = game.renderer.window_to_virtual(event.pos, scale, dest_rect)
            self._mouse_pos = vpos
            self._mouse_pymunk = pygame_to_pymunk(vpos)

            if self._mouse_down:
                game.renderer.update_trail(vpos)

            # Slider dragging
            if self._dragging_slider:
                self._dragging_slider.update_drag(self._mouse_pymunk)

        elif event.type == pygame.KEYDOWN:
            self._handle_key(game, event)

    def _handle_key(self, game, event):
        """Handle letter-key cutting + winch extend/retract."""
        key_name = pygame.key.name(event.key).upper()

        # Only handle single letter keys A-Z
        if len(key_name) != 1 or not key_name.isalpha():
            return

        mods = pygame.key.get_mods()
        shift = mods & pygame.KMOD_SHIFT
        ctrl = mods & (pygame.KMOD_CTRL | pygame.KMOD_META)

        # Check winch anchors first for Shift/Ctrl + letter
        for w in game.winches:
            if w.letter == key_name and w.active:
                if shift:
                    return  # Retract handled continuously in update
                elif ctrl:
                    return  # Extend handled continuously in update
                else:
                    # Plain letter = cut the winch rope
                    self._cut_by_letter(game, key_name)
                    w.active = False
                    return

        # Plain letter = cut rope
        self._cut_by_letter(game, key_name)

    def _cut_by_letter(self, game, letter: str):
        """Cut rope by letter and emit particles."""
        rd = game.physics.cut_rope_by_letter(letter)
        if rd:
            if rd in game.rope_datas:
                game.rope_datas.remove(rd)
            # Particles at anchor position
            if rd.anchor_body:
                px, py = pymunk_to_pygame(rd.anchor_body.position)
                game.renderer.particle_system.emit(
                    px, py, COLOR_PARTICLE_CUT, count=15, speed=150)
            # Deactivate magnet anchors with this letter
            for m in game.magnets:
                if m.letter == letter.upper() and m.state == "active":
                    m.deactivate()
