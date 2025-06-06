#ifndef CONFIG_H
#define CONFIG_H

// ================================
// FACULTY DESK UNIT - SIMPLIFIED CONFIGURATION
// ================================
// Updated: June 2, 2025 - Improved UI layout with clean message display
// By: Jeysibn

// ===== REQUIRED FACULTY INFORMATION =====
#define FACULTY_ID 1
#define FACULTY_NAME "Cris Angelo Salonga"
#define FACULTY_DEPARTMENT "Computer Engineering"

// ===== REQUIRED NETWORK SETTINGS =====
#define WIFI_SSID "Rods"
#define WIFI_PASSWORD "asdfghjkl"
#define MQTT_SERVER "172.20.10.8"
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
#define BUTTON_A_PIN 14  // Blue button (Acknowledge)
#define BUTTON_B_PIN 27  // Red button (Busy)

// LED notification pin
#define MESSAGE_LED_PIN 2    // LED pin for message notifications
#define LED_BLINK_INTERVAL 500  // Blink every 500ms (1 second cycle)

// ===== SIMPLIFIED TIMING SETTINGS =====
// BLE Detection
#define BLE_SCAN_INTERVAL_SEARCHING 2000    // Fast scan when away (2s)
#define BLE_SCAN_INTERVAL_MONITORING 8000   // Slow scan when present (8s)
#define BLE_SCAN_INTERVAL_VERIFICATION 1000 // Quick scan during transitions
#define BLE_GRACE_PERIOD_MS 60000           // 1 minute grace period
#define BLE_RECONNECT_ATTEMPT_INTERVAL 5000 // Reconnect every 5s

// ===== CONNECTION RETRY SETTINGS =====
#define WIFI_MAX_RETRIES 5              // Maximum WiFi connection attempts
#define WIFI_RETRY_DELAY 3000           // Delay between WiFi retries (3 seconds)
#define MQTT_MAX_RETRIES 3              // Maximum MQTT connection attempts  
#define MQTT_RETRY_DELAY 2000           // Delay between MQTT retries (2 seconds)
#define CONNECTION_RETRY_INTERVAL 30000  // Retry failed connections every 30 seconds

// Network timeouts
#define WIFI_CONNECT_TIMEOUT 20000          // 20 seconds
#define WIFI_RECONNECT_INTERVAL 5000        // 5 seconds between WiFi reconnect attempts
#define MQTT_KEEPALIVE 60                   // 60 seconds
#define MQTT_QOS 1                          // MQTT Quality of Service
#define MQTT_CLIENT_ID "Faculty_Desk_Unit_" TOSTRING(FACULTY_ID) // MQTT client identifier

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

// ===== CANCEL FUNCTIONALITY SETTINGS =====
#define MQTT_TOPIC_CANCEL "consultease/faculty/" TOSTRING(FACULTY_ID) "/cancellations"
#define CANCEL_CONFIRMATION_DISPLAY_TIME 1500  // 1.5 seconds to show cancel confirmation

// ===== IMPROVED DISPLAY LAYOUT =====
// Screen dimensions
#define SCREEN_WIDTH 320
#define SCREEN_HEIGHT 240

// Main layout areas (fixed sizing issues)
#define TOP_PANEL_HEIGHT 30
#define TOP_PANEL_Y 0
#define STATUS_PANEL_HEIGHT 25
#define STATUS_PANEL_Y 30        // Right after top panel
#define MAIN_AREA_Y 30           // Starts right after top panel (status hidden after init)
#define MAIN_AREA_HEIGHT 180     // Increased height since status bar is hidden
#define BOTTOM_PANEL_HEIGHT 30
#define BOTTOM_PANEL_Y 210       // Bottom of screen

// Status indicators (centered in main area)
#define STATUS_CENTER_X 160      // Center of 320px width
#define STATUS_CENTER_Y 120      // Center of expanded main area

// Text positions (corrected offsets)
#define PROFESSOR_NAME_X 10
#define PROFESSOR_NAME_Y 8
#define DEPARTMENT_X 10
#define DEPARTMENT_Y 18

// Time and date in bottom panel
#define TIME_X 10
#define TIME_Y 220               // Bottom panel
#define DATE_X 250
#define DATE_Y 220               // Bottom panel

// Message display layout (new clean layout)
#define MESSAGE_HEADER_HEIGHT 20
#define MESSAGE_CONTENT_START_Y 60    // After header + some padding
#define MESSAGE_LINE_HEIGHT 22        // Better spacing for size 2 text
#define MESSAGE_MARGIN_X 15          // Left margin for all message content
#define MESSAGE_MAX_LINES 8          // Maximum lines for message content

// ===== COLOR SCHEME (CORRECTED FOR ST7789) =====
// ST7789 uses RGB565 format - corrected color values
#define COLOR_BLACK      0xFFFF  // Black
#define COLOR_WHITE      0x0000 // White
#define COLOR_SUCCESS    0xF81F  // Green
#define COLOR_ERROR      0x07FF  // Red
#define COLOR_WARNING    0xFE60  // Yellow
#define COLOR_BLUE       0xF800  // Blue
#define COLOR_ACCENT     0xFE60  // Orange accent
#define COLOR_PANEL      0x001F  // Light blue panel
#define COLOR_PANEL_DARK 0x000B  // Dark blue panel
#define COLOR_BACKGROUND COLOR_WHITE  // Changed to white for clean look
#define COLOR_TEXT       COLOR_BLACK  // Black text on white background
#define COLOR_GRAY_LIGHT 0x7BEF  // Light gray

// ===== SYSTEM SETTINGS =====
#define ENABLE_SERIAL_DEBUG true
#define SERIAL_BAUD_RATE 115200
#define MAX_MESSAGE_LENGTH 512
#define MQTT_MAX_PACKET_SIZE 1024    // Increased for larger payloads
#define HEARTBEAT_INTERVAL 300000    // 5 minutes
#define TIME_ZONE_OFFSET 8           // GMT+8 Philippines

// ===== NTP SERVERS =====
#define NTP_SERVER_PRIMARY "pool.ntp.org"
#define NTP_SERVER_SECONDARY "time.nist.gov"
#define NTP_SERVER_TERTIARY "time.google.com"
#define NTP_SYNC_TIMEOUT 10000        // 10 seconds
#define NTP_UPDATE_INTERVAL 7200000   // 2 hours
#define NTP_RETRY_INTERVAL 30000      // 30 seconds
#define NTP_MAX_RETRIES 3             // Maximum retries

// ===== ADVANCED BLE SETTINGS (OPTIONAL) =====
#define BLE_SCAN_DURATION_QUICK 1
#define BLE_SCAN_DURATION_FULL 3
#define BLE_SIGNAL_STRENGTH_THRESHOLD -80
#define BLE_RECONNECT_MAX_ATTEMPTS 4
#define PRESENCE_CONFIRM_TIME 6000            // Time to confirm presence change
#define BLE_STATS_REPORT_INTERVAL 60000      // Report stats every minute

// ===== CONSULTATION MESSAGE QUEUE SETTINGS =====
#define MAX_CONSULTATION_QUEUE_SIZE 10       // Maximum queued messages
#define MESSAGE_DISPLAY_TIMEOUT 0            // 0 = never timeout (button only)

// ===== HELPER MACROS =====
#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)
#define DEBUG_PRINT(x) if(ENABLE_SERIAL_DEBUG) Serial.print(x)
#define DEBUG_PRINTLN(x) if(ENABLE_SERIAL_DEBUG) Serial.println(x)
#define DEBUG_PRINTF(format, ...) if(ENABLE_SERIAL_DEBUG) Serial.printf(format, ##__VA_ARGS__)

// ===== CONFIGURATION VALIDATION =====
inline bool validateConfiguration() {
  bool valid = true;

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

  // Layout validation
  if (MAIN_AREA_Y + MAIN_AREA_HEIGHT > BOTTOM_PANEL_Y) {
    DEBUG_PRINTLN("❌ ERROR: Main area overlaps with bottom panel");
    valid = false;
  }

  if (valid) {
    DEBUG_PRINTLN("✅ Configuration validation passed");
    DEBUG_PRINTF("   Faculty: %s (ID: %d)\n", FACULTY_NAME, FACULTY_ID);
    DEBUG_PRINTF("   Department: %s\n", FACULTY_DEPARTMENT);
    DEBUG_PRINTF("   Beacon MAC: %s\n", FACULTY_BEACON_MAC);
    DEBUG_PRINTF("   Grace Period: %d seconds\n", BLE_GRACE_PERIOD_MS / 1000);
    DEBUG_PRINTF("   MQTT Topics: consultease/faculty/%d/*\n", FACULTY_ID);
    DEBUG_PRINTF("   Display Layout: %dx%d, Main Area: %d-%d\n", 
                 SCREEN_WIDTH, SCREEN_HEIGHT, MAIN_AREA_Y, MAIN_AREA_Y + MAIN_AREA_HEIGHT);
  } else {
    DEBUG_PRINTLN("❌ Configuration validation FAILED - Check settings above");
  }

  return valid;
}

#endif // CONFIG_H