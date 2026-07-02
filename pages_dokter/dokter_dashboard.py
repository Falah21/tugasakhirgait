import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import traceback
from database.mongodb import get_collection
from pages_dokter.dokter_visualization import (
    create_visualizations, 
    show_normal_charts_only,
    show_mae_overall_summary,
    show_mae_phases_table,
    show_gait_kinematics_table,
    show_ai_generation_section,
    get_phase_indices,
    calculate_mae_per_phase,
    create_pelvis_figure,
    create_joint_figure,
    calculate_bounds_from_normal_data
)

def show_dashboard():
    st.markdown("## Dashboard Gait Analysis")

    has_patient_data = ('uploaded_patient_data' in st.session_state and 
                       'norm_kinematics_df' in st.session_state and
                       st.session_state.norm_kinematics_df is not None)

    if has_patient_data:
        try:
            process_dashboard_with_patient()
        except Exception as e:
            st.error(f"Error dalam memproses dashboard: {e}")
    else:
        st.warning("Tidak ada data pasien yang diupload. Silakan upload data pasien di menu 'Input Pemeriksaan Pasien' untuk melihat analisis perbandingan.")
        show_normal_dashboard()

def process_dashboard_with_patient():
    px.defaults.template = 'plotly_dark'
    px.defaults.color_continuous_scale = 'reds'

    collection = get_collection('gait_data')

    cursor = collection.find().limit(100)
    data = list(cursor)
    
    if len(data) == 0:
        st.error("Database Normal Belum Ada. Silahkan Upload Data Normal pada Menu 'Input Baseline Data Gait'")
        return
    
    df = pd.json_normalize(data)
    df.columns = df.columns.str.replace('Trial Information.', '')
    df.columns = df.columns.str.replace('Subject Parameters.', '')
    df.columns = df.columns.str.replace('Body Measurements.', '')
    df.columns = df.columns.str.replace('Norm Kinematics.', '')

    st.markdown("<div class='filter-box'>", unsafe_allow_html=True)
    st.markdown("### Filter Data")
    
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        min_age = df['Age'].min()
        max_age = df['Age'].max()
        age_range = st.slider('Filter by Age Range:', min_value=min_age, max_value=max_age, value=(min_age, max_age))

    with col2:
        bmi_options = ["All BMI Classification"] + list(df["BMI Classification"].value_counts().keys().sort_values())
        classbmi = st.selectbox(label="BMI Classification", options=bmi_options)

    with col3:
        gender_mapping = {"L": "Pria", "P": "Wanita"}
        df["Gender"] = df["Gender"].map(gender_mapping)
        gender_options = ["All Gender"] + list(df["Gender"].value_counts().keys().sort_values())
        gender = st.selectbox(label="Gender", options=gender_options)

    st.markdown("</div>", unsafe_allow_html=True)
        
    filtered_df = df[(df['Age'] >= age_range[0]) & (df['Age'] <= age_range[1])]
    if classbmi != "All BMI Classification":
        filtered_df = filtered_df[filtered_df['BMI Classification'] == classbmi]
    if gender != "All Gender":
        filtered_df = filtered_df[filtered_df["Gender"] == gender]
        
    if filtered_df.empty:
        st.error(f"Tidak terdapat data dengan jenis kelamin {gender} yang terklasifikasi {classbmi}")
        return
        
    st.markdown(f"**Total Records:** {len(filtered_df)}")
    st.session_state.filtered_normal_df = filtered_df

    norm_kinematics_df = st.session_state.norm_kinematics_df
    
    # Proses visualisasi
    create_visualizations(filtered_df, norm_kinematics_df)

def show_normal_dashboard():
    px.defaults.template = 'plotly_dark'
    px.defaults.color_continuous_scale = 'reds'

    try:
        collection = get_collection('gait_data')

        cursor = collection.find().limit(100)
        data = list(cursor)
        
        if len(data) == 0:
            st.error("Database Normal Belum Ada. Silahkan Upload Data Normal pada Menu 'Input Baseline Data Gait'")
            st.info("Untuk melihat dashboard analisis gait, Anda perlu mengupload data subjek normal terlebih dahulu.")
            return
     
        df = pd.json_normalize(data)
        df.columns = df.columns.str.replace('Trial Information.', '')
        df.columns = df.columns.str.replace('Subject Parameters.', '')
        df.columns = df.columns.str.replace('Body Measurements.', '')
        df.columns = df.columns.str.replace('Norm Kinematics.', '')

        st.markdown("<div class='filter-box'>", unsafe_allow_html=True)
        st.markdown("### Filter Data")

        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            min_age = df['Age'].min()
            max_age = df['Age'].max()
            age_range = st.slider('Filter by Age Range:', min_value=min_age, max_value=max_age, value=(min_age, max_age))

        with col2:
            bmi_options = ["All BMI Classification"] + list(df["BMI Classification"].value_counts().keys().sort_values())
            classbmi = st.selectbox(label="BMI Classification", options=bmi_options)

        with col3:
            gender_mapping = {"L": "Pria", "P": "Wanita"}
            df["Gender"] = df["Gender"].map(gender_mapping)
            gender_options = ["All Gender"] + list(df["Gender"].value_counts().keys().sort_values())
            gender = st.selectbox(label="Gender", options=gender_options)

        st.markdown("</div>", unsafe_allow_html=True)

        filtered_df = df[(df['Age'] >= age_range[0]) & (df['Age'] <= age_range[1])]
        if classbmi != "All BMI Classification":
            filtered_df = filtered_df[filtered_df['BMI Classification'] == classbmi]
        if gender != "All Gender":
            filtered_df = filtered_df[filtered_df["Gender"] == gender]
            
        if filtered_df.empty:
            st.error(f"There is no data with gender {gender} classified as {classbmi}.")
            return
        
        show_normal_charts_only(filtered_df)
        
    except Exception as e:
        st.error(f"Error dalam memproses dashboard: {e}")
        traceback.print_exc()
