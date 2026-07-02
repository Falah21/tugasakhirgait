import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from bson import ObjectId
from database.mongodb import get_collection
from services.ai_summary import get_latest_ai_summary

def show_dashboard():
    nomor_identitas = st.session_state.get("pasien_nomor_identitas")
    profil = _get_profil_by_nomor_identitas(nomor_identitas)
    if profil:
        st.session_state.pasien_nama = profil["Nama Lengkap"]

    st.markdown("<h1 style='text-align: center; color: #560000;'>Dashboard Pemeriksaan Gait</h1>", unsafe_allow_html=True)
    
    if st.button("🔄 Refresh Data", key="refresh_dashboard"):
        _refresh_data()

    user_object_id = st.session_state.get("pasien_user_id")
    available_dates = _get_all_pemeriksaan_dates(user_object_id)
    
    if not available_dates:
        st.warning("Silakan lakukan pemeriksaan terlebih dahulu dengan dokter agar dashboard pemeriksaan Gait Anda dapat ditampilkan.")
        return

    selected_date = st.selectbox("Pilih Tanggal Pemeriksaan", options=available_dates, format_func=lambda x: x.strftime("%d %B %Y"))
    
    pemeriksaan = _get_pemeriksaan_data(user_object_id, selected_date)
    if not pemeriksaan:
        st.warning(f"Tidak ada data pemeriksaan untuk tanggal {selected_date.strftime('%d %B %Y')}")
        return
    
    normal_data = _get_normal_data()
    if normal_data is None:
        st.error("Data normal belum tersedia. Silakan hubungi administrator.")
        return

    st.markdown(f"### Hasil Pemeriksaan - {selected_date.strftime('%d %B %Y')}")
    
    kinematic_data = _process_kinematic_data(normal_data, pemeriksaan.get('gait_data', {}).get('Norm Kinematics', {}))
    
    _show_dashboard_visualization(kinematic_data, pasien_id=user_object_id, tanggal_pemeriksaan=selected_date.strftime("%Y-%m-%d"), pemeriksaan=pemeriksaan)

def _get_profil_by_nomor_identitas(nomor_identitas):
    for p in st.session_state.get("pasien_list", []):
        if p.get("Nomor Identitas") == nomor_identitas:
            return p
    return None

def _refresh_data():
    try:
        from pages_pasien.pasien_login import PasienLogin
        PasienLogin()._load_pasien_list()
        st.success("Data berhasil direfresh!")
        st.rerun()
    except Exception as e:
        st.error(f"Error refreshing data: {e}")

def _get_normal_data():
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

def _get_pemeriksaan_data(pasien_object_id, tanggal):
    try:
        collection = get_collection('patient_examinations')
        
        try:
            pasien_id_obj = ObjectId(pasien_object_id)
        except:
            pasien_id_obj = pasien_object_id
        
        pemeriksaan = collection.find_one({
            'pasien_id': pasien_id_obj, 
            'tanggal_pemeriksaan': tanggal.strftime("%Y-%m-%d")
        })
        return pemeriksaan
        
    except Exception as e:
        st.error(f"Error mengambil data pemeriksaan: {e}")
        return None

def _get_all_pemeriksaan_dates(pasien_object_id):
    try:
        collection = get_collection('patient_examinations')

        try:
            pasien_id_obj = ObjectId(pasien_object_id)
        except:
            pasien_id_obj = pasien_object_id

        pemeriksaan_list = collection.find({'pasien_id': pasien_id_obj}, {'tanggal_pemeriksaan': 1})
        
        dates = []
        for exam in pemeriksaan_list:
            tanggal_str = exam.get('tanggal_pemeriksaan')
            if tanggal_str:
                try:
                    dates.append(datetime.strptime(tanggal_str, "%Y-%m-%d").date())
                except:
                    continue
        return sorted(dates, reverse=True) 
    except Exception as e:
        st.error(f"Error mengambil daftar pemeriksaan: {e}")
        return []

def _process_kinematic_data(filtered_df, patient_kinematics=None):
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

    patient_data = {}
    if patient_kinematics:
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

def _create_joint_figure(data, title, color, patient_data=None):
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
            name='Data Anda',
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
        text=[f"Batas Atas: {cycle}%, {valup:.2f}°<br>Batas Bawah: {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(data["%cycle"], data["mean"] - data["std"], data["mean"] + data["std"])]
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

def _show_dashboard_visualization(kinematic_data, pasien_id=None, tanggal_pemeriksaan=None, pemeriksaan=None):
    fig1 = _create_joint_figure(kinematic_data['lpelvis'], "Left Pelvis", 'orange', 
                               kinematic_data['patient_data'].get('l_pelvis'))
    fig2 = _create_joint_figure(kinematic_data['rpelvis'], "Right Pelvis", 'darkblue', 
                               kinematic_data['patient_data'].get('r_pelvis'))
    fig3 = _create_joint_figure(kinematic_data['lknee'], "Left Knee", 'orange', 
                               kinematic_data['patient_data'].get('l_knee'))
    fig4 = _create_joint_figure(kinematic_data['rknee'], "Right Knee", 'darkblue', 
                               kinematic_data['patient_data'].get('r_knee'))
    fig5 = _create_joint_figure(kinematic_data['lhip'], "Left Hip", 'orange', 
                               kinematic_data['patient_data'].get('l_hip'))
    fig6 = _create_joint_figure(kinematic_data['rhip'], "Right Hip", 'darkblue', 
                               kinematic_data['patient_data'].get('r_hip'))
    fig7 = _create_joint_figure(kinematic_data['lankle'], "Left Ankle", 'orange', 
                               kinematic_data['patient_data'].get('l_ankle'))
    fig8 = _create_joint_figure(kinematic_data['rankle'], "Right Ankle", 'darkblue', 
                               kinematic_data['patient_data'].get('r_ankle'))

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["PELVIS", "KNEE", "HIP", "ANKLE", "HASIL PEMERIKSAAN"])

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
                st.write(f"**Perbedaan rata-rata sudut pelvis kiri (Anda vs Normal): {maelpelvis:.2f}°**")
        with col2:
            st.plotly_chart(fig2, use_container_width=True)
            if kinematic_data['patient_data'].get('r_pelvis') and len(kinematic_data['patient_data']['r_pelvis']) > 0:
                st.write(f"**Perbedaan rata-rata sudut pelvis kanan (Anda vs Normal): {maerpelvis:.2f}°**")
            
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
                st.write(f"**Perbedaan rata-rata sudut lutut kiri (Anda vs Normal): {maelknee:.2f}°**")
        with col2:
            st.plotly_chart(fig4, use_container_width=True)
            if kinematic_data['patient_data'].get('r_knee') and len(kinematic_data['patient_data']['r_knee']) > 0:
                st.write(f"**Perbedaan rata-rata sudut lutut kanan (Anda vs Normal): {maerknee:.2f}°**")

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
                st.write(f"**Perbedaan rata-rata sudut pinggul kiri (Anda vs Normal): {maelhip:.2f}°**")
        with col2:
            st.plotly_chart(fig6, use_container_width=True)
            if kinematic_data['patient_data'].get('r_hip') and len(kinematic_data['patient_data']['r_hip']) > 0:
                st.write(f"**Perbedaan rata-rata sudut pinggul kanan (Anda vs Normal): {maerhip:.2f}°**")

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
                st.write(f"**Perbedaan rata-rata sudut pergelangan kaki kiri (Anda vs Normal): {maelankle:.2f}°**")
        with col2:
            st.plotly_chart(fig8, use_container_width=True)
            if kinematic_data['patient_data'].get('r_ankle') and len(kinematic_data['patient_data']['r_ankle']) > 0:
                st.write(f"**Perbedaan rata-rata sudut pergelangan kaki kanan (Anda vs Normal): {maerankle:.2f}°**")

    with tab5:
        _show_ai_summaries_tab(pasien_id, tanggal_pemeriksaan, pemeriksaan)

def _show_ai_summaries_tab(pasien_id, tanggal_pemeriksaan, pemeriksaan):
    summary = get_latest_ai_summary(pasien_id, tanggal_pemeriksaan)

    if not summary:
        st.info("Belum ada hasil pemeriksaan dari dokter untuk tanggal ini. Silakan tunggu atau konsultasikan dengan dokter Anda.")
        return
        
    with st.container(border=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("##### Informasi Pemeriksa")
            st.markdown(f"**Dokter Pemeriksa:** {summary.get('dokter_nama', 'Tidak diketahui')}")
            
            tgl = summary.get('timestamp')
            if tgl:
                if isinstance(tgl, datetime):
                    tgl_str = tgl.strftime("%d %B %Y")
                else:
                    tgl_str = str(tgl)
                st.markdown(f"**Tanggal Analisis:** {tgl_str}")

        with col2:
            st.markdown("##### Informasi Pasien")
            bb = pemeriksaan.get('berat_badan', '-')
            tb = pemeriksaan.get('tinggi_badan', '-')
            bmi = pemeriksaan.get('bmi', '-')
            bmi_class = pemeriksaan.get('bmi_classification', '-')

            if isinstance(bmi, (int, float)):
                bmi = f"{bmi:.2f}"

            st.markdown(f"""
            - **Berat Badan:** {bb} kg  
            - **Tinggi Badan:** {tb} cm  
            - **BMI:** {bmi}  
            - **Klasifikasi BMI:** {bmi_class}
            """)

        st.markdown("---")

        content = summary.get('content', 'Konten tidak tersedia')
        st.markdown(content)
        
        mae_overall = summary.get('mae_overall')
        if mae_overall:
            st.markdown("**Mean Absolute Error (MAE) - Perbedaan rata-rata sudut Anda vs Normal:**")
                
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
