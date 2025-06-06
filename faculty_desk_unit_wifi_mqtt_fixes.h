#ifndef FACULTY_DESK_UNIT_WIFI_MQTT_FIXES_H
#define FACULTY_DESK_UNIT_WIFI_MQTT_FIXES_H

// ================================
// FACULTY DESK UNIT - WIFI & MQTT CONNECTION FIXES
// ================================
// This file contains enhanced WiFi and MQTT connection handling
// to fix disconnection issues and improve stability.

#include <WiFi.h>
#include <PubSubClient.h>

// ================================
// ENHANCED CONNECTION CONFIGURATION
// ================================

// WiFi Enhanced Settings
#define WIFI_RECONNECT_DELAY_FAST 2000        // 2 seconds for fast reconnect
#define WIFI_RECONNECT_DELAY_SLOW 10000       // 10 seconds for slow reconnect
#define WIFI_CONNECTION_TIMEOUT 20000         // 20 seconds connection timeout
#define WIFI_SIGNAL_CHECK_INTERVAL 30000      // Check signal every 30 seconds
#define WIFI_MIN_SIGNAL_STRENGTH -80          // Minimum signal strength (dBm)
#define WIFI_MAX_RECONNECT_ATTEMPTS 10        // Maximum reconnection attempts

// MQTT Enhanced Settings  
#define MQTT_RECONNECT_DELAY_FAST 1000        // 1 second for fast reconnect
#define MQTT_RECONNECT_DELAY_SLOW 5000        // 5 seconds for slow reconnect
#define MQTT_CONNECTION_TIMEOUT 15000         // 15 seconds connection timeout
#define MQTT_KEEPALIVE_ENHANCED 90            // 90 seconds keepalive (increased)
#define MQTT_SOCKET_TIMEOUT_ENHANCED 20       // 20 seconds socket timeout
#define MQTT_MAX_RECONNECT_ATTEMPTS 15        // Maximum reconnection attempts

// Connection monitoring
struct ConnectionHealth {
  bool wifi_stable;
  bool mqtt_stable;
  unsigned long wifi_last_connected;
  unsigned long mqtt_last_connected;
  int wifi_reconnect_count;
  int mqtt_reconnect_count;
  int wifi_signal_strength;
  unsigned long last_signal_check;
};

ConnectionHealth connection_health = {false, false, 0, 0, 0, 0, 0, 0};

// ================================
// ENHANCED WIFI CONNECTION FUNCTIONS
// ================================

bool setupWiFiEnhanced() {
  DEBUG_PRINTLN("🔧 Starting enhanced WiFi setup...");
  
  // Set WiFi mode and power settings for stability
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // Disable WiFi sleep for better stability
  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);
  
  // Set transmit power to maximum for better range
  WiFi.setTxPower(WIFI_POWER_19_5dBm);
  
  DEBUG_PRINTF("📡 Connecting to WiFi: %s\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - startTime) < WIFI_CONNECTION_TIMEOUT) {
    delay(500);
    DEBUG_PRINT(".");
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    connection_health.wifi_stable = true;
    connection_health.wifi_last_connected = millis();
    connection_health.wifi_signal_strength = WiFi.RSSI();
    
    DEBUG_PRINTLN();
    DEBUG_PRINTLN("✅ WiFi connected successfully!");
    DEBUG_PRINTF("   IP Address: %s\n", WiFi.localIP().toString().c_str());
    DEBUG_PRINTF("   Signal Strength: %d dBm\n", WiFi.RSSI());
    DEBUG_PRINTF("   MAC Address: %s\n", WiFi.macAddress().c_str());
    
    return true;
  } else {
    DEBUG_PRINTLN();
    DEBUG_PRINTLN("❌ WiFi connection failed!");
    wifiConnected = false;
    connection_health.wifi_stable = false;
    return false;
  }
}

bool checkWiFiConnectionEnhanced() {
  static unsigned long lastCheck = 0;
  static unsigned long lastReconnectAttempt = 0;
  static bool wasConnected = false;
  
  // Check connection status every 2 seconds
  if (millis() - lastCheck < 2000) {
    return WiFi.isConnected() && wifiConnected;
  }
  lastCheck = millis();
  
  bool currentlyConnected = WiFi.isConnected();
  
  // Check signal strength periodically
  if (currentlyConnected && (millis() - connection_health.last_signal_check > WIFI_SIGNAL_CHECK_INTERVAL)) {
    connection_health.wifi_signal_strength = WiFi.RSSI();
    connection_health.last_signal_check = millis();
    
    DEBUG_PRINTF("📶 WiFi Signal: %d dBm\n", connection_health.wifi_signal_strength);
    
    // Warn if signal is weak
    if (connection_health.wifi_signal_strength < WIFI_MIN_SIGNAL_STRENGTH) {
      DEBUG_PRINTF("⚠️ Weak WiFi signal: %d dBm (min: %d dBm)\n", 
                   connection_health.wifi_signal_strength, WIFI_MIN_SIGNAL_STRENGTH);
    }
  }
  
  // Connection state changed
  if (currentlyConnected != wasConnected) {
    if (currentlyConnected) {
      DEBUG_PRINTLN("✅ WiFi connection restored!");
      wifiConnected = true;
      connection_health.wifi_stable = true;
      connection_health.wifi_last_connected = millis();
      connection_health.wifi_reconnect_count = 0;  // Reset counter on success
    } else {
      DEBUG_PRINTLN("❌ WiFi connection lost!");
      wifiConnected = false;
      connection_health.wifi_stable = false;
    }
    wasConnected = currentlyConnected;
  }
  
  // Handle reconnection if disconnected
  if (!currentlyConnected && !wifiConnected) {
    unsigned long timeSinceLastAttempt = millis() - lastReconnectAttempt;
    unsigned long reconnectDelay = (connection_health.wifi_reconnect_count < 3) ? 
                                   WIFI_RECONNECT_DELAY_FAST : WIFI_RECONNECT_DELAY_SLOW;
    
    if (timeSinceLastAttempt > reconnectDelay) {
      if (connection_health.wifi_reconnect_count < WIFI_MAX_RECONNECT_ATTEMPTS) {
        DEBUG_PRINTF("🔄 WiFi reconnect attempt %d/%d\n", 
                     connection_health.wifi_reconnect_count + 1, WIFI_MAX_RECONNECT_ATTEMPTS);
        
        WiFi.disconnect();
        delay(1000);
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        
        connection_health.wifi_reconnect_count++;
        lastReconnectAttempt = millis();
      } else {
        DEBUG_PRINTLN("❌ WiFi max reconnect attempts reached");
        // Reset counter after a longer delay
        if (timeSinceLastAttempt > 60000) {  // 1 minute
          connection_health.wifi_reconnect_count = 0;
          DEBUG_PRINTLN("🔄 Resetting WiFi reconnect counter");
        }
      }
    }
  }
  
  return currentlyConnected && wifiConnected;
}

// ================================
// ENHANCED MQTT CONNECTION FUNCTIONS
// ================================

bool setupMQTTEnhanced() {
  if (!wifiConnected || !WiFi.isConnected()) {
    DEBUG_PRINTLN("❌ Cannot setup MQTT - WiFi not connected");
    return false;
  }
  
  DEBUG_PRINTLN("🔧 Starting enhanced MQTT setup...");
  
  // Configure MQTT client with enhanced settings
  mqttClient.setBufferSize(MQTT_MAX_PACKET_SIZE);
  mqttClient.setKeepAlive(MQTT_KEEPALIVE_ENHANCED);
  mqttClient.setSocketTimeout(MQTT_SOCKET_TIMEOUT_ENHANCED);
  
  // Set server
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(onMqttMessageEnhanced);  // Use enhanced message handler
  
  DEBUG_PRINTF("📡 MQTT Server: %s:%d\n", MQTT_SERVER, MQTT_PORT);
  DEBUG_PRINTF("📦 Buffer Size: %d bytes\n", MQTT_MAX_PACKET_SIZE);
  DEBUG_PRINTF("💓 Keepalive: %d seconds\n", MQTT_KEEPALIVE_ENHANCED);
  
  return connectMQTTEnhanced();
}

bool connectMQTTEnhanced() {
  if (!wifiConnected || !WiFi.isConnected()) {
    DEBUG_PRINTLN("❌ Cannot connect MQTT - WiFi not available");
    return false;
  }
  
  // Generate unique client ID to avoid conflicts
  uint64_t chipid = ESP.getEfuseMac();
  String clientId = "FacultyDesk_" + String(FACULTY_ID) + "_" + 
                   String((uint32_t)(chipid >> 32), HEX) + 
                   String((uint32_t)chipid, HEX);
  
  DEBUG_PRINTF("🔗 MQTT Client ID: %s\n", clientId.c_str());
  
  // Set last will message for connection monitoring
  String willTopic = String("consultease/faculty/") + String(FACULTY_ID) + "/status";
  String willMessage = "{\"status\":\"offline\",\"timestamp\":" + String(millis()) + 
                      ",\"reason\":\"connection_lost\"}";
  mqttClient.setWill(willTopic.c_str(), willMessage.c_str(), 1, true);
  
  // Attempt connection
  bool connected = false;
  if (strlen(MQTT_USERNAME) > 0) {
    connected = mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD);
  } else {
    connected = mqttClient.connect(clientId.c_str());
  }
  
  if (connected) {
    DEBUG_PRINTLN("✅ MQTT connected successfully!");
    mqttConnected = true;
    connection_health.mqtt_stable = true;
    connection_health.mqtt_last_connected = millis();
    connection_health.mqtt_reconnect_count = 0;  // Reset counter on success
    
    // Subscribe to topics immediately
    String messagesTopic = String("consultease/faculty/") + String(FACULTY_ID) + "/messages";
    String cancellationTopic = String("consultease/faculty/") + String(FACULTY_ID) + "/cancellations";
    
    bool subMessages = mqttClient.subscribe(messagesTopic.c_str(), 1);
    bool subCancellations = mqttClient.subscribe(cancellationTopic.c_str(), 1);
    
    DEBUG_PRINTF("📨 Subscribed to messages: %s\n", subMessages ? "✅" : "❌");
    DEBUG_PRINTF("📨 Subscribed to cancellations: %s\n", subCancellations ? "✅" : "❌");
    
    // Publish online status
    String statusTopic = String("consultease/faculty/") + String(FACULTY_ID) + "/status";
    String statusMessage = "{\"status\":\"online\",\"signal\":" + String(WiFi.RSSI()) + 
                          ",\"timestamp\":" + String(millis()) + "}";
    mqttClient.publish(statusTopic.c_str(), statusMessage.c_str(), true);
    
    return true;
  } else {
    int state = mqttClient.state();
    DEBUG_PRINTF("❌ MQTT connection failed! State: %d (%s)\n", state, getMqttStateString(state));
    
    mqttConnected = false;
    connection_health.mqtt_stable = false;
    return false;
  }
}

bool checkMQTTConnectionEnhanced() {
  static unsigned long lastCheck = 0;
  static unsigned long lastReconnectAttempt = 0;
  static bool wasConnected = false;
  
  // Check connection status every 2 seconds
  if (millis() - lastCheck < 2000) {
    return mqttClient.connected() && mqttConnected;
  }
  lastCheck = millis();
  
  bool currentlyConnected = mqttClient.connected() && (mqttClient.state() == 0);
  
  // Connection state changed
  if (currentlyConnected != wasConnected) {
    if (currentlyConnected) {
      DEBUG_PRINTLN("✅ MQTT connection restored!");
      mqttConnected = true;
      connection_health.mqtt_stable = true;
      connection_health.mqtt_last_connected = millis();
      connection_health.mqtt_reconnect_count = 0;  // Reset counter on success
    } else {
      DEBUG_PRINTF("❌ MQTT connection lost! State: %d (%s)\n", 
                   mqttClient.state(), getMqttStateString(mqttClient.state()));
      mqttConnected = false;
      connection_health.mqtt_stable = false;
    }
    wasConnected = currentlyConnected;
  }
  
  // Handle reconnection if disconnected
  if (!currentlyConnected && wifiConnected && WiFi.isConnected()) {
    unsigned long timeSinceLastAttempt = millis() - lastReconnectAttempt;
    unsigned long reconnectDelay = (connection_health.mqtt_reconnect_count < 3) ? 
                                   MQTT_RECONNECT_DELAY_FAST : MQTT_RECONNECT_DELAY_SLOW;
    
    if (timeSinceLastAttempt > reconnectDelay) {
      if (connection_health.mqtt_reconnect_count < MQTT_MAX_RECONNECT_ATTEMPTS) {
        DEBUG_PRINTF("🔄 MQTT reconnect attempt %d/%d\n", 
                     connection_health.mqtt_reconnect_count + 1, MQTT_MAX_RECONNECT_ATTEMPTS);
        
        if (connectMQTTEnhanced()) {
          DEBUG_PRINTLN("✅ MQTT reconnection successful!");
        } else {
          connection_health.mqtt_reconnect_count++;
        }
        lastReconnectAttempt = millis();
      } else {
        DEBUG_PRINTLN("❌ MQTT max reconnect attempts reached");
        // Reset counter after a longer delay
        if (timeSinceLastAttempt > 60000) {  // 1 minute
          connection_health.mqtt_reconnect_count = 0;
          DEBUG_PRINTLN("🔄 Resetting MQTT reconnect counter");
        }
      }
    }
  }
  
  // Process MQTT messages if connected
  if (currentlyConnected) {
    mqttClient.loop();
  }
  
  return currentlyConnected && mqttConnected;
}

// ================================
// CONNECTION DIAGNOSTICS
// ================================

void printConnectionDiagnosticsEnhanced() {
  DEBUG_PRINTLN("📊 === ENHANCED CONNECTION DIAGNOSTICS ===");
  
  // WiFi diagnostics
  DEBUG_PRINTF("WiFi Status: %s\n", wifiConnected ? "CONNECTED" : "DISCONNECTED");
  if (WiFi.isConnected()) {
    DEBUG_PRINTF("  SSID: %s\n", WiFi.SSID().c_str());
    DEBUG_PRINTF("  IP: %s\n", WiFi.localIP().toString().c_str());
    DEBUG_PRINTF("  Signal: %d dBm (%s)\n", WiFi.RSSI(), 
                 WiFi.RSSI() > -50 ? "EXCELLENT" : 
                 WiFi.RSSI() > -70 ? "GOOD" : 
                 WiFi.RSSI() > -80 ? "FAIR" : "POOR");
    DEBUG_PRINTF("  Reconnects: %d\n", connection_health.wifi_reconnect_count);
    DEBUG_PRINTF("  Stable: %s\n", connection_health.wifi_stable ? "YES" : "NO");
  }
  
  // MQTT diagnostics
  DEBUG_PRINTF("MQTT Status: %s\n", mqttConnected ? "CONNECTED" : "DISCONNECTED");
  DEBUG_PRINTF("  Server: %s:%d\n", MQTT_SERVER, MQTT_PORT);
  DEBUG_PRINTF("  State: %d (%s)\n", mqttClient.state(), getMqttStateString(mqttClient.state()));
  DEBUG_PRINTF("  Reconnects: %d\n", connection_health.mqtt_reconnect_count);
  DEBUG_PRINTF("  Stable: %s\n", connection_health.mqtt_stable ? "YES" : "NO");
  
  // System health
  DEBUG_PRINTF("System Health:\n");
  DEBUG_PRINTF("  Network Ready: %s\n", isNetworkReady() ? "YES" : "NO");
  DEBUG_PRINTF("  Can Process: %s\n", canProcessConsultations() ? "YES" : "NO");
  DEBUG_PRINTF("  Free Heap: %d bytes\n", ESP.getFreeHeap());
  DEBUG_PRINTF("  Uptime: %lu minutes\n", millis() / 60000);
  
  DEBUG_PRINTLN("==========================================");
}

// ================================
// INTEGRATION FUNCTIONS
// ================================

void initNetworkEnhanced() {
  DEBUG_PRINTLN("🚀 Initializing enhanced network system...");
  
  // Initialize connection health
  connection_health = {false, false, 0, 0, 0, 0, 0, 0};
  
  // Setup WiFi
  if (setupWiFiEnhanced()) {
    DEBUG_PRINTLN("✅ Enhanced WiFi setup complete");
    
    // Setup MQTT
    if (setupMQTTEnhanced()) {
      DEBUG_PRINTLN("✅ Enhanced MQTT setup complete");
    } else {
      DEBUG_PRINTLN("⚠️ MQTT setup failed, will retry in main loop");
    }
  } else {
    DEBUG_PRINTLN("❌ WiFi setup failed, will retry in main loop");
  }
}

void updateNetworkEnhanced() {
  // Update WiFi connection
  checkWiFiConnectionEnhanced();
  
  // Update MQTT connection (only if WiFi is connected)
  if (wifiConnected && WiFi.isConnected()) {
    checkMQTTConnectionEnhanced();
  } else if (mqttConnected) {
    // Force disconnect MQTT if WiFi is down
    mqttConnected = false;
    connection_health.mqtt_stable = false;
    DEBUG_PRINTLN("🔌 MQTT disconnected due to WiFi loss");
  }
  
  // Print diagnostics every 5 minutes
  static unsigned long lastDiagnostics = 0;
  if (millis() - lastDiagnostics > 300000) {  // 5 minutes
    printConnectionDiagnosticsEnhanced();
    lastDiagnostics = millis();
  }
}

// ================================
// CONFIGURATION VALIDATION
// ================================

bool validateNetworkConfig() {
  DEBUG_PRINTLN("🔍 Validating network configuration...");
  
  bool valid = true;
  
  // Check WiFi configuration
  if (strlen(WIFI_SSID) == 0) {
    DEBUG_PRINTLN("❌ WiFi SSID not configured");
    valid = false;
  }
  
  if (strlen(WIFI_PASSWORD) == 0) {
    DEBUG_PRINTLN("⚠️ WiFi password is empty (open network?)");
  }
  
  // Check MQTT configuration
  if (strlen(MQTT_SERVER) == 0) {
    DEBUG_PRINTLN("❌ MQTT server not configured");
    valid = false;
  }
  
  if (MQTT_PORT <= 0 || MQTT_PORT > 65535) {
    DEBUG_PRINTLN("❌ Invalid MQTT port");
    valid = false;
  }
  
  // Check faculty configuration
  if (FACULTY_ID <= 0) {
    DEBUG_PRINTLN("❌ Invalid faculty ID");
    valid = false;
  }
  
  if (strlen(FACULTY_NAME) == 0) {
    DEBUG_PRINTLN("❌ Faculty name not configured");
    valid = false;
  }
  
  if (valid) {
    DEBUG_PRINTLN("✅ Network configuration is valid");
    DEBUG_PRINTF("   WiFi: %s\n", WIFI_SSID);
    DEBUG_PRINTF("   MQTT: %s:%d\n", MQTT_SERVER, MQTT_PORT);
    DEBUG_PRINTF("   Faculty: %s (ID: %d)\n", FACULTY_NAME, FACULTY_ID);
  } else {
    DEBUG_PRINTLN("❌ Network configuration has errors!");
  }
  
  return valid;
}

#endif // FACULTY_DESK_UNIT_WIFI_MQTT_FIXES_H 