// ================================
// ENHANCED WIFI STABILITY FUNCTIONS
// ================================
// These functions replace the existing WiFi management in faculty_desk_unit.ino
// to address frequent disconnection issues.

// Include the improved configuration
// #include "config_wifi_improved.h"  // Add this at the top of your main sketch

// ===== ENHANCED WIFI MANAGEMENT VARIABLES =====
// Add these variables to the top of your main sketch (after includes, before setup)

// WiFi connection state tracking
int wifiState = WIFI_STATE_DISCONNECTED;
unsigned long wifiStateChangeTime = 0;
int wifiRetryCount = 0;
int consecutiveWifiFailures = 0;
bool forceWifiReconnect = false;

// Signal quality monitoring
int rssiSamples[WIFI_QUALITY_SAMPLE_SIZE];
int rssiSampleIndex = 0;
int consecutivePoorSignal = 0;
int averageRSSI = -100;

// Connection timing
unsigned long lastWifiReconnectAttempt = 0;
unsigned long lastWifiHealthCheck = 0;
unsigned long lastSignalQualityCheck = 0;
unsigned long wifiConnectedTime = 0;

// Enhanced error tracking
String lastWifiError = "";
int wifiErrorCount = 0;
bool wifiRecoveryMode = false;

// ================================
// ENHANCED WIFI SETUP FUNCTION
// ================================
void setupWiFiEnhanced() {
    WIFI_DEBUG("🔧 Enhanced WiFi setup starting...");
    WIFI_DEBUGF("   Target SSID: %s\n", WIFI_SSID);
    WIFI_DEBUGF("   Signal threshold: %d dBm\n", MIN_WIFI_SIGNAL_STRENGTH);
    
    // Initialize WiFi state tracking
    wifiState = WIFI_STATE_DISCONNECTED;
    wifiRetryCount = 0;
    consecutiveWifiFailures = 0;
    forceWifiReconnect = false;
    
    // Initialize signal quality tracking
    for (int i = 0; i < WIFI_QUALITY_SAMPLE_SIZE; i++) {
        rssiSamples[i] = -100;
    }
    rssiSampleIndex = 0;
    consecutivePoorSignal = 0;
    
    // Configure WiFi for maximum stability
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(false); // Manual control for better reliability
    WiFi.setSleep(WIFI_POWER_SAVE_MODE);
    
    // Set advanced WiFi parameters for stability
    esp_wifi_set_bandwidth(WIFI_IF_STA, WIFI_BANDWIDTH);
    esp_wifi_set_protocol(WIFI_IF_STA, WIFI_PHY_MODE);
    
    WIFI_DEBUG("✅ WiFi configuration applied");
    
    // Start initial connection attempt
    connectWiFiEnhanced();
}

// ================================
// ENHANCED WIFI CONNECTION FUNCTION
// ================================
void connectWiFiEnhanced() {
    if (wifiRetryCount >= WIFI_MAX_RETRIES) {
        WIFI_DEBUGF("❌ WiFi connection failed after %d attempts\n", WIFI_MAX_RETRIES);
        wifiState = WIFI_STATE_FAILED;
        consecutiveWifiFailures++;
        
        // Trigger recovery mode if too many consecutive failures
        if (consecutiveWifiFailures >= WIFI_CONSECUTIVE_FAILURES_LIMIT) {
            initiateWiFiRecovery();
        }
        
        updateSystemStatus();
        return;
    }

    wifiState = WIFI_STATE_CONNECTING;
    wifiStateChangeTime = millis();
    
    WIFI_DEBUGF("📡 WiFi connection attempt %d/%d\n", wifiRetryCount + 1, WIFI_MAX_RETRIES);
    
    // Disconnect cleanly before reconnecting
    WiFi.disconnect(true);
    delay(1000); // Allow clean disconnect
    
    // Optional: Scan for the target network first
    if (WIFI_SCAN_ON_FAILURE && wifiRetryCount > 2) {
        scanForTargetNetwork();
    }
    
    // Start connection with enhanced error handling
    wl_status_t connectResult = WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    if (connectResult == WL_CONNECT_FAILED) {
        WIFI_DEBUG("❌ WiFi.begin() failed immediately");
        handleWiFiError("CONNECT_FAILED");
        return;
    }
    
    // Wait for connection with enhanced timeout
    unsigned long startTime = millis();
    unsigned long timeout = WIFI_CONNECT_TIMEOUT + (wifiRetryCount * 5000);
    
    while (WiFi.status() != WL_CONNECTED && (millis() - startTime) < timeout) {
        delay(500);
        WIFI_DEBUG(".");
        
        // Update display during connection attempt
        updateSystemStatus();
        
        // Check for specific failure conditions
        wl_status_t currentStatus = WiFi.status();
        if (currentStatus == WL_CONNECT_FAILED || currentStatus == WL_CONNECTION_LOST) {
            WIFI_DEBUGF("\n❌ WiFi connection failed with status: %d\n", currentStatus);
            handleWiFiError("CONNECTION_FAILED");
            return;
        }
        
        // Allow other tasks to run
        yield();
    }

    // Check final connection status
    if (WiFi.status() == WL_CONNECTED) {
        handleSuccessfulWiFiConnection();
    } else {
        handleFailedWiFiConnection();
    }
}

// ================================
// SUCCESS HANDLER
// ================================
void handleSuccessfulWiFiConnection() {
    wifiConnected = true;
    wifiState = WIFI_STATE_CONNECTED;
    wifiStateChangeTime = millis();
    wifiConnectedTime = millis();
    wifiRetryCount = 0;
    consecutiveWifiFailures = 0;
    wifiRecoveryMode = false;
    
    // Get initial signal quality
    int initialRSSI = WiFi.RSSI();
    updateSignalQualitySample(initialRSSI);
    
    WIFI_DEBUGF("\n✅ WiFi connected successfully!\n");
    WIFI_DEBUGF("   IP Address: %s\n", WiFi.localIP().toString().c_str());
    WIFI_DEBUGF("   Signal Strength: %d dBm (%s)\n", initialRSSI, getSignalQualityText(initialRSSI));
    WIFI_DEBUGF("   Gateway: %s\n", WiFi.gatewayIP().toString().c_str());
    WIFI_DEBUGF("   DNS: %s\n", WiFi.dnsIP().toString().c_str());
    
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
void handleFailedWiFiConnection() {
    wifiConnected = false;
    wifiState = WIFI_STATE_DISCONNECTED;
    wifiRetryCount++;
    
    // Calculate exponential backoff with jitter
    int baseDelay = WIFI_RECONNECT_INTERVAL;
    int backoffMultiplier = min(wifiRetryCount, 6); // Cap at 6 for reasonable delays
    int backoffDelay = baseDelay * (1 << (backoffMultiplier - 1));
    int jitter = random(0, baseDelay); // Add random jitter
    int totalDelay = backoffDelay + jitter;
    
    WIFI_DEBUGF("\n❌ WiFi connection failed! Retry #%d in %d ms\n", wifiRetryCount, totalDelay);
    lastWifiReconnectAttempt = millis();
    
    handleWiFiError("CONNECTION_TIMEOUT");
    updateSystemStatus();
    
    // Schedule next retry
    lastWifiReconnectAttempt = millis() - WIFI_RECONNECT_INTERVAL + totalDelay;
}

// ================================
// ENHANCED CONNECTION MONITORING
// ================================
void checkWiFiConnectionEnhanced() {
    unsigned long now = millis();
    
    // Skip if not time for health check yet
    if (now - lastWifiHealthCheck < WIFI_HEALTH_CHECK_INTERVAL) {
        return;
    }
    lastWifiHealthCheck = now;
    
    wl_status_t currentStatus = WiFi.status();
    
    // Handle disconnection
    if (currentStatus != WL_CONNECTED) {
        handleWiFiDisconnection(currentStatus);
        return;
    }
    
    // WiFi is connected - monitor quality and stability
    handleConnectedWiFiMonitoring(now);
}

// ================================
// DISCONNECTION HANDLER
// ================================
void handleWiFiDisconnection(wl_status_t status) {
    if (wifiConnected) {
        WIFI_DEBUGF("⚠️ WiFi connection lost! Status: %d (%s)\n", status, getWiFiStatusText(status));
        wifiConnected = false;
        wifiState = WIFI_STATE_DISCONNECTED;
        wifiStateChangeTime = millis();
        
        // Force dependent services to reconnect
        timeInitialized = false;
        mqttConnected = false;
        
        updateSystemStatus();
        handleWiFiError("CONNECTION_LOST");
    }

    // Attempt reconnection if enough time has passed
    unsigned long now = millis();
    if (now - lastWifiReconnectAttempt > WIFI_RECONNECT_INTERVAL) {
        connectWiFiEnhanced();
    }
}

// ================================
// CONNECTED WIFI MONITORING
// ================================
void handleConnectedWiFiMonitoring(unsigned long now) {
    // Mark as stable if connected long enough
    if (wifiState == WIFI_STATE_CONNECTED && 
        (now - wifiStateChangeTime > WIFI_STABILITY_PERIOD)) {
        wifiState = WIFI_STATE_STABLE;
        WIFI_DEBUG("🔒 WiFi connection is now stable");
    }
    
    // Monitor signal quality
    if (now - lastSignalQualityCheck > WIFI_SIGNAL_CHECK_INTERVAL) {
        monitorSignalQuality();
        lastSignalQualityCheck = now;
    }
    
    // Check if we're in degraded state and need proactive reconnection
    if (wifiState == WIFI_STATE_DEGRADED) {
        handleDegradedConnection();
    }
    
    // Force reconnection if requested
    if (forceWifiReconnect) {
        WIFI_DEBUG("🔄 Forcing WiFi reconnection as requested");
        forceWifiReconnect = false;
        WiFi.disconnect();
        delay(100);
        connectWiFiEnhanced();
    }
}

// ================================
// SIGNAL QUALITY MONITORING
// ================================
void monitorSignalQuality() {
    int currentRSSI = WiFi.RSSI();
    updateSignalQualitySample(currentRSSI);
    
    // Check for signal degradation
    if (averageRSSI < POOR_SIGNAL_THRESHOLD) {
        consecutivePoorSignal++;
        WIFI_DEBUGF("⚠️ Poor signal detected: %d dBm (count: %d/%d)\n", 
                   averageRSSI, consecutivePoorSignal, SIGNAL_DEGRADATION_TOLERANCE);
        
        if (consecutivePoorSignal >= SIGNAL_DEGRADATION_TOLERANCE) {
            wifiState = WIFI_STATE_DEGRADED;
            WIFI_DEBUG("📉 WiFi connection marked as degraded due to poor signal");
        }
    } else {
        // Signal is good, reset poor signal counter
        if (consecutivePoorSignal > 0) {
            WIFI_DEBUGF("📶 Signal quality improved: %d dBm\n", averageRSSI);
            consecutivePoorSignal = 0;
            if (wifiState == WIFI_STATE_DEGRADED) {
                wifiState = WIFI_STATE_STABLE;
            }
        }
    }
    
    // Check for critical signal levels
    if (currentRSSI < CRITICAL_SIGNAL_THRESHOLD) {
        WIFI_DEBUGF("🚨 Critical signal level: %d dBm - forcing reconnection\n", currentRSSI);
        forceWifiReconnect = true;
    }
}

// ================================
// SIGNAL QUALITY HELPERS
// ================================
void updateSignalQualitySample(int rssi) {
    rssiSamples[rssiSampleIndex] = rssi;
    rssiSampleIndex = (rssiSampleIndex + 1) % WIFI_QUALITY_SAMPLE_SIZE;
    
    // Calculate average
    int sum = 0;
    for (int i = 0; i < WIFI_QUALITY_SAMPLE_SIZE; i++) {
        sum += rssiSamples[i];
    }
    averageRSSI = sum / WIFI_QUALITY_SAMPLE_SIZE;
}

const char* getSignalQualityText(int rssi) {
    if (rssi > -50) return "EXCELLENT";
    if (rssi > -60) return "VERY GOOD";
    if (rssi > -70) return "GOOD";
    if (rssi > -80) return "FAIR";
    if (rssi > -90) return "POOR";
    return "VERY POOR";
}

const char* getWiFiStatusText(wl_status_t status) {
    switch (status) {
        case WL_IDLE_STATUS: return "IDLE";
        case WL_NO_SSID_AVAIL: return "SSID_NOT_FOUND";
        case WL_SCAN_COMPLETED: return "SCAN_COMPLETED";
        case WL_CONNECTED: return "CONNECTED";
        case WL_CONNECT_FAILED: return "CONNECT_FAILED";
        case WL_CONNECTION_LOST: return "CONNECTION_LOST";
        case WL_DISCONNECTED: return "DISCONNECTED";
        default: return "UNKNOWN";
    }
}

// ================================
// DEGRADED CONNECTION HANDLER
// ================================
void handleDegradedConnection() {
    static unsigned long lastDegradedCheck = 0;
    unsigned long now = millis();
    
    // Only check every 30 seconds when degraded
    if (now - lastDegradedCheck < 30000) {
        return;
    }
    lastDegradedCheck = now;
    
    WIFI_DEBUGF("🔧 Attempting to improve degraded connection (RSSI: %d dBm)\n", averageRSSI);
    
    // Try to reconnect proactively
    forceWifiReconnect = true;
}

// ================================
// NETWORK SCANNING
// ================================
void scanForTargetNetwork() {
    WIFI_DEBUG("🔍 Scanning for available networks...");
    
    WiFi.scanDelete(); // Clear previous results
    int networkCount = WiFi.scanNetworks(false, false, false, 300);
    
    if (networkCount == 0) {
        WIFI_DEBUG("   No networks found");
        return;
    }
    
    WIFI_DEBUGF("   Found %d networks:\n", networkCount);
    bool targetFound = false;
    int targetRSSI = -100;
    
    for (int i = 0; i < networkCount; i++) {
        String ssid = WiFi.SSID(i);
        int rssi = WiFi.RSSI(i);
        
        if (ssid == WIFI_SSID) {
            targetFound = true;
            targetRSSI = rssi;
            WIFI_DEBUGF("   ✅ Target network found: %s (%d dBm)\n", ssid.c_str(), rssi);
        } else {
            WIFI_DEBUGF("   📡 %s (%d dBm)\n", ssid.c_str(), rssi);
        }
    }
    
    if (!targetFound) {
        WIFI_DEBUGF("   ❌ Target network '%s' not found\n", WIFI_SSID);
        handleWiFiError("SSID_NOT_FOUND");
    } else if (targetRSSI < CRITICAL_SIGNAL_THRESHOLD) {
        WIFI_DEBUGF("   ⚠️ Target network signal too weak: %d dBm\n", targetRSSI);
        handleWiFiError("SIGNAL_TOO_WEAK");
    }
    
    WiFi.scanDelete(); // Clean up
}

// ================================
// ERROR HANDLING
// ================================
void handleWiFiError(String errorType) {
    lastWifiError = errorType;
    wifiErrorCount++;
    
    WIFI_DEBUGF("❌ WiFi Error: %s (count: %d)\n", errorType.c_str(), wifiErrorCount);
    
    // Trigger recovery mode if too many errors
    if (wifiErrorCount >= WIFI_CONSECUTIVE_FAILURES_LIMIT) {
        initiateWiFiRecovery();
    }
}

// ================================
// RECOVERY MODE
// ================================
void initiateWiFiRecovery() {
    if (wifiRecoveryMode) {
        return; // Already in recovery
    }
    
    WIFI_DEBUG("🚨 Initiating WiFi recovery mode...");
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
    wifiState = WIFI_STATE_DISCONNECTED;
    consecutivePoorSignal = 0;
    
    // Reinitialize WiFi configuration
    WiFi.setAutoReconnect(false);
    WiFi.setSleep(WIFI_POWER_SAVE_MODE);
    
    WIFI_DEBUG("✅ WiFi recovery completed, attempting reconnection...");
    
    // Attempt connection after recovery
    connectWiFiEnhanced();
}

// ================================
// DIAGNOSTIC FUNCTIONS
// ================================
void printWiFiDiagnostics() {
    WIFI_DEBUG("📊 === ENHANCED WIFI DIAGNOSTICS ===");
    WIFI_DEBUGF("Status: %s (State: %d)\n", 
               wifiConnected ? "CONNECTED" : "DISCONNECTED", wifiState);
    
    if (wifiConnected) {
        WIFI_DEBUGF("  SSID: %s\n", WiFi.SSID().c_str());
        WIFI_DEBUGF("  IP: %s\n", WiFi.localIP().toString().c_str());
        WIFI_DEBUGF("  Gateway: %s\n", WiFi.gatewayIP().toString().c_str());
        WIFI_DEBUGF("  Current RSSI: %d dBm\n", WiFi.RSSI());
        WIFI_DEBUGF("  Average RSSI: %d dBm (%s)\n", averageRSSI, getSignalQualityText(averageRSSI));
        WIFI_DEBUGF("  Connection uptime: %lu ms\n", millis() - wifiConnectedTime);
        WIFI_DEBUGF("  Stability: %s\n", wifiState == WIFI_STATE_STABLE ? "STABLE" : 
                                        wifiState == WIFI_STATE_DEGRADED ? "DEGRADED" : "UNSTABLE");
    }
    
    WIFI_DEBUGF("Statistics:\n");
    WIFI_DEBUGF("  Retry count: %d/%d\n", wifiRetryCount, WIFI_MAX_RETRIES);
    WIFI_DEBUGF("  Consecutive failures: %d\n", consecutiveWifiFailures);
    WIFI_DEBUGF("  Poor signal count: %d/%d\n", consecutivePoorSignal, SIGNAL_DEGRADATION_TOLERANCE);
    WIFI_DEBUGF("  Error count: %d\n", wifiErrorCount);
    WIFI_DEBUGF("  Last error: %s\n", lastWifiError.c_str());
    WIFI_DEBUGF("  Recovery mode: %s\n", wifiRecoveryMode ? "ACTIVE" : "INACTIVE");
    WIFI_DEBUG("=============================");
}

// ================================
// USAGE INSTRUCTIONS
// ================================
/*
 * TO APPLY THESE ENHANCED WIFI FUNCTIONS:
 * 
 * 1. Add #include "config_wifi_improved.h" at the top of your main sketch
 * 
 * 2. Replace existing functions in your main sketch:
 *    setupWiFi() → setupWiFiEnhanced()
 *    checkWiFiConnection() → checkWiFiConnectionEnhanced()
 * 
 * 3. Add the enhanced variables at the top of your sketch (after includes)
 * 
 * 4. In your main loop, replace WiFi checking with:
 *    static unsigned long lastWiFiCheck = 0;
 *    if (millis() - lastWiFiCheck > WIFI_HEALTH_CHECK_INTERVAL) {
 *        checkWiFiConnectionEnhanced();
 *        lastWiFiCheck = millis();
 *    }
 * 
 * 5. Optional: Add diagnostics reporting:
 *    static unsigned long lastDiagnostics = 0;
 *    if (millis() - lastDiagnostics > DIAGNOSTIC_REPORT_INTERVAL) {
 *        printWiFiDiagnostics();
 *        lastDiagnostics = millis();
 *    }
 */ 