# My Shop Backend

## Run locally

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn server.app.main:app --host 127.0.0.1 --port 8000
```

## Run with Docker Compose

```bash
docker compose up --build
```

Backend API will be available at `http://localhost:8000`.

