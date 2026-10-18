# Walkthrough demo (submission video)

`../MitraField_Walkthrough.mp4` (1:41) is one real, unedited session in the app, narrated by Viraj (cloned voice):
topic + Direction ("mostly maps and data charts") + look -> the director's storyboard, which followed the
direction -> the automatic fact check (14 claims, Google Search sources) -> editing one beat in plain words ->
render -> the automatic quality check with a flagged beat and its Fix button -> the post-render fact check
catching one claim -> the finished video with its own narration.

Long waits (directing, rendering) are time-lapsed; nothing else is staged.

- `session.py` drives the real app with Playwright and records it, logging the time of every step
- `vo.json` is the voiceover script with measured line lengths
- `cut.py` retimes each recorded moment to its voiceover line and mixes voice, a low music bed and the result's own sound
