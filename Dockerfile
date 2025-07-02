FROM python:3.11-slim

WORKDIR /app

# deps for matplot
RUN apt-get update && apt-get install -y \
    gcc \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
RUN mkdir -p /app/data
COPY data/ ./data
COPY .env ./.env

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]