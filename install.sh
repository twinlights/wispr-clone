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
echo "Next steps:"
echo "  1. While you still have internet access, pre-cache the Whisper model:"
echo "       source .venv/bin/activate && python3 scripts/predownload_model.py"
echo "  2. Make sure Ollama is running with mistral:7b already pulled:"
echo "       ollama list"
echo "  3. Run the app:"
echo "       source .venv/bin/activate && python3 main.py"
