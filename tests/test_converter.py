import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from kirlat.converter import convert, detect_direction  # noqa: E402
from kirlat.layouts import LAYOUTS, build_maps  # noqa: E402


class ConverterTests(unittest.TestCase):
    def test_phonetic_traditional_to_bg(self):
        self.assertEqual(convert("Zdrawej kak si", "phonetic_traditional"), "Здравей как си")
        self.assertEqual(convert("Zdrawej, kak si?", "phonetic_traditional"), "Здравей, как си?")
        self.assertEqual(convert("[opa ]e ]e", "phonetic_traditional"), "шопа ще ще")
        self.assertEqual(convert("`owek", "phonetic_traditional"), "човек")
        self.assertEqual(convert("vaba", "phonetic_traditional"), "жаба")

    def test_phonetic_traditional_to_en(self):
        self.assertEqual(convert("Здравей как си", "phonetic_traditional"), "Zdrawej kak si")
        self.assertEqual(convert("Хелло њорлд", "phonetic_traditional", "to_en")[:5], "Hello")

    def test_bds(self):
        # физическите клавиши на "Здравей" по БДС: З=Shift+p, д=o, р=",", а=d, в=l, е=e, й=x
        self.assertEqual(convert("Po,dlex", "bds"), "Здравей")
        text = "Здравей, как си?"
        self.assertEqual(convert(convert(text, "bds", "to_en"), "bds", "to_bg"), text)

    def test_roundtrip_all_layouts(self):
        sample = "The quick brown fox jumps over the lazy dog 1234567890 [];',./`-="
        for lid in LAYOUTS:
            bg = convert(sample, lid, "to_bg")
            back = convert(bg, lid, "to_en")
            self.assertEqual(back, sample, lid)

    def test_auto_direction(self):
        self.assertEqual(detect_direction("Zdrawej"), "to_bg")
        self.assertEqual(detect_direction("Здравей"), "to_en")
        self.assertEqual(detect_direction("123 ..."), "to_bg")
        self.assertEqual(convert("Zdrawej", "phonetic_traditional", "auto"), "Здравей")
        self.assertEqual(convert("Здравей", "phonetic_traditional", "auto"), "Zdrawej")

    def test_unknown_chars_untouched(self):
        self.assertEqual(convert("😀 ok\n", "phonetic_traditional"), "😀 ок\n")

    def test_maps_are_bijective(self):
        for lid in LAYOUTS:
            en2bg, bg2en = build_maps(lid)
            for e, b in en2bg.items():
                self.assertEqual(bg2en.get(b), e, f"{lid}: {e!r}->{b!r}")


if __name__ == "__main__":
    unittest.main()
