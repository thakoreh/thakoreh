#!/usr/bin/env python3
"""Draws the four app icons (letter tiles in the design-system tints) into scripts/icons/.
Run by hand or by the nightly workflow before build.py; the PNGs are only read by cards.py
and phone.py through img_b64, they are never committed as profile images themselves."""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
APPS = [("agent-tally", "AT", "#cfe6ff"), ("llm-speedtest-mcp", "LS", "#e7defc"),
        ("vibecheck", "VC", "#ffe1b8"), ("paris-pulse", "PP", "#d6f2dc")]

os.makedirs(os.path.join(HERE, "icons"), exist_ok=True)
font = ImageFont.truetype(os.path.join(HERE, "fonts", "Fredoka-700.ttf"), 118)
for aid, letters, bg in APPS:
    img = Image.new("RGB", (288, 288), bg)
    d = ImageDraw.Draw(img)
    d.text((144, 148), letters, font=font, fill="#22201c", anchor="mm")
    img.save(os.path.join(HERE, "icons", aid + ".png"))
print("icons drawn")
