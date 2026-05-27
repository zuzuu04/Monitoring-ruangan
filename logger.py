import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import os

st.set_page_config(page_title="Data Logger Skripsi", layout="centered")
st.title("📊 Perekam Data Otomatis (Suhu & Sensor)")
st.write("Dashboard ini menarik data dari Firebase dan menyimpannya ke CSV untuk training Decision Tree.")

CSV_FILE = "dataset_sensor_skripsi.csv"

# Variabel kontrol
if "recording" not in st.session_state:
    st.session_state.recording = False

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 MULAI REKAM DATA", use_container_width=True):
        st.session_state.recording = True
with col2:
    if st.button("🛑 BERHENTI REKAM", use_container_width=True):
        st.session_state.recording = False

status_placeholder = st.empty()
data_placeholder = st.empty()

# Proses Perekaman
while st.session_state.recording:
    try:
        base_url = "https://monitoringruangan-16163-default-rtdb.asia-southeast1.firebasedatabase.app"
        
        # Ambil data sekaligus
        val_gas = requests.get(f"{base_url}/Data_Sensor/Gas_PPM.json").json() or 0
        val_pir = requests.get(f"{base_url}/Data_Sensor/Gerakan_PIR.json").json() or 0
        val_suhu = requests.get(f"{base_url}/Data_Sensor/Suhu.json").json() or 0
        val_kipas = requests.get(f"{base_url}/Control_Perangkat/Kipas.json").json() or "MATI"

        df_baru = pd.DataFrame([{
            "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Gas_PPM": val_gas,
            "Gerakan_PIR": val_pir,
            "Suhu": val_suhu,
            "Status_Kipas": val_kipas
        }])

        # Append data ke CSV
        if not os.path.isfile(CSV_FILE):
            df_baru.to_csv(CSV_FILE, index=False)
        else:
            df_baru.to_csv(CSV_FILE, mode='a', header=False, index=False)

        status_placeholder.success(f"🟢 Merekam: Gas={val_gas}, Suhu={val_suhu}, PIR={val_pir}")
        
        # Tampilkan data di web
        df_total = pd.read_csv(CSV_FILE)
        data_placeholder.dataframe(df_total.tail(10))

    except Exception as e:
        status_placeholder.error(f"Error koneksi: {e}")
    
    time.sleep(3)
    st.rerun()

# Kalau berhenti
if not st.session_state.recording:
    status_placeholder.info("🔴 Perekaman berhenti. Data aman tersimpan.")
    if os.path.isfile(CSV_FILE):
        df_total = pd.read_csv(CSV_FILE)
        st.write("### Cuplikan Dataset Terakhir:")
        st.dataframe(df_total.tail(10))
