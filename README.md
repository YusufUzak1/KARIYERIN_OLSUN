# 🎭 Duygu Analizi API

Canlı avatar mülakatı sırasında gerçek zamanlı duygu analizi ve AI cevap puanlama servisi.

## 🚀 Hızlı Başlangıç (Ekip İçin)

```bash
# 1. Python 3.12 gerekli
python --version  # Python 3.12.x olmalı

# 2. Sanal ortam oluştur
python -m venv venv

# 3. Sanal ortamı aktifleştir
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Bağımlılıkları yükle (bu adım 5-10 dakika sürebilir, ~2GB indirir)
pip install -r requirements.txt

# 5. .env dosyasını oluştur
copy .env.example .env
# Sonra .env dosyasını aç ve API keylerini doldur

# 6. Servisi başlat
python api.py
```

## 🔐 API Keyler

`.env` dosyasına şunları ekle:

```env
SUPABASE_URL=https://huyyknstzknrmdbafpwq.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
OPENAI_API_KEY=sk-...
```

> ⚠️ API keylerini ekip koordinatöründen alın.

## 🛠️ Özellikler

- 🎥 **Gerçek Zamanlı Duygu Analizi** - DeepFace ile yüz ifadesi tespiti
- 🧠 **AI Cevap Puanlama** - OpenAI ile mülakat cevaplarını değerlendirme
- 💾 **Supabase Entegrasyonu** - Mülakat sonuçlarını veritabanına kaydetme

## 📂 Proje Yapısı

```
duyguanaliz/
├── api.py              # Ana Flask API servisi
├── .env                # API keyler (PAYLAŞILMAZ)
├── .env.example        # Örnek env dosyası
├── requirements.txt    # Python bağımlılıkları
├── .gitignore          # Git ignore listesi
└── README.md           # Bu dosya
```

## 🔗 API Endpoints

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/health` | GET | Servis durumu |
| `/analyze-frame` | POST | Kare analizi (base64 görüntü) |
| `/score-answer` | POST | AI cevap puanlama |
| `/save-interview` | POST | Mülakat kaydetme |

## 🎯 Duygu Haritası

| İngilizce | Türkçe |
|-----------|--------|
| happy | Mutlu |
| sad | Üzgün |
| fear | Gergin |
| neutral | Nötr |
| angry | Kızgın |
| surprise | Şaşkın |

## ⚠️ Önemli Notlar

1. **İlk çalıştırma yavaş olabilir** - DeepFace modeli indirilir (~500MB)
2. **Python 3.12 gerekli** - Daha düşük sürümler çalışmaz
3. **venv klasörünü paylaşmayın** - Her bilgisayar kendi oluşturur
4. **.env dosyasını paylaşmayın** - API keyler gizli kalmalı

---

**Port:** 5001  
**Ana Dosya:** `api.py`  
**Son Güncelleme:** 2025-12-16