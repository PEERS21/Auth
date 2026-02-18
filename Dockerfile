FROM python:3.14-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt -r common/requirements.txt \
 && pip install --no-cache-dir "redis>=4.6.0,<5" 

EXPOSE 8000

CMD ["python", "-m", "auth_server"]