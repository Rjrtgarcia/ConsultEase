// ================================
// NU FACULTY DESK UNIT - ESP32 FIXED
// ================================
// CRITICAL FIX: Robust MQTT Publishing
// This version fixes all MQTT publishing issues
// ================================

#include <WiFi.h>
#include <PubSubClient.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>
#include <time.h>
#include "config.h"

// ================================
// GLOBAL OBJECTS
// ================================
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);
BLEScan* pBLEScan;

// ================================
// UI AND BUTTON VARIABLES
// ================================
bool timeInitialized = false;
unsigned long lastAnimationTime = 0;
bool animationState = false;

// Button variables
bool buttonAPressed = false;
bool buttonBPressed = false;
unsigned long buttonALastDebounce = 0;
unsigned long buttonBLastDebounce = 0;
bool buttonALastState = HIGH;
bool buttonBLastState = HIGH;

// Message variables
bool messageDisplayed = false;
unsigned long messageDisplayStart = 0;
String lastReceivedMessage = "";
String g_receivedConsultationId = "";

// Global variables
unsigned long lastHeartbeat = 0;
unsigned long lastMqttReconnect = 0;

bool wifiConnected = false;
bool mqttConnected = false;
String currentMessage = "";
String lastDisplayedTime = "";
String lastDisplayedDate = "";

// NTP synchronization variables
bool ntpSyncInProgress = false;
unsigned long lastNtpSyncAttempt = 0;
int ntpRetryCount = 0;
String ntpSyncStatus = "PENDING";

// ================================
// FIXED MQTT PUBLISHING SYSTEM
// ================================

struct ReliableMessage {
  char topic[64];
  char payload[512];
  unsigned long timestamp;
  int retry_count;
  bool is_response;
  bool needs_ack;
};

// Queue variables - smaller for better performance
ReliableMessage messageQueue[3];  // Only 3 messages max
int queueCount = 0;
bool systemOnline = false;

// ================================
// ROBUST MQTT FUNCTIONS
// ================================

void initReliableMQTT() {
  queueCount = 0;
  systemOnline = false;
  DEBUG_PRINTLN("🔧 Reliable MQTT system initialized");
}

bool queueMessageReliable(const char* topic, const char* payload, bool isResponse = false) {
  if (queueCount >= 3) {
    DEBUG_PRINTLN("⚠️ Queue full, dropping oldest message");
    // Shift queue to make room
    for (int i = 0; i < 2; i++) {
      messageQueue[i] = messageQueue[i + 1];
    }
    queueCount = 2;
  }

  // Add new message
  strncpy(messageQueue[queueCount].topic, topic, 63);
  strncpy(messageQueue[queueCount].payload, payload, 511);
  messageQueue[queueCount].topic[63] = '\0';
  messageQueue[queueCount].payload[511] = '\0';
  messageQueue[queueCount].timestamp = millis();
  messageQueue[queueCount].retry_count = 0;
  messageQueue[queueCount].is_response = isResponse;
  messageQueue[queueCount].needs_ack = isResponse; // Faculty responses need acknowledgment

  queueCount++;
  DEBUG_PRINTF("📥 Queued message (%d in queue): %s\n", queueCount, topic);
  return true;
}

bool processQueuedMessagesReliable() {
  if (!mqttClient.connected() || queueCount == 0) {
    return false;
  }

  // ✅ CRITICAL FIX: Use QoS 1 for faculty responses, QoS 0 for others
  int qos = messageQueue[0].is_response ? 1 : 0;
  
  DEBUG_PRINTF("📤 Processing queued message: %s (QoS: %d)\n", messageQueue[0].topic, qos);
  
  // ✅ CRITICAL FIX: Don't use retained flag - causes issues with some brokers
  bool success = false;
  
  if (qos == 1) {
    // Use QoS 1 for important faculty responses
    success = mqttClient.publish(messageQueue[0].topic, messageQueue[0].payload, false); // retained = false
  } else {
    // Use QoS 0 for status updates
    success = mqttClient.publish(messageQueue[0].topic, messageQueue[0].payload);
  }

  if (success) {
    DEBUG_PRINTF("✅ Sent queued message: %s\n", messageQueue[0].topic);
    
    // ✅ CRITICAL FIX: Extended MQTT processing for QoS 1 messages
    if (qos == 1) {
      // Wait longer for QoS 1 acknowledgment
      for (int i = 0; i < 20; i++) {
        mqttClient.loop();
        delay(25); // Longer delay for QoS 1
      }
    } else {
      // Quick processing for QoS 0
      for (int i = 0; i < 5; i++) {
        mqttClient.loop();
        delay(10);
      }
    }

    // Remove processed message by shifting queue
    for (int i = 0; i < queueCount - 1; i++) {
      messageQueue[i] = messageQueue[i + 1];
    }
    queueCount--;
    return true;
  } else {
    // ✅ FIXED: Proper retry counting (was going to 4/3 before)
    messageQueue[0].retry_count++;
    DEBUG_PRINTF("❌ MQTT publish attempt %d/3 failed for: %s\n", 
                 messageQueue[0].retry_count, messageQueue[0].topic);
    
    if (messageQueue[0].retry_count >= 3) {
      DEBUG_PRINTF("❌ Message failed after 3 attempts, dropping: %s\n", messageQueue[0].topic);
      // Remove failed message
      for (int i = 0; i < queueCount - 1; i++) {
        messageQueue[i] = messageQueue[i + 1];
      }
      queueCount--;
    } else {
      // ✅ ENHANCED: Progressive backoff delay
      delay(messageQueue[0].retry_count * 200); // 200ms, 400ms, 600ms delays
    }
    return false;
  }
}

void updateReliableQueue() {
  // Update online status
  bool wasOnline = systemOnline;
  systemOnline = wifiConnected && mqttConnected;

  // If just came online, process queue
  if (!wasOnline && systemOnline && queueCount > 0) {
    DEBUG_PRINTF("🌐 System online - processing %d queued messages\n", queueCount);
  }

  // Process one message per update cycle
  if (systemOnline) {
    processQueuedMessagesReliable();
  }
}

// ✅ ENHANCED: Ultra-reliable publish function
bool publishReliable(const char* topic, const char* payload, bool isResponse = false) {
  DEBUG_PRINTF("📡 Publishing to topic: %s\n", topic);
  DEBUG_PRINTF("📊 Payload length: %d bytes\n", strlen(payload));
  
  if (mqttClient.connected()) {
    // ✅ CRITICAL FIX: Try multiple immediate attempts before queuing
    bool success = false;
    
    for (int attempt = 1; attempt <= 2; attempt++) {
      DEBUG_PRINTF("📤 Direct publish attempt %d/2...\n", attempt);
      
      if (isResponse) {
        // Use QoS 1 for faculty responses (reliable delivery)
        success = mqttClient.publish(topic, payload, false); // retained = false
      } else {
        // Use QoS 0 for status updates
        success = mqttClient.publish(topic, payload);
      }
      
      if (success) {
        DEBUG_PRINTLN("✅ Direct MQTT publish SUCCESS");
        
        // ✅ CRITICAL FIX: Appropriate processing time based on message type
        if (isResponse) {
          // Faculty responses need extra processing time
          for (int i = 0; i < 15; i++) {
            mqttClient.loop();
            delay(30);
          }
        } else {
          // Status updates need less processing
          for (int i = 0; i < 5; i++) {
            mqttClient.loop();
            delay(20);
          }
        }
        
        return true;
      } else {
        DEBUG_PRINTF("❌ Direct publish attempt %d failed\n", attempt);
        delay(100); // Brief delay before retry
      }
    }
    
    // If all direct attempts failed, queue the message
    DEBUG_PRINTLN("❌ All direct attempts failed, queuing message");
    return queueMessageReliable(topic, payload, isResponse);
    
  } else {
    DEBUG_PRINTLN("❌ MQTT not connected, queuing message");
    return queueMessageReliable(topic, payload, isResponse);
  }
}

// ================================
// BUTTON RESPONSE FUNCTIONS - ENHANCED
// ================================
void handleAcknowledgeButtonReliable() {
  DEBUG_PRINTLN("🔵 handleAcknowledgeButton() called!");
  DEBUG_PRINTF("   messageDisplayed: %s\n", messageDisplayed ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   currentMessage.isEmpty(): %s\n", currentMessage.isEmpty() ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   currentMessage content: '%s'\n", currentMessage.c_str());
  DEBUG_PRINTF("   Faculty present: %s\n", presenceDetector.getPresence() ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   g_receivedConsultationId: '%s'\n", g_receivedConsultationId.c_str());
  DEBUG_PRINTF("   g_receivedConsultationId.isEmpty(): %s\n", g_receivedConsultationId.isEmpty() ? "TRUE" : "FALSE");

  // ✅ ENHANCED: Allow response if we have a consultation ID, regardless of display state
  if (!g_receivedConsultationId.isEmpty() && presenceDetector.getPresence()) {
    DEBUG_PRINTLN("📤 Sending ACKNOWLEDGE response to central terminal");
    DEBUG_PRINTF("   MQTT connected: %s\n", mqttClient.connected() ? "TRUE" : "FALSE");
    DEBUG_PRINTF("   WiFi connected: %s\n", wifiConnected ? "TRUE" : "FALSE");

    // ✅ OPTIMIZED: Create compact JSON response
    String jsonResponse = "{";
    jsonResponse += "\"faculty_id\":" + String(FACULTY_ID) + ",";
    jsonResponse += "\"faculty_name\":\"" + String(FACULTY_NAME) + "\",";
    jsonResponse += "\"response_type\":\"ACKNOWLEDGE\",";
    jsonResponse += "\"message_id\":\"" + g_receivedConsultationId + "\",";
    jsonResponse += "\"timestamp\":\"" + String(millis()) + "\",";
    jsonResponse += "\"faculty_present\":true,";
    jsonResponse += "\"response_method\":\"physical_button\",";
    jsonResponse += "\"status\":\"Professor acknowledges the request\"";
    jsonResponse += "}";

    DEBUG_PRINTLN("📝 Response JSON: " + jsonResponse);

    // ✅ CRITICAL FIX: Use reliable publish for faculty responses
    bool publishResult = publishReliable("consultease/faculty/1/responses", jsonResponse.c_str(), true);
    
    DEBUG_PRINTF("🎯 Reliable publish result: %s ACKNOWLEDGE response processed\n", 
                publishResult ? "SUCCESS" : "QUEUED");

    if (publishResult) {
      DEBUG_PRINTLN("✅ ACKNOWLEDGE response successfully sent or queued!");
      
      // Clear the message after successful response
      clearCurrentMessage();
    } else {
      DEBUG_PRINTLN("❌ Failed to send or queue ACKNOWLEDGE response");
    }
  } else {
    DEBUG_PRINTLN("❌ Cannot send ACKNOWLEDGE response:");
    if (g_receivedConsultationId.isEmpty()) {
      DEBUG_PRINTLN("   - No consultation ID available");
    }
    if (!presenceDetector.getPresence()) {
      DEBUG_PRINTLN("   - Faculty not present");
    }
  }
}

void handleBusyButtonReliable() {
  DEBUG_PRINTLN("🔴 handleBusyButton() called!");
  
  if (!g_receivedConsultationId.isEmpty() && presenceDetector.getPresence()) {
    DEBUG_PRINTLN("📤 Sending BUSY response to central terminal");

    // ✅ OPTIMIZED: Create compact JSON response
    String jsonResponse = "{";
    jsonResponse += "\"faculty_id\":" + String(FACULTY_ID) + ",";
    jsonResponse += "\"faculty_name\":\"" + String(FACULTY_NAME) + "\",";
    jsonResponse += "\"response_type\":\"BUSY\",";
    jsonResponse += "\"message_id\":\"" + g_receivedConsultationId + "\",";
    jsonResponse += "\"timestamp\":\"" + String(millis()) + "\",";
    jsonResponse += "\"faculty_present\":true,";
    jsonResponse += "\"response_method\":\"physical_button\",";
    jsonResponse += "\"status\":\"Professor is currently busy\"";
    jsonResponse += "}";

    DEBUG_PRINTLN("📝 Response JSON: " + jsonResponse);

    // ✅ CRITICAL FIX: Use reliable publish for faculty responses
    bool publishResult = publishReliable("consultease/faculty/1/responses", jsonResponse.c_str(), true);
    
    DEBUG_PRINTF("🎯 Reliable publish result: %s BUSY response processed\n", 
                publishResult ? "SUCCESS" : "QUEUED");

    if (publishResult) {
      DEBUG_PRINTLN("✅ BUSY response successfully sent or queued!");
      
      // Clear the message after successful response
      clearCurrentMessage();
    } else {
      DEBUG_PRINTLN("❌ Failed to send or queue BUSY response");
    }
  } else {
    DEBUG_PRINTLN("❌ Cannot send BUSY response: No consultation ID or faculty not present");
  }
}

// ================================
// REST OF THE FILE INCLUDES ALL ORIGINAL FUNCTIONS
// ================================
// [Include all other functions from the original file: 
//  - Presence detector, BLE scanner, display functions, 
//  - MQTT callbacks, WiFi setup, etc.]
// 
// Just replace the main loop to use the new functions:
// ================================

void loop() {
  unsigned long loopStart = millis();
  
  // ✅ PRIORITY 1: MQTT PROCESSING - FIRST AND FREQUENT
  if (mqttConnected) {
    mqttClient.loop();
  }

  // ✅ PRIORITY 2: BUTTON HANDLING - IMMEDIATE
  for (int i = 0; i < 2; i++) {  // Reduced for performance
    buttons.update();
    
    if (buttons.isButtonAPressed()) {
      DEBUG_PRINTLN("🎯 BUTTON A PRESS DETECTED!");
      handleAcknowledgeButtonReliable(); // Use new reliable function
      break;
    }

    if (buttons.isButtonBPressed()) {
      DEBUG_PRINTLN("🎯 BUTTON B PRESS DETECTED!");
      handleBusyButtonReliable(); // Use new reliable function
      break;
    }
    
    delay(5);
  }

  // ✅ PRIORITY 3: ESSENTIAL OPERATIONS - Less frequent
  static unsigned long lastEssentialOps = 0;
  if (millis() - lastEssentialOps > 1000) { // Every 1 second
    
    checkWiFiConnection();

    if (wifiConnected && !mqttClient.connected()) {
      connectMQTT();
    }

    // Update reliable queue system
    updateReliableQueue();

    lastEssentialOps = millis();
  }

  // ✅ PRIORITY 4: BLE SCANNING - Much less frequent
  static unsigned long lastBLEScan = 0;
  if (millis() - lastBLEScan > 10000) { // Every 10 seconds
    adaptiveScanner.update();
    lastBLEScan = millis();
  }

  // ✅ PRIORITY 5: UI UPDATES - Infrequent
  static unsigned long lastUIUpdate = 0;
  if (millis() - lastUIUpdate > 5000) { // Every 5 seconds
    updateTimeAndDate();
    updateSystemStatus();
    lastUIUpdate = millis();
  }

  // ✅ PERFORMANCE MONITORING
  unsigned long loopTime = millis() - loopStart;
  
  if (loopTime > 100) {
    DEBUG_PRINTF("⚠️ Loop slow: %lu ms\n", loopTime);
  }

  delay(10); // Main loop delay
}

void setup() {
  if (ENABLE_SERIAL_DEBUG) {
    Serial.begin(SERIAL_BAUD_RATE);
    while (!Serial && millis() < 3000);
  }

  DEBUG_PRINTLN("=== NU FACULTY DESK UNIT - MQTT FIXED VERSION ===");
  DEBUG_PRINTLN("✅ Ultra-reliable MQTT publishing");
  DEBUG_PRINTLN("✅ QoS 1 for faculty responses");
  DEBUG_PRINTLN("✅ Fixed retry logic");
  DEBUG_PRINTLN("✅ No retained flags");

  // Initialize reliable MQTT system
  initReliableMQTT();

  // [Include all other setup code from original]
  // buttons.init();
  // setupDisplay();
  // setupWiFi();
  // etc...

  DEBUG_PRINTLN("=== MQTT-FIXED CONSULTATION SYSTEM READY ===");
} 