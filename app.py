import streamlit as st
import pandas as pd
import time
from streamlit_option_menu import option_menu
import requests
from datetime import datetime
import pytz 

# --- 0. KONFIGURASI HALAMAN ---
st.set_page_config(layout="wide", page_title="Dashboard Monitoring Room")

# --- IMPORT LIBRARY ML ---
from sklearn.tree import DecisionTreeClassifier, plot_tree
import matplotlib.pyplot as plt

# --- 1. KONFIGURASI URL & CREDENTIALS ---
# Sudah dirapikan ujung URL-nya menggunakan garing (/)
FIREBASE_URL = "https://monitoringruangan-16163-default-rtdb.asia-southeast1.firebasedatabase.app/"

# Credential Telegram Lu
TELEGRAM_TOKEN = "8928926243:AAEVJu2PPCHJ9A3I5E7Gzh_mHojqgDw6U-8"
TELEGRAM_CHAT_ID = "8687837733"

# --- FUNGSI KIRIM NOTIFIKASI TELEGRAM ---
def kirim_notif_telegram(pesan):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": pesan,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=3)
    except:
        pass # Mengabaikan error jika koneksi internet putus/timeout

# --- 2. INISIALISASI GLOBAL SESSION STATE (THRESHOLD DINAMIS) ---
if "thresh_suhu" not in st.session_state:
    st.session_state.thresh_suhu = 30
if "thresh_gas" not in st.session_state:
    st.session_state.thresh_gas = 300

# State untuk mencegah spam notifikasi terus-menerus setiap 3 detik refresh
if "last_alert_kipas" not in st.session_state:
    st.session_state.last_alert_kipas = "MATI"
if "last_alert_maling" not in st.session_state:
    st.session_state.last_alert_maling = False

# --- 3. CUSTOM CSS DENGAN ANIMASI EMERGENSI & SAKELAR VISUAL ---
st.markdown("""
    <style>
    /* Styling Dasar Kontainer */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.1);
        padding: 20px;
    }
    [data-testid="stMetricValue"] { font-size: 24px; }
    
    /* Styling Alur Langkah (Step Boxes) */
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
    
    /* Animasi Pulse Bahaya */
    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.8; }
        100% { transform: scale(1); opacity: 1; }
    }
    .danger-pulse {
        animation: pulse 1s infinite;
        box-shadow: 0 0 15px #ff4d4d;
    }

    /* === SAKELAR VISUAL SAKTI === */
    [data-testid="stSidebarNav"] div[data-testid="toggle_kipas_ai"] {
        display: none !important;
    }

    .custom-switch {
        position: relative;
        display: inline-block;
        width: 60px;
        height: 34px;
        transition: all 0.5s ease;
    }
    .custom-switch-slider {
        position: absolute;
        cursor: not-allowed;
        top: 0; left: 0; right: 0; bottom: 0;
        border-radius: 34px;
        transition: 0.5s;
    }
    .custom-switch-slider:before {
        position: absolute;
        content: "";
        height: 26px; width: 26px;
        left: 4px; bottom: 4px;
        background-color: white;
        border-radius: 50%;
        transition: 0.5s;
    }
    
    .status-on .custom-switch-slider {
        background-color: #ADFF2F !important;
        box-shadow: 0 0 15px #ADFF2F !important;
    }
    .status-on .custom-switch-slider:before {
        transform: translateX(26px);
    }
    
    .status-off .custom-switch-slider {
        background-color: #D9534F !important;
        box-shadow: 0 0 15px #D9534F !important;
    }
    .status-off .custom-switch-slider:before {
        transform: translateX(0px);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNGSI ALUR VISUALISASI ---
def render_alur_dt(s, l, g, p):
    st_suhu = "NORMAL" if s <= st.session_state.thresh_suhu else "PANAS"
    st_lembab = "NORMAL" if l <= 70 else "LEMBAP"
    st_gas = "AMAN" if g <= st.session_state.thresh_gas else "BAHAYA"
    st_pir = "ADA ORANG" if p == "Terdeteksi" else "KOSONG"

    c_suhu = "#2E5A88" if st_suhu == "NORMAL" else "#D9534F"
    c_lembab = "#3B7FB9" if st_lembab == "NORMAL" else "#D9534F"
    c_gas = "#4A90E2" if st_gas == "AMAN" else "#D9534F"
    c_pir = "#5DADE2" if st_pir == "KOSONG" else "#e67e22"
    
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
    
    # --- FITUR INTEGRASI KEAMANAN ALAT ---
    st.markdown("### 🔒 Sistem Keamanan Alat")
    
    default_mode_aman = False
    try:
        resp_mode = requests.get(f"{FIREBASE_URL}Control_Perangkat/Mode_Aman.json", timeout=2)
        if resp_mode.status_code == 200 and resp_mode.json() == "ON":
            default_mode_aman = True
    except:
        pass

    mode_keamanan = st.toggle("Aktifkan Alarm Anti-Maling", value=default_mode_aman, help="Jika AKTIF, buzzer ESP32 akan bunyi panjang saat PIR mendeteksi gerakan.")
    
    status_str = "ON" if mode_keamanan else "OFF"
    try:
        requests.patch(f"{FIREBASE_URL}Control_Perangkat.json", json={"Mode_Aman": status_str}, timeout=2)
    except:
        pass
    
    if mode_keamanan:
        st.markdown("<p style='color: #D9534F; font-weight: bold; margin-top: -5px;'>🔴 STATUS: SIAGA (Anti-Maling Aktif)</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='color: #777777; font-weight: bold; margin-top: -5px;'>⚪ STATUS: MATI (Standby)</p>", unsafe_allow_html=True)
    
    st.divider()
    
    mode_simulasi = st.toggle("🔌 Aktifkan Mode Simulasi Alat", value=False, help="Gunakan ini jika hardware ESP32 offline")
    if mode_simulasi:
        st.info("Mode Simulasi Aktif. Gunakan slider di bawah untuk manipulasi data.")
        sim_suhu = st.slider("Simulasi Suhu (°C)", 15.0, 45.0, 26.5)
        sim_gas = st.slider("Simulasi Gas (PPM)", 100, 800, 230)
        sim_pir = st.selectbox("Simulasi PIR", ["Tidak Terdeteksi", "Terdeteksi"])

# --- 6. MEMBACA DATA REAL-TIME ---
error_msg = ""
suhu, kelembapan, gas_co, gerakan = 26.5, 55.0, 120.0, "Tidak Terdeteksi"

if mode_simulasi:
    suhu = sim_suhu
    kelembapan = 55.0
    gas_co = sim_gas
    gerakan = sim_pir
    status_sistem = "SIMULATION MODE"
else:
    try:
        response = requests.get(f"{FIREBASE_URL}Data_Sensor.json", timeout=5)
        if response.status_code == 200:
            data_firebase = response.json()
            if data_firebase is not None:
                suhu = float(data_firebase.get("Suhu", 25.0))
                kelembapan = float(data_firebase.get("Kelembapan", 60.0))
                gas_co = float(data_firebase.get("Gas_PPM", 100.0))
                pir_status = int(data_firebase.get("Gerakan_PIR", 0))
                gerakan = "Terdeteksi" if pir_status == 1 else "Tidak Terdeteksi"
                
                # --- LOGIKA PENGECEKAN STATUS ONLINE / OFFLINE YANG VALID ---
                last_seen_esp = data_firebase.get("Last_Seen", None) 
                waktu_sekarang_epoch = int(time.time())
                
                if last_seen_esp is not None:
                    selisih_waktu = waktu_sekarang_epoch - int(last_seen_esp)
                    if selisih_waktu > 5:
                        status_sistem = "OFFLINE (Alat Mati)"
                    else:
                        status_sistem = "ONLINE"
                else:
                    status_sistem = "OFFLINE (No Heartbeat Data)"
            else:
                status_sistem = "FIREBASE EMPTY"
        else:
            status_sistem = "HTTP ERROR"
            error_msg = f"Status Code: {response.status_code}"
    except Exception as e:
        status_sistem = "DISCONNECTED"
        error_msg = str(e)

# --- 7. LOGIKA DASHBOARD UTAMA ---
if menu == "Dashboard Utama":
    st.title("🏠 Dashboard Monitoring")
    st.subheader("Implementasi Decision Tree C4.5")
    
    if error_msg and not mode_simulasi:
        st.error(f"Detail Error Firebase: {error_msg}")

    # --- PROSES TRAINING MACHINE LEARNING ---
    data_ready = False
    try:
        df_train = pd.read_csv("data/dataset_sensor_skripsi.csv")
        X = df_train[['Gas_PPM', 'Gerakan_PIR']]
        y = df_train['Status_Kipas']
        
        model_dt = DecisionTreeClassifier(criterion='entropy', max_depth=3, random_state=42)
        model_dt.fit(X, y)
        data_ready = True
    except FileNotFoundError:
        st.error("Gagal memuat dataset! Pastikan file 'data/dataset_sensor_skripsi.csv' sudah benar.")

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
                
                st.markdown("#### 🔌 Status Perangkat (Kipas)")
                
                class_status = "status-on" if hasil_prediksi == "NYALA" else "status-off"
                status_warna = "HIJAU (Neon ON)" if hasil_prediksi == "NYALA" else "MERAH (Neon OFF)"
                
                st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 15px; margin-top: 10px;">
                        <label class="custom-switch {class_status}">
                            <span class="custom-switch-slider"></span>
                        </label>
                        <span style="font-weight: bold; color: {'#ADFF2F' if hasil_prediksi == 'NYALA' else '#D9534F'};">
                            AI Output: {hasil_prediksi} (Warna {status_warna})
                        </span>
                    </div>
                """, unsafe_allow_html=True)
                
                st.caption("Sakelar dikontrol sepenuhnya oleh logika AI, tidak bisa diklik manual.")
                
                # --- LOGIKA WAKTU DI TELE ---
                zona_wib = pytz.timezone('Asia/Jakarta')
                waktu_notif = datetime.now(zona_wib).strftime('%d-%m-%Y %H:%M:%S')
                
                # --- INTEGRASI LOGIKA NOTIFIKASI TELEGRAM ---
                if hasil_prediksi == "NYALA":
                    st.error(f"⚠️ TRIGGER C4.5: Kipas telah diaktifkan secara otomatis!")
                    
                    if st.session_state.last_alert_kipas == "MATI":
                        pesan_kipas = (
                            f"🚨 *PERINGATAN SISTEM LU* 🚨\n\n"
                            f"📅 *Waktu:* {waktu_notif} WIB\n"
                            f"⚠️ AI C4.5 mendeteksi kadar gas berbahaya! *Kipas Otomatis Dinyalakan*.\n"
                            f"💨 *Gas CO:* {gas_co} PPM\n"
                            f"🌡️ *Suhu:* {suhu} °C"
                        )
                        kirim_notif_telegram(pesan_kipas)
                        st.session_state.last_alert_kipas = "NYALA"

                    if not mode_simulasi:
                        try: requests.patch(f"{FIREBASE_URL}Control_Perangkat.json", json={"Kipas": "NYALA"}, timeout=3)
                        except: pass
                else:
                    st.success(f"✅ TRIGGER C4.5: Ruangan aman, kipas dinonaktifkan.")
                    
                    if st.session_state.last_alert_kipas == "NYALA":
                        pesan_aman = f"✅ *INFO SISTEM:*\n📅 *Waktu:* {waktu_notif} WIB\nKondisi ruangan sudah kembali normal. Kipas dinonaktifkan."
                        kirim_notif_telegram(pesan_aman)
                        st.session_state.last_alert_kipas = "MATI"
                        
                    if not mode_simulasi:
                        try: requests.patch(f"{FIREBASE_URL}Control_Perangkat.json", json={"Kipas": "MATI"}, timeout=3)
                        except: pass

                # --- NOTIFIKASI TELEGRAM UNTUK ANTI-MALING (PIR) ---
                if mode_keamanan and gerakan == "Terdeteksi":
                    if not st.session_state.last_alert_maling:
                        pesan_maling = (
                            f"⚠️ *ALARM KEAMANAN (ANTI-MALING)* ⚠️\n\n"
                            f"📅 *Waktu:* {waktu_notif} WIB\n"
                            f"Terdeteksi adanya pergerakan mencurigakan saat Mode Siaga Aktif!\n"
                            f"🏃 *Status PIR:* Ada Gerakan!"
                        )
                        kirim_notif_telegram(pesan_maling)
                        st.session_state.last_alert_maling = True
                elif gerakan == "Tidak Terdeteksi":
                    st.session_state.last_alert_maling = False

    if data_ready:
        st.write("### 🌳 Hasil Training: Struktur Pohon Keputusan")
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
                st.markdown("<h3 style='color: red; text-align: center; font-weight: bold;'>🔴 ADA PERGERAKAN</h3>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='color: gray; text-align: center;'>⚪ TIDAK ADA PERGERAKAN</h3>", unsafe_allow_html=True)

    # --- GRAFIK DATA SENSOR ---
    st.write("### 📈 Tren Data Sensor Real-Time")
    if "df_history" not in st.session_state:
        st.session_state.df_history = pd.DataFrame(columns=["Waktu", "Suhu (°C)", "Kelembapan (%)", "Gas (PPM)", "PIR"])

    waktu_sekarang = time.strftime('%H:%M:%S')
    data_baru = pd.DataFrame([{"Waktu": waktu_sekarang, "Suhu (°C)": suhu, "Kelembapan (%)": kelembapan, "Gas (PPM)": gas_co, "PIR": 1 if gerakan == "Terdeteksi" else 0}])
    st.session_state.df_history = pd.concat([st.session_state.df_history, data_baru], ignore_index=True)

    if len(st.session_state.df_history) > 20:
        st.session_state.df_history = st.session_state.df_history.iloc[1:].reset_index(drop=True)

    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        with st.container(border=True):
            st.markdown("#### 🌡️ Tren Suhu (°C)")
            st.line_chart(st.session_state.df_history[["Waktu", "Suhu (°C)"]].set_index("Waktu"), color="#D9534F")
        
        with st.container(border=True):
            st.markdown("#### 💨 Tren Sensor Gas MQ135 (PPM)")
            st.line_chart(st.session_state.df_history[["Waktu", "Gas (PPM)"]].set_index("Waktu"), color="#4A90E2")

    with col_g2:
        with st.container(border=True):
            st.markdown("#### 💧 Tren Kelembapan (%)")
            st.line_chart(st.session_state.df_history[["Waktu", "Kelembapan (%)"]].set_index("Waktu"), color="#3B7FB9")
            
        with st.container(border=True):
            st.markdown("#### 🏃 Tren Pergerakan (PIR)")
            st.line_chart(st.session_state.df_history[["Waktu", "PIR"]].set_index("Waktu"), color="#e67e22")

    # --- AUTO REFRESH LOOP (3 DETIK) --- 
    time.sleep(3)
    st.rerun()

# --- PANEL MENU LAIN ---
elif menu == "Statistik Data":
    st.title("📊 Statistik & History")
    with st.container(border=True):
        st.write("### 🗄️ Dataset Training Decision Tree")
        try:
            df_dummy = pd.read_csv("data/dataset_sensor_skripsi.csv")
            st.dataframe(df_dummy)
        except FileNotFoundError:
            st.error("File 'data/dataset_sensor_skripsi.csv' nggak ditemukan.")

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
        st.write("Atur batas toleransi keadaan lingkungan ruang di bawah ini:")
        st.session_state.thresh_suhu = st.slider("Batas Kebisingan / Suhu Panas (°C)", 20, 40, st.session_state.thresh_suhu)
        st.session_state.thresh_gas = st.slider("Batas Aman Deteksi Gas MQ135 (PPM)", 100, 600, st.session_state.thresh_gas)
        
        if st.button("Simpan & Terapkan Konfigurasi"):
            st.success("✅ Batas threshold berhasil diperbarui! Silakan cek kembali halaman Dashboard Utama.")
