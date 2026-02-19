FROM python:3.14-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN git clone https://github.com/PEERS21/Common-python.git /app/common

RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt -r common/requirements.txt \
 && pip install --no-cache-dir "redis>=4.6.0,<5"

EXPOSE 8000

CMD ["python", "-m", "auth_server"]
