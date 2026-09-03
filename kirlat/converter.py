from .layouts import build_maps

DIRECTIONS = {
    "auto": "Автоматично (по преобладаващата азбука)",
    "to_bg": "Само латиница → кирилица",
    "to_en": "Само кирилица → латиница",
}


def _is_cyrillic(ch: str) -> bool:
    return "Ѐ" <= ch <= "ӿ"


def detect_direction(text: str) -> str:
    """'to_bg' ако латинските букви са повече от кирилските, иначе 'to_en'."""
    lat = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    cyr = sum(1 for ch in text if _is_cyrillic(ch))
    if lat == 0 and cyr == 0:
        return "to_bg"
    return "to_bg" if lat >= cyr else "to_en"


def convert(text: str, layout_id: str, direction: str = "auto") -> str:
    if not text:
        return text
    en2bg, bg2en = build_maps(layout_id)
    if direction not in ("to_bg", "to_en"):
        direction = detect_direction(text)
    table = en2bg if direction == "to_bg" else bg2en
    return "".join(table.get(ch, ch) for ch in text)
