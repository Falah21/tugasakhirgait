import streamlit as st
import pandas as pd
from database.mongodb import get_collection

def manage_normal_data():
    st.markdown("### Baseline Data Gait")

    collection = get_collection('gait_data')
    
    total_data = collection.count_documents({})
    male_count = collection.count_documents({"Subject Parameters.Gender": "L"})
    female_count = collection.count_documents({"Subject Parameters.Gender": "P"})
    
    col1, col2, col3 = st.columns(3) 
    with col1:
        st.markdown(f"""
        <div class="stats-card">
            <div>Total Data Gait Normal</div>
            <div class="stats-number">{total_data}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stats-card">
            <div>Data Pria</div>
            <div class="stats-number">{male_count}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stats-card">
            <div>Data Wanita</div>
            <div class="stats-number">{female_count}</div>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("Daftar Baseline Data Gait")
    
    data = list(collection.find())
    if not data:
        st.warning("Data baseline gait tidak ditemukan.")
        return

    table_data = []
    for doc in data:
        subject_params = doc.get('Subject Parameters', {})
        table_data.append({
            '_id': str(doc['_id']),
            'Nama Subject': subject_params.get('Subject Name', 'N/A'),
            'Usia': subject_params.get('Age', 'N/A'),
            'Gender': subject_params.get('Gender', 'N/A'),
            'Tinggi (cm)': round(subject_params.get('Height (mm)', 0) / 10, 1) if subject_params.get('Height (mm)') else 'N/A',
            'Berat (kg)': subject_params.get('Bodymass (kg)', 'N/A'),
            'BMI': round(subject_params.get('BMI', 0), 2) if subject_params.get('BMI') else 'N/A',
            'Klasifikasi BMI': subject_params.get('BMI Classification', 'N/A'),
            'Tanggal Upload': doc.get('upload_date', 'N/A')
        })
        
    df = pd.DataFrame(table_data)
    display_df = df.drop('_id', axis=1)
    st.dataframe(display_df, use_container_width=True)

    st.subheader("Kelola Data Baseline")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Edit Data")
        
        if data:
            edit_options_dict = {}
            for doc in data:
                subject_params = doc.get('Subject Parameters', {})
                name = subject_params.get('Subject Name', 'N/A')
                age = subject_params.get('Age', 'N/A')
                gender = subject_params.get('Gender', 'N/A')
                display_text = f"{name} ({age} tahun, {gender})"
                edit_options_dict[display_text] = doc

            edit_options_list = ["Pilih Data untuk Diedit"] + list(edit_options_dict.keys())
            
            selected_display = st.selectbox(
                "Silahkan pilih data yang akan diedit!!",
                options=edit_options_list,
                key="edit_select"
            )

            if selected_display and selected_display != "Pilih Data untuk Diedit":
                selected_doc = edit_options_dict[selected_display]
                if selected_doc:
                    with st.form("edit_form"):
                        subject_params = selected_doc.get('Subject Parameters', {})
                        current_name = subject_params.get('Subject Name', '')
                        new_name = st.text_input("Nama Subjek", value=subject_params.get('Subject Name', ''))
                        new_age = st.number_input("Usia", min_value=0, max_value=120, value=subject_params.get('Age', 0))
                        new_gender = st.selectbox("Jenis Kelamin", ["L", "P"], index=0 if subject_params.get('Gender') == 'L' else 1)
                        new_height = st.number_input("Tinggi (mm)", min_value=0, value=subject_params.get('Height (mm)', 0))
                        new_weight = st.number_input("Berat (kg)", min_value=0.0, value=subject_params.get('Bodymass (kg)', 0.0))
                        
                        if st.form_submit_button("Update Data"):
                            errors = []
                            if new_name != current_name:
                                existing_data = collection.find_one({
                                    "Subject Parameters.Subject Name": new_name,
                                    "_id": {"$ne": selected_doc['_id']}
                                })
                                if existing_data:
                                    errors.append(f"Nama '{new_name}' sudah terdaftar! Silahkan gunakan nama yang berbeda.")
                            if errors:
                                for err in errors:
                                    st.error(err)
                            else:
                                update_data = {
                                    "Subject Parameters.Subject Name": new_name,
                                    "Subject Parameters.Age": new_age,
                                    "Subject Parameters.Gender": new_gender,
                                    "Subject Parameters.Height (mm)": new_height,
                                    "Subject Parameters.Bodymass (kg)": new_weight
                                }
                                
                                height_m = new_height / 1000
                                new_bmi = new_weight / (height_m ** 2) if height_m > 0 else 0
                                bmi_class = (
                                    "Kurus Berat" if new_bmi < 17.0 else
                                    "Kurus Ringan" if 17.0 <= new_bmi <= 18.4 else
                                    "Normal" if 18.5 <= new_bmi <= 25.0 else
                                    "Gemuk Ringan" if 25.1 <= new_bmi <= 27.0 else
                                    "Gemuk Berat")
                                
                                update_data["Subject Parameters.BMI"] = round(new_bmi, 2)
                                update_data["Subject Parameters.BMI Classification"] = bmi_class
                                
                                collection.update_one({'_id': selected_doc['_id']}, {'$set': update_data})
                                st.success(f"Data {new_name} berhasil diupdate!")
                                st.rerun()
        else:
            st.info("Tidak ada data yang dapat diedit")
    
    with col2:
        st.markdown("#### Hapus Data")
        
        if data:
            delete_options_dict = {}
            for doc in data:
                subject_params = doc.get('Subject Parameters', {})
                name = subject_params.get('Subject Name', 'N/A')
                age = subject_params.get('Age', 'N/A')
                gender = subject_params.get('Gender', 'N/A')
                display_text = f"{name} ({age} tahun, {gender})"
                delete_options_dict[display_text] = doc

            delete_options_list = ["Pilih Data untuk Dihapus"] + list(delete_options_dict.keys())
            
            selected_delete_display = st.selectbox(
                "Silahkan pilih data yang ingin dihapus!!",
                options=delete_options_list,
                key="delete_select"
            )
            
            if selected_delete_display and selected_delete_display != "Pilih Data untuk Dihapus":
                selected_doc = delete_options_dict[selected_delete_display]
                if selected_doc:
                    subject_params = selected_doc.get('Subject Parameters', {})
                    st.warning(f"Anda akan menghapus data: **{subject_params.get('Subject Name', 'N/A')}**")
                    st.write(f"- Usia: {subject_params.get('Age', 'N/A')}")
                    st.write(f"- Gender: {subject_params.get('Gender', 'N/A')}")
                    st.write(f"- Tinggi: {subject_params.get('Height (mm)', 'N/A')} mm")
                    st.write(f"- Berat: {subject_params.get('Bodymass (kg)', 'N/A')} kg")
                    st.write(f"- BMI: {subject_params.get('BMI', 'N/A')} ({subject_params.get('BMI Classification', 'N/A')})")
                    
                    col_confirm1, col_confirm2 = st.columns(2)
                    with col_confirm1:
                        if st.button("Hapus Permanen", type="secondary", use_container_width=True):
                            collection.delete_one({'_id': selected_doc['_id']})
                            st.success("Data berhasil dihapus!")
                            st.rerun()
                    with col_confirm2:
                        if st.button("Batal", use_container_width=True):
                            st.info("Penghapusan dibatalkan")
        else:
            st.info("Tidak ada data yang dapat dihapus")
