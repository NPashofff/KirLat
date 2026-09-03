"""KirLat – стартов файл.

  python main.py               стартира приложението в трея
  python main.py --settings    отваря само прозореца с настройки
  python main.py --convert T   отпечатва преобразувания текст T (за проба)
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kirlat import config  # noqa: E402


def _setup_logging() -> None:
    try:
        os.makedirs(config.config_dir(), exist_ok=True)
        handlers = [logging.FileHandler(config.log_path(), encoding="utf-8")]
    except OSError:
        handlers = []
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=handlers)


def main(argv) -> int:
    _setup_logging()

    if "--settings" in argv:
        from kirlat.settings_gui import run
        run()
        return 0

    if "--convert" in argv:
        from kirlat.converter import convert
        text = " ".join(argv[argv.index("--convert") + 1:])
        cfg = config.load()
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
        print(convert(text, cfg["layout"], cfg["direction"]))
        return 0

    from kirlat.platform_utils import acquire_single_instance
    if not acquire_single_instance():
        # Вече работи – показваме настройките; работещата инстанция ще ги презареди сама.
        from kirlat.settings_gui import run
        run()
        return 0

    from kirlat.tray import TrayApp
    TrayApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
