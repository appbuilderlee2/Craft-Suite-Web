"""Inject passive stability diagnostics after official and patched apps are assembled."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def inject(dist=None):
    dist = Path(dist) if dist else ROOT / "dist"
    if not (dist / "stability.js").is_file():
        raise ValueError("Shared stability script is missing")
    apps = json.loads((dist / "versions.json").read_text())["apps"]
    if len(apps) != 13:
        raise ValueError("Expected 13 apps")
    for app in apps:
        page = dist / app["path"] / "index.html"
        if not page.is_file() or not page.resolve().is_relative_to(dist.resolve()):
            raise ValueError("Missing or unsafe app entry: " + app["id"])
        text = page.read_text(encoding="utf-8")
        if text.lower().count("</head>") != 1:
            raise ValueError("Unrecognized HTML head: " + app["id"])
        if 'src="../../../stability.js"' in text:
            continue
        close = text.lower().index("</head>")
        text = text[:close] + '<script defer src="../../../stability.js"></script>\n' + text[close:]
        page.write_text(text, encoding="utf-8")
    print("Added non-reloading Safari diagnostics to", len(apps), "app entrypoints")

if __name__ == "__main__":
    inject()
