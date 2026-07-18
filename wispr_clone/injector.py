"""Types the final text into whatever window currently has focus (X11)."""
import shutil
import subprocess


class TextInjector:
    def __init__(self, method="clipboard"):
        self.method = method
        self._check_deps()

    def _check_deps(self):
        if self.method == "clipboard" and not shutil.which("xclip") and not shutil.which("xsel"):
            raise RuntimeError(
                "xclip or xsel is required for clipboard injection. "
                "Install with: sudo apt install xclip"
            )
        if not shutil.which("xdotool"):
            raise RuntimeError(
                "xdotool is required. Install with: sudo apt install xdotool "
                "(note: xdotool needs an X11 session; use XWayland if on Wayland)."
            )

    def inject(self, text):
        if not text:
            return
        if self.method == "clipboard":
            self._inject_via_clipboard(text)
        else:
            self._inject_via_type(text)

    def _inject_via_clipboard(self, text):
        # Clipboard + paste is more reliable than simulated typing for
        # Dutch/Flemish diacritics (é, ë, ï, etc.).
        if shutil.which("xclip"):
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode("utf-8"),
                check=True,
            )
        else:
            subprocess.run(
                ["xsel", "--clipboard", "--input"],
                input=text.encode("utf-8"),
                check=True,
            )
        subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"], check=True)

    def _inject_via_type(self, text):
        subprocess.run(["xdotool", "type", "--clearmodifiers", "--", text], check=True)
