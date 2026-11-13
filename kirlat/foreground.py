"""Коя програма е на преден план – за да пропускаме комбинацията към клиенти за отдалечен достъп.

Ако и на двете машини върви KirLat, локалният не бива да прихваща Ctrl+W в прозореца на
Remote Desktop: иначе го поглъща, отдалеченият KirLat никога не го получава, а нашият
Ctrl+C / Ctrl+V минава през бавно синхронизирания RDP клипборд и замяната се проваля.
"""
import logging
import os

from .config import IS_MAC, IS_WIN

log = logging.getLogger(__name__)

# Идентификатори на клиенти за отдалечен достъп: bundle id (macOS) или име на .exe (Windows).
# Bundle id съвпада и по префикс (com.microsoft.rdc → com.microsoft.rdc.macos).
REMOTE_APPS = (
    # macOS
    "com.microsoft.rdc",            # Microsoft Remote Desktop / Windows App
    "com.apple.screensharing",      # Screen Sharing
    "com.p5sys.jump.mac.viewer",    # Jump Desktop
    "com.lemonmojo.royaltsx.app",   # Royal TSX
    "com.philandro.anydesk",        # AnyDesk
    "com.teamviewer.teamviewer",    # TeamViewer
    "com.realvnc.vncviewer",        # RealVNC Viewer
    "com.carriez.rustdesk",         # RustDesk
    # Windows
    "mstsc.exe",                    # Remote Desktop Connection
    "msrdc.exe",                    # Windows App / Azure Virtual Desktop
    "msrdcw.exe",
    "rdcman.exe",                   # Remote Desktop Connection Manager
    "mremoteng.exe",
    "royalts.exe",
    "vmconnect.exe",                # Hyper-V
    "anydesk.exe",
    "teamviewer.exe",
    "vncviewer.exe",
    "tvnviewer.exe",
    "rustdesk.exe",
)


def matches(ids, patterns) -> bool:
    """Дали някой от идентификаторите на програмата съвпада с шаблон (без значение от регистъра)."""
    pats = [str(p).strip().lower() for p in patterns if str(p).strip()]
    for i in ids:
        i = (i or "").lower()
        if not i:
            continue
        for p in pats:
            if i == p or i.startswith(p + "."):
                return True
    return False


def foreground_app_ids() -> set:
    """Идентификатори на програмата на преден план; празно множество, ако не може да се установи."""
    try:
        if IS_MAC:
            return _mac_ids()
        if IS_WIN:
            return _win_ids()
    except Exception:
        log.debug("Foreground app lookup failed", exc_info=True)
    return set()


def _mac_ids() -> set:
    from AppKit import NSWorkspace

    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return set()
    ids = {app.bundleIdentifier(), app.localizedName()}
    url = app.executableURL()
    if url is not None:
        ids.add(os.path.basename(url.path()))
    return {str(i) for i in ids if i}


def _win_ids() -> set:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32")
    kernel32 = ctypes.WinDLL("kernel32")
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return set()
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return set()
    handle = kernel32.OpenProcess(0x1000, False, pid.value)   # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return set()
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buf))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return set()
        return {os.path.basename(buf.value)}
    finally:
        kernel32.CloseHandle(handle)


def make_passthrough_check(cfg: dict):
    """Функция за HotkeyListener: True – не прихващай комбинацията (активен е клиент за отдалечен достъп)."""
    if not cfg.get("passthrough_remote", True):
        return lambda: False
    patterns = list(REMOTE_APPS) + [p for p in cfg.get("passthrough_apps", []) if isinstance(p, str)]

    def check() -> bool:
        ids = foreground_app_ids()
        if matches(ids, patterns):
            log.info("Hotkey passed through to remote session app: %s", ", ".join(sorted(ids)))
            return True
        return False

    return check
