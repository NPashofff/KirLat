"""Жив тест на замяната: отваря прозорец с избран текст, пуска SelectionConverter и проверява резултата.

    python tests/live_test.py
Изисква работещ десктоп (прозорецът трябва да получи фокус).
"""
import os
import sys
import threading
import tkinter as tk

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pyperclip  # noqa: E402

from kirlat.actions import SelectionConverter  # noqa: E402
from kirlat.config import DEFAULTS  # noqa: E402

ORIGINAL = "Zdrawej kak si"
EXPECTED = "Здравей как си"
result = {}


def main() -> int:
    pyperclip.copy("clipboard-before")
    root = tk.Tk()
    root.title("KirLat live test")
    root.attributes("-topmost", True)
    txt = tk.Text(root, width=40, height=4, font=("Arial", 14))
    txt.pack()
    txt.insert("1.0", "before ")
    txt.insert("end", ORIGINAL)
    txt.insert("end", " after")
    txt.tag_add("sel", "1.7", f"1.{7 + len(ORIGINAL)}")
    txt.mark_set("insert", "1.7")
    txt.focus_force()

    conv = SelectionConverter(lambda: DEFAULTS, notify=lambda m: print("notify:", m))

    def go():
        conv.run()
        root.after(400, finish)

    def finish():
        result["text"] = txt.get("1.0", "end").rstrip("\n")
        result["clip"] = pyperclip.paste()
        root.destroy()

    root.after(800, lambda: threading.Thread(target=go, daemon=True).start())
    root.after(6000, finish)
    root.mainloop()

    got = result.get("text")
    print("text after :", got)
    print("clipboard  :", result.get("clip"))
    ok = got == f"before {EXPECTED} after" and result.get("clip") == "clipboard-before"
    print("RESULT:", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
