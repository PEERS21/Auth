FROM python:3.14-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN git clone https://github.com/PEERS21/Common-python.git /app/common

RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt -r common/requirements.txt \
 && pip uninstall -y redis || true \
 && pip install --no-cache-dir "redis==7.2.0"

RUN python - <<'PY'
import importlib, sys
try:
    r = importlib.import_module('redis')
    print('redis:', r.__version__, r.__file__)
except Exception as e:
    print('redis import error:', e)
    raise
PY

EXPOSE 8000

CMD ["python", "-m", "auth_server"]
