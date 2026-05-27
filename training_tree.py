import pandas as pd
from sklearn.tree import DecisionTreeClassifier, plot_tree
import matplotlib.pyplot as plt

# 1. Load data
df = pd.read_csv("data/dataset_sensor_skripsi.csv")

# 2. Pastikan tipe datanya angka semua
df['Gas_PPM'] = pd.to_numeric(df['Gas_PPM'])
df['Gerakan_PIR'] = pd.to_numeric(df['Gerakan_PIR'])
df['Suhu'] = pd.to_numeric(df['Suhu'])

# 3. Definisikan fitur dan target
X = df[['Gas_PPM', 'Gerakan_PIR', 'Suhu']]
Y = df['Status_Kipas']

# 4. Training Model
model = DecisionTreeClassifier(criterion='entropy', max_depth=3, random_state=42)
model.fit(X, Y)

# 5. Visualisasi
plt.figure(figsize=(15, 10)) # Ukuran gambar lebih gede biar kebaca
plot_tree(model, 
          feature_names=['Gas_PPM', 'Gerakan_PIR', 'Suhu'], 
          class_names=['MATI', 'NYALA'], 
          filled=True, 
          rounded=True)

plt.title("Visualisasi Pohon Keputusan (Decision Tree)")
plt.savefig('DecicionTree.png', dpi=300) # Simpan dengan kualitas tinggi
print("✅ Pohon keputusan sudah jadi di file 'DecicionTree.png'!")
