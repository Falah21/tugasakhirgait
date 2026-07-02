import streamlit as st
from datetime import datetime
from database.mongodb import get_collection
from models.gait_normal import GaitAnalysisDataNormal

def input_data_gait_normal():
    st.subheader("Input Baseline Data Gait")
    uploaded_file = st.file_uploader("Upload file data subjek gait normal (Format .xlsx)", type=["xlsx"], key="normal_upload")
    
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        with col1:
            usia = st.number_input("Masukkan Usia:", min_value=0, max_value=120, key="usia_normal")
        with col2:
            jenis_kelamin = st.selectbox("Jenis Kelamin", ["Pilih Jenis Kelamin", "L", "P"], key="gender_normal").strip().upper()

        if st.button("Proses Data Baseline", key="process_normal"):
            if usia == 0 or jenis_kelamin == "":
                st.warning("Harap masukkan usia dan jenis kelamin sebelum memproses file.")
            elif jenis_kelamin not in ['L', 'P']:
                st.warning("Jenis kelamin harus diisi.")
            else:
                try:
                    content = uploaded_file.read()
                    gait_data = GaitAnalysisDataNormal(content, usia, jenis_kelamin)
                
                    if hasattr(gait_data, 'df'):
                        data_dict = gait_data.to_dict()

                        def check_missing(data):
                            if isinstance(data, dict):
                                return any(check_missing(v) for v in data.values())
                            elif isinstance(data, list):
                                return any(check_missing(v) for v in data)
                            else:
                                return pd.isna(data)

                        def check_norm_kinematics(norm_kinematics):
                            for key, value in norm_kinematics.items():
                                if isinstance(value, list):
                                    for v in value:
                                        if pd.isna(v):
                                            return True
                                        try:
                                            float(v)
                                        except ValueError:
                                            return True
                                else:
                                    return True
                            return False

                        norm_kin_data = data_dict.get("Norm Kinematics", {})
                        if check_missing(data_dict) or check_norm_kinematics(norm_kin_data):
                            st.error("Data tidak valid: terdapat nilai kosong atau teks non-numerik.")
                        else:
                            try:
                                collection = get_collection('gait_data')
                                data_dict["upload_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                collection.insert_one(data_dict)
                                st.success("Data berhasil disimpan ke database!")
                                
                                st.markdown("Ringkasan Data yang Disimpan")
                                st.json({
                                    "Nama Subjek": data_dict["Subject Parameters"]["Subject Name"],
                                    "Usia": data_dict["Subject Parameters"]["Age"],
                                    "Jenis Kelamin": data_dict["Subject Parameters"]["Gender"],
                                    "BMI": f"{data_dict['Subject Parameters']['BMI']:.2f}",
                                    "Klasifikasi BMI": data_dict["Subject Parameters"]["BMI Classification"]
                                })
                            except Exception as e:
                                st.error(f"Error menyimpan data ke database: {e}")
                    else:
                        st.error("Gagal memproses data yang diupload.")
                except Exception as e:
                    st.error(f"Error dalam memproses file: {e}")
