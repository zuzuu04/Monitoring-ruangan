import streamlit as st
import pandas as pd
import time
from streamlit_option_menu import option_menu
import requests

# --- 0. KONFIGURASI HALAMAN ---
st.set_page_config(layout="wide", page_title="Dashboard Monitoring Room")

# --- IMPORT LIBRARY ML ---
from sklearn.tree import DecisionTreeClassifier, plot_tree
import matplotlib.pyplot as plt

# --- 1. KONFIGURASI URL FIREBASE REALTIME DATABASE ---
FIREBASE_URL = "https://monitoringruangan-16163-default-rtdb.asia-southeast1.firebasedatabase.app"

# --- 2. INISIALISASI GLOBAL SESSION STATE (THRESHOLD DINAMIS) ---
if "thresh_suhu" not in st.session_state:
    st.session_state.thresh_suhu = 30
if "thresh_gas" not in st.session_state:
    st.session_state.thresh_gas = 300

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
        min-width: 110px;
        text-align: center;
        font-size: 13px;
        font-weight: bold;
        transition: all 0.5s ease;
    }
    .arrow { color: #ccc; font-size: 18px; font-weight: bold; }
    
    /* Animasi pulse kalau status bahaya */
    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.8; }
        100% { transform: scale(1); opacity: 1; }
    }
    .danger-pulse {
        animation: pulse 1s infinite;
        box-shadow: 0 0 15px #ff4d4d;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNGSI ALUR VISUALISASI DENGAN THRESHOLD VARIABEL ---
def render_alur_dt(s, l, g, p):
    # Menggunakan nilai dinamis dari session state pengaturan
    st_suhu = "NORMAL" if s <= st.session_state.thresh_suhu else "PANAS"
    st_lembab = "NORMAL" if l <= 70 else "LEMBAP"
    st_gas = "AMAN" if g <= st.session_state.thresh_gas else "BAHAYA"
    st_pir = "ADA ORANG" if p == "Terdeteksi" else "KOSONG"

    c_suhu = "#2E5A88" if st_suhu == "NORMAL" else "#D9534F"
    c_lembab = "#3B7FB9" if st_lembab == "NORMAL" else "#D9534F"
    c_gas = "#4A90E2" if st_gas == "AMAN" else "#D9534F"
    c_pir = "#5DADE2" if st_pir == "KOSONG" else "#e67e22"
    
    # Deteksi kelas tambahan jika ada parameter bahaya
    class_gas = "step-box danger-pulse" if st_gas == "BAHAYA" else "step-box"
    class_suhu = "step-box danger-pulse" if st_suhu == "PANAS" else "step-box"

    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin: 15px 0;">
            <div class="{class_suhu}" style="background-color: {c_suhu};">SUHU<br><small style="color: #ADFF2F;">→ {st_suhu}</small></div>
            <div class="arrow">➤</div>
            <div class="step-box" style="background-color: {c_lembab};">LEMBAP<br><small style="color: #ADFF2F;">→ {st_lembab}</small></div>
            <div class="arrow">➤</div>
            <div class="step-box {class_gas}" style="background-color: {c_gas};">GAS<br><small style="color: #ADFF2F;">→ {st_gas}</small></div>
            <div class="arrow">➤</div>
            <div class="step-box" style="background-color: {c_pir};">PIR<br><small style="color: #ADFF2F;">→ {st_pir}</small></div>
        </div>
    """, unsafe_allow_html=True)

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("### Monitoring Ruang Keluarga")
    st.write("Diss")
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
    
    st.divider()
    # Fitur Mode Simulasi Sidang
    mode_simulasi = st.toggle("🔌 Aktifkan Mode Simulasi Alat", value=False, help="Pake ini kalau alat nggak bawa atau lagi offline")
    if mode_simulasi:
        st.info("Mode Simulasi Aktif. Gunakan slider di bawah untuk manipulasi data.")
        sim_suhu = st.slider("Simulasi Suhu (°C)", 15.0, 45.0, 26.5)
        sim_gas = st.slider("Simulasi Gas (PPM)", 100, 800, 230)
        sim_pir = st.selectbox("Simulasi PIR", ["Tidak Terdeteksi", "Terdeteksi"])

# --- 6. MEMBACA DATA REAL-TIME (FIREBASE VS SIMULASI) ---
error_msg = ""
suhu, kelembapan, gas_co, gerakan = 26.5, 55.0, 120.0, "Terdeteksi"

if mode_simulasi:
    suhu = sim_suhu
    kelembapan = 55.0
    gas_co = sim_gas
    gerakan = sim_pir
    status_sistem = "SIMULATION MODE"
else:
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
            error_msg = f"Status Code: {response.status_code}"
    except Exception as e:
        status_sistem = "DISCONNECTED"
        error_msg = str(e)

# --- 7. LOGIKA SINKRONISASI HALAMAN ---
if menu == "Dashboard Utama":
    st.title("🏠 Dashboard Monitoring")
    st.subheader("Implementasi Decision Tree C4.5")
    
    if error_msg and not mode_simulasi:
        st.error(f"Detail Error Firebase: {error_msg}")

    # --- PROSES TRAINING MACHINE LEARNING ---
    try:
        df_train = pd.read_csv("data/dataset_sensor_skripsi.csv")
        X = df_train[['Gas_PPM', 'Gerakan_PIR']]
        y = df_train['Status_Kipas']
        
        model_dt = DecisionTreeClassifier(criterion='entropy', max_depth=3, random_state=42)
        model_dt.fit(X, y)
        data_ready = True
    except FileNotFoundError:
        data_ready = False
        st.error("pathnya salah weeyy 'dataset_sensor_skripsi.csv' harus ada disatu folder!")

    col1, col2 = st.columns([1, 2.3])
    
    with col1:
        with st.container(border=True):
            st.markdown("### 📡 Status Sistem")
            st.metric(label="Konektivitas Sistem", value=status_sistem, delta="Live Stream" if not mode_simulasi else "Local Data")
            st.caption(f"Update: {time.strftime('%H:%M:%S')} WIB")
            if st.button("🔄 Ambil Data Terbaru"):
                st.rerun()

    with col2:
        with st.container(border=True):
            st.markdown("### 🧠 Proses Prediksi Decision Tree (C4.5)")
            render_alur_dt(suhu, kelembapan, gas_co, gerakan)
            
            if data_ready:
                input_pir_numeric = 1 if gerakan == "Terdeteksi" else 0
                input_data = [[gas_co, input_pir_numeric]]
                hasil_prediksi = model_dt.predict(input_data)[0]
                
                if hasil_prediksi == "NYALA":
                    st.error("⚠️ STATUS : KIPAS NYALA (Butuh Pendinginan / Sirkulasi)")
                    if not mode_simulasi:
                        try: requests.patch(f"{FIREBASE_URL}/Control_Perangkat.json", json={"Kipas": "NYALA"}, timeout=3)
                        except: pass
                else:
                    st.success("✅ STATUS AI: KIPAS MATI (Ruangan Aman & Adem)")
                    if not mode_simulasi:
                        try: requests.patch(f"{FIREBASE_URL}/Control_Perangkat.json", json={"Kipas": "MATI"}, timeout=3)
                        except: pass
            else:
                st.warning("Model belum bisa memprediksi karena file CSV tidak ditemukan.")

    st.divider()

    if data_ready:
        st.write("### 🌳 Hasil Training: Struktur Pohon Keputusan Asli")
        with st.container(border=True):
            fig, ax = plt.subplots(figsize=(12, 4))
            plot_tree(model_dt, feature_names=['Gas_PPM', 'PIR'], class_names=model_dt.classes_, filled=True, rounded=True, ax=ax)
            st.pyplot(fig)

    st.write("### 📡 Parameter Sensor Real-Time (Data Active)")
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
                st.markdown("<h3 style='color: red; text-align: center; font-weight: bold;'>🔴 AKTIF</h3>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='color: gray; text-align: center;'>⚪ SEPI</h3>", unsafe_allow_html=True)

    # --- 📈 TREN DATA SENSOR INTERAKTIF ---
    st.write("### 📈 Grafik Data Sensor Real-Time")
    if "df_history" not in st.session_state:
        st.session_state.df_history = pd.DataFrame(columns=["Waktu", "Suhu (°C)", "Kelembapan (%)", "Gas (PPM)", "PIR"])

    waktu_sekarang = time.strftime('%H:%M:%S')
    data_baru = pd.DataFrame([{"Waktu": waktu_sekarang, "Suhu (°C)": suhu, "Kelembapan (%)": kelembapan, "Gas (PPM)": gas_co, "PIR": 1 if gerakan == "Terdeteksi" else 0}])
    st.session_state.df_history = pd.concat([st.session_state.df_history, data_baru], ignore_index=True)

    if len(st.session_state.df_history) > 20:
        st.session_state.df_history = st.session_state.df_history.iloc[1:].reset_index(drop=True)

    kolom_grafik1, kolom_grafik2 = st.columns(2)
    with kolom_grafik1:
        with st.container(border=True):
            st.markdown("#### 💨 Tren Sensor Gas MQ135")
            data_gas = st.session_state.df_history[["Waktu", "Gas (PPM)"]].set_index("Waktu")
            st.line_chart(data_gas, color="#4A90E2")
    with kolom_grafik2:
        with st.container(border=True):
            st.markdown("#### 🏃 Tren Pergerakan Manusia (PIR)")
            data_pir = st.session_state.df_history[["Waktu", "PIR"]].set_index("Waktu")
            st.line_chart(data_pir, color="#e67e22")

    # --- AUTO REFRESH LOOP ---
    time.sleep(3)
    st.rerun()

elif menu == "Statistik Data":
    st.title("📊 Statistik & History")
    with st.container(border=True):
        st.write("### 🗄️ Dataset Training Decision Tree")
        try:
            df_dummy = pd.read_csv("data/dataset_sensor_skripsi.csv")
            st.dataframe(df_dummy)
        except FileNotFoundError:
            st.error("File 'dataset_sensor_skripsi.csv' tidak ditemukan.")

elif menu == "Status Perangkat":
    st.title("💻 Hardware Monitoring")
    with st.container(border=True):
        st.json({"Device": "ESP32", "Database_Connected": True if status_sistem=="ONLINE" else False, "Mode": status_sistem})

elif menu == "Log Aktivitas":
    st.title("📝 Activity Logs")
    with st.container(border=True):
        st.code(f"{time.strftime('%H:%M:%S')} - Status: {status_sistem} - Gas: {gas_co} PPM - PIR: {gerakan}")

elif menu == "Pengaturan":
    st.title("⚙️ Konfigurasi Threshold")
    with st.container(border=True):
        st.write("Atur batas toleransi sensor lokal di bawah ini:")
        # Mengikat slider langsung ke global session state browser
        st.session_state.thresh_suhu = st.slider("Batas Kebisingan / Suhu Panas (°C)", 20, 40, st.session_state.thresh_suhu)
        st.session_state.thresh_gas = st.slider("Batas Aman Deteksi Gas (PPM)", 100, 600, st.session_state.thresh_gas)
        
        if st.button("Simpan & Terapkan Konfigurasi"):
            st.success("✅ Batas threshold berhasil diperbarui! Silakan cek kembali halaman Dashboard Utama.")
