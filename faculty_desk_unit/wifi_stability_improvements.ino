/*
 * WiFi Stability Improvements for ConsultEase Faculty Desk Units
 * 
 * This file contains enhanced WiFi management to fix frequent connection failures.
 * Apply these improvements to your main faculty_desk_unit.ino file.
 */

// ================================
// ENHANCED WIFI CONFIGURATION
// ================================

// Add these variables at the top of your main file
unsigned long wifiHealthCheckInterval = 10000;  // Check WiFi health every 10 seconds
unsigned long lastWifiHealthCheck = 0;
int consecutiveWifiFailures = 0;
const int maxConsecutiveWifiFailures = 3;
bool forceWifiReconnect = false;

// Enhanced WiFi signal strength monitoring
int previousRSSI = 0;
int poorSignalCount = 0;
const int maxPoorSignalCount = 5;  // Allow 5 consecutive poor readings before action

// WiFi connection quality metrics
struct WiFiQualityMetrics {
  int reconnectCount = 0;
  unsigned long totalUptime = 0;
  unsigned long lastConnectTime = 0;
  int averageRSSI = 0;
  int worstRSSI = 0;
  bool isStable = false;
};

WiFiQualityMetrics wifiMetrics;

// ================================
// ENHANCED WIFI SETUP WITH POWER MANAGEMENT
// ================================

void setupWiFiEnhanced() {
  DEBUG_PRINTLN("🔧 Enhanced WiFi setup with stability improvements...");
  
  // Configure WiFi for maximum stability
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(false);  // Manual control for better diagnostics
  WiFi.setSleep(false);          // Disable power saving for stability
  WiFi.persistent(false);        // Don't save credentials to flash (reduces wear)
  
  // Set static IP if available (improves connection speed)
  #ifdef STATIC_IP_ENABLED
  IPAddress local_IP(STATIC_IP);
  IPAddress gateway(GATEWAY_IP);
  IPAddress subnet(SUBNET_MASK);
  IPAddress primaryDNS(PRIMARY_DNS);
  IPAddress secondaryDNS(SECONDARY_DNS);
  
  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) {
    DEBUG_PRINTLN("⚠️ Static IP configuration failed, using DHCP");
  }
  #endif
  
  // Initialize metrics
  wifiMetrics.lastConnectTime = millis();
  wifiRetryCount = 0;
  consecutiveWifiFailures = 0;
  
  connectWiFiWithEnhancedBackoff();
}

// ================================
// ENHANCED CONNECTION WITH ADAPTIVE BACKOFF
// ================================

void connectWiFiWithEnhancedBackoff() {
  if (wifiRetryCount >= maxWifiRetries) {
    DEBUG_PRINTF("❌ WiFi failed after %d attempts, entering recovery mode\n", maxWifiRetries);
    enterWiFiRecoveryMode();
    return;
  }

  DEBUG_PRINTF("📡 Enhanced WiFi attempt %d/%d\n", wifiRetryCount + 1, maxWifiRetries);
  
  // Progressive connection strategy
  if (wifiRetryCount > 0) {
    DEBUG_PRINTLN("🔄 Performing WiFi reset sequence...");
    
    // Full WiFi reset for stubborn connections
    WiFi.disconnect(true);
    delay(1000);
    
    // Reset WiFi stack completely
    WiFi.mode(WIFI_OFF);
    delay(500);
    WiFi.mode(WIFI_STA);
    delay(500);
    
    // Re-apply power management settings
    WiFi.setSleep(false);
    WiFi.persistent(false);
  }
  
  // Enhanced connection with power and channel optimization
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  // Adaptive timeout based on retry count
  unsigned long baseTimeout = WIFI_CONNECT_TIMEOUT;
  unsigned long adaptiveTimeout = baseTimeout + (wifiRetryCount * 3000);
  unsigned long startTime = millis();
  
  DEBUG_PRINTF("🕐 Connection timeout: %lu ms\n", adaptiveTimeout);
  
  while (WiFi.status() != WL_CONNECTED && (millis() - startTime) < adaptiveTimeout) {
    delay(250);  // Reduced delay for faster status checking
    
    // Show progress and update system status
    if ((millis() - startTime) % 2000 == 0) {
      DEBUG_PRINT(".");
      updateSystemStatus();
    }
    
    // Early exit on specific error conditions
    wl_status_t status = WiFi.status();
    if (status == WL_CONNECT_FAILED || status == WL_NO_SSID_AVAIL) {
      DEBUG_PRINTF("\n❌ WiFi error detected: %d\n", status);
      break;
    }
    
    // Yield to prevent watchdog reset
    yield();
  }

  if (WiFi.status() == WL_CONNECTED) {
    handleSuccessfulWiFiConnection();
  } else {
    handleFailedWiFiConnection();
  }
}

// ================================
// SUCCESS AND FAILURE HANDLERS
// ================================

void handleSuccessfulWiFiConnection() {
  wifiConnected = true;
  wifiRetryCount = 0;
  consecutiveWifiFailures = 0;
  forceWifiReconnect = false;
  
  wifiStableTime = millis();
  wifiConnectionStable = false;
  
  // Update connection metrics
  wifiMetrics.reconnectCount++;
  wifiMetrics.lastConnectTime = millis();
  
  currentWifiRSSI = WiFi.RSSI();
  previousRSSI = currentWifiRSSI;
  poorSignalCount = 0;
  
  // Update running average RSSI
  if (wifiMetrics.averageRSSI == 0) {
    wifiMetrics.averageRSSI = currentWifiRSSI;
  } else {
    wifiMetrics.averageRSSI = (wifiMetrics.averageRSSI + currentWifiRSSI) / 2;
  }
  
  // Track worst RSSI
  if (currentWifiRSSI < wifiMetrics.worstRSSI) {
    wifiMetrics.worstRSSI = currentWifiRSSI;
  }
  
  DEBUG_PRINTF("\n✅ WiFi connected! IP: %s\n", WiFi.localIP().toString().c_str());
  DEBUG_PRINTF("📶 Signal: %d dBm (Avg: %d, Worst: %d)\n", 
               currentWifiRSSI, wifiMetrics.averageRSSI, wifiMetrics.worstRSSI);
  DEBUG_PRINTF("🔄 Reconnect count: %d\n", wifiMetrics.reconnectCount);
  
  // Enhanced signal quality assessment
  assessSignalQuality(currentWifiRSSI);
  
  // Initialize time and publish status
  setupTimeWithRetry();
  publishEnhancedPresenceUpdate();
  updateSystemStatus();
}

void handleFailedWiFiConnection() {
  wifiConnected = false;
  wifiRetryCount++;
  consecutiveWifiFailures++;
  
  wl_status_t status = WiFi.status();
  DEBUG_PRINTF("\n❌ WiFi connection failed! Status: %d\n", status);
  
  // Adaptive backoff with jitter to prevent synchronized retries
  int baseDelay = wifiReconnectDelay * (1 << min(wifiRetryCount - 1, 3));
  int jitter = random(1000, 3000);  // Add 1-3 second random jitter
  wifiReconnectDelay = min(baseDelay + jitter, 45000);  // Cap at 45 seconds
  
  DEBUG_PRINTF("🔄 Next attempt in %d seconds\n", wifiReconnectDelay / 1000);
  
  lastWifiReconnectAttempt = millis();
  updateSystemStatus();
  
  // Emergency recovery after multiple consecutive failures
  if (consecutiveWifiFailures >= maxConsecutiveWifiFailures) {
    DEBUG_PRINTLN("🚨 Multiple consecutive failures detected, starting recovery");
    enterWiFiRecoveryMode();
  }
}

// ================================
// ENHANCED WIFI MONITORING
// ================================

void checkWiFiConnectionEnhanced() {
  unsigned long now = millis();
  
  // Regular health check
  if (now - lastWifiHealthCheck > wifiHealthCheckInterval) {
    performWiFiHealthCheck();
    lastWifiHealthCheck = now;
  }
  
  // Force reconnect if requested
  if (forceWifiReconnect) {
    DEBUG_PRINTLN("🔄 Force WiFi reconnect requested");
    forceWifiReconnect = false;
    WiFi.disconnect();
    delay(500);
    connectWiFiWithEnhancedBackoff();
    return;
  }
  
  // Check connection status
  if (WiFi.status() != WL_CONNECTED) {
    if (wifiConnected) {
      DEBUG_PRINTLN("⚠️ WiFi connection lost!");
      wifiConnected = false;
      wifiConnectionStable = false;
      timeInitialized = false;
      mqttConnected = false;
      updateSystemStatus();
    }

    // Attempt reconnection with enhanced backoff
    if (now - lastWifiReconnectAttempt > wifiReconnectDelay) {
      connectWiFiWithEnhancedBackoff();
    }
  } else {
    // Connection is up - perform quality monitoring
    if (!wifiConnected) {
      DEBUG_PRINTLN("✅ WiFi reconnected!");
      handleSuccessfulWiFiConnection();
    }
    
    monitorConnectionQuality();
    checkConnectionStability(now);
  }
}

// ================================
// CONNECTION QUALITY MONITORING
// ================================

void performWiFiHealthCheck() {
  if (!wifiConnected) return;
  
  // Check signal strength
  int newRSSI = WiFi.RSSI();
  int rssiDelta = abs(newRSSI - currentWifiRSSI);
  
  if (rssiDelta > 5) {  // Significant change
    DEBUG_PRINTF("📶 Signal changed: %d -> %d dBm (Δ%+d)\n", 
                 currentWifiRSSI, newRSSI, newRSSI - currentWifiRSSI);
    currentWifiRSSI = newRSSI;
  }
  
  // Update metrics
  wifiMetrics.averageRSSI = (wifiMetrics.averageRSSI * 9 + newRSSI) / 10;  // Weighted average
  if (newRSSI < wifiMetrics.worstRSSI) {
    wifiMetrics.worstRSSI = newRSSI;
  }
  
  // Poor signal detection
  if (newRSSI < -85) {
    poorSignalCount++;
    DEBUG_PRINTF("⚠️ Poor signal detected (%d dBm) - Count: %d/%d\n", 
                 newRSSI, poorSignalCount, maxPoorSignalCount);
    
    if (poorSignalCount >= maxPoorSignalCount) {
      DEBUG_PRINTLN("🚨 Persistent poor signal - requesting reconnect");
      forceWifiReconnect = true;
      poorSignalCount = 0;
    }
  } else {
    poorSignalCount = max(0, poorSignalCount - 1);  // Gradual recovery
  }
  
  // Check for IP address validity
  IPAddress ip = WiFi.localIP();
  if (ip[0] == 0) {
    DEBUG_PRINTLN("⚠️ Invalid IP address detected - forcing reconnect");
    forceWifiReconnect = true;
  }
}

void monitorConnectionQuality() {
  static unsigned long lastQualityCheck = 0;
  unsigned long now = millis();
  
  if (now - lastQualityCheck > 30000) {  // Every 30 seconds
    assessSignalQuality(WiFi.RSSI());
    
    // Update uptime metrics
    if (wifiMetrics.lastConnectTime > 0) {
      wifiMetrics.totalUptime += (now - lastQualityCheck);
    }
    
    lastQualityCheck = now;
  }
}

void assessSignalQuality(int rssi) {
  String quality;
  if (rssi > -60) {
    quality = "Excellent";
  } else if (rssi > -70) {
    quality = "Good";
  } else if (rssi > -80) {
    quality = "Fair";
  } else if (rssi > -90) {
    quality = "Poor";
  } else {
    quality = "Very Poor";
  }
  
  DEBUG_PRINTF("📶 Signal quality: %s (%d dBm)\n", quality.c_str(), rssi);
  
  // Proactive reconnection for very poor signals
  if (rssi < -90 && wifiConnected) {
    DEBUG_PRINTLN("🚨 Signal too weak - proactive reconnection");
    forceWifiReconnect = true;
  }
}

// ================================
// WIFI RECOVERY MODE
// ================================

void enterWiFiRecoveryMode() {
  DEBUG_PRINTLN("🔧 Entering WiFi recovery mode...");
  
  // Complete WiFi stack reset
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  delay(2000);  // Extended delay for full reset
  
  // Clear all counters
  wifiRetryCount = 0;
  consecutiveWifiFailures = 0;
  poorSignalCount = 0;
  wifiReconnectDelay = 5000;  // Reset to base delay
  
  // Try alternative recovery methods
  DEBUG_PRINTLN("🔄 Attempting recovery strategies...");
  
  // Strategy 1: Reset with different power settings
  WiFi.mode(WIFI_STA);
  delay(500);
  
  // Strategy 2: Try without power management first
  WiFi.setSleep(true);   // Try with power saving first
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  delay(10000);
  
  if (WiFi.status() != WL_CONNECTED) {
    DEBUG_PRINTLN("🔄 Recovery attempt 1 failed, trying without power saving...");
    WiFi.disconnect();
    delay(1000);
    WiFi.setSleep(false);  // Disable power saving
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    delay(10000);
  }
  
  // Strategy 3: If still failing, schedule longer recovery delay
  if (WiFi.status() != WL_CONNECTED) {
    DEBUG_PRINTLN("🔄 Recovery failed, scheduling extended retry...");
    lastWifiReconnectAttempt = millis();
    wifiReconnectDelay = 60000;  // 1 minute delay
  } else {
    DEBUG_PRINTLN("✅ WiFi recovery successful!");
    handleSuccessfulWiFiConnection();
  }
}

// ================================
// ENHANCED PRESENCE UPDATE WITH CONNECTIVITY INFO
// ================================

void publishEnhancedPresenceUpdate() {
  if (!mqttClient.connected()) return;

  String payload = "{";
  payload += "\"faculty_id\":" + String(FACULTY_ID) + ",";
  payload += "\"faculty_name\":\"" + String(FACULTY_NAME) + "\",";
  payload += "\"present\":" + String(presenceDetector.getPresence() ? "true" : "false") + ",";
  payload += "\"status\":\"" + String(presenceDetector.getPresence() ? "AVAILABLE" : "AWAY") + "\",";
  payload += "\"timestamp\":" + String(millis()) + ",";
  
  // Enhanced connectivity information
  payload += "\"wifi_rssi\":" + String(currentWifiRSSI) + ",";
  payload += "\"wifi_quality\":\"" + getSignalQualityString() + "\",";
  payload += "\"connection_stable\":" + String(wifiConnectionStable ? "true" : "false") + ",";
  payload += "\"reconnect_count\":" + String(wifiMetrics.reconnectCount) + ",";
  payload += "\"avg_rssi\":" + String(wifiMetrics.averageRSSI) + ",";
  payload += "\"uptime\":" + String(millis() - wifiMetrics.lastConnectTime);
  payload += "}";

  DEBUG_PRINTF("📡 Enhanced presence: %s\n", payload.c_str());
  
  bool success = mqttClient.publish(MQTT_TOPIC_STATUS, payload.c_str(), true);  // Retained
  DEBUG_PRINTF("📤 Presence update: %s\n", success ? "SUCCESS" : "FAILED");
}

String getSignalQualityString() {
  int rssi = WiFi.RSSI();
  if (rssi > -60) return "excellent";
  if (rssi > -70) return "good";
  if (rssi > -80) return "fair";
  if (rssi > -90) return "poor";
  return "very_poor";
}

// ================================
// USAGE INSTRUCTIONS
// ================================

/*
 * TO APPLY THESE IMPROVEMENTS:
 * 
 * 1. Replace your existing setupWiFi() function with setupWiFiEnhanced()
 * 2. Replace checkWiFiConnection() with checkWiFiConnectionEnhanced()
 * 3. Add the new variables at the top of your main file
 * 4. Replace publishPresenceUpdate() with publishEnhancedPresenceUpdate()
 * 5. In your main loop(), call checkWiFiConnectionEnhanced() instead of checkWiFiConnection()
 * 
 * EXAMPLE INTEGRATION:
 * 
 * void setup() {
 *   // ... existing setup code ...
 *   setupWiFiEnhanced();  // Instead of setupWiFi()
 *   // ... rest of setup ...
 * }
 * 
 * void loop() {
 *   checkWiFiConnectionEnhanced();  // Instead of checkWiFiConnection()
 *   // ... rest of loop ...
 * }
 * 
 * BENEFITS:
 * - Adaptive reconnection with exponential backoff + jitter
 * - Signal quality monitoring with proactive reconnection
 * - Recovery mode for persistent failures
 * - Enhanced metrics and diagnostics
 * - Reduced power consumption options
 * - Better MQTT connectivity reliability
 */ 