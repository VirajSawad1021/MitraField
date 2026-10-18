"""Fact-check agent: every checkable claim in the storyboard (narration and the numbers, dates and labels
the exact engines will draw) is verified against the person's sources first, then Google Search.
Runs automatically after the storyboard is written, before anything is rendered. Claims that are not
supported are flagged in the studio with the evidence and a suggested correction, which can be applied to
the beat with one click (the director rewrites it and the beat re-renders).
"""
import json
import re
import time

from . import config, costs, director, gemini, log, store
from .guards import INJECTION_RULE

logger = log.get("factcheck")

VERDICTS = ("supported", "unsupported", "contradicted", "unverifiable")
FLAG = {"contradicted", "unsupported"}

PROMPT = """You are the fact-checker of an explainer-video studio. Below is a storyboard: numbered beats with the
narration, plus the words and numbers each beat will show on screen.

1. List every checkable factual claim: numbers, quantities, dates, rankings, names, causes and effects stated as
   fact. Skip opinions, rhetorical questions, analogies and obvious simplifications for a general audience.
2. Verify each claim. Use the person's sources first (they are the source of truth when they cover a claim);
   for every other claim you MUST search Google before giving a verdict. Never rely on memory alone. A reasonable rounding ("about 21 million") of a precise figure is supported.
3. Verdicts: supported, unsupported (no reliable evidence found), contradicted (reliable evidence says otherwise),
   unverifiable (cannot be checked, e.g. a prediction).

{injection}

Answer with ONLY a JSON array, no prose, like:
[{{"beat": 2, "claim": "...", "verdict": "contradicted", "evidence": "one sentence on what the evidence says",
   "correction": "the corrected wording, or empty", "source": "your sources" or the publication name}}]

Topic: {topic}
{sources}
Storyboard:
{board}"""


def _on_screen(s):
    """Words and numbers a beat will draw (engine params), so charts and labels get checked too."""
    keep = {}
    for k, v in (s.params or {}).items():
        if k.startswith("_"):
            continue
        keep[k] = v
    text = json.dumps(keep, ensure_ascii=False)
    return text[:600] if keep else ""


def _parse(text):
    m = re.search(r"\[.*\]", text or "", re.S)
    if not m:
        return []
    try:
        rows = json.loads(m.group(0))
    except ValueError:
        return []
    out = []
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict) or not r.get("claim"):
            continue
        v = str(r.get("verdict", "")).lower()
        out.append({"beat": int(r.get("beat") or 0), "claim": str(r["claim"])[:300],
                    "verdict": v if v in VERDICTS else "unverifiable",
                    "evidence": str(r.get("evidence", ""))[:400], "correction": str(r.get("correction", ""))[:300],
                    "source": str(r.get("source", ""))[:120]})
    return out


@costs.tracked
def run(pid):
    p = store.load(pid)
    if not p.scenes:
        return None
    store.mutate(pid, lambda pp: setattr(pp, "factcheck", {"status": "checking", "t": time.time()}))
    try:
        parts, notes = director.source_parts(p)
        board = "\n".join(f"Beat {i + 1} [{s.engine}]: {s.narration}" + (f"\n   on screen: {_on_screen(s)}" if _on_screen(s) else "")
                          for i, s in enumerate(p.scenes))
        sources = (f"The person's sources:\n{notes}\n" if notes else "") + ("Attached files are sources too.\n" if parts else "")
        if not sources:
            sources = "The person gave no sources: verify with Google Search.\n"
        text, web = gemini.grounded(PROMPT.format(injection=INJECTION_RULE, topic=p.topic, sources=sources, board=board),
                                    model=config.MODEL_DIRECTOR, parts=parts)
        claims = [c for c in _parse(text) if 1 <= c["beat"] <= len(p.scenes)]
        for c in claims:
            c["sid"] = p.scenes[c["beat"] - 1].id
        flagged = sorted({c["sid"] for c in claims if c["verdict"] in FLAG}, key=lambda sid: [s.id for s in p.scenes].index(sid))
        n_bad = sum(c["verdict"] in FLAG for c in claims)
        report = {"status": "flagged" if n_bad else "passed", "t": time.time(), "claims": claims, "web": web[:12],
                  "flagged": flagged,
                  "summary": (f"{n_bad} of {len(claims)} claims need attention." if n_bad
                              else f"All {len(claims)} checkable claims are supported." if claims
                              else "No checkable claims found.")}
    except Exception as e:
        logger.exception("fact check failed", extra={"pid": pid})
        report = {"status": "error", "t": time.time(), "summary": f"The fact check could not run: {str(e)[:200]}"}
    store.mutate(pid, lambda pp: setattr(pp, "factcheck", report))
    return report


def correction_instruction(c: dict) -> str:
    fix = c.get("correction") or "state only what the evidence supports"
    return (f"Fact-check correction. The claim \"{c['claim']}\" is {c['verdict']}: {c.get('evidence', '')} "
            f"Rewrite this beat so it is accurate: {fix}. Keep the same engine and length; update any on-screen numbers.")
