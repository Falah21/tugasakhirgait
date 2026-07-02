import streamlit as st
from css_style import load_css
from pages_admin.login import AdminLogin
from pages_admin.dashboard import show_dashboard
from pages_admin.user_management import manage_users
from pages_admin.baseline_data import manage_normal_data
from pages_admin.examination_history import show_examination_history

class AdminPage:
    def __init__(self):
        self.admin_login = AdminLogin()
        
        if 'admin_logged_in' not in st.session_state:
            st.session_state.admin_logged_in = False
        if 'admin_user_data' not in st.session_state:
            st.session_state.admin_user_data = None
        if "menu_admin" not in st.session_state:
            st.session_state.menu_admin = "Beranda"

    def run(self):
        st.markdown(load_css(), unsafe_allow_html=True)

        if not st.session_state.admin_logged_in:
            self.admin_login.run()
            return

        menu = self._sidebar()
        
        if menu == "Beranda":
            show_dashboard()
        elif menu == "Manajemen Pengguna":
            manage_users()
        elif menu == "Baseline Data Gait":
            manage_normal_data()
        elif menu == "Riwayat Pemeriksaan Pasien":
            show_examination_history()
        elif menu == "Logout":
            self._logout()

    def _sidebar(self):
        admin_data = st.session_state.get('admin_user_data', {})
        admin_name = admin_data.get('nama_lengkap', 'Admin')

        st.sidebar.markdown(f"<p class='sidebar-title'>Selamat Datang<br> {admin_name}</p>", unsafe_allow_html=True)
        st.sidebar.markdown("<p class='sidebar-subtitle'>Menu</p>", unsafe_allow_html=True)
    
        menu_list = ["Beranda", "Manajemen Pengguna", "Baseline Data Gait", "Riwayat Pemeriksaan Pasien", "Logout"]
    
        for menu in menu_list:
            if st.sidebar.button(menu, use_container_width=True, type="primary" 
                                 if st.session_state.menu_admin == menu 
                                 else "secondary"):
                st.session_state.menu_admin = menu
                st.rerun()
                                     
        return st.session_state.menu_admin

    def _logout(self):
        st.session_state.admin_logged_in = False
        st.session_state.pasien_list_initialized = False 
        if 'admin_user_data' in st.session_state:
            del st.session_state.admin_user_data
        st.rerun()
