import streamlit as st
import pandas as pd
from datetime import datetime
from bson import ObjectId
from database.mongodb import get_collection
from services.auth_service import hash_password, get_user_by_id, check_user_examinations

def manage_users():
    _load_pasien_data()
    st.markdown("### Manajemen Pengguna")

    tabs = st.tabs(["Semua Pengguna", "Tambah Pengguna Baru", "Kelola Pengguna"])
    
    all_users = _get_all_users()
    pasien_data = [user for user in all_users if user.get('Role') == 'pasien']
    dokter_data = [user for user in all_users if user.get('Role') == 'dokter']
    admin_data = [user for user in all_users if user.get('Role') == 'admin']
    
    # Tab 1: Semua Pengguna
    with tabs[0]:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Pengguna", len(all_users))
        with col2:
            st.metric("Pasien", len(pasien_data))
        with col3:
            st.metric("Dokter", len(dokter_data))
        with col4:
            st.metric("Admin", len(admin_data))
        
        filter_role = st.selectbox("Filter berdasarkan Role:", ["Semua", "Pasien", "Dokter", "Admin"], key="filter_role")
        if filter_role == "Semua":
            filtered_data = all_users
        elif filter_role == "Pasien":
            filtered_data = pasien_data
        elif filter_role == "Dokter":
            filtered_data = dokter_data
        else:
            filtered_data = admin_data
        
        if filtered_data:
            df_users = pd.DataFrame(filtered_data)
            df_users.insert(0, 'No', range(1, len(df_users) + 1))
            
            # Tentukan kolom yang akan ditampilkan berdasarkan role
            if filter_role == "Dokter" or filter_role == "Semua":
                display_columns = ['No', 'Nomor Identitas', 'Nama Lengkap', 'Role', 'Jenis Kelamin', 'Tanggal Lahir', 
                                 'Institusi', 'Spesialisasi', 'Tanggal Dibuat']
            elif filter_role == "Admin":
                display_columns = ['No', 'Nomor Identitas', 'Nama Lengkap', 'Role', 'Jenis Kelamin', 'Tanggal Lahir', 
                                 'Institusi', 'Tanggal Dibuat']
            else:
                display_columns = ['No', 'Nomor Identitas', 'Nama Lengkap', 'Role', 'Jenis Kelamin', 'Tanggal Lahir', 'Tanggal Dibuat']
            
            # Filter kolom yang ada di dataframe
            available_columns = [col for col in display_columns if col in df_users.columns]
            df_display = df_users[available_columns]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada data pengguna terdaftar")

    # Tab 2: Tambah User Baru
    with tabs[1]:
        with st.form("tambah_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                role = st.selectbox("Jenis User", ["pasien", "dokter", "admin"])
                nomor_identitas = st.text_input("Nomor Identitas", placeholder="Masukkan NIK untuk pasien, NIP untuk dokter/admin")
                nama_lengkap = st.text_input("Nama Lengkap", placeholder="Masukkan nama lengkap")
                
            with col2:
                tanggal_lahir = st.date_input("Tanggal Lahir", min_value=datetime(1900, 1, 1), max_value=datetime.now(), value=None)
                jenis_kelamin = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
                password = st.text_input("Password", type="password", placeholder="Masukkan password")
            
            # Field dinamis berdasarkan role
            if role == "dokter":
                st.markdown("---")
                st.markdown("#### Informasi Dokter")
                col3, col4 = st.columns(2)
                with col3:
                    institusi = st.text_input("Institusi / Rumah Sakit", placeholder="Masukkan nama institusi")
                with col4:
                    spesialisasi = st.text_input("Spesialisasi Profesi", placeholder="Masukkan spesialisasi (contoh: Spesialis Jantung)")
            elif role == "admin":
                st.markdown("---")
                st.markdown("#### Informasi Admin")
                institusi = st.text_input("Institusi", placeholder="Masukkan nama institusi")
                spesialisasi = None
            else:  # pasien
                institusi = None
                spesialisasi = None
            
            submitted = st.form_submit_button("Tambah Pengguna Baru")
            
            if submitted:
                if nomor_identitas and nama_lengkap and password:
                    errors = []
                    
                    # Validasi role spesifik
                    if role in ["dokter", "admin"]:
                        if not nomor_identitas.isdigit():
                            errors.append(f"NIP untuk {role} harus berupa angka (tidak boleh huruf).")
                        if len(nomor_identitas) != 18:
                            errors.append(f"NIP untuk {role} harus terdiri dari 18 digit.")
                    else:
                        if not nomor_identitas.isdigit():
                            errors.append("NIK harus berupa angka (tidak boleh huruf).")
                        if len(nomor_identitas) != 16:
                            errors.append("NIK harus terdiri dari 16 digit.")
                            
                    if any(char.isdigit() for char in nama_lengkap):
                        errors.append("Nama lengkap harus berupa huruf dan tidak boleh mengandung angka.")
                    if not tanggal_lahir:
                        errors.append("Tanggal lahir wajib diisi.")
                    
                    # Validasi field tambahan
                    if role in ["dokter", "admin"] and not institusi:
                        errors.append(f"Institusi wajib diisi untuk {role}.")
                    if role == "dokter" and not spesialisasi:
                        errors.append("Spesialisasi wajib diisi untuk dokter.")
                    
                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        user_data = {
                            'nomor_identitas': nomor_identitas,
                            'nama_lengkap': nama_lengkap,
                            'password': password,
                            'role': role,
                            'tanggal_lahir': tanggal_lahir.strftime("%d-%m-%Y"),
                            'jenis_kelamin': jenis_kelamin,
                            'tanggal_dibuat': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # Tambahkan field tambahan
                        if role in ["dokter", "admin"]:
                            user_data['institusi'] = institusi
                        if role == "dokter":
                            user_data['spesialisasi'] = spesialisasi
                        
                        if _add_new_user(user_data):
                            st.success(f"{nama_lengkap} berhasil ditambahkan sebagai {role}!")
                            st.rerun()
                else:
                    st.error("Harap isi semua kolom")

    # Tab 3: Kelola Pengguna (Edit & Delete)
    with tabs[2]:
        if not all_users:
            st.warning("Tidak ada data pengguna yang tersedia.")
            return
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Edit Data Pengguna")

            edit_options = []
            for user in all_users:
                display_text = f"{user.get('Nama Lengkap', 'N/A')} ({user.get('Nomor Identitas', 'N/A')}) - {user.get('Role', 'N/A')}"
                edit_options.append((user.get('_id', ''), display_text))
            
            if edit_options:
                options_with_default = [("", "Pilih Pengguna untuk Diedit")] + edit_options
                
                selected_option = st.selectbox(
                    "Silahkan pilih pengguna yang ingin diedit!!",
                    options=[opt[0] for opt in options_with_default],
                    format_func=lambda x: next((display for id, display in options_with_default if id == x), 'Pilih Pengguna untuk Diedit'))

                if selected_option and selected_option != "":
                    selected_user = next((user for user in all_users if user.get('_id') == selected_option), None)
                    if selected_user:
                        with st.form("edit_user_form"):
                            st.markdown(f"Mengedit: {selected_user.get('Nama Lengkap')}")
                            
                            col_form1, col_form2 = st.columns(2)
                            
                            with col_form1:
                                new_nomor_identitas = st.text_input("Nomor Identitas", value=selected_user.get('Nomor Identitas', ''))
                                new_nama = st.text_input("Nama Lengkap", value=selected_user.get('Nama Lengkap', ''))
                                new_role = st.selectbox("Role", ["pasien", "dokter", "admin"], 
                                                       index=["pasien", "dokter", "admin"].index(selected_user.get('Role', 'pasien'))
                                                       if selected_user.get('Role') in ["pasien", "dokter", "admin"] else 0)
                                            
                            with col_form2:
                                tgl_lahir_str = selected_user.get('Tanggal Lahir', '01-01-1990')
                                try:
                                    default_tgl = datetime.strptime(tgl_lahir_str, "%d-%m-%Y")
                                except:
                                    default_tgl = datetime(1990, 1, 1)
                                
                                new_tanggal_lahir = st.date_input("Tanggal Lahir", value=default_tgl)
                                new_jenis_kelamin = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"], 
                                                                index=0 if selected_user.get('Jenis Kelamin') == "Laki-laki" else 1)
                                new_password = st.text_input("Password Baru (kosongkan jika tidak diubah)", type="password")
                            
                            # Field tambahan untuk edit
                            st.markdown("---")
                            st.markdown("#### Informasi Tambahan")
                            
                            # Tampilkan field berdasarkan role
                            if new_role in ["dokter", "admin"]:
                                current_institusi = selected_user.get('Institusi', '')
                                new_institusi = st.text_input("Institusi", value=current_institusi)
                            else:
                                new_institusi = None
                                
                            if new_role == "dokter":
                                current_spesialisasi = selected_user.get('Spesialisasi', '')
                                new_spesialisasi = st.text_input("Spesialisasi Profesi", value=current_spesialisasi)
                            else:
                                new_spesialisasi = None
                            
                            if st.form_submit_button("Update Pengguna"):
                                errors = []
                                if new_role in ["dokter", "admin"]:
                                    if not new_nomor_identitas.isdigit():
                                        errors.append(f"NIP untuk {new_role} harus berupa angka (tidak boleh huruf).")
                                    if len(new_nomor_identitas) != 18:
                                        errors.append(f"NIP untuk {new_role} harus terdiri dari 18 digit.")
                                else:
                                    if not new_nomor_identitas.isdigit():
                                        errors.append("NIK harus berupa angka (tidak boleh huruf).")
                                    if len(new_nomor_identitas) != 16:
                                        errors.append("NIK harus terdiri dari 16 digit.")
                                if any(char.isdigit() for char in new_nama):
                                    errors.append("Nama lengkap harus berupa huruf dan tidak boleh mengandung angka.")
                                if not new_tanggal_lahir:
                                    errors.append("Tanggal lahir wajib diisi.")
                                if new_role in ["dokter", "admin"] and not new_institusi:
                                    errors.append(f"Institusi wajib diisi untuk {new_role}.")
                                if new_role == "dokter" and not new_spesialisasi:
                                    errors.append("Spesialisasi wajib diisi untuk dokter.")
                                
                                if errors:
                                    for err in errors:
                                        st.error(err)
                                else:
                                    update_data = {
                                        'nomor_identitas': new_nomor_identitas,
                                        'nama_lengkap': new_nama,
                                        'role': new_role,
                                        'tanggal_lahir': new_tanggal_lahir.strftime("%d-%m-%Y"),
                                        'jenis_kelamin': new_jenis_kelamin
                                    }
                                    
                                    # Tambahkan field tambahan
                                    if new_role in ["dokter", "admin"]:
                                        update_data['institusi'] = new_institusi
                                    if new_role == "dokter":
                                        update_data['spesialisasi'] = new_spesialisasi
                                    
                                    # Hapus field yang tidak relevan jika role berubah
                                    if new_role != "dokter":
                                        update_data['spesialisasi'] = None
                                    if new_role not in ["dokter", "admin"]:
                                        update_data['institusi'] = None

                                    if new_password:
                                        update_data['password'] = new_password
                                    
                                    if _update_user(selected_user['_id'], update_data):
                                        st.success(f"Data {new_nama} berhasil diupdate!")
                                        st.rerun()
            else:
                st.info("Tidak ada data pengguna yang dapat diedit")
        
        with col2:
            st.markdown("#### Hapus Data Pengguna")

            delete_options = []
            for user in all_users:
                display_text = f"{user.get('Nama Lengkap', 'N/A')} ({user.get('Nomor Identitas', 'N/A')}) - {user.get('Role', 'N/A')}"
                delete_options.append((user.get('_id', ''), display_text))
            
            if delete_options:
                delete_options_with_default = [("", "Pilih Pengguna untuk Dihapus")] + delete_options
                
                selected_delete_option = st.selectbox(
                    "Silahkan pilih pengguna yang ingin dihapus!!",
                    options=[opt[0] for opt in delete_options_with_default],
                    key="delete_user_select",
                    format_func=lambda x: next((display for id, display in delete_options_with_default if id == x), 'Pilih Pengguna untuk Dihapus'))
                
                if selected_delete_option and selected_delete_option != "":
                    selected_user = next((user for user in all_users if user.get('_id') == selected_delete_option), None)
                    if selected_user:
                        st.warning(f" Anda akan menghapus pengguna: {selected_user.get('Nama Lengkap')}")
                        st.write(f"Nomor Identitas: {selected_user.get('Nomor Identitas')}")
                        st.write(f"Role: {selected_user.get('Role')}")
                        st.write(f"Jenis Kelamin: {selected_user.get('Jenis Kelamin')}")
                        st.write(f"Tanggal Lahir: {selected_user.get('Tanggal Lahir')}")
                        
                        # Tampilkan informasi tambahan
                        if selected_user.get('Role') in ['dokter', 'admin']:
                            st.write(f"Institusi: {selected_user.get('Institusi', '-')}")
                        if selected_user.get('Role') == 'dokter':
                            st.write(f"Spesialisasi: {selected_user.get('Spesialisasi', '-')}")

                        if selected_user.get('Role') == 'admin':
                            st.error(" **PERINGATAN:** Menghapus akun admin mungkin dapat menyebabkan masalah akses!")

                        has_examinations = check_user_examinations(selected_user['_id'])
                        if has_examinations:
                            st.warning("⚠️ **Perhatian:** Pengguna ini memiliki riwayat pemeriksaan. Menghapus user akan menghapus semua data pemeriksaannya!")

                        col_confirm1, col_confirm2 = st.columns(2)
                        with col_confirm1:
                            if st.button("Hapus Permanen", type="secondary", use_container_width=True):
                                if _delete_user(selected_user['_id']):
                                    st.success(f" Pengguna {selected_user.get('Nama Lengkap')} berhasil dihapus!")
                                    st.session_state.pasien_list_initialized = False 
                                    st.rerun()
                        with col_confirm2:
                            if st.button("Batal", use_container_width=True):
                                st.info("Penghapusan dibatalkan")
            else:
                st.info("Tidak ada data pengguna yang dapat dihapus")

# Helper functions
def _load_pasien_data():
    if not st.session_state.get('pasien_list_initialized', False):
        try:
            collection = get_collection('users')
            pasien_data = list(collection.find({'role': 'pasien'}))

            st.session_state.pasien_list = []
            for pasien in pasien_data:
                st.session_state.pasien_list.append({
                    "_id": str(pasien['_id']),
                    "Nomor Identitas": pasien.get('nomor_identitas', ''),
                    "Nama Lengkap": pasien.get('nama_lengkap', ''),
                    "Tanggal Lahir": pasien.get('tanggal_lahir', ''),
                    "Jenis Kelamin": pasien.get('jenis_kelamin', ''),
                    "Role": pasien.get('role', ''),
                    "Tanggal Dibuat": pasien.get('tanggal_dibuat', '')
                })
            
            st.session_state.pasien_list_initialized = True
                
        except Exception as e:
            st.error(f"Error loading patient data: {e}")

def _get_all_users():
    try:
        collection = get_collection('users')
        all_users = list(collection.find({}, {'password': 0}))
        
        data = []
        for user in all_users:
            user_data = {
                "_id": str(user['_id']), 
                "Nomor Identitas": user.get('nomor_identitas', ''),
                "Nama Lengkap": user.get('nama_lengkap', ''),
                "Role": user.get('role', ''),
                "Tanggal Lahir": user.get('tanggal_lahir', ''),
                "Jenis Kelamin": user.get('jenis_kelamin', ''),
                "Tanggal Dibuat": user.get('tanggal_dibuat', '')
            }
            
            # Tambahkan field tambahan
            if user.get('role') in ['dokter', 'admin']:
                user_data['Institusi'] = user.get('institusi', '')
            if user.get('role') == 'dokter':
                user_data['Spesialisasi'] = user.get('spesialisasi', '')
            
            data.append(user_data)
        
        return data
    except Exception as e:
        st.error(f"Error loading users data: {e}")
        return []

def _add_new_user(user_data):
    try:
        collection = get_collection('users')
        
        existing_user = collection.find_one({'nomor_identitas': user_data['nomor_identitas']})
        if existing_user:
            st.error(f"Nomor Identitas '{user_data['nomor_identitas']}' sudah terdaftar")
            return False
        
        hashed_password = hash_password(user_data['password'])
        
        new_user = {
            'nomor_identitas': user_data['nomor_identitas'],
            'nama_lengkap': user_data['nama_lengkap'],
            'password': hashed_password,
            'role': user_data['role'],
            'tanggal_lahir': user_data['tanggal_lahir'],
            'jenis_kelamin': user_data['jenis_kelamin'],
            'tanggal_dibuat': user_data['tanggal_dibuat']
        }
        
        # Tambahkan field tambahan
        if user_data.get('role') in ['dokter', 'admin']:
            new_user['institusi'] = user_data.get('institusi', '')
        if user_data.get('role') == 'dokter':
            new_user['spesialisasi'] = user_data.get('spesialisasi', '')
        
        result = collection.insert_one(new_user)
        st.session_state.pasien_list_initialized = False
        return result.inserted_id is not None
        
    except Exception as e:
        st.error(f"Error menambahkan user: {e}")
        return False

def _update_user(user_id, update_data):
    try:
        collection = get_collection('users')
        
        if 'nomor_identitas' in update_data:
            existing_user = collection.find_one({
                'nomor_identitas': update_data['nomor_identitas'],
                '_id': {'$ne': ObjectId(user_id)}
            })
            if existing_user:
                st.error(f"Nomor Identitas '{update_data['nomor_identitas']}' sudah terdaftar! Silahkan gunakan ID lain.")
                return False
                
        if 'password' in update_data and update_data['password']:
            update_data['password'] = hash_password(update_data['password'])
        elif 'password' in update_data:
            del update_data['password']
        
        # Handle field tambahan
        if 'institusi' in update_data and update_data['institusi'] is None:
            del update_data['institusi']
        if 'spesialisasi' in update_data and update_data['spesialisasi'] is None:
            del update_data['spesialisasi']
        
        result = collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )

        st.session_state.pasien_list_initialized = False
        return result.modified_count > 0
        
    except Exception as e:
        st.error(f"Error updating user: {e}")
        return False

def _delete_user(user_id):
    try:
        collection = get_collection('users')
        exam_collection = get_collection('patient_examinations')
        
        try:
            exam_collection.delete_many({'pasien_id': ObjectId(user_id)})
        except:
            exam_collection.delete_many({'pasien_id': user_id})
        
        result = collection.delete_one({'_id': ObjectId(user_id)})
        return result.deleted_count > 0
        
    except Exception as e:
        st.error(f"Error deleting user: {e}")
        return False
