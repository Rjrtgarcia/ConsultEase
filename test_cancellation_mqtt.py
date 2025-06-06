#!/usr/bin/env python3
"""
Test script to simulate cancellation messages being sent to ESP32 faculty desk unit.
This will help verify if the ESP32 is properly receiving and processing cancellation messages.
"""

import paho.mqtt.client as mqtt
import json
import time
import sys

# MQTT Configuration (adjust these to match your setup)
MQTT_BROKER = "10.0.2.15"  # Replace with your Raspberry Pi IP
MQTT_PORT = 1883
MQTT_USERNAME = "pi"
MQTT_PASSWORD = "password"

# Faculty configuration
FACULTY_ID = 1  # Change this to match your ESP32 faculty ID

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        return True
    else:
        print(f"❌ Failed to connect to MQTT broker. Return code: {rc}")
        return False

def test_cancellation_message():
    """Send a test cancellation message to the ESP32"""
    
    # Create MQTT client
    client = mqtt.Client()
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    
    try:
        print(f"🔌 Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        # Wait for connection
        time.sleep(2)
        
        if not client.is_connected():
            print("❌ Could not establish MQTT connection")
            return False
        
        # Create test cancellation message (matching the format from central system)
        cancellation_topic = f"consultease/faculty/{FACULTY_ID}/cancellations"
        
        test_message = {
            "type": "consultation_cancelled",
            "consultation_id": 999,  # Test ID
            "student_name": "Test Student",
            "course_code": "TEST101",
            "cancelled_at": "2025-06-07T07:17:30.160591"
        }
        
        payload = json.dumps(test_message)
        
        print(f"\n📤 Publishing test cancellation message:")
        print(f"   Topic: {cancellation_topic}")
        print(f"   Payload: {payload}")
        
        # Publish the message
        result = client.publish(cancellation_topic, payload, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("✅ Test cancellation message published successfully!")
            print(f"💡 Check your ESP32 serial monitor for cancellation debug logs")
            print(f"💡 Look for: '🚫 CANCELLATION REQUEST RECEIVED on topic:' messages")
        else:
            print(f"❌ Failed to publish message. Return code: {result.rc}")
            return False
            
        # Wait a bit for message delivery
        time.sleep(3)
        
        # Test another cancellation with a different ID
        test_message2 = {
            "type": "consultation_cancelled", 
            "consultation_id": 888,
            "student_name": "Another Test Student",
            "course_code": "",
            "cancelled_at": "2025-06-07T07:18:00.000000"
        }
        
        payload2 = json.dumps(test_message2)
        print(f"\n📤 Publishing second test cancellation:")
        print(f"   Payload: {payload2}")
        
        result2 = client.publish(cancellation_topic, payload2, qos=1)
        
        if result2.rc == mqtt.MQTT_ERR_SUCCESS:
            print("✅ Second test cancellation message published!")
        else:
            print(f"❌ Failed to publish second message. Return code: {result2.rc}")
        
        time.sleep(2)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during MQTT test: {str(e)}")
        return False
        
    finally:
        client.loop_stop()
        client.disconnect()
        print("\n🔌 Disconnected from MQTT broker")

def main():
    print("=" * 60)
    print("ESP32 CANCELLATION MESSAGE TEST")
    print("=" * 60)
    print(f"Target Faculty ID: {FACULTY_ID}")
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Username: {MQTT_USERNAME}")
    print("\n🎯 This script will send test cancellation messages to your ESP32")
    print("📋 Make sure your ESP32 is connected and monitor its serial output")
    print("=" * 60)
    
    input("\nPress Enter to start the test...")
    
    success = test_cancellation_message()
    
    if success:
        print("\n✅ Test completed successfully!")
        print("\n📋 Next steps:")
        print("1. Check ESP32 serial monitor for cancellation debug messages")
        print("2. Verify that consultation messages are being cleared from display")
        print("3. If no debug messages appear, check ESP32 MQTT connection")
    else:
        print("\n❌ Test failed!")
        print("\n🔧 Troubleshooting:")
        print("1. Verify MQTT broker IP address and credentials")
        print("2. Check if MQTT broker is running")
        print("3. Ensure ESP32 is connected to the same network")

if __name__ == "__main__":
    main() 