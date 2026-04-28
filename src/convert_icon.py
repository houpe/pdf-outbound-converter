#!/usr/bin/env python3
"""Convert PNG icon to ICNS format for macOS builds."""
import os
import sys
from PIL import Image

SIZES = [16, 32, 64, 128, 256, 512]

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(base_dir)
    source = os.path.join(project_dir, 'assets', 'icon_source.png')
    iconset_dir = os.path.join(project_dir, 'assets', 'app_icon.iconset')

    if not os.path.exists(source):
        print(f"Source icon not found: {source}")
        sys.exit(1)

    os.makedirs(iconset_dir, exist_ok=True)
    img = Image.open(source)

    for size in SIZES:
        resized = img.resize((size, size), Image.LANCZOS)
        resized.save(os.path.join(iconset_dir, f"icon_{size}x{size}.png"))
        resized.save(os.path.join(iconset_dir, f"icon_{size}x{size}@2x.png"))

    print(f"Icon set generated in {iconset_dir}")
    print("Run: iconutil -c icns app_icon.iconset")


if __name__ == '__main__':
    main()
