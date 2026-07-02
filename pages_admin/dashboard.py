import streamlit as st
from database.mongodb import get_collection

def show_dashboard():
    st.markdown("### Beranda Admin")
    st.info("Selamat datang di Sistem Dashboard Pemeriksaan Gait. Gunakan menu di sidebar untuk mengakses menu yang tersedia.")
    
    _load_pasien_data()
    
    collection = get_collection('gait_data')
    
    total_pasien = len(st.session_state.pasien_list)
    total_data = collection.count_documents({})
    
    try:
        collection_exams = get_collection('patient_examinations')
        total_exams = collection_exams.count_documents({})
    except:
        total_exams = 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stats-card">
            <div>Total Pasien</div>
            <div class="stats-number">{total_pasien}</div>
            <div>Terdaftar</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stats-card">
            <div>Baseline Data Gait</div>
            <div class="stats-number">{total_data}</div>
            <div>Dataset</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stats-card">
            <div>Pemeriksaan</div>
            <div class="stats-number">{total_exams}</div>
            <div>Total</div>
        </div>
        """, unsafe_allow_html=True)

def _load_pasien_data():
    if not st.session_state.get('pasien_list_initialized', False):
        try:
            collection = get_collection('users')
            pasien_data = list(collection.find({'role': 'pasien'}))

            st.session_state.pasien_list = []
            for pasien in pasien_data:
                st.session_state.pasien_list.append({
                    "_id": str(pasien['_id']),
                    "Nomor Identitas": pasien.get('nomor_identitas', ''),
                    "Nama Lengkap": pasien.get('nama_lengkap', ''),
                    "Tanggal Lahir": pasien.get('tanggal_lahir', ''),
                    "Jenis Kelamin": pasien.get('jenis_kelamin', ''),
                    "Role": pasien.get('role', ''),
                    "Tanggal Dibuat": pasien.get('tanggal_dibuat', '')
                })
            
            st.session_state.pasien_list_initialized = True
                
        except Exception as e:
            st.error(f"Error loading patient data: {e}")
