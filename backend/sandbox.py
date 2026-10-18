"""Running model-written code.

The Manim engine executes Python that Gemini wrote, steered by whatever the user uploaded. That is
untrusted code, so it gets four independent layers (none is claimed to be a perfect sandbox):

1. Static check (`check`): an allow-list of imports and a deny-list of dangerous builtins,
   attributes and file/network entry points. Refused code goes back to the model as a repair error.
2. Clean process (`run`): an allow-listed environment (no keys, no tokens), a private HOME and
   working directory, its own process group (a timeout kills LaTeX and ffmpeg children too).
3. Runtime guard (`sandbox_guard/sitecustomize.py`): no sockets, and only the programs Manim itself needs
   (latex, dvisvgm, ffmpeg) may be started. Best effort: it shares a process with the code it guards.
4. No network (`run`): the child runs in an empty network namespace when the host allows it
   (`unshare -rn`), which also removes the Cloud Run metadata server (the credentials the worker
   itself holds). `NET_ISOLATED` says whether layer 4 is active; the worker logs it at startup.

Residual risk, stated plainly: where namespaces are unavailable, layer 4 is absent and layers 1 to 3
are the defence. The worker service account therefore holds only what rendering needs (no secrets,
no project admin), and renders are the only thing it runs.
"""
import ast
import os
import signal
import subprocess
import tempfile
from pathlib import Path

ALLOWED_IMPORTS = {"manim", "numpy", "math", "cmath", "random", "itertools", "functools", "colorsys", "typing",
                   "collections", "dataclasses", "fractions", "decimal", "statistics", "enum", "operator", "copy"}
DENIED_NAMES = {"eval", "exec", "compile", "open", "__import__", "input", "breakpoint", "globals", "locals", "vars",
                "getattr", "setattr", "delattr", "memoryview", "exit", "quit"}
DENIED_ATTRS = {"load", "loads", "save", "savez", "savetxt", "loadtxt", "genfromtxt", "fromfile", "tofile", "memmap",
                "system", "popen", "environ", "getenv", "fromfunction_file", "read_text", "write_text", "read_bytes",
                "write_bytes", "unlink", "rmtree"}
DENIED_CALLS = {"ImageMobject", "SVGMobject", "VideoMobject"}   # read files named by the code
ALLOWED_DUNDER = {"__init__", "__name__"}


def check(code: str):
    """Return None when the code is acceptable, else a one-line reason (fed back to the model)."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"syntax error: {e}"
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORTS:
                    return f"import of {a.name!r} is not allowed (allowed: manim, numpy, math, random, itertools, ...)"
        elif isinstance(n, ast.ImportFrom):
            if (n.module or "").split(".")[0] not in ALLOWED_IMPORTS or n.level:
                return f"import from {n.module!r} is not allowed"
        elif isinstance(n, ast.Name) and n.id in DENIED_NAMES:
            return f"use of {n.id!r} is not allowed"
        elif isinstance(n, ast.Attribute):
            if n.attr in DENIED_ATTRS:
                return f"attribute {n.attr!r} is not allowed (no files, no environment)"
            if n.attr.startswith("__") and n.attr not in ALLOWED_DUNDER:
                return f"attribute {n.attr!r} is not allowed"
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in DENIED_CALLS:
            return f"{n.func.id} reads files and is not allowed; draw with shapes instead"
    return None


def _probe_net_isolation():
    try:
        return subprocess.run(["unshare", "-rn", "true"], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


NET_ISOLATED = _probe_net_isolation()

_ENV_ALLOW = ("PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH", "FONTCONFIG_PATH", "FONTCONFIG_FILE", "TEXMFCNF",
              "TEXINPUTS", "TEXMFHOME", "TEXMFVAR", "TEXMFCONFIG", "PYTHONHASHSEED")


GUARD_DIR = Path(__file__).parent / "sandbox_guard"   # holds a sitecustomize.py the child imports at startup


def clean_env(home):
    env = {k: os.environ[k] for k in _ENV_ALLOW if k in os.environ}
    env.update(HOME=str(home), TMPDIR=str(home), PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(GUARD_DIR))
    return env


def run(cmd, cwd, timeout):
    """Run cmd in a clean environment, in its own process group, without network where possible.
    Raises subprocess.TimeoutExpired after killing the whole group."""
    cmd = [str(c) for c in cmd]
    if NET_ISOLATED:
        cmd = ["unshare", "-rn", *cmd]
    with tempfile.TemporaryDirectory(prefix="sbx-") as home:
        p = subprocess.Popen(cmd, cwd=cwd, env=clean_env(home), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, start_new_session=True)
        try:
            out, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.communicate()
            raise
        return subprocess.CompletedProcess(cmd, p.returncode, out, err)
