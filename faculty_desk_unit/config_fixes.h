#ifndef CONFIG_FIXES_H
#define CONFIG_FIXES_H

/*
 * CONFIGURATION FIXES FOR FACULTY DESK UNIT CONNECTIVITY
 * 
 * These settings should replace or supplement the existing config.h
 * to improve WiFi and MQTT connection stability.
 * 
 * APPLY THESE CHANGES TO config.h:
 */

// ================================
// NETWORK TIMING FIXES
// ================================

// Original problematic settings:
// #define WIFI_CONNECT_TIMEOUT 30000
// #define MQTT_KEEPALIVE 60
// #define MQTT_MAX_PACKET_SIZE 1024

// IMPROVED SETTINGS:
#undef WIFI_CONNECT_TIMEOUT
#undef MQTT_KEEPALIVE  
#undef MQTT_MAX_PACKET_SIZE

// WiFi Connection Improvements
#define WIFI_CONNECT_TIMEOUT 45000              // Increased from 30s to 45s
#define WIFI_RECONNECT_INTERVAL 3000            // Reduced from 5s to 3s
#define WIFI_MAX_RETRIES 15                     // Increased from default
#define WIFI_SIGNAL_QUALITY_THRESHOLD -75       // Improved from -80 dBm

// MQTT Connection Improvements  
#define MQTT_KEEPALIVE 120                      // Increased from 60s to 120s
#define MQTT_MAX_PACKET_SIZE 2048               // Increased from 1024 to 2048
#define MQTT_SOCKET_TIMEOUT 30                  // Increased from 15s to 30s
#define MQTT_CONNECT_TIMEOUT 20000              // Increased from 15s to 20s
#define MQTT_RECONNECT_INTERVAL 2000            // Reduced from 5s to 2s
#define MQTT_QOS_IMPROVED 1                     // Ensure reliable delivery

// Connection Monitoring Improvements
#define CONNECTION_CHECK_FREQUENCY 2000         // Check every 2 seconds
#define HEARTBEAT_FREQUENCY 120000              // Send heartbeat every 2 minutes
#define STATUS_UPDATE_FREQUENCY 10000           // Update status every 10 seconds

// ================================
// POWER MANAGEMENT FIXES
// ================================

// Disable WiFi power saving for stability
#define WIFI_POWER_SAVE_DISABLED true
#define WIFI_TX_POWER_MAX true                  // Use maximum TX power

// ================================
// BUFFER AND QUEUE IMPROVEMENTS
// ================================

#define MESSAGE_QUEUE_SIZE_IMPROVED 15          // Increased from 10
#define MAX_MESSAGE_LENGTH_IMPROVED 768         // Increased from 512
#define OFFLINE_RETRY_LIMIT 5                   // Maximum retry attempts

// ================================
// TIMING OPTIMIZATIONS
// ================================

// Main loop timing improvements
#define MAIN_LOOP_DELAY 5                       // Keep responsive for buttons
#define NETWORK_CHECK_INTERVAL 2000             // Check connections every 2s
#define BLE_SCAN_INTERVAL_OPTIMIZED 10000       // Reduced BLE scanning frequency
#define STATUS_DISPLAY_UPDATE_INTERVAL 5000     // Update display every 5s

// Button response optimization
#define BUTTON_CHECK_FREQUENCY 10               // Check buttons every 10ms
#define BUTTON_DEBOUNCE_IMPROVED 50             // Increased debounce time

// ================================
// ERROR HANDLING IMPROVEMENTS
// ================================

#define MAX_CONSECUTIVE_FAILURES 5              // Maximum consecutive connection failures
#define CONNECTION_STABILITY_TIME 30000         // Time to consider connection stable
#define RECOVERY_DELAY_BASE 2000                // Base delay for exponential backoff
#define RECOVERY_DELAY_MAX 30000                // Maximum recovery delay

// ================================
// DIAGNOSTIC SETTINGS
// ================================

#define ENABLE_CONNECTION_DIAGNOSTICS true      // Enable detailed connection logging
#define DIAGNOSTIC_REPORT_INTERVAL 300000      // Report diagnostics every 5 minutes
#define SIGNAL_STRENGTH_LOGGING true           // Log WiFi signal strength changes

// ================================
// CONFIGURATION VALIDATION
// ================================

// Validate that required improvements are applied
#if WIFI_CONNECT_TIMEOUT < 40000
#warning "WiFi timeout should be at least 40 seconds for stability"
#endif

#if MQTT_KEEPALIVE < 90
#warning "MQTT keepalive should be at least 90 seconds for stability"
#endif

#if MQTT_MAX_PACKET_SIZE < 1500
#warning "MQTT packet size should be at least 1500 bytes for consultation messages"
#endif

// ================================
// INTEGRATION MACROS
// ================================

#define USE_IMPROVED_NETWORKING true

// Backward compatibility
#ifndef MQTT_CLIENT_ID
#define MQTT_CLIENT_ID "Faculty_Desk_Unit_" TOSTRING(FACULTY_ID)
#endif

// Enhanced debugging
#if ENABLE_CONNECTION_DIAGNOSTICS
#define CONNECTION_DEBUG(x) DEBUG_PRINTLN(x)
#define CONNECTION_DEBUGF(format, ...) DEBUG_PRINTF(format, ##__VA_ARGS__)
#else
#define CONNECTION_DEBUG(x)
#define CONNECTION_DEBUGF(format, ...)
#endif

// ================================
// RECOMMENDED IMPLEMENTATION
// ================================

/*
 * TO APPLY THESE FIXES:
 * 
 * 1. Include this file in your main sketch:
 *    #include "config_fixes.h"
 * 
 * 2. Include the network connection fixes:
 *    #include "network_connection_fixes.h"
 * 
 * 3. Replace the setupWiFi() and setupMQTT() calls with:
 *    setupNetworkingImproved();
 * 
 * 4. Replace checkWiFiConnection() and checkMQTTConnection() with:
 *    updateNetworkConnectionsImproved();
 * 
 * 5. In your main loop, call:
 *    updateNetworkConnectionsImproved();
 *    instead of the individual connection checks
 * 
 * 6. Optional: Add diagnostic reporting:
 *    static unsigned long lastDiagnostics = 0;
 *    if (millis() - lastDiagnostics > DIAGNOSTIC_REPORT_INTERVAL) {
 *        printNetworkDiagnostics();
 *        lastDiagnostics = millis();
 *    }
 */

#endif // CONFIG_FIXES_H 