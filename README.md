# Football Club

FastAPI backend, Streamlit frontend, and PostgreSQL for accounts.

People register with a first name, email, password, and account type (`Coach / Admin` or `Player`). Later sign-ins use that email and password. Google sign-in is also available.

## Local setup

PostgreSQL is expected to already be running with a database named `football_club`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set `POSTGRES_PASSWORD` for your local Postgres user (the default user is `postgres`). Also set `SECRET_KEY` to a long random string. The API creates these tables in `football_club` on startup:

- `users`
- `auth_identities`
- `email_login_codes`
- `auth_handoffs`

## Run

Terminal 1 — API:

```powershell
uvicorn api:app --reload
```

Terminal 2 — UI:

```powershell
streamlit run app.py
```

Open the Streamlit URL (usually http://localhost:8501).

### Google sign-in

1. In Google Cloud, create an OAuth client of type **Web application**.
2. Add this authorized redirect URI: `http://127.0.0.1:8000/auth/google/callback`
3. Put the client id and secret in `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
4. Restart the API.

On Render, add the API service's public URL plus `/auth/google/callback` as a second redirect URI.

## Deploy on Render

`render.yaml` defines two free web services. It does not create a database. The API uses the Postgres database already in the Render account.

| Service | What it runs | Health check |
| --- | --- | --- |
| `football-club-api` | `uvicorn api:app --host 0.0.0.0 --port $PORT` | `/health` |
| `football-club-web` | Streamlit on `$PORT` / `0.0.0.0` | `/_stcore/health` |

The UI talks to the API over Render's private network (`API_HOSTPORT`). Override with `API_URL` if you need a public URL instead.

1. Push this repo to GitHub (Render deploys from Git).
2. Open [Render Blueprints](https://dashboard.render.com/blueprints) → **New Blueprint Instance**.
3. Connect the repo. Render reads `render.yaml`.
4. For `DATABASE_URL`, paste the **Internal Database URL** from the existing Render Postgres database. Do not create another database.
5. Google client id and secret can be left empty until Google sign-in is ready.
6. Create the Blueprint. Open the `football-club-web` URL when the deploys are live.

Local development keeps using your installed Postgres database. Production uses the Render database.

Free instances spin down after idle time; the first request after that can take ~30–60s.
