FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml requirements.txt requirements-dev.txt ./

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/
COPY main.py alembic.ini seed_data.py docker-entrypoint.sh ./
COPY alembic/ ./alembic/

RUN mkdir -p uploads/avatars uploads/products && chmod +x docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
