"""
Minimal, always-on-top oval status widget.

Tkinter is used deliberately: it ships with Python, needs no extra
runtime (no Electron/Chromium/Qt), and its memory footprint is a few MB
rather than 100+. It shows "Wispr" when idle and "Recording" (plus a
color change) while the hotkey combo is held.
"""
import queue
import subprocess
import tkinter as tk


# Friendly labels for the hotkey combo shown in the widget.
_KEY_LABELS = {
    "cmd": "\u229E",       # Windows/Super key (squared plus / window logo)
    "cmd_r": "\u229E",
    "alt_gr": "AltGr",
    "alt_l": "Alt",
    "alt_r": "Alt",
    "alt": "Alt",
    "ctrl_l": "Ctrl",
    "ctrl_r": "Ctrl",
    "ctrl": "Ctrl",
    "shift_l": "Shift",
    "shift_r": "Shift",
    "shift": "Shift",
}


class WisprWidget:
    def __init__(self, cfg, on_menu_action=None):
        self.cfg = cfg
        self.on_menu_action = on_menu_action
        self.queue = queue.Queue()

        self.root = tk.Tk()
        self.root.overrideredirect(True)        # borderless
        self.root.attributes("-topmost", True)   # always on top

        # Widget size: tall enough for three lines of text.
        w, h = 160, 80
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        # Left side, roughly two-thirds down the screen.
        x = 30
        y = int(screen_h * 2 / 3)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.canvas = tk.Canvas(self.root, width=w, height=h,
                                 highlightthickness=0, bg="black")
        self.canvas.pack()

        self.oval = self.canvas.create_oval(
            2, 2, w - 2, h - 2, fill=cfg["ui"]["idle_color"], outline=""
        )

        # Three-line display: status, shortcut, model.
        self.status_label = self.canvas.create_text(
            w / 2, 22, text=cfg["ui"]["idle_text"],
            fill="white", font=("Sans", 13, "bold")
        )
        self.shortcut_label = self.canvas.create_text(
            w / 2, 44, text=self._format_shortcut(),
            fill="white", font=("Sans", 10)
        )
        self.model_label = self.canvas.create_text(
            w / 2, 64, text=self._format_model(),
            fill="white", font=("Sans", 9)
        )

        # "..." menu indicator in the top-right corner.
        self.menu_indicator = self.canvas.create_text(
            w - 10, 12, text="...",
            fill="#a0a0a0", font=("Sans", 10, "bold"), anchor="e"
        )
        self.canvas.tag_bind(self.menu_indicator, "<Button-1>", self._show_menu)

        # Let the user drag the widget to a more convenient spot.
        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._do_drag)
        self._drag = (0, 0)

        self._poll()

        # Under systemd autostart, this window can be created a moment
        # before the X session/window manager is fully settled, leaving
        # it invisible until something forces a repaint. Force one
        # ourselves shortly after startup as a safety net.
        self.root.after(800, self._force_repaint)

    def _format_shortcut(self):
        keys = self.cfg["hotkey"]["keys"]
        parts = []
        for key in keys:
            if key in _KEY_LABELS:
                parts.append(_KEY_LABELS[key])
            elif key.startswith("raw:"):
                # 65027 is the common X keysym code for AltGr.
                # See scripts/debug_keys.py if you ever need to remap this.
                code = key.split(":", 1)[1]
                if code == "65027":
                    parts.append("AltGr")
                else:
                    parts.append(f"Key {code}")
            else:
                parts.append(key)
        return " + ".join(parts)

    def _format_model(self):
        return f"Model: {self.cfg['whisper']['model_size']}"

    def _show_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)

        model_menu = tk.Menu(menu, tearoff=0)
        for size in ("tiny", "base", "small", "medium", "large-v3"):
            model_menu.add_command(
                label=size,
                command=lambda s=size: self._on_model_selected(s)
            )
        menu.add_cascade(label="Speech Model Size", menu=model_menu)

        menu.add_separator()

        is_cleaning = self.cfg["ollama"]["enabled"]
        cleaning_label = "Polishing: ON" if is_cleaning else "Polishing: OFF"
        menu.add_command(
            label=cleaning_label,
            command=lambda: self._on_toggle_cleaning(not is_cleaning)
        )

        cleaning_model_menu = tk.Menu(menu, tearoff=0)
        current_cleaning_model = self.cfg["ollama"]["model"]
        available_models = self._get_ollama_models()
        cleaning_model_var = tk.StringVar(value=current_cleaning_model)
        for model in available_models:
            cleaning_model_menu.add_radiobutton(
                label=model,
                variable=cleaning_model_var,
                value=model,
                command=lambda m=model: self._on_cleaning_model_selected(m),
            )
        if not available_models:
            # Ollama isn't running or has no models pulled — still
            # show the configured model so it remains selectable.
            cleaning_model_menu.add_radiobutton(
                label=current_cleaning_model,
                variable=cleaning_model_var,
                value=current_cleaning_model,
            )
            cleaning_model_menu.add_separator()
            cleaning_model_menu.add_command(
                label=f"Pull {current_cleaning_model}",
                command=lambda: self._pull_ollama_model(current_cleaning_model),
            )
        menu.add_cascade(label=f"Ollama Polisher: {current_cleaning_model}", menu=cleaning_model_menu)

        menu.add_separator()
        menu.add_command(label="Open config.yaml", command=self._open_config)
        menu.add_separator()
        menu.add_command(label="Restart Service", command=self._restart_service)
        menu.add_command(label="Quit", command=self.root.quit)

        menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _on_model_selected(self, model_size):
        if self.on_menu_action:
            self.on_menu_action("switch_model", model_size)

    def _on_toggle_cleaning(self, enabled):
        if self.on_menu_action:
            self.on_menu_action("toggle_cleaning", enabled)

    def _on_cleaning_model_selected(self, model):
        if self.on_menu_action:
            self.on_menu_action("switch_cleaning_model", model)

    # Models that definitely can't be used for text polishing.
    # - embedding models (nomic-embed-text, mxbai-embed-large, etc.)
    # - vision-only models (llava, bakllava, qwen*vl, minicpm-v, cogvlm,
    #   moondream) — these often respond with image descriptions, not text cleanup
    _NON_CHAT_PATTERNS = [
        "embed", "llava", "bakllava", "cogvlm", "moondream",
        "minicpm-v", "vl:", "-vision",
    ]

    @classmethod
    def _is_chat_model(cls, name):
        """Return False only for models that definitely can't polish text.

        Uses a conservative blocklist: if we're not sure, the model stays.
        """
        lower = name.lower()
        return not any(p in lower for p in cls._NON_CHAT_PATTERNS)

    def _get_ollama_models(self):
        """Return installed Ollama model names via 'ollama list'.

        Filters out models that definitely can't do text polishing
        (embedding models, vision-only). When in doubt, the model is
        shown — users can always disable polishing if a model misbehaves.

        If Ollama isn't running or no models are pulled, returns only
        the currently configured model so the radiobutton still shows
        what's selected — along with a hint shown separately in the menu.
        """
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode != 0:
                raise RuntimeError("ollama list failed")
            models = []
            for line in result.stdout.strip().split("\n")[1:]:  # skip header
                if line.strip():
                    name = line.split()[0]
                    if self._is_chat_model(name):
                        models.append(name)
            if models:
                current = self.cfg["ollama"]["model"]
                if current not in models:
                    models.append(current)
                return models
        except Exception:
            pass
        # Ollama unreachable or no models pulled.
        return []

    def _pull_ollama_model(self, model):
        """Pull an Ollama model in the background via 'ollama pull'."""
        try:
            subprocess.Popen(
                ["ollama", "pull", model],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            print("[wispr-clone] ollama not found — install it first: "
                  "curl -fsSL https://ollama.com/install.sh | sh")

    def _open_config(self):
        from wispr_clone.config import DEFAULT_CONFIG_PATH
        try:
            subprocess.Popen(["mousepad", str(DEFAULT_CONFIG_PATH)])
        except FileNotFoundError:
            subprocess.Popen(["xdg-open", str(DEFAULT_CONFIG_PATH)])

    def _restart_service(self):
        """Restart the wispr-clone systemd user service."""
        try:
            subprocess.Popen(
                ["systemctl", "--user", "restart", "wispr-clone.service"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass
        self.root.quit()

    def update_model_label(self):
        """Refresh the model label after a model change (thread-safe)."""
        self.root.after(0, self._update_model_label_sync)

    def _update_model_label_sync(self):
        self.canvas.itemconfig(self.model_label, text=self._format_model())

    def _force_repaint(self):
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.set_state("idle")

    def _start_drag(self, event):
        self._drag = (event.x, event.y)

    def _do_drag(self, event):
        x = self.root.winfo_x() + event.x - self._drag[0]
        y = self.root.winfo_y() + event.y - self._drag[1]
        self.root.geometry(f"+{x}+{y}")

    def set_state(self, state):
        """state: 'idle' | 'recording' | 'processing'"""
        ui = self.cfg["ui"]
        mapping = {
            "idle": (ui["idle_text"], ui["idle_color"]),
            "recording": (ui["recording_text"], ui["recording_color"]),
            "processing": (ui.get("processing_text", "..."), ui["processing_color"]),
        }
        text, color = mapping.get(state, mapping["idle"])
        self.canvas.itemconfig(self.oval, fill=color)
        self.canvas.itemconfig(self.status_label, text=text)

    def request_state(self, state):
        """Thread-safe: call this from any background thread."""
        self.queue.put(state)

    def _poll(self):
        try:
            while True:
                state = self.queue.get_nowait()
                self.set_state(state)
        except queue.Empty:
            pass
        self.root.after(50, self._poll)

    def run(self):
        self.root.mainloop()
