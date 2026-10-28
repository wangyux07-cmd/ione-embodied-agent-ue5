"""Create editable UE screen ornaments; background art remains a separate source asset."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Content" / "UI" / "Source"
OUT.mkdir(parents=True, exist_ok=True)

shadow = Image.new("RGBA", (400, 90), (0, 0, 0, 0))
ink = Image.new("RGBA", shadow.size, (0, 0, 0, 0))
ImageDraw.Draw(ink).ellipse((18, 18, 382, 72), fill=(20, 14, 15, 185))
shadow.alpha_composite(ink.filter(ImageFilter.GaussianBlur(16)))
ImageDraw.Draw(shadow).ellipse((70, 38, 330, 61), fill=(33, 23, 24, 65))
shadow.save(OUT / "Ione_ContactShadow.png")

w, h = 780, 188
frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
d = ImageDraw.Draw(frame)
d.rounded_rectangle((2, 2, w - 3, h - 3), radius=15, fill=(28, 30, 28, 233), outline=(169, 147, 110, 240), width=3)
d.rounded_rectangle((9, 9, w - 10, h - 10), radius=10, outline=(104, 110, 93, 210), width=2)
d.line((25, 41, w - 25, 41), fill=(148, 136, 111, 190), width=2)
d.line((25, h - 27, w - 25, h - 27), fill=(105, 108, 91, 135), width=1)
for side in (0, 1):
    x = 24 if side == 0 else w - 24
    direction = 1 if side == 0 else -1
    for y in (23, h - 23):
        d.ellipse((x - 8, y - 8, x + 8, y + 8), outline=(194, 163, 116, 245), width=2)
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(187, 122, 85, 240))
        d.line((x + direction * 13, y, x + direction * 49, y), fill=(163, 141, 108, 220), width=2)
        d.polygon([(x + direction * 55, y), (x + direction * 62, y - 4), (x + direction * 62, y + 4)], fill=(163, 141, 108, 220))
for cx in (w - 73, w - 51):
    d.ellipse((cx - 7, 18, cx + 7, 32), outline=(172, 153, 123, 220), width=2)
    d.ellipse((cx - 2, 23, cx + 2, 27), fill=(190, 139, 104, 240))
frame.save(OUT / "Ione_DialogueFrame.png")

print(OUT)
