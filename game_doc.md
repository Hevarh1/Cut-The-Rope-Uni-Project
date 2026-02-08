Game Design Document: Cut The Rope

1. Overview

Title: Cut The Rope Genre: Physics Puzzle Core Mechanic: The player cannot control the object directly. They interact by removing constraints (cutting ropes) to let gravity and momentum guide the object to the goal. Tech Stack: Python, pygame-ce, and pymunk (essential for physics). 2. Technical Architecture

    Physics Engine: pymunk. This library handles gravity, collisions, and—most importantly—PinJoints (which act as ropes).

    Rendering: Pygame draws the Pymunk bodies.

        Coordinate Conversion: Pymunk uses (x, y) starting from the bottom-left. Pygame uses top-left. The Agent must include a conversion function.

3.  Game Rules & Mechanics
    A. The Goal

        Primary Goal: Guide the Candy (a ball) into the Delivery Box (Target Zone).

        Win Condition: The Candy stays inside the Delivery Box for 2 seconds (settles).

        Fail Condition: The Candy falls off the screen or touches a "Spike" hazard.

B. The Ropes (Constraints)

    The Candy hangs from one or more Anchors via ropes.

    Physics: These are pymunk.PinJoints. They have a fixed length but allow the candy to swing freely like a pendulum.

    Visual: Drawn as a simple line from the Anchor to the Candy.

C. The Interaction (The Knife)

    Input: Mouse Drag.

    Mechanism: When the player holds the left mouse button and moves the mouse, it draws a "Slash Line" (trail).

    Cutting Logic: If the Slash Line intersects with a Rope Line, that Rope (Joint) is immediately destroyed (space.remove(joint)).

D. Game Objects

    Candy: Dynamic Body (has mass and inertia). Bounces slightly.

    Anchor: Static Body (fixed in space). The rope ties to this.

    Obstacles: Static platforms (wood/metal) that the candy can bounce off.

    Blower (Auxiliary): An air cushion that pushes the candy if clicked (adds a force vector).

4.  Level Progression (Example)

    Level 1: Single rope directly above the box. Cut rope -> Falls straight down.

    Level 2: Two ropes holding the candy. Cut left rope -> Candy swings right -> Cut right rope at the apex of the swing -> Candy arcs into the box.

    Level 3: Obstacles block the direct path. Player must swing the candy to hit a wall, bounce off, and then cut.

5.  Visual Style

    Ropes: Brown or Black lines.

    Candy: Red ball.

    Target: Green open-top box.

    Cut Trail: White fading line (like a sword slash).

6.  Implementation Steps for the Agent
    Step 1: Pymunk Setup

        Initialize pymunk.Space. Set Gravity to (0, 900).

        Create a generic function create_structure(x, y) to build walls.

Step 2: The Rope Logic

    The Agent needs to store Ropes in a list: ropes = [{'joint': joint_obj, 'start': anchor_body, 'end': candy_body}, ...].

    This is crucial because you need the coordinates of the start and end points to detect if the mouse crossed the line.

Step 3: The Cutting Algorithm (Line Intersection)

    Use a standard "Line Segment Intersection" formula.

    Check if Segment(Mouse_Start, Mouse_End) intersects Segment(Rope_Start, Rope_End).

    If True: Remove the joint from the physics space and delete it from the list.

Step 4: Win Detection

    Create a Sensor (Collision Handler) in the box.

    If Candy touches Sensor: Start a timer. If timer > 2s, Level Complete.
