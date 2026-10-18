"""Loaded automatically by the interpreter that runs model-written Manim code (via PYTHONPATH).

A runtime layer under the static check in ../sandbox.py, for hosts where a network namespace is not
available: outbound sockets are refused, and the only programs that may be started are the ones Manim
itself needs. It raises the bar against the obvious routes (np.os.system, a stray socket). It is not a
security boundary against determined code in the same process; see the notes in ../sandbox.py.
"""
import os
import socket
import subprocess

_ALLOWED_PROGRAMS = {"latex", "pdflatex", "xelatex", "dvisvgm", "dvips", "ffmpeg", "ffprobe", "tex", "kpsewhich", "pdftex"}


def _deny(*_a, **_k):
    raise PermissionError("blocked by the MitraField sandbox")


for _name in ("connect", "connect_ex", "sendto", "bind", "listen"):
    setattr(socket.socket, _name, _deny)
socket.create_connection = _deny
socket.getaddrinfo = _deny
socket.gethostbyname = _deny

for _name in ("system", "popen", "execv", "execve", "execvp", "execvpe", "execl", "execle", "execlp", "execlpe",
              "spawnv", "spawnve", "spawnvp", "spawnvpe", "spawnl", "spawnle", "spawnlp", "spawnlpe", "posix_spawn",
              "posix_spawnp", "fork", "forkpty"):
    if hasattr(os, _name):
        setattr(os, _name, _deny)

_Popen_init = subprocess.Popen.__init__


def _popen_init(self, args, *a, **k):
    prog = args if isinstance(args, str) else (args[0] if args else "")
    if os.path.basename(str(prog)).split(" ")[0] not in _ALLOWED_PROGRAMS:
        raise PermissionError(f"starting {os.path.basename(str(prog))!r} is blocked by the MitraField sandbox")
    _Popen_init(self, args, *a, **k)


subprocess.Popen.__init__ = _popen_init
