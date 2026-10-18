"""Record one real session on the current app: topic + Direction + look -> storyboard and fact check ->
edit a beat -> render -> quality check -> watch. Writes session.webm and marks.json."""
import json, time
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright

B = "http://localhost:8096"
OUT = Path("/home/one-point/lab/AI_Content/aibuildercup/scratch/walk2")
TOPIC = "Why is the Dead Sea so salty?"
DIRECTION = "Mostly maps and data charts. At most one short video shot."
marks, T0 = {}, None


def mark(k):
    marks[k] = round(time.monotonic() - T0, 2)
    print(k, marks[k], flush=True)


def st(pid):
    return requests.get(f"{B}/api/projects/{pid}").json()


def smooth(pg, to, ms):
    pg.evaluate("""([to, ms]) => new Promise(r => { const y0 = scrollY, t0 = performance.now();
      const f = t => { const k = Math.min(1, (t - t0) / ms), e = k < .5 ? 2*k*k : 1 - Math.pow(-2*k + 2, 2) / 2;
      scrollTo(0, y0 + (to - y0) * e); k < 1 ? requestAnimationFrame(f) : r(); }; requestAnimationFrame(f); })""", [to, ms])


def card_y(pg, text):
    return pg.evaluate(f"document.evaluate(\"//p[normalize-space()='{text}']\", document, null, 9, null).singleNodeValue.getBoundingClientRect().top + scrollY - 140")


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1920, "height": 1080}, record_video_dir=str(OUT / "raw"),
                        record_video_size={"width": 1920, "height": 1080})
    pg = ctx.new_page()
    T0 = time.monotonic()
    pg.add_init_script("document.addEventListener('DOMContentLoaded', () => { document.documentElement.style.zoom = '1.35'; })")
    pg.on("dialog", lambda d: d.accept())

    pg.goto(B + "/"); pg.wait_for_timeout(1200); mark("landing"); pg.wait_for_timeout(4000)
    pg.goto(B + "/new/"); pg.wait_for_timeout(1500); mark("form")
    pg.click("textarea >> nth=0"); pg.keyboard.type(TOPIC, delay=60); pg.wait_for_timeout(500); mark("typed")
    pg.click("textarea >> nth=1"); pg.keyboard.type(DIRECTION, delay=40); pg.wait_for_timeout(700); mark("direction")
    y = pg.evaluate("document.evaluate(\"//p[normalize-space()='Look']\", document, null, 9, null).singleNodeValue.getBoundingClientRect().top + scrollY - 200")
    smooth(pg, y, 1400); pg.wait_for_timeout(500)
    pg.click("text=Cinematic >> nth=0"); pg.wait_for_timeout(1200); mark("look")
    smooth(pg, 99999, 900); pg.wait_for_timeout(400)
    pg.click("text=Direct the storyboard"); mark("submit")

    pg.wait_for_url("**/studio/**", timeout=60000)
    pid = pg.url.split("p=")[1].split("&")[0]
    (OUT / "pid.txt").write_text(pid); mark("directing")
    while st(pid)["render_status"] == "directing":
        time.sleep(1)
    pg.wait_for_timeout(2500); mark("storyboard")
    for _ in range(120):   # fact check + cast references
        d = st(pid)
        if (d.get("factcheck") or {}).get("status") in ("passed", "flagged", "error") and all(c["status"] in ("ready", "error") for c in d["cast"]):
            break
        time.sleep(2)
    pg.wait_for_timeout(2500); mark("checked")
    smooth(pg, 500, 3000); pg.wait_for_timeout(1200)
    smooth(pg, card_y(pg, "Fact check") if False else 0, 10)
    fy = pg.evaluate("document.evaluate(\"//*[normalize-space()='Fact check']\", document, null, 9, null).singleNodeValue.getBoundingClientRect().top + scrollY - 140")
    smooth(pg, fy, 1800); pg.wait_for_timeout(500); mark("factcheck")
    pg.wait_for_timeout(5000)
    smooth(pg, 0, 1200); pg.wait_for_timeout(500)

    scenes = st(pid)["scenes"]
    target = next((s for s in scenes if s["engine"] in ("title", "image", "character")), scenes[1])
    pg.click(f"text={target['narration'][:28]}"); pg.wait_for_timeout(1500); mark("beat_open")
    pg.mouse.move(1900, 400)
    pg.click("input[placeholder^='e.g. Explain']")
    pg.keyboard.type("Make it simpler, with an everyday comparison", delay=50); pg.wait_for_timeout(300)
    pg.keyboard.press("Enter"); mark("instruct")
    for _ in range(200):
        s = next(x for x in st(pid)["scenes"] if x["id"] == target["id"])
        if s["status"] in ("ready", "error"):
            break
        time.sleep(2)
    pg.wait_for_timeout(2500); mark("beat_done")
    pg.locator("aside button:has(svg.lucide-x)").first.click(); pg.wait_for_timeout(800)

    smooth(pg, 0, 500)
    pg.click("text=Render video"); mark("render")
    last = time.time()
    while st(pid)["render_status"] not in ("done", "error"):
        if time.time() - last > 40:
            smooth(pg, 380, 2500); smooth(pg, 0, 2500); last = time.time()
        time.sleep(2)
    mark("render_done")
    for _ in range(150):
        if (st(pid).get("qa") or {}).get("status") in ("passed", "flagged", "error"):
            break
        time.sleep(2)
    pg.wait_for_timeout(3000); mark("qa_done")
    qy = pg.evaluate("document.evaluate(\"//*[normalize-space()='Quality check']\", document, null, 9, null).singleNodeValue.getBoundingClientRect().top + scrollY - 140")
    smooth(pg, qy, 1800); pg.wait_for_timeout(500); mark("qa_card")
    pg.wait_for_timeout(6000)
    smooth(pg, 0, 1200); pg.wait_for_timeout(400)
    pg.click("text=Watch >> nth=0"); pg.wait_for_timeout(1000); mark("watch")
    pg.wait_for_timeout(16000); mark("watch_end")
    ctx.close(); b.close()

vid = sorted((OUT / "raw").glob("*.webm"))[-1]
vid.rename(OUT / "session.webm")
(OUT / "marks.json").write_text(json.dumps(marks, indent=1))
print("done", marks)
