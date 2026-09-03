"""Прозорец с настройки (tkinter). Стартира се като отделен процес: main.py --settings"""
import tkinter as tk
from tkinter import messagebox, ttk

from . import autostart, config
from .converter import DIRECTIONS, convert
from .layouts import HOTKEY_KEYS, LAYOUTS

PAD = {"padx": 6, "pady": 4}


def _key_display(k: str) -> str:
    return "Space" if k == "space" else k.upper()


def run() -> None:
    cfg = config.load()
    hk = cfg["hotkey"]

    root = tk.Tk()
    root.title("KirLat – Настройки")
    root.resizable(False, False)
    try:
        root.attributes("-topmost", True)
        root.after(300, lambda: root.attributes("-topmost", False))
    except tk.TclError:
        pass

    try:
        import base64
        import io
        from .icon import make_icon_image
        buf = io.BytesIO()
        make_icon_image(64).save(buf, format="PNG")
        root._icon_img = tk.PhotoImage(data=base64.b64encode(buf.getvalue()))
        root.iconphoto(True, root._icon_img)
    except Exception:
        pass

    bold = ("TkDefaultFont", 10, "bold")
    frm = ttk.Frame(root, padding=14)
    frm.grid(sticky="nsew")

    # ---- Клавишна комбинация ------------------------------------------------
    ttk.Label(frm, text="Клавишна комбинация", font=bold).grid(row=0, column=0, columnspan=4, sticky="w", **PAD)
    v_ctrl = tk.BooleanVar(value=bool(hk.get("ctrl")))
    v_alt = tk.BooleanVar(value=bool(hk.get("alt")))
    v_shift = tk.BooleanVar(value=bool(hk.get("shift")))
    v_meta = tk.BooleanVar(value=bool(hk.get("meta")))
    v_key = tk.StringVar(value=_key_display(str(hk.get("key", "w"))))

    mods = ttk.Frame(frm)
    mods.grid(row=1, column=0, columnspan=4, sticky="w", **PAD)
    ttk.Checkbutton(mods, text="Ctrl", variable=v_ctrl).pack(side="left", padx=(0, 8))
    ttk.Checkbutton(mods, text="Option" if config.IS_MAC else "Alt", variable=v_alt).pack(side="left", padx=(0, 8))
    ttk.Checkbutton(mods, text="Shift", variable=v_shift).pack(side="left", padx=(0, 8))
    ttk.Checkbutton(mods, text="Cmd" if config.IS_MAC else "Win", variable=v_meta).pack(side="left", padx=(0, 8))
    ttk.Label(mods, text="+").pack(side="left", padx=(0, 8))
    key_box = ttk.Combobox(mods, textvariable=v_key, width=8, state="readonly",
                           values=[_key_display(k) for k in HOTKEY_KEYS])
    key_box.pack(side="left")

    v_preview = tk.StringVar()
    ttk.Label(frm, textvariable=v_preview, foreground="#007a5e").grid(row=2, column=0, columnspan=4, sticky="w", **PAD)

    # ---- Подредба и посока ---------------------------------------------------
    ttk.Label(frm, text="Българска клавиатурна подредба", font=bold).grid(row=3, column=0, columnspan=4, sticky="w", **PAD)
    layout_ids = list(LAYOUTS.keys())
    layout_names = [LAYOUTS[i]["name"] for i in layout_ids]
    cur_layout = cfg.get("layout") if cfg.get("layout") in LAYOUTS else layout_ids[0]
    v_layout = tk.StringVar(value=LAYOUTS[cur_layout]["name"])
    ttk.Combobox(frm, textvariable=v_layout, values=layout_names, state="readonly", width=70).grid(
        row=4, column=0, columnspan=4, sticky="w", **PAD)

    ttk.Label(frm, text="Посока на преобразуване", font=bold).grid(row=5, column=0, columnspan=4, sticky="w", **PAD)
    dir_ids = list(DIRECTIONS.keys())
    cur_dir = cfg.get("direction") if cfg.get("direction") in DIRECTIONS else "auto"
    v_dir = tk.StringVar(value=DIRECTIONS[cur_dir])
    ttk.Combobox(frm, textvariable=v_dir, values=list(DIRECTIONS.values()), state="readonly", width=70).grid(
        row=6, column=0, columnspan=4, sticky="w", **PAD)

    # ---- Опции ---------------------------------------------------------------
    ttk.Label(frm, text="Опции", font=bold).grid(row=7, column=0, columnspan=4, sticky="w", **PAD)
    v_autostart = tk.BooleanVar(value=autostart.is_enabled())
    v_restore = tk.BooleanVar(value=bool(cfg.get("restore_clipboard", True)))
    ttk.Checkbutton(frm, text="Стартирай автоматично при вход в системата", variable=v_autostart).grid(
        row=8, column=0, columnspan=4, sticky="w", **PAD)
    ttk.Checkbutton(frm, text="Възстановявай съдържанието на клипборда след замяна", variable=v_restore).grid(
        row=9, column=0, columnspan=4, sticky="w", **PAD)
    v_sound = tk.BooleanVar(value=bool(cfg.get("sound", True)))
    snd = ttk.Frame(frm)
    snd.grid(row=10, column=0, columnspan=4, sticky="w", **PAD)
    ttk.Checkbutton(snd, text="Звуков сигнал при замяна", variable=v_sound).pack(side="left", padx=(0, 10))

    def play_test_sound():
        from .sound import play_success
        play_success()

    ttk.Button(snd, text="Чуй", width=6, command=play_test_sound).pack(side="left")

    # ---- Проба ---------------------------------------------------------------
    ttk.Label(frm, text="Проба", font=bold).grid(row=11, column=0, columnspan=4, sticky="w", **PAD)
    v_test_in = tk.StringVar(value="Zdrawej, kak si?")
    v_test_out = tk.StringVar()
    ttk.Entry(frm, textvariable=v_test_in, width=72).grid(row=12, column=0, columnspan=4, sticky="w", **PAD)
    ttk.Label(frm, textvariable=v_test_out, font=("TkDefaultFont", 11)).grid(row=13, column=0, columnspan=4, sticky="w", **PAD)

    # ---- Бутони --------------------------------------------------------------
    btns = ttk.Frame(frm)
    btns.grid(row=14, column=0, columnspan=4, sticky="e", pady=(10, 0))

    def current_layout_id() -> str:
        return layout_ids[layout_names.index(v_layout.get())]

    def current_dir_id() -> str:
        return dir_ids[list(DIRECTIONS.values()).index(v_dir.get())]

    def current_hotkey() -> dict:
        key = v_key.get()
        return {
            "ctrl": v_ctrl.get(), "alt": v_alt.get(), "shift": v_shift.get(), "meta": v_meta.get(),
            "key": "space" if key == "Space" else key.lower(),
        }

    def refresh(*_):
        v_preview.set("Текуща комбинация: " + config.hotkey_label(current_hotkey()))
        v_test_out.set("→ " + convert(v_test_in.get(), current_layout_id(), current_dir_id()))

    def save():
        h = current_hotkey()
        if not (h["ctrl"] or h["alt"] or h["shift"] or h["meta"]):
            messagebox.showwarning("KirLat", "Изберете поне един модификатор (Ctrl, Alt, Shift …).", parent=root)
            return
        new_cfg = dict(cfg)
        new_cfg.update({
            "hotkey": h,
            "layout": current_layout_id(),
            "direction": current_dir_id(),
            "restore_clipboard": v_restore.get(),
            "sound": v_sound.get(),
        })
        try:
            config.save(new_cfg)
        except OSError as e:
            messagebox.showerror("KirLat", f"Настройките не могат да бъдат записани:\n{e}", parent=root)
            return
        try:
            if v_autostart.get() != autostart.is_enabled():
                autostart.set_enabled(v_autostart.get())
        except Exception as e:
            messagebox.showwarning("KirLat", f"Автостартът не може да бъде променен:\n{e}", parent=root)
        root.destroy()

    ttk.Button(btns, text="Запази", command=save).pack(side="right", padx=(8, 0))
    ttk.Button(btns, text="Отказ", command=root.destroy).pack(side="right")

    for var in (v_ctrl, v_alt, v_shift, v_meta, v_key, v_layout, v_dir, v_test_in):
        var.trace_add("write", refresh)
    refresh()

    root.bind("<Return>", lambda e: save())
    root.bind("<Escape>", lambda e: root.destroy())
    root.update_idletasks()
    root.lift()
    root.focus_force()
    root.mainloop()


if __name__ == "__main__":
    run()
