# 1. Python 3.10 Slim kullanıyoruz (Hafif ve hızlı)
FROM python:3.10-slim

# 2. Sistem kütüphanelerini kur (Torch ve PDF araçları için gerekli)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 3. Çalışma klasörünü ayarla
WORKDIR /app

# 4. Gereksinimleri kopyala ve yükle
COPY requirements.txt .

# Önce pip'i güncelle, sonra kütüphaneleri kur (Cache kullanarak hızlandır)
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 5. Tüm kodları içeri al
COPY . .

# 6. Gunicorn ile uygulamayı başlat
# Timeout 0: Cloud Run'ın kendi zaman aşımını kullanmasını sağlar
# Workers 1 Threads 8: Yapay zeka ve I/O işlemleri için en iyi ayar
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 cv_parser:app
