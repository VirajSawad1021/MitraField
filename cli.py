"""Headless end-to-end: python cli.py "topic" [short|medium|long] [16:9|9:16]"""
import sys
import time

from backend import director, pipeline, store
from backend.models import Project

topic = sys.argv[1]
p = Project(topic=topic, length=sys.argv[2] if len(sys.argv) > 2 else "short",
            aspect=sys.argv[3] if len(sys.argv) > 3 else "16:9")
t = time.time()
p = director.storyboard(p)
store.save(p)
print(f"[{time.time() - t:.0f}s] {p.id} '{p.title}'")
for i, s in enumerate(p.scenes):
    print(f"  {i + 1:2d} {s.engine:8s} {s.narration}")
pipeline.render_all(p.id)
p = store.load(p.id)
print(f"[{time.time() - t:.0f}s] {p.render_status} {p.render_path or p.render_error}")
for i, s in enumerate(p.scenes):
    if s.error:
        print(f"  scene {i + 1}: {s.error}")
