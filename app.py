import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
import pytz
from streamlit_option_menu import option_menu

from config import FIREBASE_URL, DATASET_PATH
from utils import (
    kirim_notif_telegram, train_model, render_alur_dt, render_decision_tree_analysis,
    measure_latency, get_alert_state, build_alert_message, build_clear_message
)

# --- 0. KONFIGURASI HALAMAN ---
st.set_page_config(layout="wide", page_title="Dashboard Monitoring Room")

# --- 1. SESSION STATE ---
defaults = {
    "thresh_suhu": 30,
    "thresh_gas": 300,
    "last_alert_state": "NONE",  # NONE, SUHU, GAS, GAS_SUHU, INTRUDER, EMERGENCY
    "df_history": pd.DataFrame(columns=["Waktu", "Suhu (°C)", "Kelembapan (%)", "Gas (PPM)", "PIR"]),
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- 2. CUSTOM CSS ---
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; font-size: 50px; margin-bottom: -10px;'>🏠</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #4A90E2; font-weight: bold;'>RUMAH PINTAR</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888; font-size: 13px; margin-top: -10px;'>IoT Room Monitoring & Automation</p>", unsafe_allow_html=True)
    st.divider()

    menu = option_menu(
        menu_title="NAVIGASI UTAMA",
        options=["Dashboard Utama", "Statistik Data", "Status Perangkat", "Log Aktivitas", "Pengaturan"],
        icons=["house-door-fill", "bar-chart-line-fill", "cpu-fill", "journal-text", "gear-wide-connected"],
        default_index=0,
        styles={
            "container": {"padding": "5px!important", "background-color": "transparent", "border-radius": "10px"},
            "icon": {"color": "#475569", "font-size": "16px"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left",
                "margin": "5px",
                "--hover-color": "RGBA(15, 118, 110, 0.1)",
                "border-radius": "8px"
            },
            "nav-link-selected": {
                "background-color": "#0F766E",
                "color": "#ffffff",
                "font-weight": "600"
            },
        }
    )

    st.divider()

    # --- Anti-Maling Toggle ---
    st.markdown("### 🔒 Sistem Keamanan Alat")
    default_mode_aman = False
    try:
        r = requests.get(f"{FIREBASE_URL}Control_Perangkat/Mode_Aman.json", timeout=2)
        if r.status_code == 200 and r.json() == "ON":
            default_mode_aman = True
    except Exception:
        pass

    mode_keamanan = st.toggle("Aktifkan Alarm Anti-Maling", value=default_mode_aman,
        help="Jika AKTIF, buzzer ESP32 bunyi saat PIR mendeteksi gerakan.")
    try:
        requests.patch(f"{FIREBASE_URL}Control_Perangkat.json",
            json={"Mode_Aman": "ON" if mode_keamanan else "OFF"}, timeout=2)
    except Exception:
        pass

    if mode_keamanan:
        st.markdown("<div class='blink-alarm'>🚨 STATUS: SIAGA AKTIF</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='standby-badge'>⚪ STATUS: STANDBY</div>", unsafe_allow_html=True)

    st.divider()

    # --- Mode Simulasi ---
    mode_simulasi = st.toggle("🔌 Mode Simulasi Alat", value=False,
        help="Gunakan jika hardware ESP32 offline")
    if mode_simulasi:
        st.info("Mode Simulasi Aktif.")
        sim_suhu = st.slider("Simulasi Suhu (°C)", 15.0, 45.0, 26.5)
        sim_gas = st.slider("Simulasi Gas (PPM)", 100, 800, 230)
        sim_pir = st.selectbox("Simulasi PIR", ["Tidak Terdeteksi", "Terdeteksi"])

    st.sidebar.markdown("""
    <br><br>
    <div style='background-color: #F4F6F7; padding: 10px; border-radius: 8px; border-left: 4px solid #FFC193;'>
        <p style='margin: 0; font-size: 11px; color: #7F8C8D;'><b>Sistem Hybrid AI IoT</b></p>
        <p style='margin: 0; font-size: 11px; color: #7F8C8D;'>Metode: Decision Tree C4.5</p>
        <p style='margin: 0; font-size: 10px; color: #BDC3C7;'>Kelas: 4KB02</p>
    </div>
    """, unsafe_allow_html=True)

# --- 4. BACA DATA REAL-TIME ---
error_msg = ""
suhu, kelembapan, gas_co, gerakan = 26.5, 55.0, 120.0, "Tidak Terdeteksi"
status_sistem = "UNKNOWN"

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
            data = response.json()
            if data:
                suhu = float(data.get("Suhu", 25.0))
                kelembapan = float(data.get("Kelembapan", 60.0))
                gas_co = float(data.get("Gas_PPM", 100.0))
                gerakan = "Terdeteksi" if int(data.get("Gerakan_PIR", 0)) == 1 else "Tidak Terdeteksi"

                last_seen = data.get("Last_Seen", None)
                if last_seen:
                    selisih = int(time.time()) - int(last_seen)
                    status_sistem = "ONLINE" if selisih <= 5 else "OFFLINE (Alat Mati)"
                else:
                    status_sistem = "OFFLINE (No Heartbeat)"
            else:
                status_sistem = "FIREBASE EMPTY"
        else:
            status_sistem = f"HTTP ERROR {response.status_code}"
    except Exception as e:
        status_sistem = "DISCONNECTED"
        error_msg = str(e)

# --- 5. HALAMAN DASHBOARD UTAMA ---
if menu == "Dashboard Utama":
    st.title("🏠 Dashboard Monitoring")
    st.subheader("Informasi Kondisi Ruangan Real-Time")

    if error_msg and not mode_simulasi:
        st.error(f"Firebase Error: {error_msg}")

    # --- Load Model Decision Tree (cached) ---
    model_dt, data_ready, _akurasi, _n_test = train_model()
    if not data_ready:
        st.error(f"Dataset tidak ditemukan: '{DATASET_PATH}'")

    col1, col2 = st.columns([1, 2.3])

    with col1:
        with st.container(border=True):
            st.markdown("### 📡 Status Sistem")
            st.metric("Konektivitas", status_sistem,
                delta="Live Stream" if not mode_simulasi else "Local Sim")
            st.caption(f"🔄 Auto-refresh tiap 3 detik · Update terakhir: {time.strftime('%H:%M:%S')} WIB")

    with col2:
        with st.container(border=True):
            st.markdown("### 🧠 Proses Prediksi Decision Tree C4.5")
            render_alur_dt(suhu, kelembapan, gas_co, gerakan,
                            st.session_state.thresh_suhu, st.session_state.thresh_gas)

            if data_ready:
                input_pir = 1 if gerakan == "Terdeteksi" else 0
                input_data = pd.DataFrame(
                    [[suhu, kelembapan, gas_co, input_pir]],
                    columns=['Suhu', 'Kelembapan', 'Gas_PPM', 'Gerakan_PIR']
                )
                hasil = model_dt.predict(input_data)[0]
                class_status = "status-on" if hasil == "NYALA" else "status-off"
                warna_label = "#2ECC71" if hasil == "NYALA" else "#94A3B8"

                st.markdown("#### 🔌 Output AI → Kontrol Kipas")
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:15px;margin-top:10px;">
                    <label class="custom-switch {class_status}">
                        <span class="custom-switch-slider"></span>
                    </label>
                    <span style="font-weight:bold;color:{warna_label}; font-size:16px;">
                        Decision Tree Output: <b>{hasil}</b>
                    </span>
                </div>
                <br>
                """, unsafe_allow_html=True)

                if hasil == "NYALA":
                    st.error("⚠️ Decision Tree C4.5: Kipas dinyalakan (gas/suhu/gerakan terdeteksi).")
                    if not mode_simulasi:
                        try: requests.patch(f"{FIREBASE_URL}Control_Perangkat.json", json={"Kipas": "NYALA"}, timeout=3)
                        except Exception: pass
                else:
                    st.success("✅ Kondisi aman — Kipas dinonaktifkan.")
                    if not mode_simulasi:
                        try: requests.patch(f"{FIREBASE_URL}Control_Perangkat.json", json={"Kipas": "MATI"}, timeout=3)
                        except Exception: pass

                # --- Logic Notifikasi Bertingkat (Lapis 1: Safety, Lapis 2: Keamanan, Lapis 3: Darurat) ---
                gas_bahaya = gas_co > st.session_state.thresh_gas
                suhu_tinggi = suhu > st.session_state.thresh_suhu
                pir_aktif = gerakan == "Terdeteksi"

                current_state = get_alert_state(gas_bahaya, suhu_tinggi, mode_keamanan, pir_aktif)
                zona_wib = pytz.timezone('Asia/Jakarta')
                waktu_notif = datetime.now(zona_wib).strftime('%d-%m-%Y %H:%M:%S')

                if current_state != st.session_state.last_alert_state:
                    if current_state == "NONE":
                        pesan = build_clear_message(st.session_state.last_alert_state, waktu_notif)
                    else:
                        pesan = build_alert_message(current_state, waktu_notif, suhu, gas_co)
                    if pesan:
                        kirim_notif_telegram(pesan)
                    st.session_state.last_alert_state = current_state

                if current_state == "EMERGENCY":
                    st.error("🚨🚨 DARURAT: Rumah kosong + gerakan + gas/suhu tidak normal — kemungkinan bahaya serius!")
                elif current_state == "GAS_SUHU":
                    st.error("🚨 Gas berbahaya & suhu tinggi terdeteksi bersamaan!")
                elif current_state == "GAS":
                    st.error("🚨 Gas berbahaya terdeteksi — kipas otomatis ventilasi.")
                elif current_state == "SUHU":
                    st.info("🌡️ Suhu ruangan tinggi — kipas otomatis menyala untuk sirkulasi.")
                elif current_state == "INTRUDER":
                    st.warning("⚠️ Mode Siaga: Gerakan terdeteksi! Buzzer aktif di ESP32.")
                elif pir_aktif and not mode_keamanan:
                    st.caption("🏃 Ada gerakan terdeteksi — kipas dinyalakan untuk sirkulasi udara (bukan kondisi bahaya).")

    # --- Kartu Sensor ---
    st.write("### 📡 Parameter Sensor")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.markdown("### 🌡️ Suhu")
            st.metric("Temperature", f"{suhu} °C")
    with c2:
        with st.container(border=True):
            st.markdown("#### 💧 Kelembapan")
            st.metric("Humidity", f"{kelembapan} %")
    with c3:
        with st.container(border=True):
            st.markdown("### 💨 Kualitas Udara")
            st.metric("Gas CO", f"{gas_co} ppm")
    with c4:
        with st.container(border=True):
            st.markdown("### 🏃 Gerakan")
            if gerakan == "Terdeteksi":
                st.markdown("<h3 style='color:red;text-align:center;font-weight:bold;'>🔴 AKTIF</h3>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='color:gray;text-align:center;'>⚪ TIDAK AKTIF</h3>", unsafe_allow_html=True)

    # --- Grafik Real-Time ---
    st.write("### 📈 Grafik Sensor")
    waktu_skrg = time.strftime('%H:%M:%S')
    data_baru = pd.DataFrame([{
        "Waktu": waktu_skrg, "Suhu (°C)": suhu,
        "Kelembapan (%)": kelembapan, "Gas (PPM)": gas_co,
        "PIR": 1 if gerakan == "Terdeteksi" else 0
    }])
    st.session_state.df_history = pd.concat(
        [st.session_state.df_history, data_baru], ignore_index=True
    ).iloc[-20:]

    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        with st.container(border=True):
            st.markdown("#### 🌡️💧 Suhu & Kelembapan")
            st.line_chart(
                st.session_state.df_history[["Waktu", "Suhu (°C)", "Kelembapan (%)"]].set_index("Waktu"),
                color=["#D9534F", "#3B7FB9"]
            )
    with col_g2:
        with st.container(border=True):
            st.markdown("#### 💨 Kualitas Udara (PPM)")
            st.line_chart(st.session_state.df_history[["Waktu", "Gas (PPM)"]].set_index("Waktu"), color="#4A90E2")
    with col_g3:
        with st.container(border=True):
            st.markdown("#### 🏃 Pergerakan (PIR)")
            st.line_chart(st.session_state.df_history[["Waktu", "PIR"]].set_index("Waktu"), color="#e67e22")

    time.sleep(3)
    st.rerun()

# --- 6. HALAMAN LAIN ---
elif menu == "Statistik Data":
    st.title("📊 Statistik & Analisis Dataset Skripsi")
    try:
        df_train = pd.read_csv(DATASET_PATH)
        st.markdown("#### 📈 Ringkasan Data Training")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Sampel Data", f"{len(df_train)} Baris")
        with c2:
            nyala_count = len(df_train[df_train['Status_Kipas'] == 'NYALA'])
            st.metric("Kondisi Kipas NYALA", f"{nyala_count} Data", delta=f"{nyala_count/len(df_train)*100:.1f}%")
        with c3:
            mati_count = len(df_train[df_train['Status_Kipas'] == 'MATI'])
            st.metric("Kondisi Kipas MATI", f"{mati_count} Data", delta=f"-{mati_count/len(df_train)*100:.1f}%", delta_color="inverse")
        with c4:
            _model_dt, _data_ready, akurasi_holdout, n_test = train_model()
            if akurasi_holdout is not None:
                st.metric("Akurasi (Holdout Test)", f"{akurasi_holdout*100:.1f}%", help=f"Diukur dari {n_test} data uji yang tidak dilihat model saat training (train/test split 80/20).")
            else:
                st.metric("Akurasi (Holdout Test)", "N/A", help="Dataset terlalu kecil untuk displit train/test.")

        if akurasi_holdout is not None and akurasi_holdout >= 0.99:
            st.caption("⚠️ Akurasi mendekati 100% pada dataset kecil bisa jadi tanda overfitting, bukan berarti model sudah sempurna. Perlu data uji independen yang lebih besar untuk validasi lebih meyakinkan.")

        st.divider()
        st.markdown("#### 🔬 Distribusi Parameter Sensor dalam Dataset")
        tab_suhu, tab_gas, tab_pir, tab_tree = st.tabs(
            ["🌡️ Sebaran Suhu", "💨 Sebaran Gas MQ135", "🏃 Distribusi PIR", "🌳 Analisis Decision Tree"]
        )

        with tab_suhu:
            st.write("Rata-rata suhu ruangan dalam dataset berdasarkan status kipas:")
            suhu_pivot = df_train.groupby('Status_Kipas')['Suhu'].mean().reset_index()
            st.bar_chart(suhu_pivot.set_index('Status_Kipas'), color="#FF8A8A")

        with tab_gas:
            st.write("Perbandingan kadar Gas (PPM) saat kipas menyala vs mati:")
            gas_pivot = df_train.groupby('Status_Kipas')['Gas_PPM'].mean().reset_index()
            st.bar_chart(gas_pivot.set_index('Status_Kipas'), color="#4FA8FF")

        with tab_pir:
            st.write("Korelasi gerakan PIR terhadap status kipas:")
            pir_matrix = pd.crosstab(df_train['Gerakan_PIR'], df_train['Status_Kipas'])
            st.dataframe(pir_matrix, use_container_width=True)

        with tab_tree:
            model_dt, data_ready, _akurasi, _n_test = train_model()
            if data_ready:
                render_decision_tree_analysis(model_dt)
            else:
                st.error("Model belum siap — dataset tidak ditemukan.")

        st.divider()
        with st.expander("🗄️ Lihat Dataset Mentah (opsional — referensi dataset training)"):
            st.dataframe(
                df_train,
                use_container_width=True,
                column_config={
                    "Suhu": st.column_config.NumberColumn("Suhu (°C)", format="%.1f"),
                    "Kelembapan": st.column_config.NumberColumn("Kelembapan (%)", format="%.1f"),
                    "Gas_PPM": st.column_config.NumberColumn("Kadar Gas (PPM)", format="%d"),
                    "Gerakan_PIR": st.column_config.CheckboxColumn("Gerakan Terdeteksi (1/0)"),
                    "Status_Kipas": st.column_config.SelectboxColumn("Output Kipas", options=["NYALA", "MATI"])
                }
            )

            csv_data = df_train.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Dataset Skripsi (.CSV)",
                data=csv_data,
                file_name="dataset_sensor_skripsi1.csv",
                mime="text/csv",
            )
    except FileNotFoundError:
        st.error(f"⚠️ File '{DATASET_PATH}' tidak ditemukan.")

elif menu == "Status Perangkat":
    st.title("💻 Hardware & Network Diagnostics")
    col_hw1, col_hw2 = st.columns([2, 1])

    with col_hw1:
        with st.container(border=True):
            st.markdown("#### 🛠️ Live Status Komponen ESP32")
            sh1, sh2 = st.columns(2)
            with sh1:
                latency_ms, latency_status = measure_latency()
                if latency_ms is not None:
                    kualitas = "Excellent" if latency_ms < 150 else ("Lumayan" if latency_ms < 500 else "Lambat")
                    latency_display = f"`{latency_ms} ms` ({kualitas})"
                else:
                    latency_display = f"`Gagal diukur` ({latency_status})"

                firebase_connected = latency_ms is not None
                status_label = "<span style='color:#2ECC71; font-weight:bold;'>CONNECTED</span>" if firebase_connected else "<span style='color:#E74C3C; font-weight:bold;'>DISCONNECTED</span>"
                st.markdown(f"""
                **📡 Jaringan & Basis Data**
                - Status Firebase: {status_label}
                - Latency Terhitung: {latency_display}
                - Protokol: HTTPS REST API
                """, unsafe_allow_html=True)
                st.caption("Latency diukur real-time saat halaman ini dibuka (ping request ke Firebase).")
                if status_sistem == "ONLINE":
                    st.success("🟢 CORE SYSTEM: ESP32 IS ALIVE")
                else:
                    st.error(f"🔴 CORE SYSTEM: {status_sistem}")

            with sh2:
                st.markdown(f"""
                **🔌 Kondisi Aktuator (Relay)**
                - Kipas Angin: `Decision Tree Auto Control`
                - Buzzer Alarm: `Rule-Based Safety Layer`
                - Status Alarm: {"<span style='color:red;font-weight:bold;'>SIAGA (ARMED)</span>" if mode_keamanan else "<span style='color:gray;'>MATI (DISARMED)</span>"}
                """, unsafe_allow_html=True)

        with st.expander("🧪 Testing Manual Perangkat (Developer Only — di luar alur monitoring)"):
            st.caption("Bagian ini buat ngetes hardware secara manual, bukan bagian dari pipeline monitoring/otomatisasi.")
            ct1, ct2 = st.columns(2)
            with ct1:
                if st.button("🔥 Test Nyalakan Buzzer (5 Detik)"):
                    try:
                        requests.patch(f"{FIREBASE_URL}Control_Perangkat.json", json={"Buzzer_Test": "ON"}, timeout=3)
                        st.toast("Perintah test buzzer dikirim!", icon="🔔")
                    except Exception: st.error("Gagal terhubung ke Firebase.")
            with ct2:
                if st.button("❄️ Reset Semua Output Sakelar"):
                    try:
                        requests.patch(f"{FIREBASE_URL}Control_Perangkat.json", json={"Kipas": "MATI", "Mode_Amap": "OFF"}, timeout=3)
                        st.toast("Semua sakelar di-reset ke kondisi default.", icon="🔄")
                    except Exception: pass

    with col_hw2:
        with st.container(border=True):
            st.markdown("#### 📐 Alokasi Pin ESP32")
            st.markdown("""
            | Komponen | Tipe Pin | Nomor Pin |
            |---|---|---|
            | **DHT11 (Suhu)** | Input | `GPIO 23` |
            | **MQ135 (Gas)** | Analog | `VP (GPIO 36)` |
            | **PIR (Motion)**| Digital| `GPIO 19` |
            | **Relay Kipas** | Output | `GPIO 25` |
            | **Buzzer** | Output | `GPIO 26` |
            """)

            st.info("Konfigurasi pin dicocokkan dengan skema rangkaian PCB skripsi.")
        with st.container(border=True):
            st.markdown("### 🏗️ Arsitektur Sistem")
            st.markdown("""
            | Komponen | Peran |
            |---|---|
            | 🧠 **Decision Tree C4.5** | Kontrol **Kipas** |
            | 🛡️ **Rule-based lokal** | Kontrol **Buzzer** |
            """)
            st.caption("Buzzer tetap bunyi walau internet mati (safety layer).")


elif menu == "Log Aktivitas":
    st.title("📝 Log Aktivitas (Sesi Ini)")
    st.caption("⚠️ Log ini hanya tersimpan sementara di sesi browser saat ini — menampilkan maksimal 20 entri terakhir dan akan hilang jika halaman di-reload atau server di-restart. Ini bukan penyimpanan permanen/database log.")
    with st.container(border=True):
        if not st.session_state.df_history.empty:
            log_display = st.session_state.df_history.copy()
            log_display["Tingkat Bahaya"] = log_display.apply(
                lambda r: "🚨 BAHAYA" if r["Gas (PPM)"] > st.session_state.thresh_gas or r["Suhu (°C)"] > st.session_state.thresh_suhu else "✅ AMAN",
                axis=1
            )
            log_display = log_display.iloc[::-1]
            st.dataframe(
                log_display,
                use_container_width=True,
                column_config={
                    "Waktu": st.column_config.TextColumn("🕒 Waktu Log"),
                    "Suhu (°C)": st.column_config.NumberColumn("🌡️ Suhu", format="%.1f °C"),
                    "Kelembapan (%)": st.column_config.NumberColumn("💧 Lembab", format="%.1f %%"),
                    "Gas (PPM)": st.column_config.NumberColumn("💨 Gas CO", format="%d PPM"),
                    "PIR": st.column_config.NumberColumn("🏃 Gerakan PIR"),
                    "Tingkat Bahaya": st.column_config.SelectboxColumn("🛡️ Status Ruangan", options=["✅ AMAN", "🚨 BAHAYA"])
                }
            )
        else:
            st.info("Belum ada log aktivitas tercatat.")

        if st.button("🗑️ Bersihkan Riwayat Log"):
            st.session_state.df_history = pd.DataFrame(columns=["Waktu", "Suhu (°C)", "Kelembapan (%)", "Gas (PPM)", "PIR"])
            st.rerun()

elif menu == "Pengaturan":
    st.title("⚙️ Konfigurasi Threshold")
    with st.container(border=True):
        st.session_state.thresh_suhu = st.slider("Batas Suhu Panas (°C)", 20, 40, st.session_state.thresh_suhu)
        st.session_state.thresh_gas = st.slider("Batas Aman Gas MQ135 (PPM)", 100, 800, st.session_state.thresh_gas)
        st.divider()
        st.info("""
        **Catatan Arsitektur:**
        - Threshold di sini hanya memengaruhi visualisasi warna alur.
        - Keputusan logika kipas dikendalikan model AI hasil training dataset C4.5.
        """)
        if st.button("Simpan & Terapkan"):
            st.success("✅ Threshold visualisasi diperbarui!")
