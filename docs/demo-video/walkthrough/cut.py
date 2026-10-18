import json, subprocess
from pathlib import Path
W = Path("."); OUT = W / "cut"; OUT.mkdir(exist_ok=True)
vo = json.load(open("vo.json")); GAP = 0.45
P = json.load(open("/home/one-point/lab/AI_Content/aibuildercup/data/projects/" + open("pid.txt").read().strip() + "/project.json"))
FINAL = P["render_path"].replace("${DATA}", "/home/one-point/lab/AI_Content/aibuildercup/data/projects"); MUSIC = str(Path(FINAL).parents[1] / "music.mp3")
def run(c): subprocess.run([str(x) for x in c], check=True, capture_output=True)
def piece(src, a, b, dur, out):
    """src[a:b] retimed to exactly dur seconds (time-lapse or slow), 1080p30, no audio."""
    k = dur / (b - a)
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", f"{a:.2f}", "-t", f"{b - a:.2f}", "-i", src, "-an",
         "-vf", f"setpts={k:.5f}*PTS,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0xf4f3ef,fps=30,format=yuv420p,tpad=stop_mode=clone:stop_duration=3",
         "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", out]); return out
def cat(parts, out):
    l = OUT / (Path(out).stem + ".txt"); l.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in parts))
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", l, "-c", "copy", out]); return out
d = {k: v["dur"] + GAP for k, v in vo.items()}
S, T = "session.webm", "tour.webm"
segs = [
 ("v1", [(S, 1.4, 6.9)]),
 ("v2", [(S, 7.0, 17.4)]),
 ("v3", [(S, 17.4, 70.0, 0.35), (S, 70.0, 90.0, 0.65)]),          # directing time-lapse, then the storyboard
 ("v4", [(S, 119.0, 133.0)]),                                       # fact check card
 ("v5", [(S, 134.0, 139.5, 0.6), (S, 228.0, 238.0, 0.4)]),          # instruction, then the redrawn beat
 ("v6", [(S, 239.0, 681.0)]),                                       # render time-lapse
 ("v7", [(T, 3.6, 17.1)]),                                          # quality check, flagged beat, Fix
 ("v8", [(T, 17.1, 25.6)]),                                         # fact check after render
]
clips = []
for k, parts in segs:
    tot = d[k]; out = []
    for i, p in enumerate(parts):
        src, a, b = p[:3]; share = p[3] if len(p) > 3 else 1.0
        out.append(piece(src, a, b, tot * share, OUT / f"{k}_{i}.mp4"))
    clips.append(cat(out, OUT / f"{k}.mp4") if len(out) > 1 else out[0])
# result: v9 then the finished video with its own sound
RES = 14.0
res = OUT / "res.mp4"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", FINAL, "-t", f"{RES}", "-vf", "scale=1920:1080,fps=30,format=yuv420p",
     "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-an", res]); clips.append(res)
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-loop", "1", "-i", "/tmp/claude-1000/-home-one-point-lab-AI-Content/060eef8b-0d11-4ccf-83d0-c8905c6faf6c/scratchpad/deck/slide_14.png",
     "-t", f"{d['v10'] + 1.5:.2f}", "-vf", "scale=1920:1080,fade=t=in:d=0.5,fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", OUT / "end.mp4"])
clips.append(OUT / "end.mp4")
video = cat(clips, OUT / "video.mp4")
# narration track: each VO padded to its section, silence over the result (its own audio goes there)
order = ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8"]
pads = []
for k in order:
    o = OUT / f"n_{k}.wav"; run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", f"{k}.wav", "-af", f"apad=whole_dur={d[k]:.3f}", "-ar", "48000", "-ac", "1", o]); pads.append(o)
# result section: v9 over the first seconds, then the video's own audio rises
o = OUT / "n_res.wav"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", "v9.wav", "-ss", "0", "-t", f"{RES}", "-i", FINAL, "-filter_complex",
     f"[0:a]aresample=48000,apad=whole_dur={RES}[v];[1:a]aresample=48000,pan=mono|c0=c0,volume='if(lt(t,1.6),0.15,1)':eval=frame[f];[v][f]amix=inputs=2:duration=longest:normalize=0",
     "-t", f"{RES}", "-ac", "1", o]); pads.append(o)
o = OUT / "n_end.wav"; run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", "v10.wav", "-af", f"apad=whole_dur={d['v10'] + 1.5:.3f}", "-ar", "48000", "-ac", "1", o]); pads.append(o)
l = OUT / "voice.txt"; l.write_text("".join(f"file '{p.resolve()}'\n" for p in pads))
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", l, "-c:a", "pcm_s16le", OUT / "voice.wav"])
total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", OUT / "voice.wav"], capture_output=True, text=True).stdout)
res_at = sum(d[k] for k in order)
# low music bed, ducked out while the finished video plays
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", OUT / "voice.wav", "-stream_loop", "-1", "-i", MUSIC, "-filter_complex",
     f"[1:a]aresample=48000,volume=-25dB,volume='if(between(t,{res_at:.2f},{res_at + RES:.2f}),0,1)':eval=frame,afade=t=in:d=1.5,afade=t=out:st={total - 2.5:.2f}:d=2.5[m];"
     f"[0:a]aresample=48000[v];[v][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11",
     "-t", f"{total:.3f}", "-ar", "48000", OUT / "mix.wav"])
final = W / "MitraField_Walkthrough.mp4"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", video, "-i", OUT / "mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "24",
     "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", final])
print(final, round(total, 1))
