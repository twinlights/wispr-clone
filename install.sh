#!/usr/bin/env bash
set -e

echo "== Wispr-clone installer (Kali Linux / X11) =="

sudo apt update
sudo apt install -y \
    python3 python3-venv python3-pip python3-tk \
    portaudio19-dev libportaudio2 \
    xdotool xclip \
    ffmpeg

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "Install done."
echo

# ── Optional: Ollama for punctuation/capitalization polishing ──
echo "──────────────────────────────────────────"
echo "Ollama (optional) — adds punctuation and"
echo "capitalization to transcribed text."
echo "The app works fine without it."
echo "──────────────────────────────────────────"
read -p "Install Ollama and pull llama3.2:1b (~1.3 GB)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo
    if ! command -v ollama &> /dev/null; then
        echo "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
    else
        echo "Ollama is already installed."
    fi
    echo "Pulling llama3.2:1b..."
    ollama pull llama3.2:1b || echo "Pull failed — retry later: ollama pull llama3.2:1b"
    echo "Ollama ready."
    echo
    echo "Next steps:"
    echo "  1. While you still have internet access, pre-cache the Whisper model:"
    echo "       source .venv/bin/activate && python3 scripts/predownload_model.py"
    echo "  2. Run the app:"
    echo "       source .venv/bin/activate && python3 main.py"
    echo "  3. (Optional) Enable polishing in the widget menu (Polishing: ON)"
else
    echo "Skipping Ollama — dictation works without it."
    echo "You can install it later: curl -fsSL https://ollama.com/install.sh | sh"
    echo
    echo "Next steps:"
    echo "  1. While you still have internet access, pre-cache the Whisper model:"
    echo "       source .venv/bin/activate && python3 scripts/predownload_model.py"
    echo "  2. Run the app:"
    echo "       source .venv/bin/activate && python3 main.py"
fi
