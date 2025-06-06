// ================================
// ENHANCED WIFI STABILITY FUNCTIONS FOR ESP32 FACULTY DESK UNIT
// ================================
// This file provides robust WiFi management to address frequent disconnections
// Apply these functions to replace the existing WiFi code in faculty_desk_unit.ino

// ===== ENHANCED WIFI CONFIGURATION =====
// Add these #defines at the top of your main sketch if not already defined
#ifndef WIFI_CONNECT_TIMEOUT_ENHANCED
#define WIFI_CONNECT_TIMEOUT_ENHANCED 45000    // 45 seconds
#define WIFI_RECONNECT_INTERVAL_ENHANCED 3000  // 3 seconds
#define WIFI_MAX_RETRIES_ENHANCED 15           // 15 attempts
#define WIFI_SIGNAL_THRESHOLD_ENHANCED -75     // -75 dBm minimum
#define WIFI_HEALTH_CHECK_INTERVAL_ENHANCED 5000 // Check every 5 seconds
#endif

// ===== ENHANCED WIFI VARIABLES =====
// Add these global variables to your main sketch
/*
// WiFi connection state tracking - ADD THESE TO YOUR MAIN SKETCH
int wifiConnectionState = 0; // 0=disconnected, 1=connecting, 2=connected, 3=stable
unsigned long wifiStateStartTime = 0;
int wifiRetryCount = 0;
int consecutiveWifiFailures = 0;
bool forceWifiReconnect = false;

// Signal quality monitoring
int wifiSignalSamples[5] = {-100, -100, -100, -100, -100};
int wifiSignalIndex = 0;
int averageWifiSignal = -100;
int poorSignalCount = 0;

// Timing variables
unsigned long lastWifiReconnectAttempt = 0;
unsigned long lastWifiHealthCheck = 0;
unsigned long lastWifiSignalCheck = 0;
unsigned long wifiConnectedTime = 0;

// Error tracking
String lastWifiError = "";
int wifiErrorCount = 0;
bool wifiRecoveryMode = false;
*/

// ================================
// ENHANCED WIFI SETUP FUNCTION
// ================================
void setupWiFiEnhanced() {
    DEBUG_PRINTLN("🔧 Enhanced WiFi setup starting...");
    DEBUG_PRINTF("   Target SSID: %s\n", WIFI_SSID);
    DEBUG_PRINTF("   Signal threshold: %d dBm\n", WIFI_SIGNAL_THRESHOLD_ENHANCED);
    
    // Initialize WiFi state tracking
    wifiConnectionState = 0; // disconnected
    wifiRetryCount = 0;
    consecutiveWifiFailures = 0;
    forceWifiReconnect = false;
    
    // Initialize signal quality tracking
    for (int i = 0; i < 5; i++) {
        wifiSignalSamples[i] = -100;
    }
    wifiSignalIndex = 0;
    poorSignalCount = 0;
    
    // Configure WiFi for maximum stability
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(false); // Manual control for better reliability
    WiFi.setSleep(false); // Disable power saving for stability
    
    DEBUG_PRINTLN("✅ WiFi configuration applied");
    
    // Start initial connection attempt
    connectWiFiEnhanced();
}

// ================================
// ENHANCED WIFI CONNECTION FUNCTION
// ================================
void connectWiFiEnhanced() {
    if (wifiRetryCount >= WIFI_MAX_RETRIES_ENHANCED) {
        DEBUG_PRINTF("❌ WiFi connection failed after %d attempts\n", WIFI_MAX_RETRIES_ENHANCED);
        wifiConnectionState = 5; // failed state
        consecutiveWifiFailures++;
        
        // Trigger recovery mode if too many consecutive failures
        if (consecutiveWifiFailures >= 3) {
            initiateWiFiRecoveryEnhanced();
        }
        
        updateSystemStatus();
        return;
    }

    wifiConnectionState = 1; // connecting
    wifiStateStartTime = millis();
    
    DEBUG_PRINTF("📡 WiFi connection attempt %d/%d\n", wifiRetryCount + 1, WIFI_MAX_RETRIES_ENHANCED);
    
    // Disconnect cleanly before reconnecting
    WiFi.disconnect(true);
    delay(1000); // Allow clean disconnect
    
    // Start connection
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    // Wait for connection with enhanced timeout
    unsigned long startTime = millis();
    unsigned long timeout = WIFI_CONNECT_TIMEOUT_ENHANCED + (wifiRetryCount * 5000);
    
    while (WiFi.status() != WL_CONNECTED && (millis() - startTime) < timeout) {
        delay(500);
        DEBUG_PRINT(".");
        
        // Update display during connection attempt
        updateSystemStatus();
        
        // Check for specific failure conditions
        wl_status_t currentStatus = WiFi.status();
        if (currentStatus == WL_CONNECT_FAILED || currentStatus == WL_CONNECTION_LOST) {
            DEBUG_PRINTF("\n❌ WiFi connection failed with status: %d\n", currentStatus);
            handleWiFiErrorEnhanced("CONNECTION_FAILED");
            return;
        }
        
        // Allow other tasks to run
        yield();
    }

    // Check final connection status
    if (WiFi.status() == WL_CONNECTED) {
        handleSuccessfulWiFiConnectionEnhanced();
    } else {
        handleFailedWiFiConnectionEnhanced();
    }
}

// ================================
// SUCCESS HANDLER
// ================================
void handleSuccessfulWiFiConnectionEnhanced() {
    wifiConnected = true;
    wifiConnectionState = 2; // connected
    wifiStateStartTime = millis();
    wifiConnectedTime = millis();
    wifiRetryCount = 0;
    consecutiveWifiFailures = 0;
    wifiRecoveryMode = false;
    
    // Get initial signal quality
    int initialRSSI = WiFi.RSSI();
    updateWiFiSignalSampleEnhanced(initialRSSI);
    
    DEBUG_PRINTF("\n✅ WiFi connected successfully!\n");
    DEBUG_PRINTF("   IP Address: %s\n", WiFi.localIP().toString().c_str());
    DEBUG_PRINTF("   Signal Strength: %d dBm (%s)\n", initialRSSI, getSignalQualityTextEnhanced(initialRSSI));
    DEBUG_PRINTF("   Gateway: %s\n", WiFi.gatewayIP().toString().c_str());
    
    // Setup dependent services
    setupTimeWithRetry();
    updateSystemStatus();
    
    // Clear any previous errors
    lastWifiError = "";
    wifiErrorCount = 0;
}

// ================================
// FAILURE HANDLER
// ================================
void handleFailedWiFiConnectionEnhanced() {
    wifiConnected = false;
    wifiConnectionState = 0; // disconnected
    wifiRetryCount++;
    
    // Calculate exponential backoff with jitter
    int baseDelay = WIFI_RECONNECT_INTERVAL_ENHANCED;
    int backoffMultiplier = min(wifiRetryCount, 6); // Cap at 6 for reasonable delays
    int backoffDelay = baseDelay * (1 << (backoffMultiplier - 1));
    int jitter = random(0, baseDelay); // Add random jitter
    int totalDelay = backoffDelay + jitter;
    
    DEBUG_PRINTF("\n❌ WiFi connection failed! Retry #%d in %d ms\n", wifiRetryCount, totalDelay);
    
    handleWiFiErrorEnhanced("CONNECTION_TIMEOUT");
    updateSystemStatus();
    
    // Schedule next retry
    lastWifiReconnectAttempt = millis() - WIFI_RECONNECT_INTERVAL_ENHANCED + totalDelay;
}

// ================================
// ENHANCED CONNECTION MONITORING
// ================================
void checkWiFiConnectionEnhanced() {
    unsigned long now = millis();
    
    // Skip if not time for health check yet
    if (now - lastWifiHealthCheck < WIFI_HEALTH_CHECK_INTERVAL_ENHANCED) {
        return;
    }
    lastWifiHealthCheck = now;
    
    wl_status_t currentStatus = WiFi.status();
    
    // Handle disconnection
    if (currentStatus != WL_CONNECTED) {
        handleWiFiDisconnectionEnhanced(currentStatus);
        return;
    }
    
    // WiFi is connected - monitor quality and stability
    handleConnectedWiFiMonitoringEnhanced(now);
}

// ================================
// DISCONNECTION HANDLER
// ================================
void handleWiFiDisconnectionEnhanced(wl_status_t status) {
    if (wifiConnected) {
        DEBUG_PRINTF("⚠️ WiFi connection lost! Status: %d\n", status);
        wifiConnected = false;
        wifiConnectionState = 0; // disconnected
        wifiStateStartTime = millis();
        
        // Force dependent services to reconnect
        timeInitialized = false;
        mqttConnected = false;
        
        updateSystemStatus();
        handleWiFiErrorEnhanced("CONNECTION_LOST");
    }

    // Attempt reconnection if enough time has passed
    unsigned long now = millis();
    if (now - lastWifiReconnectAttempt > WIFI_RECONNECT_INTERVAL_ENHANCED) {
        connectWiFiEnhanced();
    }
}

// ================================
// CONNECTED WIFI MONITORING
// ================================
void handleConnectedWiFiMonitoringEnhanced(unsigned long now) {
    // Mark as stable if connected long enough (60 seconds)
    if (wifiConnectionState == 2 && (now - wifiStateStartTime > 60000)) {
        wifiConnectionState = 3; // stable
        DEBUG_PRINTLN("🔒 WiFi connection is now stable");
    }
    
    // Monitor signal quality every 15 seconds
    if (now - lastWifiSignalCheck > 15000) {
        monitorSignalQualityEnhanced();
        lastWifiSignalCheck = now;
    }
    
    // Check if we're in degraded state and need proactive reconnection
    if (wifiConnectionState == 4) { // degraded
        handleDegradedConnectionEnhanced();
    }
    
    // Force reconnection if requested
    if (forceWifiReconnect) {
        DEBUG_PRINTLN("🔄 Forcing WiFi reconnection as requested");
        forceWifiReconnect = false;
        WiFi.disconnect();
        delay(100);
        connectWiFiEnhanced();
    }
}

// ================================
// SIGNAL QUALITY MONITORING
// ================================
void monitorSignalQualityEnhanced() {
    int currentRSSI = WiFi.RSSI();
    updateWiFiSignalSampleEnhanced(currentRSSI);
    
    // Check for signal degradation
    if (averageWifiSignal < -85) { // Poor signal threshold
        poorSignalCount++;
        DEBUG_PRINTF("⚠️ Poor signal detected: %d dBm (count: %d/3)\n", averageWifiSignal, poorSignalCount);
        
        if (poorSignalCount >= 3) {
            wifiConnectionState = 4; // degraded
            DEBUG_PRINTLN("📉 WiFi connection marked as degraded due to poor signal");
        }
    } else {
        // Signal is good, reset poor signal counter
        if (poorSignalCount > 0) {
            DEBUG_PRINTF("📶 Signal quality improved: %d dBm\n", averageWifiSignal);
            poorSignalCount = 0;
            if (wifiConnectionState == 4) {
                wifiConnectionState = 3; // back to stable
            }
        }
    }
    
    // Check for critical signal levels
    if (currentRSSI < -90) {
        DEBUG_PRINTF("🚨 Critical signal level: %d dBm - forcing reconnection\n", currentRSSI);
        forceWifiReconnect = true;
    }
}

// ================================
// SIGNAL QUALITY HELPERS
// ================================
void updateWiFiSignalSampleEnhanced(int rssi) {
    wifiSignalSamples[wifiSignalIndex] = rssi;
    wifiSignalIndex = (wifiSignalIndex + 1) % 5;
    
    // Calculate average
    int sum = 0;
    for (int i = 0; i < 5; i++) {
        sum += wifiSignalSamples[i];
    }
    averageWifiSignal = sum / 5;
}

const char* getSignalQualityTextEnhanced(int rssi) {
    if (rssi > -50) return "EXCELLENT";
    if (rssi > -60) return "VERY GOOD";
    if (rssi > -70) return "GOOD";
    if (rssi > -80) return "FAIR";
    if (rssi > -90) return "POOR";
    return "VERY POOR";
}

// ================================
// DEGRADED CONNECTION HANDLER
// ================================
void handleDegradedConnectionEnhanced() {
    static unsigned long lastDegradedCheck = 0;
    unsigned long now = millis();
    
    // Only check every 30 seconds when degraded
    if (now - lastDegradedCheck < 30000) {
        return;
    }
    lastDegradedCheck = now;
    
    DEBUG_PRINTF("🔧 Attempting to improve degraded connection (RSSI: %d dBm)\n", averageWifiSignal);
    
    // Try to reconnect proactively
    forceWifiReconnect = true;
}

// ================================
// ERROR HANDLING
// ================================
void handleWiFiErrorEnhanced(String errorType) {
    lastWifiError = errorType;
    wifiErrorCount++;
    
    DEBUG_PRINTF("❌ WiFi Error: %s (count: %d)\n", errorType.c_str(), wifiErrorCount);
    
    // Trigger recovery mode if too many errors
    if (wifiErrorCount >= 3) {
        initiateWiFiRecoveryEnhanced();
    }
}

// ================================
// RECOVERY MODE
// ================================
void initiateWiFiRecoveryEnhanced() {
    if (wifiRecoveryMode) {
        return; // Already in recovery
    }
    
    DEBUG_PRINTLN("🚨 Initiating WiFi recovery mode...");
    wifiRecoveryMode = true;
    consecutiveWifiFailures = 0;
    wifiErrorCount = 0;
    
    // Perform full WiFi stack reset
    WiFi.disconnect(true);
    delay(2000);
    WiFi.mode(WIFI_OFF);
    delay(2000);
    WiFi.mode(WIFI_STA);
    delay(1000);
    
    // Reset all counters and state
    wifiRetryCount = 0;
    wifiConnectionState = 0;
    poorSignalCount = 0;
    
    // Reinitialize WiFi configuration
    WiFi.setAutoReconnect(false);
    WiFi.setSleep(false);
    
    DEBUG_PRINTLN("✅ WiFi recovery completed, attempting reconnection...");
    
    // Attempt connection after recovery
    connectWiFiEnhanced();
}

// ================================
// DIAGNOSTIC FUNCTIONS
// ================================
void printWiFiDiagnosticsEnhanced() {
    DEBUG_PRINTLN("📊 === ENHANCED WIFI DIAGNOSTICS ===");
    DEBUG_PRINTF("Status: %s (State: %d)\n", 
               wifiConnected ? "CONNECTED" : "DISCONNECTED", wifiConnectionState);
    
    if (wifiConnected) {
        DEBUG_PRINTF("  SSID: %s\n", WiFi.SSID().c_str());
        DEBUG_PRINTF("  IP: %s\n", WiFi.localIP().toString().c_str());
        DEBUG_PRINTF("  Current RSSI: %d dBm\n", WiFi.RSSI());
        DEBUG_PRINTF("  Average RSSI: %d dBm (%s)\n", averageWifiSignal, getSignalQualityTextEnhanced(averageWifiSignal));
        DEBUG_PRINTF("  Connection uptime: %lu ms\n", millis() - wifiConnectedTime);
        
        const char* stateText = "UNKNOWN";
        switch (wifiConnectionState) {
            case 0: stateText = "DISCONNECTED"; break;
            case 1: stateText = "CONNECTING"; break;
            case 2: stateText = "CONNECTED"; break;
            case 3: stateText = "STABLE"; break;
            case 4: stateText = "DEGRADED"; break;
            case 5: stateText = "FAILED"; break;
        }
        DEBUG_PRINTF("  Stability: %s\n", stateText);
    }
    
    DEBUG_PRINTF("Statistics:\n");
    DEBUG_PRINTF("  Retry count: %d/%d\n", wifiRetryCount, WIFI_MAX_RETRIES_ENHANCED);
    DEBUG_PRINTF("  Consecutive failures: %d\n", consecutiveWifiFailures);
    DEBUG_PRINTF("  Poor signal count: %d/3\n", poorSignalCount);
    DEBUG_PRINTF("  Error count: %d\n", wifiErrorCount);
    DEBUG_PRINTF("  Last error: %s\n", lastWifiError.c_str());
    DEBUG_PRINTF("  Recovery mode: %s\n", wifiRecoveryMode ? "ACTIVE" : "INACTIVE");
    DEBUG_PRINTLN("=============================");
}

// ================================
// MAIN LOOP INTEGRATION
// ================================
void updateWiFiConnectionEnhanced() {
    // Call this function in your main loop() instead of checkWiFiConnection()
    static unsigned long lastWiFiCheck = 0;
    if (millis() - lastWiFiCheck > WIFI_HEALTH_CHECK_INTERVAL_ENHANCED) {
        checkWiFiConnectionEnhanced();
        lastWiFiCheck = millis();
    }
    
    // Optional: Print diagnostics every 5 minutes
    static unsigned long lastDiagnostics = 0;
    if (millis() - lastDiagnostics > 300000) { // 5 minutes
        printWiFiDiagnosticsEnhanced();
        lastDiagnostics = millis();
    }
}

/*
 * ================================
 * INTEGRATION INSTRUCTIONS
 * ================================
 * 
 * TO APPLY THESE ENHANCED WIFI FUNCTIONS TO YOUR FACULTY_DESK_UNIT.INO:
 * 
 * 1. Add the enhanced variables (shown in comments above) to the top of your main sketch
 * 
 * 2. Replace your existing setupWiFi() call in setup() with:
 *    setupWiFiEnhanced();
 * 
 * 3. Replace your existing checkWiFiConnection() call in loop() with:
 *    updateWiFiConnectionEnhanced();
 * 
 * 4. Optional: Add this line to your setup() for validation:
 *    DEBUG_PRINTLN("✅ Enhanced WiFi management enabled");
 * 
 * 5. Monitor the serial output for enhanced WiFi diagnostics and debugging
 * 
 * BENEFITS OF THESE ENHANCEMENTS:
 * ✅ Exponential backoff with jitter prevents network congestion
 * ✅ Signal quality monitoring enables proactive reconnection
 * ✅ Recovery mode handles persistent connection failures
 * ✅ Enhanced error tracking and diagnostics
 * ✅ Stable/degraded state tracking for better reliability
 * ✅ Configurable timeouts and thresholds
 */ 