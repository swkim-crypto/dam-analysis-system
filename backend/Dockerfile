FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# GDAL 및 Python 설치
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# backend 폴더 전체 복사
COPY backend/ .

# requirements 설치
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]