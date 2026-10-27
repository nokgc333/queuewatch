FROM python:3.12-slim

WORKDIR /app

COPY requirements-runtime.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements-runtime.lock

COPY app ./app

RUN useradd --system --uid 10001 queuewatch \
    && mkdir -p /app/data \
    && chown -R queuewatch /app/data
USER queuewatch

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
