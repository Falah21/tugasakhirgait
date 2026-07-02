import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from database.mongodb import get_collection
from models.gait_patient import GaitAnalysisData
from services.ai_summary import gemini_model, generate_ai_summary, save_ai_summary
from bson import ObjectId

def get_gait_phase(percentage):
    if 0 <= percentage <= 2:
        return "Initial Contact"
    elif 2 < percentage <= 10:
        return "Loading Response"
    elif 10 < percentage <= 30:
        return "Mid-Stance"
    elif 30 < percentage <= 50:
        return "Terminal Stance"
    elif 50 < percentage <= 60:
        return "Pre-Swing"
    elif 60 < percentage <= 73:
        return "Initial Swing"
    elif 73 < percentage <= 87:
        return "Mid-Swing"
    elif 87 < percentage <= 100:
        return "Terminal Swing"
    else:
        return "Unknown"

def get_phase_indices(percentage_list):
    phases = {
        'Initial Contact (0-2%)': (0, 2),
        'Loading Response (2-10%)': (2, 10),
        'Mid-Stance (10-30%)': (10, 30),
        'Terminal Stance (30-50%)': (30, 50),
        'Pre-Swing (50-60%)': (50, 60),
        'Initial Swing (60-73%)': (60, 73),
        'Mid-Swing (73-87%)': (73, 87),
        'Terminal Swing (87-100%)': (87, 100)
    }
    
    phase_indices = {}
    for phase, (start, end) in phases.items():
        indices = [i for i, p in enumerate(percentage_list) if start <= p <= end]
        phase_indices[phase] = indices
    return phase_indices

def calculate_mae_per_phase(patient_values, normal_values, phase_indices):
    mae_per_phase = {}
    for phase, indices in phase_indices.items():
        if indices:
            patient_phase = [patient_values[i] for i in indices]
            normal_phase = [normal_values[i] for i in indices]
            mae = np.mean(np.abs(np.array(patient_phase) - np.array(normal_phase)))
            mae_per_phase[phase] = mae
    return mae_per_phase

def calculate_bounds_from_normal_data(filtered_df):
    bounds = {}
    joints = {
        'LPelvisAngles_X': [],
        'RPelvisAngles_X': [],
        'LHipAngles_X': [],
        'RHipAngles_X': [],
        'LKneeAngles_X': [],
        'RKneeAngles_X': [],
        'LAnkleAngles_X': [],
        'RAnkleAngles_X': []
    }
    
    for joint in joints.keys():
        if joint in filtered_df.columns:
            joint_values = pd.DataFrame(filtered_df[joint].tolist())
            mean_values = joint_values.mean(axis=0).values
            std_values = joint_values.std(axis=0).values
            upper_bound = mean_values + (2 * std_values)
            lower_bound = mean_values - (2 * std_values)
            bounds[joint] = {
                'upper': np.mean(upper_bound),
                'lower': np.mean(lower_bound),
                'upper_by_cycle': upper_bound.tolist(),
                'lower_by_cycle': lower_bound.tolist(),
                'mean_by_cycle': mean_values.tolist()
            }
    return bounds

def create_pelvis_figure(data, title, color):
    fig = go.Figure()
    mean_col = "Mean_Lpelvis" if "Mean_Lpelvis" in data.columns else "Mean_Rpelvis"
    std_col = "std_Lpelvis" if "std_Lpelvis" in data.columns else "std_Rpelvis"
    patient_col = "your left pelvis" if "your left pelvis" in data.columns else "your right pelvis"
    
    fig.add_trace(go.Scatter(
        x=data["%cycle"], 
        y=data[mean_col], 
        mode='lines',
        name=f'Average {title}<br>(Normal Subjects)',
        line=dict(color=color),
        hoverinfo='text',
        text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(data["%cycle"], data[mean_col])]
    ))
    if patient_col in data.columns:
        fig.add_trace(go.Scatter(
            x=data["%cycle"], 
            y=data[patient_col], 
            mode='lines',
            name='Patient',
            line=dict(color='black')
        ))
    fig.add_trace(go.Scatter(
        x=data["%cycle"], 
        y=data[mean_col] + data[std_col], 
        mode='lines',
        name='Upper Bound',
        line=dict(color=color, width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=data["%cycle"], 
        y=data[mean_col] - data[std_col], 
        mode='lines',
        name='Standard Error Area',
        line=dict(color=color, width=0),
        fill='tonexty',
        fillcolor=f'rgba({255 if color=="orange" else 0}, {165 if color=="orange" else 255}, {0 if color=="orange" else 255}, 0.2)',
        showlegend=True,
        hoverinfo='text',
        text=[f"Upper Bound: {cycle}%, {valup:.2f}°<br>Lower Bound: {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(data["%cycle"], data[mean_col] - data[std_col], data[mean_col] + data[std_col])]
    ))
    fig.update_layout(
        title=title,
        xaxis_title="%Cycle",
        yaxis_title="Value",
        template="plotly_dark",
        title_x=0.5,
        hovermode="x unified"
    )
    return fig

def create_joint_figure(data, title, color):
    mean_col = [col for col in data.columns if col.startswith('Mean_')][0]
    std_col = [col for col in data.columns if col.startswith('std_')][0]
    patient_col = [col for col in data.columns if col.startswith('your ')][0]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["%cycle"], 
        y=data[mean_col], 
        mode='lines',
        name=f'Average {title}<br>(Normal Subjects)',
        line=dict(color=color),
        hoverinfo='text',
        text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(data["%cycle"], data[mean_col])]
    ))
    fig.add_trace(go.Scatter(
        x=data["%cycle"], 
        y=data[patient_col], 
        mode='lines',
        name='Patient',
        line=dict(color='black')
    ))
    fig.add_trace(go.Scatter(
        x=data["%cycle"], 
        y=data[mean_col] + data[std_col], 
        mode='lines',
        name='Upper Bound',
        line=dict(color=color, width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=data["%cycle"], 
        y=data[mean_col] - data[std_col], 
        mode='lines',
        name='Standard Error Area',
        line=dict(color=color, width=0),
        fill='tonexty',
        fillcolor=f'rgba({255 if color=="orange" else 0}, {165 if color=="orange" else 255}, {0 if color=="orange" else 255}, 0.2)',
        showlegend=False,
        hoverinfo='text',
        text=[f"Upper Bound: {cycle}%, {valup:.2f}°<br>Lower Bound: {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(data["%cycle"], data[mean_col] - data[std_col], data[mean_col] + data[std_col])]
    ))
    fig.update_layout(
        title=title,
        xaxis_title="%Cycle",
        yaxis_title="Value",
        template="plotly_dark",
        title_x=0.5,
        hovermode="x unified"
    )
    return fig

def create_visualizations(filtered_df, norm_kinematics_df):
    percentage_cycle = list(range(101))
    phase_indices = get_phase_indices(percentage_cycle)
    
    # PELVIS
    l_pelvis_angles = pd.DataFrame(filtered_df['LPelvisAngles_X'].tolist())
    r_pelvis_angles = pd.DataFrame(filtered_df['RPelvisAngles_X'].tolist())

    mean_l_pelvis = l_pelvis_angles.mean(axis=0).values
    std_l_pelvis = l_pelvis_angles.std(axis=0) / np.sqrt(l_pelvis_angles.shape[0])
    mean_r_pelvis = r_pelvis_angles.mean(axis=0).values
    std_r_pelvis = r_pelvis_angles.std(axis=0) / np.sqrt(r_pelvis_angles.shape[0])

    lpelvis = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Lpelvis': mean_l_pelvis,
        'std_Lpelvis': std_l_pelvis,
        'your left pelvis': norm_kinematics_df['LPelvisAngles_X'].values})
    
    rpelvis = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Rpelvis': mean_r_pelvis,
        'std_Rpelvis': std_r_pelvis,
        'your right pelvis': norm_kinematics_df['RPelvisAngles_X'].values})

    mae_pelvis_left_phases = calculate_mae_per_phase(
        lpelvis["your left pelvis"].values, 
        lpelvis["Mean_Lpelvis"].values, 
        phase_indices)
    
    mae_pelvis_right_phases = calculate_mae_per_phase(
        rpelvis["your right pelvis"].values, 
        rpelvis["Mean_Rpelvis"].values, 
        phase_indices)

    # KNEE
    l_knee_angles = pd.DataFrame(filtered_df['LKneeAngles_X'].tolist())
    r_knee_angles = pd.DataFrame(filtered_df['RKneeAngles_X'].tolist())
    
    mean_l_knee = l_knee_angles.mean(axis=0).values
    std_l_knee = l_knee_angles.std(axis=0) / np.sqrt(l_knee_angles.shape[0])
    mean_r_knee = r_knee_angles.mean(axis=0).values
    std_r_knee = r_knee_angles.std(axis=0) / np.sqrt(r_knee_angles.shape[0])
    
    lknee = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Lknee': mean_l_knee,
        'std_Lknee': std_l_knee,
        'your left knee': norm_kinematics_df['LKneeAngles_X'].values
    })
    
    rknee = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Rknee': mean_r_knee,
        'std_Rknee': std_r_knee,
        'your right knee': norm_kinematics_df['RKneeAngles_X'].values
    })
    
    mae_knee_left_phases = calculate_mae_per_phase(
        lknee["your left knee"].values, 
        lknee["Mean_Lknee"].values, 
        phase_indices)
    
    mae_knee_right_phases = calculate_mae_per_phase(
        rknee["your right knee"].values, 
        rknee["Mean_Rknee"].values, 
        phase_indices)

    # HIP
    l_hip_angles = pd.DataFrame(filtered_df['LHipAngles_X'].tolist())
    r_hip_angles = pd.DataFrame(filtered_df['RHipAngles_X'].tolist())
    
    mean_l_hip = l_hip_angles.mean(axis=0).values
    std_l_hip = l_hip_angles.std(axis=0) / np.sqrt(l_hip_angles.shape[0])
    mean_r_hip = r_hip_angles.mean(axis=0).values
    std_r_hip = r_hip_angles.std(axis=0) / np.sqrt(r_hip_angles.shape[0])
    
    lhip = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Lhip': mean_l_hip,
        'std_Lhip': std_l_hip,
        'your left hip': norm_kinematics_df['LHipAngles_X'].values
    })
    
    rhip = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Rhip': mean_r_hip,
        'std_Rhip': std_r_hip,
        'your right hip': norm_kinematics_df['RHipAngles_X'].values
    })
    
    mae_hip_left_phases = calculate_mae_per_phase(
        lhip["your left hip"].values, 
        lhip["Mean_Lhip"].values, 
        phase_indices)
    
    mae_hip_right_phases = calculate_mae_per_phase(
        rhip["your right hip"].values, 
        rhip["Mean_Rhip"].values, 
        phase_indices)

    # ANKLE
    l_ankle_angles = pd.DataFrame(filtered_df['LAnkleAngles_X'].tolist())
    r_ankle_angles = pd.DataFrame(filtered_df['RAnkleAngles_X'].tolist())
    
    mean_l_ankle = l_ankle_angles.mean(axis=0).values
    std_l_ankle = l_ankle_angles.std(axis=0) / np.sqrt(l_ankle_angles.shape[0])
    mean_r_ankle = r_ankle_angles.mean(axis=0).values
    std_r_ankle = r_ankle_angles.std(axis=0) / np.sqrt(r_ankle_angles.shape[0])

    lankle = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Lankle': mean_l_ankle,
        'std_Lankle': std_l_ankle,
        'your left ankle': norm_kinematics_df['LAnkleAngles_X'].values
    })
    
    rankle = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Rankle': mean_r_ankle,
        'std_Rankle': std_r_ankle,
        'your right ankle': norm_kinematics_df['RAnkleAngles_X'].values
    })

    mae_ankle_left_phases = calculate_mae_per_phase(
        lankle["your left ankle"].values, 
        lankle["Mean_Lankle"].values, 
        phase_indices)
    
    mae_ankle_right_phases = calculate_mae_per_phase(
        rankle["your right ankle"].values, 
        rankle["Mean_Rankle"].values, 
        phase_indices)

    # MAE KESELURUHAN
    maelpelvis = np.mean(np.abs(lpelvis["your left pelvis"] - lpelvis["Mean_Lpelvis"]))
    maerpelvis = np.mean(np.abs(rpelvis["your right pelvis"] - rpelvis["Mean_Rpelvis"]))
    maelknee = np.mean(np.abs(lknee["your left knee"] - lknee["Mean_Lknee"]))
    maerknee = np.mean(np.abs(rknee["your right knee"] - rknee["Mean_Rknee"]))
    maelhip = np.mean(np.abs(lhip["your left hip"] - lhip["Mean_Lhip"]))
    maerhip = np.mean(np.abs(rhip["your right hip"] - rhip["Mean_Rhip"]))
    maelankle = np.mean(np.abs(lankle["your left ankle"] - lankle["Mean_Lankle"]))
    maerankle = np.mean(np.abs(rankle["your right ankle"] - rankle["Mean_Rankle"]))

    # Simpan ke session state
    st.session_state.mae_pelvis_left = maelpelvis
    st.session_state.mae_pelvis_right = maerpelvis
    st.session_state.mae_knee_left = maelknee
    st.session_state.mae_knee_right = maerknee
    st.session_state.mae_hip_left = maelhip
    st.session_state.mae_hip_right = maerhip
    st.session_state.mae_ankle_left = maelankle
    st.session_state.mae_ankle_right = maerankle
    
    st.session_state.mae_pelvis_left_phases = mae_pelvis_left_phases
    st.session_state.mae_pelvis_right_phases = mae_pelvis_right_phases
    st.session_state.mae_knee_left_phases = mae_knee_left_phases
    st.session_state.mae_knee_right_phases = mae_knee_right_phases
    st.session_state.mae_hip_left_phases = mae_hip_left_phases
    st.session_state.mae_hip_right_phases = mae_hip_right_phases
    st.session_state.mae_ankle_left_phases = mae_ankle_left_phases
    st.session_state.mae_ankle_right_phases = mae_ankle_right_phases
    st.session_state.phase_indices = phase_indices

    # Buat Figure
    fig1 = create_pelvis_figure(lpelvis, "Left Pelvis", 'orange')
    fig2 = create_pelvis_figure(rpelvis, "Right Pelvis", 'dark blue')
    fig3 = create_joint_figure(lknee, "Left Knee", 'orange')
    fig4 = create_joint_figure(rknee, "Right Knee", 'dark blue')
    fig5 = create_joint_figure(lhip, "Left Hip", 'orange')
    fig6 = create_joint_figure(rhip, "Right Hip", 'dark blue')
    fig7 = create_joint_figure(lankle, "Left Ankle", 'orange')
    fig8 = create_joint_figure(rankle, "Right Ankle", 'dark blue')

    # Tampilkan dalam tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["PELVIS", "KNEE", "HIP", "ANKLE", "HASIL RINGKASAN"])

    with tab1:
        tab1.subheader("PELVIS")
        tab1.write('Pelvis (dalam bahasa Indonesia: panggul) adalah struktur tulang yang berbentuk cekungan di bawah perut, di antara tulang pinggul, dan di atas paha.')
        col1, col2 = tab1.columns(2)
        with col1:
            st.plotly_chart(fig1, use_container_width=True)
            st.write(f"**MAE Keseluruhan Left Pelvis: {maelpelvis:.2f}°**") 
        with col2:
            st.plotly_chart(fig2, use_container_width=True)
            st.write(f"**MAE Keseluruhan Right Pelvis: {maerpelvis:.2f}°**") 
            
    with tab2:
        tab2.subheader("KNEE")
        tab2.write('Knee (dalam bahasa Indonesia: lutut) adalah bagian tubuh manusia yang terletak di antara paha dan betis, berfungsi sebagai sendi yang menghubungkan tulang femur (paha) dengan tulang tibia (betis).')
        col1, col2 = tab2.columns(2)
        with col1:
            st.plotly_chart(fig3, use_container_width=True)
            st.write(f"**MAE Keseluruhan Left Knee: {maelknee:.2f}°**")
        with col2:
            st.plotly_chart(fig4, use_container_width=True)
            st.write(f"**MAE Keseluruhan Right Knee: {maerknee:.2f}°**")
            
    with tab3:
        tab3.subheader("HIP")
        tab3.write('Hip (dalam bahasa Indonesia: pinggul) adalah bagian tubuh yang terletak di bawah perut, menghubungkan tubuh bagian atas dengan kaki.')
        col1, col2 = tab3.columns(2)
        with col1:
            st.plotly_chart(fig5, use_container_width=True)
            st.write(f"**MAE Keseluruhan Left Hip: {maelhip:.2f}°**")
        with col2:
            st.plotly_chart(fig6, use_container_width=True)
            st.write(f"**MAE Keseluruhan Right Hip: {maerhip:.2f}°**")
            
    with tab4:
        tab4.subheader("ANKLE")
        tab4.write('Ankle (dalam bahasa Indonesia: pergelangan kaki) adalah sendi yang terletak di antara kaki bagian bawah (tulang tibia dan fibula) dan bagian atas kaki (tulang talus).')
        col1, col2 = tab4.columns(2)
        with col1:
            st.plotly_chart(fig7, use_container_width=True)
            st.write(f"**MAE Keseluruhan Left Ankle: {maelankle:.2f}°**")
        with col2:
            st.plotly_chart(fig8, use_container_width=True)
            st.write(f"**MAE Keseluruhan Right Ankle: {maerankle:.2f}°**")

    with tab5:
        show_mae_overall_summary()
        show_mae_phases_table()
        show_gait_kinematics_table()
        show_ai_generation_section()

def show_normal_charts_only(filtered_df):
    percentage_cycle = list(range(101))
    
    # Pelvis
    l_pelvis_angles = pd.DataFrame(filtered_df['LPelvisAngles_X'].tolist())
    r_pelvis_angles = pd.DataFrame(filtered_df['RPelvisAngles_X'].tolist())

    mean_l_pelvis = l_pelvis_angles.mean(axis=0).values
    std_l_pelvis = l_pelvis_angles.std(axis=0)/np.sqrt(l_pelvis_angles.shape[0])
    mean_r_pelvis = r_pelvis_angles.mean(axis=0).values
    std_r_pelvis = r_pelvis_angles.std(axis=0)/np.sqrt(r_pelvis_angles.shape[0])

    lpelvis = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Lpelvis': mean_l_pelvis,
        'std_Lpelvis': std_l_pelvis
    })

    rpelvis = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Rpelvis': mean_r_pelvis,
        'std_Rpelvis': std_r_pelvis
    })
    
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=lpelvis["%cycle"], 
        y=lpelvis["Mean_Lpelvis"], 
        mode='lines',
        name='Average Left Pelvis<br>(Normal Subjects)',
        line=dict(color='orange'),
        hoverinfo='text',
        text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(lpelvis["%cycle"], lpelvis["Mean_Lpelvis"])]
    ))
    fig1.add_trace(go.Scatter(
        x=lpelvis["%cycle"], 
        y=lpelvis["Mean_Lpelvis"] + lpelvis["std_Lpelvis"], 
        mode='lines',
        name='Upper Bound (Left)',
        line=dict(color='orange', width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig1.add_trace(go.Scatter(
        x=lpelvis["%cycle"], 
        y=lpelvis["Mean_Lpelvis"] - lpelvis["std_Lpelvis"], 
        mode='lines',
        name='Standard Error Area',
        line=dict(color='orange', width=0),
        fill='tonexty',
        fillcolor='rgba(255, 165, 0, 0.2)',
        showlegend=True,
        hoverinfo='text',
        text=[f"Upper Bound (Left): {cycle}%, {valup:.2f}°<br>Lower Bound (Left): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(lpelvis["%cycle"], lpelvis["Mean_Lpelvis"] - lpelvis["std_Lpelvis"], lpelvis["Mean_Lpelvis"] + lpelvis["std_Lpelvis"])]
    ))
    fig1.update_layout(
        title="Left Pelvis",
        xaxis_title="%Cycle",
        yaxis_title="Value",
        template="plotly_dark",
        title_x=0.5,
        hovermode="x unified"
    )
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=rpelvis["%cycle"], 
        y=rpelvis["Mean_Rpelvis"], 
        mode='lines',
        name='Average Right Pelvis<br>(Normal Subjects)',
        line=dict(color='dark blue'),
        hoverinfo='text',
        text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(rpelvis["%cycle"], rpelvis["Mean_Rpelvis"])]
    ))
    fig2.add_trace(go.Scatter(
        x=rpelvis["%cycle"], 
        y=rpelvis["Mean_Rpelvis"] + rpelvis["std_Rpelvis"], 
        mode='lines',
        name='Upper Bound (Right)',
        line=dict(color='dark blue', width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig2.add_trace(go.Scatter(
        x=rpelvis["%cycle"], 
        y=rpelvis["Mean_Rpelvis"] - rpelvis["std_Rpelvis"], 
        mode='lines',
        name='Standard Error Area',
        line=dict(color='dark blue', width=0),
        fill='tonexty',
        fillcolor='rgba(0, 255, 255, 0.2)',
        showlegend=True,
        hoverinfo='text',
        text=[f"Upper Bound (Right): {cycle}%, {valup:.2f}°<br>Lower Bound (Right): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(rpelvis["%cycle"], rpelvis["Mean_Rpelvis"] - rpelvis["std_Rpelvis"], rpelvis["Mean_Rpelvis"] + rpelvis["std_Rpelvis"])]
    ))
    fig2.update_layout(
        title="Right Pelvis",
        xaxis_title="%Cycle",
        yaxis_title="Value",
        template="plotly_dark",
        title_x=0.5,
        hovermode="x unified"
    )

    # KNEE
    l_knee_angles = pd.DataFrame(filtered_df['LKneeAngles_X'].tolist())
    r_knee_angles = pd.DataFrame(filtered_df['RKneeAngles_X'].tolist())

    mean_l_knee = l_knee_angles.mean(axis=0).values
    std_l_knee = l_knee_angles.std(axis=0) / np.sqrt(l_knee_angles.shape[0])
    mean_r_knee = r_knee_angles.mean(axis=0).values
    std_r_knee = r_knee_angles.std(axis=0) / np.sqrt(r_knee_angles.shape[0])

    lknee = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Lknee': mean_l_knee,
        'std_Lknee': std_l_knee
    })
    
    rknee = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Rknee': mean_r_knee,
        'std_Rknee': std_r_knee
    })

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=lknee["%cycle"], 
        y=lknee["Mean_Lknee"], 
        mode='lines',
        name='Average Left Knee<br>(Normal Subjects)',
        line=dict(color='orange'),
        hoverinfo='text',
        text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(lknee["%cycle"], lknee["Mean_Lknee"])]
    ))
    fig3.add_trace(go.Scatter(
        x=lknee["%cycle"], 
        y=lknee["Mean_Lknee"] + lknee["std_Lknee"], 
        mode='lines',
        name='Upper Bound (Left)',
        line=dict(color='orange', width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig3.add_trace(go.Scatter(
        x=lknee["%cycle"], 
        y=lknee["Mean_Lknee"] - lknee["std_Lknee"], 
        mode='lines',
        name='Standard Error Area',
        line=dict(color='orange', width=0),
        fill='tonexty',
        fillcolor='rgba(255, 165, 0, 0.2)',
        showlegend=False,
        hoverinfo='text',
        text=[f"Upper Bound (Left): {cycle}%, {valup:.2f}°<br>Lower Bound (Left): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(lknee["%cycle"], lknee["Mean_Lknee"] - lknee["std_Lknee"], lknee["Mean_Lknee"] + lknee["std_Lknee"])]
    ))
    fig3.update_layout(
        title="Left Knee",
        xaxis_title="%Cycle",
        yaxis_title="Value",
        template="plotly_dark",
        title_x=0.5,
        hovermode="x unified"
    )
    
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=rknee["%cycle"], 
        y=rknee["Mean_Rknee"], 
        mode='lines',
        name='Average Right Knee<br>(Normal Subjects)',
        line=dict(color='dark blue'),
        hoverinfo='text',
        text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(rknee["%cycle"], rknee["Mean_Rknee"])]
    ))
    fig4.add_trace(go.Scatter(
        x=rknee["%cycle"], 
        y=rknee["Mean_Rknee"] + rknee["std_Rknee"], 
        mode='lines',
        name='Upper Bound (Right)',
        line=dict(color='dark blue', width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig4.add_trace(go.Scatter(
        x=rknee["%cycle"], 
        y=rknee["Mean_Rknee"] - rknee["std_Rknee"], 
        mode='lines',
        name='Standard Error Area',
        line=dict(color='dark blue', width=0),
        fill='tonexty',
        fillcolor='rgba(0, 255, 255, 0.2)',
        showlegend=False,
        hoverinfo='text',
        text=[f"Upper Bound (Right): {cycle}%, {valup:.2f}°<br>Lower Bound (Right): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(rknee["%cycle"], rknee["Mean_Rknee"] - rknee["std_Rknee"], rknee["Mean_Rknee"] + rknee["std_Rknee"])]
    ))
    fig4.update_layout(
        title="Right Knee",
        xaxis_title="%Cycle",
        yaxis_title="Value",
        template="plotly_dark",
        title_x=0.5,
        hovermode="x unified"
    )

    # HIP
    l_hip_angles = pd.DataFrame(filtered_df['LHipAngles_X'].tolist())
    r_hip_angles = pd.DataFrame(filtered_df['RHipAngles_X'].tolist())

    mean_l_hip = l_hip_angles.mean(axis=0).values
    std_l_hip = l_hip_angles.std(axis=0) / np.sqrt(l_hip_angles.shape[0])
    mean_r_hip = r_hip_angles.mean(axis=0).values
    std_r_hip = r_hip_angles.std(axis=0) / np.sqrt(r_hip_angles.shape[0])

    lhip = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Lhip': mean_l_hip,
        'std_Lhip': std_l_hip
    })
    
    rhip = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Rhip': mean_r_hip,
        'std_Rhip': std_r_hip
    })

    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(
        x=lhip["%cycle"], 
        y=lhip["Mean_Lhip"], 
        mode='lines',
        name='Average Left Hip<br>(Normal Subjects)',
        line=dict(color='orange'),
        hoverinfo='text',
        text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(lhip["%cycle"], lhip["Mean_Lhip"])]
    ))
    fig5.add_trace(go.Scatter(
        x=lhip["%cycle"], 
        y=lhip["Mean_Lhip"] + lhip["std_Lhip"], 
        mode='lines',
        name='Upper Bound (Left)',
        line=dict(color='orange', width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig5.add_trace(go.Scatter(
        x=lhip["%cycle"], 
        y=lhip["Mean_Lhip"] - lhip["std_Lhip"], 
        mode='lines',
        name='Standard Error Area',
        line=dict(color='orange', width=0),
        fill='tonexty',
        fillcolor='rgba(255, 165, 0, 0.2)',
        showlegend=False,
        hoverinfo='text',
        text=[f"Upper Bound (Left): {cycle}%, {valup:.2f}°<br>Lower Bound (Left): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(lhip["%cycle"], lhip["Mean_Lhip"] - lhip["std_Lhip"], lhip["Mean_Lhip"] + lhip["std_Lhip"])]
    ))
    fig5.update_layout(
        title="Left Hip",
        xaxis_title="%Cycle",
        yaxis_title="Value",
        template="plotly_dark",
        title_x=0.5,
        hovermode="x unified"
    )
    
    fig6 = go.Figure()
    fig6.add_trace(go.Scatter(
        x=rhip["%cycle"], 
        y=rhip["Mean_Rhip"], 
        mode='lines',
        name='Average Right Hip<br>(Normal Subjects)',
        line=dict(color='dark blue'),
        hoverinfo='text',
        text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(rhip["%cycle"], rhip["Mean_Rhip"])]
    ))
    fig6.add_trace(go.Scatter(
        x=rhip["%cycle"], 
        y=rhip["Mean_Rhip"] + rhip["std_Rhip"], 
        mode='lines',
        name='Upper Bound (Right)',
        line=dict(color='dark blue', width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig6.add_trace(go.Scatter(
        x=rhip["%cycle"], 
        y=rhip["Mean_Rhip"] - rhip["std_Rhip"], 
        mode='lines',
        name='Standard Error Area',
        line=dict(color='dark blue', width=0),
        fill='tonexty',
        fillcolor='rgba(0, 255, 255, 0.2)',
        showlegend=False,
        hoverinfo='text',
        text=[f"Upper Bound (Right): {cycle}%, {valup:.2f}°<br>Lower Bound (Right): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(rhip["%cycle"], rhip["Mean_Rhip"] - rhip["std_Rhip"], rhip["Mean_Rhip"] + rhip["std_Rhip"])]
    ))
    fig6.update_layout(
        title="Right Hip",
        xaxis_title="%Cycle",
        yaxis_title="Value",
        template="plotly_dark",
        title_x=0.5,
        hovermode="x unified"
    )

    # ANKLE
    l_ankle_angles = pd.DataFrame(filtered_df['LAnkleAngles_X'].tolist())
    r_ankle_angles = pd.DataFrame(filtered_df['RAnkleAngles_X'].tolist())

    mean_l_ankle = l_ankle_angles.mean(axis=0).values
    std_l_ankle = l_ankle_angles.std(axis=0) / np.sqrt(l_ankle_angles.shape[0])
    mean_r_ankle = r_ankle_angles.mean(axis=0).values
    std_r_ankle = r_ankle_angles.std(axis=0) / np.sqrt(r_ankle_angles.shape[0])

    lankle = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Lankle': mean_l_ankle,
        'std_Lankle': std_l_ankle
    })

    rankle = pd.DataFrame({
        "%cycle": percentage_cycle,
        'Mean_Rankle': mean_r_ankle,
        'std_Rankle': std_r_ankle
    })
    
    fig7 = go.Figure()
    fig7.add_trace(go.Scatter(
        x=lankle["%cycle"], 
        y=lankle["Mean_Lankle"], 
        mode='lines',
        name='Average Left Ankle<br>(Normal Subjects)',
        line=dict(color='orange'),
        hoverinfo='text',
        text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(lankle["%cycle"], lankle["Mean_Lankle"])]
    ))
    fig7.add_trace(go.Scatter(
        x=lankle["%cycle"], 
        y=lankle["Mean_Lankle"] + lankle["std_Lankle"], 
        mode='lines',
        name='Upper Bound (Left)',
        line=dict(color='orange', width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig7.add_trace(go.Scatter(
        x=lankle["%cycle"], 
        y=lankle["Mean_Lankle"] - lankle["std_Lankle"], 
        mode='lines',
        name='Standard Error Area',
        line=dict(color='orange', width=0),
        fill='tonexty',
        fillcolor='rgba(255, 165, 0, 0.2)',
        showlegend=False,
        hoverinfo='text',
        text=[f"Upper Bound (Left): {cycle}%, {valup:.2f}°<br>Lower Bound (Left): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(lankle["%cycle"], lankle["Mean_Lankle"] - lankle["std_Lankle"], lankle["Mean_Lankle"] + lankle["std_Lankle"])]
    ))
    fig7.update_layout(
        title="Left Ankle",
        xaxis_title="%Cycle",
        yaxis_title="Value",
        template="plotly_dark",
        title_x=0.5,
        hovermode="x unified"
    )

    fig8 = go.Figure()
    fig8.add_trace(go.Scatter(
        x=rankle["%cycle"], 
        y=rankle["Mean_Rankle"], 
        mode='lines',
        name='Average Right Ankle<br>(Normal Subjects)',
        line=dict(color='dark blue'),
        hoverinfo='text',
        text=[f"Average Normal Subjects: {cycle}%, {val:.2f}°" for cycle, val in zip(rankle["%cycle"], rankle["Mean_Rankle"])]
    ))
    fig8.add_trace(go.Scatter(
        x=rankle["%cycle"], 
        y=rankle["Mean_Rankle"] + rankle["std_Rankle"], 
        mode='lines',
        name='Upper Bound (Right)',
        line=dict(color='dark blue', width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig8.add_trace(go.Scatter(
        x=rankle["%cycle"], 
        y=rankle["Mean_Rankle"] - rankle["std_Rankle"], 
        mode='lines',
        name='Standard Error Area',
        line=dict(color='dark blue', width=0),
        fill='tonexty',
        fillcolor='rgba(0, 255, 255, 0.2)',
        showlegend=False,
        hoverinfo='text',
        text=[f"Upper Bound (Right): {cycle}%, {valup:.2f}°<br>Lower Bound (Right): {cycle}%, {vallow:.2f}°" for cycle, vallow, valup in zip(rankle["%cycle"], rankle["Mean_Rankle"] - rankle["std_Rankle"], rankle["Mean_Rankle"] + rankle["std_Rankle"])]
    ))
    fig8.update_layout(
        title="Right Ankle",
        xaxis_title="%Cycle",
        yaxis_title="Value",
        template="plotly_dark",
        title_x=0.5,
        hovermode="x unified"
    )

    # Tampilkan tabs
    tab1, tab2, tab3, tab4 = st.tabs(["PELVIS", "KNEE","HIP","ANKLE"])

    with tab1:
        tab1.subheader("PELVIS")
        tab1.write(
            'Pelvis (dalam bahasa Indonesia: panggul) adalah struktur tulang yang berbentuk cekungan di bawah perut, '
            'di antara tulang pinggul, dan di atas paha.')
        col1, col2 = tab1.columns(2)
        with col1:
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.plotly_chart(fig2, use_container_width=True)
            
    with tab2:
        tab2.subheader("KNEE")
        tab2.write(
            'Knee (dalam bahasa Indonesia: lutut) adalah bagian tubuh manusia yang terletak di antara paha dan betis, '
            'berfungsi sebagai sendi yang menghubungkan tulang femur (paha) dengan tulang tibia (betis).')
        col1, col2 = tab2.columns(2)
        with col1:
            st.plotly_chart(fig3, use_container_width=True)
        with col2:
            st.plotly_chart(fig4, use_container_width=True)

    with tab3:
        tab3.subheader("HIP")
        tab3.write(
            'Hip (dalam bahasa Indonesia: pinggul) adalah bagian tubuh yang terletak di bawah perut, menghubungkan tubuh bagian atas dengan kaki.')
        col1, col2 = tab3.columns(2)
        with col1:
            st.plotly_chart(fig5, use_container_width=True)
        with col2:
            st.plotly_chart(fig6, use_container_width=True)

    with tab4:
        tab4.subheader("ANKLE")
        tab4.write(
            'Ankle (dalam bahasa Indonesia: pergelangan kaki) adalah sendi yang terletak di antara kaki bagian bawah (tulang tibia dan fibula) dan bagian atas kaki (tulang talus).')
        col1, col2 = tab4.columns(2)
        with col1:
            st.plotly_chart(fig7, use_container_width=True)
        with col2:
            st.plotly_chart(fig8, use_container_width=True)

def show_mae_overall_summary():
    st.markdown("### Ringkasan MAE Keseluruhan")
    
    required_mae_keys = [
        'mae_pelvis_left', 'mae_pelvis_right',
        'mae_knee_left', 'mae_knee_right',
        'mae_hip_left', 'mae_hip_right',
        'mae_ankle_left', 'mae_ankle_right'
    ]
    
    missing_keys = [key for key in required_mae_keys if key not in st.session_state]
    if missing_keys:
        st.info("Data MAE keseluruhan belum tersedia. Silakan upload data pasien terlebih dahulu.")
        return
    
    mae_overall_data = []
    
    pelvis_avg = (st.session_state.mae_pelvis_left + st.session_state.mae_pelvis_right) / 2
    mae_overall_data.append({
        'Sendi': 'Pelvis (Panggul)',
        'Kiri (°)': f"{st.session_state.mae_pelvis_left:.2f}",
        'Kanan (°)': f"{st.session_state.mae_pelvis_right:.2f}",
        'Rata-rata (°)': f"{pelvis_avg:.2f}"
    })
    
    knee_avg = (st.session_state.mae_knee_left + st.session_state.mae_knee_right) / 2
    mae_overall_data.append({
        'Sendi': 'Knee (Lutut)',
        'Kiri (°)': f"{st.session_state.mae_knee_left:.2f}",
        'Kanan (°)': f"{st.session_state.mae_knee_right:.2f}",
        'Rata-rata (°)': f"{knee_avg:.2f}"
    })
    
    hip_avg = (st.session_state.mae_hip_left + st.session_state.mae_hip_right) / 2
    mae_overall_data.append({
        'Sendi': 'Hip (Pinggul)',
        'Kiri (°)': f"{st.session_state.mae_hip_left:.2f}",
        'Kanan (°)': f"{st.session_state.mae_hip_right:.2f}",
        'Rata-rata (°)': f"{hip_avg:.2f}"
    })
    
    ankle_avg = (st.session_state.mae_ankle_left + st.session_state.mae_ankle_right) / 2
    mae_overall_data.append({
        'Sendi': 'Ankle (Pergelangan Kaki)',
        'Kiri (°)': f"{st.session_state.mae_ankle_left:.2f}",
        'Kanan (°)': f"{st.session_state.mae_ankle_right:.2f}",
        'Rata-rata (°)': f"{ankle_avg:.2f}"
    })
    
    df_mae_overall = pd.DataFrame(mae_overall_data)
    st.dataframe(df_mae_overall, use_container_width=True, hide_index=True)

def show_mae_phases_table():
    if not all(key in st.session_state for key in [
        'mae_pelvis_left_phases', 'mae_pelvis_right_phases',
        'mae_knee_left_phases', 'mae_knee_right_phases',
        'mae_hip_left_phases', 'mae_hip_right_phases',
        'mae_ankle_left_phases', 'mae_ankle_right_phases'
    ]):
        st.info("Data MAE per fase belum tersedia.")
        return
    
    phases_order = [
        'Initial Contact (0-2%)',
        'Loading Response (2-10%)',
        'Mid-Stance (10-30%)',
        'Terminal Stance (30-50%)',
        'Pre-Swing (50-60%)',
        'Initial Swing (60-73%)',
        'Mid-Swing (73-87%)',
        'Terminal Swing (87-100%)'
    ]
    
    st.markdown("### Detail MAE per Fase Gait")
    
    mae_phases_data = []
    
    for phase in phases_order:
        row_data = {
            'Fase Gait': phase,
            'Pelvis Kiri (°)': f"{st.session_state.mae_pelvis_left_phases.get(phase, 0):.2f}",
            'Pelvis Kanan (°)': f"{st.session_state.mae_pelvis_right_phases.get(phase, 0):.2f}",
            'Knee Kiri (°)': f"{st.session_state.mae_knee_left_phases.get(phase, 0):.2f}",
            'Knee Kanan (°)': f"{st.session_state.mae_knee_right_phases.get(phase, 0):.2f}",
            'Hip Kiri (°)': f"{st.session_state.mae_hip_left_phases.get(phase, 0):.2f}",
            'Hip Kanan (°)': f"{st.session_state.mae_hip_right_phases.get(phase, 0):.2f}",
            'Ankle Kiri (°)': f"{st.session_state.mae_ankle_left_phases.get(phase, 0):.2f}",
            'Ankle Kanan (°)': f"{st.session_state.mae_ankle_right_phases.get(phase, 0):.2f}"
        }
        mae_phases_data.append(row_data)
    
    mae_phases_df = pd.DataFrame(mae_phases_data)
    st.dataframe(mae_phases_df, use_container_width=True, hide_index=True)

def show_gait_kinematics_table():
    if not all(key in st.session_state for key in [
        'mae_pelvis_left_phases', 'mae_pelvis_right_phases',
        'mae_knee_left_phases', 'mae_knee_right_phases',
        'mae_hip_left_phases', 'mae_hip_right_phases',
        'mae_ankle_left_phases', 'mae_ankle_right_phases',
        'norm_kinematics_df', 'filtered_normal_df'
    ]):
        st.info("Data kinematika gait belum tersedia. Silakan upload data pasien terlebih dahulu.")
        return
    
    st.markdown("### Hasil Kinematika Gait")
    
    phases = [
        "Initial Contact (0-2%)",
        "Loading Response (2-10%)",
        "Mid Stance (10-30%)",
        "Terminal Stance (30-50%)",
        "Pre-Swing (50-60%)",
        "Initial Swing (60-73%)",
        "Mid Swing (73-87%)",
        "Terminal Swing (87-100%)"
    ]
    
    patient_df = st.session_state.norm_kinematics_df
    filtered_df = st.session_state.filtered_normal_df
    
    normal_means = {}
    
    l_pelvis_angles = pd.DataFrame(filtered_df['LPelvisAngles_X'].tolist())
    r_pelvis_angles = pd.DataFrame(filtered_df['RPelvisAngles_X'].tolist())
    normal_means['l_pelvis'] = l_pelvis_angles.mean(axis=0).values
    normal_means['r_pelvis'] = r_pelvis_angles.mean(axis=0).values
    
    l_knee_angles = pd.DataFrame(filtered_df['LKneeAngles_X'].tolist())
    r_knee_angles = pd.DataFrame(filtered_df['RKneeAngles_X'].tolist())
    normal_means['l_knee'] = l_knee_angles.mean(axis=0).values
    normal_means['r_knee'] = r_knee_angles.mean(axis=0).values
    
    l_hip_angles = pd.DataFrame(filtered_df['LHipAngles_X'].tolist())
    r_hip_angles = pd.DataFrame(filtered_df['RHipAngles_X'].tolist())
    normal_means['l_hip'] = l_hip_angles.mean(axis=0).values
    normal_means['r_hip'] = r_hip_angles.mean(axis=0).values
    
    l_ankle_angles = pd.DataFrame(filtered_df['LAnkleAngles_X'].tolist())
    r_ankle_angles = pd.DataFrame(filtered_df['RAnkleAngles_X'].tolist())
    normal_means['l_ankle'] = l_ankle_angles.mean(axis=0).values
    normal_means['r_ankle'] = r_ankle_angles.mean(axis=0).values
    
    def get_phase_average(values, phase_start, phase_end):
        percentages = list(range(101))
        indices = [i for i, p in enumerate(percentages) if phase_start <= p <= phase_end]
        if indices and len(values) > max(indices):
            phase_values = [values[i] for i in indices]
            return np.mean(phase_values)
        return 0
    
    phase_ranges = {
        "Initial Contact (0-2%)": (0, 2),
        "Loading Response (2-10%)": (2, 10),
        "Mid Stance (10-30%)": (10, 30),
        "Terminal Stance (30-50%)": (30, 50),
        "Pre-Swing (50-60%)": (50, 60),
        "Initial Swing (60-73%)": (60, 73),
        "Mid Swing (73-87%)": (73, 87),
        "Terminal Swing (87-100%)": (87, 100)
    }
    
    joints = [
        ("Pelvis", "LPelvisAngles_X", "RPelvisAngles_X", "l_pelvis", "r_pelvis"),
        ("Knee", "LKneeAngles_X", "RKneeAngles_X", "l_knee", "r_knee"),
        ("Hip", "LHipAngles_X", "RHipAngles_X", "l_hip", "r_hip"),
        ("Ankle", "LAnkleAngles_X", "RAnkleAngles_X", "l_ankle", "r_ankle")
    ]
    
    st.markdown("#### Kaki Kanan")
    
    right_table_data = []
    for phase in phases:
        start_pct, end_pct = phase_ranges[phase]
        first_row = True
        for joint_name, left_col, right_col, normal_left_key, normal_right_key in joints:
            patient_values = patient_df[right_col].values
            patient_avg = get_phase_average(patient_values, start_pct, end_pct)
            
            normal_values = normal_means[normal_right_key]
            normal_avg = get_phase_average(normal_values, start_pct, end_pct)
            
            mae_key = f"mae_{joint_name.lower()}_right_phases"
            mae_value = st.session_state.get(mae_key, {}).get(phase, 0)
            
            if mae_value == 0 and len(patient_values) > 0 and len(normal_values) > 0:
                indices = [i for i, p in enumerate(range(101)) if start_pct <= p <= end_pct]
                if indices:
                    patient_phase = [patient_values[i] for i in indices if i < len(patient_values)]
                    normal_phase = [normal_values[i] for i in indices if i < len(normal_values)]
                    if patient_phase and normal_phase:
                        mae_value = np.mean(np.abs(np.array(patient_phase) - np.array(normal_phase)))
            
            right_table_data.append({
                "Fase Gait": phase if first_row else "",
                "Sendi": joint_name,
                "Rata-Rata Nilai Pasien": f"{patient_avg:.1f}°",
                "Nilai Rujukan (Baseline)": f"{normal_avg:.1f}°",
                "Deviasi (MAE)": f"{mae_value:.2f}°"
            })
            
            first_row = False
    
    df_right = pd.DataFrame(right_table_data)
    st.dataframe(df_right, use_container_width=True, hide_index=True)
    
    st.markdown("#### Kaki Kiri")
    
    left_table_data = []
    for phase in phases:
        start_pct, end_pct = phase_ranges[phase]
        first_row = True
        for joint_name, left_col, right_col, normal_left_key, normal_right_key in joints:
            patient_values = patient_df[left_col].values
            patient_avg = get_phase_average(patient_values, start_pct, end_pct)
            
            normal_values = normal_means[normal_left_key]
            normal_avg = get_phase_average(normal_values, start_pct, end_pct)
            
            mae_key = f"mae_{joint_name.lower()}_left_phases"
            mae_value = st.session_state.get(mae_key, {}).get(phase, 0)
            
            if mae_value == 0 and len(patient_values) > 0 and len(normal_values) > 0:
                indices = [i for i, p in enumerate(range(101)) if start_pct <= p <= end_pct]
                if indices:
                    patient_phase = [patient_values[i] for i in indices if i < len(patient_values)]
                    normal_phase = [normal_values[i] for i in indices if i < len(normal_values)]
                    if patient_phase and normal_phase:
                        mae_value = np.mean(np.abs(np.array(patient_phase) - np.array(normal_phase)))
            
            left_table_data.append({
                "Fase Gait": phase if first_row else "",
                "Sendi": joint_name,
                "Rata-Rata Nilai Pasien": f"{patient_avg:.1f}°",
                "Nilai Rujukan (Baseline)": f"{normal_avg:.1f}°",
                "Deviasi (MAE)": f"{mae_value:.2f}°"
            })
            first_row = False
    
    df_left = pd.DataFrame(left_table_data)
    st.dataframe(df_left, use_container_width=True, hide_index=True)

def show_ai_generation_section():
    required_keys = [
        'mae_pelvis_left', 'mae_pelvis_right',
        'mae_knee_left', 'mae_knee_right',
        'mae_hip_left', 'mae_hip_right',
        'mae_ankle_left', 'mae_ankle_right',
        'mae_pelvis_left_phases', 'mae_pelvis_right_phases',
        'mae_knee_left_phases', 'mae_knee_right_phases',
        'mae_hip_left_phases', 'mae_hip_right_phases',
        'mae_ankle_left_phases', 'mae_ankle_right_phases',
        'phase_indices'
    ]
    
    missing_keys = [key for key in required_keys if key not in st.session_state]
    if missing_keys:
        st.warning("Data MAE belum tersedia. Silakan upload data pasien terlebih dahulu.")
        return

    if 'current_patient_key' not in st.session_state:
        st.warning("Belum ada data pasien. Silakan upload data pasien terlebih dahulu.")
        return

    current_patient_key = st.session_state.current_patient_key
    
    if 'filtered_normal_df' not in st.session_state:
        st.info("Silakan upload data normal terlebih dahulu.")
        return
    
    filtered_df = st.session_state.filtered_normal_df
    if filtered_df.empty:
        st.warning("Data normal kosong. Silakan cek filter yang Anda gunakan.")
        return
    
    bounds_data = calculate_bounds_from_normal_data(filtered_df)

    patient_saved_key = f'saved_summary_content_{current_patient_key}'
    patient_ai_generated_key = f'ai_summaries_generated_{current_patient_key}'
    
    phases_order = [
        'Initial Contact (0-2%)',
        'Loading Response (2-10%)',
        'Mid-Stance (10-30%)',
        'Terminal Stance (30-50%)',
        'Pre-Swing (50-60%)',
        'Initial Swing (60-73%)',
        'Mid-Swing (73-87%)',
        'Terminal Swing (87-100%)'
    ]
    
    if patient_saved_key in st.session_state and st.session_state[patient_saved_key]:
        st.markdown("#### Hasil Ringkasan AI")
        st.info(st.session_state[patient_saved_key])
        st.markdown("---")
        return
    
    if patient_ai_generated_key not in st.session_state:
        st.markdown("### Generate Ringkasan AI")
        st.info("Klik tombol di bawah untuk menghasilkan ringkasan AI berdasarkan data MAE dan batas normal (Upper/Lower Bound) yang telah dihitung.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            generate_button = st.button("Generate Ringkasan AI", use_container_width=True, type="primary")
        
        if not generate_button:
            st.stop()
        
        if generate_button:
            model = gemini_model
            if model is None:
                st.error("Fitur AI tidak tersedia karena API key Gemini tidak dikonfigurasi.")
                return

            all_mae_values = [
                st.session_state.mae_pelvis_left,
                st.session_state.mae_pelvis_right,
                st.session_state.mae_knee_left,
                st.session_state.mae_knee_right,
                st.session_state.mae_hip_left,
                st.session_state.mae_hip_right,
                st.session_state.mae_ankle_left,
                st.session_state.mae_ankle_right
            ]
            
            overall_mae = np.mean(all_mae_values)

            mae_summary = f"""
            MAE KESELURUHAN (Rata-rata seluruh siklus gait 0-100%):
            - Pelvis Kiri: {st.session_state.mae_pelvis_left:.2f}°, Pelvis Kanan: {st.session_state.mae_pelvis_right:.2f}°, Rata-rata: {(st.session_state.mae_pelvis_left + st.session_state.mae_pelvis_right)/2:.2f}°
            - Knee Kiri: {st.session_state.mae_knee_left:.2f}°, Knee Kanan: {st.session_state.mae_knee_right:.2f}°, Rata-rata: {(st.session_state.mae_knee_left + st.session_state.mae_knee_right)/2:.2f}°
            - Hip Kiri: {st.session_state.mae_hip_left:.2f}°, Hip Kanan: {st.session_state.mae_hip_right:.2f}°, Rata-rata: {(st.session_state.mae_hip_left + st.session_state.mae_hip_right)/2:.2f}°
            - Ankle Kiri: {st.session_state.mae_ankle_left:.2f}°, Ankle Kanan: {st.session_state.mae_ankle_right:.2f}°, Rata-rata: {(st.session_state.mae_ankle_left + st.session_state.mae_ankle_right)/2:.2f}°
            Rata-rata Keseluruhan Semua Sendi: {overall_mae:.2f}°
            """
            
            mae_phases_summary = "\nMAE PER FASE GAIT:\n"
            
            for phase in phases_order:
                mae_phases_summary += f"\n{phase}:\n"
                mae_phases_summary += f"  - Pelvis Kiri: {st.session_state.mae_pelvis_left_phases.get(phase, 0):.2f}°, Pelvis Kanan: {st.session_state.mae_pelvis_right_phases.get(phase, 0):.2f}°\n"
                mae_phases_summary += f"  - Knee Kiri: {st.session_state.mae_knee_left_phases.get(phase, 0):.2f}°, Knee Kanan: {st.session_state.mae_knee_right_phases.get(phase, 0):.2f}°\n"
                mae_phases_summary += f"  - Hip Kiri: {st.session_state.mae_hip_left_phases.get(phase, 0):.2f}°, Hip Kanan: {st.session_state.mae_hip_right_phases.get(phase, 0):.2f}°\n"
                mae_phases_summary += f"  - Ankle Kiri: {st.session_state.mae_ankle_left_phases.get(phase, 0):.2f}°, Ankle Kanan: {st.session_state.mae_ankle_right_phases.get(phase, 0):.2f}°\n"
            
            bounds_summary = "\nBATAS NORMAL (Upper Bound dan Lower Bound):\n"
            joints_for_bounds = [
                ('LPelvisAngles_X', 'Pelvis Kiri'),
                ('RPelvisAngles_X', 'Pelvis Kanan'),
                ('LKneeAngles_X', 'Knee Kiri'),
                ('RKneeAngles_X', 'Knee Kanan'),
                ('LHipAngles_X', 'Hip Kiri'),
                ('RHipAngles_X', 'Hip Kanan'),
                ('LAnkleAngles_X', 'Ankle Kiri'),
                ('RAnkleAngles_X', 'Ankle Kanan')
            ]
            
            for key, name in joints_for_bounds:
                bound = bounds_data.get(key, {'upper': 0, 'lower': 0})
                bounds_summary += f"- {name}: Upper={bound['upper']:.2f}°, Lower={bound['lower']:.2f}°\n"
            
            full_data = mae_summary + mae_phases_summary + bounds_summary

            final_prompt = f"""
            Anda adalah fisioterapis klinis dan analis biomekanika gait.
            
            DATA:
            {full_data}
            
            TUGAS:
            Lakukan interpretasi gait analysis secara klinis dan terstruktur berdasarkan data yang diberikan.
            
            ATURAN WAJIB:
            - Maksimal 300 kata
            - Fokus pada temuan paling signifikan
            - Hindari terlalu banyak angka (cukup gunakan: rendah, sedang, tinggi)
            - Gunakan istilah klinis yang profesional dan mudah dipahami
            - Gunakan hanya data yang diberikan
            - Jangan menetapkan diagnosis medis pasti
            - Gunakan bahasa interpretatif dan observasional, bukan diagnosis medis.
            - Gunakan istilah seperti "mengindikasikan", "berpotensi menunjukkan", atau "konsisten dengan"
            - Gunakan data upper bound dan lower bound untuk menentukan apakah parameter berada di luar rentang normal
            - Sebutkan secara singkat jika terdapat parameter yang berada di luar rentang normal
            - Prioritaskan temuan dengan MAE tinggi dan berada di luar rentang normal
            - Gunakan format **bold** untuk menyorot sendi bermasalah, fase gait kritis, dan tingkat deviasi
            - Jangan menggunakan bold secara berlebihan
            
            STRUKTUR:
            1. Highlight Temuan Utama:
            - Sebutkan 3–4 temuan paling signifikan
            
            2. Tabel Ringkasan Deviasi
            | Sendi | Sisi | Fase Paling Bermasalah | Tingkat Deviasi | Hasil |
            |-------|------|------------------------|-----------------|-------|
            Isi maksimal 5 baris.
            
            3. Interpretasi Klinis
            Buat dalam bentuk bullet point per sendi.
            - Gunakan istilah observasional seperti:
              - lebih
              - kurang
              - cenderung meningkat
              - cenderung menurun
            - Hindari diagnosis medis atau kesimpulan pasti
            - Fokus pada pola gerak dan fungsi gait
            - Jelaskan apakah gerakan tampak lebih atau kurang dibanding pola normal
            - Sertakan jika parameter berada di luar rentang normal
            
            4. Kesimpulan
            Buat dalam bentuk bullet point singkat.
            - Jelaskan indikasi fungsional berdasarkan pola gait
            - Hindari diagnosis medis
            - Fokus pada kemungkinan gangguan biomekanik atau kompensasi gerak.
            """
            
            try:
                with st.spinner("Mohon tunggu... Sistem sedang membuat Ringkasan AI"):
                    response = model.generate_content(final_prompt)
                    summary_content = response.text
                        
            except Exception as e:
                st.error(f"Error generating AI summaries: {e}")
                summary_content = "Ringkasan tidak tersedia. Silakan periksa koneksi API Gemini atau coba lagi nanti."

            st.session_state[f'ai_summary_content_{current_patient_key}'] = summary_content
            st.session_state[patient_ai_generated_key] = True
            
            st.success(f"Ringkasan AI berhasil digenerate!")
            st.rerun()
    
    else:
        summary_content = st.session_state.get(f'ai_summary_content_{current_patient_key}', "")
        if not summary_content:
            st.warning("Tidak ada ringkasan yang dihasilkan.")
            return

        st.markdown("### Hasil Ringkasan AI")
        st.markdown(summary_content)
        st.markdown("---")

        st.markdown("### Simpan Hasil")
      
        if st.button("Simpan Hasil Ringkasan", use_container_width=True, type="primary", key="save_ai_summary"):
            mae_data_for_save = []
              
            for phase in phases_order:
                mae_data_for_save.append({
                    'phase': phase,
                    'pelvis_left': st.session_state.mae_pelvis_left_phases.get(phase, 0),
                    'pelvis_right': st.session_state.mae_pelvis_right_phases.get(phase, 0),
                    'knee_left': st.session_state.mae_knee_left_phases.get(phase, 0),
                    'knee_right': st.session_state.mae_knee_right_phases.get(phase, 0),
                    'hip_left': st.session_state.mae_hip_left_phases.get(phase, 0),
                    'hip_right': st.session_state.mae_hip_right_phases.get(phase, 0),
                    'ankle_left': st.session_state.mae_ankle_left_phases.get(phase, 0),
                    'ankle_right': st.session_state.mae_ankle_right_phases.get(phase, 0)
                })
                
            success = _save_single_summary(
                content=summary_content,
                mae_overall={
                    'pelvis_left': st.session_state.mae_pelvis_left,
                    'pelvis_right': st.session_state.mae_pelvis_right,
                    'knee_left': st.session_state.mae_knee_left,
                    'knee_right': st.session_state.mae_knee_right,
                    'hip_left': st.session_state.mae_hip_left,
                    'hip_right': st.session_state.mae_hip_right,
                    'ankle_left': st.session_state.mae_ankle_left,
                    'ankle_right': st.session_state.mae_ankle_right
                },
                mae_phases=mae_data_for_save,
                bounds_data=bounds_data
            )
              
            if success:
                st.session_state[patient_saved_key] = summary_content
                st.success("Ringkasan AI berhasil disimpan!")
                st.rerun()
            else:
                st.error("Gagal menyimpan ke database")

def _save_single_summary(content, mae_overall, mae_phases, bounds_data):
    try:
        collection = get_collection('ai_summaries')
        examination_collection = get_collection('patient_examinations')

        pasien_object_id = st.session_state.get('current_pasien_id', None)
        pasien_nomor_identitas = st.session_state.get('current_pasien_nomor_identitas', None)
        nama_pasien = st.session_state.get('current_nama_pasien', None)
        tanggal_pemeriksaan = st.session_state.get('current_tanggal_pemeriksaan', None)

        if not pasien_object_id:
            st.warning("Data pasien tidak ditemukan di session state. Pastikan data pasien sudah diupload.")
            return False

        examination = examination_collection.find_one({
            'pasien_id': ObjectId(pasien_object_id),
            'tanggal_pemeriksaan': tanggal_pemeriksaan
        })
        
        if not examination:
            st.warning(f"Pemeriksaan untuk pasien {nama_pasien} pada tanggal {tanggal_pemeriksaan} tidak ditemukan.")
            return False
        
        summary_data = {
            'timestamp': datetime.now(),
            'dokter_id': ObjectId(st.session_state.get('dokter_user_id')),
            'dokter_nama': st.session_state.get('dokter_nama'),
            'pasien_id': ObjectId(pasien_object_id),
            'pasien_nomor_identitas': pasien_nomor_identitas,
            'nama_pasien': nama_pasien,
            'tanggal_pemeriksaan': tanggal_pemeriksaan,
            'examination_id': examination['_id'],
            'content': content,
            'mae_overall': mae_overall,
            'mae_phases': mae_phases,
            'bounds_data': bounds_data,
        }
        
        result = collection.insert_one(summary_data)
        return True
        
    except Exception as e:
        st.error(f"Error menyimpan ringkasan: {e}")
        return False
