FROM python:3.11-slim

WORKDIR /app

# system deps for common python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
