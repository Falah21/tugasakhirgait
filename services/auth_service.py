import bcrypt
import streamlit as st
from database.mongodb import get_collection
from bson import ObjectId

# Hashing password dengan bcrypt
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
  
# Verifikasi password input dengan pw yg udh di hash
def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# Autentikasi user sesuai nomor identitas dan role
def authenticate_user(nomor_identitas, password, role=None):
    try:
        collection = get_collection('users')
        query = {'nomor_identitas': nomor_identitas}
        if role:
            query['role'] = role
        
        user = collection.find_one(query)
        
        if user:
            stored_password = user.get('password')
            if verify_password(password, stored_password):
                return {
                    '_id': str(user.get('_id')),
                    'nomor_identitas': user.get('nomor_identitas'),
                    'nama_lengkap': user.get('nama_lengkap'),
                    'role': user.get('role'),
                    'tanggal_lahir': user.get('tanggal_lahir', ''),
                    'jenis_kelamin': user.get('jenis_kelamin', '')
                }
        return None
        
    except Exception as e:
        print(f"Authentication error: {e}")
        return None

# Mengambil data user berdasarkan ID
def get_user_by_id(user_id):
    try:
        collection = get_collection('users')
        
        try:
            user = collection.find_one({'_id': ObjectId(user_id)})
        except:
            user = collection.find_one({'_id': user_id})
        
        if user:
            return {
                '_id': str(user['_id']),
                'nomor_identitas': user.get('nomor_identitas', ''),
                'nama_lengkap': user.get('nama_lengkap', ''),
                'role': user.get('role', ''),
            }
        return None
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        return None

# cek data pemeriksaan user
def check_user_examinations(user_id):
    try:
        collection = get_collection('patient_examinations')
        
        try:
            count = collection.count_documents({'pasien_id': ObjectId(user_id)})
        except:
            count = collection.count_documents({'pasien_id': user_id})
        
        return count > 0
    except Exception as e:
        print(f"Error checking user examinations: {e}")
        return False
