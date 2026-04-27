#!/usr/bin/env python3
"""Convert icon_source.png to app_icon.ico for Windows build."""
from PIL import Image
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
png_path = os.path.join(script_dir, 'icon_source.png')
ico_path = os.path.join(script_dir, 'app_icon.ico')

img = Image.open(png_path)
img.save(ico_path, format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(f"Created: {ico_path}")
