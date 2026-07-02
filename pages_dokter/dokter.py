import streamlit as st
from css_style import load_css
from pages_dokter.dokter_login import DokterLogin
from pages_dokter.dokter_dashboard import show_dashboard
from pages_dokter.input_baseline import input_data_gait_normal
from pages_dokter.input_patient import input_data_gait_pasien
from pages_dokter.dokter_history import show_examination_history

class DokterPage:
    def __init__(self):
        self.dokter_login = DokterLogin()
        
        if 'dokter_logged_in' not in st.session_state:
            st.session_state.dokter_logged_in = False
        if 'dokter_user_id' not in st.session_state:
            st.session_state.dokter_user_id = None
        if 'dokter_nama' not in st.session_state:
            st.session_state.dokter_nama = None
        if "dokter_menu" not in st.session_state:
            st.session_state.dokter_menu = "Dashboard"

    def run(self):
        st.markdown(load_css(), unsafe_allow_html=True)

        if not st.session_state.dokter_logged_in:
            self.dokter_login.run()
            return

        menu = self._sidebar()
        
        if menu == "Dashboard":
            show_dashboard()
        elif menu == "Input Baseline Data Gait":
            input_data_gait_normal()
        elif menu == "Input Pemeriksaan Pasien":
            input_data_gait_pasien()
        elif menu == "Riwayat Pemeriksaan":
            show_examination_history()
        elif menu == "Logout":
            self._logout()

    def _sidebar(self):
        dokter_nama = st.session_state.get('dokter_nama', 'Dokter')
        st.sidebar.markdown(f"<p class='sidebar-title'>Selamat Datang<br> dr. {dokter_nama}</p>", unsafe_allow_html=True)
        st.sidebar.markdown("<p class='sidebar-subtitle'>Menu</p>", unsafe_allow_html=True)
        
        menu_list = ["Dashboard", "Input Baseline Data Gait", "Input Pemeriksaan Pasien", "Riwayat Pemeriksaan", "Logout"]
        
        for menu in menu_list:
            if st.sidebar.button(menu, use_container_width=True, type="primary" 
                                 if st.session_state.dokter_menu == menu else "secondary"):
                st.session_state.dokter_menu = menu
                st.rerun()

        return st.session_state.dokter_menu

    def _logout(self):
        self._reset_patient_data_session_state()
        st.session_state.dokter_logged_in = False
        st.session_state.dokter_user_id = None
        st.session_state.dokter_nama = None
        st.session_state.dokter_role = None
        st.session_state.dokter_menu = "Dashboard"
        st.session_state.role = None
        st.rerun()

    def _reset_patient_data_session_state(self):
        patient_keys = [
            'uploaded_patient_data',
            'norm_kinematics_df',
            'current_pasien_id',
            'current_pasien_nomor_identitas',
            'current_nama_pasien',
            'current_tanggal_pemeriksaan',
            'current_patient_key',
            'filtered_normal_df'
        ]
        
        for key in patient_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        self._reset_ai_summary_session_state_except_current()

    def _reset_ai_summary_session_state_except_current(self):
        keys_to_reset = [
            'ai_summaries_generated',
            'saved_summary_content'
        ]
        
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        
        if 'current_patient_key' in st.session_state:
            current_key = st.session_state.current_patient_key
            for key in list(st.session_state.keys()):
                if ('patient_' in key or 'summaries_' in key) and key != 'current_patient_key':
                    del st.session_state[key]
