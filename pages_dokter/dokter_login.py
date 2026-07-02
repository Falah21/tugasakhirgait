import streamlit as st
from css_style import load_css
from services.auth_service import authenticate_user

def login_form(role_label: str = "Dokter"):
    st.markdown(load_css(), unsafe_allow_html=True)
    if st.button("Kembali", key="back_button"):
        st.session_state.role = None
        st.rerun()

    st.markdown("<h2>Sistem Dashboard Gait Analysis</h2>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Selamat Datang di Sistem Dashboard Pemeriksaan Gait</p>", unsafe_allow_html=True)
    st.markdown("---")

    st.subheader(f"Login - {role_label}")
    nomor_identitas = st.text_input("Nomor Identitas", max_chars=18, placeholder="Masukkan NIK/NIP anda")
    password = st.text_input("Password", type="password", placeholder="Masukkan password anda")
    submit = st.button("Login", use_container_width=True)

    st.markdown("<p class='footer'>Dengan masuk, Anda menyetujui kebijakan Privasi & Syarat Layanan sistem GAIT ini.</p>", unsafe_allow_html=True)
    return nomor_identitas, password, submit

class DokterLogin:
    def __init__(self):
        pass

    def _check_dokter_login(self, nomor_identitas, password):
        return authenticate_user(nomor_identitas, password, 'dokter')

    def run(self):
        nomor_identitas, password, submit = login_form("Dokter")
        if submit:
            user_data = self._check_dokter_login(nomor_identitas, password)
            if user_data:
                st.session_state.dokter_logged_in = True
                st.session_state.dokter_user_id = user_data['_id']
                st.session_state.dokter_nama = user_data['nama_lengkap']
                st.session_state.dokter_role = user_data['role']
                st.success(f"Login berhasil! Selamat datang dr. {user_data['nama_lengkap']}")
                st.rerun()
            else:
                st.error("Login gagal! Username atau password salah.")
