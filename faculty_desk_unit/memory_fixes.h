/**
 * Memory Optimization Fixes for ConsultEase ESP32 Faculty Desk Unit
 * 
 * This file contains memory-optimized replacements for String-heavy operations
 * that are causing low memory warnings (42KB free heap is too low).
 * 
 * Key Changes:
 * 1. Replace String concatenation with static char buffers
 * 2. Use sprintf instead of String operations
 * 3. Implement buffer recycling for MQTT payloads
 * 4. Add memory monitoring and cleanup routines
 */

#ifndef MEMORY_FIXES_H
#define MEMORY_FIXES_H

#include <Arduino.h>
#include <ESP.h>

// Memory management constants
#define MQTT_PAYLOAD_BUFFER_SIZE 1024
#define TOPIC_BUFFER_SIZE 128
#define MESSAGE_BUFFER_SIZE 512
#define MEMORY_WARNING_THRESHOLD 50000  // 50KB
#define MEMORY_CRITICAL_THRESHOLD 30000 // 30KB

// Static buffers to replace String operations
extern char mqtt_payload_buffer[MQTT_PAYLOAD_BUFFER_SIZE];
extern char mqtt_topic_buffer[TOPIC_BUFFER_SIZE];
extern char temp_message_buffer[MESSAGE_BUFFER_SIZE];

// Memory monitoring functions
void initMemoryOptimization();
void checkMemoryStatus();
void forceMemoryCleanup();
void logMemoryStats();

// Optimized MQTT publishing functions
bool publishHeartbeatOptimized(int faculty_id, const char* mqtt_topic_heartbeat);
bool publishPresenceUpdateOptimized(int faculty_id, const char* faculty_name, bool present, bool in_grace_period, unsigned long grace_remaining, const char* mqtt_topic_status);
bool publishDiagnosticsOptimized(int faculty_id, const char* mqtt_topic_diagnostics);

// String operation replacements
void buildJsonPayload(char* buffer, size_t buffer_size, const char* format, ...);
void appendJsonField(char* buffer, size_t buffer_size, const char* key, const char* value, bool is_last = false);
void appendJsonFieldInt(char* buffer, size_t buffer_size, const char* key, int value, bool is_last = false);
void appendJsonFieldBool(char* buffer, size_t buffer_size, const char* key, bool value, bool is_last = false);

// Memory management utilities
void clearBuffer(char* buffer, size_t size);
size_t getStringLength(const char* str, size_t max_len);
bool isMemoryLow();
bool isMemoryCritical();

// Emergency memory management
void emergencyMemoryCleanup();
void resetStringBuffers();

#endif // MEMORY_FIXES_H 