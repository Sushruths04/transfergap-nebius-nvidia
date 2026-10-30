# Apple-shaped object (sphere), object_apple_v1, laptop CPU

Same method as `object_scale_v1` (same clip, 60 held-out seeds, frozen five-fix stack, MuJoCo 3.14.0 physics), but the object is a SPHERE (`TG_OBJECT=apple`, `scene.py`) of diameter 6 and 7 cm (radius 3.0 and 3.5 cm; an apple is about 7-8 cm). Exploratory, simulation only; the object is rigid with the same density rule as the cube, no stem or deformation, and the fix stack was never tuned for spheres.

| diameter | UR5e raw -> fixes | UR10e raw -> fixes | KAIROS raw -> fixes |
|---|---|---|---|
| 6 cm | 3 -> 44 | 5 -> 55 | 36 -> 60 |
| 7 cm | 0 -> 28 | 1 -> 52 | 40 -> 60 |

Reading: a sphere is harder than a cube for the UR arms (UR5e 28/60 at 7 cm vs 47/60 for the cube; its 8.5 cm gripper opening leaves little margin and a round object rolls), KAIROS (12.8 cm opening) is unaffected. The raw copy fails almost always on the UR arms. No intervals computed here (60 seeds per cell).
