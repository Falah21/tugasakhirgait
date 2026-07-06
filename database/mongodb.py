from pymongo import MongoClient
import streamlit as st

# Membuat koneksi ke MongoDB beserta konfigurasi batas waktu koneksi
def get_mongo_client():
    return MongoClient(
        st.secrets["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000
    )

# Mwngambil database tugasakhir
def get_db():
    client = get_mongo_client()
    return client['tugasakhir']

# Mengambil collection dari database
def get_collection(collection_name):
    db = get_db()
    return db[collection_name]
