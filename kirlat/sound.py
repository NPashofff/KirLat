"""Кратък звуков сигнал при успешна замяна."""
import io
import logging
import math
import struct
import subprocess
import wave

from .config import IS_MAC, IS_WIN

log = logging.getLogger(__name__)

_wav_cache = None
_ns_sound = None   # пазим референция, докато свири


def _wav_bytes() -> bytes:
    """Двутонов „пинг“ (A5 → D6), ~140 ms, генериран в паметта."""
    global _wav_cache
    if _wav_cache is not None:
        return _wav_cache
    rate, dur = 44100, 0.14
    n = int(rate * dur)
    frames = bytearray()
    for i in range(n):
        t = i / rate
        freq = 880.0 if t < dur / 2 else 1174.66
        env = min(1.0, t / 0.005) * min(1.0, (dur - t) / 0.04)
        frames += struct.pack("<h", int(0.35 * 32767 * env * math.sin(2 * math.pi * freq * t)))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    _wav_cache = buf.getvalue()
    return _wav_cache


def play_success() -> None:
    """Пуска сигнала асинхронно; грешките само се логват."""
    global _ns_sound
    try:
        if IS_WIN:
            import threading
            import winsound
            # SND_MEMORY не може да е асинхронно → свирим синхронно в отделна нишка (~140 ms)
            data = _wav_bytes()
            threading.Thread(
                target=lambda: winsound.PlaySound(data, winsound.SND_MEMORY | winsound.SND_NODEFAULT),
                daemon=True,
            ).start()
            return
        if IS_MAC:
            try:
                from AppKit import NSSound
                _ns_sound = NSSound.soundNamed_("Pop")
                if _ns_sound is not None and _ns_sound.play():
                    return
            except Exception:
                pass
            subprocess.Popen(["afplay", "/System/Library/Sounds/Pop.aiff"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        # Linux: paplay/aplay от временен файл, иначе системен beep
        import os
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".wav")
        with os.fdopen(fd, "wb") as f:
            f.write(_wav_bytes())
        for cmd in (["paplay", path], ["aplay", "-q", path]):
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue
        print("\a", end="", flush=True)
    except Exception:
        log.exception("Sound failed")
