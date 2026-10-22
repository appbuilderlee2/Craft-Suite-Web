"""Install a reproducibly built, locally patched WordCraft into the 13-app hub."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORK_COMMIT = "d52cf9737a441e9b04259932d9703199a10922a5"

def overlay(source, dist=None):
    source = Path(source).resolve()
    dist = Path(dist) if dist else ROOT / "dist"
    if not source.is_dir() or not (source / "index.html").is_file():
        raise ValueError("Missing compiled WordCraft web output")
    sys.path.insert(0, str(ROOT / "scripts"))
    from build import verify_web, MAX_SITE
    verify_web(source)
    meta_path = dist / "versions.json"
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    matches = [app for app in metadata["apps"] if app["id"] == "wordcraft"]
    if len(matches) != 1 or not matches[0].get("path"):
        raise ValueError("WordCraft release not found")
    app = matches[0]
    target = dist / app["path"]
    if not target.is_dir() or not target.resolve().is_relative_to(dist.resolve()):
        raise ValueError("Invalid WordCraft destination")
    # Original release's license and attribution must accompany the patched build.
    preserved = {name: (target / name).read_bytes() for name in
                 ("LICENSE-MIT", "LICENSE-APACHE", "NOTICE", "ATTRIBUTION.md")
                 if (target / name).exists()}
    shutil.rmtree(target)
    shutil.copytree(source, target)
    for name, data in preserved.items():
        (target / name).write_bytes(data)
    verify_web(target)
    app["source"] = "appbuilderlee2/wordcraft-web"
    app["forkCommit"] = FORK_COMMIT
    app["patchedTraditionalChinese"] = True
    app["deployedBytes"] = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
    metadata["totalBytes"] = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
    if metadata["totalBytes"] > MAX_SITE:
        raise ValueError("Patched suite exceeds 900 MiB size limit")
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WordCraft patched {FORK_COMMIT[:8]} at {app['path']} ({app['deployedBytes']} bytes)")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: overlay_wordcraft.py /path/to/compiled/web")
    overlay(sys.argv[1])
