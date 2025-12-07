Nexa — Developer README
⸻

*** Table of contents ***
	•	Prerequisites
	•	Quick start (minimal)
	•	Detailed setup (Windows PowerShell)
	•	Python venv & dependencies
	•	PostgreSQL
	•	Redis (Docker or local)
	•	Environment variables (.env)
	•	Run backend (uvicorn)
	•	Run Celery worker
	•	Run Telethon userbot (personal account listener)
	•	Webhook & ngrok (exposing local server for Telegram)
	•	Testing & end-to-end script
	•	Common troubleshooting
	•	Security notes
	•	Useful commands reference

⸻

*** Prerequisites ***
	•	Windows (PowerShell) or macOS/Linux (commands will be similar)
	•	Python 3.11+ (the project uses 3.11 in Dockerfile)
	•	Git
	•	PostgreSQL (local or remote)
	•	Redis (local or via Docker)
	•	Optional: Docker Desktop (recommended for Redis/Postgres if you prefer containers)
	•	(For userbot) Telegram API credentials from https://my.telegram.org (API ID & API HASH)

⸻

Quick start (minimal)
	1.	Create and activate a Python venv:

python -m venv .venv
.\.venv\Scripts\Activate.ps1

	2.	Install dependencies:

pip install -r requirements.txt
# If you encounter SQL driver issues, also install:
pip install psycopg2-binary asyncpg

	3.	Create a Postgres DB nexa_db and run the table creation script:

# Example using psql (adjust user/password/host)
psql "postgresql://postgres:postgres@localhost:5432/postgres"
CREATE DATABASE nexa_db;
-- run the create tables script from the repo
python scripts\create_tables.py

	4.	Start Redis (Docker recommended):

# Docker example
docker run -d --name nexa-redis -p 6379:6379 redis:7

	5.	Start backend (uvicorn):

# make sure .env is configured (see below)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

	6.	Start Celery (in another shell):

# use --pool=solo on Windows if you see billiard permission issues
celery -A app.tasks.celery_app.celery worker --loglevel=info --pool=solo

	7.	(Optional) Start the Telethon userbot (see below)
	8.	Run the E2E test script (optional):

py .\scripts\test_e2e.py


⸻

Detailed setup (Windows PowerShell)

1) Python venv & dependencies

# create venv and activate
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install dependencies
pip install -r requirements.txt
# database drivers if needed
pip install psycopg2-binary asyncpg

If your project uses Pydantic v2, you may need pydantic-settings. If you get an error about BaseSettings missing, install:

pip install pydantic-settings

2) PostgreSQL

You can install Postgres locally or run via Docker. Example Docker command:

# run postgres container (adjust password, port)
docker run -d --name nexa-postgres -e POSTGRES_USER=roshan -e POSTGRES_PASSWORD=Roshan123 -e POSTGRES_DB=nexa_db -p 5432:5432 postgres:15

Or create DB locally and run the schema script:

# create db (psql interactive)
psql "postgresql://roshan:Roshan123@localhost:5432/postgres"
CREATE DATABASE nexa_db;
# then run
python scripts\create_tables.py

If create_tables.py connects using settings from your app.core.config, ensure .env has the correct DATABASE_URL before running.

3) Redis

You can run Redis locally or via Docker. Docker example:

docker run -d --name nexa-redis -p 6379:6379 redis:7

If you use Docker Desktop you can also launch Redis via a docker-compose file.

4) Environment variables (.env)

Create a .env file in the repo root with the configuration required by app.core.config. Example .env (edit values):

ENV=dev
DATABASE_URL=postgresql://roshan:Roshan123@localhost:5432/nexa_db
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-REPLACE_ME
TELEGRAM_BOT_TOKEN=8280461069:AA...REPLACE
USERBOT_URL=http://127.0.0.1:9000/send_reply
USERBOT_SECRET=supersecret123
# optional
WEBHOOK_BASE_URL=https://your-ngrok-or-public-url

Notes:
	•	If you prefer postgresql+asyncpg:// in DATABASE_URL, keep it, but some local tools or scripts that use sync SQLAlchemy will want postgresql://. The test script included normalizes this.
	•	Keep secrets out of source control. Add .env to .gitignore.

5) Run the backend (uvicorn)

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

Check http://127.0.0.1:8000/docs for API docs and http://127.0.0.1:8000/openapi.json.

6) Run Celery worker

# from repo root, inside venv
celery -A app.tasks.celery_app.celery worker --loglevel=info --pool=solo

On Windows, using --pool=solo avoids Pool/permission issues with billiard.

7) Run the Telethon userbot (personal account listener)
	1.	Register an API app at https://my.telegram.org → get API ID and API HASH.
	2.	Export environment variables (PowerShell):

$env:TG_API_ID = "123456"
$env:TG_API_HASH = "abcdef..."
$env:TG_PHONE = "+911234567890"   # only needed on first run
$env:BACKEND_WEBHOOK = "http://127.0.0.1:8000/connectors/personal/webhook"
$env:USERBOT_SECRET = "supersecret123"
python userbot_listener.py

On first run Telethon will ask for the login code sent to your Telegram app. Save the generated session file (the user_session.session file) securely.

⸻

Webhook & ngrok (expose local server to Telegram)

If you want Telegram to send webhooks to your local machine, expose http://127.0.0.1:8000/connectors/telegram/webhook with ngrok.
	1.	Start ngrok (or use the new ngrok CLI):

ngrok http 8000

	2.	Copy the forwarding HTTPS URL shown by ngrok (e.g. https://abcd-1234.ngrok.io).
	3.	Set WEBHOOK_BASE_URL or TELEGRAM_WEBHOOK_URL accordingly and register the webhook with Telegram:

from app.core.config import settings
import requests
requests.post(f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook", data={"url": f"{NGROK_URL}/connectors/telegram/webhook"})

Check http://127.0.0.1:4040 (ngrok web UI) for requests, or query Telegram getWebhookInfo to check last error.

⸻

Testing & end-to-end (scripts/test_e2e.py)

A test script scripts/test_e2e.py is provided to simulate a personal DM payload, verify DB persistence, attempt replying (admin endpoint or userbot), and optionally queue a Celery reminder.

Run it with:

py .\scripts\test_e2e.py

If the script reports database driver errors, install the missing driver:

pip install psycopg2-binary asyncpg

If you see relation "normalized_messages" does not exist — run python scripts\create_tables.py or inspect the DB schema.

⸻

Common troubleshooting

pydantic / BaseSettings errors

If you see "Config" and "model_config" cannot be used together or similar Pydantic v2 errors, ensure your app.core.config is compatible with your installed Pydantic version. Installing pydantic-settings may be necessary:

pip install pydantic-settings

Or use the app/core/config.py file that dynamically handles v1/v2 shipped in the repo.

DB driver / asyncpg vs psycopg2

The app can use async or sync DB drivers. If a script expects sync SQLAlchemy engine but your DATABASE_URL is postgresql+asyncpg://..., either:
	•	Install psycopg2-binary and use postgresql://... for that script, or
	•	Install asyncpg and adapt the script to use create_async_engine.

Commands:

pip install psycopg2-binary asyncpg

Celery & Redis connection refused
	•	Ensure Redis is running and REDIS_URL is correct (redis://localhost:6379/0).
	•	If Celery cannot start on Windows due to billiard permission issues, use --pool=solo.

Telegram webhook 404 / Wrong response from webhook
	•	Telegram shows Wrong response from the webhook: 404 Not Found when your webhook URL returns 404. Confirm you set the webhook to the correct path (e.g. /connectors/telegram/webhook or your WEBHOOK_BASE_URL + /connectors/telegram/webhook).
	•	Use ngrok’s web UI (http://127.0.0.1:4040) to inspect incoming Telegram requests.

⸻

Security & operational notes
	•	Keep .env and the Telethon session file out of source control. Add them to .gitignore.
	•	user_session.session grants access to your Telegram account — protect it.
	•	Use a strong USERBOT_SECRET and only expose the userbot HTTP endpoint on localhost or internal network. If you must expose it publicly, use HTTPS and additional auth.
	•	Rate limits: respect Telegram and OpenAI rate limits. The worker logs show retries/backoff when rate-limited.

⸻
