# Payload Drop

A physics-based puzzle game where you cut ropes to guide a payload into a target box. Built with `pygame-ce` and `pymunk`.

## Requirements

- Python 3.10+
- `pygame-ce`
- `pymunk`

## Install

Create/activate your virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python payload_drop.py
```

## How to Play

**Objective:** Cut the ropes holding the payload to swing and drop it into the green target box. The payload must settle (stay inside for 2 seconds) to win.

### Controls

- **Mouse Drag**: Draw a slash line to cut ropes
- **R**: Restart current level
- **I**: Toggle instructions on/off
- **Esc**: Return to level select
- **1-3 Keys**: Quick level select

### Strategy

1. **Observe** the rope configuration and target location
2. **Plan** which rope to cut first to create the right swing
3. **Time** your cuts to use momentum and gravity
4. **Avoid** spikes (red hazards)
5. **Use** platforms to bounce and redirect the payload

### Levels

- **Level 1**: Simple drop - cut the single rope
- **Level 2**: Dual ropes - swing the payload toward the target using momentum
- **Level 3**: Complex path - navigate around obstacles and spikes

## Game Mechanics

- **Pymunk Physics**: Realistic gravity, collisions, and rope constraints
- **PinJoint Ropes**: Act as fixed-length pendulums allowing natural swinging
- **Line Intersection**: Precise rope cutting using segment intersection detection
- **Collision Sensors**: Target box detects when payload enters and tracks settle time

## Architecture Notes

- Coordinate conversion between Pymunk (bottom-left origin) and Pygame (top-left origin)
- Rope cutting uses mathematical line segment intersection
- Physics simulation runs at 4 substeps per frame for stability
- Win condition requires both position (in target) and velocity (< 50 units/s) criteria

## Creating Custom Levels

Use the **visual level editor** to create your own levels:

```bash
python level_editor.py
```

### Level Editor Controls:

- **1** - Place Payload (red circle)
- **2** - Place Anchor (grey circle)
- **3** - Place Target Box (green box)
- **4** - Place Platform (grey rectangle)
- **5** - Place Spike (red hazard)
- **Left Click** - Place selected object
- **Right Click** - Delete object at mouse
- **S** - Save level code to console
- **C** - Clear all objects
- **ESC** - Quit

### Workflow:

1. Press `1` and click to place the payload (where it starts)
2. Press `2` and click to place anchors (where ropes attach)
3. Press `3` and click twice to draw the target box (top-left, then bottom-right)
4. Press `4` and click twice to draw platforms
5. Press `5` and click twice to draw spike hazards
6. Press `S` to print the level code to the console
7. Copy the generated `LevelData` code
8. Paste it into `payload_drop.py` in the `create_levels()` method
9. Add it to the return statement: `return [level_1, level_2, your_new_level]`

### Tips:

- Payload should be at a medium Y value (400-550)
- Anchors should be HIGHER Y values (600-700) - remember Y increases upward in pymunk!
- Target should be at LOW Y values (80-150) near the bottom
- Use platforms to create bounce paths
- Use spikes to add challenge (they reset the level on contact)
