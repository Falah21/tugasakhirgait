import streamlit as st

def show_profile():
    nomor_identitas = st.session_state.get("pasien_nomor_identitas")
    profil = _get_profil_by_nomor_identitas(nomor_identitas)
    
    st.markdown("<h1 style='text-align: center; color: #560000;'>Profil Pasien</h1>", unsafe_allow_html=True)
    
    if profil:
        st.subheader("Data Profil")
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown(f"**NIK:** {profil['Nomor Identitas']}")
                st.markdown(f"**Nama Lengkap:** {profil['Nama Lengkap']}")
                st.markdown(f"**Tanggal Lahir:** {profil['Tanggal Lahir']}")
        with col2:
            with st.container(border=True):
                st.markdown(f"**Jenis Kelamin:** {profil['Jenis Kelamin']}")
                st.markdown(f"**Role:** {profil['Role']}")
                st.markdown(f"**Tanggal Pendaftaran:** {profil['Tanggal Dibuat']}")
    else:
        st.warning("Data profil tidak ditemukan")

def _get_profil_by_nomor_identitas(nomor_identitas):
    for p in st.session_state.get("pasien_list", []):
        if p.get("Nomor Identitas") == nomor_identitas:
            return p
    return None
