import streamlit as st
import pandas as pd
import time
from streamlit_option_menu import option_menu
import requests

# --- 0. KONFIGURASI HALAMAN (SOLUSI LAYOUT BERANTAKANN) ---
# Memaksa halaman menggunakan wide mode agar kolom tetap sejajar ke samping
st.set_page_config(layout="wide")

# --- IMPORT LIBRARY ML ---
from sklearn.tree import DecisionTreeClassifier, plot_tree
import matplotlib.pyplot as plt

# --- 1. KONFIGURASI URL FIREBASE REALTIME DATABASE ---
FIREBASE_URL = "https://monitoringruangan-16163-default-rtdb.asia-southeast1.firebasedatabase.app"

# --- 3. CUSTOM CSS ---
st.markdown("""
    <style>
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.1);
        padding: 20px;
    }
    [data-testid="stMetricValue"] { font-size: 24px; }
    .step-box {
        color: white;
        padding: 10px;
        border-radius: 5px;
        min-width: 100px;
        text-align: center;
        font-size: 13px;
        font-weight: bold;
    }
    .arrow { color: #ccc; font-size: 18px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNGSI ALUR VISUALISASI ---
def render_alur_dt(s, l, g, p):
    st_suhu = "NORMAL" if s <= 30 else "PANAS"
    st_lembab = "NORMAL" if l <= 70 else "LEMBAP"
    st_gas = "AMAN" if g <= 200 else "BAHAYA"
    st_pir = "ADA ORANG" if p == "Terdeteksi" else "KOSONG"

    c_suhu = "#2E5A88" if st_suhu == "NORMAL" else "#D9534F"
    c_lembab = "#3B7FB9" if st_lembab == "NORMAL" else "#D9534F"
    c_gas = "#4A90E2" if st_gas == "AMAN" else "#D9534F"
    c_pir = "#5DADE2" if st_pir == "KOSONG" else "#e67e22"

    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin: 15px 0;">
            <div class="step-box" style="background-color: {c_suhu};">SUHU<br><small style="color: #ADFF2F;">→ {st_suhu}</small></div>
            <div class="arrow">➤</div>
            <div class="step-box" style="background-color: {c_lembab};">LEMBAP<br><small style="color: #ADFF2F;">→ {st_lembab}</small></div>
            <div class="arrow">➤</div>
            <div class="step-box" style="background-color: {c_gas};">GAS<br><small style="color: #ADFF2F;">→ {st_gas}</small></div>
            <div class="arrow">➤</div>
            <div class="step-box" style="background-color: {c_pir};">PIR<br><small style="color: #ADFF2F;">→ {st_pir}</small></div>
        </div>
    """, unsafe_allow_html=True)

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("### 🎓 Skripsi IoT")
    st.write("Anesya Gendisty M.")
    st.divider()
    menu = option_menu(
        menu_title="Main Menu",
        options=["Dashboard Utama", "Statistik Data", "Status Perangkat", "Log Aktivitas", "Pengaturan"], 
        icons=["house", "graph-up", "cpu", "clipboard-data", "gear"],
        default_index=0,
        styles={
            "container": {"padding": "5!important", "background-color": "#FFEDCE"},
            "nav-link-selected": {"background-color": "#FFC193"},
        }
    )

# --- 6. MEMBACA DATA REAL-TIME DARI FIREBASE ---
error_msg = ""
suhu, kelembapan, gas_co, gerakan = 26.5, 55.0, 120.0, "Terdeteksi"

try:
    response = requests.get(f"{FIREBASE_URL}/Data_Sensor.json", timeout=5)
    if response.status_code == 200:
        data_firebase = response.json()
        if data_firebase is not None:
            suhu = float(data_firebase.get("Suhu", 25.0))
            kelembapan = float(data_firebase.get("Kelembapan", 60.0))
            gas_co = float(data_firebase.get("Gas_PPM", 100.0))
            pir_status = int(data_firebase.get("Gerakan_PIR", 0))
            gerakan = "Terdeteksi" if pir_status == 1 else "Tidak Terdeteksi"
            status_sistem = "ONLINE"
        else:
            status_sistem = "FIREBASE EMPTY"
    else:
        status_sistem = "HTTP ERROR"
        error_msg = f"Status Code: {response.status_code} (Cek Rules Firebase Anda!)"
except Exception as e:
    status_sistem = "DISCONNECTED"
    error_msg = str(e)

# --- 7. LOGIKA SINKRONISASI HALAMAN ---
if menu == "Dashboard Utama":
    st.title("🏠 Dashboard Monitoring")
    st.subheader("Implementasi Decision Tree C4.5")
    
    if error_msg:
        st.error(f"Detail Error Firebase: {error_msg}")

    # === PROSES TRAINING MACHINE LEARNING ===
    try:
        df_train = pd.read_csv("data_dummy_sensor_kipas.csv")
        X = df_train[['Suhu_DHT22', 'Kelembapan_DHT22', 'PPM_MQ135', 'Gerakan_PIR']]
        y = df_train['Status_Kipas']
        
        model_dt = DecisionTreeClassifier(criterion='entropy', max_depth=3, random_state=42)
        model_dt.fit(X, y)
        data_ready = True
    except FileNotFoundError:
        data_ready = False
        st.error("Nes, pastiin file 'data_dummy_sensor_kipas.csv' udah satu folder sama app.py ya!")

    # Pembagian kolom layout yang kokoh di wide mode
    col1, col2 = st.columns([1, 2.3])
    
    with col1:
        with st.container(border=True):
            st.markdown("### 📡 Status Sistem")
            st.metric(label="Konektivitas Firebase", value=status_sistem, delta="Live Stream")
            st.caption(f"Update: {time.strftime('%H:%M:%S')} WIB")
            if st.button("🔄 Ambil Data Terbaru"):
                st.rerun()

    with col2:
        with st.container(border=True):
            st.markdown("### 🧠 Proses Prediksi Decision Tree (C4.5)")
            render_alur_dt(suhu, kelembapan, gas_co, gerakan)
            
            if data_ready:
                input_pir_numeric = 1 if gerakan == "Terdeteksi" else 0
                input_data = [[suhu, kelembapan, gas_co, input_pir_numeric]]
                hasil_prediksi = model_dt.predict(input_data)[0]
                
                if hasil_prediksi == "NYALA":
                    st.error("⚠️ STATUS AI: KIPAS NYALA (Butuh Pendinginan / Sirkulasi)")
                    try: requests.patch(f"{FIREBASE_URL}/Control_Perangkat.json", json={"Kipas": "NYALA"}, timeout=3)
                    except: pass
                else:
                    st.success("✅ STATUS AI: KIPAS MATI (Ruangan Aman & Adem)")
                    try: requests.patch(f"{FIREBASE_URL}/Control_Perangkat.json", json={"Kipas": "MATI"}, timeout=3)
                    except: pass
            else:
                st.warning("Model belum bisa memprediksi karena file CSV tidak ditemukan.")

    st.divider()

    if data_ready:
        st.write("### 🌳 Hasil Training: Struktur Pohon Keputusan Asli")
        with st.container(border=True):
            fig, ax = plt.subplots(figsize=(12, 5))
            plot_tree(model_dt, 
                      feature_names=['Suhu', 'Lembap', 'Gas_PPM', 'PIR'], 
                      class_names=model_dt.classes_, 
                      filled=True, 
                      rounded=True, 
                      ax=ax)
            st.pyplot(fig)

    st.write("### 📡 Parameter Sensor Real-Time (Data Firebase)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.markdown("### 🌡️ Suhu")
            st.metric(label="Temperature", value=f"{suhu} °C")
    with c2:
        with st.container(border=True):
            st.markdown("#### 💧 Kelembapan")
            st.metric(label="Humidity", value=f"{kelembapan} %")
    with c3:
        with st.container(border=True):
            st.markdown("### 💨 Gas CO")
            st.metric(label="Gas CO", value=f"{gas_co} ppm")
    with c4:
        with st.container(border=True):
            st.markdown("### 🏃 Gerakan")
            if gerakan == "Terdeteksi":
                st.markdown("<h3 style='color: red; text-align: center;'>🔴 AKTIF</h3>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='color: gray; text-align: center;'>⚪ SEPI</h3>", unsafe_allow_html=True)

    with st.container(border=True):
        st.write("### 📈 Tren Data Sensor")
        chart_data = pd.DataFrame({"Waktu": ["1h", "2h", "3h", "4h", "5h", "6h"], "Suhu": [24, 25, 26, 25.5, 26, suhu]})
        st.line_chart(chart_data.set_index("Waktu"))

elif menu == "Statistik Data":
    st.title("📊 Statistik & History")
    with st.container(border=True):
        st.write("### 🗄️ Dataset Training Decision Tree")
        try:
            df_dummy = pd.read_csv("data_dummy_sensor_kipas.csv")
            st.dataframe(df_dummy)
        except FileNotFoundError:
            st.error("File 'data_dummy_sensor_kipas.csv' tidak ditemukan di folder project.")

elif menu == "Status Perangkat":
    st.title("💻 Hardware Monitoring")
    with st.container(border=True):
        st.json({"Device": "ESP32", "Database_Connected": True, "Location": "Singapore-Node"})

elif menu == "Log Aktivitas":
    st.title("📝 Activity Logs")
    with st.container(border=True):
        st.code(f"{time.strftime('%H:%M:%S')} - Model Evaluated - Decision Tree Prediction Running")

elif menu == "Pengaturan":
    st.title("⚙️ Konfigurasi Threshold")
    with st.container(border=True):
        st.slider("Batas Suhu Panas (°C)", 20, 40, 30)
        st.button("Simpan Perubahan")
