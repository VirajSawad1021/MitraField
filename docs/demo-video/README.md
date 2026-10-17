# Demo video

`MitraField_Demo.mp4` (1:48, under the 3-minute limit) is the submission demo.

It is built without any generative API calls: the narration is the local Johnny voice,
the picture is Playwright recordings of the real app plus clips of videos MitraField rendered.

```bash
# from the repo root, with the app running on :8020
.venv/bin/python -c "..."            # voice script.json lines (see tts.synth), writes scratch/demovid/*.wav
python docs/demo-video/record.py <titanic-project-id>   # record app sections (Playwright)
python docs/demo-video/assemble.py                      # cut, mix and export
```
