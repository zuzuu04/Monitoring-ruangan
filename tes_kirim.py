import pyrebase
import time

# Pakai config rahasia Firebase lo
firebase_config = {
    "apiKey": "AIzaSyCh6ujc-Ohcmv5dcogqZojBc_RB6gN3en8",
    "authDomain": "monitoringruangan-16163.firebaseapp.com",
    "databaseURL": "https://monitoringruangan-16163-default-rtdb.asia-southeast1.firebasedatabase.app",
    "projectId": "monitoringruangan-16163",
    "storageBucket": "monitoringruangan-16163.firebasestorage.app",
    "messagingSenderId": "466767575118",
    "appId": "1:466767575118:web:30d63345df49c1f116b1f"
}

firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

print("🚀 Memulai simulasi pengiriman data ESP32 ke Firebase...")

# Kita suntik data ekstrim: Suhu panas banget dan ada orang!
data_palsu = {
    "Suhu": 35.8,
    "Kelembapan": 75.0,
    "Gas_PPM": 250.0,
    "Gerakan_PIR": 1
}

try:
    db.child("Data_Sensor").set(data_palsu)
    print("✅ DATA BERHASIL DIKIRIM! Coba cek web Firebase dan Streamlit lo sekarang!")
except Exception as e:
    print(f"❌ Gagal ngirim karena: {e}")