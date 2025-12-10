import os
import json
import re
import numpy as np
import pdfplumber
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
import openai
import traceback

# --- Flask başlat ---
app = Flask(__name__)

# --- MOCK MODE CONFIGURATION ---
# --- MOCK MODE CONFIGURATION ---
MOCK_MODE = False # Set to true to bypass OpenAI and Supabase
print(f"⚠️ MOCK MODE: {'ACTIVE' if MOCK_MODE else 'INACTIVE'}")

# --- Ortam değişkenleri yükle ---
load_dotenv()
# vtys = os.getenv("vtys") # .env dosyasından okunacak
vtys = os.getenv("vtys")

if not MOCK_MODE:
    if not vtys:
        raise ValueError("OpenAI API anahtarı bulunamadı.")
    openai.api_key = vtys

# --- Supabase bağlantısı ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = None
if not MOCK_MODE:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ HATA: Supabase anahtarları .env dosyasında bulunamadı.")
    else:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Yardımcı fonksiyonlar ---
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        print(f"PDF okuma hatası: {e}")
        if MOCK_MODE: return "Mock PDF Text Content"
        raise e
        
    if len(text.strip()) < 50:
        print("⚠️ PDF'ten çok az metin çıkarıldı.")
    return text

def embed_text(text):
    if MOCK_MODE:
        return np.random.rand(1, 384).astype('float32')
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L12-v2')
    emb = model.encode([text])
    return np.array(emb).astype('float32')

def cosine_similarity(v1, v2):
    v1n = v1 / np.linalg.norm(v1)
    v2n = v2 / np.linalg.norm(v2)
    return np.dot(v1n, v2n.T)[0][0]

def safe_json_parse(content):
    try:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            print("⚠️ GPT JSON formatı dışında yanıt döndürdü:")
            print(content)
            return {}
    except Exception as e:
        print("❌ JSON parse hatası:", e)
        print("Ham içerik:", content)
        return {}

def parse_cv_fields(cv_text):
    if MOCK_MODE:
        return {
            "ad_soyad": "Mock Aday",
            "e_posta": "mock@example.com",
            "telefon_numarasi": "555 123 45 67",
            "adres": "İstanbul, Türkiye",
            "egitim_bilgileri": [{"okul": "Mock Üniversitesi", "bolum": "Bilgisayar Mühendisliği"}],
            "linkedin_url": "https://linkedin.com/in/mock",
            "github_url": "https://github.com/mock",
            "deneyim": [{"sirket": "Mock Tech", "pozisyon": "Yazılım Mühendisi"}],
            "yetenekler": ["Python", "JavaScript", "React", "Node.js"],
            "sertifikalar": [],
            "diller": ["Türkçe", "İngilizce"],
            "projeler": []
        }

    prompt = f"""
    Aşağıda bir CV metni var. Bu CV'den aşağıdaki alanları çıkar ve belirtilen JSON formatında döndür:

    {{
        "ad_soyad": "Ad Soyad",
        "e_posta": "email@example.com",
        "telefon_numarasi": "555...",
        "adres": "Şehir, Ülke",
        "linkedin_url": "url",
        "github_url": "url",
        "egitim_bilgileri": [
            {{"okul": "Üniversite Adı", "bolum": "Bölüm Adı", "tarih": "2020-2024"}}
        ],
        "deneyim": [
            {{"sirket": "Şirket Adı", "pozisyon": "Ünvan", "tarih": "2022-2023", "aciklama": "Kısa açıklama"}}
        ],
        "projeler": [
            {{"isim": "Proje Adı", "aciklama": "Proje açıklaması"}}
        ],
        "yetenekler": ["Java", "Python"],
        "sertifikalar": ["Sertifika 1", "Sertifika 2"],
        "diller": ["İngilizce", "Almanca"]
    }}

    Eğer bir bilgi yoksa null veya boş liste döndür.
    CV:
    {cv_text}
    """
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    content = response.choices[0].message.content.strip()
    return safe_json_parse(content)

def find_missing_fields(data):
    return [k for k, v in data.items() if v in [None, "", "null", []]]

# --- Supabase kayıt ---
def save_to_supabase(data, raw_text, user_id):
    if MOCK_MODE:
        print("✅ [MOCK] Supabase'e kaydedildi (Simülasyon).")
        return {"id": 12345, **data}

    payload = {
        "user_id": int(user_id) if user_id else None,
        "ad_soyad": data.get("ad_soyad"),
        "e_posta": data.get("e_posta"),
        "telefon_numarasi": data.get("telefon_numarasi"),
        "adres": data.get("adres"),
        "egitim_bilgileri": data.get("egitim_bilgileri") or [],
        "linkedin_url": data.get("linkedin_url"),
        "github_url": data.get("github_url"),
        "deneyim": data.get("deneyim") or [],
        "yetenekler": data.get("yetenekler") or [],
        "sertifikalar": data.get("sertifikalar") or [],
        "diller": data.get("diller") or [],
        "projeler": data.get("projeler") or [],
        "cv_raw_text": raw_text,
        "status": "pending"
    }

    # Insert into cv_drafts instead of aday_profil
    res = supabase.table("cv_drafts").insert(payload).execute()
    
    if not res.data:
        # Fallback to verify insertion
        res = supabase.table("cv_drafts").select("*").order("id", desc=True).limit(1).execute()
        
    if res.data:
        print(f"✅ Supabase cv_drafts tablosuna kaydedildi (User ID: {user_id}).")
        return res.data[0]
    else:
        print("⚠️ Supabase boş yanıt döndürdü.")
        return None

def update_supabase(record_id, updates):
    if MOCK_MODE:
        return {"id": record_id, **updates}
        
    res = supabase.table("aday_profil").update(updates).eq("id", record_id).execute()
    return res.data[0] if res.data else None

# --- API endpointleri ---
@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "CV Analiz API aktif 🚀", "mode": "MOCK" if MOCK_MODE else "LIVE"})

@app.route("/upload_cv", methods=["POST"])
def upload_cv():
    if "file" not in request.files:
        return jsonify({"error": "Dosya yüklenmedi."}), 400

    file = request.files["file"]
    user_id = request.form.get("userId") # Frontend should send this
    
    # Cloud Run'da sadece /tmp klasörü yazılabilir alandır
    pdf_path = os.path.join("/tmp", f"temp_{file.filename}")
    file.save(pdf_path)

    try:
        cv_text = extract_text_from_pdf(pdf_path)
        parsed_data = parse_cv_fields(cv_text)
        missing = find_missing_fields(parsed_data)
        cv_vec = embed_text(cv_text)
        # target_vec calculation is removed as it's not needed for draft creation
        sim_score = 0.0 # Default value since we don't calculate it for drafts
        
        record = save_to_supabase(parsed_data, cv_text, user_id)

        response = {
            "id": record["id"] if record else None,
            "parsed_data": parsed_data,
            "missing_fields": missing,
            "similarity_score": round(float(sim_score), 3)
        }
        return jsonify(response)
    except Exception as e:
        print("❌ HATA OLUŞTU:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

@app.route("/update/<int:record_id>", methods=["POST"])
def update_record(record_id):
    updates = request.get_json()
    updated = update_supabase(record_id, updates)
    if updated:
        return jsonify({"message": "✅ Güncellendi", "updated_record": updated})
    return jsonify({"error": "Kayıt güncellenemedi"}), 400

# --- Uygulama başlat ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
