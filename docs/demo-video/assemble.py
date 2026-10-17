import json, subprocess
from pathlib import Path
D = Path("scratch/demovid"); W = D / "work"; W.mkdir(exist_ok=True)
S = {s["id"]: s for s in json.load(open(D / "script.json"))}
GAP = 0.35
def proj(pid): return json.load(open(f"data/projects/{pid}/project.json"))
H, F, T, V = proj("0846ab6934"), proj("a834483018"), proj("23aebfb0d5"), proj("ade6d28b73")
hormuz_final = "data/projects/0846ab6934/out/the_bottleneck_of_the_world.mp4"
vaccine_final = V["render_path"]
CREAM = "0xf4f3ef"
def run(c): subprocess.run([str(x) for x in c], check=True, capture_output=True)
def seg(src, start, dur, out, fit="cover"):
    vf = ("scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080" if fit == "cover"
          else f"scale=-2:1000,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color={CREAM}")
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}", "-i", src, "-t", f"{dur:.3f}", "-an",
         "-vf", vf + ",fps=30,format=yuv420p,tpad=stop_mode=clone:stop_duration=5", "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", out])
    return out
def cat(parts, out):
    lst = W / (Path(out).stem + ".txt"); lst.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in parts))
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out]); return out
dur = {k: v["dur"] + GAP for k, v in S.items()}
rec = lambda n: str(D / "rec" / f"{n}.webm")
proj_ids = json.load(open(D / "ids.json"))
TS, HI = proj(proj_ids["tsunami"]), proj(proj_ids["hindi"])
secs = []
secs.append(seg(hormuz_final, 0, dur["s1_hook"], W / "s1.mp4"))
for n in ["s2_problem", "s3_ask", "s4_director"]:
    secs.append(seg(rec(n), 2.0, dur[n], W / f"{n}.mp4"))
# looks: the grid, then the same engines in two looks
d5 = dur["s5_looks"]; g = 4.2; r = (d5 - g) / 2
ts_wave = [s for s in TS["scenes"] if s["engine"] == "veo"][0]
secs.append(cat([seg(rec("s5_looks"), 2.0, g, W / "s5la.mp4"), seg(ts_wave["clip"], 0.5, r, W / "s5lb.mp4"),
                 seg(vaccine_final, 12.0, r, W / "s5lc.mp4", fit="pad")], W / "s5l.mp4"))
# cast: UI clicks, then the same ship across beats
d5 = dur["s5_cast"]; ui = 5.6; rest = (d5 - ui) / 3
img = next(s for s in T["scenes"] if s["engine"] == "image"); veos = [s for s in T["scenes"] if s["engine"] == "veo"]
secs.append(cat([seg(rec("s5_cast"), 2.0, ui, W / "s5a.mp4"), seg(img["clip"], 0.5, rest, W / "s5b.mp4"),
                 seg(veos[0]["clip"], 0.3, rest, W / "s5c.mp4"), seg(veos[1]["clip"], 0.3, rest, W / "s5d.mp4")], W / "s5.mp4"))
# engines montage: motion scene, Manim, globe, chart, flow
d6 = dur["s6_engines"] / 5
manim = [s for s in F["scenes"] if s["engine"] == "manim"][0]; globe = [s for s in H["scenes"] if s["engine"] == "globe"][1]
ts_scene = [s for s in TS["scenes"] if s["engine"] == "scene"][0]
secs.append(cat([seg(ts_scene["clip"], 0.5, d6, W / "s6a.mp4"), seg(manim["clip"], 0.8, d6, W / "s6b.mp4"),
                 seg(globe["clip"], 1.5, d6, W / "s6c.mp4"), seg("scratch/eng2/chart_bar_16x9/clip.mp4", 0.5, d6, W / "s6d.mp4"),
                 seg("scratch/eng2/flow_16x9/clip.mp4", 2.0, d6, W / "s6e.mp4")], W / "s6.mp4"))
secs.append(seg(rec("s7_edit"), 2.0, dur["s7_edit"], W / "s7.mp4"))
# translation: Hindi title, Hindi map, a reused picture beat
d8 = dur["s8_translate"] / 3
hs = HI["scenes"]
secs.append(cat([seg(hs[0]["clip"], 1.0, d8, W / "s8a.mp4"), seg(hs[1]["clip"], 2.0, d8, W / "s8b.mp4"),
                 seg(HI["render_path"], 31.0, d8, W / "s8c.mp4")], W / "s8.mp4"))
secs.append(seg(rec("s9_results"), 2.0, dur["s9_results"], W / "s9r.mp4"))
secs.append(seg(rec("s9_close"), 2.0, dur["s9_close"], W / "s9.mp4"))
run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", "scratch/deck/slide_13.png", "-t", "3.2",
     "-vf", "scale=1920:1080,fade=t=in:d=0.5,fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", W / "end.mp4"])
secs.append(W / "end.mp4")
video = cat(secs, W / "video.mp4")
# narration: each line padded to its section length
padded = []
for i, k in enumerate(S):
    extra = 3.2 if k == "s9_close" else 0
    o = W / f"n_{k}.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", D / f"{k}.wav", "-af", f"apad=whole_dur={dur[k] + extra:.3f}", "-ar", "48000", "-ac", "1", o]); padded.append(o)
lst = W / "voice.txt"; lst.write_text("".join(f"file '{p.resolve()}'\n" for p in padded))
run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c:a", "pcm_s16le", W / "voice.wav"])
total = sum(dur.values()) + 3.2
music = "data/projects/23aebfb0d5/music.mp3"
run(["ffmpeg", "-y", "-v", "error", "-i", W / "voice.wav", "-stream_loop", "-1", "-i", music, "-filter_complex",
     f"[1:a]aresample=48000,volume=-23dB,afade=t=in:d=1.5,afade=t=out:st={total - 2.5:.2f}:d=2.5[m];[0:a]aresample=48000[v];"
     f"[v][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11", "-t", f"{total:.3f}", "-ar", "48000", W / "mix.wav"])
out = D / "MitraField_Demo.mp4"
run(["ffmpeg", "-y", "-v", "error", "-i", video, "-i", W / "mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
     "-shortest", "-movflags", "+faststart", out])
print(out, total)
