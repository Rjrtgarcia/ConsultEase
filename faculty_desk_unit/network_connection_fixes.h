#ifndef NETWORK_CONNECTION_FIXES_H
#define NETWORK_CONNECTION_FIXES_H

/*
 * NETWORK CONNECTION STABILITY FIXES FOR FACULTY DESK UNIT
 * 
 * This file contains fixes for common WiFi and MQTT connection issues
 * that cause the faculty desk units to frequently lose connection.
 * 
 * ISSUES IDENTIFIED:
 * 1. Aggressive reconnection delays causing long offline periods
 * 2. Insufficient WiFi signal quality monitoring
 * 3. MQTT keepalive settings too short
 * 4. Poor error handling for network disconnections
 * 5. Blocking operations in main loop affecting connectivity
 * 6. Missing power management optimizations
 * 7. No WiFi channel persistence causing connection drops
 * 8. Inadequate MQTT buffer size for consultation messages
 */

// ================================
// IMPROVED NETWORK CONFIGURATION
// ================================

// WiFi Stability Improvements
#define WIFI_CONNECT_TIMEOUT_IMPROVED 45000       // Increased from 30s to 45s
#define WIFI_RECONNECT_INTERVAL_IMPROVED 3000     // Reduced from 5s to 3s for faster recovery
#define WIFI_MAX_RETRIES_IMPROVED 15              // Increased retry attempts
#define WIFI_SIGNAL_THRESHOLD_IMPROVED -75        // Improved from -80 dBm
#define WIFI_POWER_SAVE_MODE WIFI_PS_NONE         // Disable power save for stability

// MQTT Stability Improvements  
#define MQTT_KEEPALIVE_IMPROVED 120               // Increased from 60s to 120s
#define MQTT_SOCKET_TIMEOUT_IMPROVED 30          // Increased from 15s to 30s
#define MQTT_CONNECT_TIMEOUT_IMPROVED 20000      // Increased from 15s to 20s
#define MQTT_RECONNECT_INTERVAL_IMPROVED 2000    // Reduced from 5s to 2s
#define MQTT_MAX_RETRIES_IMPROVED 20             // Increased retry attempts
#define MQTT_BUFFER_SIZE_IMPROVED 2048           // Increased from 1024 to 2048 bytes

// Connection Monitoring
#define CONNECTION_CHECK_INTERVAL 2000            // Check every 2 seconds instead of varying
#define HEARTBEAT_INTERVAL_IMPROVED 120000       // 2 minutes instead of 5 minutes
#define SIGNAL_QUALITY_CHECK_INTERVAL 10000      // Check signal every 10 seconds

// ================================
// IMPROVED WIFI FUNCTIONS
// ================================

// Enhanced WiFi connection with better error handling
bool connectWiFiImproved() {
    Serial.println("🔧 Starting improved WiFi connection...");
    
    // Disconnect any existing connection first
    WiFi.disconnect(true);
    delay(1000);
    
    // Set WiFi mode and disable power save
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);  // Disable sleep mode for better stability
    
    // Set static IP if configured (optional - helps with faster connections)
    // WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS);
    
    // Begin connection with timeout
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    unsigned long startTime = millis();
    int attempts = 0;
    
    Serial.printf("Connecting to WiFi: %s\n", WIFI_SSID);
    
    while (WiFi.status() != WL_CONNECTED && 
           (millis() - startTime) < WIFI_CONNECT_TIMEOUT_IMPROVED) {
        
        delay(500);
        Serial.print(".");
        attempts++;
        
        // Check for specific error conditions
        wl_status_t status = WiFi.status();
        if (attempts % 10 == 0) {
            Serial.printf("\nAttempt %d, Status: %d\n", attempts, status);
            
            switch (status) {
                case WL_NO_SSID_AVAIL:
                    Serial.println("❌ SSID not found - check network name");
                    break;
                case WL_CONNECT_FAILED:
                    Serial.println("❌ Connection failed - check password");
                    break;
                case WL_CONNECTION_LOST:
                    Serial.println("⚠️ Connection lost - retrying...");
                    WiFi.disconnect();
                    delay(1000);
                    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
                    break;
            }
        }
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi connected successfully!");
        Serial.printf("IP Address: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("Signal Strength: %d dBm\n", WiFi.RSSI());
        Serial.printf("Gateway: %s\n", WiFi.gatewayIP().toString().c_str());
        Serial.printf("DNS: %s\n", WiFi.dnsIP().toString().c_str());
        
        // Set hostname for easier network identification
        String hostname = "FacultyDesk_" + String(FACULTY_ID);
        WiFi.setHostname(hostname.c_str());
        
        return true;
    } else {
        Serial.println("\n❌ WiFi connection failed!");
        Serial.printf("Final status: %d\n", WiFi.status());
        return false;
    }
}

// Enhanced WiFi monitoring with signal quality checks
void monitorWiFiConnection() {
    static unsigned long lastCheck = 0;
    static int consecutiveFailures = 0;
    static int lastRSSI = 0;
    
    if (millis() - lastCheck < CONNECTION_CHECK_INTERVAL) {
        return;
    }
    
    lastCheck = millis();
    
    if (WiFi.status() != WL_CONNECTED) {
        consecutiveFailures++;
        Serial.printf("⚠️ WiFi disconnected (failure #%d)\n", consecutiveFailures);
        
        // Attempt immediate reconnection for the first few failures
        if (consecutiveFailures <= 3) {
            Serial.println("🔄 Attempting immediate WiFi reconnection...");
            if (connectWiFiImproved()) {
                consecutiveFailures = 0;
                return;
            }
        }
        
        // For persistent failures, wait before retry
        static unsigned long lastReconnectAttempt = 0;
        if (millis() - lastReconnectAttempt > WIFI_RECONNECT_INTERVAL_IMPROVED) {
            Serial.println("🔄 Attempting WiFi reconnection after delay...");
            if (connectWiFiImproved()) {
                consecutiveFailures = 0;
            }
            lastReconnectAttempt = millis();
        }
    } else {
        // WiFi is connected - monitor signal quality
        consecutiveFailures = 0;
        
        int currentRSSI = WiFi.RSSI();
        if (abs(currentRSSI - lastRSSI) > 5 || lastRSSI == 0) {
            Serial.printf("📶 Signal: %d dBm", currentRSSI);
            
            if (currentRSSI < WIFI_SIGNAL_THRESHOLD_IMPROVED) {
                Serial.println(" ⚠️ WEAK");
            } else if (currentRSSI < -50) {
                Serial.println(" 📶 GOOD");
            } else {
                Serial.println(" 📶 EXCELLENT");
            }
            
            lastRSSI = currentRSSI;
        }
    }
}

// ================================
// IMPROVED MQTT FUNCTIONS
// ================================

// Enhanced MQTT connection with better error handling
bool connectMQTTImproved() {
    if (!WiFi.isConnected()) {
        Serial.println("❌ Cannot connect MQTT - WiFi not connected");
        return false;
    }
    
    Serial.println("🔧 Starting improved MQTT connection...");
    
    // Configure MQTT client with improved settings
    mqttClient.setBufferSize(MQTT_BUFFER_SIZE_IMPROVED);
    mqttClient.setKeepAlive(MQTT_KEEPALIVE_IMPROVED);
    mqttClient.setSocketTimeout(MQTT_SOCKET_TIMEOUT_IMPROVED);
    
    // Generate unique client ID to avoid conflicts
    uint64_t chipid = ESP.getEfuseMac();
    String clientId = "FacultyDesk_" + String(FACULTY_ID) + "_" + 
                     String((uint32_t)(chipid >> 32), HEX) + 
                     String((uint32_t)chipid, HEX);
    
    Serial.printf("MQTT Client ID: %s\n", clientId.c_str());
    Serial.printf("MQTT Server: %s:%d\n", MQTT_SERVER, MQTT_PORT);
    Serial.printf("MQTT Keepalive: %ds\n", MQTT_KEEPALIVE_IMPROVED);
    Serial.printf("MQTT Buffer: %d bytes\n", MQTT_BUFFER_SIZE_IMPROVED);
    
    // Set last will message for better connection monitoring
    String willTopic = "consultease/faculty/" + String(FACULTY_ID) + "/status";
    String willMessage = "{\"status\":\"offline\",\"timestamp\":" + String(millis()) + "}";
    mqttClient.setWill(willTopic.c_str(), willMessage.c_str(), 1, true);
    
    // Attempt connection
    bool connected = false;
    if (strlen(MQTT_USERNAME) > 0) {
        connected = mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD);
    } else {
        connected = mqttClient.connect(clientId.c_str());
    }
    
    if (connected) {
        Serial.println("✅ MQTT connected successfully!");
        
        // Subscribe to topics immediately
        String messagesTopic = "consultease/faculty/" + String(FACULTY_ID) + "/messages";
        String cancellationTopic = "consultease/faculty/" + String(FACULTY_ID) + "/cancellations";
        
        bool subMessages = mqttClient.subscribe(messagesTopic.c_str(), 1);
        bool subCancellations = mqttClient.subscribe(cancellationTopic.c_str(), 1);
        
        Serial.printf("📨 Subscribed to messages: %s\n", subMessages ? "✅" : "❌");
        Serial.printf("📨 Subscribed to cancellations: %s\n", subCancellations ? "✅" : "❌");
        
        // Publish online status
        String statusTopic = "consultease/faculty/" + String(FACULTY_ID) + "/status";
        String statusMessage = "{\"status\":\"online\",\"signal\":" + String(WiFi.RSSI()) + 
                              ",\"timestamp\":" + String(millis()) + "}";
        mqttClient.publish(statusTopic.c_str(), statusMessage.c_str(), true);
        
        return true;
    } else {
        int state = mqttClient.state();
        Serial.printf("❌ MQTT connection failed! State: %d\n", state);
        
        switch (state) {
            case -4: Serial.println("   Connection timeout"); break;
            case -3: Serial.println("   Connection lost"); break;
            case -2: Serial.println("   Connect failed"); break;
            case -1: Serial.println("   Disconnected"); break;
            case 1:  Serial.println("   Bad protocol version"); break;
            case 2:  Serial.println("   Bad client ID"); break;
            case 3:  Serial.println("   Server unavailable"); break;
            case 4:  Serial.println("   Bad credentials"); break;
            case 5:  Serial.println("   Not authorized"); break;
            default: Serial.println("   Unknown error"); break;
        }
        
        return false;
    }
}

// Enhanced MQTT monitoring with better reconnection logic
void monitorMQTTConnection() {
    static unsigned long lastCheck = 0;
    static int consecutiveFailures = 0;
    static unsigned long lastHeartbeat = 0;
    
    if (millis() - lastCheck < CONNECTION_CHECK_INTERVAL) {
        return;
    }
    
    lastCheck = millis();
    
    // Only proceed if WiFi is connected
    if (!WiFi.isConnected()) {
        if (mqttConnected) {
            Serial.println("⚠️ MQTT marked offline - WiFi disconnected");
            mqttConnected = false;
        }
        return;
    }
    
    // Check MQTT connection
    if (!mqttClient.connected()) {
        if (mqttConnected) {
            Serial.println("⚠️ MQTT connection lost!");
            mqttConnected = false;
        }
        
        consecutiveFailures++;
        
        // Attempt reconnection
        static unsigned long lastReconnectAttempt = 0;
        if (millis() - lastReconnectAttempt > MQTT_RECONNECT_INTERVAL_IMPROVED) {
            Serial.printf("🔄 MQTT reconnection attempt #%d\n", consecutiveFailures);
            
            if (connectMQTTImproved()) {
                Serial.println("✅ MQTT reconnected successfully!");
                mqttConnected = true;
                consecutiveFailures = 0;
            } else if (consecutiveFailures > MQTT_MAX_RETRIES_IMPROVED) {
                Serial.println("❌ MQTT max retries reached, will retry later");
                consecutiveFailures = 0;  // Reset to try again later
            }
            
            lastReconnectAttempt = millis();
        }
    } else {
        // MQTT is connected
        if (!mqttConnected) {
            Serial.println("✅ MQTT connection restored!");
            mqttConnected = true;
            consecutiveFailures = 0;
        }
        
        // Send periodic heartbeat
        if (millis() - lastHeartbeat > HEARTBEAT_INTERVAL_IMPROVED) {
            String heartbeatTopic = "consultease/faculty/" + String(FACULTY_ID) + "/heartbeat";
            String heartbeatMessage = "{\"timestamp\":" + String(millis()) + 
                                    ",\"signal\":" + String(WiFi.RSSI()) + 
                                    ",\"uptime\":" + String(millis() / 1000) + "}";
            
            if (mqttClient.publish(heartbeatTopic.c_str(), heartbeatMessage.c_str())) {
                Serial.println("💓 Heartbeat sent");
            } else {
                Serial.println("❌ Heartbeat failed");
            }
            
            lastHeartbeat = millis();
        }
        
        // Process MQTT messages
        mqttClient.loop();
    }
}

// ================================
// IMPROVED SETUP FUNCTIONS
// ================================

void setupNetworkingImproved() {
    Serial.println("🔧 Setting up improved networking...");
    
    // Initialize WiFi with improved settings
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);  // Disable WiFi sleep for stability
    
    // Set power mode for better signal quality
    WiFi.setTxPower(WIFI_POWER_19_5dBm);  // Max power for better range
    
    // Connect to WiFi
    if (connectWiFiImproved()) {
        Serial.println("✅ WiFi setup complete");
        
        // Setup MQTT
        if (connectMQTTImproved()) {
            Serial.println("✅ MQTT setup complete");
        } else {
            Serial.println("⚠️ MQTT setup failed, will retry in main loop");
        }
    } else {
        Serial.println("❌ WiFi setup failed, will retry in main loop");
    }
}

// ================================
// MAIN LOOP INTEGRATION
// ================================

void updateNetworkConnectionsImproved() {
    // Monitor both WiFi and MQTT connections
    monitorWiFiConnection();
    monitorMQTTConnection();
    
    // Update connection status on display
    static unsigned long lastStatusUpdate = 0;
    if (millis() - lastStatusUpdate > 5000) {  // Update every 5 seconds
        updateConnectionStatusDisplay();
        lastStatusUpdate = millis();
    }
}

void updateConnectionStatusDisplay() {
    // This function should be implemented in the main sketch
    // to update the display with current connection status
    
    // Example implementation:
    /*
    tft.fillRect(0, 0, 320, 20, COLOR_BLACK);
    tft.setCursor(5, 5);
    tft.setTextColor(COLOR_WHITE);
    tft.setTextSize(1);
    
    if (WiFi.isConnected()) {
        if (mqttConnected) {
            tft.print("ONLINE");
        } else {
            tft.print("WiFi OK, MQTT DOWN");
        }
    } else {
        tft.print("OFFLINE");
    }
    */
}

// ================================
// DIAGNOSTIC FUNCTIONS
// ================================

void printNetworkDiagnostics() {
    Serial.println("\n📊 NETWORK DIAGNOSTICS:");
    Serial.printf("WiFi Status: %s\n", WiFi.isConnected() ? "CONNECTED" : "DISCONNECTED");
    
    if (WiFi.isConnected()) {
        Serial.printf("IP: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("Signal: %d dBm\n", WiFi.RSSI());
        Serial.printf("Channel: %d\n", WiFi.channel());
        Serial.printf("Gateway: %s\n", WiFi.gatewayIP().toString().c_str());
    }
    
    Serial.printf("MQTT Status: %s\n", mqttConnected ? "CONNECTED" : "DISCONNECTED");
    if (!mqttConnected && mqttClient.state() != 0) {
        Serial.printf("MQTT State: %d\n", mqttClient.state());
    }
    
    Serial.printf("Free Heap: %d bytes\n", ESP.getFreeHeap());
    Serial.printf("Uptime: %lu seconds\n", millis() / 1000);
    Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
}

#endif // NETWORK_CONNECTION_FIXES_H 