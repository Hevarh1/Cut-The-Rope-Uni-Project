#!/usr/bin/env python3
"""
Level validation script.
Checks every campaign level for common design problems.

Run:  python validate_levels.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from src.levels import LevelManager

CANDY_R = 14          # CANDY_RADIUS from config
MIN_TARGET_W = 100    # minimum target width to be comfortably visible
MIN_TARGET_H = 60     # minimum target height
MIN_TARGET_Y = 100    # target Y should be at least this (in pymunk coords)
MARGIN = 30           # objects should be at least this far from level edges

def validate():
    mgr = LevelManager()
    levels = mgr.campaign_levels
    all_ok = True

    for i, lv in enumerate(levels):
        errs = []
        warns = []
        W, H = lv.width, lv.height

        # --- Candy ---
        cx, cy = lv.candy_pos
        if cx < MARGIN or cx > W - MARGIN:
            errs.append(f"Candy X={cx} too close to edge (level W={W})")
        if cy < MARGIN or cy > H - MARGIN:
            errs.append(f"Candy Y={cy} too close to edge (level H={H})")

        # --- Target ---
        tx, ty = lv.target_pos
        tw, th = lv.target_size
        if tw < MIN_TARGET_W:
            warns.append(f"Target width {tw} < {MIN_TARGET_W} — hard to see/hit")
        if th < MIN_TARGET_H:
            warns.append(f"Target height {th} < {MIN_TARGET_H} — hard to see/hit")
        if ty < MIN_TARGET_Y:
            warns.append(f"Target Y={ty} very low — may be clipped at bottom")
        # Target box bounds
        t_left = tx - tw / 2
        t_right = tx + tw / 2
        t_bottom = ty - th / 2
        t_top = ty + th / 2
        if t_left < 0:
            errs.append(f"Target left edge {t_left:.0f} < 0 — off-screen")
        if t_right > W:
            errs.append(f"Target right edge {t_right:.0f} > {W} — off-screen")
        if t_bottom < 0:
            errs.append(f"Target bottom edge {t_bottom:.0f} < 0 — off-screen")

        # --- Can candy fit in target? ---
        if tw < CANDY_R * 2 + 6:
            errs.append(f"Target too narrow ({tw}) for candy diameter ({CANDY_R*2})")

        # --- Anchors ---
        for j, (ax, ay) in enumerate(lv.anchors):
            if ax < 0 or ax > W or ay < 0 or ay > H:
                errs.append(f"Anchor {j} ({ax},{ay}) out of bounds")
            if ay < cy:
                warns.append(f"Anchor {j} Y={ay} is BELOW candy Y={cy} — rope drags up?")

        # --- Platforms ---
        for j, (px, py, pw, ph) in enumerate(lv.platforms):
            if px < 0 or px + pw > W:
                warns.append(f"Platform {j} ({px},{py},{pw},{ph}) extends beyond X bounds")
            if py < 0 or py + ph > H:
                warns.append(f"Platform {j} ({px},{py},{pw},{ph}) extends beyond Y bounds")
            # Check if platform overlaps target
            p_left = px
            p_right = px + pw
            p_bottom = py
            p_top = py + ph
            if (p_left < t_right and p_right > t_left and
                p_bottom < t_top and p_top > t_bottom):
                warns.append(f"Platform {j} overlaps target area!")

        # --- Spikes ---
        for j, (sx, sy, sw, sh) in enumerate(lv.spikes):
            if sx < 0 or sx + sw > W:
                warns.append(f"Spike {j} ({sx},{sy},{sw},{sh}) extends beyond X bounds")
            if sy < 0 or sy + sh > H:
                warns.append(f"Spike {j} ({sx},{sy},{sw},{sh}) extends beyond Y bounds")
            # Check if spike overlaps target
            s_left = sx
            s_right = sx + sw
            s_bottom = sy
            s_top = sy + sh
            if (s_left < t_right and s_right > t_left and
                s_bottom < t_top and s_top > t_bottom):
                errs.append(f"Spike {j} overlaps target area — instant death!")

        # --- Magnet anchors ---
        if lv.magnet_anchors:
            for j, (mx, my, mr) in enumerate(lv.magnet_anchors):
                if mx - mr < -50 or mx + mr > W + 50:
                    warns.append(f"Magnet {j} radius extends far beyond X bounds")
                if my < 0 or my > H:
                    errs.append(f"Magnet {j} ({mx},{my}) out of Y bounds")

        # --- Slingshot pairs ---
        if lv.slingshot_pairs:
            for j, ((ax, ay), (bx, by)) in enumerate(lv.slingshot_pairs):
                for label, px, py in [("A", ax, ay), ("B", bx, by)]:
                    if px < 0 or px > W or py < 0 or py > H:
                        errs.append(f"Slingshot {j} point {label} ({px},{py}) out of bounds")

        # --- Vertical spread ---
        drop_dist = cy - ty
        if drop_dist < 400:
            warns.append(f"Only {drop_dist:.0f} px drop — doesn't use vertical space well")

        # --- Print results ---
        status = "✅" if not errs else "❌"
        if warns and not errs:
            status = "⚠️ "
        print(f"\n{'='*60}")
        print(f"Level {i+1}: \"{lv.name}\"  {status}")
        print(f"  Canvas: {W}×{H}  |  Candy: ({cx},{cy})  |  Target: ({tx},{ty}) {tw}×{th}")
        if errs:
            all_ok = False
            for e in errs:
                print(f"  ❌ ERROR:   {e}")
        if warns:
            for w in warns:
                print(f"  ⚠️  WARN:   {w}")
        if not errs and not warns:
            print(f"  ✅ All checks passed")

    print(f"\n{'='*60}")
    if all_ok:
        print("🎉 All levels passed validation!")
    else:
        print("⛔ Some levels have errors — please fix them.")

if __name__ == "__main__":
    validate()
