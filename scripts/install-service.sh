#!/usr/bin/env bash
# Install the wispr-clone systemd user service.
#
# This script detects the project directory from its own location, writes
# a service file with the correct absolute path, and enables/starts it.
# It is safe to re-run after moving the repository.

set -euo pipefail

# User services must be installed as the normal user, never root.
if [ "$(id -u)" -eq 0 ]; then
    echo "error: do not run this script with sudo/root." >&2
    echo "       User systemd services must be installed as your normal user." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WRAPPER="$PROJECT_DIR/scripts/wispr-clone-launch.sh"
SERVICE_DIR="${HOME}/.config/systemd/user"
SERVICE_DST="$SERVICE_DIR/wispr-clone.service"

SERVICE_SRC="$PROJECT_DIR/systemd/wispr-clone.service"
if [ ! -f "$SERVICE_SRC" ]; then
    echo "error: service template not found at $SERVICE_SRC" >&2
    exit 1
fi

if [ ! -f "$WRAPPER" ]; then
    echo "error: launch wrapper not found at $WRAPPER" >&2
    exit 1
fi

chmod +x "$WRAPPER"

PYTHON_BIN="$PROJECT_DIR/.venv/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "error: Python venv not found at $PYTHON_BIN" >&2
    exit 1
fi

mkdir -p "$SERVICE_DIR"

# If the directory itself is not writable (e.g. owned by root), fail early
# with a clear explanation.
if [ ! -w "$SERVICE_DIR" ]; then
    owner="$(stat -c '%U' "$SERVICE_DIR")"
    echo "error: $SERVICE_DIR is owned by $owner and is not writable." >&2
    echo "       Fix it with:" >&2
    echo "         sudo chown $(id -un):$(id -gn) $SERVICE_DIR" >&2
    echo "       Then run this script again as your normal user." >&2
    exit 1
fi

# Make sure a systemd user session bus is available. This can fail if the
# script is run from a bare SSH/tmux session without XDG_RUNTIME_DIR.
if ! systemctl --user status >/dev/null 2>&1; then
    echo "error: cannot connect to the systemd user bus." >&2
    echo "       Make sure you are logged in to a graphical session, or set:" >&2
    echo "         export XDG_RUNTIME_DIR=\"/run/user/$(id - u)\"" >&2
    exit 1
fi

# If an existing service file is owned by root (usually from a previous
# accidental sudo run), we cannot overwrite it as the normal user. Detect
# this and tell the user exactly how to fix it.
if [ -e "$SERVICE_DST" ] && [ ! -w "$SERVICE_DST" ]; then
    owner="$(stat -c '%U' "$SERVICE_DST")"
    echo "error: $SERVICE_DST is owned by $owner and is not writable." >&2
    echo "       This usually happens when the service was previously" >&2
    echo "       installed with sudo. Fix it with:" >&2
    echo "         sudo rm $SERVICE_DST" >&2
    echo "       Then run this script again as your normal user." >&2
    exit 1
fi

# Generate the service file from the template, replacing the working
# directory and wrapper path. We escape only the sed replacement
# metacharacters (& and \) so paths are inserted literally.
escape_sed_replacement() {
    printf '%s' "$1" | sed 's/[\\&]/\\&/g'
}
escaped_workdir="$(escape_sed_replacement "$PROJECT_DIR")"
escaped_wrapper="$(escape_sed_replacement "$WRAPPER")"
sed \
    -e "s|@@WORKDIR@@|$escaped_workdir|g" \
    -e "s|@@WRAPPER@@|$escaped_wrapper|g" \
    "$SERVICE_SRC" > "$SERVICE_DST"

echo "Installed: $SERVICE_DST"

systemctl --user daemon-reload
systemctl --user enable wispr-clone.service

if systemctl --user is-active --quiet wispr-clone.service; then
    echo "Service already running; restarting..."
    systemctl --user restart wispr-clone.service
else
    echo "Starting service..."
    systemctl --user start wispr-clone.service
fi

systemctl --user status wispr-clone.service --no-pager
