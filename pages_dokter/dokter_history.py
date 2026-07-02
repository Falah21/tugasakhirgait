import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from bson import ObjectId
from database.mongodb import get_collection
from services.auth_service import get_user_by_id
from pages_dokter.dokter_visualization import (
    get_phase_indices,
    calculate_mae_per_phase
)
import numpy as np

def show_examination_history():
    st.subheader("Riwayat Pemeriksaan")

    tab1, tab2 = st.tabs(["Riwayat Pemeriksaan", "Detail Riwayat Pasien"])
    with tab1:
        _show_examination_list()
    with tab2:
        show_patient_detail_history()

def _show_examination_list():
    try:
        collection = get_collection('patient_examinations')
        
        dokter_id = st.session_state.get('dokter_user_id', None)
        dokter_nama = st.session_state.get('dokter_nama', None)
        
        if not dokter_id:
            st.error("Data dokter tidak ditemukan. Silakan login kembali.")
            return

        examinations = list(collection.find({'dokter_id': ObjectId(dokter_id)}).sort('upload_date', -1))
        
        if not examinations:
            st.info(f"Belum ada riwayat pemeriksaan pasien untuk Dr. {dokter_nama}.")
            return

        table_data = []
        for exam in examinations:
            file_info = exam.get('file_info', {})
            table_data.append({
                'Tanggal Pemeriksaan': exam.get('tanggal_pemeriksaan', 'N/A'),
                'NIK Pasien': exam.get('pasien_nomor_identitas', 'N/A'),
                'Nama Pasien': exam.get('nama_pasien', 'N/A'),
                'Tinggi (cm)':  exam.get('tinggi_badan', 'N/A'),
                'Berat (kg)': exam.get('berat_badan', 'N/A'),
                'Klasifikasi BMI': exam.get('bmi_classification', 'N/A'),
                'Dokter': dokter_nama,
                'File Name': file_info.get('file_name', 'N/A') if isinstance(file_info, dict) else 'N/A'
            })
        
        df = pd.DataFrame(table_data)
        
        st.markdown("#### Filter Riwayat")
        col1, col2 = st.columns(2)
        
        with col1:
            filter_nik = st.text_input("Filter berdasarkan NIK Pasien:")
        with col2:
            filter_nama = st.text_input("Filter berdasarkan Nama Pasien:")

        filtered_df = df.copy()
        if filter_nik:
            filtered_df = filtered_df[filtered_df['NIK Pasien'].str.contains(filter_nik, case=False, na=False)]
        if filter_nama:
            filtered_df = filtered_df[filtered_df['Nama Pasien'].str.contains(filter_nama, case=False, na=False)]
        
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True)
            st.markdown(f"**Menampilkan {len(filtered_df)} dari {len(df)} data pemeriksaan**")

            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download Riwayat sebagai CSV", 
                data=csv, 
                file_name=f"riwayat_pemeriksaan_{datetime.now().strftime('%Y%m%d')}.csv", 
                mime="text/csv"
            )
        else:
            st.info("Tidak ada data yang sesuai dengan filter.")

    except Exception as e:
        st.error(f"Error mengambil data riwayat: {e}")

def show_patient_detail_history():
    st.markdown("#### Detail Riwayat Pemeriksaan Pasien")
    
    try:
        users_collection = get_collection('users')
        examinations_collection = get_collection('patient_examinations')
        
        pasien_data = list(users_collection.find(
            {'role': 'pasien'}, 
            {'_id': 1, 'nomor_identitas': 1, 'nama_lengkap': 1, 'tanggal_lahir': 1, 'jenis_kelamin': 1}
        ))
        
        if not pasien_data:
            st.info("Belum ada data pasien terdaftar.")
            return
        
        pasien_options = ["Silakan pilih pasien"] + [
            f"{p['nomor_identitas']} - {p['nama_lengkap']}" 
            for p in pasien_data
            if 'nomor_identitas' in p and 'nama_lengkap' in p
        ]
        
        pasien_mapping = {
            f"{p['nomor_identitas']} - {p['nama_lengkap']}": {
                'id': str(p['_id']),
                'nomor_identitas': p['nomor_identitas'],
                'nama_lengkap': p['nama_lengkap'],
                'tanggal_lahir': p.get('tanggal_lahir', '-'),
                'jenis_kelamin': p.get('jenis_kelamin', '-')
            }
            for p in pasien_data
            if 'nomor_identitas' in p and 'nama_lengkap' in p
        }
        
        selected_label = st.selectbox(
            "Pilih Pasien", 
            options=pasien_options, 
            key="detail_pasien_select", 
            index=0
        )
        
        if selected_label == "Silakan pilih pasien" or not selected_label:
            st.info("Silakan pilih pasien terlebih dahulu untuk melihat riwayat pemeriksaan.")
            return
            
        pasien_info = pasien_mapping.get(selected_label)
        if not pasien_info:
            st.error("Data pasien tidak ditemukan.")
            return
        
        pasien_object_id = pasien_info['id']
        pasien_nomor_identitas = pasien_info['nomor_identitas']
        nama_pasien = pasien_info['nama_lengkap']
        
        if pasien_info:
            with st.expander("Profil Pasien", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**NIK:** {pasien_nomor_identitas}")
                    st.markdown(f"**Nama Lengkap:** {nama_pasien}")
                    st.markdown(f"**Jenis Kelamin:** {pasien_info.get('jenis_kelamin', '-')}")

                with col2:
                    st.markdown(f"**Tanggal Lahir:** {pasien_info.get('tanggal_lahir', '-')}")
                    st.markdown(f"**Usia:** {_calculate_age(pasien_info.get('tanggal_lahir', ''))} tahun")
            
        dokter_id = st.session_state.get('dokter_user_id')
        examinations = list(examinations_collection.find({
            'pasien_id': ObjectId(pasien_object_id), 
            'dokter_id': ObjectId(dokter_id)
        }).sort('tanggal_pemeriksaan', -1))
            
        if not examinations:
            st.warning(f"Belum ada riwayat pemeriksaan untuk pasien ini.")
            return
            
        tanggal_options = {f"{e['tanggal_pemeriksaan']}": e for e in examinations}
        selected_tanggal_label = st.selectbox(
            "Pilih Tanggal Pemeriksaan", 
            options=list(tanggal_options.keys()), 
            key="detail_tanggal_select"
        )
            
        if selected_tanggal_label:
            selected_exam = tanggal_options[selected_tanggal_label]
            _show_patient_examination_detail(selected_exam, pasien_object_id)
                    
    except Exception as e:
        st.error(f"Error mengambil data riwayat: {e}")

def _show_patient_examination_detail(examination, pasien_object_id):
    tanggal = examination.get('tanggal_pemeriksaan')
    st.markdown(f"#### Hasil Pemeriksaan - {tanggal}")
    
    with st.container(border=True):
        st.markdown("##### Informasi Pasien")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Tinggi Badan:** {examination.get('tinggi_badan', '-')} cm")
            st.markdown(f"**Berat Badan:** {examination.get('berat_badan', '-')} kg")
        with col2:
            st.markdown(f"**BMI:** {examination.get('bmi', '-'):.2f}" if examination.get('bmi') else "**BMI:** -")
            st.markdown(f"**Klasifikasi BMI:** {examination.get('bmi_classification', '-')}")
    
    gait_data = examination.get('gait_data', {})
    norm_kinematics = gait_data.get('Norm Kinematics', {})
    
    if not norm_kinematics:
        st.warning("Data kinematik tidak tersedia untuk pemeriksaan ini.")
        return
    
    normal_data = _get_normal_data_for_comparison()
    if normal_data is None:
        st.error("Data normal belum tersedia. Silakan hubungi administrator.")
        return
    
    rows = []
    for i in range(len(norm_kinematics.get("Percentage of Gait Cycle", []))):
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
    
    patient_kinematics_df = pd.DataFrame(rows)
    
    temp_norm_kinematics_df = st.session_state.get('norm_kinematics_df', None)
    temp_filtered_normal_df = st.session_state.get('filtered_normal_df', None)
    
    st.session_state.norm_kinematics_df = patient_kinematics_df
    st.session_state.filtered_normal_df = normal_data
    
    kinematic_data = _process_kinematic_data_for_detail(normal_data, norm_kinematics)
    
    percentage_cycle = list(range(101))
    phase_indices = get_phase_indices(percentage_cycle)
    
    l_pelvis_normal = pd.DataFrame(normal_data['LPelvisAngles_X'].tolist()).mean(axis=0).values
    r_pelvis_normal = pd.DataFrame(normal_data['RPelvisAngles_X'].tolist()).mean(axis=0).values
    
    mae_pelvis_left_phases = calculate_mae_per_phase(
        np.array(norm_kinematics.get('LPelvisAngles_X', [])), 
        l_pelvis_normal, 
        phase_indices
    )
    mae_pelvis_right_phases = calculate_mae_per_phase(
        np.array(norm_kinematics.get('RPelvisAngles_X', [])), 
        r_pelvis_normal, 
        phase_indices
    )
    
    l_knee_normal = pd.DataFrame(normal_data['LKneeAngles_X'].tolist()).mean(axis=0).values
    r_knee_normal = pd.DataFrame(normal_data['RKneeAngles_X'].tolist()).mean(axis=0).values
    
    mae_knee_left_phases = calculate_mae_per_phase(
        np.array(norm_kinematics.get('LKneeAngles_X', [])), 
        l_knee_normal, 
        phase_indices
    )
    mae_knee_right_phases = calculate_mae_per_phase(
        np.array(norm_kinematics.get('RKneeAngles_X', [])), 
        r_knee_normal, 
        phase_indices
    )
    
    l_hip_normal = pd.DataFrame(normal_data['LHipAngles_X'].tolist()).mean(axis=0).values
    r_hip_normal = pd.DataFrame(normal_data['RHipAngles_X'].tolist()).mean(axis=0).values
    
    mae_hip_left_phases = calculate_mae_per_phase(
        np.array(norm_kinematics.get('LHipAngles_X', [])), 
        l_hip_normal, 
        phase_indices
    )
    mae_hip_right_phases = calculate_mae_per_phase(
        np.array(norm_kinematics.get('RHipAngles_X', [])), 
        r_hip_normal, 
        phase_indices
    )
    
    l_ankle_normal = pd.DataFrame(normal_data['LAnkleAngles_X'].tolist()).mean(axis=0).values
    r_ankle_normal = pd.DataFrame(normal_data['RAnkleAngles_X'].tolist()).mean(axis=0).values
    
    mae_ankle_left_phases = calculate_mae_per_phase(
        np.array(norm_kinematics.get('LAnkleAngles_X', [])), 
        l_ankle_normal, 
        phase_indices
    )
    mae_ankle_right_phases = calculate_mae_per_phase(
        np.array(norm_kinematics.get('RAnkleAngles_X', [])), 
        r_ankle_normal, 
        phase_indices
    )
    
    st.session_state.mae_pelvis_left = np.mean(list(mae_pelvis_left_phases.values())) if mae_pelvis_left_phases else 0
    st.session_state.mae_pelvis_right = np.mean(list(mae_pelvis_right_phases.values())) if mae_pelvis_right_phases else 0
    st.session_state.mae_knee_left = np.mean(list(mae_knee_left_phases.values())) if mae_knee_left_phases else 0
    st.session_state.mae_knee_right = np.mean(list(mae_knee_right_phases.values())) if mae_knee_right_phases else 0
    st.session_state.mae_hip_left = np.mean(list(mae_hip_left_phases.values())) if mae_hip_left_phases else 0
    st.session_state.mae_hip_right = np.mean(list(mae_hip_right_phases.values())) if mae_hip_right_phases else 0
    st.session_state.mae_ankle_left = np.mean(list(mae_ankle_left_phases.values())) if mae_ankle_left_phases else 0
    st.session_state.mae_ankle_right = np.mean(list(mae_ankle_right_phases.values())) if mae_ankle_right_phases else 0
    
    st.session_state.mae_pelvis_left_phases = mae_pelvis_left_phases
    st.session_state.mae_pelvis_right_phases = mae_pelvis_right_phases
    st.session_state.mae_knee_left_phases = mae_knee_left_phases
    st.session_state.mae_knee_right_phases = mae_knee_right_phases
    st.session_state.mae_hip_left_phases = mae_hip_left_phases
    st.session_state.mae_hip_right_phases = mae_hip_right_phases
    st.session_state.mae_ankle_left_phases = mae_ankle_left_phases
    st.session_state.mae_ankle_right_phases = mae_ankle_right_phases
    st.session_state.phase_indices = phase_indices
    
    _show_detail_visualization(kinematic_data, pasien_object_id, tanggal, examination)
    
    if temp_norm_kinematics_df is not None:
        st.session_state.norm_kinematics_df = temp_norm_kinematics_df
    else:
        if 'norm_kinematics_df' in st.session_state:
            del st.session_state.norm_kinematics_df
    
    if temp_filtered_normal_df is not None:
        st.session_state.filtered_normal_df = temp_filtered_normal_df
    else:
        if 'filtered_normal_df' in st.session_state:
            del st.session_state.filtered_normal_df

def _get_normal_data_for_comparison():
    try:
        collection = get_collection('gait_data')
        cursor = collection.find().limit(100)
        data = list(cursor)
        
        if len(data) == 0:
            return None
        
        df = pd.json_normalize(data)
        df.columns = df.columns.str.replace('Trial Information.', '')
        df.columns = df.columns.str.replace('Subject Parameters.', '')
        df.columns = df.columns.str.replace('Body Measurements.', '')
        df.columns = df.columns.str.replace('Norm Kinematics.', '')
        
        return df
    except Exception as e:
        st.error(f"Error mengambil data normal: {e}")
        return None

def _process_kinematic_data_for_detail(filtered_df, patient_kinematics):
    l_pelvis_angles = pd.DataFrame(filtered_df['LPelvisAngles_X'].tolist())
    r_pelvis_angles = pd.DataFrame(filtered_df['RPelvisAngles_X'].tolist())
    
    mean_l_pelvis = l_pelvis_angles.mean(axis=0).values
    std_l_pelvis = l_pelvis_angles.std(axis=0)/np.sqrt(l_pelvis_angles.shape[0])
    mean_r_pelvis = r_pelvis_angles.mean(axis=0).values
    std_r_pelvis = r_pelvis_angles.std(axis=0)/np.sqrt(r_pelvis_angles.shape[0])
    
    lpelvis = pd.DataFrame({
        "%cycle": list(range(101)),
        'mean': mean_l_pelvis,
        'std': std_l_pelvis
    })
    
    rpelvis = pd.DataFrame({
        "%cycle": list(range(101)),
        'mean': mean_r_pelvis,
        'std': std_r_pelvis
    })
    
    l_knee_angles = pd.DataFrame(filtered_df['LKneeAngles_X'].tolist())
    r_knee_angles = pd.DataFrame(filtered_df['RKneeAngles_X'].tolist())
    
    mean_l_knee = l_knee_angles.mean(axis=0).values
    std_l_knee = l_knee_angles.std(axis=0) / np.sqrt(l_knee_angles.shape[0])
    mean_r_knee = r_knee_angles.mean(axis=0).values
    std_r_knee = r_knee_angles.std(axis=0) / np.sqrt(r_knee_angles.shape[0])
    
    lknee = pd.DataFrame({
        "%cycle": list(range(101)),
        'mean': mean_l_knee,
        'std': std_l_knee
    })
    
    rknee = pd.DataFrame({
        "%cycle": list(range(101)),
        'mean': mean_r_knee,
        'std': std_r_knee
    })
    
    l_hip_angles = pd.DataFrame(filtered_df['LHipAngles_X'].tolist())
    r_hip_angles = pd.DataFrame(filtered_df['RHipAngles_X'].tolist())
    
    mean_l_hip = l_hip_angles.mean(axis=0).values
    std_l_hip = l_hip_angles.std(axis=0) / np.sqrt(l_hip_angles.shape[0])
    mean_r_hip = r_hip_angles.mean(axis=0).values
    std_r_hip = r_hip_angles.std(axis=0) / np.sqrt(r_hip_angles.shape[0])
    
    lhip = pd.DataFrame({
        "%cycle": list(range(101)),
        'mean': mean_l_hip,
        'std': std_l_hip
    })
    
    rhip = pd.DataFrame({
        "%cycle": list(range(101)),
        'mean': mean_r_hip,
        'std': std_r_hip
    })
    
    l_ankle_angles = pd.DataFrame(filtered_df['LAnkleAngles_X'].tolist())
    r_ankle_angles = pd.DataFrame(filtered_df['RAnkleAngles_X'].tolist())
    
    mean_l_ankle = l_ankle_angles.mean(axis=0).values
    std_l_ankle = l_ankle_angles.std(axis=0) / np.sqrt(l_ankle_angles.shape[0])
    mean_r_ankle = r_ankle_angles.mean(axis=0).values
    std_r_ankle = r_ankle_angles.std(axis=0) / np.sqrt(r_ankle_angles.shape[0])
    
    lankle = pd.DataFrame({
        "%cycle": list(range(101)),
        'mean': mean_l_ankle,
        'std': std_l_ankle
    })
    
    rankle = pd.DataFrame({
        "%cycle": list(range(101)),
        'mean': mean_r_ankle,
        'std': std_r_ankle
    })
    
    patient_data = {
        'l_pelvis': patient_kinematics.get('LPelvisAngles_X', []),
        'r_pelvis': patient_kinematics.get('RPelvisAngles_X', []),
        'l_knee': patient_kinematics.get('LKneeAngles_X', []),
        'r_knee': patient_kinematics.get('RKneeAngles_X', []),
        'l_hip': patient_kinematics.get('LHipAngles_X', []),
        'r_hip': patient_kinematics.get('RHipAngles_X', []),
        'l_ankle': patient_kinematics.get('LAnkleAngles_X', []),
        'r_ankle': patient_kinematics.get('RAnkleAngles_X', [])
    }
    
    return {
        'lpelvis': lpelvis, 'rpelvis': rpelvis,
        'lknee': lknee, 'rknee': rknee,
        'lhip': lhip, 'rhip': rhip,
        'lankle': lankle, 'rankle': rankle,
        'patient_data': patient_data
    }

def _create_joint_figure_for_detail(data, title, color, patient_data=None):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=data["%cycle"], 
        y=data["mean"], 
        mode='lines',
        name=f'Rata-rata Subjek Normal',
        line=dict(color=color),
        hoverinfo='text',
        text=[f"Rata-rata Normal: {cycle}%, {val:.2f}°" for cycle, val in zip(data["%cycle"], data["mean"])]
    ))
    
    if patient_data is not None and len(patient_data) > 0:
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=patient_data, 
            mode='lines',
            name='Data Pasien',
            line=dict(color='black', width=3)
        ))
    
    fig.add_trace(go.Scatter(
        x=data["%cycle"], 
        y=data["mean"] + data["std"], 
        mode='lines',
        name='Upper Bound',
        line=dict(color=color, width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=data["%cycle"], 
        y=data["mean"] - data["std"], 
        mode='lines',
        name='Standard Error Area',
        line=dict(color=color, width=0),
        fill='tonexty',
        fillcolor=f'rgba({255 if color=="orange" else 0}, {165 if color=="orange" else 255}, {0 if color=="orange" else 255}, 0.2)',
        showlegend=True,
        hoverinfo='text',
        text=[
            f"Batas Atas: {cycle}%, {valup:.2f}°<br>"
            f"Batas Bawah: {cycle}%, {vallow:.2f}°"
            for cycle, vallow, valup in zip(
                data["%cycle"],
                data["mean"] - data["std"],
                data["mean"] + data["std"]
            )
        ]
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="% Siklus Gait",
        yaxis_title="Sudut (Derajat)",
        template="plotly_white",
        title_x=0.5,
        hovermode="x unified",
        height=400
    )
    return fig

def _show_detail_visualization(kinematic_data, pasien_object_id, tanggal_pemeriksaan, pemeriksaan):
    fig1 = _create_joint_figure_for_detail(kinematic_data['lpelvis'], "Left Pelvis", 'orange', 
                                           kinematic_data['patient_data'].get('l_pelvis'))
    fig2 = _create_joint_figure_for_detail(kinematic_data['rpelvis'], "Right Pelvis", 'darkblue', 
                                           kinematic_data['patient_data'].get('r_pelvis'))
    fig3 = _create_joint_figure_for_detail(kinematic_data['lknee'], "Left Knee", 'orange', 
                                           kinematic_data['patient_data'].get('l_knee'))
    fig4 = _create_joint_figure_for_detail(kinematic_data['rknee'], "Right Knee", 'darkblue', 
                                           kinematic_data['patient_data'].get('r_knee'))
    fig5 = _create_joint_figure_for_detail(kinematic_data['lhip'], "Left Hip", 'orange', 
                                           kinematic_data['patient_data'].get('l_hip'))
    fig6 = _create_joint_figure_for_detail(kinematic_data['rhip'], "Right Hip", 'darkblue', 
                                           kinematic_data['patient_data'].get('r_hip'))
    fig7 = _create_joint_figure_for_detail(kinematic_data['lankle'], "Left Ankle", 'orange', 
                                           kinematic_data['patient_data'].get('l_ankle'))
    fig8 = _create_joint_figure_for_detail(kinematic_data['rankle'], "Right Ankle", 'darkblue', 
                                           kinematic_data['patient_data'].get('r_ankle'))
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["PELVIS", "KNEE", "HIP", "ANKLE", "HASIL RINGKASAN"])
    
    with tab1:
        st.subheader("PELVIS")
        st.write('Pelvis (dalam bahasa Indonesia: panggul) adalah struktur tulang yang berbentuk cekungan di bawah perut, di antara tulang pinggul, dan di atas paha.')
        
        if kinematic_data['patient_data'].get('l_pelvis') and len(kinematic_data['patient_data']['l_pelvis']) > 0:
            maelpelvis = np.mean(np.abs(np.array(kinematic_data['patient_data']['l_pelvis']) - kinematic_data['lpelvis']["mean"]))
            maerpelvis = np.mean(np.abs(np.array(kinematic_data['patient_data']['r_pelvis']) - kinematic_data['rpelvis']["mean"]))
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig1, use_container_width=True)
            if kinematic_data['patient_data'].get('l_pelvis') and len(kinematic_data['patient_data']['l_pelvis']) > 0:
                st.write(f"**Perbedaan rata-rata sudut pelvis kiri (Pasien vs Normal): {maelpelvis:.2f}°**")
        with col2:
            st.plotly_chart(fig2, use_container_width=True)
            if kinematic_data['patient_data'].get('r_pelvis') and len(kinematic_data['patient_data']['r_pelvis']) > 0:
                st.write(f"**Perbedaan rata-rata sudut pelvis kanan (Pasien vs Normal): {maerpelvis:.2f}°**")
            
    with tab2:
        st.subheader("KNEE")
        st.write('Knee (dalam bahasa Indonesia: lutut) adalah bagian tubuh manusia yang terletak di antara paha dan betis, berfungsi sebagai sendi yang menghubungkan tulang femur (paha) dengan tulang tibia (betis).')
        
        if kinematic_data['patient_data'].get('l_knee') and len(kinematic_data['patient_data']['l_knee']) > 0:
            maelknee = np.mean(np.abs(np.array(kinematic_data['patient_data']['l_knee']) - kinematic_data['lknee']["mean"]))
            maerknee = np.mean(np.abs(np.array(kinematic_data['patient_data']['r_knee']) - kinematic_data['rknee']["mean"]))
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig3, use_container_width=True)
            if kinematic_data['patient_data'].get('l_knee') and len(kinematic_data['patient_data']['l_knee']) > 0:
                st.write(f"**Perbedaan rata-rata sudut lutut kiri (Pasien vs Normal): {maelknee:.2f}°**")
        with col2:
            st.plotly_chart(fig4, use_container_width=True)
            if kinematic_data['patient_data'].get('r_knee') and len(kinematic_data['patient_data']['r_knee']) > 0:
                st.write(f"**Perbedaan rata-rata sudut lutut kanan (Pasien vs Normal): {maerknee:.2f}°**")
    
    with tab3:
        st.subheader("HIP")
        st.write('Hip (dalam bahasa Indonesia: pinggul) adalah bagian tubuh yang terletak di bawah perut, menghubungkan tubuh bagian atas dengan kaki.')
        
        if kinematic_data['patient_data'].get('l_hip') and len(kinematic_data['patient_data']['l_hip']) > 0:
            maelhip = np.mean(np.abs(np.array(kinematic_data['patient_data']['l_hip']) - kinematic_data['lhip']["mean"]))
            maerhip = np.mean(np.abs(np.array(kinematic_data['patient_data']['r_hip']) - kinematic_data['rhip']["mean"]))
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig5, use_container_width=True)
            if kinematic_data['patient_data'].get('l_hip') and len(kinematic_data['patient_data']['l_hip']) > 0:
                st.write(f"**Perbedaan rata-rata sudut pinggul kiri (Pasien vs Normal): {maelhip:.2f}°**")
        with col2:
            st.plotly_chart(fig6, use_container_width=True)
            if kinematic_data['patient_data'].get('r_hip') and len(kinematic_data['patient_data']['r_hip']) > 0:
                st.write(f"**Perbedaan rata-rata sudut pinggul kanan (Pasien vs Normal): {maerhip:.2f}°**")
    
    with tab4:
        st.subheader("ANKLE")
        st.write('Ankle (dalam bahasa Indonesia: pergelangan kaki) adalah sendi yang terletak di antara kaki bagian bawah (tulang tibia dan fibula) dan bagian atas kaki (tulang talus).')
        
        if kinematic_data['patient_data'].get('l_ankle') and len(kinematic_data['patient_data']['l_ankle']) > 0:
            maelankle = np.mean(np.abs(np.array(kinematic_data['patient_data']['l_ankle']) - kinematic_data['lankle']["mean"]))
            maerankle = np.mean(np.abs(np.array(kinematic_data['patient_data']['r_ankle']) - kinematic_data['rankle']["mean"]))
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig7, use_container_width=True)
            if kinematic_data['patient_data'].get('l_ankle') and len(kinematic_data['patient_data']['l_ankle']) > 0:
                st.write(f"**Perbedaan rata-rata sudut pergelangan kaki kiri (Pasien vs Normal): {maelankle:.2f}°**")
        with col2:
            st.plotly_chart(fig8, use_container_width=True)
            if kinematic_data['patient_data'].get('r_ankle') and len(kinematic_data['patient_data']['r_ankle']) > 0:
                st.write(f"**Perbedaan rata-rata sudut pergelangan kaki kanan (Pasien vs Normal): {maerankle:.2f}°**")
    
    with tab5:
        from pages_dokter.dokter_visualization import show_mae_phases_table, show_gait_kinematics_table
        from pages_dokter.dokter_visualization import show_mae_overall_summary
        
        show_mae_phases_table()
        show_gait_kinematics_table()
        _show_ai_summaries_for_detail(pasien_object_id, tanggal_pemeriksaan)

def _show_ai_summaries_for_detail(pasien_object_id, tanggal_pemeriksaan):
    from services.ai_summary_service import get_latest_ai_summary
    
    summary = get_latest_ai_summary(pasien_object_id, tanggal_pemeriksaan)
    
    if not summary:
        st.info("Belum ada hasil analisis AI untuk pemeriksaan ini.")
        return
    
    st.markdown("### Hasil Analisis AI")
    
    with st.container(border=True):
        content = summary.get('content', 'Konten tidak tersedia')
        st.markdown(content)
        
        mae_overall = summary.get('mae_overall')
        if mae_overall:
            st.markdown("**Mean Absolute Error (MAE) - Perbedaan rata-rata sudut Pasien vs Normal:**")
            
            mae_data = []
            pelvis_avg = (mae_overall.get('pelvis_left', 0) + mae_overall.get('pelvis_right', 0)) / 2
            mae_data.append({
                'Sendi': 'Pelvis (Panggul)',
                'Kiri (°)': f"{mae_overall.get('pelvis_left', 0):.2f}",
                'Kanan (°)': f"{mae_overall.get('pelvis_right', 0):.2f}",
                'Rata-rata (°)': f"{pelvis_avg:.2f}"
            })
            
            knee_avg = (mae_overall.get('knee_left', 0) + mae_overall.get('knee_right', 0)) / 2
            mae_data.append({
                'Sendi': 'Knee (Lutut)',
                'Kiri (°)': f"{mae_overall.get('knee_left', 0):.2f}",
                'Kanan (°)': f"{mae_overall.get('knee_right', 0):.2f}",
                'Rata-rata (°)': f"{knee_avg:.2f}"
            })
            
            hip_avg = (mae_overall.get('hip_left', 0) + mae_overall.get('hip_right', 0)) / 2
            mae_data.append({
                'Sendi': 'Hip (Pinggul)',
                'Kiri (°)': f"{mae_overall.get('hip_left', 0):.2f}",
                'Kanan (°)': f"{mae_overall.get('hip_right', 0):.2f}",
                'Rata-rata (°)': f"{hip_avg:.2f}"
            })
            
            ankle_avg = (mae_overall.get('ankle_left', 0) + mae_overall.get('ankle_right', 0)) / 2
            mae_data.append({
                'Sendi': 'Ankle (Pergelangan Kaki)',
                'Kiri (°)': f"{mae_overall.get('ankle_left', 0):.2f}",
                'Kanan (°)': f"{mae_overall.get('ankle_right', 0):.2f}",
                'Rata-rata (°)': f"{ankle_avg:.2f}"
            })
            
            df_mae = pd.DataFrame(mae_data)
            st.dataframe(df_mae, use_container_width=True, hide_index=True)

def _calculate_age(birth_date_str):
    if not birth_date_str or birth_date_str == '-':
        return '-'
    try:
        birth_date = datetime.strptime(birth_date_str, "%d-%m-%Y")
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except:
        return '-'
