"""Record UI sections of the real app with Playwright (1920x1080 webm per section)."""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

B = "http://localhost:8020"
OUT = Path("scratch/demovid/rec")
S = {s["id"]: s["dur"] for s in json.load(open("scratch/demovid/script.json"))}
TIT = sys.argv[1]
LEAD = 2.0   # seconds of page load trimmed later


async def smooth_scroll(pg, to, ms):
    await pg.evaluate("""([to, ms]) => new Promise(r => { const y0 = scrollY, t0 = performance.now();
      const f = t => { const k = Math.min(1, (t - t0) / ms), e = k < .5 ? 2*k*k : 1 - Math.pow(-2*k + 2, 2) / 2;
      scrollTo(0, y0 + (to - y0) * e); k < 1 ? requestAnimationFrame(f) : r(); }; requestAnimationFrame(f); })""", [to, ms])


async def section(browser, name, fn):
    ctx = await browser.new_context(viewport={"width": 1920, "height": 1080}, record_video_dir=str(OUT / name),
                                       record_video_size={"width": 1920, "height": 1080})
    pg = await ctx.new_page()
    # larger UI for video: every page renders as if on a ~1420 px wide screen, captured at 1080p
    await pg.add_init_script("document.addEventListener('DOMContentLoaded', () => { document.documentElement.style.zoom = '1.35'; })")
    await fn(pg)
    await ctx.close()
    vids = list((OUT / name).glob("*.webm"))
    vids[0].rename(OUT / f"{name}.webm")
    print("recorded", name)


async def s2(pg):   # landing: hero -> comparison table
    await pg.goto(B + "/"); await pg.wait_for_timeout(800)
    y = await pg.evaluate("document.evaluate(\"//h2[contains(., 'Beautiful is easy')]\", document, null, 9, null).singleNodeValue.getBoundingClientRect().top + scrollY - 120")
    await pg.evaluate(f"scrollTo(0, {y} - 380)")
    await pg.wait_for_timeout(LEAD * 1000 - 800 + 600)
    await smooth_scroll(pg, y, 2200)
    await pg.wait_for_timeout(int(S["s2_problem"] * 1000))


async def s3(pg):   # new video form
    await pg.goto(B + "/new/"); await pg.wait_for_timeout(LEAD * 1000)
    await pg.click("textarea >> nth=0")
    await pg.keyboard.type("Why did the Titanic sink?", delay=70)
    await pg.wait_for_timeout(600); await pg.click("text=Short"); await pg.wait_for_timeout(500); await pg.click("text=~1 min")
    await pg.wait_for_timeout(500)
    await pg.click("textarea >> nth=1")
    await pg.keyboard.type("Focus on the watertight compartments.", delay=35)
    await pg.wait_for_timeout(300)
    y = await pg.evaluate("document.evaluate(\"//p[normalize-space()='Look']\", document, null, 9, null).singleNodeValue.getBoundingClientRect().top + scrollY - 160")
    await smooth_scroll(pg, y, 1100)
    await pg.click("text=Woodblock"); await pg.wait_for_timeout(int(S["s3_ask"] * 1000) - 7600)


async def s5looks(pg):   # landing: ten looks grid
    await pg.goto(B + "/"); await pg.wait_for_timeout(800)
    y = await pg.evaluate("document.evaluate(\"//h2[contains(., 'ten looks')]\", document, null, 9, null).singleNodeValue.getBoundingClientRect().top + scrollY - 60")
    await pg.evaluate(f"scrollTo(0, {y})"); await pg.wait_for_timeout(LEAD * 1000)
    await smooth_scroll(pg, y + 700, 3800)
    await pg.wait_for_timeout(1500)


async def s4(pg):   # studio storyboard + routing
    await pg.goto(f"{B}/studio/?p={TIT}"); await pg.wait_for_timeout(LEAD * 1000)
    await pg.mouse.move(1880, 500)
    await pg.wait_for_timeout(2500)
    await smooth_scroll(pg, 520, 6000)
    await pg.wait_for_timeout(int(S["s4_director"] * 1000) - 8000)


async def s5(pg):   # cast strip: open the ship
    await pg.goto(f"{B}/studio/?p={TIT}"); await pg.wait_for_timeout(LEAD * 1000)
    await pg.mouse.move(1880, 500); await pg.wait_for_timeout(1000)
    await pg.click("text=RMS Titanic"); await pg.wait_for_timeout(2500)
    await pg.click("text=Thomas"); await pg.wait_for_timeout(2000)
    await pg.click("text=Moody historical"); await pg.wait_for_timeout(1500)


async def s7(pg):   # edit a beat
    await pg.goto(f"{B}/studio/?p={TIT}"); await pg.wait_for_timeout(LEAD * 1000)
    await smooth_scroll(pg, 330, 900)
    await pg.click("text=The hull was divided"); await pg.wait_for_timeout(1200)
    await pg.mouse.move(1880, 300)
    await smooth_scroll(pg, 330, 300)
    await pg.click("input[placeholder^='e.g. Explain']")
    await pg.keyboard.type("Show it on a map of the North Atlantic", delay=55)
    await pg.wait_for_timeout(int(S["s7_edit"] * 1000) - 5200)


async def s8(pg):   # demo page with results
    await pg.goto(B + "/demo/"); await pg.wait_for_timeout(LEAD * 1000)
    await smooth_scroll(pg, 430, 1500); await pg.wait_for_timeout(1200)
    await pg.click("text=Woodblock look"); await pg.wait_for_timeout(1500)
    await pg.click("text=Biology · Short"); await pg.wait_for_timeout(1800)


async def s9(pg):   # landing hero
    await pg.goto(B + "/"); await pg.wait_for_timeout(LEAD * 1000)
    await pg.wait_for_timeout(int(S["s9_close"] * 1000) + 500)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        only = sys.argv[2:]
        for name, fn in [("s2_problem", s2), ("s3_ask", s3), ("s4_director", s4), ("s5_looks", s5looks), ("s5_cast", s5), ("s7_edit", s7), ("s9_results", s8), ("s9_close", s9)]:
            if only and name not in only:
                continue
            await section(browser, name, fn)

asyncio.run(main())
