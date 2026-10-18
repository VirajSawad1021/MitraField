import os
import subprocess
import sys
import time

import pytest

from backend import sandbox

GOOD = '''from manim import *
import numpy as np
class Beat(Scene):
    def construct(self):
        c = Circle(color=BLUE)
        self.play(Create(c), run_time=1)
        self.wait(1)
'''


def test_accepts_ordinary_manim_code():
    assert sandbox.check(GOOD) is None


@pytest.mark.parametrize("code,fragment", [
    ("import os\n", "import of 'os'"),
    ("import subprocess\n", "subprocess"),
    ("from urllib import request\n", "urllib"),
    ("import requests\n", "requests"),
    ("x = open('/etc/passwd').read()\n", "open"),
    ("exec('1')\n", "exec"),
    ("eval('1')\n", "eval"),
    ("__import__('os')\n", "__import__"),
    ("import numpy as np\nnp.load('/data/x.npy')\n", "load"),
    ("x = ().__class__.__bases__\n", "is not allowed"),
    ("import math\nmath.__loader__\n", "__loader__"),
    ("getattr(object, 'x')\n", "getattr"),
    ("from manim import *\nImageMobject('/data/secret.png')\n", "ImageMobject"),
    ("def f(:\n", "syntax"),
])
def test_refuses_dangerous_code(code, fragment):
    assert fragment in (sandbox.check(code) or "")


def test_child_env_has_no_secrets(monkeypatch, tmp_path):
    for k in ("GEMINI_API_KEY", "STUDIO_PASSCODE", "GOOGLE_APPLICATION_CREDENTIALS", "AWS_SECRET_ACCESS_KEY", "GITHUB_TOKEN"):
        monkeypatch.setenv(k, "supersecret")
    env = sandbox.clean_env(tmp_path)
    assert "supersecret" not in " ".join(env.values())
    assert set(env) <= set(sandbox._ENV_ALLOW) | {"HOME", "TMPDIR", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH"}


def test_run_executes_in_clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "supersecret")
    r = sandbox.run([sys.executable, "-c", "import os; print(sorted(os.environ))"], cwd=tmp_path, timeout=30)
    assert r.returncode == 0 and "GEMINI_API_KEY" not in r.stdout


def test_timeout_kills_the_whole_process_group(tmp_path):
    marker = tmp_path / "child-survived"
    t0 = time.time()
    with pytest.raises(subprocess.TimeoutExpired):
        sandbox.run(["sh", "-c", f"(sleep 3; touch {marker}) & sleep 60"], cwd=tmp_path, timeout=1)
    assert time.time() - t0 < 10
    time.sleep(4)
    assert not marker.exists()


@pytest.mark.skipif(not sandbox.NET_ISOLATED, reason="host does not allow network namespaces")
def test_no_network_inside_sandbox(tmp_path):
    code = "import socket; socket.create_connection(('1.1.1.1', 53), timeout=3)"
    assert sandbox.run([sys.executable, "-c", code], cwd=tmp_path, timeout=20).returncode != 0


def test_environment_is_unchanged_by_running(tmp_path):
    before = dict(os.environ)
    sandbox.run([sys.executable, "-c", "pass"], cwd=tmp_path, timeout=30)
    assert dict(os.environ) == before


def _run_py(code, tmp_path, timeout=30):
    return sandbox.run([sys.executable, "-c", code], cwd=tmp_path, timeout=timeout)


def test_guard_blocks_sockets(tmp_path):
    r = _run_py("import socket\ns = socket.socket()\ns.connect(('127.0.0.1', 9))", tmp_path)
    assert r.returncode != 0 and "blocked by the MitraField sandbox" in r.stderr


def test_guard_blocks_shells_and_unlisted_programs(tmp_path):
    for code in ("import os; os.system('echo hi')", "import subprocess; subprocess.run(['curl', '--version'])",
                 "import subprocess; subprocess.Popen('sh -c id', shell=True)", "import os; os.execv('/bin/sh', ['sh'])"):
        r = _run_py(code, tmp_path)
        assert r.returncode != 0 and "blocked" in r.stderr, code


def test_guard_still_lets_manim_start_its_own_tools(tmp_path):
    r = _run_py("import subprocess; print(subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True).stdout[:6])", tmp_path)
    assert r.returncode == 0 and "ffmpeg" in r.stdout


def _has_manim():
    from backend import config
    return subprocess.run([config.MANIM_PY, "-c", "import manim"], capture_output=True).returncode == 0


@pytest.mark.skipif(not _has_manim(), reason="manim not installed here (CI and the image have it)")
def test_a_real_manim_beat_renders_inside_the_sandbox(tmp_path):
    from backend import config
    (tmp_path / "beat.py").write_text(GOOD)
    r = sandbox.run([config.MANIM_PY, "-m", "manim", "render", "-ql", "--disable_caching", "--media_dir", str(tmp_path / "m"),
                     "-o", "beat.mp4", str(tmp_path / "beat.py"), "Beat"], cwd=tmp_path, timeout=300)
    assert r.returncode == 0, r.stderr[-800:]
    assert list((tmp_path / "m").rglob("beat.mp4"))
