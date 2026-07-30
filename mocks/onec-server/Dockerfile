FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV PYTHONPATH=/app/src

RUN useradd -r -u 10001 onec && chown -R onec:onec /app
USER onec

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/health/')" || exit 1

EXPOSE 8100

CMD ["uvicorn", "onec_mock.main:app", "--host", "0.0.0.0", "--port", "8100"]
