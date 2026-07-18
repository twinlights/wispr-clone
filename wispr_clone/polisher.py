"""
Optional cleanup pass through a local Ollama model (mistral:7b).

Rules enforced via the system prompt:
  - NEVER translate the text.
  - NEVER change the detected language.
  - Only fix punctuation, casing, and obvious filler words/stutters.
  - Never add information that wasn't spoken.

If Ollama is unreachable, times out, or is disabled in config.yaml, the
raw transcript is returned unchanged, so the app degrades gracefully and
keeps working fully offline either way.
"""
import requests

SYSTEM_PROMPT = (
    "You clean up raw speech-to-text transcripts. The text can be in Dutch "
    "(including Flemish/Belgian Dutch) or English.\n"
    "Rules you MUST follow exactly:\n"
    "1. NEVER translate the text into another language, under any circumstance.\n"
    "2. Keep the output in the exact same language as the input.\n"
    "3. Only fix punctuation, capitalization, and remove filler words "
    "(uh, um, euh, ...) and false starts/stutters.\n"
    "4. Do not add, remove, or reinterpret meaning. Do not answer questions "
    "contained in the text - only clean up the transcript itself.\n"
    "5. Reply with ONLY the cleaned text. No explanations, no quotes, no preamble."
)


class Polisher:
    def __init__(self, base_url="http://localhost:11434", model="mistral:7b",
                 timeout=15, enabled=True):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.enabled = enabled

    def polish(self, text, detected_lang=None):
        if not self.enabled or not text.strip():
            return text
        prompt = SYSTEM_PROMPT
        if detected_lang:
            prompt += f"\nThe input language code is '{detected_lang}'. The output must stay in that language."
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "system": prompt,
                    "prompt": text,
                    "stream": False,
                    "options": {"temperature": 0},
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            cleaned = resp.json().get("response", "").strip()
            return cleaned if cleaned else text
        except requests.RequestException:
            # Ollama not running / no network - fall back to the raw transcript.
            return text
