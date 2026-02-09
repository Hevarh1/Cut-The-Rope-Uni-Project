# 🎮 Cut The Rope

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Pygame](https://img.shields.io/badge/Pygame-ce-2.4+-green.svg)
![Pymunk](https://img.shields.io/badge/Pymunk-6.5+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

*A physics-based puzzle game where you cut ropes to guide a candy ball into a target box.*

[Game Design Presentation](cut-the-rope-presentation.html) • [Play Now](#-getting-started)

</div>

---

## 📸 Overview

**Cut The Rope** is a puzzle game that challenges players to use physics and timing to solve levels. The candy hangs from ropes attached to anchors - your job is to cut the ropes at the right moment to let gravity and momentum guide the candy into the target box.

Built with **Python**, **pygame-ce**, and **pymunk** for realistic 2D physics simulation.

### ✨ Key Features

- 🔗 **Realistic Rope Physics** - Chains swing and respond to cuts naturally using Pymunk physics engine
- 🎯 **Progressive Difficulty** - 6 handcrafted levels introducing new mechanics gradually
- ⚡ **Responsive Controls** - Cut ropes with mouse slashes or keyboard letters
- 🎨 **Clean Visual Design** - Dark space theme with vibrant colors and particle effects
- 🛠️ **Built-in Level Editor** - Create and share your own custom levels
- 🔄 **Quick Reset** - Instantly retry levels with the R key

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10 or higher**
- **pip** (Python package installer)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/cut-the-rope.git
cd cut-the-rope
```

2. Create a virtual environment (recommended):
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### 🎮 How to Play

Run the game:
```bash
python run.py
```

#### Objective
Cut the ropes holding the candy to swing and drop it into the green target box. The candy must **settle** (stay inside for 2 seconds) to win!

#### Controls

| Action | Key/Mouse |
|--------|-----------|
| Cut Rope | Mouse drag / Letter keys (A, B, C...) |
| Restart Level | `R` |
| Toggle Instructions | `I` |
| Level Select | `1-6` number keys |
| Quit | `ESC` |

#### Strategy Tips

1. **Observe** the rope configuration and target location
2. **Plan** which rope to cut first to create the right swing
3. **Time** your cuts to use momentum and gravity effectively
4. **Avoid** red spike hazards - they reset the level!
5. **Use** platforms to bounce and redirect the candy

---

## 🎯 Levels

| Level | Description | Challenge |
|-------|-------------|-----------|
| **Level 1** | Simple Drop | Learn the basic mechanic - cut the single rope |
| **Level 2** | Double Swing | Use momentum from two ropes to reach the target |
| **Level 3** | Obstacle Course | Navigate around platforms and barriers |
| **Level 4** | Precision | Time your cuts perfectly for the right arc |
| **Level 5** | Hazard Warning | Avoid deadly spikes while solving the puzzle |
| **Level 6** | Master Challenge | Combine all skills in a complex multi-rope setup |

---

## 🛠️ Level Editor

Create your own puzzles with the built-in visual level editor!

### Running the Editor

```bash
python level_editor.py
```

### Editor Controls

| Key | Action |
|-----|--------|
| `1` | Place Candy (starting position) |
| `2` | Place Anchor (rope attachment point) |
| `3` | Place Target Box (click twice for corners) |
| `4` | Place Platform (click twice for corners) |
| `5` | Place Spike (hazard) |
| `Left Click` | Place selected object |
| `Right Click` | Delete object at mouse |
| `S` | Print level code to console |
| `C` | Clear all objects |
| `ESC` | Quit editor |

### Adding Your Level

1. Design your level in the editor
2. Press `S` to get the level code
3. Copy the generated `LevelData` code
4. Open `src/levels.py`
5. Paste it into the `_create_levels()` method
6. Add it to the return list

```python
# Example in src/levels.py
def _create_levels():
    level_1 = LevelData(
        candy_pos=(600, 450),
        anchors=[...],
        target=...
    )

    your_level = LevelData(
        candy_pos=(600, 400),
        anchors=[(700, 600, 'A'), (500, 600, 'B')],
        ...
    )

    return [level_1, level_2, your_level]
```

---

## 🏗️ Architecture

### Project Structure

```
cut-the-rope/
├── src/
│   ├── config.py          # Game configuration & constants
│   ├── entities.py        # Entity classes (Candy, Rope, etc.)
│   ├── game.py            # Main game loop & state management
│   ├── levels.py          # Level definitions
│   ├── physics.py         # Pymunk physics engine wrapper
│   ├── renderer.py        # Pygame rendering
│   ├── ui.py              # UI components & menus
│   └── utils.py           # Utility functions
├── level_editor.py        # Visual level editor
├── run.py                 # Game entry point
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── cut-the-rope-presentation.html  # Game Design Analysis
```

### Technical Details

#### Physics Engine (Pymunk)
- **Gravity**: -900 px/s² (downward acceleration)
- **Sub-stepping**: 4 physics steps per frame for stability
- **Rope Simulation**: PinJoint constraints with damping
- **Collision**: Category-based collision filtering

#### Coordinate Systems
- **Pymunk**: Bottom-left origin (Y increases upward)
- **Pygame**: Top-left origin (Y increases downward)
- **Conversion**: `pygame_to_pymunk()` and `pymunk_to_pygame()` utilities

#### Rope Cutting Algorithm
```python
def line_segment_intersection(p1, p2, p3, p4):
    """Check if line segment (p1,p2) intersects (p3,p4)"""
    # Uses standard line intersection formula
    # Returns True if lines cross, False otherwise
```

#### Win Detection
1. Collision sensor detects candy entering target
2. Timer starts when candy is inside
3. Candy must have velocity < 80 px/s (settled)
4. Win after 2 seconds of continuous settlement

---

## 🎨 Game Design

This game was developed as part of a Game Design course, analyzing core game design principles:

- **MDA Framework**: Mechanics → Dynamics → Aesthetics
- **Bartle Player Types**: Targeted at Achievers & Explorers
- **Flow Theory**: Progressive difficulty maintains player engagement
- **Schema Theory**: Teaching patterns through level progression

View the full [Game Design Analysis Presentation](cut-the-rope-presentation.html) for an in-depth look at the design decisions behind Cut The Rope.

---

## 🧪 Testing

Run the test suite:

```bash
python -m pytest uniTest/
```

Or run specific tests:
```bash
python -m pytest uniTest/test_physics.py -v
```

---

## 📚 Dependencies

| Package | Version | Description |
|---------|---------|-------------|
| **pygame-ce** | ≥2.4.1 | Modern Python game library |
| **pymunk** | ≥6.5.0 | 2D physics engine based on Chipmunk |

---

## 🤝 Contributing

Contributions are welcome! Feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Ideas for Contributions

- 🌟 New levels (easy, medium, hard)
- 🎨 New visual themes or skins
- 🚧 New obstacle types (springs, fans, teleports)
- 🏆 Achievement system
- 📊 Level statistics and analytics
- 🎵 Sound effects and music

---

## 👥 Team

**Developed by:**
- **Muhammad Yaseen** 
- **Hevar Hemin** 
- **Revar Azim**

**Supervisor:** Mrs. Rina D. Zarro

**Course:** Game Design - University of Salahaddin - Erbil

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

- **Pymunk** - Excellent 2D physics engine
- **Pygame-ce** - Modern community-driven Pygame fork
- **Cut the Rope** (ZeptoLab) - Inspiration for this project
- Game Design course materials and lectures

---

<div align="center">

**Enjoy the game! 🎮**

[Report Bug](../../issues) • [Request Feature](../../issues) • [Game Design Presentation](cut-the-rope-presentation.html)

</div>
