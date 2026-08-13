# MenuLens — Phase 1 MVP

Extract structured menu data from PDFs and images using AI.

## Setup

### 1. System dependencies (for PDF support)

Ubuntu/Debian:
```bash
sudo apt-get install poppler-utils
```

Mac:
```bash
brew install poppler
```

Windows: install [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) and add to PATH.

### 2. Python dependencies

```bash
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Get a Gemini API key

1. Go to https://aistudio.google.com/apikey
2. Create a free API key
3. Copy `.env.example` to `.env`
4. Paste your key into `.env`
5. Set `API_KEY` to a long random secret (used to authenticate calls to the REST API) and `CORS_ORIGINS` to your frontend's domain

## Usage (CLI)

```bash
python extract.py sample_menu.jpg
python extract.py sample_menu.pdf
```

Output goes to `sample_menu.extracted.json` next to the input file.

## Usage (REST API)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Interactive OpenAPI docs are served at `/docs` (Swagger UI) and `/redoc`.

Extraction is async: upload a file to get a `job_id`, then poll for the result.

```bash
# 1. submit a file, get back a job_id
curl -X POST http://localhost:8000/extract \
  -H "X-API-Key: $API_KEY" \
  -F "file=@sample_menu.pdf"

# 2. poll until status is "done" or "error"
curl http://localhost:8000/extract/<job_id> \
  -H "X-API-Key: $API_KEY"
```

Every request (except `/health`) must include the `X-API-Key` header matching `API_KEY` in `.env`.

### Deploying on a VPS

1. Clone the repo on the VPS, create `venv`, install `requirements.txt`, install `poppler-utils` (see step 1 above), and set up `.env` as above.
2. Run behind a process manager so it restarts on crash/reboot, e.g. `systemd`:

   ```ini
   # /etc/systemd/system/menulens.service
   [Unit]
   Description=MenuLens API
   After=network.target

   [Service]
   WorkingDirectory=/path/to/menulens
   ExecStart=/path/to/menulens/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
   Restart=always
   EnvironmentFile=/path/to/menulens/.env

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   sudo systemctl enable --now menulens
   ```
3. Put nginx (or Caddy) in front for TLS and reverse-proxy to `127.0.0.1:8000`, so the API is reachable at `https://your-domain.com`.
4. Point your frontend at `https://your-domain.com/extract`, sending the `X-API-Key` header. Keep the key server-side in your FE's backend if possible — don't ship it in client-side JS, since anyone who extracts it can burn your Gemini quota.

## Project structure

```
menulens/
├── extract.py       # Core extraction logic (also runnable as a CLI)
├── main.py          # FastAPI app: POST /extract, GET /extract/{job_id}
├── schemas.py       # Pydantic data models
├── prompts.py       # LLM prompts (versioned)
├── requirements.txt
├── .env.example
└── README.md
```

## What's next (roadmap)

- Phase 2: Build evaluation dataset + accuracy metrics
- Phase 3: Split into multi-agent pipeline with LangGraph
- Phase 4: FastAPI backend + Postgres
- Phase 5: Next.js frontend
- Phase 6: Deploy on VPS
