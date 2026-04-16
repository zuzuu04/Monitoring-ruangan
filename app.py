import streamlit as st

st.title("Monitoring IoT Skripsi")
st.write("Halo! Ini dashboard monitoring suhu dan kelembapan.")

suhu = st.slider("Simulasi Input Suhu", 0, 50, 25)
st.write(f"Suhu saat ini: {suhu}°C")