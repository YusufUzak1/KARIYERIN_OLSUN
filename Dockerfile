# ============================================
# Duygu Analizi API - Production Dockerfile
# ============================================

# 1. Base Image - Python 3.11 slim (hafif ve hızlı)
FROM python:3.11-slim

# 2. Ortam değişkenleri
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEEPFACE_HOME=/app/.deepface

# 3. Çalışma dizini
WORKDIR /app

# 4. Sistem bağımlılıkları
# - libgl1: OpenCV için gerekli (libGL.so.1 hatasını önler)
# - libglib2.0-0: OpenCV ve GTK bağımlılıkları
# - libsm6, libxext6, libxrender1: Görüntü işleme kütüphaneleri
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# 5. Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Gunicorn kurulumu (Production WSGI sunucusu)
RUN pip install --no-cache-dir gunicorn

# 7. MODEL BAKING - DeepFace modellerini önceden indir
# Bu sayede container başlatıldığında model indirilmesini beklemeyiz
RUN python -c "from deepface import DeepFace; \
    DeepFace.build_model('Emotion'); \
    print('✅ Emotion model cached successfully!')"

# 8. Uygulama dosyalarını kopyala
COPY api.py .
COPY analyzer.py .
COPY models/ ./models/

# 9. Cloud Run için PORT değişkeni
ENV PORT=8080

# 10. Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# 11. Production sunucu başlatma
# - workers: CPU sayısına göre ayarlanabilir (Cloud Run için 1-2 yeterli)
# - threads: Her worker için thread sayısı
# - timeout: Uzun süren analizler için 120 saniye
# - bind: Tüm arayüzlerden dinle
CMD exec gunicorn \
    --bind :$PORT \
    --workers 1 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    api:app
