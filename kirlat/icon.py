"""Икона за трея / приложението (рисува се с Pillow, без външни файлове)."""
import sys

from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = [
    "arialbd.ttf", "arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _font(size: int):
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def make_icon_image(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = max(2, size // 5)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(0, 122, 94, 255))
    font = _font(int(size * 0.48))
    d.text((size / 2, size / 2 + size * 0.02), "KЛ", fill=(255, 255, 255, 255), font=font, anchor="mm")
    return img


if __name__ == "__main__":
    make_icon_image(256).save(sys.argv[1] if len(sys.argv) > 1 else "icon.png")
