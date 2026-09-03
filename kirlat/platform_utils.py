import os
import sys

from .config import APP_NAME, IS_MAC, IS_WIN, config_dir

_lock_handle = None


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_command() -> list:
    """Команден ред, с който се стартира самото приложение."""
    if is_frozen():
        return [sys.executable]
    exe = sys.executable
    if IS_WIN:
        pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.exists(pyw):
            exe = pyw
    main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    return [exe, main_py]


def acquire_single_instance() -> bool:
    """True ако сме единствената работеща инстанция."""
    global _lock_handle
    if IS_WIN:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, f"Local\\{APP_NAME}.SingleInstance")
        if not handle:
            return True
        _lock_handle = handle
        return kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
    import fcntl
    os.makedirs(config_dir(), exist_ok=True)
    fh = open(os.path.join(config_dir(), "instance.lock"), "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    _lock_handle = fh
    return True


def mac_accessibility_trusted(prompt: bool = True) -> bool:
    """macOS: дали приложението има разрешение за Accessibility (при нужда показва системния диалог)."""
    if not IS_MAC:
        return True
    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
        return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: prompt}))
    except Exception:
        return True
