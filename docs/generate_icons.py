"""Generate Quorum web icon assets from the master brand images in docs/images.

The master logo/favicon (`docs/images/favicon.png`) is a 2048x2048 source image.
Browsers request `/favicon.ico` and Next.js serves the file-convention icon in
`apps/web/src/app/`, so the master logo must be compiled into that exact path for
the branded tab icon to replace the placeholder.

Usage (from the repository root):
    apps/api/.venv/Scripts/python.exe docs/generate_icons.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_LOGO = REPO_ROOT / "docs" / "images" / "favicon.png"
WEB_ROOT = REPO_ROOT / "apps" / "web"

# Multi-resolution browser tab icon (Chrome/Edge/Firefox/Windows shell).
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64)]
LOGO_SIZE = (512, 512)
APPLE_ICON_SIZE = (180, 180)


def _write_png(image: Image.Image, path: Path, size: tuple[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.resize(size, Image.LANCZOS).save(path, format="PNG", optimize=True)
    print(f"[icons] wrote {path.relative_to(REPO_ROOT)} ({size[0]}x{size[1]})")


def _write_ico(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Pillow downsamples the master image into every requested ICO frame.
    image.save(path, format="ICO", sizes=ICO_SIZES)
    print(f"[icons] wrote {path.relative_to(REPO_ROOT)} ({ICO_SIZES})")


def main() -> None:
    if not SOURCE_LOGO.exists():
        raise FileNotFoundError(f"Master brand image not found: {SOURCE_LOGO}")

    with Image.open(SOURCE_LOGO) as raw:
        logo = raw.convert("RGBA")

    # Brand logo used by the top navigation and social/preview metadata.
    _write_png(logo, WEB_ROOT / "public" / "quorum-logo.png", LOGO_SIZE)

    # Next.js app-router file conventions (served at /icon.png and /apple-icon.png).
    _write_png(logo, WEB_ROOT / "src" / "app" / "icon.png", LOGO_SIZE)
    _write_png(logo, WEB_ROOT / "src" / "app" / "apple-icon.png", APPLE_ICON_SIZE)

    # /favicon.ico is resolved from the app directory first, with the public copy
    # as a static fallback for direct/edge requests.
    _write_ico(logo, WEB_ROOT / "src" / "app" / "favicon.ico")
    _write_ico(logo, WEB_ROOT / "public" / "favicon.ico")


if __name__ == "__main__":
    main()
