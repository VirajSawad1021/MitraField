"""The automatic quality check: ffmpeg technical checks, the report shape, and the fix endpoint.
Gemini is never called: the beat reviewer is replaced with a stub."""
import subprocess

from fastapi.testclient import TestClient

from backend import app as appmod
from backend import jobs, qa, store

client = TestClient(appmod.app)


def make_video(path, seconds=4.0, black_from=None):
    """A test-pattern video with a tone; optionally a black stretch in the middle."""
    vf = "testsrc2=size=320x180:rate=30"
    if black_from is not None:
        vf += f",drawbox=t=fill:c=black:enable='between(t,{black_from},{black_from + 2})'"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", vf, "-f", "lavfi", "-i", "sine=frequency=330",
                    "-t", str(seconds), "-af", "volume=-14dB", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)],
                   check=True)
    return path


def check(results, name):
    return next(c for c in results if c["check"] == name)


def test_technical_checks_pass_on_a_clean_video(tmp_path):
    r = qa.technical(make_video(tmp_path / "ok.mp4"), 4.0)
    assert check(r, "length")["ok"] and check(r, "black frames")["ok"] and check(r, "silence gaps")["ok"]


def test_technical_checks_catch_black_frames_and_wrong_length(tmp_path):
    r = qa.technical(make_video(tmp_path / "bad.mp4", seconds=6.0, black_from=2.0), 4.0)
    assert not check(r, "black frames")["ok"]
    assert not check(r, "length")["ok"]


def test_fix_brief_replaces_the_previous_note():
    once = qa.fix_brief("A map of the Gulf.", [{"kind": "text_overlap", "detail": "Labels overlap the pipeline"}])
    assert once == "A map of the Gulf. Fix from review: Labels overlap the pipeline."
    twice = qa.fix_brief(once, [{"kind": "layout", "detail": "Title is cut off."}])
    assert twice == "A map of the Gulf. Fix from review: Title is cut off."


def finished(project, tmp_path):
    d = store.pdir(project.id) / "out"
    d.mkdir(parents=True, exist_ok=True)
    final = make_video(d / "video_final.mp4", seconds=6.0)

    def f(p):
        p.render_path, p.render_status = str(final), "done"
        for s in p.scenes:
            s.clip, s.duration = str(final), 2.0
    return store.mutate(project.id, f)


def test_run_saves_a_report_and_flags_major_issues_only(project, tmp_path, monkeypatch):
    finished(project, tmp_path)
    verdicts = {"s0": [], "s1": [{"kind": "garbled_text", "severity": "major", "detail": "Sign has fake text"}],
                "s2": [{"kind": "layout", "severity": "minor", "detail": "Slightly low contrast"}]}
    monkeypatch.setattr(qa, "review_beat", lambda p, s, i: {"ok": not [x for x in verdicts[s.id] if x["severity"] == "major"],
                                                            "issues": verdicts[s.id]})
    r = qa.run(project.id)
    assert r["status"] == "flagged" and r["flagged"] == ["s1"]
    assert store.load(project.id).qa["flagged"] == ["s1"]
    assert (store.pdir(project.id) / "out" / "contact_sheet.jpg").exists()
    body = client.get(f"/api/projects/{project.id}").json()
    assert body["qa"]["sheet_url"].endswith("contact_sheet.jpg") and body["qa"]["stale"] is False


def test_fix_folds_issues_into_the_brief_and_rerenders(project, tmp_path, monkeypatch):
    finished(project, tmp_path)
    got = []
    monkeypatch.setattr(jobs, "enqueue", lambda kind, **p: got.append((kind, p)))
    store.mutate(project.id, lambda p: setattr(p, "qa", {"status": "flagged", "flagged": ["s1"], "beats": {
        "s1": {"ok": False, "issues": [{"kind": "text_overlap", "severity": "major", "detail": "Titles overlap"}]}}}))
    r = client.post(f"/api/projects/{project.id}/scenes/s1/fix")
    assert r.status_code == 200
    s1 = store.scene(store.load(project.id), "s1")
    assert "Fix from review: Titles overlap." in s1.brief and s1.status == "queued"
    assert got == [("render_scene", {"pid": project.id, "sid": "s1", "force": True, "then_assemble": True})]
    assert client.post(f"/api/projects/{project.id}/scenes/s0/fix").status_code == 400   # nothing to fix there
