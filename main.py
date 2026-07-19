"""
Wispr-clone entry point.

Flow:
  1. User presses and HOLDS the configured 2-key combo -> recording
     starts, the oval widget turns red / shows "Recording".
  2. User releases either key -> recording stops immediately, widget
     shows a "processing" state while the audio is transcribed locally
     (faster-whisper, Dutch/Flemish + English) and optionally polished
     via Ollama (mistral:7b) - cleanup only, translation is forbidden.
  3. The resulting text is typed into whatever window currently has
     focus.
  4. Widget returns to idle "Wispr" state, ready for the next press.
"""
import re
import threading

from wispr_clone.config import load_config, DEFAULT_CONFIG_PATH
from wispr_clone.hotkey import HotkeyListener
from wispr_clone.audio import AudioRecorder
from wispr_clone.transcriber import Transcriber
from wispr_clone.polisher import Polisher
from wispr_clone.injector import TextInjector
from wispr_clone.ui import WisprWidget


def main():
    cfg = load_config()

    recorder = AudioRecorder(
        sample_rate=cfg["audio"]["sample_rate"],
        channels=cfg["audio"]["channels"],
    )
    print("Loading Whisper model (first run may take a moment)...")
    transcriber = Transcriber(
        model_size=cfg["whisper"]["model_size"],
        device=cfg["whisper"]["device"],
        compute_type=cfg["whisper"]["compute_type"],
        language=cfg["whisper"]["language"],
    )
    polisher = Polisher(
        base_url=cfg["ollama"]["base_url"],
        model=cfg["ollama"]["model"],
        timeout=cfg["ollama"]["timeout"],
        enabled=cfg["ollama"]["enabled"],
    )
    injector = TextInjector(method=cfg["injection"]["method"])

    state_lock = threading.Lock()
    busy = {"value": False}

    def on_menu_action(action, value=None):
        if action == "switch_model":
            with state_lock:
                if busy["value"]:
                    print("[wispr-clone] cannot switch model while recording/processing")
                    return
                busy["value"] = True
            model_size = value

            def do_reload():
                try:
                    widget.request_state("processing")
                    with state_lock:
                        transcriber.reload_model(model_size)
                    cfg["whisper"]["model_size"] = model_size
                    _persist_model_size(model_size)
                    widget.update_model_label()
                    print(f"[wispr-clone] switched to model: {model_size}")
                except Exception as exc:
                    print(f"[wispr-clone] failed to switch model: {exc}")
                finally:
                    widget.request_state("idle")
                    with state_lock:
                        busy["value"] = False

            threading.Thread(target=do_reload, daemon=True).start()

        elif action == "toggle_cleaning":
            with state_lock:
                cfg["ollama"]["enabled"] = value
                polisher.enabled = value
            _persist_cleaning_state(value)
            print(f"[wispr-clone] cleaning set to: {value}")

        elif action == "switch_cleaning_model":
            with state_lock:
                cfg["ollama"]["model"] = value
                polisher.model = value
            _persist_ollama_model(value)
            print(f"[wispr-clone] cleaning model set to: {value}")

    widget = WisprWidget(cfg, on_menu_action=on_menu_action)

    def on_press_combo():
        with state_lock:
            if busy["value"]:
                return
            busy["value"] = True
        widget.request_state("recording")
        recorder.start()

    def on_release_combo():
        widget.request_state("processing")
        audio = recorder.stop()

        def worker():
            try:
                with state_lock:
                    text, lang = transcriber.transcribe(
                        audio, sample_rate=cfg["audio"]["sample_rate"]
                    )
                    text = polisher.polish(text, detected_lang=lang)
                injector.inject(text)
            except Exception as exc:  # keep the app alive on any failure
                print(f"[wispr-clone] error while processing speech: {exc}")
            finally:
                widget.request_state("idle")
                with state_lock:
                    busy["value"] = False

        threading.Thread(target=worker, daemon=True).start()

    listener = HotkeyListener(
        key_names=cfg["hotkey"]["keys"],
        on_press_combo=on_press_combo,
        on_release_combo=on_release_combo,
    )
    listener.start()
    print(f"Ready. Hold {cfg['hotkey']['keys']} to record.")

    try:
        widget.run()
    finally:
        listener.stop()


def _persist_model_size(model_size):
    """Update model_size in config.yaml while preserving comments."""
    path = DEFAULT_CONFIG_PATH
    text = path.read_text(encoding="utf-8")
    # Match lines like: model_size: "small"  or  model_size: small
    new_text, count = re.subn(
        r'^(\s*model_size:\s*).*$',
        r'\1"' + model_size + '"',
        text,
        flags=re.MULTILINE,
    )
    if count:
        path.write_text(new_text, encoding="utf-8")


def _persist_cleaning_state(enabled):
    """Update ollama.enabled in config.yaml while preserving comments."""
    path = DEFAULT_CONFIG_PATH
    text = path.read_text(encoding="utf-8")
    val_str = "true" if enabled else "false"
    # Match the indented enabled line under the ollama section.
    new_text, count = re.subn(
        r'^(  enabled:\s*).*$',
        r'\1' + val_str,
        text,
        flags=re.MULTILINE,
    )
    if count:
        path.write_text(new_text, encoding="utf-8")


def _persist_ollama_model(model):
    """Update ollama.model in config.yaml while preserving comments."""
    path = DEFAULT_CONFIG_PATH
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(
        r'^(  model:\s*).*$',
        r'\1"' + model + '"',
        text,
        flags=re.MULTILINE,
    )
    if count:
        path.write_text(new_text, encoding="utf-8")


if __name__ == "__main__":
    main()
