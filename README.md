# MAXA Store — Telegram bot MVP

## Run
Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN='YOUR_TOKEN_FROM_BOTFATHER'
python bot.py
```

Windows PowerShell: `.venv\\Scripts\\Activate.ps1` and `$env:BOT_TOKEN='YOUR_TOKEN_FROM_BOTFATHER'`.

Keep the token private. Do not commit `.env` or the database to source control.

## Included
- `/start` registers users in SQLite
- Inline navigation: catalog, devices, subscription, support
- `/support your message` saves support requests to SQLite

## Not included
Payment processing, IPA uploads, signing, device enrollment, Mini App, admin dashboard, or automated support replies. UI screens are placeholders.
