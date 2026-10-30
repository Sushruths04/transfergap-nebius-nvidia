# TransferGap Console (demo UI)

A single-page console for presenting the project: pipeline, the person's measurements with a synced chart, the robots with and without
correction, the gap budget, the Nemotron diagnosis rounds, the Cosmos critic, the G1 mimic, an honest "not solved" panel and a labelled roadmap.

```
python ui_demo/build.py            # rebuilds data.js from the committed result files (no numbers are typed into the page)
bash ui_demo/fetch_media.sh        # copies the videos from the cluster (needs kubectl); media/ is not in git
python ui_demo/serve.py 8765       # then open http://127.0.0.1:8765/   (opening index.html from disk also works)
```
Offline, no dependencies, light and dark theme, `P` toggles presentation mode (arrow keys move between sections).

Verified: loads without console errors; charts, bars, tabs and the pipeline detail render (screenshots of the Overview, Person, Robots, Diagnosis, Critic and Humanoid sections checked in Chrome).
NOT verified: video playback in the browser (my test tab was hidden, so Chrome never loaded media); the videos themselves decode with OpenCV and the range server answers 206.
Shoulder width on the page is the DERIVED 0.44 m. The roadmap section is plans, not results.
