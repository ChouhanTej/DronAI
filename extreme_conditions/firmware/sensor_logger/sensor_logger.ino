/*
  Extreme Conditions Failure Prediction - Sensor Logger Firmware
  Target Hardware: ESP32 Dev Module (ESP32-D0WD-V3)
  
  Sensors & Pin Mapping:
  - DHT11 Temperature & Humidity Sensor:
      VCC -> ESP32 3V3
      GND -> ESP32 GND
      OUT -> ESP32 D4 (GPIO 4)
  
  - MPU6050 / MPU6500 / GY-521 Motion Sensor:
      VCC -> ESP32 3V3
      GND -> ESP32 GND
      SDA -> ESP32 D21 (GPIO 21)
      SCL -> ESP32 D22 (GPIO 22)
  
  Required Arduino Libraries:
  1. "DHT sensor library" by Adafruit
  2. "Adafruit Unified Sensor" by Adafruit
*/

#include <Wire.h>
#include <DHT.h>

// Pin Definitions
#define DHTPIN 4         // DHT11 Data Pin connected to ESP32 GPIO 4
#define DHTTYPE DHT11    // DHT sensor model

#define SDA_PIN 21       // I2C Data Pin (ESP32 D21)
#define SCL_PIN 22       // I2C Clock Pin (ESP32 D22)

// Sampling Interval (ms)
#define SAMPLE_INTERVAL_MS 1000

// MPU6050 / MPU6500 I2C Register Addresses
#define MPU_REG_CONFIG       0x1A
#define MPU_REG_GYRO_CONFIG  0x1B
#define MPU_REG_ACCEL_CONFIG 0x1C
#define MPU_REG_ACCEL_XOUT_H 0x3B
#define MPU_REG_PWR_MGMT_1   0x6B
#define MPU_REG_WHO_AM_I     0x75

// Hardware Instances & State
DHT dht(DHTPIN, DHTTYPE);
uint8_t mpuAddr = 0x68;
bool mpuReady = false;
unsigned long lastSampleTime = 0;

// Helper: Write 1 byte to MPU I2C register
bool writeMPURegister(uint8_t reg, uint8_t data) {
  Wire.beginTransmission(mpuAddr);
  Wire.write(reg);
  Wire.write(data);
  return (Wire.endTransmission() == 0);
}

// Helper: Read single byte register from MPU
uint8_t readMPURegister(uint8_t reg) {
  Wire.beginTransmission(mpuAddr);
  Wire.write(reg);
  Wire.endTransmission(false);
  if (Wire.requestFrom(mpuAddr, (uint8_t)1)) {
    return Wire.read();
  }
  return 0x00;
}

void setup() {
  // 1. Initialize Serial Communication at 115200 baud
  Serial.begin(115200);
  delay(1000); // Give UART driver time to stabilize after ESP32 boot
  Serial.println();
  Serial.println("==================================================");
  Serial.println(" ESP32 Sensor Logger - Booting Hardware");
  Serial.println("==================================================");

  // 2. Initialize I2C bus with SDA=D21 and SCL=D22
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setTimeOut(1000); // 1-second timeout to prevent I2C hang

  // 3. Scan I2C bus to find MPU sensor address
  byte error;
  int nDevices = 0;
  Serial.println("Scanning I2C bus (SDA=D21, SCL=D22)...");
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    error = Wire.endTransmission();
    if (error == 0) {
      Serial.print(" -> Found I2C device at address 0x");
      if (addr < 16) Serial.print("0");
      Serial.println(addr, HEX);
      if (addr == 0x68 || addr == 0x69) {
        mpuAddr = addr;
        nDevices++;
      }
    }
  }

  if (nDevices == 0) {
    Serial.println("ERROR: MPU sensor not detected on I2C bus!");
    Serial.println("Please check SDA(D21), SCL(D22), 3V3, and GND wiring.");
    while (1) {
      delay(1000);
    }
  }

  // 4. Wake up MPU sensor (clear SLEEP bit in PWR_MGMT_1)
  writeMPURegister(MPU_REG_PWR_MGMT_1, 0x00);
  delay(100);

  // Read WHO_AM_I chip ID
  uint8_t whoAmI = readMPURegister(MPU_REG_WHO_AM_I);
  Serial.print(" -> Sensor WHO_AM_I (0x75) = 0x");
  if (whoAmI < 16) Serial.print("0");
  Serial.println(whoAmI, HEX);

  if (whoAmI == 0x68) {
    Serial.println("SUCCESS: Detected MPU-6050 chip.");
  } else if (whoAmI == 0x70) {
    Serial.println("SUCCESS: Detected MPU-6500 chip (fully compatible).");
  } else if (whoAmI == 0x71 || whoAmI == 0x73) {
    Serial.println("SUCCESS: Detected MPU-9250 motion sensor chip.");
  } else {
    Serial.print("SUCCESS: Motion sensor detected at 0x");
    Serial.println(mpuAddr, HEX);
  }

  // Configure MPU measurement parameters:
  // Accel ±8g range (4096 LSB/g) -> register 0x1C = 0x10
  writeMPURegister(MPU_REG_ACCEL_CONFIG, 0x10);
  // Gyro ±500 dps range (65.5 LSB/dps) -> register 0x1B = 0x08
  writeMPURegister(MPU_REG_GYRO_CONFIG, 0x08);
  // Digital Low Pass Filter ~42Hz -> register 0x1A = 0x03
  writeMPURegister(MPU_REG_CONFIG, 0x03);

  mpuReady = true;

  // 5. Initialize DHT11 Sensor
  dht.begin();
  Serial.println("SUCCESS: DHT11 initialized.");

  // Allow sensors to stabilize
  delay(1000);

  // 6. Print CSV Header ONCE over Serial
  Serial.println("--------------------------------------------------");
  Serial.println("timestamp_ms,temperature_c,humidity_percent,accel_x_g,accel_y_g,accel_z_g,gyro_x_dps,gyro_y_dps,gyro_z_dps");
}

void loop() {
  unsigned long currentMillis = millis();

  // Non-blocking 1-second sample loop
  if (currentMillis - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = currentMillis;

    // Read DHT11 Temperature (°C) and Humidity (%)
    float tempC = dht.readTemperature();
    float humPct = dht.readHumidity();

    // Read MPU Motion Sensor (14 raw bytes starting at 0x3B)
    float accelX = 0.0, accelY = 0.0, accelZ = 0.0;
    float gyroX = 0.0, gyroY = 0.0, gyroZ = 0.0;

    if (mpuReady) {
      Wire.beginTransmission(mpuAddr);
      Wire.write(MPU_REG_ACCEL_XOUT_H);
      Wire.endTransmission(false);

      if (Wire.requestFrom(mpuAddr, (uint8_t)14) == 14) {
        int16_t rawAx = (Wire.read() << 8) | Wire.read();
        int16_t rawAy = (Wire.read() << 8) | Wire.read();
        int16_t rawAz = (Wire.read() << 8) | Wire.read();
        int16_t rawTemp = (Wire.read() << 8) | Wire.read();
        int16_t rawGx = (Wire.read() << 8) | Wire.read();
        int16_t rawGy = (Wire.read() << 8) | Wire.read();
        int16_t rawGz = (Wire.read() << 8) | Wire.read();

        // Convert raw values (±8g range -> 4096 LSB/g, ±500dps range -> 65.5 LSB/dps)
        accelX = (float)rawAx / 4096.0f;
        accelY = (float)rawAy / 4096.0f;
        accelZ = (float)rawAz / 4096.0f;

        gyroX = (float)rawGx / 65.5f;
        gyroY = (float)rawGy / 65.5f;
        gyroZ = (float)rawGz / 65.5f;
      }
    }

    // Output CSV Line: timestamp_ms
    Serial.print(currentMillis);
    Serial.print(",");

    // Output Temperature (handle temporary DHT11 read failures gracefully)
    if (isnan(tempC)) {
      Serial.print("nan,");
    } else {
      Serial.print(tempC, 2);
      Serial.print(",");
    }

    // Output Humidity
    if (isnan(humPct)) {
      Serial.print("nan,");
    } else {
      Serial.print(humPct, 2);
      Serial.print(",");
    }

    // Output Acceleration (X, Y, Z in g)
    Serial.print(accelX, 2);
    Serial.print(",");
    Serial.print(accelY, 2);
    Serial.print(",");
    Serial.print(accelZ, 2);
    Serial.print(",");

    // Output Gyroscope (X, Y, Z in dps)
    Serial.print(gyroX, 2);
    Serial.print(",");
    Serial.print(gyroY, 2);
    Serial.print(",");
    Serial.println(gyroZ, 2);
  }
}
