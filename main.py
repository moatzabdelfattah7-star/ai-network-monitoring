"""AI Network Monitoring - analyzes network logs with Gemini and alerts via Telegram.

Features:
  - Structured JSON output from the LLM
  - Error handling with retries
  - PII / sensitive-data redaction before anything is sent to the model
"""
import json
import os
import re
import sys
import time

import requests
from google import genai
from google.genai import types

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "sample_logs.txt"
MAX_RETRIES = 3

PROMPT = """You are a senior network engineer.
Analyze the following network logs and answer ONLY with JSON in this shape:
{{
  "severity": "LOW | MEDIUM | HIGH | CRITICAL",
  "summary": "one short sentence",
  "root_cause": "most likely cause",
  "fix_steps": ["step 1", "step 2"]
}}

Logs:
{logs}
"""

# ---------- Privacy: mask sensitive data before sending to the model ----------
REDACTION_RULES = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    (re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"), "[MAC]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP]"),
    (re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*\S+"), r"\1=[REDACTED]"),
]


def redact(text: str) -> str:
    for pattern, replacement in REDACTION_RULES:
        text = pattern.sub(replacement, text)
    return text


# ---------- LLM call with JSON output + error handling ----------
def analyze(logs: str) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    config = types.GenerateContentConfig(response_mime_type="application/json")

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL, contents=PROMPT.format(logs=logs), config=config
            )
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            last_error = f"Model returned invalid JSON: {e}"
        except Exception as e:  # network errors, quota, API errors
            last_error = f"API error: {e}"
        print(f"Attempt {attempt}/{MAX_RETRIES} failed: {last_error}")
        time.sleep(2 ** attempt)
    raise RuntimeError(f"Analysis failed after {MAX_RETRIES} attempts: {last_error}")


def format_alert(result: dict) -> str:
    steps = "\n".join(f"  {i}. {s}" for i, s in enumerate(result.get("fix_steps", []), 1))
    return (
        f"🚨 Network Alert [{result.get('severity', '?')}]\n\n"
        f"Summary: {result.get('summary', '-')}\n"
        f"Root cause: {result.get('root_cause', '-')}\n"
        f"Fix steps:\n{steps}"
    )


def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("(Telegram not configured, skipping alert)")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=15)
        r.raise_for_status()
        print("Telegram alert sent.")
    except requests.RequestException as e:
        print(f"Failed to send Telegram alert: {e}")


def main() -> None:
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            raw_logs = f.read()
    except FileNotFoundError:
        sys.exit(f"Log file not found: {LOG_FILE}")

    safe_logs = redact(raw_logs)
    result = analyze(safe_logs)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    send_telegram(format_alert(result))


if __name__ == "__main__":
    main()
