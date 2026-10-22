"""Browser smoke test for all 13 Craft Suite Pages apps.

Captures actual Chromium screenshots and diagnostics. A successful smoke test does
not certify Chinese glyph coverage; screenshots require visual review.
"""
import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT_URL = os.environ.get("SITE_URL", "https://appbuilderlee2.github.io/Craft-Suite-Web/").rstrip("/") + "/"
OUTPUT = Path("browser-audit")
OUTPUT.mkdir(exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader"])
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1, locale="zh-HK")
        page = await context.new_page()
        response = await page.goto(ROOT_URL + "versions.json", wait_until="domcontentloaded", timeout=60000)
        if not response or not response.ok:
            raise RuntimeError("Cannot fetch deployed versions.json")
        manifest = json.loads(await page.locator("body").inner_text())
        apps = manifest["apps"]
        results = []
        for app in apps:
            app_id = app["id"]
            url = ROOT_URL + app["path"]
            tab = await context.new_page()
            errors = []
            tab.on("pageerror", lambda err: errors.append(str(err)))
            tab.on("console", lambda msg: errors.append("console: " + msg.text) if msg.type == "error" else None)
            entry = {"app": app_id, "url": url, "version": app.get("version"), "render_verified": False}
            try:
                res = await tab.goto(url, wait_until="domcontentloaded", timeout=90000)
                await tab.wait_for_timeout(9500)
                entry["http_status"] = res.status if res else None
                entry["title"] = await tab.title()
                entry["canvas_count"] = await tab.locator("canvas").count()
                entry["visible_text_sample"] = (await tab.locator("body").inner_text())[:500]
                entry["replacement_character_count"] = entry["visible_text_sample"].count("\ufffd")
                entry["canvas_based_ui"] = entry["canvas_count"] > 0
                # Rasterized canvas text cannot be validated by DOM text inspection.
                entry["render_verified"] = bool(res and res.ok and entry["canvas_count"] > 0)
                await tab.screenshot(path=str(OUTPUT / f"{app_id}.png"), full_page=True, timeout=30000)
            except Exception as exc:
                entry["exception"] = str(exc)
            entry["errors"] = errors[:15]
            results.append(entry)
            print(f"{app_id}: status={entry.get('http_status')} canvas={entry.get('canvas_count')} errors={len(errors)}", flush=True)
            await tab.close()
        await browser.close()
        (OUTPUT / "report.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        (OUTPUT / "README.txt").write_text("Screenshots require human inspection for □ or ?? glyphs. DOM checks cannot read text painted into WASM canvas.\n", encoding="utf-8")
        print("Audit screenshots:", len(list(OUTPUT.glob("*.png"))))
        if len(results) != 13 or any(x.get("http_status") != 200 or "exception" in x for x in results):
            raise RuntimeError("One or more app pages could not be captured; inspect report")

if __name__ == "__main__":
    asyncio.run(main())
