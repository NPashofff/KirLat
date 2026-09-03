"""Таблици на клавиатурните подредби.

Всеки низ описва 47-те физически клавиша на US клавиатурата в реда:
  ` 1 2 3 4 5 6 7 8 9 0 - =   q w e r t y u i o p [ ] \\   a s d f g h j k l ; '   z x c v b n m , . /
Българските низове са извлечени от реалните Windows подредби (ToUnicodeEx по сканкод).
"""

US_LOWER = "`1234567890-=qwertyuiop[]\\asdfghjkl;'zxcvbnm,./"
US_UPPER = "~!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:\"ZXCVBNM<>?"

LAYOUTS = {
    "phonetic_traditional": {
        "name": "Фонетична (традиционна) – Win „Bulgarian (Phonetic Traditional)“ / macOS „Bulgarian – Phonetic“",
        "lower": "ч1234567890-=явертъуиопшщюасдфгхйкл;'зьцжбнм,./",
        "upper": "Ч!@№$%€§*()_+ЯВЕРТЪУИОПШЩЮАСДФГХЙКЛ:\"ЗѝЦЖБНМ<>?",
    },
    "phonetic": {
        "name": "Фонетична (нова, БДС 2006) – Win „Bulgarian (Phonetic)“",
        "lower": "ю1234567890-=чшертъуиопящьасдфгхйкл;'зжцвбнм,./",
        "upper": "Ю!@№$%€§*()–+ЧШЕРТЪУИОПЯЩѝАСДФГХЙКЛ:\"ЗЖЦВБНМ„“?",
    },
    "bds": {
        "name": "БДС – Win „Bulgarian“ / macOS „Bulgarian“",
        "lower": "(1234567890-.,уеишщксдзц;„ьяаожгтнвмчюйъэфхпрлб",
        "upper": ")!?+\"%=:/–№$€ыУЕИШЩКСДЗЦ§“ѝЯАОЖГТНВМЧЮЙЪЭФХПРЛБ",
    },
    "typewriter": {
        "name": "Пишеща машина – Win „Bulgarian (Typewriter)“",
        "lower": "`1234567890-.,уеишщксдзц;(ьяаожгтнвмчюйъэфхпрлб",
        "upper": "~!?+\"%=:/_№ІVыУЕИШЩКСДЗЦ§)ЬЯАОЖГТНВМЧЮЙЪЭФХПРЛБ",
    },
}

DEFAULT_LAYOUT = "phonetic_traditional"

for _id, _l in LAYOUTS.items():
    assert len(_l["lower"]) == len(US_LOWER) == 47, _id
    assert len(_l["upper"]) == len(US_UPPER) == 47, _id

_cache = {}


def build_maps(layout_id: str):
    """Връща (en2bg, bg2en) речници за дадена подредба."""
    if layout_id not in LAYOUTS:
        layout_id = DEFAULT_LAYOUT
    if layout_id in _cache:
        return _cache[layout_id]
    lay = LAYOUTS[layout_id]
    en2bg, bg2en = {}, {}
    for us, bg in ((US_LOWER, lay["lower"]), (US_UPPER, lay["upper"])):
        for e, b in zip(us, bg):
            if e == b:
                continue
            en2bg.setdefault(e, b)
            bg2en.setdefault(b, e)
    _cache[layout_id] = (en2bg, bg2en)
    return _cache[layout_id]


# ---- Клавиши, допустими за клавишната комбинация -------------------------

HOTKEY_KEYS = (
    list("abcdefghijklmnopqrstuvwxyz")
    + list("0123456789")
    + [f"f{i}" for i in range(1, 13)]
    + ["space", "`", "-", "=", "[", "]", "\\", ";", "'", ",", ".", "/"]
)

WIN_VK = {
    **{c: ord(c.upper()) for c in "abcdefghijklmnopqrstuvwxyz0123456789"},
    **{f"f{i}": 0x6F + i for i in range(1, 13)},
    "space": 0x20, "`": 0xC0, "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD,
    "\\": 0xDC, ";": 0xBA, "'": 0xDE, ",": 0xBC, ".": 0xBE, "/": 0xBF,
}

MAC_KEYCODE = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9,
    "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19,
    "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25, "7": 26, "-": 27, "8": 28,
    "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34, "p": 35, "l": 37, "j": 38,
    "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46, ".": 47,
    "space": 49, "`": 50,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97, "f7": 98,
    "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
}
