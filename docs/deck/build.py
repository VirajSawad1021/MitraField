"""Render deck.html to MitraField_Deck.pdf (and PNG previews with --preview)."""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent


async def main(preview):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1920, "height": 1080})
        await pg.goto((HERE / "deck.html").as_uri())
        await pg.wait_for_timeout(2500)   # web fonts
        await pg.pdf(path=str(HERE / "MitraField_Deck.pdf"), width="1920px", height="1080px", print_background=True)
        if preview:
            out = Path(preview)
            out.mkdir(parents=True, exist_ok=True)
            n = await pg.evaluate("document.querySelectorAll('.slide').length")
            for i in range(n):
                el = pg.locator(".slide").nth(i)
                await el.screenshot(path=str(out / f"slide_{i + 1:02d}.png"))
        await b.close()


asyncio.run(main(sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--preview" else None))
