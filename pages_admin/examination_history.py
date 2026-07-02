import streamlit as st
import pandas as pd
from datetime import datetime
from bson import ObjectId
from database.mongodb import get_collection
from services.auth_service import get_user_by_id

def show_examination_history():
    st.markdown("### Riwayat Pemeriksaan Pasien")
    
    try:
        collection = get_collection('patient_examinations')
        examinations = list(collection.find().sort('upload_date', -1))
        
        if not examinations:
            st.info("Belum ada riwayat pemeriksaan pasien.")
            return
        
        total_exams = len(examinations)
        current_month = datetime.now().strftime("%Y-%m")
        monthly_exams = len([exam for exam in examinations 
                             if exam.get('upload_date', '').startswith(current_month)])
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Pemeriksaan Keseluruhan", total_exams)
        with col2:
            st.metric("Pemeriksaan Bulan Ini", monthly_exams)
        
        table_data = []
        for exam in examinations:
            pasien_id = exam.get('pasien_id')
            nama_pasien = exam.get('nama_pasien', 'N/A')
            if isinstance(pasien_id, ObjectId):
                pasien_data = get_user_by_id(str(pasien_id))
                if pasien_data:
                    nama_pasien = pasien_data.get('nama_lengkap', 'N/A')
                    nomor_identitas = pasien_data.get('nomor_identitas', 'N/A')
                else:
                    nomor_identitas = str(pasien_id)
            else:
                nomor_identitas = pasien_id if pasien_id else 'N/A'
            
            dokter_id = exam.get('dokter_id')
            dokter_nama = exam.get('dokter_nama', 'N/A')
            if isinstance(dokter_id, ObjectId):
                dokter_data = get_user_by_id(str(dokter_id))
                if dokter_data:
                    dokter_nama = dokter_data.get('nama_lengkap', 'N/A')
            
            tanggal_pemeriksaan = exam.get('tanggal_pemeriksaan', 'N/A')
            upload_date = exam.get('upload_date', 'N/A')
            tinggi_badan = exam.get('tinggi_badan', 'N/A')
            berat_badan = exam.get('berat_badan', 'N/A')
            bmi = exam.get('bmi', 'N/A')
            bmi_class = exam.get('bmi_classification', 'N/A')
            file_info = exam.get('file_info', {})
            file_name = file_info.get('file_name', 'N/A') if isinstance(file_info, dict) else 'N/A'
            
            table_data.append({
                'Tanggal Pemeriksaan': tanggal_pemeriksaan,
                'ID Pasien': nomor_identitas,
                'Nama Pasien': nama_pasien,
                'Tinggi (cm)': f"{tinggi_badan:.1f}" if isinstance(tinggi_badan, (int, float)) else tinggi_badan,
                'Berat (kg)': f"{berat_badan:.1f}" if isinstance(berat_badan, (int, float)) else berat_badan,
                'Klasifikasi BMI': bmi_class,
                'Dokter': dokter_nama,
                'File Name': file_name,
            })
        
        df = pd.DataFrame(table_data)

        st.markdown("### Filter Data")
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_nik = st.text_input("Filter berdasarkan ID Pasien:")
        with col2:
            filter_nama = st.text_input("Filter berdasarkan Nama Pasien:")
        with col3:
            filter_dokter = st.text_input("Filter berdasarkan Nama Dokter:")

        filtered_df = df.copy()
        if filter_nik:
            filtered_df = filtered_df[filtered_df['ID Pasien'].astype(str).str.contains(filter_nik, case=False, na=False)]
        if filter_nama:
            filtered_df = filtered_df[filtered_df['Nama Pasien'].str.contains(filter_nama, case=False, na=False)]
        if filter_dokter:
            filtered_df = filtered_df[filtered_df['Dokter'].astype(str).str.contains(filter_dokter, case=False, na=False)]

        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True)
            st.markdown(f"**Menampilkan {len(filtered_df)} dari {len(df)} data pemeriksaan**")

            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download Riwayat sebagai CSV",
                data=csv,
                file_name=f"riwayat_pemeriksaan_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv")
        else:
            st.info("Tidak ada data yang sesuai dengan filter.")
        
    except Exception as e:
        st.error(f"Error mengambil data riwayat pemeriksaan: {e}")
