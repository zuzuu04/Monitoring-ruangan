import pandas as pd

# 1. Baca file dataset lo yang masih "salah paham" tadi
file_nama = "dataset_sensor_skripsi.csv"
df = pd.read_csv(file_nama)

# 2. LOGIKA OTOMATIS: 
# Kalau Gas di bawah 300 PPM, ubah Status_Kipas jadi MATI (Kondisi Kamar Normal)
# Kalau Gas di atas 300 PPM, biarkan tetap NYALA (Kondisi Gas Bocor/Asap)
df.loc[df['Gas_PPM'] <= 300, 'Status_Kipas'] = 'MATI'
df.loc[df['Gas_PPM'] > 300, 'Status_Kipas'] = 'NYALA'

# 3. Simpan balik ke file CSV
df.to_csv(file_nama, index=False)

print("⚡ BOOM! 200 data udah bersih otomatis tanpa gempor, Nes! Coba cek file CSV lo.")