#!/usr/bin/env bash
# Launch wrapper for wispr-clone systemd user service.
#
# User services started at graphical-session startup often run before the
# sound server or X11/Wayland environment is fully ready. This script waits
# for the required pieces, then execs the app so the service inherits a
# sane environment.

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Wait for the audio server (PipeWire or PulseAudio).
# ---------------------------------------------------------------------------
wait_for_audio() {
    local tries=0
    while true; do
        # PipeWire is the modern default on most desktops.
        if pgrep -x pipewire >/dev/null 2>&1; then
            return 0
        fi
        # PulseAudio fallback.
        if pgrep -x pulseaudio >/dev/null 2>&1; then
            return 0
        fi
        tries=$((tries + 1))
        if [ "$tries" -ge 30 ]; then
            echo "wispr-clone-launch: warning: audio server not ready after 30s, continuing anyway" >&2
            return 0
        fi
        sleep 1
    done
}

# ---------------------------------------------------------------------------
# 2. Discover the active graphical session if the environment is missing.
# ---------------------------------------------------------------------------
detect_display() {
    # If DISPLAY is already set, trust it.
    if [ -n "${DISPLAY:-}" ]; then
        return 0
    fi

    # Try to infer it from the active logind session.
    if command -v loginctl >/dev/null 2>&1; then
        local session
        session="$(loginctl show-user "${USER}" --property=Display --value 2>/dev/null || true)"
        if [ -n "$session" ]; then
            local display
            display="$(loginctl show-session "$session" --property=Display --value 2>/dev/null || true)"
            if [ -n "$display" ]; then
                export DISPLAY="$display"
                return 0
            fi
        fi
    fi

    # Fallback: look at active local X sessions via the `w` command.
    if command -v w >/dev/null 2>&1; then
        local display
        display="$(w -sh 2>/dev/null | awk '/tty[0-9]+/ {print $3; exit}' || true)"
        if [ -n "$display" ] && [[ "$display" == :* ]]; then
            export DISPLAY="$display"
            return 0
        fi
    fi

    # Last resort: assume :0 (most common default) and log a warning.
    echo "wispr-clone-launch: warning: could not detect DISPLAY; falling back to :0" >&2
    export DISPLAY=":0"
}

detect_xauthority() {
    if [ -n "${XAUTHORITY:-}" ]; then
        return 0
    fi
    if [ -n "${HOME:-}" ] && [ -f "${HOME}/.Xauthority" ]; then
        export XAUTHORITY="${HOME}/.Xauthority"
    fi
}

# ---------------------------------------------------------------------------
# 3. Run the app.
# ---------------------------------------------------------------------------
wait_for_audio
detect_display
detect_xauthority

# Derive the app directory from this script's location so the service file
# does not need to hardcode it. The wrapper is expected to live at
# <project-root>/wispr-clone/scripts/wispr-clone-launch.sh.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ ! -d "$APP_DIR" ]; then
    echo "wispr-clone-launch: error: ${APP_DIR} does not exist" >&2
    exit 1
fi

PYTHON_BIN="$APP_DIR/.venv/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "wispr-clone-launch: error: venv Python not found at $PYTHON_BIN" >&2
    exit 1
fi

cd "$APP_DIR"
exec "$PYTHON_BIN" "$APP_DIR/main.py" "$@"
