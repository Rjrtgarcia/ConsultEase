# Immediate ESP32 Busy Button Fix

## Quick Diagnostic

### 1. Check ESP32 Serial Output
When you press the BUSY button, you should see:
```
🔴 handleBusyButton() called!
📤 Sending BUSY response to central terminal
✅ BUSY response sent successfully
```

If you see this but the UI doesn't update, the issue is in the central system processing.

### 2. Check Central System Processing
On your Raspberry Pi, check if BUSY responses are being received:
```bash
grep -i "BUSY" /var/log/syslog | tail -5
```

## Immediate Fix Option 1: ESP32 JSON Formatting

Replace the BUSY button response JSON with this exact format:

```cpp
// In handleBusyButton() function, replace the response creation with:
String response = "{";
response += "\"faculty_id\":" + String(FACULTY_ID) + ",";
response += "\"faculty_name\":\"" + String(FACULTY_NAME) + "\",";
response += "\"response_type\":\"BUSY\",";  // Exactly "BUSY" - case sensitive
response += "\"message_id\":\"" + g_receivedConsultationId + "\",";
response += "\"timestamp\":\"" + String(millis()) + "\",";
response += "\"faculty_present\":true,";
response += "\"response_method\":\"physical_button\",";
response += "\"status\":\"Professor is currently busy\"";
response += "}";
```

## Immediate Fix Option 2: Central System Response Processing

### Check faculty_response_controller.py
Ensure this line exists in `_process_faculty_response` method:

```python
elif response_type == "BUSY" or response_type == "UNAVAILABLE":
    new_status_enum = ConsultationStatus.BUSY
```

### Check models/consultation.py
Ensure BUSY status exists in the enum:

```python
class ConsultationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    BUSY = "busy"        # This must exist
    COMPLETED = "completed"
    CANCELLED = "cancelled"
```

## Immediate Fix Option 3: Force Debug Mode

Add this temporary debug function to ESP32:

```cpp
void handleBusyButtonForced() {
    DEBUG_PRINTLN("🔴 FORCED BUSY BUTTON DEBUG");
    
    // Force exact same logic as ACKNOWLEDGE
    if (g_receivedConsultationId.isEmpty()) {
        DEBUG_PRINTLN("❌ No consultation ID");
        return;
    }
    
    // Use minimal JSON that works
    String response = "{\"faculty_id\":1,\"response_type\":\"BUSY\",\"message_id\":\"" + g_receivedConsultationId + "\"}";
    
    DEBUG_PRINTF("📝 Minimal BUSY JSON: %s\n", response.c_str());
    
    bool success = mqttClient.publish("consultease/faculty/1/responses", response.c_str(), false);
    
    DEBUG_PRINTF("📡 Direct publish result: %s\n", success ? "SUCCESS" : "FAILED");
    
    if (success) {
        showResponseConfirmation("BUSY SENT", COLOR_ERROR);
        clearCurrentMessage();
    }
}
```

Then in main loop, call this function when busy button is pressed.

## Quick Test Commands

### On Raspberry Pi:

1. **Monitor all MQTT traffic:**
```bash
mosquitto_sub -h localhost -t "consultease/#" -v | grep -i busy
```

2. **Check central system logs for BUSY processing:**
```bash
journalctl -u your-consulease-service | grep -i busy
```

3. **Test database status updates:**
```bash
sqlite3 your_database.db "SELECT id, status FROM consultations WHERE status='busy' LIMIT 5;"
```

## Expected Results After Fix

1. **ESP32 Serial:** Shows BUSY response sent successfully
2. **MQTT Monitor:** Shows BUSY response published to correct topic
3. **Central System:** Shows BUSY response processed and status updated
4. **Database:** Shows consultation status changed to "busy"
5. **UI:** Updates immediately to show faculty as busy

## If Still Not Working

The issue is likely in the UI update subscription. Check if the dashboard is properly subscribed to:
- `consultease/ui/consultation_updates`
- `consultease/system/notifications`

And verify it handles "busy" status in the update processing logic. 