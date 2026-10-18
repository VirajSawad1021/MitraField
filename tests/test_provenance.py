import subprocess

import pytest
from fastapi.testclient import TestClient

from backend import app as appmod
from backend import config, jobs, provenance

client = TestClient(appmod.app)
MARK = 0xA1B2C3D4


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, args)], check=True, timeout=180)


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setattr(config, "WATERMARK_KEY", "test-watermark-key")
    for f in (provenance._key, provenance.patterns, provenance.sequence):
        f.cache_clear()
    yield
    for f in (provenance._key, provenance.patterns, provenance.sequence):
        f.cache_clear()


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    """A 10 s textured clip with silent audio, and the same clip carrying the mark."""
    d = tmp_path_factory.mktemp("wm")
    ff("-f", "lavfi", "-i", "gradients=size=640x360:rate=30:duration=10:speed=0.02:c0=0x1d2a3a:c1=0xe8dfc8", "-c:v", "libx264", "-crf", 14, d / "src.mp4")
    ff("-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", 10, d / "a.wav")
    return d


@pytest.fixture
def marked(source, monkeypatch):
    monkeypatch.setattr(config, "WATERMARK_KEY", "test-watermark-key")
    provenance.embed(source / "src.mp4", source / "a.wav", source / "marked.mp4", MARK)
    return source / "marked.mp4"


def test_mark_survives_reencoding_and_rescaling(marked, source):
    d = provenance.detect(marked)
    assert d.found and d.mark_id == MARK and d.offset == 0
    ff("-i", marked, "-vf", "scale=480:270", "-c:v", "libx264", "-crf", 28, "-an", source / "small.mp4")
    d = provenance.detect(source / "small.mp4")
    assert d.found and d.mark_id == MARK


def test_mark_is_found_in_a_trimmed_copy(marked, source):
    ff("-ss", 2, "-i", marked, "-c:v", "libx264", "-crf", 26, "-an", source / "trim.mp4")
    d = provenance.detect(source / "trim.mp4")
    assert d.found and d.mark_id == MARK and abs(d.offset - 60) <= 1


def test_unmarked_video_and_wrong_key_find_nothing(marked, source, monkeypatch):
    assert not provenance.detect(source / "src.mp4").found
    monkeypatch.setattr(config, "WATERMARK_KEY", "someone-elses-key")
    for f in (provenance._key, provenance.patterns, provenance.sequence):
        f.cache_clear()
    assert not provenance.detect(marked).found


def test_the_mark_is_faint(marked, source):
    out = subprocess.run(["ffmpeg", "-i", marked, "-i", source / "src.mp4", "-lavfi", "psnr", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    assert float(out.split("average:")[1].split()[0]) > 38   # dB; below this the grain starts to show


def test_verify_reports_exact_file_mark_and_nothing(marked, source, project):
    provenance.register(project, MARK, marked)
    assert provenance.verify(marked)["verdict"] == "exact"
    ff("-i", marked, "-c:v", "libx264", "-crf", 28, "-an", source / "re.mp4")
    r = provenance.verify(source / "re.mp4")
    assert r["verdict"] == "mark" and r["origin"]["project"] == project.id and not r["trimmed"]
    assert provenance.verify(source / "src.mp4")["verdict"] == "none"


def test_a_valid_mark_that_was_never_registered_is_not_ours(marked):
    assert provenance.verify(marked)["verdict"] == "none"


def test_missing_key_in_the_cloud_is_an_error(monkeypatch):
    monkeypatch.setattr(config, "WATERMARK_KEY", "")
    monkeypatch.setattr(config, "STORE", "firestore")
    provenance._key.cache_clear()
    with pytest.raises(provenance.WatermarkError):
        provenance._key()


def test_selftest_round_trip():
    assert provenance.selftest()


# ---- the Verify API: pieces in, job, verdict out

def upload(data: bytes, piece=1 << 20):
    vid = client.post("/api/verify").json()["id"]
    pieces = [data[i:i + piece] for i in range(0, len(data), piece)]
    for n, b in enumerate(pieces):
        assert client.post(f"/api/verify/{vid}/chunk/{n}", content=b).status_code == 200
    return vid, len(pieces)


def test_verify_flow_over_the_api(marked, project, monkeypatch):
    provenance.register(project, MARK, marked)
    monkeypatch.setattr(appmod, "PASSCODE", "s3cret")   # checking a video needs no passcode
    sent = []
    monkeypatch.setattr(jobs, "enqueue", lambda kind, **p: sent.append((kind, p)))
    data = marked.read_bytes()
    vid, n = upload(data)
    assert client.post(f"/api/verify/{vid}/finish", json={"chunks": n, "size": len(data)}).status_code == 200
    kind, payload = sent[0]
    assert kind == "verify" and payload == {"vid": vid, "chunks": n, "size": len(data)}
    jobs.run(kind, payload)
    r = client.get(f"/api/verify/{vid}").json()
    assert r["status"] == "done" and r["verdict"] == "exact" and r["origin"]["project"] == project.id
    assert not (config.DATA / "verify" / vid).exists()   # the upload is deleted once read


def test_verify_rejects_unknown_ids_and_bad_input(monkeypatch):
    assert client.post("/api/verify/aaaaaaaaaaaa/chunk/0", content=b"x").status_code == 404   # never started
    assert client.get("/api/verify/not-an-id").status_code == 404
    vid = client.post("/api/verify").json()["id"]
    assert client.post(f"/api/verify/{vid}/chunk/9999", content=b"x").status_code == 400
    assert client.post(f"/api/verify/{vid}/finish", json={"chunks": 9999, "size": 1}).status_code == 400
    monkeypatch.setattr(appmod, "CHUNK", 10)
    assert client.post(f"/api/verify/{vid}/chunk/0", content=b"x" * 11).status_code == 413


def test_verify_garbage_upload_is_a_friendly_error(monkeypatch):
    monkeypatch.setattr(jobs, "enqueue", lambda kind, **p: None)
    vid, n = upload(b"this is not a video" * 100)
    client.post(f"/api/verify/{vid}/finish", json={"chunks": n, "size": 1900})
    jobs.run("verify", {"vid": vid, "chunks": n, "size": 1900})
    r = client.get(f"/api/verify/{vid}").json()
    assert r["status"] == "error" and "video" in r["error"]


def test_verify_daily_cap(monkeypatch):
    monkeypatch.setattr(config, "VERIFY_DAY_CAP", 2)
    assert [client.post("/api/verify").status_code for _ in range(3)] == [200, 200, 429]


def test_the_upload_folder_is_not_served():
    (config.DATA / "verify").mkdir(parents=True, exist_ok=True)
    (config.DATA / "verify" / "x.part").write_bytes(b"secret")
    assert client.get("/files/verify/x.part").status_code == 404


def test_vertical_video_is_marked_and_read(source, monkeypatch):
    ff("-f", "lavfi", "-i", "gradients=size=360x640:rate=30:duration=8:speed=0.02:c0=0x1d2a3a:c1=0xe8dfc8", "-c:v", "libx264", source / "v.mp4")
    provenance.embed(source / "v.mp4", source / "a.wav", source / "vm.mp4", MARK)
    ff("-i", source / "vm.mp4", "-c:v", "libx264", "-crf", 28, "-an", source / "vre.mp4")
    d = provenance.detect(source / "vre.mp4")
    assert d.found and d.mark_id == MARK
