"""
Diagnostic helper: prints the exact key name pynput sees for every key you
press/release. Use this to find out what your Windows key and AltGr key
are actually reported as, so config.yaml can be set correctly.
"""
from pynput import keyboard


def on_press(key):
    print(f"PRESS   -> {key!r}")


def on_release(key):
    print(f"RELEASE -> {key!r}")


print("Listening for key presses. Press Ctrl+C to stop.")
print("Try: Windows key alone, AltGr alone, Ctrl alone, Alt alone.\n")

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
