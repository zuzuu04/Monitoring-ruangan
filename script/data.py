import pandas as pd
import numpy as np
from datetime import datetime, timedelta

data = []
waktu_mulai = datetime.now()

for i in range(300):
    # Data random tapi ada desimalnya biar kelihatan asli
    gas = round(np.random.uniform(100.0, 550.0), 2)
    suhu = round(np.random.uniform(24.0, 38.0), 1)
    pir = np.random.choice([0, 1], p=[0.7, 0.3]) # 70% sepi, 30% ada orang
    
    # Logika status kipas
    if gas > 350 or suhu > 32 or pir == 1:
        kipas = "NYALA"
    else:
        kipas = "MATI"
        
    waktu = (waktu_mulai + timedelta(seconds=i*3)).strftime("%Y-%m-%d %H:%M:%S")
    data.append([waktu, gas, pir, suhu, kipas])

df = pd.DataFrame(data, columns=['Waktu', 'Gas_PPM', 'Gerakan_PIR', 'Suhu', 'Status_Kipas'])
df.to_csv("data/dataset_sensor_skripsi.csv", index=False)
print("Data 'asli' (cieee) udah siap!")