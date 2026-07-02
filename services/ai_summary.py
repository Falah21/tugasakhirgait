import streamlit as st
import google.generativeai as genai
from datetime import datetime
from database.mongodb import get_collection
from bson import ObjectId

# Konfigurasi Gemini API
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
else:
    gemini_model = None

# Mendapatkan model Gemini yang sudah dikonfigurasi
def get_gemini_model():
    return gemini_model

# Generate AI summary menggunakan Gemini
def generate_ai_summary(prompt):
    try:
        if gemini_model is None:
            return None, "API Key Gemini tidak ditemukan"
        
        response = gemini_model.generate_content(prompt)
        return response.text, None
    except Exception as e:
        return None, str(e)

# Simpan Ai summary ke database
def save_ai_summary(data):
    try:
        collection = get_collection('ai_summaries')
        result = collection.insert_one(data)
        return result.inserted_id is not None
    except Exception as e:
        print(f"Error saving AI summary: {e}")
        return False

# Ambil AI summary dari database
def get_ai_summaries(pasien_object_id, tanggal_pemeriksaan=None):
    try:
        collection = get_collection('ai_summaries')
        
        try:
            pasien_id_obj = ObjectId(pasien_object_id)
        except:
            pasien_id_obj = pasien_object_id
        
        query = {'pasien_id': pasien_id_obj}
        if tanggal_pemeriksaan:
            query['tanggal_pemeriksaan'] = tanggal_pemeriksaan
        
        summaries = list(collection.find(query).sort('timestamp', -1))
        return summaries
        
    except Exception as e:
        print(f"Error getting AI summaries: {e}")
        return []

# AMbil AI summary terbaru
def get_latest_ai_summary(pasien_object_id, tanggal_pemeriksaan):
    try:
        collection = get_collection('ai_summaries')
        
        try:
            pasien_id_obj = ObjectId(pasien_object_id)
        except:
            pasien_id_obj = pasien_object_id
        
        summary = collection.find_one(
            {
                'pasien_id': pasien_id_obj,
                'tanggal_pemeriksaan': tanggal_pemeriksaan
            },
            sort=[('timestamp', -1)]
        )
        
        return summary
        
    except Exception as e:
        print(f"Error getting latest AI summary: {e}")
        return None
