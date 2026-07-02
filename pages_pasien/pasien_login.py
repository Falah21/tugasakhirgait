import streamlit as st
from css_style import load_css
from services.auth_service import authenticate_user

def login_form_pasien(role_label: str = "Pasien"):
    st.markdown(load_css(), unsafe_allow_html=True)

    if st.button("Kembali", key="back_button"):
        st.session_state.role = None
        st.rerun()

    st.markdown("<h2>Sistem Dashboard Gait Analysis</h2>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Selamat Datang di Sistem Dashboard Pemeriksaan Gait</p>", unsafe_allow_html=True)
    st.subheader(f"Login - {role_label}")
    nomor_identitas = st.text_input("NIK", max_chars=16, placeholder="Masukkan NIK anda")
    password = st.text_input("Password", type="password", placeholder="Masukkan password anda")
    submit = st.button("Login", use_container_width=True)
    st.markdown("<p class='register-link'>Belum punya akun?</p>", unsafe_allow_html=True)
    if st.button("Register", use_container_width=True):
        st.session_state.show_register = True
        st.rerun()

    return nomor_identitas, password, submit

class PasienLogin:
    def __init__(self):
        pass

    def _authenticate_pasien(self, nomor_identitas, password):
        return authenticate_user(nomor_identitas, password, 'pasien')

    def run(self):
        nomor_identitas, password, submit = login_form_pasien()
        if submit:
            auth_result = self._authenticate_pasien(nomor_identitas, password)
           
            if auth_result:
                st.session_state.pasien_logged_in = True
                st.session_state.pasien_user_id = auth_result['_id']
                st.session_state.pasien_nomor_identitas = auth_result['nomor_identitas']
                st.session_state.pasien_nama = auth_result['nama_lengkap']
                st.session_state.pasien_menu = "Dashboard"

                self._load_pasien_list() 
                st.success("Login berhasil!")
                st.rerun()
            else:
                st.error("NIK atau password salah!")

    def _load_pasien_list(self):
        try:
            from database.mongodb import get_collection
            collection = get_collection('users')
            pasien_data = list(collection.find({'role': 'pasien'}))
            st.session_state["pasien_list"] = []
            for pasien in pasien_data:
                st.session_state["pasien_list"].append({
                    "_id": str(pasien.get('_id')),
                    "Nomor Identitas": pasien.get('nomor_identitas'),
                    "Nama Lengkap": pasien.get('nama_lengkap'),
                    "Tanggal Lahir": pasien.get('tanggal_lahir'),
                    "Jenis Kelamin": pasien.get('jenis_kelamin'),
                    "Role": pasien.get('role'),
                    "Tanggal Dibuat": pasien.get('tanggal_dibuat')
                })
        except Exception as e:
            st.error(f"Error loading patient data: {e}")
