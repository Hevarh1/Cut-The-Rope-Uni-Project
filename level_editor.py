"""
Cut The Rope - Level Editor

Click to place objects, level data automatically saves to a file.

Controls:
- 1: Place Candy (red circle)
- 2: Place Anchor (grey circle)
- 3: Place Target Box (green box)
- 4: Place Platform (grey rectangle)
- 5: Place Spike (red rectangle)
- Click: Place selected object
- Right Click: Delete object at mouse
- S: Save level (prompts for name in console)
- C: Clear all objects
- ESC: Quit

For rectangles (Platform/Spike/Target):
- Click once for top-left corner
- Click again for bottom-right corner
"""

import sys
import pygame
from typing import List, Tuple, Optional
import os

WIDTH, HEIGHT = 1280, 720
PYMUNK_HEIGHT = 720

# Colors
COLOR_BG = (15, 18, 25)
COLOR_PAYLOAD = (220, 60, 60)
COLOR_ANCHOR = (100, 100, 120)
COLOR_TARGET = (60, 200, 100)
COLOR_PLATFORM = (80, 80, 100)
COLOR_SPIKE = (180, 40, 40)
COLOR_TEXT = (230, 230, 240)
COLOR_GRID = (30, 35, 45)
COLOR_SUCCESS = (80, 220, 120)


def pygame_to_pymunk_y(pygame_y: int) -> float:
    """Convert pygame Y coordinate to pymunk Y coordinate."""
    return float(PYMUNK_HEIGHT - pygame_y)


class EditorObject:
    def __init__(self, obj_type: str, data: dict):
        self.type = obj_type
        self.data = data


class LevelEditor:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Cut The Rope - Level Editor")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Avenir", 18)
        self.big_font = pygame.font.SysFont("Avenir", 24)
        
        self.objects: List[EditorObject] = []
        self.mode = "candy"  # Current placement mode
        self.rect_start: Optional[Tuple[int, int]] = None
        
        # Default sizes
        self.candy_radius = 20
        self.anchor_radius = 8
        self.target_default_size = (120, 80)
        
        # Save status
        self.save_message = ""
        self.save_message_timer = 0
        
        # Level counter
        self.level_counter = 1
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_1:
                    self.mode = "candy"
                    self.rect_start = None
                elif event.key == pygame.K_2:
                    self.mode = "anchor"
                    self.rect_start = None
                elif event.key == pygame.K_3:
                    self.mode = "target"
                    self.rect_start = None
                elif event.key == pygame.K_4:
                    self.mode = "platform"
                    self.rect_start = None
                elif event.key == pygame.K_5:
                    self.mode = "spike"
                    self.rect_start = None
                elif event.key == pygame.K_c:
                    self.objects.clear()
                    self.rect_start = None
                elif event.key == pygame.K_s:
                    self.save_level()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.place_object(event.pos)
                elif event.button == 3:  # Right click
                    self.delete_object_at(event.pos)
    
    def place_object(self, pos: Tuple[int, int]):
        mx, my = pos
        pymunk_y = pygame_to_pymunk_y(my)
        
        if self.mode == "candy":
            # Remove existing candy
            self.objects = [obj for obj in self.objects if obj.type != "candy"]
            self.objects.append(EditorObject("candy", {
                'x': mx,
                'y': pymunk_y
            }))
        
        elif self.mode == "anchor":
            self.objects.append(EditorObject("anchor", {
                'x': mx,
                'y': pymunk_y
            }))
        
        elif self.mode in ["target", "platform", "spike"]:
            # Rectangle placement - two clicks
            if self.rect_start is None:
                self.rect_start = pos
            else:
                x1, y1 = self.rect_start
                x2, y2 = pos
                
                # Ensure x1 < x2 and y1 < y2
                left = min(x1, x2)
                right = max(x1, x2)
                top = min(y1, y2)
                bottom = max(y1, y2)
                
                width = right - left
                height = bottom - top
                
                # Convert to pymunk coordinates
                pymunk_top = pygame_to_pymunk_y(bottom)
                
                if self.mode == "target":
                    # Remove existing target
                    self.objects = [obj for obj in self.objects if obj.type != "target"]
                    center_x = left + width / 2
                    center_y = pymunk_top + height / 2
                    self.objects.append(EditorObject("target", {
                        'x': center_x,
                        'y': center_y,
                        'w': width,
                        'h': height
                    }))
                
                elif self.mode == "platform":
                    self.objects.append(EditorObject("platform", {
                        'x': left,
                        'y': pymunk_top,
                        'w': width,
                        'h': height
                    }))
                
                elif self.mode == "spike":
                    self.objects.append(EditorObject("spike", {
                        'x': left,
                        'y': pymunk_top,
                        'w': width,
                        'h': height
                    }))
                
                self.rect_start = None
    
    def delete_object_at(self, pos: Tuple[int, int]):
        mx, my = pos
        to_remove = []
        
        for obj in self.objects:
            if obj.type in ["candy", "anchor"]:
                obj_screen_y = PYMUNK_HEIGHT - obj.data['y']
                dist = ((mx - obj.data['x'])**2 + (my - obj_screen_y)**2)**0.5
                if dist < 20:
                    to_remove.append(obj)
            
            elif obj.type == "target":
                obj_screen_y = PYMUNK_HEIGHT - obj.data['y']
                rect = pygame.Rect(
                    obj.data['x'] - obj.data['w']/2,
                    obj_screen_y - obj.data['h']/2,
                    obj.data['w'],
                    obj.data['h']
                )
                if rect.collidepoint(mx, my):
                    to_remove.append(obj)
            
            elif obj.type in ["platform", "spike"]:
                obj_screen_y = PYMUNK_HEIGHT - obj.data['y'] - obj.data['h']
                rect = pygame.Rect(
                    obj.data['x'],
                    obj_screen_y,
                    obj.data['w'],
                    obj.data['h']
                )
                if rect.collidepoint(mx, my):
                    to_remove.append(obj)
        
        for obj in to_remove:
            self.objects.remove(obj)
    
    def save_level(self):
        """Save level automatically with console prompt."""
        candy = None
        anchors = []
        target = None
        platforms = []
        spikes = []
        
        for obj in self.objects:
            if obj.type == "candy":
                candy = (int(obj.data['x']), int(obj.data['y']))
            elif obj.type == "anchor":
                anchors.append((int(obj.data['x']), int(obj.data['y'])))
            elif obj.type == "target":
                target = {
                    'pos': (int(obj.data['x']), int(obj.data['y'])),
                    'size': (int(obj.data['w']), int(obj.data['h']))
                }
            elif obj.type == "platform":
                platforms.append((
                    int(obj.data['x']),
                    int(obj.data['y']),
                    int(obj.data['w']),
                    int(obj.data['h'])
                ))
            elif obj.type == "spike":
                spikes.append((
                    int(obj.data['x']),
                    int(obj.data['y']),
                    int(obj.data['w']),
                    int(obj.data['h'])
                ))
        
        # Prompt in console
        print("\n" + "="*60)
        print("SAVE LEVEL")
        print("="*60)
        level_name = input("Enter level name (or press Enter for default): ").strip()
        if not level_name:
            level_name = f"Level {self.level_counter}"
            self.level_counter += 1
        
        difficulty_input = input("Enter difficulty (1-3, default 1): ").strip()
        try:
            difficulty = int(difficulty_input) if difficulty_input else 1
            difficulty = max(1, min(3, difficulty))
        except:
            difficulty = 1
        
        # Generate code
        level_code = f"""
# {level_name}
LevelData(
    name="{level_name}",
    difficulty={difficulty},
    candy_pos={candy if candy else (640, 520)},
    anchors={anchors if anchors else [(640, 670)]},
    target_pos={target['pos'] if target else (640, 120)},
    target_size={target['size'] if target else (120, 80)},
    platforms={platforms},
    spikes={spikes}
),
"""
        
        # Save to file
        output_file = "generated_level.txt"
        with open(output_file, 'w') as f:
            f.write("="*60 + "\n")
            f.write("COPY THIS CODE TO src/levels.py\n")
            f.write("Add it to the levels list in _create_levels()\n")
            f.write("="*60 + "\n\n")
            f.write(level_code)
            f.write("\n" + "="*60 + "\n")
        
        self.save_message = f"Saved: {level_name} to {output_file}"
        self.save_message_timer = 4.0  # Show for 4 seconds
        
        # Print to console
        print("\n" + "="*60)
        print(f"✓ LEVEL SAVED: {level_name}")
        print(f"✓ File: {output_file}")
        print("="*60)
        print(level_code)
        print("="*60)
        print("Copy the code above and add it to src/levels.py")
        print("="*60 + "\n")
    
    def draw(self):
        self.screen.fill(COLOR_BG)
        
        # Draw grid
        for x in range(0, WIDTH, 40):
            pygame.draw.line(self.screen, COLOR_GRID, (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, 40):
            pygame.draw.line(self.screen, COLOR_GRID, (0, y), (WIDTH, y), 1)
        
        # Draw coordinate reference
        ref_text = self.font.render("Pymunk Y increases UPWARD", True, (100, 100, 120))
        self.screen.blit(ref_text, (WIDTH - 250, HEIGHT - 25))
        
        # Draw objects
        for obj in self.objects:
            if obj.type == "candy":
                screen_y = PYMUNK_HEIGHT - obj.data['y']
                pygame.draw.circle(self.screen, COLOR_PAYLOAD,
                                 (int(obj.data['x']), int(screen_y)),
                                 self.candy_radius)
                pygame.draw.circle(self.screen, (180, 50, 50),
                                 (int(obj.data['x']), int(screen_y)),
                                 self.candy_radius, 2)
            
            elif obj.type == "anchor":
                screen_y = PYMUNK_HEIGHT - obj.data['y']
                pygame.draw.circle(self.screen, COLOR_ANCHOR,
                                 (int(obj.data['x']), int(screen_y)), 10)
                pygame.draw.circle(self.screen, (60, 60, 80),
                                 (int(obj.data['x']), int(screen_y)), 6)
            
            elif obj.type == "target":
                screen_y = PYMUNK_HEIGHT - obj.data['y']
                rect = pygame.Rect(
                    obj.data['x'] - obj.data['w']/2,
                    screen_y - obj.data['h']/2,
                    obj.data['w'],
                    obj.data['h']
                )
                pygame.draw.rect(self.screen, COLOR_TARGET, rect, 4)
                # Open top
                pygame.draw.line(self.screen, COLOR_TARGET,
                               (rect.left, rect.top),
                               (rect.left, rect.bottom), 4)
                pygame.draw.line(self.screen, COLOR_TARGET,
                               (rect.right, rect.top),
                               (rect.right, rect.bottom), 4)
                pygame.draw.line(self.screen, COLOR_TARGET,
                               (rect.left, rect.bottom),
                               (rect.right, rect.bottom), 4)
            
            elif obj.type == "platform":
                screen_y = PYMUNK_HEIGHT - obj.data['y'] - obj.data['h']
                rect = pygame.Rect(obj.data['x'], screen_y, obj.data['w'], obj.data['h'])
                pygame.draw.rect(self.screen, COLOR_PLATFORM, rect)
            
            elif obj.type == "spike":
                screen_y = PYMUNK_HEIGHT - obj.data['y'] - obj.data['h']
                rect = pygame.Rect(obj.data['x'], screen_y, obj.data['w'], obj.data['h'])
                pygame.draw.rect(self.screen, COLOR_SPIKE, rect)
        
        # Draw rectangle in progress
        if self.rect_start:
            mx, my = pygame.mouse.get_pos()
            x1, y1 = self.rect_start
            width = abs(mx - x1)
            height = abs(my - y1)
            left = min(x1, mx)
            top = min(y1, my)
            
            color = COLOR_TARGET if self.mode == "target" else \
                   COLOR_PLATFORM if self.mode == "platform" else COLOR_SPIKE
            
            pygame.draw.rect(self.screen, color, (left, top, width, height), 2)
        
        # Draw save message if active
        if self.save_message_timer > 0:
            msg_surf = self.big_font.render(self.save_message, True, COLOR_SUCCESS)
            msg_rect = msg_surf.get_rect(center=(WIDTH // 2, 40))
            # Background
            bg_rect = msg_rect.inflate(20, 10)
            pygame.draw.rect(self.screen, (20, 25, 35), bg_rect, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_SUCCESS, bg_rect, width=2, border_radius=8)
            self.screen.blit(msg_surf, msg_rect)
        
        # Draw HUD
        self.draw_hud()
        
        pygame.display.flip()
    
    def draw_hud(self):
        # Mode indicator
        mode_text = self.big_font.render(f"Mode: {self.mode.upper()}", True, COLOR_TEXT)
        self.screen.blit(mode_text, (20, 20))
        
        # Instructions
        instructions = [
            "1: Payload | 2: Anchor | 3: Target | 4: Platform | 5: Spike",
            "Left Click: Place | Right Click: Delete",
            "S: Save Level | C: Clear All | ESC: Quit",
            "",
            "For rectangles: Click twice (top-left, then bottom-right)"
        ]
        
        y = 60
        for line in instructions:
            surf = self.font.render(line, True, (180, 180, 200))
            self.screen.blit(surf, (20, y))
            y += 22
        
        # Object count
        counts = {
            'candy': 0,
            'anchor': 0,
            'target': 0,
            'platform': 0,
            'spike': 0
        }
        for obj in self.objects:
            counts[obj.type] += 1
        
        y = HEIGHT - 120
        self.screen.blit(self.font.render("Objects:", True, COLOR_TEXT), (20, y))
        y += 25
        for obj_type, count in counts.items():
            if count > 0:
                text = self.font.render(f"  {obj_type}: {count}", True, (150, 150, 170))
                self.screen.blit(text, (20, y))
                y += 22
    
    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            
            # Update save message timer
            if self.save_message_timer > 0:
                self.save_message_timer -= dt
                if self.save_message_timer <= 0:
                    self.save_message = ""
            
            self.handle_events()
            self.draw()


if __name__ == "__main__":
    print(__doc__)
    LevelEditor().run()
