# Recording protocol: one session that gives a realistic, measured scene (NEW 2026-10-06)

Goal: your next clip should carry its own metric ruler and a measured scene, so the robots copy YOUR task geometry and no scale has to be assumed. About one hour of work.

## 1. Before you record (15 minutes)
1. **Print the marker**: `deliverables/TransferGap_marker_12cm.pdf`, at 100% / actual size (no "fit to page"). Check with a ruler: the black square must be **12.0 cm** and the bar **10.0 cm**. If not, reprint; do not guess.
2. **Tape-measure and write down** (metres, e.g. 30 cm = 0.30):
   - the object you pick up: length, width, height; its weight if you have a scale (optional);
   - the target you place it in (box, plate, tray): INNER length and width, and the height of its walls;
   - the **centre-to-centre distance** between the object's start position and the centre of the target (this is the check on the video-derived distance);
   - table height above the floor; camera height and distance from the table edge;
   - **your shoulder width** (bone to bone across the back, in cm) and height.
3. Fill `transfergap/configs/twin_template.json` with those numbers (the template refuses to load until every `FILL_ME` is replaced). Positions `xy_m` are centres in a table frame you choose: x along one table edge, y along the other, measured from one corner.

## 2. Set up the scene
- **Camera fixed** on a tripod, no zoom, no auto-reframing, **1080p at 30 fps** (the old clip is 21.4 fps; fix the rate), landscape, upper body AND the whole table in view, as in your first clip.
- **Marker flat on the table**, in view for the whole clip, not under any object, not moved between takes. A second marker is welcome.
- Same lighting for every take; avoid strong backlight.

## 3. Record
- Start each take with **3 seconds of stillness**: arms down, marker visible, nothing moving (used for calibration).
- Then the task, **10 repetitions per condition**: slow, normal, fast; start from the left and from the right; right hand and left hand if you can. If other people are available: at least 3 people, each in the same set-up (everyone gives their own shoulder width).
- Say nothing needs to be edited: keep one file per take, named `person_object_speed_rep.mp4`.
- Different objects (box, cup, tool) are valuable but record the measured numbers for each.

## 4. After recording (done on the cluster, by the agent)
```
rtmw3d_export_joints.py  ->  pose.npz (kp2d + 3D)
python -m transfergap.human.marker detect --video clip.mp4 --size-cm 12                       # is the marker found? reprojection error?
python -m transfergap.human.twin_from_video --video clip.mp4 --pose pose.npz --events G R ... --tape-distance-cm D --out twin.json
python -m transfergap.pipeline --video clip.mp4 --scene twin.json --scale-from scene ...        # robots do YOUR geometry
```
`twin_from_video` prints the video-derived carry distance next to your tape number: if they differ by more than a few per cent the camera is not what we assumed (we give it a field of view of 70 degrees) and we calibrate it with a checkerboard.

## 5. Why each item
| You provide | It replaces | Without it |
|---|---|---|
| marker of known size | the assumed shoulder width and the guessed camera pose | every length is off by the unknown scale (it was 2.6x on the first clip) |
| object and target sizes | the 4 cm red cube and the green tray | the result describes a task you did not do (the container height and the object size changed outcomes from 35 to 7 of 60) |
| centre-to-centre tape distance | nothing, it is a check | no way to know whether the video geometry is right |
| 3 seconds of stillness | a neutral pose for calibration | the live G1 mode cannot calibrate cleanly |
| several people, 10 reps | a single clip as evidence | no statement beyond one person |
