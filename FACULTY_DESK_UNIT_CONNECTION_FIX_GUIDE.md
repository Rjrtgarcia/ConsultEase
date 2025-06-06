# Faculty Desk Unit WiFi/MQTT Connection Fix Guide

## Problem Summary
The faculty desk units are experiencing frequent WiFi and MQTT connection failures, which prevents faculty responses from reaching the central system and causes the consultation history status to not update in real-time.

## Root Causes Identified

1. **Aggressive Timeout Settings**: WiFi and MQTT timeouts are too short (30s WiFi, 60s MQTT keepalive)
2. **Poor Reconnection Logic**: Long delays between reconnection attempts (5s intervals)
3. **Insufficient Signal Quality Monitoring**: Not monitoring WiFi signal strength adequately
4. **Power Management Issues**: WiFi power save mode causing disconnections
5. **Small Buffer Sizes**: MQTT buffer too small (1024 bytes) for consultation messages
6. **Blocking Operations**: Main loop operations blocking connection monitoring
7. **No Connection Stability Checks**: No validation of connection quality before marking as stable

## Solution Overview

The fix involves three main components:

1. **Improved Configuration** (`config_fixes.h`)
2. **Enhanced Network Functions** (`network_connection_fixes.h`)
3. **Modified Main Loop** (integration changes)

## Quick Fix Implementation

### Step 1: Add the Fix Files
Copy these files to your faculty desk unit project:
- `config_fixes.h`
- `network_connection_fixes.h`

### Step 2: Modify the Main Sketch

Add these includes at the top of your `.ino` file:
```cpp
#include "config_fixes.h"
#include "network_connection_fixes.h"
```

### Step 3: Replace Network Setup
Replace your existing `setupWiFi()` and `setupMQTT()` calls in `setup()` with:
```cpp
setupNetworkingImproved();
```

### Step 4: Update Main Loop
Replace your existing WiFi/MQTT check calls in `loop()` with:
```cpp
// Replace these lines:
// checkWiFiConnection();
// checkMQTTConnection();

// With this single call:
updateNetworkConnectionsImproved();
```

### Step 5: Optional Diagnostics
Add this to your main loop for better monitoring:
```cpp
// Add diagnostic reporting every 5 minutes
static unsigned long lastDiagnostics = 0;
if (millis() - lastDiagnostics > 300000) {  // 5 minutes
    printNetworkDiagnostics();
    lastDiagnostics = millis();
}
```

## Detailed Configuration Changes

### WiFi Improvements
- **Connection Timeout**: 30s → 45s (more time for weak signals)
- **Reconnect Interval**: 5s → 3s (faster recovery)
- **Max Retries**: default → 15 (more persistent)
- **Signal Threshold**: -80 dBm → -75 dBm (better quality requirement)
- **Power Save**: Disabled (prevents sleep-related disconnections)
- **TX Power**: Set to maximum (better range)

### MQTT Improvements
- **Keepalive**: 60s → 120s (more tolerant of network hiccups)
- **Buffer Size**: 1024 → 2048 bytes (handles larger consultation messages)
- **Socket Timeout**: 15s → 30s (more time for slow networks)
- **Connect Timeout**: 15s → 20s (more time for initial connection)
- **Reconnect Interval**: 5s → 2s (faster recovery)
- **QoS**: Ensure QoS 1 for reliable message delivery

### Connection Monitoring
- **Check Frequency**: Variable → Every 2s (consistent monitoring)
- **Heartbeat**: 5 minutes → 2 minutes (more frequent status updates)
- **Signal Monitoring**: Added continuous RSSI monitoring
- **Error Handling**: Enhanced error detection and recovery

## Expected Results

After applying these fixes, you should see:

1. **Reduced Connection Drops**: Fewer "WiFi disconnected" messages
2. **Faster Recovery**: Quicker reconnection when drops do occur
3. **Better Signal Handling**: Warnings when signal quality is poor
4. **Reliable Message Delivery**: Faculty responses reaching the central system consistently
5. **Real-time Status Updates**: Consultation history updating automatically without manual refresh

## Testing the Fixes

### 1. Monitor Serial Output
Watch for these improved log messages:
```
✅ WiFi connected successfully!
📶 Signal: -65 dBm 📶 GOOD
✅ MQTT connected successfully!
💓 Heartbeat sent
```

### 2. Check Connection Stability
- Units should maintain connection for hours without drops
- Signal strength should be logged regularly
- Reconnections should happen within 3-5 seconds

### 3. Test Faculty Responses
- Send a test consultation request
- Press ACKNOWLEDGE or BUSY on the faculty desk unit
- Verify the response reaches the central system within 2-3 seconds
- Check that consultation history updates in real-time

### 4. Monitor Diagnostics
Enable diagnostic logging to see:
```
📊 NETWORK DIAGNOSTICS:
WiFi Status: CONNECTED
IP: 192.168.100.15
Signal: -62 dBm
MQTT Status: CONNECTED
Free Heap: 187456 bytes
Uptime: 3600 seconds
```

## Troubleshooting

### If WiFi Still Disconnects Frequently
1. Check signal strength: Should be better than -75 dBm
2. Verify router settings: Ensure 2.4GHz band is stable
3. Check for interference: Other devices on same channel
4. Consider static IP: Uncomment static IP configuration in fixes

### If MQTT Fails to Connect
1. Verify broker is running: `sudo systemctl status mosquitto`
2. Check firewall: Ensure port 1883 is open
3. Test from command line: `mosquitto_pub -h 192.168.100.3 -t test -m hello`
4. Check broker logs: `sudo journalctl -u mosquitto -f`

### If Messages Still Don't Reach Central System
1. Check MQTT topic subscriptions in central system
2. Verify student ID matching in consultation panel
3. Test with the simple MQTT test script: `python3 central_system/test_mqtt_realtime_simple.py`

## Additional Recommendations

1. **Router Configuration**: 
   - Set 2.4GHz channel to 1, 6, or 11 (non-overlapping)
   - Disable band steering if available
   - Increase beacon interval if many devices

2. **Power Supply**: 
   - Ensure stable 5V power supply
   - Use quality USB cables
   - Consider power isolation if multiple units

3. **Physical Placement**: 
   - Position units for good WiFi signal
   - Avoid metal enclosures that block signal
   - Keep antennas oriented properly

4. **Monitoring**: 
   - Set up MQTT monitoring dashboard
   - Log connection events for analysis
   - Monitor central system MQTT broker health

## Summary

These fixes address the root causes of connection instability by:
- Providing more generous timeouts for poor network conditions
- Implementing faster recovery from connection drops
- Adding comprehensive connection quality monitoring
- Optimizing power management for stability
- Enhancing error handling and diagnostics

The result should be faculty desk units that maintain stable connections and ensure real-time consultation status updates work reliably. 