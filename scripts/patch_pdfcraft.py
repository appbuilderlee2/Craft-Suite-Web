"""Patch upstream PdfCraft's wasm CJK fallback without embedding barred font families."""
from pathlib import Path
import sys

def patch(root):
    root = Path(root)
    build = root / "crates/fonts/build.rs"
    craft = root / "crates/fonts/src/craft.rs"
    b = build.read_text()
    before = '(*family == "BIZ UDPGothic" && *style == "Regular") || arabic'
    after = '((*family == "BIZ UDPGothic" || *family == "LXGW WenKai") && *style == "Regular") || arabic'
    if b.count(before) != 1:
        raise ValueError("Upstream PdfCraft font selection changed; aborting patch")
    build.write_text(b.replace(before, after))
    s = craft.read_text()
    old = 'f.covers("Hans") || f.covers("Jpan")'
    if s.count(old) < 1:
        raise ValueError("Upstream PdfCraft CJK fallback changed; aborting patch")
    s = s.replace(old, 'f.covers("Hans") || f.covers("Hant") || f.covers("Jpan")')
    first = 'let first = if prefer_hans { "Hans" } else { "Jpan" };'
    if s.count(first) != 1:
        raise ValueError("Upstream PdfCraft CJK priority changed")
    s = s.replace(first, 'let first = if prefer_hans { "Hans" } else { "Hant" };')
    craft.write_text(s)
    print("Patched PdfCraft embedded CJK fallback (Hans/Hant/Jpan).")

if __name__ == "__main__":
    patch(sys.argv[1])
