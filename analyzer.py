"""
Duygu Analizi Ortak Modülü
==========================
app.py'deki duygu analizi mantığını kullanır.
Hem Streamlit hem Flask API bu modülü import eder.
"""

import cv2
import numpy as np
from deepface import DeepFace
import base64

# Türkçe duygu haritası (app.py'deki ile aynı)
EMOTION_MAP = {
    'happy': 'Mutlu',
    'sad': 'Gergin',
    'fear': 'Gergin',
    'neutral': 'Nötr',
    'angry': 'Kızgın',
    'surprise': 'Şaşkın',
    'disgust': 'İğrenme'
}


def decode_base64_image(base64_string: str):
    """Base64 string'i OpenCV görüntüsüne dönüştürür."""
    try:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except:
        return None


def analyze_emotion(img) -> tuple:
    """
    app.py'deki analyze_loop mantığının aynısı.
    Görüntüden duygu analizi yapar.
    
    Returns:
        (duygu_str, confidence_score)
    """
    try:
        # app.py satır 88-100'deki analiz mantığı
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
        tr_emo = EMOTION_MAP.get(final_emo, final_emo)
        
        return tr_emo, max_score
    except Exception as e:
        return "Nötr", 0


def analyze_frame_from_base64(base64_image: str, flip: bool = True) -> dict:
    """
    Base64 görüntüden duygu analizi yapar.
    Frontend'den gelen frame'leri analiz etmek için.
    """
    img = decode_base64_image(base64_image)
    if img is None:
        return {"success": False, "error": "Invalid image"}
    
    if flip:
        img = cv2.flip(img, 1)
    
    emotion, confidence = analyze_emotion(img)
    
    return {
        "success": True,
        "emotion": emotion,
        "confidence": confidence
    }
