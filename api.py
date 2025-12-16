"""
Duygu Analizi Flask API - DeepFace Only
========================================
Sadece DeepFace ile duygu analizi.
MediaPipe yok - göz kırpma özelliği yok.
Avatar mülakatı ile eş zamanlı çalışır.

Çalıştırma: python api.py
Port: 5001
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
from deepface import DeepFace
import base64
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI
import threading
from collections import defaultdict
import time
import queue

load_dotenv()

app = Flask(__name__)

# Cloud Run ve production için CORS ayarları
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:4000").split(",")
CORS(app, origins=ALLOWED_ORIGINS)

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://huyyknstzknrmdbafpwq.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh1eXlrbnN0emtucm1kYmFmcHdxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjExMzY5OTYsImV4cCI6MjA3NjcxMjk5Nn0.fRnZB8CbhIrYaewx1736Yn-TEM_4ds7hgDOLO2_MB0M")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Turkce duygu map
EMOTION_MAP = {
    'happy': 'Mutlu',
    'sad': 'Uzgun',
    'fear': 'Gergin',
    'neutral': 'Notr',
    'angry': 'Kizgin',
    'surprise': 'Saskin',
    'disgust': 'Igrenme'
}


class SimpleEmotionAnalyzer:
    """Sadece DeepFace ile duygu analizi - MediaPipe yok."""
    
    def __init__(self):
        self.sessions = defaultdict(lambda: {
            "emotions": [],
            "last_emotion": "Notr",
            "created_at": time.time(),
            "frame_queue": queue.Queue(maxsize=1),
            "answers": []
        })
        self.lock = threading.Lock()
        
        # Arka plan analiz thread
        self.keep_running = True
        self.analysis_thread = threading.Thread(target=self._analyze_loop, daemon=True)
        self.analysis_thread.start()
        print("Emotion analyzer started (DeepFace only)")
    
    def _analyze_loop(self):
        """Ayri thread de DeepFace analizi."""
        while self.keep_running:
            analyzed = False
            
            with self.lock:
                sessions_copy = list(self.sessions.keys())
            
            for session_id in sessions_copy:
                with self.lock:
                    if session_id not in self.sessions:
                        continue
                    session = self.sessions[session_id]
                
                try:
                    img = session["frame_queue"].get_nowait()
                    emotion = self._analyze_emotion(img)
                    
                    with self.lock:
                        if session_id in self.sessions:
                            self.sessions[session_id]["last_emotion"] = emotion
                            self.sessions[session_id]["emotions"].append(emotion)
                    
                    analyzed = True
                except queue.Empty:
                    pass
                except Exception as e:
                    print(f"Analysis error: {e}")
            
            if not analyzed:
                time.sleep(0.1)
    
    def _analyze_emotion(self, img):
        """DeepFace duygu analizi."""
        try:
            obj = DeepFace.analyze(img, actions=['emotion'], enforce_detection=False, silent=True)
            emotions = obj[0]['emotion']
            
            aday_duygu = "neutral"
            max_score = 0
            for emo_name, score in emotions.items():
                if emo_name == "neutral":
                    continue
                if score > max_score:
                    max_score = score
                    aday_duygu = emo_name
            
            final_emo = aday_duygu if max_score > 10 else "neutral"
            return EMOTION_MAP.get(final_emo, final_emo)
        except:
            return "Notr"
    
    def add_frame(self, session_id: str, img):
        """Frame ekle."""
        with self.lock:
            session = self.sessions[session_id]
            try:
                try:
                    session["frame_queue"].get_nowait()
                except queue.Empty:
                    pass
                session["frame_queue"].put_nowait(img)
                return True
            except queue.Full:
                return False
    
    def get_emotion(self, session_id: str):
        with self.lock:
            if session_id in self.sessions:
                return self.sessions[session_id]["last_emotion"]
            return "Notr"
    
    def get_stats(self, session_id: str):
        with self.lock:
            if session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            emotions = session["emotions"]
            
            filtered = [e for e in emotions if e != "Notr"]
            dominant = max(set(filtered), key=filtered.count) if filtered else "Notr"
            
            return {
                "total_frames": len(emotions),
                "dominant_emotion": dominant,
                "last_emotion": session["last_emotion"],
                "emotion_counts": {e: emotions.count(e) for e in set(emotions)},
                "answers": session["answers"]
            }
    
    def score_answer(self, question: str, answer: str):
        """AI cevap puanlama."""
        if not OPENAI_API_KEY:
            return "API Key Yok"
        
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            system_prompt = """
            Sen sadece veri analizi yapan bir algoritmasin. 
            Sohbet etme, giris/gelisme/sonuc cumlesi kurma, ovgu veya nezaket ifadeleri kullanma.
            Sadece istenen formatta, en kisa ve vurucu ifadelerle cikti ver.
            """
            
            user_prompt = f"""
            Soru: {question}
            Cevap: {answer}

            Lutfen cevabi su formatta analiz et (Her madde maksimum 10 kelime olsun):
            
            PUAN: [0-10 arasi sayi]/10
            DURUM: [Tek kelime: Yetersiz / Gelistirilmeli / Iyi / Mukemmel]
            EKSIK: [Cevapta ne yok? Net ve sert ol]
            ONERI: [Ne yapmali? Emir kipi kullan]
            """
            
            res = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            return res.choices[0].message.content
        except Exception as e:
            return str(e)
    
    def add_answer(self, session_id: str, question: str, answer: str, score: str):
        with self.lock:
            self.sessions[session_id]["answers"].append({
                "question": question,
                "answer": answer,
                "score": score,
                "emotion": self.sessions[session_id]["last_emotion"]
            })
    
    def reset_session(self, session_id: str):
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]


def decode_base64_image(base64_string):
    try:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except:
        return None


# Global analyzer
analyzer = SimpleEmotionAnalyzer()


# === ENDPOINTS ===

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "service": "emotion-analyzer",
        "features": ["emotion", "scoring"]
    })


@app.route('/analyze-frame', methods=['POST'])
def analyze_frame():
    data = request.json
    if not data or 'image' not in data:
        return jsonify({"error": "Image required"}), 400
    
    session_id = data.get('session_id', 'default')
    
    img = decode_base64_image(data['image'])
    if img is None:
        return jsonify({"error": "Invalid image"}), 400
    
    img = cv2.flip(img, 1)
    analyzer.add_frame(session_id, img)
    emotion = analyzer.get_emotion(session_id)
    
    return jsonify({
        "success": True,
        "session_id": session_id,
        "emotion": emotion,
        "face_detected": True,
        "blink_count": 0
    })


@app.route('/score-answer', methods=['POST'])
def score_answer():
    data = request.json
    if not data or 'question' not in data or 'answer' not in data:
        return jsonify({"error": "question and answer required"}), 400
    
    session_id = data.get('session_id', 'default')
    question = data['question']
    answer = data['answer']
    
    score = analyzer.score_answer(question, answer)
    analyzer.add_answer(session_id, question, answer, score)
    
    return jsonify({
        "success": True,
        "score": score
    })


@app.route('/session-stats/<session_id>', methods=['GET'])
def get_session_stats(session_id):
    stats = analyzer.get_stats(session_id)
    if stats is None:
        return jsonify({"error": "Session not found"}), 404
    
    return jsonify({"success": True, **stats})


@app.route('/save-interview', methods=['POST'])
def save_interview():
    data = request.json
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    
    if not session_id:
        return jsonify({"error": "session_id required"}), 400
    
    stats = analyzer.get_stats(session_id)
    if stats is None:
        return jsonify({"error": "Session not found"}), 404
    
    try:
        insert_data = {
            "user_id": user_id or 0,
            "sorular": stats["answers"],
            "ortalama_puan": 0,
            "baskin_duygu": stats["dominant_emotion"],
            "toplam_kirpma": 0,
            "sure_saniye": data.get("duration_seconds", 0),
            "soru_sayisi": len(stats["answers"]),
            "status": "completed"
        }
        
        result = supabase.table("mulakat_gecmisi").insert(insert_data).execute()
        analyzer.reset_session(session_id)
        
        return jsonify({"success": True, "data": result.data[0] if result.data else None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/reset-session/<session_id>', methods=['POST'])
def reset_session(session_id):
    analyzer.reset_session(session_id)
    return jsonify({"success": True})


if __name__ == '__main__':
    # Cloud Run PORT environment değişkenini kullan
    port = int(os.getenv("PORT", 8080))
    
    print(f"""
    =============================================
       Duygu Analizi API - Port {port}
       DeepFace duygu analizi
       AI cevap puanlama
       Cloud Run Ready!
    =============================================
    """)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
