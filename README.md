# CShop Telegram Shopping Bot

A Persian-first (RTL-friendly) Telegram shopping bot built with Python 3.11+, aiogram 3, SQLAlchemy 2 async, and SQLite. Prices are integer Iranian Tomans. Payment is manual bank transfer with receipt review; receipt approval and fulfillment are separate states. Telegram Stars promotional rewards are internal CShop points, not Telegram's native wallet balance.

## Features in this MVP

- Persian inline-keyboard menu, dynamic database-backed product listing and price list.
- Fixed and per-unit pricing, server-side integer calculations, Stars minimum quantity guard.
- Manual payment card configuration, receipt upload and admin approve/reject workflow.
- Numeric `ADMIN_IDS` authorization on administrative routes; empty admin list fails closed.
- Admin statistics and product activate/deactivate toggles.
- Referral deep links, self-referral prevention and one-time ledger reward service.
- Async SQLAlchemy models, SQLite, tests and GitHub Actions.

**MVP limitations:** in-chat discount creation/application, a complete settings/customer-management UI, and production provider fulfillment adapters are not yet implemented. Product add/edit/price/delete operations are available to admins through restricted `/product` commands; activation and receipt review are available in the Telegram admin UI. The included initial Alembic revision is a bootstrap revision, not a long-term schema evolution strategy. `create_all` initializes the current schema. For production, add Alembic revisions, provider-specific fulfillment integrations, stronger concurrency testing on the chosen database, monitoring, backups and a full admin workflow before accepting live orders. Fake reactions/views and Premium/Stars delivery depend on third-party providers and/or Telegram policies; no provider delivery is claimed by this generic MVP.

## Requirements

- Python 3.11 or newer
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- Numeric Telegram user ID(s) for administrators
- Outbound network access to Telegram Bot API

## Setup — Linux/macOS

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL> cshop-bot
cd cshop-bot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`, set `BOT_TOKEN`, `ADMIN_IDS`, `BOT_USERNAME`, card details and support username. Never commit `.env`.

## Setup — Windows PowerShell

```powershell
git clone <YOUR_GITHUB_REPOSITORY_URL> cshop-bot
Set-Location cshop-bot
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

## Create the Telegram bot and find your ID

1. Open [@BotFather](https://t.me/BotFather), run `/newbot`, follow the prompts, and copy the token into `BOT_TOKEN`.
2. Set `BOT_USERNAME` to the bot's username without `@`.
3. To obtain your numeric user ID, use a reputable ID utility bot or inspect the `from_user.id` value in a private bot update during development. Put one or more comma-separated numeric IDs in `ADMIN_IDS` (example: `123456789,987654321`). Do not use usernames for authorization.
4. Configure `PAYMENT_CARD_NUMBER` and `PAYMENT_CARDHOLDER` only with authorized payment details.

## Database, run, tests

```bash
# Database tables are initialized automatically at startup for this MVP.
alembic upgrade head
python bot.py

# In another terminal / after installing dependencies:
pytest -q
```

The configured default database is `sqlite+aiosqlite:///./cshop.db`. Set `DATABASE_URL` for another SQLAlchemy async database URL. The initial schema migration can be applied with `alembic upgrade head` (Alembic config currently targets local synchronous SQLite for migrations). Startup also calls `create_all` for convenience in the MVP. Add versioned, reviewed migration revisions for all subsequent schema changes; do not treat `create_all` as a replacement for migration management in production.

## Security and operations

- Keep tokens in environment variables or a secret manager. Rotate any exposed token immediately.
- Configure at least one admin ID before enabling manual payment operations; an empty list intentionally disables admin actions.
- Validate transfers independently before approval. Do not rely on receipt images alone as proof of settlement.
- Use HTTPS/webhook deployment only with a verified reverse proxy and secret webhook path; polling is the default here.
- Back up the SQLite database and restrict filesystem permissions. For multiple bot workers or high concurrency, use PostgreSQL and transaction-level concurrency controls.
- The card number is configurable and the default value is only a placeholder/business-provided value; verify it before use.

## systemd deployment (Linux)

Create `/etc/systemd/system/cshop.service` (adjust paths and user):

```ini
[Unit]
Description=CShop Telegram Bot
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=cshop
WorkingDirectory=/opt/cshop-bot
EnvironmentFile=/opt/cshop-bot/.env
ExecStart=/opt/cshop-bot/.venv/bin/python /opt/cshop-bot/bot.py
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
```

Then run `sudo systemctl daemon-reload`, `sudo systemctl enable --now cshop`, and `sudo journalctl -u cshop -f`.

## Docker deployment

A minimal image can use Python slim, install `requirements.txt`, copy the application, and run `python bot.py`. Mount `.env` as a secret and persist the SQLite database directory as a volume; do not bake `.env` into the image. For production, use a non-root user and health/restart policies.

## GitHub

```bash
git remote add origin https://github.com/<OWNER>/<REPO>.git
git push -u origin main
```

The intended history contains exactly three Conventional Commits; see the delivery notes provided with the repository.
