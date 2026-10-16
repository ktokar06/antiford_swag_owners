FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --index-url https://pypi.org/simple --timeout 120 --retries 5 -r requirements.txt

COPY core/ core/
COPY etl/ etl/
COPY ml/ ml/
COPY models/release/ models/release/
COPY services/ services/
COPY scripts/ scripts/


RUN mkdir -p /app/cdr_out && useradd --system --uid 10001 --home /app app && chown -R app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/db', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "core.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
