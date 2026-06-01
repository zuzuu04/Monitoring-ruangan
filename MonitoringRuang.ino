#include <WiFi.h>
#include <FirebaseESP32.h>
#include <DHT.h>

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
#define RELAY_PIN 26
#define BUZZER_PIN 27

DHT dht(DHTPIN, DHTTYPE);
FirebaseData fbdo;
FirebaseConfig config;
FirebaseAuth auth;

unsigned long prevMillis = 0;
const long interval = 2000;

void setup() {
  Serial.begin(115200);
  
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  
  // Posisi awal: Relay Active LOW (HIGH = MATI)
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
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) return;

  unsigned long currentMillis = millis();
  if (currentMillis - prevMillis >= interval) {
    prevMillis = currentMillis;

    // 1. Baca Sensor Real
    int gas = analogRead(MQ135_PIN);
    int motion = digitalRead(PIR_PIN);
    float suhu_raw = dht.readTemperature();
    float hum = dht.readHumidity();

    // 2. Kalibrasi Suhu (Offset 6 derajat agar tidak terpengaruh panas komponen)
    // Gunakan isnan untuk cek jika sensor gagal membaca
    float suhu = isnan(suhu_raw) ? 0.0 : (suhu_raw - 6.0);
    if (isnan(hum)) hum = 0.0;

    // Debugging di Serial Monitor
    Serial.printf("Gas: %d | PIR: %d | Suhu: %.2fC | Hum: %.2f%%\n", gas, motion, suhu, hum);

    // 3. Logika Buzzer (Gerak = Bunyi)
    if (motion == HIGH) {
      digitalWrite(BUZZER_PIN, HIGH);
    } else {
      digitalWrite(BUZZER_PIN, LOW);
    }

    // 4. Kirim ke Firebase
    if (Firebase.ready()) {
      Firebase.setInt(fbdo, "/Data_Sensor/Gas_PPM", gas);
      Firebase.setInt(fbdo, "/Data_Sensor/Gerakan_PIR", motion);
      Firebase.setFloat(fbdo, "/Data_Sensor/Suhu", suhu);
      Firebase.setFloat(fbdo, "/Data_Sensor/Kelembapan", hum);

      // 5. Kontrol Kipas
      if (Firebase.getString(fbdo, "/Control_Perangkat/Kipas")) {
        if (fbdo.stringData() == "NYALA") {
          digitalWrite(RELAY_PIN, LOW); // Relay Aktif LOW
        } else {
          digitalWrite(RELAY_PIN, HIGH);
        }
      }
    }
  }
}