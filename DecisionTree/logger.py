import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import os

CSV_FILE = "data/dataset_sensor_skripsi.csv" # Pastikan folder 'data' ada

st.title("📊 Data Logger (Update: Sekarang Pakai Suhu)")

if "recording" not in st.session_state: st.session_state.recording = False

if st.button("🚀 MULAI REKAM"): st.session_state.recording = True
if st.button("🛑 BERHENTI"): st.session_state.recording = False

while st.session_state.recording:
    try:
        base_url = "https://monitoringruangan-16163-default-rtdb.asia-southeast1.firebasedatabase.app/Data_Sensor"
        val_gas = requests.get(f"{base_url}/Gas_PPM.json").json() or 0
        val_pir = requests.get(f"{base_url}/Gerakan_PIR.json").json() or 0
        val_suhu = requests.get(f"{base_url}/Suhu.json").json() or 0 # <--- SUHU DITARIK
        val_kipas = requests.get("https://monitoringruangan-16163-default-rtdb.asia-southeast1.firebasedatabase.app/Control_Perangkat/Kipas.json").json() or "MATI"

        df_baru = pd.DataFrame([{
            "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Gas_PPM": val_gas,
            "Gerakan_PIR": val_pir,
            "Suhu": val_suhu, # <--- SUHU MASUK
            "Status_Kipas": val_kipas
        }])

        if not os.path.exists('data'): os.makedirs('data')
        if not os.path.isfile(CSV_FILE): df_baru.to_csv(CSV_FILE, index=False)
        else: df_baru.to_csv(CSV_FILE, mode='a', header=False, index=False)
        
        st.success(f"Merekam: Gas={val_gas}, Suhu={val_suhu}, PIR={val_pir}")
        time.sleep(3)
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}"); time.sleep(3); st.rerun()