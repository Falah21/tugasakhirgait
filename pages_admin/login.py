import streamlit as st
from css_style import load_css
from services.auth_service import authenticate_user

def login_form(role_label: str = "Admin"):
    st.markdown(load_css(), unsafe_allow_html=True)

    if st.button("Kembali", key="back_button"):
        st.session_state.role = None
        st.rerun()

    st.markdown("<h2>Sistem Dashboard Gait Analysis</h2>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Selamat Datang di Sistem Dashboard Pemeriksaan Gait</p>", unsafe_allow_html=True)
    st.markdown("---")

    st.subheader(f"Login - {role_label}")
    username = st.text_input("NIP", max_chars=18, placeholder="Masukkan NIP anda")
    password = st.text_input("Password", type="password", placeholder="Masukkan password anda")
    
    submit = st.button("Login", use_container_width=True)

    st.markdown("<p class='footer'>Dengan masuk, Anda menyetujui kebijakan Privasi & Syarat Layanan sistem GAIT ini.</p>", unsafe_allow_html=True)
    return username, password, submit

class AdminLogin:
    def __init__(self):
        self.admin_user = st.secrets["ADMIN_USERNAME"]
        self.admin_pass = st.secrets["ADMIN_PASSWORD"]

    def _authenticate_admin(self, username, password):
        """Autentikasi admin dari database atau fallback ke super admin"""
        # Coba autentikasi dari database
        user_data = authenticate_user(username, password, 'admin')
        if user_data:
            return user_data
        
        # Fallback ke super admin dari secrets
        if username == self.admin_user and password == self.admin_pass:
            return {
                '_id': 'super_admin',
                'nomor_identitas': self.admin_user, 
                'nama_lengkap': 'Super Admin', 
                'role': 'admin'
            }
        
        return None

    def run(self):
        username, password, submit = login_form("Admin")
        
        if submit:
            admin_data = self._authenticate_admin(username, password)
            if admin_data:
                st.session_state.admin_logged_in = True
                st.session_state.admin_user_data = admin_data
                st.rerun()
            else:
                st.error("Username atau password salah!")
