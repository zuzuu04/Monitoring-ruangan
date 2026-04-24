import streamlit as st
import pandas as pd
import time
from streamlit_option_menu import option_menu

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Monitoring Ruangan", layout="wide")

# --- 2. CUSTOM CSS ---
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

# --- 3. FUNGSI ALUR DECISION TREE ---
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

# --- 4. SIDEBAR ---
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

# --- 5. MOCKUP DATA ---
suhu, kelembapan, gas_co = 26.5, 55, 120
gerakan, status_sistem = "Terdeteksi", "ONLINE"

# --- 6. LOGIKA HALAMAN ---
if menu == "Dashboard Utama":
    st.title("🏠 Dashboard Monitoring")
    st.subheader("Implementasi Decision Tree C4.5")
    
    col1, col2 = st.columns([1, 2.3])
    
    with col1:
        with st.container(border=True):
            st.markdown("### 📡 Status Sistem")
            st.metric(label="Konektivitas", value=status_sistem, delta="Normal")
            st.caption(f"Update: {time.strftime('%H:%M:%S')} WIB")

    with col2:
        with st.container(border=True):
            st.markdown("### 🧠 Proses Prediksi Decision Tree (C4.5)")
            render_alur_dt(suhu, kelembapan, gas_co, gerakan)
            if suhu <= 30 and gas_co <= 200:
                st.success("✅ STATUS: RUANGAN AMAN / NYAMAN")
            else:
                st.error("⚠️ STATUS: RUANGAN BAHAYA / TIDAK NYAMAN")

    st.divider()

    st.write("### 📡 Parameter Sensor Real-Time")
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
        chart_data = pd.DataFrame({"Waktu": ["1h", "2h", "3h", "4h", "5h", "6h"], "Suhu": [24, 25, 26, 25.5, 26, 26.5]})
        st.line_chart(chart_data.set_index("Waktu"))

# --- MENU LAIN ---
elif menu == "Statistik Data":
    st.title("📊 Statistik & History")
    with st.container(border=True):
        st.write("Database hasil record sensor.")
        st.table(pd.DataFrame({"Waktu": ["14:30"], "Suhu": [26.5], "Prediksi": ["Aman"]}))

elif menu == "Status Perangkat":
    st.title("💻 Hardware Monitoring")
    with st.container(border=True):
        st.json({"Device": "ESP32", "IP": "192.168.1.7", "RSSI": "-65 dBm"})

elif menu == "Log Aktivitas":
    st.title("📝 Activity Logs")
    with st.container(border=True):
        st.code("14:30:05 - Gas Tinggi - Relay ON")

elif menu == "Pengaturan":
    st.title("⚙️ Konfigurasi Threshold")
    with st.container(border=True):
        st.slider("Batas Suhu Panas (°C)", 20, 40, 30)
        st.button("Simpan Perubahan")
