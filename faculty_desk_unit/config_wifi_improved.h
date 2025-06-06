#ifndef CONFIG_WIFI_IMPROVED_H
#define CONFIG_WIFI_IMPROVED_H

// ================================
// ENHANCED WIFI CONFIGURATION FOR FACULTY DESK UNIT
// ================================
// This configuration addresses frequent WiFi disconnections
// Apply these settings to your config.h file

// ===== FACULTY INFORMATION (KEEP YOUR EXISTING VALUES) =====
#ifndef FACULTY_ID
#define FACULTY_ID 1
#endif
#ifndef FACULTY_NAME
#define FACULTY_NAME "Cris Angelo Salonga"
#endif
#ifndef FACULTY_DEPARTMENT  
#define FACULTY_DEPARTMENT "Computer Engineering"
#endif

// ===== IMPROVED NETWORK SETTINGS =====
#ifndef WIFI_SSID
#define WIFI_SSID "HUAWEI-2.4G-37Pf"
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "7981526rtg"
#endif
#ifndef MQTT_SERVER
#define MQTT_SERVER "192.168.100.3"
#endif
#ifndef MQTT_PORT
#define MQTT_PORT 1883
#endif

// ===== ENHANCED WIFI TIMING SETTINGS =====
// Increased timeouts for better reliability
#define WIFI_CONNECT_TIMEOUT 45000              // Increased from 30s to 45s
#define WIFI_RECONNECT_INTERVAL 3000            // Reduced from 5s to 3s for faster recovery
#define WIFI_MAX_RETRIES 15                     // Increased retry attempts
#define WIFI_STABILITY_PERIOD 60000             // 60s to consider connection stable
#define WIFI_SIGNAL_CHECK_INTERVAL 15000        // Check signal every 15s instead of 30s

// Enhanced signal quality thresholds
#define MIN_WIFI_SIGNAL_STRENGTH -75            // Improved from -80 dBm
#define POOR_SIGNAL_THRESHOLD -85               // Trigger proactive reconnect
#define CRITICAL_SIGNAL_THRESHOLD -90           // Force immediate reconnect
#define SIGNAL_DEGRADATION_TOLERANCE 3          // Allow 3 poor readings before reconnect

// WiFi power management and radio settings
#define WIFI_POWER_SAVE_MODE WIFI_PS_NONE       // Disable power saving for stability
#define WIFI_PHY_MODE WIFI_PHY_MODE_11G         // Use 802.11g for better compatibility
#define WIFI_BANDWIDTH WIFI_BW_HT20             // Use 20MHz bandwidth for stability

// Enhanced connection monitoring
#define WIFI_HEALTH_CHECK_INTERVAL 5000         // Check WiFi health every 5s
#define WIFI_QUALITY_SAMPLE_SIZE 5              // Average RSSI over 5 samples
#define WIFI_CONSECUTIVE_FAILURES_LIMIT 3       // Force reset after 3 consecutive failures

// ===== ENHANCED MQTT SETTINGS =====
#define MQTT_CONNECT_TIMEOUT 25000              // Increased from 15s to 25s
#define MQTT_KEEPALIVE 120                      // Increased from 60s to 120s  
#define MQTT_SOCKET_TIMEOUT 20                  // Increased socket timeout
#define MQTT_RECONNECT_INTERVAL 2000            // Faster MQTT reconnection
#define MQTT_MAX_PACKET_SIZE 2048               // Increased buffer size
#define MQTT_QOS 1                              // Ensure message delivery
#define MQTT_RETAIN false                       // Don't retain status messages
#define MQTT_CLEAN_SESSION true                 // Start with clean session

// MQTT connection stability
#define MQTT_STABILITY_PERIOD 30000             // 30s to consider MQTT stable
#define MQTT_MAX_RETRIES 10                     // Increased MQTT retry attempts
#define MQTT_HEARTBEAT_INTERVAL 120000          // Send heartbeat every 2 minutes

// ===== NETWORK DIAGNOSTICS AND RECOVERY =====
#define ENABLE_NETWORK_DIAGNOSTICS true
#define DIAGNOSTIC_REPORT_INTERVAL 300000       // Report diagnostics every 5 minutes
#define NETWORK_RECOVERY_ENABLED true
#define FULL_NETWORK_RESET_THRESHOLD 5          // Full reset after 5 consecutive failures

// Advanced recovery settings
#define WIFI_SCAN_ON_FAILURE true               // Scan for networks on failure
#define WIFI_CHANNEL_HOPPING_ENABLED false      // Disable for stability
#define WIFI_PERSISTENT_RECONNECT true          // Keep trying to reconnect
#define WIFI_FACTORY_RESET_ON_PERSISTENT_FAIL false // Don't factory reset

// ===== BLE OPTIMIZATIONS FOR WIFI COEXISTENCE =====
// Reduce BLE scan frequency to minimize WiFi interference
#define BLE_SCAN_INTERVAL_SEARCHING 3000        // Increased from 1500ms
#define BLE_SCAN_INTERVAL_MONITORING 5000       // Increased from 3000ms  
#define BLE_SCAN_DURATION_QUICK 1               // Short scan duration
#define BLE_SCAN_DURATION_FULL 2                // Reduced full scan duration

// ===== NTP SETTINGS FOR WIFI RELIABILITY =====
#define NTP_SERVER_PRIMARY "time.google.com"    // More reliable server
#define NTP_SERVER_SECONDARY "pool.ntp.org"
#define NTP_SERVER_TERTIARY "time.nist.gov"
#define NTP_SYNC_TIMEOUT 20000                  // Reduced timeout
#define NTP_RETRY_INTERVAL 30000                // More frequent retries
#define NTP_MAX_RETRIES 3                       // Fewer retries to avoid blocking

// ===== SYSTEM PERFORMANCE OPTIMIZATIONS =====
#define MAIN_LOOP_DELAY 10                      // Increased from 5ms for stability
#define SLOW_OPERATIONS_INTERVAL 150           // Reduced from 200ms
#define STATUS_UPDATE_INTERVAL 20000           // Less frequent status updates
#define CONNECTION_CHECK_PRIORITY true          // Prioritize connection checks

// ===== HELPER MACROS FOR WIFI MANAGEMENT =====
#define WIFI_DEBUG_ENABLED true
#define WIFI_DEBUG(x) if(WIFI_DEBUG_ENABLED && ENABLE_SERIAL_DEBUG) Serial.println(x)
#define WIFI_DEBUGF(format, ...) if(WIFI_DEBUG_ENABLED && ENABLE_SERIAL_DEBUG) Serial.printf(format, ##__VA_ARGS__)

// Connection state tracking
#define WIFI_STATE_DISCONNECTED 0
#define WIFI_STATE_CONNECTING 1
#define WIFI_STATE_CONNECTED 2
#define WIFI_STATE_STABLE 3
#define WIFI_STATE_DEGRADED 4
#define WIFI_STATE_FAILED 5

// ===== VALIDATION FUNCTIONS =====
inline bool validateWiFiConfig() {
    bool valid = true;
    
    if (strlen(WIFI_SSID) == 0) {
        DEBUG_PRINTLN("❌ WiFi SSID cannot be empty");
        valid = false;
    }
    
    if (strlen(WIFI_PASSWORD) < 8) {
        DEBUG_PRINTLN("⚠️ WiFi password should be at least 8 characters");
    }
    
    if (WIFI_CONNECT_TIMEOUT < 30000) {
        DEBUG_PRINTLN("⚠️ WiFi timeout should be at least 30 seconds");
    }
    
    if (MIN_WIFI_SIGNAL_STRENGTH < -85) {
        DEBUG_PRINTLN("⚠️ Minimum WiFi signal strength should be better than -85 dBm");
    }
    
    if (valid) {
        DEBUG_PRINTLN("✅ Enhanced WiFi configuration validated");
        WIFI_DEBUGF("   SSID: %s\n", WIFI_SSID);
        WIFI_DEBUGF("   Connect Timeout: %d ms\n", WIFI_CONNECT_TIMEOUT);
        WIFI_DEBUGF("   Min Signal: %d dBm\n", MIN_WIFI_SIGNAL_STRENGTH);
        WIFI_DEBUGF("   Health Check: %d ms\n", WIFI_HEALTH_CHECK_INTERVAL);
    }
    
    return valid;
}

// ===== QUICK DEPLOYMENT MACRO =====
// Add this to your main sketch to enable all improvements:
#define ENABLE_ENHANCED_WIFI_MANAGEMENT true

#if ENABLE_ENHANCED_WIFI_MANAGEMENT
    // Include enhanced WiFi functions
    #define USE_ENHANCED_WIFI_SETUP
    #define USE_ENHANCED_WIFI_MONITORING  
    #define USE_ENHANCED_CONNECTION_RECOVERY
    #define USE_WIFI_QUALITY_MONITORING
#endif

// ===== COMPATIBILITY CHECKS =====
#ifndef FACULTY_BEACON_MAC
#warning "FACULTY_BEACON_MAC not defined - BLE features will not work"
#endif

#ifndef MQTT_CLIENT_ID
#define MQTT_CLIENT_ID "Faculty_Desk_Unit_" TOSTRING(FACULTY_ID)
#endif

// ===== USAGE INSTRUCTIONS =====
/*
 * TO APPLY THESE WIFI IMPROVEMENTS:
 * 
 * 1. Replace your existing config.h with this file, or
 * 2. Add #include "config_wifi_improved.h" at the top of your main sketch
 * 
 * 3. In your main sketch, replace:
 *    setupWiFi() → setupWiFiEnhanced()
 *    checkWiFiConnection() → checkWiFiConnectionEnhanced()
 * 
 * 4. Add this to your setup() function:
 *    if (!validateWiFiConfig()) {
 *        while(true) delay(5000); // Stop if config invalid
 *    }
 * 
 * 5. In your main loop, ensure WiFi checking happens frequently:
 *    static unsigned long lastWiFiCheck = 0;
 *    if (millis() - lastWiFiCheck > WIFI_HEALTH_CHECK_INTERVAL) {
 *        checkWiFiConnectionEnhanced();
 *        lastWiFiCheck = millis();
 *    }
 */

#endif // CONFIG_WIFI_IMPROVED_H 