"""Annotated real human demo clips: source, licence, and the pick-and-place cycle used (events annotated by
inspecting video frames; they are an input to segmentation, not a measured result)."""

CLIPS = {
    "pexels_8135753_notebook": {
        "video": "demo_input/pexels_8135753_packing_box.mp4",
        "source_url": "https://www.pexels.com/video/man-packing-his-things-in-a-box-for-being-fired-from-work-8135753/",
        "license": "Pexels License (free use incl. commercial, modification allowed)",
        "fps": 25.0,
        "side": "Right",
        "window": [195, 249],
        "events": {"grasp": 212, "release": 233},
        "description": "picks a notebook up from the desk with the right hand, lifts it over the box rim and drops it "
                       "into the box; static front camera",
        "annotation": "grasp = first frame the notebook leaves the desk; release = first frame it falls free "
                      "inside the box; annotated by frame inspection (3-frame sampling, +/- 3 frames)",
    },
    "pexels_8135753_markers": {
        "video": "demo_input/pexels_8135753_packing_box.mp4",
        "source_url": "https://www.pexels.com/video/man-packing-his-things-in-a-box-for-being-fired-from-work-8135753/",
        "license": "Pexels License (free use incl. commercial, modification allowed)",
        "fps": 25.0,
        "side": "Right",
        "window": [90, 140],
        "events": {'grasp': 106, 'release': 127},
        "description": "grabs several markers from the desk and drops them into the box",
        "annotation": "frame-inspected at 4-frame sampling (+/- 4 frames); annotated 2026-10-02 after the notebook experiments",
    },
    "pexels_8135753_orange_marker": {
        "video": "demo_input/pexels_8135753_packing_box.mp4",
        "source_url": "https://www.pexels.com/video/man-packing-his-things-in-a-box-for-being-fired-from-work-8135753/",
        "license": "Pexels License (free use incl. commercial, modification allowed)",
        "fps": 25.0,
        "side": "Right",
        "window": [134, 170],
        "events": {'grasp': 148, 'release': 159},
        "description": "picks one orange marker and flicks it into the box",
        "annotation": "frame-inspected at 4-frame sampling (+/- 4 frames); annotated 2026-10-02 after the notebook experiments",
    },
    "pexels_8135753_notepad": {
        "video": "demo_input/pexels_8135753_packing_box.mp4",
        "source_url": "https://www.pexels.com/video/man-packing-his-things-in-a-box-for-being-fired-from-work-8135753/",
        "license": "Pexels License (free use incl. commercial, modification allowed)",
        "fps": 25.0,
        "side": "Right",
        "window": [162, 200],
        "events": {'grasp': 179, 'release': 191},
        "description": "picks a yellow notepad from the desk and tosses it into the box",
        "annotation": "frame-inspected at 4-frame sampling (+/- 4 frames); annotated 2026-10-02 after the notebook experiments",
    },
    "pexels_7205253_woman_box": {
        "video": "demo_input/pexels_7205253_woman_box.mp4",
        "source_url": "https://www.pexels.com/video/woman-carrying-a-box-7205253/",
        "license": "Pexels License (free use incl. commercial, modification allowed)",
        "fps": 25.0,
        "side": "both",
        "window": [12, 140],
        "events": {"grasp": 38, "release": 122},
        "description": "a different person (woman) lifts a box off a stack with both hands, walks a few steps and "
                       "sets it on another box; the camera pans while she walks (this GEM-X release has no visual odometry and "
                       "falls back to a static camera, so the pan adds error to her world trajectory)",
        "annotation": "frame-inspected at 6-frame sampling (+/- 6 frames); annotated 2026-10-02",
        "object_height": "hand_at_grasp",
    },
    "user_take1_right": {
        "video": "runs/videos/user_take1_21fps.mp4",
        "source_url": "recorded by the project author (private; never committed or published)",
        "license": "private recording of the author; not redistributed",
        "fps": 21.4,
        "side": "Right",
        "window": [820, 966],
        "events": {"grasp": 862, "release": 926},
        "description": "the author picks a small box off a table with the right hand and lowers it into a black box; "
                       "static Logitech Brio 100 camera, 1280x720",
        "annotation": "frame-inspected at 6-frame sampling (+/- 6 frames); annotated 2026-10-02",
    },
}
