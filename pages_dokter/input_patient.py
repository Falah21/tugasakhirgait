import streamlit as st
import pandas as pd
from datetime import datetime
from bson import ObjectId
from database.mongodb import get_collection
from models.gait_patient import GaitAnalysisData
from services.bmi_service import calculate_bmi, classify_bmi

def input_data_gait_pasien():
    st.subheader("Input Pemeriksaan Pasien")
    
    with st.form(key="form_pemeriksaan_pasien"):
        try:
            collection = get_collection('users')
            pasien_data = list(collection.find({'role': 'pasien'}, {'_id': 1, 'nomor_identitas': 1, 'nama_lengkap': 1}))
    
            pasien_options = ["Pilih Data Pasien yang akan diperiksa"] + [
                f"{pasien['nomor_identitas']} - {pasien['nama_lengkap']}" 
                for pasien in pasien_data
                if 'nomor_identitas' in pasien and 'nama_lengkap' in pasien
            ]
            
            pasien_mapping = {}
            for pasien in pasien_data:
                if 'nomor_identitas' in pasien and 'nama_lengkap' in pasien:
                    display_text = f"{pasien['nomor_identitas']} - {pasien['nama_lengkap']}"
                    pasien_mapping[display_text] = {
                        '_id': str(pasien['_id']),
                        'nomor_identitas': pasien['nomor_identitas'],
                        'nama_lengkap': pasien['nama_lengkap']
                    }
            
        except Exception as e:
            st.error(f"Error mengambil data pasien: {e}")
            pasien_options = ["Pilih Data Pasien yang akan diperiksa"]
            pasien_mapping = {}
        
        selected_pasien_display = st.selectbox(
            "Pilih Data Pasien yang akan diperiksa", 
            options=pasien_options, 
            key="pasien_dropdown_form"
        )
        
        tanggal = st.date_input("Tanggal Pemeriksaan", key="tanggal_form")
        col1, col2 = st.columns(2)
        with col1:
            tinggi_badan = st.number_input("Tinggi Badan (cm)", min_value=0.0, step=0.1, format="%.1f", key="tinggi_form")
        with col2:
            berat_badan = st.number_input("Berat Badan (kg)", min_value=0.0, step=0.1, format="%.1f", key="berat_form")
        uploaded_file = st.file_uploader("Upload file data gait pasien (Format .xlsx)", type=["xlsx"], key="file_uploader_form")
        submit_button = st.form_submit_button("Simpan Data Pemeriksaan", type="primary", use_container_width=True)

    if submit_button:  
        if selected_pasien_display == "Pilih Data Pasien yang akan diperiksa":
            st.warning("Silakan pilih pasien terlebih dahulu sebelum mengupload file.")
            return
        if uploaded_file is None:
            st.warning("Silakan upload file data gait pasien terlebih dahulu.")
            return
        if tinggi_badan <= 0 or berat_badan <= 0:
            st.warning("Silakan isi tinggi badan dan berat badan dengan benar.")
            return
        
        bmi = calculate_bmi(berat_badan, tinggi_badan)
        bmi_class = classify_bmi(bmi)
        
        if selected_pasien_display in pasien_mapping:
            pasien_data_selected = pasien_mapping[selected_pasien_display]
            pasien_object_id = pasien_data_selected['_id']
            pasien_nomor_identitas = pasien_data_selected['nomor_identitas']
            nama_pasien = pasien_data_selected['nama_lengkap']
        else:
            st.error("Data pasien tidak valid.")
            return

        try:              
            gait_data = GaitAnalysisData(uploaded_file)
            processed_data = gait_data.to_dict()
            
            norm_kinematics = processed_data["Norm Kinematics"]
            rows = []
            
            for i in range(len(norm_kinematics["Percentage of Gait Cycle"])):
                row = {
                    "%cycle": norm_kinematics["Percentage of Gait Cycle"][i],
                    "LPelvisAngles_X": norm_kinematics["LPelvisAngles_X"][i],
                    "RPelvisAngles_X": norm_kinematics["RPelvisAngles_X"][i],
                    "LHipAngles_X": norm_kinematics["LHipAngles_X"][i],
                    "RHipAngles_X": norm_kinematics["RHipAngles_X"][i],
                    "LKneeAngles_X": norm_kinematics["LKneeAngles_X"][i],
                    "RKneeAngles_X": norm_kinematics["RKneeAngles_X"][i],
                    "LAnkleAngles_X": norm_kinematics["LAnkleAngles_X"][i],
                    "RAnkleAngles_X": norm_kinematics["RAnkleAngles_X"][i],
                }
                rows.append(row)

            st.session_state.norm_kinematics_df = pd.DataFrame(rows)
            
            examination_data = {
                'pasien_id': ObjectId(pasien_object_id),
                'pasien_nomor_identitas': pasien_nomor_identitas,
                'nama_pasien': nama_pasien,
                'dokter_id': ObjectId(st.session_state.get('dokter_user_id')),
                'dokter_nama': st.session_state.get('dokter_nama', 'unknown'),
                'tanggal_pemeriksaan': tanggal.strftime("%Y-%m-%d"),
                'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'tinggi_badan': tinggi_badan,
                'berat_badan': berat_badan,
                'bmi': bmi,
                'bmi_classification': bmi_class,
                'file_info': {
                    'file_name': uploaded_file.name
                },
                'gait_data': processed_data,
            }
            
            collection = get_collection('patient_examinations')

            st.session_state.current_pasien_id = pasien_object_id
            st.session_state.current_pasien_nomor_identitas = pasien_nomor_identitas
            st.session_state.current_nama_pasien = nama_pasien
            st.session_state.current_tanggal_pemeriksaan = tanggal.strftime("%Y-%m-%d")
            
            current_key = f"patient_{pasien_object_id}_{tanggal.strftime('%Y-%m-%d')}"
            st.session_state.current_patient_key = current_key

            _reset_ai_summary_for_patient_and_date(pasien_object_id, tanggal.strftime("%Y-%m-%d"))
            
            existing_exam = collection.find_one({
                'pasien_id': ObjectId(pasien_object_id), 
                'tanggal_pemeriksaan': tanggal.strftime("%Y-%m-%d")
            })

            if existing_exam:
                collection.update_one(
                    {'_id': existing_exam['_id']},
                    {'$set': examination_data}
                )
                st.success(f"Data gait pasien dengan NIK {pasien_nomor_identitas} berhasil diupdate!")
            else:
                collection.insert_one(examination_data)
                st.success(f"Data pasien dengan NIK {pasien_nomor_identitas} berhasil disimpan!")
        except Exception as e:
            st.error(f"Error dalam memproses file: {e}")

def _reset_ai_summary_for_patient_and_date(pasien_object_id, tanggal_pemeriksaan):
    patient_date_key = f"patient_{pasien_object_id}_{tanggal_pemeriksaan}"
    
    keys_to_reset = [
        f'ai_summaries_generated_{patient_date_key}',
        f'saved_summary_content_{patient_date_key}'
    ]
    
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    
    if 'ai_summaries_generated' in st.session_state and st.session_state.get('current_patient_key') == patient_date_key:
        if 'ai_summaries_generated' in st.session_state:
            del st.session_state['ai_summaries_generated']
