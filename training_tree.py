import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.tree import export_text
from sklearn import tree
import matplotlib.pyplot as plt

# 1. Baca dataset lo yang udah bersih
file_nama = "data/dataset_sensor_skripsi.csv"
df = pd.read_csv(file_nama)

# 2. Pisahkan Fitur (X) dan Target/Label (Y)
# Kita pakai kolom Gas_PPM dan Gerakan_PIR buat memprediksi Status_Kipas
X = df[['Gas_PPM', 'Gerakan_PIR']]
Y = df['Status_Kipas']

# 3. Buat dan Latih Model Decision Tree (C4.5 / Gini)
# Kita batasi max_depth=3 biar pohonnya simpel dan gak ribet dibaca dosen
model_tree = DecisionTreeClassifier(criterion='entropy', max_depth=3, random_state=42)
model_tree.fit(X, Y)

# 4. Cetak Aturan Pohon Keputusan dalam Bentuk Teks di Terminal
print("\n=== 🔥 STRUKTUR POHON KEPUTUSAN BARU LO, NES! ===")
aturan_pohon = export_text(model_tree, feature_names=['Gas_PPM', 'Gerakan_PIR'])
print(aturan_pohon)
print("==================================================\n")

# 5. BONUS: Simpan pohonnya jadi gambar biar bisa lo pajang di bab 4 skripsi lo
plt.figure(figsize=(10,6))
tree.plot_tree(model_tree, feature_names=['Gas_PPM', 'Gerakan_PIR'], class_names=model_tree.classes_, filled=True, rounded=True)
plt.savefig('pohon_keputusan_baru.png', dpi=300)
print("📸 Gambar pohon keputusan baru udah disimpan dengan nama 'pohon_keputusan_baru.png'!")