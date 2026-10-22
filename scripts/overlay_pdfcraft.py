"""Overlay locally compiled PdfCraft Web while retaining the official versioned URL."""
import json
from pathlib import Path
import shutil
import sys

def overlay(src):
    src = Path(src).resolve()
    root = Path(__file__).resolve().parents[1]
    dist = root / "dist"
    meta = dist / "versions.json"
    from build import verify_web, MAX_SITE
    verify_web(src)
    data = json.loads(meta.read_text())
    app, = [a for a in data["apps"] if a["id"] == "pdfcraft"]
    dst = dist / app["path"]
    if not dst.is_dir() or not dst.resolve().is_relative_to(dist.resolve()):
        raise ValueError("Invalid PdfCraft target")
    preserved = {x.name: x.read_bytes() for x in dst.iterdir() if x.name.startswith(("LICENSE", "NOTICE", "ATTRIBUTION")) and x.is_file()}
    shutil.rmtree(dst)
    shutil.copytree(src, dst)
    for name, content in preserved.items():
        (dst / name).write_bytes(content)
    verify_web(dst)
    app["patchedTraditionalChinese"] = True
    app["source"] = "storytold/pdfcraft + local LXGW WenKai web patch"
    app["deployedBytes"] = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
    data["totalBytes"] = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
    if data["totalBytes"] > MAX_SITE:
        raise ValueError("Craft Suite exceeds size limit")
    meta.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n")
    print("Patched PdfCraft", app["tag"], "at", app["path"])

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    overlay(sys.argv[1])
