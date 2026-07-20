# Wispr-clone

[![CI](https://github.com/twinlights/wispr-clone/actions/workflows/ci.yml/badge.svg)](https://github.com/twinlights/wispr-clone/actions/workflows/ci.yml)

A local, offline push-to-talk dictation tool for Kali Linux, modeled on Wisprflow.

<video src="demo.mp4" autoplay loop muted playsinline controls width="100%"></video>

> Record your own demo at [screenrecorder.dev](https://screenrecorder.dev), save as `demo.mp4`, and drop it into the repo.

- **Hold-to-record**: recording starts the instant a 2-key combo is held
  down together, and stops the instant either key is released (true
  press-and-release, not a toggle, not a 3-key shortcut).
- **Fully offline** speech-to-text via `faster-whisper` (multilingual,
  handles Dutch/Flemish and English, auto-detected per utterance).
- **Optional local cleanup pass** via your existing Ollama model
  (`llama3.2:1b` by default, or any chat model you have pulled). Whisper already
  removes filler words ("uh", "euhm", stutters) on its own — the
  Ollama pass is for punctuation, capitalization, and sentence
  structure. Translation is explicitly forbidden, and if Ollama
  is unreachable the raw transcript is used instead, so the tool
  never depends on it.
- **Tiny UI**: a plain Tkinter oval widget ("Wispr" / "Recording" / "...")
  — a few MB of RAM, no Electron/Chromium/Qt involved.
- Typed text goes straight into whatever window currently has focus.

# How the hotkey works

Configured in `config.yaml` as exactly 2 keys, e.g.:

```yaml
hotkey:
  keys: ["cmd", "alt_gr"]   # Windows key + AltGr
```

Both keys must be held down **together** to start recording; releasing
**either one** stops it. This is not a single "shortcut" keypress like
Win+Alt+V — it's a genuine hold-to-talk gesture using 2 physical keys,
matching what you asked for. Other valid key names: `cmd_r`, `alt_l`,
`alt_r`, `ctrl_l`, `ctrl_r`, `shift_l`, `shift_r`.

AltGr and the Windows/Super key were chosen as the default combo
specifically because they're never produced by normal typing or by other
common shortcuts, so there's effectively no accidental-trigger risk.

## Install (Kali Linux, X11)

```bash
cd wispr-clone
chmod +x install.sh
./install.sh
```

This installs system packages (`xdotool`, `xclip`, PortAudio, Tk) and
creates a Python virtualenv with the pinned dependencies.

**Wayland note**: `xdotool` requires X11. If your Kali session runs
Wayland, either switch to the X11 session at the login screen, or run
this under XWayland. There's no code change needed either way — it's a
session-type issue, not an app issue.

## Before you go offline: cache the Whisper models

`faster-whisper` downloads its model from Hugging Face the first time
it's used. Do this once, while you still have internet:

```bash
source .venv/bin/activate
python3 scripts/predownload_model.py
```

This caches **all** supported models (`tiny`, `base`, `small`, `medium`,
`large-v3`) under `~/.cache/huggingface`, so switching between them
from the widget menu is instant and the app never needs the network
again. To cache only the currently configured model instead, run:

```bash
python3 scripts/predownload_model.py --current
```

## Ollama (optional)

Whisper already produces clean text out of the box — it removes filler
words ("uh", "euhm", stutters) and false starts natively, because its
training data was transcribed by humans who already cleaned those up.

The optional Ollama pass adds **punctuation and capitalization** on
top, plus smoother sentence structure. If you're happy with the raw
Whisper output, you can leave Ollama disabled (`ollama.enabled: false`)
and the tool works perfectly offline with zero extra RAM.

To enable cleaning, make sure a chat model is pulled and running.
The default is `llama3.2:1b` (~1.3 GB) — small, fast, and more than
capable for punctuation and capitalization.  For better sentence
structure, switch to `mistral:7b` (~4.4 GB) in the menu or config.

```bash
ollama list
```

No extra setup needed — the app just calls `http://localhost:11434`.
If Ollama isn't running, the app still works and simply skips the
cleanup step (you get the raw transcript).

## Run

```bash
source .venv/bin/activate
python3 main.py
```

An oval "Wispr" widget appears in the top-right corner (drag it anywhere
you like). Hold Win+AltGr, speak, release — the cleaned-up text is typed
into whatever window has focus.

## Autostart (optional)

The repository includes a systemd **user** service that starts automatically
when you log in to your graphical session.

### Quick install

```bash
chmod +x scripts/wispr-clone-launch.sh scripts/install-service.sh
./scripts/install-service.sh
```

The install script detects the project directory, writes the service file
with the correct absolute path, and enables/starts the service.

### Check status and logs

```bash
systemctl --user status wispr-clone.service
journalctl --user -u wispr-clone.service -f
```

### How the service is made robust

- It waits for `graphical-session.target` and `sound.target`, so it starts
  only after the desktop and audio server (PipeWire/PulseAudio) are ready.
- It uses `scripts/wispr-clone-launch.sh` to detect the correct `DISPLAY`
  and `XAUTHORITY` instead of hardcoding `DISPLAY=:0`.
- It passes through the session environment (`PATH`, `XDG_SESSION_TYPE`,
  `XDG_CURRENT_DESKTOP`, `XDG_RUNTIME_DIR`, etc.) so `xdotool`, `xclip`,
  and the Tkinter widget work correctly.
- It restarts automatically on failure (`Restart=on-failure`).

### Manual install (if you prefer)

Run this from the project root (the directory that contains `main.py`):

```bash
chmod +x scripts/wispr-clone-launch.sh
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/wispr-clone.service <<EOF
[Unit]
Description=Wispr-clone push-to-talk dictation
After=graphical-session.target sound.target
Wants=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/scripts/wispr-clone-launch.sh
Restart=on-failure
RestartSec=5
PassEnvironment=PATH DISPLAY XAUTHORITY XDG_SESSION_TYPE XDG_CURRENT_DESKTOP XDG_RUNTIME_DIR HOME USER
KillMode=mixed
TimeoutStopSec=10

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now wispr-clone.service
```

### Disabling autostart

```bash
systemctl --user disable --now wispr-clone.service
```

## Tuning for your hardware (HP 850 G8, 16GB RAM)

`config.yaml` → `whisper.model_size`:

| Size   | Approx. RAM (int8) | Notes                                  |
|--------|---------------------|-----------------------------------------|
| tiny   | ~150 MB             | fast, noticeably worse accuracy on NL   |
| small  | ~500 MB             | **default** — good balance              |
| medium | ~1.5 GB             | better Flemish accuracy, still fine on 16GB alongside Ollama |
| large-v3 | ~3 GB+            | best accuracy, only if you have headroom |

Mistral:7b via Ollama typically uses ~4–5GB resident, `llama3.2:1b`
uses ~2GB, so `small` or `medium` both leave comfortable headroom on
a 16GB machine.

## Project layout

```
wispr-clone/
├── config.yaml            # hotkey, model, UI settings
├── main.py                 # orchestrator / entry point
├── wispr_clone/
│   ├── hotkey.py            # press-and-release 2-key combo detection
│   ├── audio.py             # mic recording while combo is held
│   ├── transcriber.py       # faster-whisper (offline STT)
│   ├── polisher.py          # Ollama mistral:7b cleanup (no translation)
│   ├── injector.py          # types text into the focused window
│   └── ui.py                 # oval Tkinter status widget
├── scripts/predownload_model.py
├── systemd/wispr-clone.service
├── install.sh
└── requirements.txt
```

## Shell compatibility (zsh)

Everything here works fine with zsh as your default shell, no changes needed:

- `install.sh` starts with `#!/usr/bin/env bash`, so `./install.sh` always
  runs under bash regardless of your login shell.
- `source .venv/bin/activate` works the same in zsh as in bash — the
  venv module generates a POSIX-compatible `activate` script.
- The systemd service calls the venv's Python binary directly by path,
  bypassing the shell entirely.

Optional convenience: add this to `~/.zshrc` to start/activate the app
with a single command from anywhere:

```zsh
wispr() {
  ( cd ~/wispr-clone && source .venv/bin/activate && python3 main.py )
}
```

Then just run `wispr` in a terminal.

## Troubleshooting

- **Nothing types out**: check `xdotool key --clearmodifiers ctrl+v`
  works manually in a text editor; some apps ignore synthetic paste.
  Switch `injection.method` to `"type"` in `config.yaml` as a fallback
  (slower, but works even where paste doesn't).
- **AltGr isn't detected**: some keyboard layouts/X servers report AltGr
  as a compose key rather than `alt_gr`. Try `["cmd", "ctrl_r"]` instead.
- **Mic not found**: run `python3 -c "import sounddevice as sd; print(sd.query_devices())"`
  to list devices; set the default input in your OS sound settings.
- **High CPU on transcription**: drop `whisper.model_size` to `tiny` or
  `small`, and make sure `compute_type: "int8"` is set.
