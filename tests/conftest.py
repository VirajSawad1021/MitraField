"""Tests run against the file store and the local queue in a throwaway data dir; the Firestore
store is covered by test_store_firestore.py when an emulator is available."""
import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mitrafield-test-")
os.environ["STUDIO_DATA"] = str(Path(_tmp) / "projects")
os.environ.update(STUDIO_ROLE="all", STUDIO_STORE="file", STUDIO_QUEUE="local", STUDIO_PASSCODE="",
                  STUDIO_CAP_DAY_USD="25", STUDIO_CAP_PROJECT_USD="5", GEMINI_API_KEY="test-key-do-not-leak")

import pytest  # noqa: E402

from backend import config, costs, store  # noqa: E402


@pytest.fixture(autouse=True)
def clean_store():
    import shutil
    shutil.rmtree(config.DATA, ignore_errors=True)
    config.DATA.mkdir(parents=True, exist_ok=True)
    store.use(store.FileBackend())
    costs._cache.clear()
    yield
    store.use(None)


@pytest.fixture
def project():
    from backend.models import Project, Scene
    p = Project(id="abcdef0123", topic="t", scenes=[Scene(id=f"s{i}", narration="Hello there.", engine="title") for i in range(3)])
    return store.save(p)
