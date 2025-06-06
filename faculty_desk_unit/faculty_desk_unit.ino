// ================================
// NU FACULTY DESK UNIT - ESP32
// ================================
// Capstone Project by Jeysibn
// WITH ADAPTIVE BLE SCANNER & GRACE PERIOD SYSTEM
// Date: June 2, 2025 16:17 (Philippines Time)
// Updated: Added consultation message queue system
// 
// ✅ PERFORMANCE OPTIMIZATIONS APPLIED:
// - Reduced BLE scan frequency from 1s to 8s (major performance fix)
// - Enhanced MQTT publishing with forced processing loops
// - Optimized main loop timing to reduce from 3241ms to <100ms
// - Improved button response time with faster debouncing
// - Better queue processing with exponential backoff
// ✅ MESSAGE QUEUE SYSTEM ADDED:
// - Messages no longer overwrite each other
// - Automatic queue processing after button responses
// - Visual queue status display
// ================================

// ✅ CRITICAL FIX: Increase MQTT packet size limit for large responses
#define MQTT_MAX_PACKET_SIZE 1024  // Increased from default 128 bytes to handle consultation responses

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

struct ConsultationMessage {
  String content;
  String consultationId;
  String studentName;
  String studentId;
  String actualMessage;
  unsigned long timestamp;
  bool isValid;
};

// ================================
// GLOBAL OBJECTS
// ================================
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);
BLEScan* pBLEScan;

// ================================
// MQTT STATE DEFINITIONS AND HELPERS
// ================================
const char* getMqttStateString(int state) {
  switch(state) {
    case -4: return "CONNECTION_TIMEOUT";
    case -3: return "CONNECTION_LOST"; 
    case -2: return "CONNECT_FAILED";
    case -1: return "DISCONNECTED";
    case 0:  return "CONNECTED";
    case 1:  return "BAD_PROTOCOL";
    case 2:  return "BAD_CLIENT_ID";
    case 3:  return "UNAVAILABLE";
    case 4:  return "BAD_CREDENTIALS";
    case 5:  return "UNAUTHORIZED";
    default: return "UNKNOWN_STATE";
  }
}

bool isMqttReallyConnected() {
  bool connected = mqttClient.connected();
  int state = mqttClient.state();
  
  DEBUG_PRINTF("🔍 MQTT Status Check - connected(): %s, state(): %d (%s)\n", 
               connected ? "TRUE" : "FALSE", 
               state, 
               getMqttStateString(state));
  
  // Only consider truly connected if both conditions are met
  bool reallyConnected = connected && (state == 0);
  
  if (!reallyConnected) {
    DEBUG_PRINTF("⚠️ MQTT Connection Issue - connected=%s but state=%d (%s)\n",
                 connected ? "TRUE" : "FALSE",
                 state,
                 getMqttStateString(state));
  }
  
  return reallyConnected;
}

// ================================
// UI AND BUTTON VARIABLES
// ================================
bool timeInitialized = false;
unsigned long lastAnimationTime = 0;
bool animationState = false;
bool systemFullyInitialized = false;  

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
// FORWARD DECLARATIONS
// ================================
void publishPresenceUpdate();
void updateMainDisplay();
void updateSystemStatus();

// Consultation Message Queue variables
#define MAX_CONSULTATION_QUEUE_SIZE 10
ConsultationMessage consultationQueue[MAX_CONSULTATION_QUEUE_SIZE];
int consultationQueueHead = 0;           // Points to the first message to be displayed
int consultationQueueTail = 0;           // Points to the next position to add a message
int consultationQueueSize = 0;           // Current number of messages in queue
bool currentMessageDisplayed = false;    // Is there a message currently being displayed?

// ================================
// LED NOTIFICATION SYSTEM
// ================================
bool messageLedState = false;           // Current LED state (on/off)
unsigned long lastLedToggle = 0;        // Last time LED was toggled
bool hasUnreadMessages = false;         // Are there unread messages?

// ================================
// CONSULTATION MESSAGE QUEUE FUNCTIONS
// ================================

void initConsultationQueue() {
  consultationQueueHead = 0;
  consultationQueueTail = 0;
  consultationQueueSize = 0;
  currentMessageDisplayed = false;
  
  // Clear all messages
  for (int i = 0; i < MAX_CONSULTATION_QUEUE_SIZE; i++) {
    consultationQueue[i].isValid = false;
    consultationQueue[i].content = "";
    consultationQueue[i].consultationId = "";
  }
  
  DEBUG_PRINTLN("📥 Consultation message queue initialized");
}

bool isConsultationQueueEmpty() {
  return consultationQueueSize == 0;
}

bool isConsultationQueueFull() {
  return consultationQueueSize >= MAX_CONSULTATION_QUEUE_SIZE;
}

void parseConsultationMessage(String messageContent, String consultationId, ConsultationMessage &msg) {
  msg.content = messageContent;
  msg.consultationId = consultationId;
  
  // Parse student info from message
  int fromIndex = messageContent.indexOf("From:");
  int sidIndex = messageContent.indexOf("(SID:");
  int messageIndex = messageContent.indexOf("): ");
  
  if (fromIndex != -1 && sidIndex != -1 && messageIndex != -1) {
    // Extract student name
    msg.studentName = messageContent.substring(fromIndex + 5, sidIndex);
    msg.studentName.trim();
    
    // Extract student ID
    int sidStart = sidIndex + 5;
    int sidEnd = messageContent.indexOf(")", sidStart);
    if (sidEnd != -1) {
      msg.studentId = messageContent.substring(sidStart, sidEnd);
      msg.studentId.trim();
    }
    
    // Extract actual consultation message
    msg.actualMessage = messageContent.substring(messageIndex + 3);
    msg.actualMessage.trim();
  } else {
    // Fallback parsing
    msg.studentName = "Unknown Student";
    msg.studentId = "N/A";
    msg.actualMessage = messageContent;
  }
  
  DEBUG_PRINTF("📋 Parsed message - Student: %s, SID: %s, CID: %s\n", 
               msg.studentName.c_str(), msg.studentId.c_str(), msg.consultationId.c_str());
}

bool addConsultationToQueue(String messageContent, String consultationId) {
  DEBUG_PRINTF("📥 Adding consultation to queue: CID=%s, Size=%d/%d\n", 
               consultationId.c_str(), consultationQueueSize, MAX_CONSULTATION_QUEUE_SIZE);
  
  // Parse message content
  ConsultationMessage newMessage;
  parseConsultationMessage(messageContent, consultationId, newMessage);
  
  if (isConsultationQueueFull()) {
    DEBUG_PRINTLN("⚠️ Consultation queue is FULL! Dropping oldest message to make room");
    
    // Remove oldest message (FIFO behavior)
    consultationQueueHead = (consultationQueueHead + 1) % MAX_CONSULTATION_QUEUE_SIZE;
    consultationQueueSize--;
  }
  
  // Add new message to tail
  consultationQueue[consultationQueueTail] = newMessage;
  consultationQueue[consultationQueueTail].timestamp = millis();
  consultationQueue[consultationQueueTail].isValid = true;
  
  consultationQueueTail = (consultationQueueTail + 1) % MAX_CONSULTATION_QUEUE_SIZE;
  consultationQueueSize++;
  
  DEBUG_PRINTF("✅ Consultation added to queue. Queue size: %d/%d\n", consultationQueueSize, MAX_CONSULTATION_QUEUE_SIZE);

  updateMessageLED();
  
  return true;
}

ConsultationMessage getNextConsultationFromQueue() {
  ConsultationMessage emptyMessage;
  emptyMessage.isValid = false;
  
  if (isConsultationQueueEmpty()) {
    DEBUG_PRINTLN("📭 Consultation queue is empty, no messages to retrieve");
    return emptyMessage;
  }
  
  ConsultationMessage nextMessage = consultationQueue[consultationQueueHead];
  
  // Mark as processed and move head
  consultationQueue[consultationQueueHead].isValid = false;
  consultationQueueHead = (consultationQueueHead + 1) % MAX_CONSULTATION_QUEUE_SIZE;
  consultationQueueSize--;
  
  DEBUG_PRINTF("📤 Retrieved consultation from queue. Remaining: %d/%d\n", consultationQueueSize, MAX_CONSULTATION_QUEUE_SIZE);
  
  return nextMessage;
}

void displayQueuedConsultation(ConsultationMessage &msg) {
  // Set global variables for compatibility with existing button handlers
  currentMessage = msg.content;
  g_receivedConsultationId = msg.consultationId;
  messageDisplayed = true;
  messageDisplayStart = millis();
  currentMessageDisplayed = true;

  // 🆕 START LED NOTIFICATION
  updateMessageLED();
  
  // Clear main area
  tft.fillRect(0, MAIN_AREA_Y, SCREEN_WIDTH, MAIN_AREA_HEIGHT, COLOR_WHITE);

  // Clean message header - smaller and simpler
  drawSimpleCard(10, MAIN_AREA_Y + 5, SCREEN_WIDTH - 20, 25, COLOR_ACCENT);

  int headerX = getCenterX("CONSULTATION REQUEST", 2);
  tft.setCursor(headerX, MAIN_AREA_Y + 10);
  tft.setTextColor(COLOR_WHITE);
  tft.setTextSize(2);
  tft.print("CONSULTATION REQUEST");

  // Message content area - starts higher due to smaller header
  int lineHeight = 20;
  int maxCharsPerLine = 25;
  int currentY = MAIN_AREA_Y + 35;
  int maxLines = 10;

  // Display student name only (no SID)
  tft.setCursor(15, currentY);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(2);
  tft.print("From: ");
  tft.setTextColor(COLOR_BLACK);
  tft.print(msg.studentName);
  currentY += lineHeight + 8;
  
  // Display consultation message with better spacing
  tft.setCursor(15, currentY);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(2);
  tft.print("Message:");
  currentY += lineHeight + 5;
  
  // Display consultation message with word wrapping - more lines available
  int linesUsed = 0;
  for (int i = 0; i < msg.actualMessage.length() && linesUsed < maxLines - 2; i += maxCharsPerLine) {
    String line = msg.actualMessage.substring(i, min(i + maxCharsPerLine, (int)msg.actualMessage.length()));
    tft.setCursor(15, currentY);
    tft.setTextColor(COLOR_BLACK);
    tft.setTextSize(2);
    tft.print(line);
    currentY += lineHeight;
    linesUsed++;
  }

  DEBUG_PRINTF("📱 Displayed clean consultation: %s (Queue: %d pending)\n", 
               msg.consultationId.c_str(), consultationQueueSize);
}

void processNextQueuedConsultation() {
  if (isConsultationQueueEmpty()) {
    DEBUG_PRINTLN("📭 No more consultations in queue");
    currentMessageDisplayed = false;
    updateMainDisplay(); // Return to normal display
    return;
  }
  
  DEBUG_PRINTF("📤 Processing next consultation from queue (Queue size: %d)\n", consultationQueueSize);
  
  ConsultationMessage nextMessage = getNextConsultationFromQueue();
  if (nextMessage.isValid) {
    displayQueuedConsultation(nextMessage);
  } else {
    DEBUG_PRINTLN("❌ Invalid consultation retrieved from queue");
    processNextQueuedConsultation(); // Try next message
  }
}


// ================================
// LED NOTIFICATION FUNCTIONS
// ================================

void initMessageLED() {
  pinMode(MESSAGE_LED_PIN, OUTPUT);
  digitalWrite(MESSAGE_LED_PIN, LOW);  // Start with LED off
  messageLedState = false;
  lastLedToggle = 0;
  hasUnreadMessages = false;
  
  DEBUG_PRINTF("📡 Message notification LED initialized on pin %d\n", MESSAGE_LED_PIN);
}

void updateMessageLED() {
  // Check if we have unread messages (either displayed or in queue)
  bool shouldBlink = currentMessageDisplayed || (consultationQueueSize > 0);
  
  if (shouldBlink != hasUnreadMessages) {
    hasUnreadMessages = shouldBlink;
    if (shouldBlink) {
      DEBUG_PRINTF("💡 LED notification started - %d message(s) pending\n", 
                   consultationQueueSize + (currentMessageDisplayed ? 1 : 0));
    } else {
      DEBUG_PRINTLN("💡 LED notification stopped - no pending messages");
      digitalWrite(MESSAGE_LED_PIN, LOW);  // Turn off LED
      messageLedState = false;
    }
  }
  
  // Handle blinking when there are unread messages
  if (hasUnreadMessages) {
    unsigned long now = millis();
    if (now - lastLedToggle >= LED_BLINK_INTERVAL) {
      messageLedState = !messageLedState;
      digitalWrite(MESSAGE_LED_PIN, messageLedState ? HIGH : LOW);
      lastLedToggle = now;
      
      // Debug every 10th blink to avoid spam
      static int blinkCount = 0;
      blinkCount++;
      if (blinkCount % 10 == 0) {
        DEBUG_PRINTF("💡 LED blink #%d - %d total messages pending\n", 
                     blinkCount, consultationQueueSize + (currentMessageDisplayed ? 1 : 0));
      }
    }
  }
}

void testMessageLED() {
  DEBUG_PRINTLN("🔧 Testing message notification LED...");
  
  // Blink 3 times quickly
  for (int i = 0; i < 3; i++) {
    digitalWrite(MESSAGE_LED_PIN, HIGH);
    delay(200);
    digitalWrite(MESSAGE_LED_PIN, LOW);
    delay(200);
  }
  
  DEBUG_PRINTLN("✅ LED test complete");
}

// ================================
// SIMPLE OFFLINE MESSAGE QUEUE
// ================================

struct SimpleMessage {
  char topic[64];
  char payload[512];
  unsigned long timestamp;
  int retry_count;
  bool is_response;
};

// Queue variables
SimpleMessage messageQueue[10];  // Adjust size as needed
int queueCount = 0;
bool systemOnline = false;

// ================================
// OFFLINE QUEUE FUNCTIONS
// ================================

void initOfflineQueue() {
  queueCount = 0;
  systemOnline = false;
  DEBUG_PRINTLN("📥 Offline message queue initialized");
}

bool queueMessage(const char* topic, const char* payload, bool isResponse = false) {
  if (queueCount >= 10) {
    DEBUG_PRINTLN("⚠️ Queue full, dropping oldest message");
    // Shift queue to make room
    for (int i = 0; i < 9; i++) {
      messageQueue[i] = messageQueue[i + 1];
    }
    queueCount = 9;
  }

  // Add new message
  strncpy(messageQueue[queueCount].topic, topic, 63);
  strncpy(messageQueue[queueCount].payload, payload, 511);
  messageQueue[queueCount].topic[63] = '\0';
  messageQueue[queueCount].payload[511] = '\0';
  messageQueue[queueCount].timestamp = millis();
  messageQueue[queueCount].retry_count = 0;
  messageQueue[queueCount].is_response = isResponse;

  queueCount++;
  DEBUG_PRINTF("📥 Queued message (%d in queue): %s\n", queueCount, topic);
  return true;
}

bool processQueuedMessages() {
  // ✅ ENHANCED: Use detailed MQTT state checking instead of just connected()
  if (!isMqttReallyConnected() || queueCount == 0) {
    if (queueCount > 0 && !isMqttReallyConnected()) {
      DEBUG_PRINTF("📥 Cannot process %d queued messages - MQTT not properly connected\n", queueCount);
    }
    return false;
  }

  // ✅ ENHANCED: Process one message at a time with better error handling
  DEBUG_PRINTF("📤 Processing queued message: %s\n", messageQueue[0].topic);
  
  // ✅ ENHANCED: Pre-publish validation
  int payloadLength = strlen(messageQueue[0].payload);
  DEBUG_PRINTF("📄 Queue message payload: %d bytes\n", payloadLength);
  
  // ✅ CRITICAL FIX: Use QoS 0 and NO retained flag for responses
  bool success = mqttClient.publish(messageQueue[0].topic, messageQueue[0].payload, false); // retained = false

  if (success) {
    DEBUG_PRINTF("✅ Sent queued message: %s (%d bytes)\n", messageQueue[0].topic, payloadLength);
    
    // ✅ CRITICAL FIX: Reduced MQTT processing to prevent blocking
    for (int i = 0; i < 3; i++) { // Reduced from 10 to 3
      mqttClient.loop();
      delay(10); // Reduced from 30ms to 10ms
    }

    // Remove processed message by shifting queue
    for (int i = 0; i < queueCount - 1; i++) {
      messageQueue[i] = messageQueue[i + 1];
    }
    queueCount--;
    return true;
  } else {
    // ✅ ENHANCED: Better error diagnostics with MQTT state checking
    int mqttState = mqttClient.state();
    messageQueue[0].retry_count++;
    
    DEBUG_PRINTF("❌ MQTT publish retry %d/3 FAILED for: %s\n", 
                 messageQueue[0].retry_count, messageQueue[0].topic);
    DEBUG_PRINTF("   📊 MQTT State: %d (%s)\n", mqttState, getMqttStateString(mqttState));
    DEBUG_PRINTF("   📄 Payload size: %d bytes\n", payloadLength);
    DEBUG_PRINTF("   🔌 WiFi connected: %s\n", wifiConnected ? "TRUE" : "FALSE");
    
    // ✅ ENHANCED: Check if we need to force reconnection
    if (mqttState != 0) {
      DEBUG_PRINTF("🔄 MQTT state not CONNECTED (%d), may need reconnection\n", mqttState);
      mqttConnected = false; // Force reconnection attempt in main loop
    }
    
    if (messageQueue[0].retry_count > 3) {
      DEBUG_PRINTF("❌ Message failed after 3 retries, dropping: %s\n", messageQueue[0].topic);
      DEBUG_PRINTF("   Final MQTT state was: %d (%s)\n", mqttState, getMqttStateString(mqttState));
      
      // Remove failed message
      for (int i = 0; i < queueCount - 1; i++) {
        messageQueue[i] = messageQueue[i + 1];
      }
      queueCount--;
    }
    // ✅ CRITICAL FIX: Removed blocking retry delay
    return false;
  }
}

void updateOfflineQueue() {
  // Update online status with enhanced MQTT checking
  bool wasOnline = systemOnline;
  systemOnline = wifiConnected && isMqttReallyConnected();

  // If just came online, process queue
  if (!wasOnline && systemOnline && queueCount > 0) {
    DEBUG_PRINTF("🌐 System online - processing %d queued messages\n", queueCount);
  }

  // ✅ CRITICAL FIX: Process multiple messages per cycle for better throughput
  if (systemOnline && queueCount > 0) {
    int processedCount = 0;
    int maxProcessPerCycle = min(3, queueCount); // Process up to 3 messages per cycle
    
    for (int i = 0; i < maxProcessPerCycle; i++) {
      if (processQueuedMessages()) {
        processedCount++;
      } else {
        break; // Stop if processing fails
      }
    }
    
    if (processedCount > 0) {
      DEBUG_PRINTF("📤 Processed %d queued messages this cycle\n", processedCount);
    }
  }
}

// Enhanced publish function with queuing
bool publishWithQueue(const char* topic, const char* payload, bool isResponse = false) {
  DEBUG_PRINTF("📤 Publishing to topic: %s\n", topic);
  DEBUG_PRINTF("📄 Payload length: %d bytes (MQTT limit: %d bytes)\n", strlen(payload), MQTT_MAX_PACKET_SIZE);
  
  // ✅ ENHANCED: Check payload size before attempting publish
  int payload_length = strlen(payload);
  if (payload_length > MQTT_MAX_PACKET_SIZE - 50) {
    DEBUG_PRINTF("❌ PAYLOAD TOO LARGE: %d bytes exceeds MQTT limit of %d bytes\n", 
                 payload_length, MQTT_MAX_PACKET_SIZE - 50);
    return false;
  }
  
  // ✅ ENHANCED: Use detailed MQTT state checking instead of just connected()
  if (isMqttReallyConnected()) {
    DEBUG_PRINTF("🔍 MQTT verified as properly connected, attempting direct publish\n");
    
    // ✅ CRITICAL FIX: No retained flag for responses, only for status updates
    bool useRetained = !isResponse; // Only retain status updates, not responses
    bool success = mqttClient.publish(topic, payload, useRetained);
    
    if (success) {
      DEBUG_PRINTF("✅ Direct MQTT publish SUCCESS (%d bytes)\n", payload_length);
      
      // ✅ CRITICAL FIX: Reduced MQTT processing to prevent blocking
      for (int i = 0; i < 3; i++) { // Reduced from 10 to 3
        mqttClient.loop();
        delay(15); // Reduced from 50ms to 15ms
      }
      
      return true;
    } else {
      // ✅ ENHANCED: Better error diagnostics with MQTT state after failed publish
      int mqttState = mqttClient.state();
      bool stillConnected = mqttClient.connected();
      
      DEBUG_PRINTF("❌ Direct MQTT publish FAILED (%d bytes), queuing message\n", payload_length);
      DEBUG_PRINTF("   📊 MQTT State after failure: %d (%s)\n", mqttState, getMqttStateString(mqttState));
      DEBUG_PRINTF("   🔌 Connected status after failure: %s\n", stillConnected ? "TRUE" : "FALSE");
      DEBUG_PRINTF("   🔌 WiFi status: %s\n", wifiConnected ? "TRUE" : "FALSE");
      
      // ✅ ENHANCED: Force reconnection if state changed
      if (mqttState != 0) {
        DEBUG_PRINTF("🔄 MQTT state corrupted after publish failure, forcing reconnection\n");
        mqttConnected = false; // Force reconnection attempt in main loop
      }
      
      // MQTT publish failed, queue the message
      return queueMessage(topic, payload, isResponse);
    }
  } else {
    // ✅ ENHANCED: Better diagnostics for connection issues
    int mqttState = mqttClient.state();
    bool connected = mqttClient.connected();
    
    DEBUG_PRINTF("❌ MQTT not properly connected, queuing message (%d bytes)\n", payload_length);
    DEBUG_PRINTF("   📊 MQTT State: %d (%s)\n", mqttState, getMqttStateString(mqttState));
    DEBUG_PRINTF("   🔌 Connected status: %s\n", connected ? "TRUE" : "FALSE");
    DEBUG_PRINTF("   🔌 WiFi status: %s\n", wifiConnected ? "TRUE" : "FALSE");
    
    // Not properly connected, queue the message
    return queueMessage(topic, payload, isResponse);
  }
}



// ================================
// BEACON VALIDATOR
// ================================
bool isFacultyBeacon(BLEAdvertisedDevice& device) {
  String deviceMAC = device.getAddress().toString().c_str();
  deviceMAC.toUpperCase();

  String expectedMAC = String(FACULTY_BEACON_MAC);
  expectedMAC.toUpperCase();

  return deviceMAC.equals(expectedMAC);
}

// ================================
// BUTTON HANDLING CLASS
// ================================
class ButtonHandler {
private:
  int pinA, pinB;
  bool lastStateA, lastStateB;
  unsigned long lastDebounceA, lastDebounceB;

public:
  ButtonHandler(int buttonAPin, int buttonBPin) {
    pinA = buttonAPin;
    pinB = buttonBPin;
    lastStateA = HIGH;
    lastStateB = HIGH;
    lastDebounceA = 0;
    lastDebounceB = 0;
  }

  void init() {
    pinMode(pinA, INPUT_PULLUP);
    pinMode(pinB, INPUT_PULLUP);
    DEBUG_PRINTLN("Buttons initialized:");
    DEBUG_PRINTF("  Button A (Blue/Acknowledge): Pin %d\n", pinA);
    DEBUG_PRINTF("  Button B (Red/Busy): Pin %d\n", pinB);
  }

  void update() {
    // Add debug logging for button states - REDUCED frequency for better real-time monitoring
    static unsigned long lastDebugPrint = 0;
    bool currentA = digitalRead(pinA);
    bool currentB = digitalRead(pinB);
    
    // Print raw button states every 10 seconds instead of 2 now that it's working
    if (millis() - lastDebugPrint > 10000) {
      DEBUG_PRINTF("🔧 Button Debug - Raw states: A(Pin%d)=%s, B(Pin%d)=%s\n", 
                   pinA, currentA ? "HIGH" : "LOW", 
                   pinB, currentB ? "HIGH" : "LOW");
      DEBUG_PRINTF("🔧 Button Debug - Flag states: buttonAPressed=%s, buttonBPressed=%s\n",
                   buttonAPressed ? "TRUE" : "FALSE",
                   buttonBPressed ? "TRUE" : "FALSE");
      lastDebugPrint = millis();
    }

    // Button A (Acknowledge) handling
    bool readingA = digitalRead(pinA);
    if (readingA != lastStateA) {
      lastDebounceA = millis();
      DEBUG_PRINTF("🔧 Button A state change: %s -> %s at %lu ms (debounce timer reset)\n", 
                   lastStateA ? "HIGH" : "LOW", 
                   readingA ? "HIGH" : "LOW",
                   millis());
      
      // IMMEDIATE DETECTION - Set flag instantly on press to handle slow main loops
      if (readingA == LOW && lastStateA == HIGH) {
        buttonAPressed = true;
        DEBUG_PRINTLN("🔵 BUTTON A PRESSED - FLAG SET IMMEDIATELY (no debounce wait)!");
      }
    }

    unsigned long currentTime = millis();
    unsigned long debounceElapsed = currentTime - lastDebounceA;
    
    if (debounceElapsed > BUTTON_DEBOUNCE_DELAY) {
      if (readingA == LOW && lastStateA == HIGH) {
        buttonAPressed = true;
        DEBUG_PRINTF("🔵 BUTTON A (ACKNOWLEDGE) PRESSED - FLAG SET! (debounce: %lu ms)\n", debounceElapsed);
      }
    } else {
      // Debug why debounce is blocking
      if (readingA == LOW && lastStateA == HIGH) {
        DEBUG_PRINTF("🕐 Button A press BLOCKED by debounce (elapsed: %lu ms < required: %d ms)\n", 
                     debounceElapsed, BUTTON_DEBOUNCE_DELAY);
      }
    }
    lastStateA = readingA;

    // Button B (Busy) handling
    bool readingB = digitalRead(pinB);
    if (readingB != lastStateB) {
      lastDebounceB = millis();
      DEBUG_PRINTF("🔧 Button B state change: %s -> %s at %lu ms (debounce timer reset)\n", 
                   lastStateB ? "HIGH" : "LOW", 
                   readingB ? "HIGH" : "LOW",
                   millis());
      
      // IMMEDIATE DETECTION - Set flag instantly on press to handle slow main loops
      if (readingB == LOW && lastStateB == HIGH) {
        buttonBPressed = true;
        DEBUG_PRINTLN("🔴 BUTTON B PRESSED - FLAG SET IMMEDIATELY (no debounce wait)!");
      }
    }

    unsigned long debounceElapsedB = currentTime - lastDebounceB;
    
    if (debounceElapsedB > BUTTON_DEBOUNCE_DELAY) {
      if (readingB == LOW && lastStateB == HIGH) {
        buttonBPressed = true;
        DEBUG_PRINTF("🔴 BUTTON B (BUSY) PRESSED - FLAG SET! (debounce: %lu ms)\n", debounceElapsedB);
      }
    } else {
      // Debug why debounce is blocking
      if (readingB == LOW && lastStateB == HIGH) {
        DEBUG_PRINTF("🕐 Button B press BLOCKED by debounce (elapsed: %lu ms < required: %d ms)\n", 
                     debounceElapsedB, BUTTON_DEBOUNCE_DELAY);
      }
    }
    lastStateB = readingB;
  }

  bool isButtonAPressed() {
    if (buttonAPressed) {
      DEBUG_PRINTLN("🔵 Button A flag was SET, clearing and returning TRUE");
      buttonAPressed = false;
      return true;
    }
    return false;
  }

  bool isButtonBPressed() {
    if (buttonBPressed) {
      DEBUG_PRINTLN("🔴 Button B flag was SET, clearing and returning TRUE");
      buttonBPressed = false;
      return true;
    }
    return false;
  }
};

// ================================
// ENHANCED PRESENCE DETECTOR WITH GRACE PERIOD
// ================================
class BooleanPresenceDetector {
private:
  bool currentPresence = false;           // Current confirmed status
  bool lastKnownPresence = false;         // Last status before disconnection
  unsigned long lastDetectionTime = 0;   // Last successful BLE detection
  unsigned long lastStateChange = 0;      // Last confirmed status change
  unsigned long gracePeriodStartTime = 0; // When grace period started

  // Grace period state
  bool inGracePeriod = false;
  int gracePeriodAttempts = 0;

  // Detection counters for immediate detection
  int consecutiveDetections = 0;
  int consecutiveMisses = 0;

  const int CONFIRM_SCANS = 2;            // Scans needed to confirm presence
  const int CONFIRM_ABSENCE_SCANS = 3;    // More scans needed to confirm absence

public:
  void checkBeacon(bool beaconFound, int rssi = 0) {
    unsigned long now = millis();

    if (beaconFound) {
      // Beacon detected!
      lastDetectionTime = now;
      consecutiveDetections++;
      consecutiveMisses = 0;

      // Optional RSSI filtering for better reliability
      if (rssi != 0 && rssi < BLE_SIGNAL_STRENGTH_THRESHOLD) {
        DEBUG_PRINTF("⚠️ Beacon found but signal weak: %d dBm (threshold: %d)\n",
                    rssi, BLE_SIGNAL_STRENGTH_THRESHOLD);
        return; // Ignore weak signals
      }

      // If we were in grace period, cancel it
      if (inGracePeriod) {
        DEBUG_PRINTF("✅ BLE reconnected during grace period! (attempt %d/%d)\n",
                   gracePeriodAttempts, BLE_RECONNECT_MAX_ATTEMPTS);
        endGracePeriod(true); // Successfully reconnected
      }

      // Confirm presence if we have enough detections
      if (consecutiveDetections >= CONFIRM_SCANS && !currentPresence) {
        updatePresenceStatus(true, now);
      }

    } else {
      // Beacon NOT detected
      consecutiveMisses++;
      consecutiveDetections = 0;

      // Handle absence detection
      if (currentPresence && consecutiveMisses >= CONFIRM_ABSENCE_SCANS) {
        // Professor was present but now we can't detect beacon
        if (!inGracePeriod) {
          startGracePeriod(now);
        } else {
          updateGracePeriod(now);
        }
      } else if (!currentPresence) {
        // Professor was already away, continue normal operation
        inGracePeriod = false;
      }
    }
  }

private:
  void startGracePeriod(unsigned long now) {
    inGracePeriod = true;
    gracePeriodStartTime = now;
    gracePeriodAttempts = 0;
    lastKnownPresence = currentPresence; // Remember status before grace period

    DEBUG_PRINTF("⏳ Starting grace period - Professor was PRESENT, giving %d seconds to reconnect...\n",
                BLE_GRACE_PERIOD_MS / 1000);

    // Note: No display changes - your existing display will continue showing "AVAILABLE"
    // until grace period expires, which is exactly what we want!
  }

  void updateGracePeriod(unsigned long now) {
    gracePeriodAttempts++;

    unsigned long elapsed = now - gracePeriodStartTime;
    unsigned long remaining = BLE_GRACE_PERIOD_MS - elapsed;

    DEBUG_PRINTF("⏳ Grace period: attempt %d/%d | %lu seconds remaining\n",
                gracePeriodAttempts, BLE_RECONNECT_MAX_ATTEMPTS, remaining / 1000);

    // Check if grace period expired
    if (elapsed >= BLE_GRACE_PERIOD_MS || gracePeriodAttempts >= BLE_RECONNECT_MAX_ATTEMPTS) {
      DEBUG_PRINTLN("⏰ Grace period expired - Professor confirmed AWAY");
      endGracePeriod(false); // Grace period failed
    }
  }

  void endGracePeriod(bool reconnected) {
    inGracePeriod = false;
    gracePeriodAttempts = 0;

    if (reconnected) {
      // Beacon reconnected - maintain PRESENT status
      DEBUG_PRINTLN("🔄 Grace period ended - Professor still PRESENT (reconnected)");
      // Status doesn't change, just clear grace period state
      // Display will continue showing "AVAILABLE" - no change needed!
    } else {
      // Grace period expired - confirm AWAY
      DEBUG_PRINTLN("🔄 Grace period expired - Professor confirmed AWAY");
      updatePresenceStatus(false, millis());
    }
  }

  void updatePresenceStatus(bool newPresence, unsigned long now) {
    if (newPresence != currentPresence) {
      currentPresence = newPresence;
      lastStateChange = now;

      DEBUG_PRINTF("🔄 Professor status CONFIRMED: %s\n",
                 currentPresence ? "PRESENT" : "AWAY");

      // Reset counters
      consecutiveDetections = 0;
      consecutiveMisses = 0;

      // Update systems
      publishPresenceUpdate();
      updateMainDisplay(); // This will call your existing display function
    }
  }

public:
  // Public getters (keeping your existing interface)
  bool getPresence() const {
    // During grace period, still return true (professor considered present)
    if (inGracePeriod) {
      return lastKnownPresence;
    }
    return currentPresence;
  }

  String getStatusString() const {
    // During grace period, maintain last known status
    if (inGracePeriod) {
      return lastKnownPresence ? "AVAILABLE" : "AWAY";
    }
    return currentPresence ? "AVAILABLE" : "AWAY";
  }

  // Additional methods for debugging (optional)
  bool isInGracePeriod() const { return inGracePeriod; }

  unsigned long getGracePeriodRemaining() const {
    if (!inGracePeriod) return 0;
    unsigned long elapsed = millis() - gracePeriodStartTime;
    return elapsed < BLE_GRACE_PERIOD_MS ? (BLE_GRACE_PERIOD_MS - elapsed) : 0;
  }

  String getDetailedStatus() const {
    if (inGracePeriod) {
      unsigned long remaining = getGracePeriodRemaining() / 1000;
      return "AVAILABLE (reconnecting... " + String(remaining) + "s)";
    }
    return getStatusString();
  }
};

// ================================
// ADAPTIVE BLE SCANNER CLASS (Enhanced for Grace Period)
// ================================
class AdaptiveBLEScanner {
private:
    enum ScanMode {
        SEARCHING,      // Looking for professor (frequent scans)
        MONITORING,     // Professor present (occasional scans)
        VERIFYING       // Confirming state change
    };

    ScanMode currentMode = SEARCHING;
    unsigned long lastScanTime = 0;
    unsigned long modeChangeTime = 0;
    unsigned long statsReportTime = 0;

    // Detection counters
    int consecutiveDetections = 0;
    int consecutiveMisses = 0;

    // Reference to presence detector (will be set in init)
    BooleanPresenceDetector* presenceDetectorPtr = nullptr;

    // Performance stats
    struct {
        unsigned long totalScans = 0;
        unsigned long successfulDetections = 0;
        unsigned long gracePeriodActivations = 0;
        unsigned long gracePeriodSuccesses = 0;
        unsigned long timeInSearching = 0;
        unsigned long timeInMonitoring = 0;
        unsigned long timeInVerifying = 0;
        unsigned long lastModeStart = 0;
    } stats;

    // Dynamic intervals based on mode and grace period
    unsigned long getCurrentScanInterval() {
        // During grace period, scan more frequently to catch reconnections
        if (presenceDetectorPtr && presenceDetectorPtr->isInGracePeriod()) {
            return BLE_RECONNECT_ATTEMPT_INTERVAL;
        }

        switch(currentMode) {
            case SEARCHING: return BLE_SCAN_INTERVAL_SEARCHING;
            case MONITORING: return BLE_SCAN_INTERVAL_MONITORING;
            case VERIFYING: return BLE_SCAN_INTERVAL_VERIFICATION;
            default: return BLE_SCAN_INTERVAL_SEARCHING;
        }
    }

    int getCurrentScanDuration() {
        // During grace period, use quick scans to save power while still being responsive
        if (presenceDetectorPtr && presenceDetectorPtr->isInGracePeriod()) {
            return BLE_SCAN_DURATION_QUICK;
        }

        switch(currentMode) {
            case SEARCHING: return BLE_SCAN_DURATION_FULL;
            case MONITORING: return BLE_SCAN_DURATION_QUICK;
            case VERIFYING: return BLE_SCAN_DURATION_QUICK;
            default: return BLE_SCAN_DURATION_FULL;
        }
    }

    void updateStats(unsigned long now) {
        // Update time in current mode
        unsigned long timeInMode = now - stats.lastModeStart;
        switch(currentMode) {
            case SEARCHING: stats.timeInSearching += timeInMode; break;
            case MONITORING: stats.timeInMonitoring += timeInMode; break;
            case VERIFYING: stats.timeInVerifying += timeInMode; break;
        }
        stats.lastModeStart = now;

        // Report stats periodically
        if (now - statsReportTime > BLE_STATS_REPORT_INTERVAL) {
            reportStats();
            statsReportTime = now;
        }
    }

    void reportStats() {
        unsigned long totalTime = stats.timeInSearching + stats.timeInMonitoring + stats.timeInVerifying;
        if (totalTime > 0) {
            float searchingPercent = (stats.timeInSearching * 100.0) / totalTime;
            float monitoringPercent = (stats.timeInMonitoring * 100.0) / totalTime;
            float verifyingPercent = (stats.timeInVerifying * 100.0) / totalTime;
            float successRate = (stats.successfulDetections * 100.0) / max(stats.totalScans, 1UL);
            float gracePeriodSuccessRate = stats.gracePeriodActivations > 0 ?
                                         (stats.gracePeriodSuccesses * 100.0) / stats.gracePeriodActivations : 0;

            DEBUG_PRINTLN("📊 === BLE SCANNER STATS (WITH GRACE PERIOD) ===");
            DEBUG_PRINTF("   Total Scans: %lu | Success Rate: %.1f%%\n",
                        stats.totalScans, successRate);
            DEBUG_PRINTF("   Grace Periods: %lu activated | %.1f%% successful reconnections\n",
                        stats.gracePeriodActivations, gracePeriodSuccessRate);
            DEBUG_PRINTF("   Time Distribution - Searching: %.1f%% | Monitoring: %.1f%% | Verifying: %.1f%%\n",
                        searchingPercent, monitoringPercent, verifyingPercent);
            DEBUG_PRINTF("   Current Mode: %s | Interval: %lums\n",
                        getModeString().c_str(), getCurrentScanInterval());
        }
    }

public:
    void init(BooleanPresenceDetector* detector) {
        presenceDetectorPtr = detector;
        currentMode = SEARCHING;
        lastScanTime = 0;
        modeChangeTime = millis();
        statsReportTime = millis();
        stats.lastModeStart = millis();

        DEBUG_PRINTLN("🔍 Adaptive BLE Scanner with Grace Period initialized");
        DEBUG_PRINTF("   Searching Mode: %dms interval, %ds duration\n",
                    BLE_SCAN_INTERVAL_SEARCHING, BLE_SCAN_DURATION_FULL);
        DEBUG_PRINTF("   Monitoring Mode: %dms interval, %ds duration\n",
                    BLE_SCAN_INTERVAL_MONITORING, BLE_SCAN_DURATION_QUICK);
        DEBUG_PRINTF("   Grace Period: %ds with %dms reconnect attempts\n",
                    BLE_GRACE_PERIOD_MS / 1000, BLE_RECONNECT_ATTEMPT_INTERVAL);
    }

    void update() {
        if (!presenceDetectorPtr) return;  // Safety check

        unsigned long now = millis();
        unsigned long interval = getCurrentScanInterval();

        // Check if it's time to scan
        if (now - lastScanTime < interval) return;

        // Update stats before scanning
        updateStats(now);

        // Perform adaptive scan
        bool beaconFound = performScan();
        lastScanTime = now;
        stats.totalScans++;

        if (beaconFound) {
            stats.successfulDetections++;
            consecutiveDetections++;
            consecutiveMisses = 0;
        } else {
            consecutiveMisses++;
            consecutiveDetections = 0;
        }

        // Smart mode switching (enhanced for grace period)
        updateScanMode(beaconFound, now);

        // Send to presence detector (this handles grace period logic)
        presenceDetectorPtr->checkBeacon(beaconFound);

        // Debug info (show grace period status)
        if (stats.totalScans % 10 == 0 || beaconFound || presenceDetectorPtr->isInGracePeriod()) {
            String gracePeriodInfo = "";
            if (presenceDetectorPtr->isInGracePeriod()) {
                unsigned long remaining = presenceDetectorPtr->getGracePeriodRemaining() / 1000;
                gracePeriodInfo = " | GRACE: " + String(remaining) + "s";
            }

            DEBUG_PRINTF("🔍 BLE Scan #%lu: %s | Mode: %s%s | Next: %lums\n",
                        stats.totalScans,
                        beaconFound ? "✅ FOUND" : "❌ MISS",
                        getModeString().c_str(),
                        gracePeriodInfo.c_str(),
                        interval);
        }
    }

    // Get current scanning statistics
    String getStatsString() {
        float efficiency = 0;
        unsigned long totalActiveTime = stats.timeInSearching + stats.timeInMonitoring;
        if (totalActiveTime > 0) {
            efficiency = (stats.timeInMonitoring * 100.0) / totalActiveTime;
        }

        String modeStr = getModeString().substring(0, 3);
        if (presenceDetectorPtr && presenceDetectorPtr->isInGracePeriod()) {
            modeStr = "GRC"; // Grace period indicator
        }

        return modeStr + ":" + String(efficiency, 0) + "%";
    }

private:
    bool performScan() {
        int duration = getCurrentScanDuration();

        // Add error handling for BLE scan
        BLEScanResults* results = nullptr;
        bool beaconDetected = false;
        int bestRSSI = -999;

        try {
            results = pBLEScan->start(duration, false);

            if (results && results->getCount() > 0) {
                for (int i = 0; i < results->getCount(); i++) {
                    BLEAdvertisedDevice device = results->getDevice(i);
                    if (isFacultyBeacon(device)) {
                        beaconDetected = true;
                        bestRSSI = device.getRSSI();

                        // Log RSSI occasionally for signal strength monitoring
                        if (stats.totalScans % 20 == 0) {
                            DEBUG_PRINTF("📶 Beacon RSSI: %d dBm\n", bestRSSI);
                        }
                        break;
                    }
                }
            }

            pBLEScan->clearResults();

        } catch (...) {
            DEBUG_PRINTLN("⚠️ BLE scan error - continuing");
            beaconDetected = false;
        }

        return beaconDetected;
    }

    void updateScanMode(bool beaconFound, unsigned long now) {
        ScanMode newMode = currentMode;

        switch(currentMode) {
            case SEARCHING:
                // Switch to verification after consistent detections
                if (consecutiveDetections >= 2) {
                    newMode = VERIFYING;
                    DEBUG_PRINTLN("📡 BLE Mode: SEARCHING -> VERIFYING (beacon detected)");
                }
                break;

            case MONITORING:
                // Switch to verification if beacon goes missing
                if (consecutiveMisses >= 2) {
                    newMode = VERIFYING;
                    DEBUG_PRINTLN("📡 BLE Mode: MONITORING -> VERIFYING (beacon lost)");
                }
                break;

            case VERIFYING:
                // Stay in verification for minimum time, then decide
                if (now - modeChangeTime > PRESENCE_CONFIRM_TIME) {
                    if (consecutiveDetections > consecutiveMisses) {
                        newMode = MONITORING;
                        DEBUG_PRINTLN("📡 BLE Mode: VERIFYING -> MONITORING (presence confirmed)");
                    } else {
                        newMode = SEARCHING;
                        DEBUG_PRINTLN("📡 BLE Mode: VERIFYING -> SEARCHING (absence confirmed)");
                    }
                }
                break;
        }

        // Execute mode change
        if (newMode != currentMode) {
            // Update stats for old mode
            updateStats(now);

            // Change mode
            currentMode = newMode;
            modeChangeTime = now;
            consecutiveDetections = 0;
            consecutiveMisses = 0;

            DEBUG_PRINTF("🔄 New scan interval: %lums, duration: %ds\n",
                        getCurrentScanInterval(), getCurrentScanDuration());
        }
    }

    String getModeString() {
        switch(currentMode) {
            case SEARCHING: return "SEARCHING";
            case MONITORING: return "MONITORING";
            case VERIFYING: return "VERIFYING";
            default: return "UNKNOWN";
        }
    }
};

// ================================
// GLOBAL INSTANCES (CORRECT ORDER)
// ================================
BooleanPresenceDetector presenceDetector;
ButtonHandler buttons(BUTTON_A_PIN, BUTTON_B_PIN);
AdaptiveBLEScanner adaptiveScanner;

// ================================
// BLE CALLBACK CLASS
// ================================
class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice advertisedDevice) {}
};

// ================================
// SIMPLE UI HELPER FUNCTIONS
// ================================
void drawSimpleCard(int x, int y, int w, int h, uint16_t color) {
  tft.fillRect(x, y, w, h, color);
  tft.drawRect(x, y, w, h, COLOR_ACCENT);
}

void drawStatusIndicator(int x, int y, bool available) {
  int radius = 12;
  if (available) {
    if (animationState) {
      tft.fillCircle(x, y, radius + 2, COLOR_SUCCESS);
      tft.fillCircle(x, y, radius, COLOR_ACCENT);
    } else {
      tft.fillCircle(x, y, radius, COLOR_SUCCESS);
    }
    tft.fillCircle(x, y, radius - 4, COLOR_WHITE);
    tft.fillCircle(x, y, 3, COLOR_SUCCESS);
  } else {
    tft.fillCircle(x, y, radius, COLOR_ERROR);
    tft.fillCircle(x, y, radius - 4, COLOR_WHITE);
    tft.fillCircle(x, y, 3, COLOR_ERROR);
  }
}

int getCenterX(String text, int textSize) {
  int charWidth = 6 * textSize;
  int textWidth = text.length() * charWidth;
  return (SCREEN_WIDTH - textWidth) / 2;
}

// ================================
// MESSAGE DISPLAY WITH ENHANCED CONSULTATION REQUEST HANDLING
// ================================
void displayIncomingMessage(String message) {
  // For backward compatibility, parse and display using the new queue system
  ConsultationMessage tempMessage;
  parseConsultationMessage(message, g_receivedConsultationId, tempMessage);
  displayQueuedConsultation(tempMessage);
}

// ================================
// BUTTON RESPONSE FUNCTIONS
// ================================
void handleAcknowledgeButton() {
  DEBUG_PRINTLN("🔵 handleAcknowledgeButton() called!");
  
  // Debug all the conditions that could cause early return
  DEBUG_PRINTF("   messageDisplayed: %s\n", messageDisplayed ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   currentMessage.isEmpty(): %s\n", currentMessage.isEmpty() ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   currentMessage content: '%s'\n", currentMessage.c_str());
  
  if (!messageDisplayed || currentMessage.isEmpty()) {
    DEBUG_PRINTLN("❌ EARLY RETURN: No message displayed or message is empty");
    return;
  }

  // Check if faculty is present before allowing response
  bool facultyPresent = presenceDetector.getPresence();
  DEBUG_PRINTF("   Faculty present: %s\n", facultyPresent ? "TRUE" : "FALSE");
  
  if (!facultyPresent) {
    DEBUG_PRINTLN("❌ Cannot send ACKNOWLEDGE: Faculty not present");
    showResponseConfirmation("NOT PRESENT!", COLOR_ERROR);
    return;
  }

  DEBUG_PRINTF("   g_receivedConsultationId: '%s'\n", g_receivedConsultationId.c_str());
  DEBUG_PRINTF("   g_receivedConsultationId.isEmpty(): %s\n", g_receivedConsultationId.isEmpty() ? "TRUE" : "FALSE");
  
  if (g_receivedConsultationId.isEmpty()) {
    DEBUG_PRINTLN("❌ Cannot send ACKNOWLEDGE: Missing Consultation ID (CID).");
    showResponseConfirmation("NO CID!", COLOR_ERROR);
    return;
  }

  DEBUG_PRINTLN("📤 Sending ACKNOWLEDGE response to central terminal");
  DEBUG_PRINTF("   MQTT connected: %s\n", mqttClient.connected() ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   WiFi connected: %s\n", wifiConnected ? "TRUE" : "FALSE");

  // Create acknowledge response with enhanced data
  String response = "{";
  response += "\"faculty_id\":" + String(FACULTY_ID) + ",";
  response += "\"faculty_name\":\"" + String(FACULTY_NAME) + "\",";
  response += "\"response_type\":\"ACKNOWLEDGE\",";
  response += "\"message_id\":\"" + g_receivedConsultationId + "\",";
  // ✅ REMOVED: original_message field to reduce payload size
  response += "\"timestamp\":\"" + String(millis()) + "\",";
  response += "\"faculty_present\":true,";
  response += "\"response_method\":\"physical_button\",";
  response += "\"status\":\"Professor acknowledges the request and will respond accordingly\"";
  response += "}";

  DEBUG_PRINTF("📝 Response JSON (%d bytes): %s\n", response.length(), response.c_str());
  DEBUG_PRINTF("📡 Publishing to topic: %s\n", MQTT_TOPIC_RESPONSES);
  
  // ✅ CRITICAL CHECK: Verify payload size before publishing
  if (response.length() > MQTT_MAX_PACKET_SIZE - 50) { // Leave 50 bytes margin for MQTT headers
    DEBUG_PRINTF("⚠️ WARNING: Payload size %d bytes may exceed MQTT limit!\n", response.length());
  }

  // Publish response with offline queuing support
  bool success = publishWithQueue(MQTT_TOPIC_RESPONSES, response.c_str(), true);
  DEBUG_PRINTF("   publishWithQueue result: %s\n", success ? "SUCCESS" : "FAILED");
  
  if (success) {
    if (mqttClient.connected()) {
      DEBUG_PRINTLN("✅ ACKNOWLEDGE response sent successfully");
      DEBUG_PRINTF("📡 Response sent to central system via topic: %s\n", MQTT_TOPIC_RESPONSES);
      showResponseConfirmation("ACKNOWLEDGED", COLOR_BLUE);
    } else {
      DEBUG_PRINTLN("📥 ACKNOWLEDGE response queued (offline)");
      DEBUG_PRINTF("📥 Response queued for central system, queue size: %d\n", queueCount);
      showResponseConfirmation("QUEUED", COLOR_WARNING);
    }
  } else {
    DEBUG_PRINTLN("❌ Failed to send/queue ACKNOWLEDGE response");
    DEBUG_PRINTF("❌ Central system communication failed for topic: %s\n", MQTT_TOPIC_RESPONSES);
    showResponseConfirmation("FAILED", COLOR_ERROR);
  }

  // Clear message
  DEBUG_PRINTLN("🧹 Calling clearCurrentMessage()");
  updateMessageLED(); 
  clearCurrentMessage();
}

void handleBusyButton() {
  DEBUG_PRINTLN("🔴 handleBusyButton() called!");
  
  // Debug all the conditions that could cause early return
  DEBUG_PRINTF("   messageDisplayed: %s\n", messageDisplayed ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   currentMessage.isEmpty(): %s\n", currentMessage.isEmpty() ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   currentMessage content: '%s'\n", currentMessage.c_str());
  
  if (!messageDisplayed || currentMessage.isEmpty()) {
    DEBUG_PRINTLN("❌ EARLY RETURN: No message displayed or message is empty");
    return;
  }

  // Check if faculty is present before allowing response
  bool facultyPresent = presenceDetector.getPresence();
  DEBUG_PRINTF("   Faculty present: %s\n", facultyPresent ? "TRUE" : "FALSE");
  
  if (!facultyPresent) {
    DEBUG_PRINTLN("❌ Cannot send BUSY: Faculty not present");
    showResponseConfirmation("NOT PRESENT!", COLOR_ERROR);
    return;
  }

  DEBUG_PRINTF("   g_receivedConsultationId: '%s'\n", g_receivedConsultationId.c_str());
  DEBUG_PRINTF("   g_receivedConsultationId.isEmpty(): %s\n", g_receivedConsultationId.isEmpty() ? "TRUE" : "FALSE");
  
  if (g_receivedConsultationId.isEmpty()) {
    DEBUG_PRINTLN("❌ Cannot send BUSY: Missing Consultation ID (CID).");
    showResponseConfirmation("NO CID!", COLOR_ERROR);
    return;
  }

  DEBUG_PRINTLN("📤 Sending BUSY response to central terminal");
  DEBUG_PRINTF("   MQTT connected: %s\n", mqttClient.connected() ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   WiFi connected: %s\n", wifiConnected ? "TRUE" : "FALSE");

  // Create busy response with enhanced data
  String response = "{";
  response += "\"faculty_id\":" + String(FACULTY_ID) + ",";
  response += "\"faculty_name\":\"" + String(FACULTY_NAME) + "\",";
  response += "\"response_type\":\"BUSY\",";
  response += "\"message_id\":\"" + g_receivedConsultationId + "\",";
  // ✅ REMOVED: original_message field to reduce payload size
  response += "\"timestamp\":\"" + String(millis()) + "\",";
  response += "\"faculty_present\":true,";
  response += "\"response_method\":\"physical_button\",";
  response += "\"status\":\"Professor is currently busy and cannot cater to this request\"";
  response += "}";

  DEBUG_PRINTF("📝 Response JSON (%d bytes): %s\n", response.length(), response.c_str());
  DEBUG_PRINTF("📡 Publishing to topic: %s\n", MQTT_TOPIC_RESPONSES);
  
  // ✅ CRITICAL CHECK: Verify payload size before publishing
  if (response.length() > MQTT_MAX_PACKET_SIZE - 50) { // Leave 50 bytes margin for MQTT headers
    DEBUG_PRINTF("⚠️ WARNING: Payload size %d bytes may exceed MQTT limit!\n", response.length());
  }

  // Publish response with offline queuing support
  bool success = publishWithQueue(MQTT_TOPIC_RESPONSES, response.c_str(), true);
  DEBUG_PRINTF("   publishWithQueue result: %s\n", success ? "SUCCESS" : "FAILED");
  
  if (success) {
    if (mqttClient.connected()) {
      DEBUG_PRINTLN("✅ BUSY response sent successfully");
      DEBUG_PRINTF("📡 Response sent to central system via topic: %s\n", MQTT_TOPIC_RESPONSES);
      showResponseConfirmation("MARKED BUSY", COLOR_ERROR);
    } else {
      DEBUG_PRINTLN("📥 BUSY response queued (offline)");
      DEBUG_PRINTF("📥 Response queued for central system, queue size: %d\n", queueCount);
      showResponseConfirmation("QUEUED", COLOR_WARNING);
    }
  } else {
    DEBUG_PRINTLN("❌ Failed to send/queue BUSY response");
    DEBUG_PRINTF("❌ Central system communication failed for topic: %s\n", MQTT_TOPIC_RESPONSES);
    showResponseConfirmation("FAILED", COLOR_ERROR);
  }

  // Clear message
  DEBUG_PRINTLN("🧹 Calling clearCurrentMessage()");
  updateMessageLED(); 
  clearCurrentMessage();
}

void showResponseConfirmation(String confirmText, uint16_t color) {
  // Clear main area
  tft.fillRect(0, MAIN_AREA_Y, SCREEN_WIDTH, MAIN_AREA_HEIGHT, COLOR_WHITE);

  // Show confirmation card
  drawSimpleCard(20, STATUS_CENTER_Y - 30, 280, 60, color);

  int confirmX = getCenterX(confirmText, 2);
  tft.setCursor(confirmX, STATUS_CENTER_Y - 15);
  tft.setTextSize(2);
  tft.setTextColor(COLOR_WHITE);
  tft.print(confirmText);

  tft.setCursor(getCenterX("Response Sent", 1), STATUS_CENTER_Y + 10);
  tft.setTextSize(1);
  tft.setTextColor(COLOR_WHITE);
  tft.print("Response Sent");

  delay(CONFIRMATION_DISPLAY_TIME);
}

void clearCurrentMessage() {
  DEBUG_PRINTLN("📱 Consultation message dismissed via physical button");
  currentMessage = "";
  messageDisplayed = false;
  messageDisplayStart = 0;
  g_receivedConsultationId = "";
  currentMessageDisplayed = false;
  
  // 🆕 UPDATE LED STATUS
  updateMessageLED();
  
  // Process next consultation in queue
  processNextQueuedConsultation();
}

// ================================
// WIFI FUNCTIONS
// ================================

// Enhanced WiFi connection variables
int wifiRetryCount = 0;
unsigned long lastWifiReconnectAttempt = 0;
int maxWifiRetries = 10;
int wifiReconnectDelay = 5000;  // Base delay, will increase exponentially
int currentWifiRSSI = -100;
bool wifiConnectionStable = false;
unsigned long wifiStableTime = 0;

void setupWiFi() {
  DEBUG_PRINT("🔧 Enhanced WiFi setup - Connecting to: ");
  DEBUG_PRINTLN(WIFI_SSID);

  // Configure WiFi for maximum reliability
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(false); // We handle reconnection manually for better control
  
  // Disable power management for stable connection
  WiFi.setSleep(false);
  
  wifiRetryCount = 0;
  connectWiFiWithBackoff();
}

void connectWiFiWithBackoff() {
  if (wifiRetryCount >= maxWifiRetries) {
    DEBUG_PRINTF("❌ WiFi connection failed after %d attempts\n", maxWifiRetries);
    wifiConnected = false;
    updateSystemStatus();
    return;
  }

  DEBUG_PRINTF("📡 WiFi connection attempt %d/%d\n", wifiRetryCount + 1, maxWifiRetries);
  
  // Disconnect any existing connection
  WiFi.disconnect(true);
  delay(500);
  
  // Start new connection
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  unsigned long startTime = millis();
  unsigned long timeout = WIFI_CONNECT_TIMEOUT + (wifiRetryCount * 5000); // Increase timeout with retries
  
  while (WiFi.status() != WL_CONNECTED && (millis() - startTime) < timeout) {
    delay(500);
    DEBUG_PRINT(".");
    updateSystemStatus();
    
    // Check for specific error conditions
    wl_status_t status = WiFi.status();
    if (status == WL_CONNECT_FAILED) {
      DEBUG_PRINTF("\n❌ WiFi connection failed with status: %d\n", status);
      break;
    }
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    wifiRetryCount = 0; // Reset retry count on successful connection
    wifiStableTime = millis();
    wifiConnectionStable = false; // Will be set to true after stability period
    
    currentWifiRSSI = WiFi.RSSI();
    DEBUG_PRINTF("\n✅ WiFi connected! IP: %s, RSSI: %d dBm\n", 
                WiFi.localIP().toString().c_str(), currentWifiRSSI);
    
    // Check connection quality
    if (currentWifiRSSI > -70) {
      DEBUG_PRINTLN("📶 Excellent signal strength");
    } else if (currentWifiRSSI > -80) {
      DEBUG_PRINTLN("📶 Good signal strength");
    } else {
      DEBUG_PRINTLN("⚠️ Weak signal strength - may cause instability");
    }
    
    setupTimeWithRetry();
    updateSystemStatus();
  } else {
    wifiConnected = false;
    wifiRetryCount++;
    
    // Calculate exponential backoff delay
    int backoffDelay = wifiReconnectDelay * (1 << min(wifiRetryCount - 1, 4)); // Cap at 16x base delay
    
    DEBUG_PRINTF("\n❌ WiFi connection failed! Retry in %d seconds\n", backoffDelay / 1000);
    lastWifiReconnectAttempt = millis();
    wifiReconnectDelay = backoffDelay;
    updateSystemStatus();
  }
}

void checkWiFiConnection() {
  unsigned long now = millis();
  
  // Check if WiFi is still connected
  if (WiFi.status() != WL_CONNECTED) {
    if (wifiConnected) {
      DEBUG_PRINTLN("⚠️ WiFi connection lost!");
      wifiConnected = false;
      wifiConnectionStable = false;
      timeInitialized = false;
      mqttConnected = false; // Force MQTT reconnection
      updateSystemStatus();
    }

    // Attempt reconnection with backoff
    if (now - lastWifiReconnectAttempt > wifiReconnectDelay) {
      connectWiFiWithBackoff();
    }
  } else {
    // WiFi is connected - monitor quality and stability
    if (!wifiConnected) {
      DEBUG_PRINTLN("✅ WiFi reconnected!");
      wifiConnected = true;
      wifiStableTime = millis();
      wifiConnectionStable = false;
      setupTimeWithRetry();
      updateSystemStatus();
    }
    
    // Check connection stability (mark as stable after 30 seconds)
    if (!wifiConnectionStable && (now - wifiStableTime > 30000)) {
      wifiConnectionStable = true;
      DEBUG_PRINTLN("🔒 WiFi connection is now stable");
      wifiRetryCount = 0; // Reset retry count after stable connection
      wifiReconnectDelay = 5000; // Reset delay
    }
    
    // Monitor signal strength every 30 seconds
    static unsigned long lastRSSICheck = 0;
    if (now - lastRSSICheck > 30000) {
      int newRSSI = WiFi.RSSI();
      if (abs(newRSSI - currentWifiRSSI) > 10) { // Significant change
        DEBUG_PRINTF("📶 Signal strength changed: %d dBm -> %d dBm\n", currentWifiRSSI, newRSSI);
        currentWifiRSSI = newRSSI;
        
        // Warn about poor signal quality
        if (currentWifiRSSI < -85) {
          DEBUG_PRINTLN("⚠️ Poor signal quality - connection may become unstable");
        }
      }
      lastRSSICheck = now;
    }
  }
}

// ================================
// ENHANCED NTP TIME FUNCTIONS
// ================================
void setupTimeWithRetry() {
  DEBUG_PRINTLN("Setting up enhanced NTP time synchronization...");
  ntpSyncInProgress = true;
  ntpRetryCount = 0;
  ntpSyncStatus = "SYNCING";

  // Try multiple NTP servers for better reliability
  configTime(TIME_ZONE_OFFSET * 3600, 0, NTP_SERVER_PRIMARY, NTP_SERVER_SECONDARY, NTP_SERVER_TERTIARY);

  unsigned long startTime = millis();
  struct tm timeinfo;

  while (!getLocalTime(&timeinfo) && (millis() - startTime) < NTP_SYNC_TIMEOUT) {
    delay(1000);
    DEBUG_PRINT(".");
    updateSystemStatus(); // Update display during sync
  }

  if (getLocalTime(&timeinfo)) {
    timeInitialized = true;
    ntpSyncInProgress = false;
    ntpSyncStatus = "SYNCED";
    ntpRetryCount = 0;
    DEBUG_PRINTLN(" Time synced successfully!");
    DEBUG_PRINTF("Current time: %04d-%02d-%02d %02d:%02d:%02d\n",
                timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday,
                timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
    updateTimeAndDate();
    updateSystemStatus();

    // Publish NTP sync status to central system
    publishNtpSyncStatus(true);
  } else {
    timeInitialized = false;
    ntpSyncInProgress = false;
    ntpSyncStatus = "FAILED";
    ntpRetryCount++;
    DEBUG_PRINTLN(" Time sync failed!");

    // Publish NTP sync failure to central system
    publishNtpSyncStatus(false);
  }
}

void updateTimeAndDate() {
  if (!wifiConnected) {
    if (lastDisplayedTime != "OFFLINE") {
      lastDisplayedTime = "OFFLINE";
      lastDisplayedDate = "NO WIFI";

      tft.fillRect(TIME_X, TIME_Y, 120, 15, COLOR_PANEL);
      tft.setCursor(TIME_X, TIME_Y);
      tft.setTextColor(COLOR_ERROR);
      tft.setTextSize(1);
      tft.print("TIME: OFFLINE");

      tft.fillRect(DATE_X - 60, DATE_Y, 70, 15, COLOR_PANEL);
      tft.setCursor(DATE_X - 60, DATE_Y);
      tft.setTextColor(COLOR_ERROR);
      tft.setTextSize(1);
      tft.print("NO WIFI");
    }
    return;
  }

  struct tm timeinfo;
  if (getLocalTime(&timeinfo) && timeInitialized) {
    char timeStr[12];
    strftime(timeStr, sizeof(timeStr), "%H:%M:%S", &timeinfo);

    char dateStr[15];
    strftime(dateStr, sizeof(dateStr), "%b %d, %Y", &timeinfo);

    String currentTimeStr = String(timeStr);
    String currentDateStr = String(dateStr);

    if (currentTimeStr != lastDisplayedTime) {
      lastDisplayedTime = currentTimeStr;

      tft.fillRect(TIME_X, TIME_Y, 120, 15, COLOR_PANEL);
      tft.setCursor(TIME_X, TIME_Y);
      tft.setTextColor(COLOR_ACCENT);
      tft.setTextSize(1);
      tft.print("TIME: ");
      tft.print(timeStr);
    }

    if (currentDateStr != lastDisplayedDate) {
      lastDisplayedDate = currentDateStr;

      tft.fillRect(DATE_X - 90, DATE_Y, 90, 15, COLOR_PANEL);
      tft.setCursor(DATE_X - 90, DATE_Y);
      tft.setTextColor(COLOR_ACCENT);
      tft.setTextSize(1);
      tft.print("DATE: ");
      tft.print(dateStr);
    }
  } else {
    if (lastDisplayedTime != "SYNCING") {
      lastDisplayedTime = "SYNCING";
      lastDisplayedDate = "SYNCING";

      tft.fillRect(TIME_X, TIME_Y, 120, 15, COLOR_PANEL);
      tft.setCursor(TIME_X, TIME_Y);
      tft.setTextColor(COLOR_WARNING);
      tft.setTextSize(1);
      tft.print("TIME: SYNCING...");

      tft.fillRect(DATE_X - 90, DATE_Y, 90, 15, COLOR_PANEL);
      tft.setCursor(DATE_X - 90, DATE_Y);
      tft.setTextColor(COLOR_WARNING);
      tft.setTextSize(1);
      tft.print("WAIT...");
    }
  }
}

void checkPeriodicTimeSync() {
  static unsigned long lastNTPSync = 0;
  unsigned long now = millis();

  // Periodic sync for already synchronized time
  if (timeInitialized && wifiConnected && (now - lastNTPSync > NTP_UPDATE_INTERVAL)) {
    DEBUG_PRINTLN("Performing periodic NTP sync...");
    ntpSyncInProgress = true;
    ntpSyncStatus = "SYNCING";

    configTime(TIME_ZONE_OFFSET * 3600, 0, NTP_SERVER_PRIMARY, NTP_SERVER_SECONDARY);

    // Quick check for sync success
    delay(2000);
    struct tm timeinfo;
    if (getLocalTime(&timeinfo)) {
      ntpSyncStatus = "SYNCED";
      DEBUG_PRINTLN("Periodic NTP sync successful");
      publishNtpSyncStatus(true);
    } else {
      ntpSyncStatus = "FAILED";
      DEBUG_PRINTLN("Periodic NTP sync failed");
      publishNtpSyncStatus(false);
    }

    ntpSyncInProgress = false;
    lastNTPSync = now;
  }

  // Retry failed sync attempts
  if (!timeInitialized && wifiConnected && !ntpSyncInProgress &&
      (now - lastNtpSyncAttempt > NTP_RETRY_INTERVAL) &&
      ntpRetryCount < NTP_MAX_RETRIES) {
    DEBUG_PRINTF("Retrying NTP sync (attempt %d/%d)...\n", ntpRetryCount + 1, NTP_MAX_RETRIES);
    lastNtpSyncAttempt = now;
    setupTimeWithRetry();
  }
}

// ================================
// MQTT FUNCTIONS
// ================================

// Enhanced MQTT connection variables
int mqttRetryCount = 0;
unsigned long lastMqttReconnectAttempt = 0;
int maxMqttRetries = 10;
int mqttReconnectDelay = 5000;  // Base delay, will increase exponentially
bool mqttConnectionStable = false;
unsigned long mqttStableTime = 0;
unsigned long lastMqttHeartbeat = 0;

void setupMQTT() {
  // Set buffer size BEFORE setting server
  mqttClient.setBufferSize(MQTT_MAX_PACKET_SIZE);
  
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setKeepAlive(MQTT_KEEPALIVE);
  
  // Set socket timeout for faster detection of connection issues
  mqttClient.setSocketTimeout(15); // 15 seconds
  
  DEBUG_PRINTF("📦 Enhanced MQTT setup - Buffer: %d bytes, Server: %s:%d\n", 
               MQTT_MAX_PACKET_SIZE, MQTT_SERVER, MQTT_PORT);
  
  mqttRetryCount = 0;
  mqttConnectionStable = false;
}

void connectMQTT() {
  if (!wifiConnected) {
    DEBUG_PRINTLN("⚠️ Cannot connect MQTT - WiFi not connected");
    return;
  }
  
  unsigned long now = millis();
  
  // Respect reconnection delay
  if (now - lastMqttReconnectAttempt < mqttReconnectDelay) {
    return;
  }
  
  if (mqttRetryCount >= maxMqttRetries) {
    DEBUG_PRINTF("❌ MQTT connection failed after %d attempts\n", maxMqttRetries);
    return;
  }

  DEBUG_PRINTF("📡 MQTT connection attempt %d/%d to %s:%d\n", 
               mqttRetryCount + 1, maxMqttRetries, MQTT_SERVER, MQTT_PORT);
  
  lastMqttReconnectAttempt = now;
  
  // Generate unique client ID to avoid conflicts
  uint64_t chipid = ESP.getEfuseMac();
  String clientId = String(MQTT_CLIENT_ID) + "_" + String((uint32_t)chipid, HEX) + "_" + String(random(0xffff), HEX);
  
  bool connected = false;
  if (strlen(MQTT_USERNAME) > 0) {
    connected = mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD);
  } else {
    connected = mqttClient.connect(clientId.c_str());
  }

  if (connected) {
    mqttConnected = true;
    mqttRetryCount = 0; // Reset retry count
    mqttReconnectDelay = 5000; // Reset delay
    mqttStableTime = now;
    mqttConnectionStable = false;
    lastMqttHeartbeat = now;
    
    DEBUG_PRINTLN("✅ MQTT connected!");
    
    // Subscribe to topics
    bool subSuccess = mqttClient.subscribe(MQTT_TOPIC_MESSAGES, MQTT_QOS);
    DEBUG_PRINTF("📨 Subscription to %s: %s\n", MQTT_TOPIC_MESSAGES, subSuccess ? "SUCCESS" : "FAILED");
    
    // Subscribe to cancellation notifications
    String cancellationTopic = String("consultease/faculty/") + String(FACULTY_ID) + "/cancellations";
    bool subCancelSuccess = mqttClient.subscribe(cancellationTopic.c_str(), MQTT_QOS);
    DEBUG_PRINTF("📨 Subscription to %s: %s\n", cancellationTopic.c_str(), subCancelSuccess ? "SUCCESS" : "FAILED");
    
    // Publish presence immediately
    publishPresenceUpdate();
    updateSystemStatus();
    
    // Process any queued messages
    updateOfflineQueue();
    
  } else {
    mqttConnected = false;
    mqttRetryCount++;
    
    int mqttState = mqttClient.state();
    DEBUG_PRINTF("❌ MQTT connection failed! State: %d (%s)\n", mqttState, getMqttStateString(mqttState));
    
    // Calculate exponential backoff delay
    int backoffDelay = mqttReconnectDelay * (1 << min(mqttRetryCount - 1, 4)); // Cap at 16x base delay
    mqttReconnectDelay = min(backoffDelay, 60000); // Cap at 60 seconds
    
    DEBUG_PRINTF("🔄 Next MQTT retry in %d seconds\n", mqttReconnectDelay / 1000);
    updateSystemStatus();
  }
}

void checkMQTTConnection() {
  if (!wifiConnected) {
    if (mqttConnected) {
      mqttConnected = false;
      mqttConnectionStable = false;
      updateSystemStatus();
    }
    return;
  }
  
  unsigned long now = millis();
  
  // Check if MQTT is still connected
  if (!mqttClient.connected()) {
    if (mqttConnected) {
      DEBUG_PRINTLN("⚠️ MQTT connection lost!");
      mqttConnected = false;
      mqttConnectionStable = false;
      updateSystemStatus();
    }
    
    // Attempt reconnection
    connectMQTT();
  } else {
    // MQTT is connected - monitor stability and send heartbeats
    if (!mqttConnected) {
      DEBUG_PRINTLN("✅ MQTT reconnected!");
      mqttConnected = true;
      mqttStableTime = now;
      mqttConnectionStable = false;
      lastMqttHeartbeat = now;
      updateSystemStatus();
    }
    
    // Check connection stability (mark as stable after 30 seconds)
    if (!mqttConnectionStable && (now - mqttStableTime > 30000)) {
      mqttConnectionStable = true;
      DEBUG_PRINTLN("🔒 MQTT connection is now stable");
      mqttRetryCount = 0; // Reset retry count after stable connection
    }
    
    // Send periodic heartbeat to keep connection alive
    if (now - lastMqttHeartbeat > 30000) { // Every 30 seconds
      DEBUG_PRINTLN("💓 Sending MQTT keepalive heartbeat");
      publishHeartbeat();
      lastMqttHeartbeat = now;
    }
    
    // Process MQTT loop frequently for stability
    mqttClient.loop();
  }
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  DEBUG_PRINTF("📨 onMqttMessage called - Topic: %s, Length: %d\n", topic, length);
  
  // Bounds checking for security
  if (length > MAX_MESSAGE_LENGTH) {
    DEBUG_PRINTF("⚠️ Message too long (%d bytes), truncating to %d\n", length, MAX_MESSAGE_LENGTH);
    length = MAX_MESSAGE_LENGTH;
  }

  String messageContent = "";
  messageContent.reserve(length + 1);  // Pre-allocate memory

  for (unsigned int i = 0; i < length; i++) {
    messageContent += (char)payload[i];
  }

  DEBUG_PRINTF("📨 Message received (%d bytes): %s\n", length, messageContent.c_str());
  
  // Check if this is a cancellation notification
  String topicStr = String(topic);
  if (topicStr.indexOf("/cancellations") != -1) {
    handleCancellationNotification(messageContent);
    return;
  }

  // Parse Consultation ID (CID) from the message
  DEBUG_PRINTLN("🔍 Starting CID parsing...");
  int cidStartIndex = messageContent.indexOf("CID:");
  DEBUG_PRINTF("   CID: search index = %d\n", cidStartIndex);
  
  String parsedConsultationId = "";

  if (cidStartIndex != -1) {
    cidStartIndex += 4; // Length of "CID:"
    int cidEndIndex = messageContent.indexOf(" ", cidStartIndex);
    
    if (cidEndIndex != -1) {
      parsedConsultationId = messageContent.substring(cidStartIndex, cidEndIndex);
    } else {
      parsedConsultationId = messageContent.substring(cidStartIndex);
    }
    DEBUG_PRINTF("🔑 Parsed Consultation ID (CID): '%s'\n", parsedConsultationId.c_str());
  } else {
    DEBUG_PRINTLN("⚠️ Consultation ID (CID:) not found in message.");
    return; // Skip messages without CID
  }
  
  bool facultyPresent = presenceDetector.getPresence();
  DEBUG_PRINTF("👤 Faculty presence check: %s\n", facultyPresent ? "PRESENT" : "AWAY");
  
  if (!facultyPresent) {
    DEBUG_PRINTLN("📭 Message ignored - Professor is AWAY");
    return;
  }

  // NEW QUEUE LOGIC: Check if a message is currently being displayed
  if (currentMessageDisplayed) {
    DEBUG_PRINTLN("📥 Message currently displayed, adding new consultation to queue");
    addConsultationToQueue(messageContent, parsedConsultationId);
  } else {
    DEBUG_PRINTLN("📱 No message currently displayed, showing consultation immediately");
    
    // Parse and display immediately
    ConsultationMessage newMessage;
    parseConsultationMessage(messageContent, parsedConsultationId, newMessage);
    displayQueuedConsultation(newMessage);
  }
}

void handleCancellationNotification(String messageContent) {
  DEBUG_PRINTF("🚫 Cancellation notification received: %s\n", messageContent.c_str());
  
  // Parse JSON message to extract consultation ID
  int cidIndex = messageContent.indexOf("consultation_id");
  if (cidIndex == -1) {
    DEBUG_PRINTLN("⚠️ No consultation_id found in cancellation notification");
    return;
  }
  
  // Extract consultation ID from JSON
  int colonIndex = messageContent.indexOf(":", cidIndex);
  if (colonIndex == -1) return;
  
  int startIndex = colonIndex + 1;
  int endIndex = messageContent.indexOf(",", startIndex);
  if (endIndex == -1) {
    endIndex = messageContent.indexOf("}", startIndex);
  }
  if (endIndex == -1) return;
  
  String consultationId = messageContent.substring(startIndex, endIndex);
  consultationId.trim();
  consultationId.replace("\"", "");  // Remove quotes
  consultationId.replace(" ", "");   // Remove spaces
  
  DEBUG_PRINTF("🔑 Extracted consultation ID from cancellation: '%s'\n", consultationId.c_str());
  
  // Check if this consultation is currently displayed
  if (currentMessageDisplayed && g_receivedConsultationId.equals(consultationId)) {
    DEBUG_PRINTLN("🚫 Cancelling currently displayed consultation");
    
    // Clear the current message
    currentMessageDisplayed = false;
    messageDisplayed = false;
    g_receivedConsultationId = "";
    
    // Show cancellation message
    tft.fillScreen(ST77XX_BLACK);
    displayCancelledConsultation(consultationId);
    
    // Process next message in queue after a short delay
    unsigned long cancelDisplayTime = millis();
    while (millis() - cancelDisplayTime < 3000) {  // Show cancellation for 3 seconds
      delay(100);
    }
    
    // Process next consultation in queue
    processNextQueuedConsultation();
    
  } else {
    // Check if the consultation is in the queue and remove it
    bool foundInQueue = false;
    for (int i = 0; i < MAX_CONSULTATION_QUEUE_SIZE; i++) {
      if (consultationQueue[i].isValid && consultationQueue[i].consultationId.equals(consultationId)) {
        DEBUG_PRINTF("🚫 Removing consultation %s from queue (position %d)\n", consultationId.c_str(), i);
        
        // Mark as invalid
        consultationQueue[i].isValid = false;
        consultationQueue[i].consultationId = "";
        consultationQueue[i].content = "";
        
        foundInQueue = true;
        break;
      }
    }
    
    if (foundInQueue) {
      // Compress the queue to remove gaps
      compressConsultationQueue();
      DEBUG_PRINTF("📥 Consultation queue compressed, new size: %d\n", consultationQueueSize);
    } else {
      DEBUG_PRINTF("ℹ️ Consultation %s not found in current display or queue\n", consultationId.c_str());
    }
  }
}

void displayCancelledConsultation(String consultationId) {
  // Clear screen
  tft.fillScreen(ST77XX_BLACK);
  
  // Header
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.setCursor(10, 10);
  tft.println("CONSULTATION");
  tft.setCursor(10, 35);
  tft.println("CANCELLED");
  
  // Draw line
  tft.drawLine(0, 65, SCREEN_WIDTH, 65, ST77XX_RED);
  
  // Cancellation icon and message
  tft.setTextColor(ST77XX_RED);
  tft.setTextSize(3);
  tft.setCursor(SCREEN_WIDTH/2 - 10, 80);
  tft.println("X");
  
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(1);
  tft.setCursor(10, 120);
  tft.println("The consultation request");
  tft.setCursor(10, 135);
  tft.println("has been cancelled by");
  tft.setCursor(10, 150);
  tft.println("the student.");
  
  // Consultation ID
  tft.setTextColor(ST77XX_YELLOW);
  tft.setCursor(10, 175);
  tft.printf("ID: %s", consultationId.c_str());
  
  // Status message
  tft.setTextColor(ST77XX_CYAN);
  tft.setCursor(10, 200);
  tft.println("Returning to main screen...");
}

void compressConsultationQueue() {
  int writeIndex = 0;
  
  // Compress valid entries to front of queue
  for (int readIndex = 0; readIndex < MAX_CONSULTATION_QUEUE_SIZE; readIndex++) {
    if (consultationQueue[readIndex].isValid) {
      if (writeIndex != readIndex) {
        consultationQueue[writeIndex] = consultationQueue[readIndex];
        consultationQueue[readIndex].isValid = false;
        consultationQueue[readIndex].consultationId = "";
        consultationQueue[readIndex].content = "";
      }
      writeIndex++;
    }
  }
  
  // Update queue pointers
  consultationQueueHead = 0;
  consultationQueueTail = writeIndex;
  consultationQueueSize = writeIndex;
  
  DEBUG_PRINTF("📥 Queue compressed: %d valid entries\n", consultationQueueSize);
}

void publishPresenceUpdate() {
  String payload = "{";
  payload += "\"faculty_id\":" + String(FACULTY_ID) + ",";
  payload += "\"faculty_name\":\"" + String(FACULTY_NAME) + "\",";
  payload += "\"present\":" + String(presenceDetector.getPresence() ? "true" : "false") + ",";
  payload += "\"status\":\"" + presenceDetector.getStatusString() + "\",";
  payload += "\"timestamp\":" + String(millis()) + ",";
  payload += "\"ntp_sync_status\":\"" + ntpSyncStatus + "\"";

  // Add grace period information for debugging
  if (presenceDetector.isInGracePeriod()) {
    payload += ",\"grace_period_remaining\":" + String(presenceDetector.getGracePeriodRemaining());
    payload += ",\"in_grace_period\":true";
  } else {
    payload += ",\"in_grace_period\":false";
  }

  // Add detailed status for central system
  payload += ",\"detailed_status\":\"" + presenceDetector.getDetailedStatus() + "\"";

  payload += "}";

  // Publish with offline queuing support
  bool success1 = publishWithQueue(MQTT_TOPIC_STATUS, payload.c_str(), false);
  bool success2 = publishWithQueue(MQTT_LEGACY_STATUS, payload.c_str(), false);

  if (success1 || success2) {
    if (mqttClient.connected()) {
      DEBUG_PRINTF("📡 Published presence update: %s\n", presenceDetector.getStatusString().c_str());
    } else {
      DEBUG_PRINTF("📥 Queued presence update: %s\n", presenceDetector.getStatusString().c_str());
    }
  } else {
    DEBUG_PRINTLN("❌ Failed to send/queue presence update");
  }
}

void publishNtpSyncStatus(bool success) {
  if (!mqttClient.connected()) return;

  String payload = "{";
  payload += "\"faculty_id\":" + String(FACULTY_ID) + ",";
  payload += "\"ntp_sync_success\":" + String(success ? "true" : "false") + ",";
  payload += "\"ntp_sync_status\":\"" + ntpSyncStatus + "\",";
  payload += "\"retry_count\":" + String(ntpRetryCount) + ",";
  payload += "\"timestamp\":" + String(millis());

  if (success && timeInitialized) {
    struct tm timeinfo;
    if (getLocalTime(&timeinfo)) {
      char timeStr[32];
      strftime(timeStr, sizeof(timeStr), "%Y-%m-%d %H:%M:%S", &timeinfo);
      payload += ",\"current_time\":\"" + String(timeStr) + "\"";
    }
  }

  payload += "}";

  mqttClient.publish(MQTT_TOPIC_HEARTBEAT, payload.c_str(), MQTT_QOS);
  DEBUG_PRINTF("📡 Published NTP sync status: %s\n", success ? "SUCCESS" : "FAILED");
}

void publishHeartbeat() {
  if (!mqttClient.connected()) return;

  String payload = "{";
  payload += "\"faculty_id\":" + String(FACULTY_ID) + ",";
  payload += "\"uptime\":" + String(millis()) + ",";
  payload += "\"free_heap\":" + String(ESP.getFreeHeap()) + ",";
  payload += "\"wifi_connected\":" + String(wifiConnected ? "true" : "false") + ",";
  payload += "\"wifi_rssi\":" + String(currentWifiRSSI) + ",";
  payload += "\"wifi_stable\":" + String(wifiConnectionStable ? "true" : "false") + ",";
  payload += "\"mqtt_stable\":" + String(mqttConnectionStable ? "true" : "false") + ",";
  payload += "\"wifi_retries\":" + String(wifiRetryCount) + ",";
  payload += "\"mqtt_retries\":" + String(mqttRetryCount) + ",";
  payload += "\"time_initialized\":" + String(timeInitialized ? "true" : "false") + ",";
  payload += "\"ntp_sync_status\":\"" + ntpSyncStatus + "\",";
  payload += "\"presence_status\":\"" + presenceDetector.getStatusString() + "\",";
  payload += "\"queue_size\":" + String(queueCount) + ",";
  payload += "\"consultation_queue_size\":" + String(consultationQueueSize);
  payload += "}";

  mqttClient.publish(MQTT_TOPIC_HEARTBEAT, payload.c_str());
  DEBUG_PRINTF("💓 Enhanced heartbeat published - WiFi: %d dBm, Stable: %s/%s\n", 
               currentWifiRSSI, 
               wifiConnectionStable ? "Y" : "N", 
               mqttConnectionStable ? "Y" : "N");
}

// ================================
// CONNECTION DIAGNOSTICS AND MONITORING
// ================================

void printConnectionDiagnostics() {
  DEBUG_PRINTLN("📊 === CONNECTION DIAGNOSTICS ===");
  DEBUG_PRINTF("WiFi Status: %s\n", wifiConnected ? "CONNECTED" : "DISCONNECTED");
  if (wifiConnected) {
    DEBUG_PRINTF("  SSID: %s\n", WiFi.SSID().c_str());
    DEBUG_PRINTF("  IP Address: %s\n", WiFi.localIP().toString().c_str());
    DEBUG_PRINTF("  RSSI: %d dBm\n", currentWifiRSSI);
    DEBUG_PRINTF("  Signal Quality: %s\n", currentWifiRSSI > -70 ? "EXCELLENT" : 
                                         currentWifiRSSI > -80 ? "GOOD" : "POOR");
    DEBUG_PRINTF("  Stable: %s (uptime: %lu ms)\n", 
                 wifiConnectionStable ? "YES" : "NO", 
                 wifiConnectionStable ? millis() - wifiStableTime : 0);
    DEBUG_PRINTF("  Retry Count: %d/%d\n", wifiRetryCount, maxWifiRetries);
  }
  
  DEBUG_PRINTF("MQTT Status: %s\n", mqttConnected ? "CONNECTED" : "DISCONNECTED");
  if (mqttConnected) {
    DEBUG_PRINTF("  Server: %s:%d\n", MQTT_SERVER, MQTT_PORT);
    DEBUG_PRINTF("  Client ID: %s\n", MQTT_CLIENT_ID);
    DEBUG_PRINTF("  Stable: %s (uptime: %lu ms)\n", 
                 mqttConnectionStable ? "YES" : "NO",
                 mqttConnectionStable ? millis() - mqttStableTime : 0);
    DEBUG_PRINTF("  Retry Count: %d/%d\n", mqttRetryCount, maxMqttRetries);
    DEBUG_PRINTF("  Buffer Size: %d bytes\n", MQTT_MAX_PACKET_SIZE);
  }
  
  DEBUG_PRINTF("System Health:\n");
  DEBUG_PRINTF("  Free Heap: %d bytes\n", ESP.getFreeHeap());
  DEBUG_PRINTF("  Uptime: %lu minutes\n", millis() / 60000);
  DEBUG_PRINTF("  Message Queue: %d/%d\n", queueCount, MAX_OFFLINE_QUEUE_SIZE);
  DEBUG_PRINTF("  Consultation Queue: %d/%d\n", consultationQueueSize, MAX_CONSULTATION_QUEUE_SIZE);
  DEBUG_PRINTF("  Time Sync: %s\n", ntpSyncStatus.c_str());
  DEBUG_PRINTLN("==============================");
}

void publishConnectionDiagnostics() {
  if (!mqttConnected) return;
  
  String topic = String("consultease/faculty/") + String(FACULTY_ID) + "/diagnostics";
  
  String payload = "{";
  payload += "\"faculty_id\":" + String(FACULTY_ID) + ",";
  payload += "\"timestamp\":" + String(millis()) + ",";
  payload += "\"wifi_rssi\":" + String(currentWifiRSSI) + ",";
  payload += "\"wifi_stable\":" + String(wifiConnectionStable ? "true" : "false") + ",";
  payload += "\"mqtt_stable\":" + String(mqttConnectionStable ? "true" : "false") + ",";
  payload += "\"wifi_retries\":" + String(wifiRetryCount) + ",";
  payload += "\"mqtt_retries\":" + String(mqttRetryCount) + ",";
  payload += "\"free_heap\":" + String(ESP.getFreeHeap()) + ",";
  payload += "\"queue_size\":" + String(queueCount) + ",";
  payload += "\"consultation_queue_size\":" + String(consultationQueueSize) + ",";
  payload += "\"system_uptime\":" + String(millis()) + ",";
  payload += "\"ntp_status\":\"" + ntpSyncStatus + "\"";
  payload += "}";
  
  bool success = mqttClient.publish(topic.c_str(), payload.c_str(), false);
  DEBUG_PRINTF("📊 Diagnostics published: %s\n", success ? "SUCCESS" : "FAILED");
}

// ================================
// BLE FUNCTIONS
// ================================
void setupBLE() {
  DEBUG_PRINTLN("Initializing BLE...");

  BLEDevice::init("");
  pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(true);
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);

  DEBUG_PRINTLN("BLE ready");
}

// ================================
// DISPLAY FUNCTIONS
// ================================
void setupDisplay() {
  tft.init(240, 320);
  tft.setRotation(3);
  tft.fillScreen(COLOR_BLACK);

  DEBUG_PRINTLN("Display initialized - With Grace Period BLE System + Message Queue");

  tft.fillScreen(COLOR_BACKGROUND);

  tft.setCursor(getCenterX("NU FACULTY", 3), 100);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(3);
  tft.print("NU FACULTY");

  tft.setCursor(getCenterX("DESK UNIT", 2), 130);
  tft.setTextSize(2);
  tft.setTextColor(COLOR_TEXT);
  tft.print("DESK UNIT");

  tft.setCursor(getCenterX("Message Queue System", 1), 160);
  tft.setTextSize(1);
  tft.setTextColor(COLOR_ACCENT);
  tft.print("Message Queue System");

  delay(2000);
}

void drawCompleteUI() {
  tft.fillScreen(COLOR_BACKGROUND);

  // Top panel with professor info
  tft.fillRect(0, TOP_PANEL_Y, SCREEN_WIDTH, TOP_PANEL_HEIGHT, COLOR_PANEL);

  tft.setCursor(PROFESSOR_NAME_X, PROFESSOR_NAME_Y);
  tft.setTextColor(COLOR_ACCENT);
  tft.setTextSize(2);
  tft.print("PROFESSOR: ");
  tft.setTextSize(2);
  tft.print(FACULTY_NAME);

  //tft.setCursor(DEPARTMENT_X, DEPARTMENT_Y);
  //tft.setTextColor(COLOR_ACCENT);
 // tft.setTextSize(1);
  //tft.print("DEPARTMENT: ");
 // tft.print(FACULTY_DEPARTMENT);

  // Only show status panel during initialization
  if (!systemFullyInitialized) {
    tft.fillRect(0, STATUS_PANEL_Y, SCREEN_WIDTH, STATUS_PANEL_HEIGHT, COLOR_PANEL_DARK);
    updateSystemStatus();
  } else {
    // Hide status panel - fill with background color
    tft.fillRect(0, STATUS_PANEL_Y, SCREEN_WIDTH, STATUS_PANEL_HEIGHT, COLOR_BACKGROUND);
  }

  tft.fillRect(0, BOTTOM_PANEL_Y, SCREEN_WIDTH, BOTTOM_PANEL_HEIGHT, COLOR_PANEL);

  updateTimeAndDate();
  updateMainDisplay();
}

void updateMainDisplay() {
  tft.fillRect(0, MAIN_AREA_Y, SCREEN_WIDTH, MAIN_AREA_HEIGHT, COLOR_WHITE);

  if (presenceDetector.getPresence()) {
    drawSimpleCard(20, STATUS_CENTER_Y - 40, 280, 70, COLOR_PANEL);

    int availableX = getCenterX("AVAILABLE", 4);
    tft.setCursor(availableX, STATUS_CENTER_Y - 25);
    tft.setTextSize(4);
    tft.setTextColor(COLOR_SUCCESS);
    tft.print("AVAILABLE");

    int subtitleX = getCenterX("Ready for Consultation", 2);
    tft.setCursor(subtitleX, STATUS_CENTER_Y + 5);
    tft.setTextSize(2);
    tft.setTextColor(COLOR_ACCENT);
    tft.print("Ready for Consultation");

    drawStatusIndicator(STATUS_CENTER_X, STATUS_CENTER_Y + 50, true);

  } else {
    drawSimpleCard(20, STATUS_CENTER_Y - 40, 280, 70, COLOR_GRAY_LIGHT);

    int awayX = getCenterX("AWAY", 4);
    tft.setCursor(awayX, STATUS_CENTER_Y - 25);
    tft.setTextSize(4);
    tft.setTextColor(COLOR_ERROR);
    tft.print("AWAY");

    int notAvailableX = getCenterX("Not Available", 2);
    tft.setCursor(notAvailableX, STATUS_CENTER_Y + 5);
    tft.setTextSize(2);
    tft.setTextColor(COLOR_WHITE);
    tft.print("Not Available");

    drawStatusIndicator(STATUS_CENTER_X, STATUS_CENTER_Y + 50, false);
  }
}

void updateSystemStatus() {
  // Only show status during initialization
  if (!systemFullyInitialized) {
    tft.fillRect(2, STATUS_PANEL_Y + 1, SCREEN_WIDTH - 4, STATUS_PANEL_HEIGHT - 2, COLOR_PANEL_DARK);

    int topLineY = STATUS_PANEL_Y + 3;

    tft.setCursor(10, topLineY);
    tft.setTextColor(COLOR_ACCENT);
    tft.setTextSize(1);
    tft.print("WiFi:");
    if (wifiConnected) {
      tft.setTextColor(COLOR_SUCCESS);
      tft.print("CONNECTED");
    } else {
      tft.setTextColor(COLOR_ERROR);
      tft.print("FAILED");
    }

    tft.setCursor(120, topLineY);
    tft.setTextColor(COLOR_ACCENT);
    tft.print("MQTT:");
    if (mqttConnected) {
      tft.setTextColor(COLOR_SUCCESS);
      tft.print("ONLINE");
    } else {
      tft.setTextColor(COLOR_ERROR);
      tft.print("OFFLINE");
    }

    tft.setCursor(230, topLineY);
    tft.setTextColor(COLOR_ACCENT);
    tft.print("BLE:");
    tft.setTextColor(COLOR_SUCCESS);
    tft.print("ACTIVE");

    int bottomLineY = STATUS_PANEL_Y + 15;

    tft.setCursor(10, bottomLineY);
    tft.setTextColor(COLOR_ACCENT);
    tft.print("TIME:");
    if (timeInitialized) {
      tft.setTextColor(COLOR_SUCCESS);
      tft.print("SYNCED");
    } else if (ntpSyncInProgress) {
      tft.setTextColor(COLOR_WARNING);
      tft.print("SYNCING");
    } else if (ntpSyncStatus == "FAILED") {
      tft.setTextColor(COLOR_ERROR);
      tft.print("FAILED");
    } else {
      tft.setTextColor(COLOR_WARNING);
      tft.print("PENDING");
    }

    tft.setCursor(120, bottomLineY);
    tft.setTextColor(COLOR_ACCENT);
    tft.print("RAM:");
    int freeHeapKB = ESP.getFreeHeap() / 1024;
    tft.printf("%dKB", freeHeapKB);

    tft.setCursor(200, bottomLineY);
    tft.setTextColor(COLOR_ACCENT);
    tft.print("UPTIME:");
    unsigned long uptimeMinutes = millis() / 60000;
    if (uptimeMinutes < 60) {
      tft.printf("%dm", uptimeMinutes);
    } else {
      tft.printf("%dh%dm", uptimeMinutes / 60, uptimeMinutes % 60);
    }
  }
}

// ================================
// MAIN SETUP FUNCTION - OPTIMIZED
// ================================
void setup() {
  if (ENABLE_SERIAL_DEBUG) {
    Serial.begin(SERIAL_BAUD_RATE);
    while (!Serial && millis() < 3000);
  }

  DEBUG_PRINTLN("=== NU FACULTY DESK UNIT - ENHANCED CONSULTATION SYSTEM ===");
  DEBUG_PRINTLN("=== PERSISTENT MESSAGES + MESSAGE QUEUE + PHYSICAL BUTTON CONTROL ===");
  DEBUG_PRINTLN("=== PERFORMANCE OPTIMIZED VERSION ===");
  DEBUG_PRINTLN("✅ BLE scan frequency reduced from 1s to 8s");
  DEBUG_PRINTLN("✅ Enhanced MQTT reliability with forced processing");
  DEBUG_PRINTLN("✅ Optimized main loop for <100ms response time");
  DEBUG_PRINTLN("✅ Improved button debouncing for faster response");
  DEBUG_PRINTLN("✅ Message queue system prevents message loss");

  if (!validateConfiguration()) {
    while(true) delay(5000);
  }

  DEBUG_PRINTF("Faculty: %s\n", FACULTY_NAME);
  DEBUG_PRINTF("Department: %s\n", FACULTY_DEPARTMENT);
  DEBUG_PRINTF("iBeacon: %s\n", FACULTY_BEACON_MAC);
  DEBUG_PRINTF("WiFi: %s\n", WIFI_SSID);
  DEBUG_PRINTF("Grace Period: %d seconds\n", BLE_GRACE_PERIOD_MS / 1000);

  // Initialize offline operation system
  DEBUG_PRINTLN("🔄 Initializing optimized offline operation system...");
  initOfflineQueue();
  initConsultationQueue();

  // Initialize components
  buttons.init();
  initMessageLED();
  setupDisplay();
  setupWiFi();

  if (wifiConnected) {
    setupMQTT();
  }

  setupBLE();
  adaptiveScanner.init(&presenceDetector);  // Pass reference to presence detector

  DEBUG_PRINTLN("=== OPTIMIZED CONSULTATION SYSTEM WITH MESSAGE QUEUE READY ===");
  DEBUG_PRINTLN("✅ BLE disconnections now have 1-minute grace period!");
  DEBUG_PRINTLN("✅ Consultation messages persist until physical button press!");
  DEBUG_PRINTLN("✅ Message queue prevents consultation loss!");
  DEBUG_PRINTLN("✅ Larger, more readable consultation message display!");
  DEBUG_PRINTLN("✅ Physical button-only control (no on-screen buttons)!");
  DEBUG_PRINTLN("✅ Performance optimized for fast button response!");
  testMessageLED();
  systemFullyInitialized = true;
  drawCompleteUI();
}

// ================================
// MAIN LOOP WITH GRACE PERIOD BLE SCANNER - OPTIMIZED
// ================================
void loop() {
  // Add loop timing monitoring for button debugging
  unsigned long loopStart = millis();
  static unsigned long lastLoopTime = 0;
  static unsigned long maxLoopTime = 0;
  static unsigned long loopCount = 0;

  // ✅ CRITICAL FIX: MQTT LOOP FIRST AND FREQUENT
  if (mqttConnected) {
    mqttClient.loop();
  }

  // PRIORITY 1: Update button states FIRST and FREQUENTLY
  // Run button updates multiple times per main loop to catch quick presses
  for (int i = 0; i < 3; i++) {  // Reduced from 5 to 3 for performance
    buttons.update();

    // 🆕 UPDATE LED FREQUENTLY FOR SMOOTH BLINKING
    updateMessageLED();

    // Handle button presses immediately
    if (buttons.isButtonAPressed()) {
      DEBUG_PRINTLN("🎯 BUTTON A PRESS DETECTED IN MAIN LOOP!");
      handleAcknowledgeButton();
      break; // Exit loop if button handled
    }

    if (buttons.isButtonBPressed()) {
      DEBUG_PRINTLN("🎯 BUTTON B PRESS DETECTED IN MAIN LOOP!");
      handleBusyButton();
      break; // Exit loop if button handled
    }
    
    delay(2); // Small delay between button checks
  }

  // Handle button presses
  static unsigned long lastButtonCheck = 0;
  static int buttonCheckCount = 0;
  
  // Debug button checking frequency every 1000 checks (reduced from 100)
  buttonCheckCount++;
  if (buttonCheckCount % 1000 == 0) {
    unsigned long checkInterval = millis() - lastButtonCheck;
    DEBUG_PRINTF("🔍 Button check #%d - last 1000 checks took %lu ms (avg: %.1f ms per check)\n", 
                 buttonCheckCount, checkInterval, (float)checkInterval / 1000.0);
    lastButtonCheck = millis();
  }

  // ✅ CRITICAL FIX: REST OF MAIN LOOP - Run MUCH less frequently to speed up button response
  static unsigned long lastSlowOperations = 0;
  if (millis() - lastSlowOperations > 200) { // Increased frequency from 500ms to 200ms
    
    // Enhanced connection checking with robust reconnection
    checkWiFiConnection();
    checkMQTTConnection();

    // Update offline queue system
    updateOfflineQueue();

    lastSlowOperations = millis();
  }

  // ✅ CRITICAL FIX: BLE SCANNING - Run MUCH less frequently (major performance fix)
  static unsigned long lastBLEScan = 0;
  if (millis() - lastBLEScan > 8000) { // Increased from 1000ms to 8000ms (8 seconds)
    adaptiveScanner.update();
    lastBLEScan = millis();
  }

  // Update time every 10 seconds (increased from 5)
  static unsigned long lastTimeUpdate = 0;
  if (millis() - lastTimeUpdate > 10000) { // Increased frequency
    updateTimeAndDate();
    lastTimeUpdate = millis();
  }

  // Update system status every 15 seconds (increased from 10)
    // Update system status only during initialization
  static unsigned long lastStatusUpdate = 0;
  if (!systemFullyInitialized && millis() - lastStatusUpdate > 15000) {
    updateSystemStatus();
    lastStatusUpdate = millis();
  }

  // Heartbeat every 5 minutes (unchanged)
  static unsigned long lastHeartbeatTime = 0;
  if (millis() - lastHeartbeatTime > HEARTBEAT_INTERVAL) {
    publishHeartbeat();
    lastHeartbeatTime = millis();
  }

  // Periodic time sync check - less frequent
  static unsigned long lastTimeSyncCheck = 0;
  if (millis() - lastTimeSyncCheck > 60000) { // Increased from 30 seconds to 60 seconds
    checkPeriodicTimeSync();
    lastTimeSyncCheck = millis();
  }

  // Connection diagnostics every 10 minutes
  static unsigned long lastDiagnostics = 0;
  if (millis() - lastDiagnostics > 600000) { // 10 minutes
    printConnectionDiagnostics();
    if (mqttConnected) {
      publishConnectionDiagnostics();
    }
    lastDiagnostics = millis();
  }

  // Simple animation toggle every 1000ms (reduced frequency)
  static unsigned long lastIndicatorUpdate = 0;
  if (millis() - lastIndicatorUpdate > 1000) { // Increased from 800ms
    animationState = !animationState;
    if (presenceDetector.getPresence() && !messageDisplayed) {
      drawStatusIndicator(STATUS_CENTER_X, STATUS_CENTER_Y + 50, true);
    }
    lastIndicatorUpdate = millis();
  }

  // Loop timing analysis
  unsigned long loopTime = millis() - loopStart;
  loopCount++;
  
  if (loopTime > maxLoopTime) {
    maxLoopTime = loopTime;
  }
  
  // Log slow loops that could interfere with button processing
  if (loopTime > 50) {  // Keep threshold at 50ms
    DEBUG_PRINTF("⚠️ Slow loop detected: %lu ms (could affect button response)\n", loopTime);
  }
  
  // Report loop performance every 60 seconds (increased from 30)
  static unsigned long lastLoopReport = 0;
  if (millis() - lastLoopReport > 60000) {
    DEBUG_PRINTF("🔧 Loop Performance: Max=%lu ms, Avg=%.1f ms, Count=%lu\n", 
                maxLoopTime, 
                (float)(millis() - lastLoopTime) / loopCount,
                loopCount);
    maxLoopTime = 0;  // Reset max
    loopCount = 0;    // Reset count
    lastLoopTime = millis();
    lastLoopReport = millis();
  }

  delay(5); // Keep at 5ms for fast button response
}

// ================================
// END OF ENHANCED SYSTEM WITH MESSAGE QUEUE
// ================================