import pytest

from backend import config, costs, gemini, store


def test_guard_blocks_over_daily_cap(project, monkeypatch):
    monkeypatch.setattr(config, "CAP_DAY_USD", 1.0)
    with costs.track(project.id):
        costs.add("video", 0.9)
        costs.guard()
        costs.add("video", 0.2)
        with pytest.raises(costs.BudgetExceeded, match="daily"):
            costs.guard()


def test_guard_blocks_over_project_cap_but_not_other_projects(project, monkeypatch):
    from backend.models import Project
    other = store.save(Project(id="2222222222", topic="o"))
    monkeypatch.setattr(config, "CAP_PROJECT_USD", 0.5)
    with costs.track(project.id):
        costs.add("image", 0.6)
        with pytest.raises(costs.BudgetExceeded, match="project"):
            costs.guard()
    with costs.track(other.id):
        costs.guard()


def test_summary_matches_ledger(project):
    with costs.track(project.id):
        costs.add("voice", 0.1)
        costs.add("image", 0.3)
        costs.add("image", 0.3)
    s = costs.summary(project.id)
    assert s["total"] == pytest.approx(0.7) and s["calls"] == 3
    assert list(s["by_kind"]) == ["image", "voice"]


def test_add_outside_a_project_is_ignored():
    costs.add("text", 1.0)
    assert store.spend(f"d:{store._today()}")["total"] == 0


def test_retry_never_retries_a_budget_refusal(project, monkeypatch):
    monkeypatch.setattr(config, "CAP_PROJECT_USD", 0.0)
    calls = []
    with costs.track(project.id), pytest.raises(costs.BudgetExceeded):
        gemini._retry(lambda: calls.append(1))
    assert calls == []


def test_retry_retries_transient_errors(monkeypatch):
    monkeypatch.setattr(gemini.time, "sleep", lambda s: None)
    n = []

    def flaky():
        n.append(1)
        if len(n) < 3:
            raise RuntimeError("503")
        return "ok"
    assert gemini._retry(flaky) == "ok" and len(n) == 3


def test_rate_limits_are_retried_longer_and_with_growing_waits(monkeypatch):
    waits = []
    monkeypatch.setattr(gemini.time, "sleep", waits.append)
    n = []

    def limited():
        n.append(1)
        if len(n) < 6:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return "ok"
    assert gemini._retry(limited) == "ok"
    assert waits == [10, 20, 40, 60, 60]


def test_rate_limit_gives_up_eventually(monkeypatch):
    monkeypatch.setattr(gemini.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="429"):
        gemini._retry(lambda: (_ for _ in ()).throw(RuntimeError("429 RESOURCE_EXHAUSTED")))
