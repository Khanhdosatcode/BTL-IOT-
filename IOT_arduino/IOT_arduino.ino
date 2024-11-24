#include <ESP32Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <MFRC522.h>
#include <WebSocketsClient.h>
#include <WiFi.h>
#include <SPI.h>

#define I2C_ADDRESS 0x27
#define LCD_COLUMNS 16
#define LCD_ROWS 2
LiquidCrystal_I2C lcd(I2C_ADDRESS, LCD_COLUMNS, LCD_ROWS);

Servo servoIn, servoOut;

// Các chân sensor
#define ir_car1 26
#define ir_car2 25
#define ir_car3 33

#define SERVO_IN_PIN 13  // Chân GPIO cho servo cửa vào
#define SERVO_OUT_PIN 12 // Chân GPIO cho servo cửa ra

#define SS_PIN_IN 5
#define RST_PIN_IN 4
MFRC522 mfrc522_IN(SS_PIN_IN, RST_PIN_IN);
#define SS_PIN_OUT 21
#define RST_PIN_OUT 4
MFRC522 mfrc522_OUT(SS_PIN_OUT, RST_PIN_OUT);

// Các chân cho cảm biến lửa và chuông
#define fireSensorPin 34
#define buzzerPin 27

const char* ssid = "Khanh";  // Thay đổi với SSID WiFi của bạn
const char* password = "khanh111";   // Thay đổi với mật khẩu WiFi của bạn
IPAddress local_IP(192, 168, 43, 2); // Địa chỉ IP cố định
IPAddress gateway(192, 168, 43, 1);   // Địa chỉ gateway (router)
IPAddress subnet(255, 255, 255, 0);   // Địa chỉ subnet
int S1 = 0, S2 = 0, S3 = 0;
int lastS1 = -1, lastS2 = -1, lastS3 = -1; // Biến lưu trạng thái trước đó
int slot = 3; // Số lượng chỗ trống
int flag = 1; // Điều khiển cổng ra
bool carEntered = false; // Xe vào thông qua RFID
unsigned long servoCloseTime = 0;
unsigned long fireOpenTime = 0; // Thời gian mở cửa khi có lửa
bool fireDetected = false; // Cờ báo có lửa

// Khởi tạo WebSocket client
WebSocketsClient webSocket;

// Địa chỉ WebSocket Server Python
const char* serverIP = "192.168.43.39"; // Địa chỉ IP của WebSocket server Python
const uint16_t serverPort = 5000; // Cổng WebSocket

// Cập nhật thời gian gửi dữ liệu qua WebSocket
unsigned long lastSendTime = 0; // Thời gian lần gửi trước đó
unsigned long sendInterval = 1000; // Đặt khoảng thời gian giữa các lần gửi (1000 ms = 1 giây)

void onWebSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    String message = String((char*)payload);  // Chuyển byte payload thành String

    switch (type) {
        case WStype_DISCONNECTED:
            Serial.println("[WS] Disconnected");
            break;
        case WStype_CONNECTED:
            Serial.println("[WS] Connected");
            break;
        case WStype_TEXT:
            Serial.print("[WS] Received message: ");
            Serial.println(message);

            // Phân biệt các loại tin nhắn từ server
            if (message.indexOf("Access granted") >= 0) {
                Serial.println("Access granted. Opening door...");
                openDoorIn();  // Mở cửa khi thanh toán thành công
            }
            else if (message.indexOf("Exit registered") >= 0) {
                Serial.println("User exit registered. Closing door...");
                openDoorOut();  // Mở cửa khi quét thẻ 
            }
            else if (message.indexOf("Slot") >= 0)
            {
                Serial.println(message);
            }
            else if (message.indexOf("open_in") >= 0) {
                servoIn.write(0);  // Mở cửa vào
            }
            else if (message.indexOf("close_in") >= 0) {
                servoIn.write(90);   // Đóng cửa vào
            }
            else if (message.indexOf("open_out") >= 0) {
                servoOut.write(0); // Mở cửa ra
            }
            else if (message.indexOf("close_out") >= 0) {
                servoOut.write(90);  // Đóng cửa ra
            }
            else if (message.indexOf("buzzer_on") >= 0) {
                digitalWrite(buzzerPin, HIGH); 
            }
            else if (message.indexOf("buzzer_off") >= 0) {
                digitalWrite(buzzerPin, LOW);
            }
            break;
    }
}

// Kết nối WiFi và WebSocket
void setup() {
    Serial.begin(9600);
    delay(1500);
    Wire.begin(21, 22);
    lcd.init();
    lcd.backlight();

    SPI.begin();
    mfrc522_IN.PCD_Init();
    mfrc522_OUT.PCD_Init();

    pinMode(ir_car1, INPUT);
    pinMode(ir_car2, INPUT);
    pinMode(ir_car3, INPUT);
    pinMode(fireSensorPin, INPUT);
    pinMode(buzzerPin, OUTPUT);
    digitalWrite(buzzerPin, LOW);

    servoIn.attach(SERVO_IN_PIN);  // Đính kèm servo cửa vào với GPIO đã khai báo
    servoOut.attach(SERVO_OUT_PIN); // Đính kèm servo cửa ra với GPIO đã khai báo
    servoIn.write(180); // Đóng cửa vào
    servoOut.write(180); // Đóng cửa ra

    lcd.setCursor(0, 0);
    lcd.print("Car Parking Sys");
    delay(2000);
    lcd.clear();

    Read_Sensor();
    updateSlotCount();

    // Cấu hình địa chỉ IP tĩnh
    WiFi.config(local_IP, gateway, subnet);
  
    // Kết nối WiFi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("Connected to WiFi!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    // Bắt đầu WebSocket
    webSocket.begin(serverIP, serverPort);
    webSocket.onEvent(onWebSocketEvent);

    // Thiết lập vị trí ban đầu của servo là 0 độ (cửa đóng)
    Serial.println("Scan a RFID tag...");
}

void loop() {
    // Đảm bảo gọi webSocket.loop() trong loop chính để xử lý các sự kiện WebSocket
    webSocket.loop();

    //  Kiểm tra kết nối WebSocket và kết nối lại nếu ngắt
    // if (!webSocket.isConnected()) {
    //     Serial.println("WebSocket disconnected! Reconnecting...");
    //     webSocket.begin(serverIP, serverPort);  // Kết nối lại WebSocket
    //     webSocket.onEvent(onWebSocketEvent);  // Đảm bảo bắt sự kiện khi WebSocket kết nối lại
    //     delay(5000);  // Đợi 5 giây trước khi thử kết nối lại
    // }

    // Kiểm tra và xử lý các cảm biến IR
    Read_Sensor();
    updateSlotCount();

    // Kiểm tra cảm biến lửa
    if (digitalRead(fireSensorPin) == LOW) {
        if (!fireDetected) {
            fireDetected = true;
            fireOpenTime = millis() + 2000; // Mở cửa trong 5 giây
            digitalWrite(buzzerPin, HIGH);
            servoIn.write(0);
            servoOut.write(0);
            Serial.println("Fire detected! Opening gates.");
            StaticJsonDocument<200> doc;
            doc["message"] = "Fire Detected";  // Thông điệp Fire Detected
            String jsonString;
            serializeJson(doc, jsonString);   // Chuyển đối tượng JSON thành chuỗi

            // Gửi chuỗi JSON qua WebSocket
            webSocket.sendTXT(jsonString);
        }
    } else {
        if (fireDetected == true && millis() > fireOpenTime) {
            fireDetected = false;
            digitalWrite(buzzerPin, LOW);
            servoIn.write(90);
            servoOut.write(90);
            Serial.println("No fire detected.");
            StaticJsonDocument<200> doc;
            doc["message"] = "No Fire Detected";  // Thông điệp Fire Detected
            String jsonString;
            serializeJson(doc, jsonString);   // Chuyển đối tượng JSON thành chuỗi
            // Gửi chuỗi JSON qua WebSocket
            webSocket.sendTXT(jsonString);
        }
    }

    // Cập nhật LCD khi số lượng chỗ trống thay đổi
    static int lastSlot = -1;
    if (slot != lastSlot) {
        updateLCD();
        lastSlot = slot; // Cập nhật số chỗ trước đó
    }

    // Kiểm tra và gửi trạng thái các cảm biến IR lên WebSocket chỉ khi có thay đổi
    if (millis() - lastSendTime > sendInterval) {
        sendSensorStatusIfChanged();
        lastSendTime = millis(); // Cập nhật thời gian gửi
    }

    // Kiểm tra xem có thẻ RFID vào nào được quét không
    if (isNewCardPresent_IN()) {
        // Lấy và xử lý UID của thẻ RFID
        String rfid_code = getRFIDCode_IN();
        if (rfid_code != "") {
            // In ra mã RFID
            Serial.print("RFID Code VÀO: ");
            Serial.println(rfid_code);
             // Tạo đối tượng JSON
            StaticJsonDocument<200> doc;  // Khai báo đối tượng JSON
            doc["action"] = "rfid_code_in";  // Loại hành động
            doc["rfid_code"] = rfid_code;   // Mã RFID

            // Chuyển đối tượng JSON thành chuỗi và gửi qua WebSocket
            String message;
            serializeJson(doc, message);  // Chuyển đối tượng JSON thành chuỗi
            webSocket.sendTXT(message);  // Gửi tin nhắn qua WebSocket
            // Dừng việc quét thẻ sau khi đã gửi
            mfrc522_IN.PICC_HaltA();
            mfrc522_IN.PCD_StopCrypto1();
        }
        delay(500);  // Thời gian chờ giữa các lần quét
    }
     if (isNewCardPresent_OUT()) {
        // Lấy và xử lý UID của thẻ RFID
        String rfid_code = getRFIDCode_OUT();
        if (rfid_code != "") {
            // In ra mã RFID
            Serial.print("RFID Code Ra: ");
            Serial.println(rfid_code);
            StaticJsonDocument<200> doc;  // Khai báo đối tượng JSON
            doc["action"] = "rfid_code_out";  // Loại hành động
            doc["rfid_code"] = rfid_code;   // Mã RFID

            // Chuyển đối tượng JSON thành chuỗi và gửi qua WebSocket
            String message;
            serializeJson(doc, message);  // Chuyển đối tượng JSON thành chuỗi
            webSocket.sendTXT(message);  // Gửi tin nhắn qua WebSocket
            // Gửi mã RFID qua WebSocket
            // Dừng việc quét thẻ sau khi đã gửi
            mfrc522_OUT.PICC_HaltA();
            mfrc522_OUT.PCD_StopCrypto1();
        }
        delay(500);  // Thời gian chờ giữa các lần quét
    }

}

// Hàm kiểm tra thẻ mới cho cửa vào có xuất hiện hay không
bool isNewCardPresent_IN() {
  return mfrc522_IN.PICC_IsNewCardPresent() && mfrc522_IN.PICC_ReadCardSerial();
}
// Hàm kiểm tra thẻ mới cho cửa ra có xuất hiện hay không
bool isNewCardPresent_OUT() {
  return mfrc522_OUT.PICC_IsNewCardPresent() && mfrc522_OUT.PICC_ReadCardSerial();
}
// Hàm lấy mã RFID từ thẻ quét
String getRFIDCode_IN() {
  String rfid_code = "";
  for (byte i = 0; i < mfrc522_IN.uid.size; i++) {
    rfid_code += String(mfrc522_IN.uid.uidByte[i], HEX);  // Chuyển mỗi byte thành chuỗi hex
  }
  rfid_code.toUpperCase();  // Chuyển mã RFID về chữ in hoa
  return rfid_code;
}
String getRFIDCode_OUT() {
  String rfid_code = "";
  for (byte i = 0; i < mfrc522_OUT.uid.size; i++) {
    rfid_code += String(mfrc522_OUT.uid.uidByte[i], HEX);  // Chuyển mỗi byte thành chuỗi hex
  }
  rfid_code.toUpperCase();  // Chuyển mã RFID về chữ in hoa
  return rfid_code;
}
// Hàm mở cửa vào (điều khiển servo)
void openDoorIn() {
  servoIn.write(90);  // Mở cửa (servo quay 90 độ, tùy vào vị trí servo của bạn)
  delay(2000);  // Giữ cửa mở trong 2 giây
  closeDoorIn();  // Đóng cửa sau 2 giây
}

// Hàm đóng cửa vào
void closeDoorIn() {
  servoIn.write(180);  // Đóng cửa (servo quay về vị trí ban đầu)
}

void openDoorOut() {
  servoOut.write(90);
  delay(2000);
  closeDoorOut();
}
void closeDoorOut() {
  servoOut.write(180);  // Đóng cửa (servo quay về vị trí ban đầu)
}

// Hàm gửi trạng thái cảm biến IR lên WebSocket server nếu có thay đổi
void sendSensorStatusIfChanged() {
  if (S1 != lastS1) {
       // Tạo một đối tượng JSON
    StaticJsonDocument<200> doc;
    doc["action"] = "update_slot";
    doc["slot_id"] = 2;
    doc["status"] = (S2 ? "available" : "occupied");
    // Chuyển đổi đối tượng JSO thành chuỗi
    String message;
    serializeJson(doc, message);
    lastS1 = S1; // Cập nhật trạng thái cũ
  }

  if (S2 != lastS2) {
       // Tạo một đối tượng JSON
    StaticJsonDocument<200> doc;
    doc["action"] = "update_slot";
    doc["slot_id"] = 2;
    doc["status"] = (S2 ? "available" : "occupied");
    // Chuyển đổi đối tượng JSON thành chuỗi
    String message;
    serializeJson(doc, message);
    lastS2 = S2; // Cập nhật trạng thái cũ
  }

  if (S3 != lastS3) {
       // Tạo một đối tượng JSON
    StaticJsonDocument<200> doc;
    doc["action"] = "update_slot";
    doc["slot_id"] = 3;
    doc["status"] = (S3 ? "available" : "occupied");
    // Chuyển đổi đối tượng JSON thành chuỗi
    String message;
    serializeJson(doc, message);
    webSocket.sendTXT(message);
    lastS3 = S3; // Cập nhật trạng thái cũ
  }
}

void Read_Sensor() {
    S1 = digitalRead(ir_car1);
    S2 = digitalRead(ir_car2);
    S3 = digitalRead(ir_car3);
}

void updateSlotCount() {
    slot = 3 - (S1 + S2 + S3);
}

void updateLCD() {
    lcd.setCursor(0, 0); lcd.print("Slots: ");
    lcd.print(slot);   
    lcd.print("   ");
    
    lcd.setCursor(0, 1);
    lcd.print(S1 ? "S1: O " : "S1: A ");
    lcd.print(S2 ? "S2: O " : "S2: A ");
    lcd.print(S3 ? "S3: O " : "S3: A ");
}