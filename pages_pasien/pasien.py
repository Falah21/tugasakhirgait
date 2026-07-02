import streamlit as st
from css_style import load_css
from pages_pasien.pasien_login import PasienLogin
from pages_pasien.pasien_dashboard import show_dashboard
from pages_pasien.profile import show_profile

class PasienPage:
    def __init__(self):
        self.pasien_login = PasienLogin()
        
        if 'pasien_logged_in' not in st.session_state:
            st.session_state.pasien_logged_in = False
        if 'pasien_user_id' not in st.session_state:
            st.session_state.pasien_user_id = None
        if 'pasien_nomor_identitas' not in st.session_state:
            st.session_state.pasien_nomor_identitas = None
        if "pasien_menu" not in st.session_state:
            st.session_state.pasien_menu = "Dashboard"
        if "show_register" not in st.session_state:
            st.session_state.show_register = False

    def run(self):
        st.markdown(load_css(), unsafe_allow_html=True)
        
        if st.session_state.get("show_register", False):
            from register_page import RegisterPage
            RegisterPage().show()
            return
        
        if not st.session_state.get("pasien_logged_in", False):
            self.pasien_login.run()
            return

        self._sidebar()

        if st.session_state.pasien_menu == "Dashboard":
            show_dashboard()
        elif st.session_state.pasien_menu == "Profile":
            show_profile()
        elif st.session_state.pasien_menu == "Logout":
            self._logout()

    def _sidebar(self):
        pasien_nama = st.session_state.get('pasien_nama', 'Pasien')
        st.sidebar.markdown(f"<p class='sidebar-title'>Selamat Datang<br> {pasien_nama}</p>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<p class='sidebar-title'>Menu</p>", unsafe_allow_html=True)
        
        menu_list = ["Dashboard", "Profile", "Logout"]

        for menu in menu_list:
            if st.sidebar.button(menu, use_container_width=True, type="primary"
                                 if st.session_state.pasien_menu == menu
                                 else "secondary"):
                st.session_state.pasien_menu = menu
                st.rerun()

    def _logout(self):
        st.session_state.pasien_logged_in = False
        st.session_state.pasien_user_id = None
        st.session_state.pasien_nomor_identitas = None
        st.session_state.pasien_nama = None
        st.session_state.show_register = False
        st.session_state.role = None
        st.rerun()
