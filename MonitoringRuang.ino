#include <WiFi.h>
#include <FirebaseESP32.h>
#include <DHT.h>
#include <WiFiUdp.h>
#include <NTPClient.h>

// --- Konfigurasi ---
#define WIFI_SSID "Bergas"
#define WIFI_PASSWORD "bergasH520"
#define FIREBASE_HOST "https://monitoringruangan-16163-default-rtdb.asia-southeast1.firebasedatabase.app/"
#define FIREBASE_AUTH "FvmMgAeh9zOQ9MbABs9CIpN2ATpBUFyHm6qREql0"

// --- Pin Definisi ---
#define DHTPIN 4
#define DHTTYPE DHT22
#define MQ135_PIN 34
#define PIR_PIN 13
#define RELAY_PIN 32
#define BUZZER_PIN 27

// --- Threshold Alarm ---
// PENTING: Samakan angka ini dengan slider "Pengaturan" di Streamlit (thresh_gas, thresh_suhu)
// supaya kondisi kipas (dikontrol AI via Firebase) & buzzer (dikontrol lokal di sini) konsisten.
#define GAS_THRESHOLD 366
#define SUHU_THRESHOLD 32.0

DHT dht(DHTPIN, DHTTYPE);
FirebaseData fbdo;
FirebaseConfig config;
FirebaseAuth auth;

WiFiUDP ntpUDP; 
NTPClient timeClient(ntpUDP, "pool.ntp.org", 25200);

unsigned long prevMillis = 0;
const long interval = 2000;

// Variabel tambahan untuk menampung status kontrol dari Firebase
String statusKipas = "MATI";
String statusModeAman = "OFF"; 

void setup() {
  Serial.begin(115200);
  
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  
  // Posisi awal: Relay Active LOW (LOW = NYALA, HIGH = MATI)
  // Set HIGH dulu di awal supaya relay dalam kondisi MATI saat boot
  digitalWrite(RELAY_PIN, HIGH); 
  digitalWrite(BUZZER_PIN, LOW);

  dht.begin();
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi Terkoneksi!");

  config.database_url = FIREBASE_HOST;
  config.signer.tokens.legacy_token = FIREBASE_AUTH;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  timeClient.begin();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) return;

  unsigned long currentMillis = millis();
  if (currentMillis - prevMillis >= interval) {
    prevMillis = currentMillis;

    // --- REVISI 2: Ambil waktu epoch terbaru dari internet sebelum dikirim ---
    timeClient.update();
    unsigned long waktuSekarang = timeClient.getEpochTime();

    // 1. Baca Sensor Real
    int gas = analogRead(MQ135_PIN);
    int motion = digitalRead(PIR_PIN);
    float suhu_raw = dht.readTemperature();
    float hum = dht.readHumidity();

    // 2. Kalibrasi Suhu (Offset 6 derajat agar tidak terpengaruh panas komponen)
    float suhu = isnan(suhu_raw) ? 0.0 : (suhu_raw - 6.0);
    if (isnan(hum)) hum = 0.0;

    // Debugging di Serial Monitor
    Serial.printf("Gas: %d | PIR: %d | Suhu: %.2fC | Hum: %.2f%%\n", gas, motion, suhu, hum);

    // 3. Kirim Data Sensor ke Firebase
    if (Firebase.ready()) {
      Firebase.setInt(fbdo, "/Data_Sensor/Gas_PPM", gas);
      Firebase.setInt(fbdo, "/Data_Sensor/Gerakan_PIR", motion);
      Firebase.setFloat(fbdo, "/Data_Sensor/Suhu", suhu);
      Firebase.setFloat(fbdo, "/Data_Sensor/Kelembapan", hum);
      
      // --- REVISI 3: Mengubah ke setInt, variabel waktuSekarang, dan folder Last_Seen ---
      Firebase.setInt(fbdo, "/Data_Sensor/Last_Seen", waktuSekarang); 

      // 4. Ambil Status Kontrol Kipas dari Firebase
      if (Firebase.getString(fbdo, "/Control_Perangkat/Kipas")) {
        statusKipas = fbdo.stringData();
      }

      // 5. Ambil Status Mode Keamanan Maling dari Firebase
      if (Firebase.getString(fbdo, "/Control_Perangkat/Mode_Aman")) {
        statusModeAman = fbdo.stringData();
      }
    }

    // 6. Eksekusi Kontrol Kipas (Relay Aktif LOW: LOW = NYALA, HIGH = MATI)
    if (statusKipas == "NYALA") {
      digitalWrite(RELAY_PIN, LOW); 
    } else {
      digitalWrite(RELAY_PIN, HIGH);
    }

    // 7. Logika Gabungan Multi-Tier Alarm Buzzer
    //    Tier 1 (tertinggi) : DARURAT     -> Mode Aman ON + Gerakan + (Gas bahaya ATAU Suhu tinggi) bersamaan
    //    Tier 2              : Gas Bocor   -> Gas > GAS_THRESHOLD (berlaku kapan saja, prioritas di atas alarm maling biasa)
    //    Tier 3              : Penyusup    -> Mode Aman ON + Gerakan, TANPA bahaya lingkungan
    //    Catatan: Suhu tinggi SENDIRIAN (tanpa gerakan+mode aman) sengaja TIDAK membunyikan buzzer,
    //    cukup kipas menyala + notifikasi di Streamlit, karena suhu tinggi bisa jadi kondisi wajar (siang hari panas).
    bool gasBahaya    = (gas > GAS_THRESHOLD);
    bool suhuTinggi   = (suhu > SUHU_THRESHOLD);
    bool pirAktif     = (motion == HIGH);
    bool modeAmanOn   = (statusModeAman == "ON");

    if (modeAmanOn && pirAktif && (gasBahaya || suhuTinggi)) {
      Serial.println("ALARM: DARURAT! Gerakan + Bahaya Lingkungan saat rumah kosong!");
      // Pola darurat: 3x beep cepat lalu jeda -> beda dari 2 pola lain biar gampang dibedain kupingnya
      for (int i = 0; i < 3; i++) {
        digitalWrite(BUZZER_PIN, HIGH);
        delay(80);
        digitalWrite(BUZZER_PIN, LOW);
        delay(80);
      }
      delay(300);
    }
    else if (gasBahaya) {
      Serial.println("ALARM: Gas Bahaya Terdeteksi!");
      // Bunyi putus-putus cepat (Beep... Beep...)
      digitalWrite(BUZZER_PIN, HIGH);
      delay(150);
      digitalWrite(BUZZER_PIN, LOW);
      delay(150);
    }
    else if (modeAmanOn && pirAktif) {
      Serial.println("ALARM: Penyusup Terdeteksi!");
      // Bunyi konstan panjang menakuti maling (Breeeeeep)
      digitalWrite(BUZZER_PIN, HIGH);
    }
    else {
      digitalWrite(BUZZER_PIN, LOW);
    }
  }
}
