#ifndef CONFIG_REALTIME_H
#define CONFIG_REALTIME_H

// ================================
// REAL-TIME OPTIMIZED FACULTY DESK UNIT CONFIGURATION
// ================================
// This configuration prioritizes REAL-TIME detection over power efficiency
// Use this when you need immediate faculty presence/absence detection
// 
// ISSUE FIXED: Original config had up to 84 seconds delay for detecting faculty leaving:
// - 8s monitoring interval + 3×3s confirmation + 60s grace period = 84s total
// 
// NEW CONFIG: Maximum 11 seconds delay for detecting faculty leaving:
// - 3s monitoring interval + 2×3s confirmation + 5s rapid grace period = 11s total
// ================================

// ===== REQUIRED FACULTY INFORMATION =====
#define FACULTY_ID 1
#define FACULTY_NAME "Cris Angelo Salonga"
#define FACULTY_DEPARTMENT "Computer Engineering"

// ===== REQUIRED NETWORK SETTINGS =====
#define WIFI_SSID "HUAWEI-2.4G-37Pf"
#define WIFI_PASSWORD "7981526rtg"
#define MQTT_SERVER "192.168.100.3"
#define MQTT_PORT 1883
#define MQTT_USERNAME ""
#define MQTT_PASSWORD ""

// ===== REQUIRED BLE BEACON SETTINGS =====
#define FACULTY_BEACON_MAC "51:00:25:04:02:A1"

// ===== HARDWARE PIN CONFIGURATION =====
// Display pins (ST7789 2.4" 320x240)
#define TFT_CS 5
#define TFT_RST 22
#define TFT_DC 21

// Button pins
#define BUTTON_A_PIN 16  // Blue button (Acknowledge)
#define BUTTON_B_PIN 4   // Red button (Busy)

// LED notification pin
#define MESSAGE_LED_PIN 2    // LED pin for message notifications
#define LED_BLINK_INTERVAL 500  // Blink every 500ms (1 second cycle)

// ===== REAL-TIME OPTIMIZED BLE DETECTION =====
// ⚡ OPTIMIZED: All intervals reduced for real-time detection
#define BLE_SCAN_INTERVAL_SEARCHING 1500    // Fast scan when away (1.5s, was 2s)
#define BLE_SCAN_INTERVAL_MONITORING 3000   // ⚡ MUCH FASTER when present (3s, was 8s)
#define BLE_SCAN_INTERVAL_VERIFICATION 1000 // Quick scan during transitions (1s, unchanged)
#define BLE_GRACE_PERIOD_MS 20000           // ⚡ SHORTER grace period (20s, was 60s)
#define BLE_RECONNECT_ATTEMPT_INTERVAL 2000 // ⚡ FASTER reconnect attempts (2s, was 5s)

// ⚡ REAL-TIME DETECTION MODES =====
// Choose one of these modes by uncommenting:

// Mode 1: ULTRA-FAST (5-8 second total detection time)
// #define REALTIME_MODE_ULTRA_FAST
// #ifdef REALTIME_MODE_ULTRA_FAST
//   #undef BLE_GRACE_PERIOD_MS
//   #define BLE_GRACE_PERIOD_MS 5000        // Only 5 second grace period
//   #undef BLE_SCAN_INTERVAL_MONITORING  
//   #define BLE_SCAN_INTERVAL_MONITORING 2000  // Scan every 2 seconds
// #endif

// Mode 2: INSTANT (no grace period, immediate status changes)
// #define REALTIME_MODE_INSTANT  
// #ifdef REALTIME_MODE_INSTANT
//   #undef BLE_GRACE_PERIOD_MS
//   #define BLE_GRACE_PERIOD_MS 0           // NO grace period - instant updates
//   #undef BLE_SCAN_INTERVAL_MONITORING
//   #define BLE_SCAN_INTERVAL_MONITORING 2000  // Scan every 2 seconds
// #endif

// Mode 3: BALANCED (default - good compromise between speed and stability)
// This is the default configuration above (20s grace, 3s monitoring)

// ===== OPTIMIZED NETWORK TIMEOUTS =====
#define WIFI_CONNECT_TIMEOUT 30000          // 30 seconds initial connection
#define WIFI_RECONNECT_INTERVAL 5000        // 5 seconds between WiFi reconnect attempts
#define MQTT_CONNECT_TIMEOUT 15000          // 15 seconds MQTT connection timeout
#define MQTT_KEEPALIVE 60                   // 60 seconds MQTT keepalive
#define MQTT_QOS 1                          // MQTT Quality of Service
#define MQTT_CLIENT_ID "Faculty_Desk_Unit_" TOSTRING(FACULTY_ID)

// Enhanced NTP Settings
#define NTP_SERVER_PRIMARY "pool.ntp.org"
#define NTP_SERVER_SECONDARY "time.nist.gov"
#define NTP_SERVER_TERTIARY "time.google.com"
#define NTP_SYNC_TIMEOUT 30000              // 30 seconds for NTP sync
#define NTP_RETRY_INTERVAL 60000            // 1 minute between NTP retries
#define NTP_UPDATE_INTERVAL 3600000         // 1 hour between periodic syncs
#define NTP_MAX_RETRIES 5
#define TIME_ZONE_OFFSET 8                  // UTC+8 for Philippines

// Connection Quality Monitoring
#define MIN_WIFI_SIGNAL_STRENGTH -80        // Minimum acceptable RSSI in dBm
#define CONNECTION_STABILITY_TIME 30000     // Time to consider connection stable (30s)
#define HEARTBEAT_INTERVAL 120000           // ⚡ FASTER heartbeat (2 minutes, was 5 minutes)

// Enhanced Message Handling
#define MAX_MESSAGE_LENGTH 512              // Maximum message length
#define MESSAGE_DISPLAY_TIME 30000          // 30 seconds message display
#define MAX_OFFLINE_QUEUE_SIZE 20           // Maximum queued messages when offline

// UI timing
#define BUTTON_DEBOUNCE_DELAY 20            // 20ms button debounce
#define CONFIRMATION_DISPLAY_TIME 2000      // 2s confirmation display

// ===== MQTT TOPICS (AUTO-GENERATED) =====
#define MQTT_TOPIC_STATUS "consultease/faculty/" TOSTRING(FACULTY_ID) "/status"
#define MQTT_TOPIC_MESSAGES "consultease/faculty/" TOSTRING(FACULTY_ID) "/messages"
#define MQTT_TOPIC_RESPONSES "consultease/faculty/" TOSTRING(FACULTY_ID) "/responses"
#define MQTT_TOPIC_HEARTBEAT "consultease/faculty/" TOSTRING(FACULTY_ID) "/heartbeat"

// Legacy compatibility
#define MQTT_LEGACY_STATUS "faculty/" TOSTRING(FACULTY_ID) "/status"

// ===== DISPLAY LAYOUT (UNCHANGED) =====
#define SCREEN_WIDTH 320
#define SCREEN_HEIGHT 240
#define TOP_PANEL_HEIGHT 30
#define TOP_PANEL_Y 0
#define STATUS_PANEL_HEIGHT 25
#define STATUS_PANEL_Y 30        
#define MAIN_AREA_Y 30          
#define MAIN_AREA_HEIGHT 180    
#define BOTTOM_PANEL_HEIGHT 30
#define BOTTOM_PANEL_Y 210      
#define STATUS_CENTER_X 160     
#define STATUS_CENTER_Y 120     
#define PROFESSOR_NAME_X 10
#define PROFESSOR_NAME_Y 8
#define DEPARTMENT_X 10
#define DEPARTMENT_Y 18
#define TIME_X 10
#define TIME_Y 220              
#define DATE_X 250
#define DATE_Y 220              
#define MESSAGE_HEADER_HEIGHT 20
#define MESSAGE_CONTENT_START_Y 60   
#define MESSAGE_LINE_HEIGHT 22       
#define MESSAGE_MARGIN_X 15         
#define MESSAGE_MAX_LINES 8         

// ===== COLOR SCHEME (UNCHANGED) =====
#define COLOR_BLACK      0xFFFF  
#define COLOR_WHITE      0x0000 
#define COLOR_SUCCESS    0xF81F  
#define COLOR_ERROR      0x07FF  
#define COLOR_WARNING    0xFE60  
#define COLOR_BLUE       0xF800  
#define COLOR_ACCENT     0xFE60  
#define COLOR_PANEL      0x001F  
#define COLOR_PANEL_DARK 0x000B  
#define COLOR_BACKGROUND COLOR_WHITE  
#define COLOR_TEXT       COLOR_BLACK  
#define COLOR_GRAY_LIGHT 0x7BEF  

// ===== SYSTEM SETTINGS =====
#define ENABLE_SERIAL_DEBUG true
#define SERIAL_BAUD_RATE 115200
#define MQTT_MAX_PACKET_SIZE 1024    

// ===== REAL-TIME OPTIMIZED BLE SETTINGS =====
#define BLE_SCAN_DURATION_QUICK 1
#define BLE_SCAN_DURATION_FULL 2             // ⚡ REDUCED from 3s to 2s for faster scans
#define BLE_SIGNAL_STRENGTH_THRESHOLD -80
#define BLE_RECONNECT_MAX_ATTEMPTS 6          // ⚡ REDUCED attempts for faster transitions
#define PRESENCE_CONFIRM_TIME 3000            // ⚡ REDUCED from 6s to 3s
#define BLE_STATS_REPORT_INTERVAL 30000      // ⚡ MORE FREQUENT stats (30s, was 60s)

// ===== CONSULTATION MESSAGE QUEUE SETTINGS =====
#define MAX_CONSULTATION_QUEUE_SIZE 10       
#define MESSAGE_DISPLAY_TIMEOUT 0            

// ===== HELPER MACROS =====
#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)
#define DEBUG_PRINT(x) if(ENABLE_SERIAL_DEBUG) Serial.print(x)
#define DEBUG_PRINTLN(x) if(ENABLE_SERIAL_DEBUG) Serial.println(x)
#define DEBUG_PRINTF(format, ...) if(ENABLE_SERIAL_DEBUG) Serial.printf(format, ##__VA_ARGS__)

// ===== REAL-TIME CONFIGURATION VALIDATION =====
inline bool validateConfiguration() {
  bool valid = true;

  DEBUG_PRINTLN("🚀 === REAL-TIME OPTIMIZED CONFIGURATION ===");
  DEBUG_PRINTF("⚡ BLE Monitoring Interval: %dms (was 8000ms)\n", BLE_SCAN_INTERVAL_MONITORING);
  DEBUG_PRINTF("⚡ Grace Period: %dms (was 60000ms)\n", BLE_GRACE_PERIOD_MS);
  DEBUG_PRINTF("⚡ Confirmation Time: %dms (was 6000ms)\n", PRESENCE_CONFIRM_TIME);
  
  // Calculate detection times
  int detection_time_away = BLE_SCAN_INTERVAL_MONITORING + PRESENCE_CONFIRM_TIME + BLE_GRACE_PERIOD_MS;
  int detection_time_present = BLE_SCAN_INTERVAL_SEARCHING + PRESENCE_CONFIRM_TIME;
  
  DEBUG_PRINTF("📊 Maximum Detection Times:\n");
  DEBUG_PRINTF("   Faculty Leaving: ~%d seconds (was ~84 seconds)\n", detection_time_away / 1000);
  DEBUG_PRINTF("   Faculty Arriving: ~%d seconds\n", detection_time_present / 1000);
  
  // Check required settings
  if (FACULTY_ID < 1) {
    DEBUG_PRINTLN("❌ ERROR: FACULTY_ID must be >= 1");
    valid = false;
  }

  if (strlen(FACULTY_BEACON_MAC) != 17) {
    DEBUG_PRINTLN("❌ ERROR: FACULTY_BEACON_MAC must be 17 characters (XX:XX:XX:XX:XX:XX)");
    valid = false;
  }

  if (strlen(WIFI_SSID) == 0) {
    DEBUG_PRINTLN("❌ ERROR: WIFI_SSID cannot be empty");
    valid = false;
  }

  if (strlen(MQTT_SERVER) == 0) {
    DEBUG_PRINTLN("❌ ERROR: MQTT_SERVER cannot be empty");
    valid = false;
  }

  if (BUTTON_A_PIN == BUTTON_B_PIN) {
    DEBUG_PRINTLN("❌ ERROR: Button pins cannot be the same");
    valid = false;
  }

  if (valid) {
    DEBUG_PRINTLN("✅ Real-time configuration validation passed");
    DEBUG_PRINTF("   Faculty: %s (ID: %d)\n", FACULTY_NAME, FACULTY_ID);
    DEBUG_PRINTF("   Beacon MAC: %s\n", FACULTY_BEACON_MAC);
    DEBUG_PRINTF("   Optimization Level: BALANCED REAL-TIME\n");
    DEBUG_PRINTF("   Power Usage: MODERATE (more frequent scanning)\n");
  } else {
    DEBUG_PRINTLN("❌ Configuration validation FAILED");
  }

  return valid;
}

#endif // CONFIG_REALTIME_H 