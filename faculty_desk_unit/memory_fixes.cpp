/**
 * Memory Optimization Implementation for ConsultEase ESP32 Faculty Desk Unit
 */

#include "memory_fixes.h"
#include <PubSubClient.h>
#include <stdarg.h>
#include <stdio.h>

// External references
extern PubSubClient mqttClient;
extern bool wifiConnected;
extern bool mqttConnected;
extern bool wifiConnectionStable;
extern bool mqttConnectionStable;
extern int currentWifiRSSI;
extern int wifiRetryCount;
extern int mqttRetryCount;
extern bool timeInitialized;
extern String ntpSyncStatus;
extern int queueCount;
extern int consultationQueueSize;

// Static buffer definitions
char mqtt_payload_buffer[MQTT_PAYLOAD_BUFFER_SIZE];
char mqtt_topic_buffer[TOPIC_BUFFER_SIZE];
char temp_message_buffer[MESSAGE_BUFFER_SIZE];

// Memory monitoring variables
static unsigned long last_memory_check = 0;
static size_t min_free_heap = 0;
static bool memory_optimization_initialized = false;

void initMemoryOptimization() {
    // Clear all buffers
    clearBuffer(mqtt_payload_buffer, MQTT_PAYLOAD_BUFFER_SIZE);
    clearBuffer(mqtt_topic_buffer, TOPIC_BUFFER_SIZE);
    clearBuffer(temp_message_buffer, MESSAGE_BUFFER_SIZE);
    
    min_free_heap = ESP.getFreeHeap();
    memory_optimization_initialized = true;
    
    Serial.println("Memory optimization initialized");
    logMemoryStats();
}

void checkMemoryStatus() {
    if (!memory_optimization_initialized) return;
    
    unsigned long current_time = millis();
    if (current_time - last_memory_check < 10000) return; // Check every 10 seconds
    
    size_t current_free = ESP.getFreeHeap();
    
    // Update minimum free heap
    if (current_free < min_free_heap) {
        min_free_heap = current_free;
    }
    
    // Check for memory warnings
    if (isMemoryCritical()) {
        Serial.printf("CRITICAL: Memory critically low! %d bytes free\n", current_free);
        emergencyMemoryCleanup();
    } else if (isMemoryLow()) {
        Serial.printf("WARNING: Memory low! %d bytes free\n", current_free);
        forceMemoryCleanup();
    }
    
    last_memory_check = current_time;
}

void forceMemoryCleanup() {
    Serial.println("Performing memory cleanup...");
    
    // Clear all static buffers
    resetStringBuffers();
    
    // Force garbage collection
    void* temp = malloc(1024);
    if (temp) {
        free(temp);
    }
    
    Serial.printf("Memory cleanup complete. Free heap: %d bytes\n", ESP.getFreeHeap());
}

void emergencyMemoryCleanup() {
    Serial.println("EMERGENCY: Performing aggressive memory cleanup...");
    
    // Reset all buffers
    resetStringBuffers();
    
    // Multiple garbage collection cycles
    for (int i = 0; i < 5; i++) {
        void* temp = malloc(512);
        if (temp) {
            free(temp);
        }
        delay(10);
    }
    
    // If still critical, restart
    if (ESP.getFreeHeap() < 20000) {
        Serial.println("CRITICAL: Restarting ESP32 due to memory shortage...");
        delay(1000);
        ESP.restart();
    }
    
    Serial.printf("Emergency cleanup complete. Free heap: %d bytes\n", ESP.getFreeHeap());
}

void logMemoryStats() {
    size_t free_heap = ESP.getFreeHeap();
    Serial.printf("Memory Stats - Free: %d bytes, Min: %d bytes\n", free_heap, min_free_heap);
    Serial.printf("Largest block: %d bytes, Total heap: %d bytes\n", 
                  ESP.getMaxAllocHeap(), ESP.getHeapSize());
}

bool publishHeartbeatOptimized(int faculty_id, const char* mqtt_topic_heartbeat) {
    if (!mqttClient.connected()) return false;
    
    // Check memory before proceeding
    if (isMemoryCritical()) {
        Serial.println("Skipping heartbeat due to critical memory");
        return false;
    }
    
    clearBuffer(mqtt_payload_buffer, MQTT_PAYLOAD_BUFFER_SIZE);
    
    // Build JSON payload using sprintf instead of String concatenation
    snprintf(mqtt_payload_buffer, MQTT_PAYLOAD_BUFFER_SIZE,
        "{"
        "\"faculty_id\":%d,"
        "\"uptime\":%lu,"
        "\"free_heap\":%d,"
        "\"wifi_connected\":%s,"
        "\"wifi_rssi\":%d,"
        "\"wifi_stable\":%s,"
        "\"mqtt_stable\":%s,"
        "\"wifi_retries\":%d,"
        "\"mqtt_retries\":%d,"
        "\"time_initialized\":%s,"
        "\"ntp_sync_status\":\"%s\","
        "\"queue_size\":%d,"
        "\"consultation_queue_size\":%d"
        "}",
        faculty_id,
        millis(),
        ESP.getFreeHeap(),
        wifiConnected ? "true" : "false",
        currentWifiRSSI,
        wifiConnectionStable ? "true" : "false",
        mqttConnectionStable ? "true" : "false",
        wifiRetryCount,
        mqttRetryCount,
        timeInitialized ? "true" : "false",
        ntpSyncStatus.c_str(),
        queueCount,
        consultationQueueSize
    );
    
    bool result = mqttClient.publish(mqtt_topic_heartbeat, mqtt_payload_buffer);
    
    if (result) {
        Serial.printf("💓 Optimized heartbeat published - Free heap: %d bytes\n", ESP.getFreeHeap());
    } else {
        Serial.println("❌ Optimized heartbeat publish failed");
    }
    
    return result;
}

bool publishPresenceUpdateOptimized(int faculty_id, const char* faculty_name, bool present, bool in_grace_period, unsigned long grace_remaining, const char* mqtt_topic_status) {
    if (!mqttClient.connected()) return false;
    
    if (isMemoryCritical()) {
        Serial.println("Skipping presence update due to critical memory");
        return false;
    }
    
    clearBuffer(mqtt_payload_buffer, MQTT_PAYLOAD_BUFFER_SIZE);
    
    // Build presence JSON payload
    int written = snprintf(mqtt_payload_buffer, MQTT_PAYLOAD_BUFFER_SIZE,
        "{"
        "\"faculty_id\":%d,"
        "\"faculty_name\":\"%s\","
        "\"present\":%s,"
        "\"status\":\"%s\","
        "\"timestamp\":%lu,"
        "\"in_grace_period\":%s",
        faculty_id,
        faculty_name,
        (present && !in_grace_period) ? "true" : "false",
        (present && !in_grace_period) ? "AVAILABLE" : "AWAY",
        millis(),
        in_grace_period ? "true" : "false"
    );
    
    // Add grace period remaining if applicable
    if (in_grace_period && written < MQTT_PAYLOAD_BUFFER_SIZE - 50) {
        written += snprintf(mqtt_payload_buffer + written, MQTT_PAYLOAD_BUFFER_SIZE - written,
            ",\"grace_period_remaining\":%lu", grace_remaining);
    }
    
    // Close JSON
    if (written < MQTT_PAYLOAD_BUFFER_SIZE - 2) {
        strcat(mqtt_payload_buffer, "}");
    }
    
    bool result = mqttClient.publish(mqtt_topic_status, mqtt_payload_buffer);
    
    if (result) {
        Serial.printf("📡 Optimized presence published - Free heap: %d bytes\n", ESP.getFreeHeap());
    } else {
        Serial.println("❌ Optimized presence publish failed");
    }
    
    return result;
}

bool publishDiagnosticsOptimized(int faculty_id, const char* mqtt_topic_diagnostics) {
    if (!mqttClient.connected()) return false;
    
    if (isMemoryCritical()) {
        Serial.println("Skipping diagnostics due to critical memory");
        return false;
    }
    
    clearBuffer(mqtt_payload_buffer, MQTT_PAYLOAD_BUFFER_SIZE);
    
    // Build diagnostics JSON payload
    snprintf(mqtt_payload_buffer, MQTT_PAYLOAD_BUFFER_SIZE,
        "{"
        "\"faculty_id\":%d,"
        "\"timestamp\":%lu,"
        "\"wifi_rssi\":%d,"
        "\"wifi_stable\":%s,"
        "\"mqtt_stable\":%s,"
        "\"wifi_retries\":%d,"
        "\"mqtt_retries\":%d,"
        "\"free_heap\":%d,"
        "\"queue_size\":%d,"
        "\"consultation_queue_size\":%d,"
        "\"system_uptime\":%lu,"
        "\"ntp_status\":\"%s\""
        "}",
        faculty_id,
        millis(),
        currentWifiRSSI,
        wifiConnectionStable ? "true" : "false",
        mqttConnectionStable ? "true" : "false",
        wifiRetryCount,
        mqttRetryCount,
        ESP.getFreeHeap(),
        queueCount,
        consultationQueueSize,
        millis(),
        ntpSyncStatus.c_str()
    );
    
    bool result = mqttClient.publish(mqtt_topic_diagnostics, mqtt_payload_buffer, false);
    
    if (result) {
        Serial.printf("📊 Optimized diagnostics published - Free heap: %d bytes\n", ESP.getFreeHeap());
    } else {
        Serial.println("❌ Optimized diagnostics publish failed");
    }
    
    return result;
}

void clearBuffer(char* buffer, size_t size) {
    if (buffer && size > 0) {
        memset(buffer, 0, size);
    }
}

size_t getStringLength(const char* str, size_t max_len) {
    if (!str) return 0;
    
    size_t len = 0;
    while (len < max_len && str[len] != '\0') {
        len++;
    }
    return len;
}

bool isMemoryLow() {
    return ESP.getFreeHeap() < MEMORY_WARNING_THRESHOLD;
}

bool isMemoryCritical() {
    return ESP.getFreeHeap() < MEMORY_CRITICAL_THRESHOLD;
}

void resetStringBuffers() {
    clearBuffer(mqtt_payload_buffer, MQTT_PAYLOAD_BUFFER_SIZE);
    clearBuffer(mqtt_topic_buffer, TOPIC_BUFFER_SIZE);
    clearBuffer(temp_message_buffer, MESSAGE_BUFFER_SIZE);
}

void appendJsonField(char* buffer, size_t buffer_size, const char* key, const char* value, bool is_last) {
    size_t current_len = strlen(buffer);
    size_t remaining = buffer_size - current_len;
    
    if (remaining > 20) { // Ensure enough space
        if (current_len > 1) { // Not the first field
            strncat(buffer, ",", remaining - 1);
            remaining--;
        }
        
        snprintf(buffer + strlen(buffer), remaining, "\"%s\":\"%s\"", key, value);
        
        if (is_last) {
            strncat(buffer, "}", remaining - 1);
        }
    }
}

void appendJsonFieldInt(char* buffer, size_t buffer_size, const char* key, int value, bool is_last) {
    size_t current_len = strlen(buffer);
    size_t remaining = buffer_size - current_len;
    
    if (remaining > 20) {
        if (current_len > 1) {
            strncat(buffer, ",", remaining - 1);
            remaining--;
        }
        
        snprintf(buffer + strlen(buffer), remaining, "\"%s\":%d", key, value);
        
        if (is_last) {
            strncat(buffer, "}", remaining - 1);
        }
    }
}

void appendJsonFieldBool(char* buffer, size_t buffer_size, const char* key, bool value, bool is_last) {
    size_t current_len = strlen(buffer);
    size_t remaining = buffer_size - current_len;
    
    if (remaining > 20) {
        if (current_len > 1) {
            strncat(buffer, ",", remaining - 1);
            remaining--;
        }
        
        snprintf(buffer + strlen(buffer), remaining, "\"%s\":%s", key, value ? "true" : "false");
        
        if (is_last) {
            strncat(buffer, "}", remaining - 1);
        }
    }
} 