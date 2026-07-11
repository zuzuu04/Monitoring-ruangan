"""
Fungsi-fungsi bantu untuk Dashboard Monitoring Room:
- kirim_notif_telegram : kirim notifikasi ke Telegram
- measure_latency      : ukur latency asli ke Firebase (bukan angka statis)
- train_model          : training Decision Tree C4.5 + hitung akurasi jujur via holdout test set
- render_alur_dt       : render visual alur SUHU -> LEMBAP -> GAS -> PIR
- render_decision_tree_analysis : render grafik pohon + aturan interaktif
"""

import requests
import time
import pandas as pd
import streamlit as st
from sklearn.tree import DecisionTreeClassifier, _tree, export_graphviz
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DATASET_PATH, FIREBASE_URL


def kirim_notif_telegram(pesan: str):
    """Kirim pesan notifikasi ke Telegram. Gagal diam-diam kalau offline."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=3)
    except Exception:
        pass


def measure_latency():
    """
    Ukur latency beneran ke Firebase dengan ping request kecil.
    Return: (latency_ms: int | None, status: str)
    """
    try:
        t0 = time.perf_counter()
        r = requests.get(f"{FIREBASE_URL}Data_Sensor.json", timeout=5)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        if r.status_code == 200:
            return latency_ms, "OK"
        return latency_ms, f"HTTP {r.status_code}"
    except Exception:
        return None, "TIMEOUT/ERROR"


@st.cache_resource
def train_model():
    """
    Training Decision Tree C4.5 dari dataset skripsi.
    Model final di-fit ke SELURUH data (dipakai untuk prediksi live).
    Akurasi yang dilaporkan dihitung dari train/test split terpisah (80/20)
    supaya jujur merepresentasikan performa di data yang belum pernah dilihat model,
    bukan skor "menghafal" data training itu sendiri.

    Di-cache (st.cache_resource) supaya nggak retrain ulang tiap auto-refresh.
    Return: (model, data_ready: bool, akurasi_holdout: float | None, n_test: int)
    """
    try:
        df = pd.read_csv(DATASET_PATH)
        X = df[['Suhu', 'Kelembapan', 'Gas_PPM', 'Gerakan_PIR']]
        y = df['Status_Kipas']

        akurasi_holdout = None
        n_test = 0
        # Evaluasi jujur pakai data yang disisihkan (kalau datanya cukup buat displit)
        if len(df) >= 10:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None
            )
            eval_model = DecisionTreeClassifier(criterion='entropy', max_depth=3, random_state=42)
            eval_model.fit(X_train, y_train)
            akurasi_holdout = accuracy_score(y_test, eval_model.predict(X_test))
            n_test = len(X_test)

        # Model final dipakai untuk prediksi live: di-fit ke semua data yang ada
        model = DecisionTreeClassifier(criterion='entropy', max_depth=3, random_state=42)
        model.fit(X, y)
        return model, True, akurasi_holdout, n_test
    except FileNotFoundError:
        return None, False, None, 0


def render_alur_dt(s, l, g, p, thresh_suhu, thresh_gas):
    """Render kartu alur SUHU -> LEMBAP -> GAS -> PIR dengan status warna."""
    st_suhu = "NORMAL" if s <= thresh_suhu else "PANAS"
    st_lembab = "NORMAL" if l <= 70 else "LEMBAP"
    st_gas = "AMAN" if g <= thresh_gas else "BAHAYA"
    st_pir = "ADA ORANG" if p == "Terdeteksi" else "KOSONG"

    c_suhu = "#475569" if st_suhu == "NORMAL" else "#E74C3C"
    c_lembab = "#334156" if st_lembab == "NORMAL" else "#E74C3C"
    c_gas = "#0F766E" if st_gas == "AMAN" else "#E74C3C"
    c_pir = "#64748B" if st_pir == "KOSONG" else "#D35400"

    lbl_suhu = "#A7F3D0" if st_suhu == "NORMAL" else "#FFD2D2"
    lbl_lembab = "#A7F3D0" if st_lembab == "NORMAL" else "#FFD2D2"
    lbl_gas = "#A7F3D0" if st_gas == "AMAN" else "#FFD2D2"
    lbl_pir = "#E2E8F0" if st_pir == "KOSONG" else "#FFE3D1"

    cls_gas = "step-box danger-pulse" if st_gas == "BAHAYA" else "step-box"
    cls_suhu = "step-box danger-pulse" if st_suhu == "PANAS" else "step-box"

    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin:20px 0;flex-wrap:wrap;">
        <div class="{cls_suhu}"   style="background:{c_suhu};">SUHU<small style="color:{lbl_suhu};">→ {st_suhu}</small></div>
        <div class="arrow">➤</div>
        <div class="step-box"    style="background:{c_lembab};">LEMBAP<small style="color:{lbl_lembab};">→ {st_lembab}</small></div>
        <div class="arrow">➤</div>
        <div class="{cls_gas}"     style="background:{c_gas};">GAS<small style="color:{lbl_gas};">→ {st_gas}</small></div>
        <div class="arrow">➤</div>
        <div class="step-box"    style="background:{c_pir};">PIR<small style="color:{lbl_pir};">→ {st_pir}</small></div>
    </div>
    """, unsafe_allow_html=True)


def render_decision_tree_analysis(model_dt):
    """Render grafik pohon (graphviz) + aturan interaktif dari model Decision Tree."""
    st.markdown("#### 📊 Visualisasi Decision Tree C4.5")
    with st.container(border=True):
        dot_str = export_graphviz(
            model_dt,
            out_file=None,
            feature_names=['Suhu', 'Kelembapan', 'Gas_PPM', 'PIR'],
            class_names=model_dt.classes_,
            filled=True,
            rounded=True,
            special_characters=True,
            impurity=False
        )
        dot_str = dot_str.replace('fillcolor="#e58139"', 'fillcolor="#FFE6CC" style="filled,rounded" color="#D3D3D3"')
        dot_str = dot_str.replace('fillcolor="#399de5"', 'fillcolor="#E6F2FF" style="filled,rounded" color="#D3D3D3"')
        st.graphviz_chart(dot_str, use_container_width=True)

    st.markdown("#### 📜 Aturan Decision Tree (Klik Expand untuk Membuka Alur)")
    with st.container(border=True):
        def recurse(tree_, feature_name, node, depth):
            if tree_.feature[node] != _tree.TREE_UNDEFINED:
                name = feature_name[node]
                threshold = tree_.threshold[node]

                with st.expander(f"{'  ' * depth}🔹 JIKA {name} ≤ {threshold:.2f}"):
                    recurse(tree_, feature_name, tree_.children_left[node], depth + 1)

                with st.expander(f"{'  ' * depth}🔸 JIKA {name} > {threshold:.2f}"):
                    recurse(tree_, feature_name, tree_.children_right[node], depth + 1)
            else:
                value = tree_.value[node]
                ind = value.argmax()
                kelas = model_dt.classes_[ind]
                badge = "🟢 NYALA" if kelas == "NYALA" else "🔴 MATI"
                st.markdown(f"{'  ' * depth} ➔ 🚪 KIPAS : **{badge}**")

        feature_names = ['Suhu (°C)', 'Kelembapan (%)', 'Gas (PPM)', 'PIR']
        tree_ = model_dt.tree_
        feature_name = [
            feature_names[i] if i != _tree.TREE_UNDEFINED else "undefined!"
            for i in tree_.feature
        ]
        recurse(tree_, feature_name, 0, 0)