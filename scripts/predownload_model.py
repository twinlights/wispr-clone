"""
Run this ONCE while the machine still has internet access, so the
Whisper models get cached locally (under ~/.cache/huggingface). After
that, wispr-clone never needs the network again to transcribe speech.

By default all supported model sizes are cached, so switching between
them from the widget menu is instant.

Usage:
    source .venv/bin/activate
    python3 scripts/predownload_model.py

To cache only the model currently configured in config.yaml:
    python3 scripts/predownload_model.py --current
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faster_whisper import WhisperModel
from wispr_clone.config import load_config

ALL_SIZES = ["tiny", "base", "small", "medium", "large-v3"]


def main():
    parser = argparse.ArgumentParser(description="Pre-cache Whisper models for offline use.")
    parser.add_argument(
        "--current",
        action="store_true",
        help="Only download the model size currently set in config.yaml.",
    )
    args = parser.parse_args()

    cfg = load_config()
    compute_type = cfg["whisper"]["compute_type"]

    if args.current:
        sizes = [cfg["whisper"]["model_size"]]
    else:
        sizes = ALL_SIZES

    failed = []
    for size in sizes:
        print(f"Downloading/caching Whisper model '{size}' (compute_type={compute_type}) ...")
        try:
            WhisperModel(size, device="cpu", compute_type=compute_type)
            print(f"  Done: {size}")
        except Exception as exc:
            print(f"  Failed to cache '{size}': {exc}")
            failed.append(size)

    if failed:
        print(f"Some models failed to cache: {failed}")
    else:
        print("All requested models are cached locally and no longer need internet access.")


if __name__ == "__main__":
    main()
