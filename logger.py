import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import os

st.set_page_config(page_title="Data Logger Skripsi", layout="centered")
st.title("📊 Perekam Data Otomatis (Firebase to CSV)")
st.write("Dashboard ini otomatis menarik data dari Firebase dan menyimpannya ke file Excel/CSV untuk training Decision Tree.")

# Nama file CSV yang bakal menampung data skripsi lo
CSV_FILE = "dataset_sensor_skripsi.csv"

# Variabel kontrol untuk tombol Mulai/Berhenti Rekam
if "recording" not in st.session_state:
    st.session_state.recording = False

# Tombol di Dashboard Streamlit
col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 MULAI REKAM DATA", use_container_width=True):
        st.session_state.recording = True
with col2:
    if st.button("🛑 BERHENTI REKAM", use_container_width=True):
        st.session_state.recording = False

# Tampilan Status Perekaman
status_placeholder = st.empty()
data_placeholder = st.empty()

# 2. Proses Perekaman Otomatis (Looping selama tombol REKAM aktif)
while st.session_state.recording:
    try:
        # Trik tembak langsung pake REST API Firebase (.json di akhir URL)
        # Ini cara paling aman dan anti-error kredensial, Nes!
        url_gas = "https://monitoringruangan-16163-default-rtdb.asia-southeast1.firebasedatabase.app/Data_Sensor/Gas_PPM.json"
        url_pir = "https://monitoringruangan-16163-default-rtdb.asia-southeast1.firebasedatabase.app/Data_Sensor/Gerakan_PIR.json"
        url_kipas = "https://monitoringruangan-16163-default-rtdb.asia-southeast1.firebasedatabase.app/Control_Perangkat/Kipas.json"
        
        val_gas = requests.get(url_gas).json()
        val_pir = requests.get(url_pir).json()
        val_kipas = requests.get(url_kipas).json()

        # Antisipasi kalau data di Firebase sempat kosong/None
        if val_gas is None: val_gas = 0
        if val_pir is None: val_pir = 0
        if val_kipas is None: val_kipas = "MATI"

        # Ambil waktu saat data ditarik
        waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Struktur baris data baru
        data_baru = {
            "Waktu": [waktu_sekarang],
            "Gas_PPM": [val_gas],
            "Gerakan_PIR": [val_pir],
            "Status_Kipas": [val_kipas]
        }
        df_baru = pd.DataFrame(data_baru)

        # Cek apakah file CSV sudah ada di laptop atau belum
        if not os.path.isfile(CSV_FILE):
            df_baru.to_csv(CSV_FILE, index=False)
        else:
            df_baru.to_csv(CSV_FILE, mode='a', header=False, index=False)

        # Update status & tampilan tabel di web Streamlit secara real-time
        status_placeholder.success(f"🟢 Sedang merekam... Data terakhir masuk pada: {waktu_sekarang}")
        
        # Baca seluruh isi CSV saat ini untuk ditampilkan ke layar dashboard lo
        df_total = pd.read_csv(CSV_FILE)
        data_placeholder.dataframe(df_total.tail(10))

    except Exception as e:
        status_placeholder.error(f"Waduh ada error koneksi: {e}")
    
    # Kasih jeda waktu perekaman 3 detik sekali
    time.sleep(3)
    st.rerun()

if not st.session_state.recording:
    status_placeholder.info("🔴 Perekaman berhenti. Data aman tersimpan di file 'dataset_sensor_skripsi.csv'")
    if os.path.isfile(CSV_FILE):
        df_total = pd.read_csv(CSV_FILE)
        st.write("### Cuplikan Dataset Lo Saat Ini:")
        st.dataframe(df_total)