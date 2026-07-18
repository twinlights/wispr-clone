"""
Press-and-release detection for a 2-key combination.

Recording starts the instant BOTH configured keys are held down at the
same time, and stops the instant EITHER of them is released.

Keys can be named (see KEY_MAP) or given as a raw X keysym code using
"raw:<number>" — needed for keys like AltGr, which some keyboard layouts
report as an unnamed code instead of pynput's Key.alt_gr constant.
"""
import threading
from pynput import keyboard

KEY_MAP = {
    "cmd": keyboard.Key.cmd,
    "cmd_r": keyboard.Key.cmd_r,
    "alt_gr": keyboard.Key.alt_gr,
    "alt_l": keyboard.Key.alt_l,
    "alt_r": keyboard.Key.alt_r,
    "alt": keyboard.Key.alt_l,
    "ctrl_l": keyboard.Key.ctrl_l,
    "ctrl_r": keyboard.Key.ctrl_r,
    "ctrl": keyboard.Key.ctrl_l,
    "shift_l": keyboard.Key.shift_l,
    "shift_r": keyboard.Key.shift_r,
    "shift": keyboard.Key.shift_l,
}


def _resolve_key(name):
    if name in KEY_MAP:
        return KEY_MAP[name]
    if name.startswith("raw:"):
        vk = int(name.split(":", 1)[1])
        return keyboard.KeyCode(vk=vk)
    raise ValueError(
        f"Unknown key name '{name}'. Valid names: {sorted(KEY_MAP)}, "
        f"or 'raw:<code>' for a raw key code (see scripts/debug_keys.py)."
    )


class HotkeyListener:
    def __init__(self, key_names, on_press_combo, on_release_combo):
        if len(key_names) != 2:
            raise ValueError("Exactly 2 keys must be configured for the combo.")
        self.target_keys = {_resolve_key(name) for name in key_names}
        self.on_press_combo = on_press_combo
        self.on_release_combo = on_release_combo

        self._pressed = set()
        self._combo_active = False
        self._lock = threading.Lock()
        self._listener = None

    def _on_press(self, key):
        with self._lock:
            self._pressed.add(key)
            if not self._combo_active and self.target_keys.issubset(self._pressed):
                self._combo_active = True
                self.on_press_combo()

    def _on_release(self, key):
        with self._lock:
            self._pressed.discard(key)
            if self._combo_active and not self.target_keys.issubset(self._pressed):
                self._combo_active = False
                self.on_release_combo()

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
