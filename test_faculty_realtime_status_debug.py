#!/usr/bin/env python3
"""
Comprehensive debug test for faculty real-time status updates.
This will help identify why faculty availability updates are not working in real-time.
"""

import sys
import os
import json
import time
import logging
from datetime import datetime
import paho.mqtt.client as mqtt

# Add the central_system directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'central_system'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MQTT Configuration
MQTT_BROKER = "192.168.100.3"  # Your MQTT broker IP
MQTT_PORT = 1883
FACULTY_ID = 1

class FacultyStatusDebugger:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        self.received_messages = {}
        self.test_sequence = 0
        
    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected to MQTT broker with result code {rc}")
        
        # Subscribe to ALL topics that might be involved in faculty status
        topics = [
            # ESP32 Raw Messages
            f"consultease/faculty/{FACULTY_ID}/status",
            f"consultease/faculty/{FACULTY_ID}/mac_status", 
            f"consultease/faculty/{FACULTY_ID}/heartbeat",
            
            # Faculty Controller Processed Messages
            f"consultease/faculty/{FACULTY_ID}/status_update",
            
            # System Notifications
            "consultease/system/notifications",
            
            # Dashboard UI Updates
            "consultease/ui/consultation_updates",
            
            # Legacy Topics
            f"faculty/{FACULTY_ID}/status",
            "professor/status"
        ]
        
        for topic in topics:
            client.subscribe(topic)
            logger.info(f"📡 Subscribed to: {topic}")
    
    def on_message(self, client, userdata, msg):
        try:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            topic = msg.topic
            
            try:
                if msg.payload:
                    payload = json.loads(msg.payload.decode())
                    payload_str = json.dumps(payload, indent=2)
                else:
                    payload_str = "(empty payload)"
            except:
                payload_str = f"(raw): {msg.payload.decode()}"
                
            # Store message for analysis
            if topic not in self.received_messages:
                self.received_messages[topic] = []
            
            self.received_messages[topic].append({
                'timestamp': timestamp,
                'payload': payload_str,
                'qos': msg.qos,
                'retain': msg.retain
            })
            
            logger.info(f"📨 [{timestamp}] {topic} (QoS: {msg.qos}, Retain: {msg.retain})")
            logger.info(f"    {payload_str}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def simulate_esp32_status_changes(self):
        """Simulate ESP32 status changes to test the full chain."""
        logger.info("=" * 80)
        logger.info("SIMULATING ESP32 STATUS CHANGES")
        logger.info("=" * 80)
        
        test_cases = [
            {
                "status": "AVAILABLE",
                "present": True,
                "description": "Faculty becomes available"
            },
            {
                "status": "AWAY", 
                "present": False,
                "description": "Faculty goes away"
            },
            {
                "status": "BUSY",
                "present": True,
                "description": "Faculty becomes busy"
            },
            {
                "status": "AVAILABLE",
                "present": True,
                "description": "Faculty returns to available"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            self.test_sequence += 1
            
            logger.info(f"\n--- Test {i}/{len(test_cases)}: {test_case['description']} ---")
            
            # Simulate ESP32 status message
            esp32_message = {
                "faculty_id": FACULTY_ID,
                "faculty_name": "Cris Angelo Salonga",
                "present": test_case["present"],
                "status": test_case["status"],
                "timestamp": int(time.time() * 1000),
                "ntp_sync_status": "SYNCED",
                "in_grace_period": False,
                "detailed_status": test_case["status"],
                "test_sequence": self.test_sequence
            }
            
            topic = f"consultease/faculty/{FACULTY_ID}/status"
            
            logger.info(f"📤 Publishing to {topic}:")
            logger.info(f"    {json.dumps(esp32_message, indent=2)}")
            
            result = self.client.publish(topic, json.dumps(esp32_message), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Published successfully")
            else:
                logger.error(f"❌ Failed to publish, error code: {result.rc}")
                
            # Wait for processing
            logger.info("⏳ Waiting 5 seconds for message processing...")
            time.sleep(5)
            
    def simulate_heartbeat_messages(self):
        """Simulate ESP32 heartbeat messages."""
        logger.info("\n" + "=" * 80)
        logger.info("SIMULATING ESP32 HEARTBEAT MESSAGES")
        logger.info("=" * 80)
        
        heartbeat_message = {
            "faculty_id": FACULTY_ID,
            "uptime": 12345678,
            "free_heap": 45000,
            "wifi_connected": True,
            "mqtt_connected": True,
            "time_initialized": True,
            "faculty_present": True,
            "system_healthy": True,
            "wifi_rssi": -65,
            "connection_quality": "EXCELLENT",
            "presence_status": "AVAILABLE",
            "queue_size": 0,
            "consultation_queue_size": 0
        }
        
        topic = f"consultease/faculty/{FACULTY_ID}/heartbeat"
        
        logger.info(f"📤 Publishing heartbeat to {topic}:")
        logger.info(f"    {json.dumps(heartbeat_message, indent=2)}")
        
        result = self.client.publish(topic, json.dumps(heartbeat_message), qos=0)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"✅ Heartbeat published successfully")
        else:
            logger.error(f"❌ Failed to publish heartbeat, error code: {result.rc}")
            
        time.sleep(3)
    
    def analyze_message_flow(self):
        """Analyze the message flow to identify issues."""
        logger.info("\n" + "=" * 80)
        logger.info("MESSAGE FLOW ANALYSIS")
        logger.info("=" * 80)
        
        # Analyze what messages were received on each topic
        for topic, messages in self.received_messages.items():
            logger.info(f"\n📊 Topic: {topic}")
            logger.info(f"   Messages received: {len(messages)}")
            
            for i, msg in enumerate(messages, 1):
                logger.info(f"   {i}. [{msg['timestamp']}] QoS:{msg['qos']} Retain:{msg['retain']}")
                # Only show first 200 chars of payload to avoid spam
                payload_preview = msg['payload'][:200] + "..." if len(msg['payload']) > 200 else msg['payload']
                logger.info(f"      {payload_preview}")
        
        # Check for expected message flow
        expected_flow = [
            f"consultease/faculty/{FACULTY_ID}/status",           # ESP32 publishes here
            f"consultease/faculty/{FACULTY_ID}/status_update",    # Faculty Controller should publish here
            "consultease/system/notifications"                   # System notifications
        ]
        
        logger.info(f"\n🔍 Expected Message Flow Analysis:")
        
        flow_working = True
        for topic in expected_flow:
            if topic in self.received_messages and len(self.received_messages[topic]) > 0:
                logger.info(f"   ✅ {topic}: {len(self.received_messages[topic])} messages")
            else:
                logger.error(f"   ❌ {topic}: NO MESSAGES RECEIVED!")
                flow_working = False
        
        if flow_working:
            logger.info(f"\n✅ Message flow appears to be working correctly")
        else:
            logger.error(f"\n❌ Message flow is BROKEN - some steps are missing")
            
        # Suggest fixes
        logger.info(f"\n🔧 TROUBLESHOOTING SUGGESTIONS:")
        
        esp32_topic = f"consultease/faculty/{FACULTY_ID}/status"
        status_update_topic = f"consultease/faculty/{FACULTY_ID}/status_update"
        
        if esp32_topic not in self.received_messages:
            logger.info(f"   1. ESP32 is not publishing to {esp32_topic}")
            logger.info(f"      - Check ESP32 connection and publishPresenceUpdate() function")
            logger.info(f"      - Verify MQTT_TOPIC_STATUS in config.h")
            
        elif status_update_topic not in self.received_messages:
            logger.info(f"   2. Faculty Controller is not processing ESP32 messages")
            logger.info(f"      - Check if Faculty Controller is subscribed to {esp32_topic}")
            logger.info(f"      - Check faculty_controller.py handle_faculty_status_update()")
            logger.info(f"      - Check if faculty exists in database")
            
        elif "consultease/system/notifications" not in self.received_messages:
            logger.info(f"   3. System notifications not being published")
            logger.info(f"      - Check Faculty Controller _publish_status_update_with_sequence_safe()")
            
        else:
            logger.info(f"   4. Dashboard might not be processing the updates")
            logger.info(f"      - Check Dashboard subscription to {status_update_topic}")
            logger.info(f"      - Check handle_realtime_status_update() in dashboard_window.py")
    
    def run_comprehensive_test(self):
        """Run the complete diagnostic test."""
        logger.info("🚀 Starting comprehensive faculty status debug test...")
        
        # Connect to MQTT
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            time.sleep(2)  # Wait for connection
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
        
        # Clear received messages
        self.received_messages.clear()
        
        # Test 1: Heartbeat messages
        self.simulate_heartbeat_messages()
        
        # Test 2: Status changes
        self.simulate_esp32_status_changes()
        
        # Wait for final processing
        logger.info("\n⏳ Waiting 10 seconds for final message processing...")
        time.sleep(10)
        
        # Test 3: Analyze results
        self.analyze_message_flow()
        
        # Cleanup
        self.client.loop_stop()
        self.client.disconnect()
        
        logger.info("\n✅ Comprehensive debug test completed!")
        logger.info("📋 Check the analysis above to identify the issue.")
        
        return True

if __name__ == "__main__":
    debugger = FacultyStatusDebugger()
    try:
        success = debugger.run_comprehensive_test()
        if success:
            logger.info("✅ Debug test completed successfully")
        else:
            logger.error("❌ Debug test failed")
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc()) 