# Football Club

Simple Hello World with a FastAPI backend and a Streamlit frontend.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

Terminal 1 — API:

```powershell
uvicorn api:app --reload
```

Terminal 2 — UI:

```powershell
streamlit run app.py
```

Open the Streamlit URL (usually http://localhost:8501) and click **Say hello**.
The API is also at http://127.0.0.1:8000.

## Deploy on Render

`render.yaml` defines two free web services:

| Service | What it runs | Health check |
| --- | --- | --- |
| `football-club-api` | `uvicorn api:app --host 0.0.0.0 --port $PORT` | `/health` |
| `football-club-web` | Streamlit on `$PORT` / `0.0.0.0` | `/_stcore/health` |

The UI talks to the API over Render's private network (`API_HOSTPORT`). Override with `API_URL` if you need a public URL instead.

1. Push this repo to GitHub (Render deploys from Git).
2. Open [Render Blueprints](https://dashboard.render.com/blueprints) → **New Blueprint Instance**.
3. Connect the repo. Render reads `render.yaml`.
4. Create the Blueprint. Open the `football-club-web` URL when both deploys are live.

Free instances spin down after idle time; the first request after that can take ~30–60s.
