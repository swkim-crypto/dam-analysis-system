FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# GDAL 시스템 라이브러리 설치
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# backend 폴더 전체 복사
COPY backend/ .

# fiona 먼저 고정 설치 후 나머지 설치 (버전 충돌 방지)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    fiona==1.9.6 \
    geopandas==0.14.1 && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
