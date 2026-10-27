# AI Network Monitoring System

Automated network log analysis powered by **Google Gemini**, with instant **Telegram** alerts. Built with an n8n workflow plus a standalone Python script.

## Architecture

```
Trigger -> Python Code -> If (error?) -> Edit Fields -> Gemini -> Google Sheets
                                                          \-> Telegram Alert
```

- **n8n workflow**: ingests logs, filters errors, asks Gemini for diagnosis, stores results in Google Sheets, and sends a Telegram alert.
- **`main.py`**: standalone version that analyzes a log file with Gemini and sends the result to Telegram.

## Features
- AI-based root-cause analysis and severity rating
- **Structured JSON output** from the model (severity, summary, root cause, fix steps)
- **Error handling**: retries with backoff, invalid-JSON detection, graceful Telegram failures
- **Privacy by default**: IPs, MAC addresses, emails and secrets are masked before logs leave the machine
- Real-time Telegram notifications
- Incident history in Google Sheets

## Setup

```bash
git clone https://github.com/<your-username>/ai-network-monitoring.git
cd ai-network-monitoring
pip install -r requirements.txt
```

Set environment variables (PowerShell):

```powershell
$env:GEMINI_API_KEY="your_key"
$env:TELEGRAM_BOT_TOKEN="your_bot_token"   # optional
$env:TELEGRAM_CHAT_ID="your_chat_id"       # optional
```

## Run

```bash
python main.py sample_logs.txt
```

Example output:

```json
{
  "severity": "HIGH",
  "summary": "Core switch uplink down causing OSPF and BGP failures.",
  "root_cause": "Interface Gi0/1 on core-sw1 went down.",
  "fix_steps": ["Check cable/SFP on Gi0/1", "Verify OSPF neighbor recovery"]
}
```

## Data Privacy & Responsible Use

Logs can contain sensitive information. Before anything is sent to the LLM, `redact()` masks:

| Data | Replaced with |
|------|---------------|
| IPv4 addresses | `[IP]` |
| MAC addresses | `[MAC]` |
| Email addresses | `[EMAIL]` |
| `password=`, `token=`, `api_key=` values | `[REDACTED]` |

Guidelines:
- Never send credentials, customer personal data, or full config files to a third-party model.
- Treat AI output as a **recommendation**; a human should review before applying fixes on production devices.
- Keep API keys in environment variables, never in the repo.

## Concepts & Future Work

**RAG (Retrieval-Augmented Generation)**: instead of relying on the model's general knowledge, relevant internal documents (runbooks, past incidents, vendor manuals) are retrieved and added to the prompt, so answers match the company's own procedures. Planned: index past incidents from Google Sheets and retrieve similar ones for each new alert.

**AI agents**: an agent lets the model decide which tool to call (e.g. ping a device, query a monitoring API) in a loop. Use a plain LLM call for fixed tasks like this project's log analysis; use an agent when the next step depends on intermediate results (multi-step troubleshooting). Agents that act on production devices should require human approval.

## Tech Stack
Python, n8n, Google Gemini API, Telegram Bot API, Google Sheets
