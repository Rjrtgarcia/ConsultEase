#!/usr/bin/env python3
"""
Test script to compare BUSY vs ACKNOWLEDGE responses from ESP32.
This will help identify why real-time updates aren't working for the BUSY button.
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

# MQTT Topics
RESPONSES_TOPIC = f"consultease/faculty/{FACULTY_ID}/responses"
MESSAGES_TOPIC = f"consultease/faculty/{FACULTY_ID}/messages"
UI_UPDATES_TOPIC = "consultease/ui/consultation_updates"
SYSTEM_NOTIFICATIONS_TOPIC = "consultease/system/notifications"

class BusyVsAcknowledgeTester:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        self.received_messages = []
        self.test_consultation_id = int(time.time())  # Use timestamp as unique ID
        
    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected to MQTT broker with result code {rc}")
        
        # Subscribe to all relevant topics to monitor responses
        topics = [
            RESPONSES_TOPIC,
            UI_UPDATES_TOPIC,
            SYSTEM_NOTIFICATIONS_TOPIC,
            f"consultease/student/{FACULTY_ID}/notifications"
        ]
        
        for topic in topics:
            client.subscribe(topic)
            logger.info(f"Subscribed to: {topic}")
    
    def on_message(self, client, userdata, msg):
        try:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            topic = msg.topic
            
            try:
                payload = json.loads(msg.payload.decode())
                payload_str = json.dumps(payload, indent=2)
            except:
                payload_str = msg.payload.decode()
                
            log_entry = {
                'timestamp': timestamp,
                'topic': topic,
                'payload': payload_str
            }
            
            self.received_messages.append(log_entry)
            
            logger.info(f"📨 [{timestamp}] {topic}")
            logger.info(f"    {payload_str}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def send_test_consultation(self):
        """Send a test consultation message to ESP32."""
        logger.info("=" * 60)
        logger.info("SENDING TEST CONSULTATION")
        logger.info("=" * 60)
        
        consultation_message = f"CID:{self.test_consultation_id} From:Test Student (SID:12345): Test consultation for busy vs acknowledge comparison"
        
        logger.info(f"📤 Sending to topic: {MESSAGES_TOPIC}")
        logger.info(f"📤 Message: {consultation_message}")
        
        result = self.client.publish(MESSAGES_TOPIC, consultation_message, qos=2)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info("✅ Test consultation sent successfully")
            logger.info("💡 ESP32 should now display the consultation message")
            return True
        else:
            logger.error(f"❌ Failed to send consultation, error code: {result.rc}")
            return False
    
    def simulate_esp32_response(self, response_type):
        """Simulate an ESP32 response (ACKNOWLEDGE or BUSY)."""
        logger.info("=" * 60)
        logger.info(f"SIMULATING ESP32 {response_type} RESPONSE")
        logger.info("=" * 60)
        
        # Create response exactly like ESP32 would send it
        response_data = {
            "faculty_id": FACULTY_ID,
            "faculty_name": "Cris Angelo Salonga",
            "response_type": response_type,
            "message_id": str(self.test_consultation_id),
            "timestamp": str(int(time.time() * 1000)),
            "faculty_present": True,
            "response_method": "physical_button",
            "status": f"Professor {'acknowledges the request' if response_type == 'ACKNOWLEDGE' else 'is currently busy'}"
        }
        
        logger.info(f"📤 Sending {response_type} response to topic: {RESPONSES_TOPIC}")
        logger.info(f"📤 Response data: {json.dumps(response_data, indent=2)}")
        
        result = self.client.publish(RESPONSES_TOPIC, json.dumps(response_data), qos=2)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"✅ {response_type} response sent successfully")
            return True
        else:
            logger.error(f"❌ Failed to send {response_type} response, error code: {result.rc}")
            return False
    
    def run_comparison_test(self):
        """Run the complete comparison test."""
        logger.info("🚀 Starting BUSY vs ACKNOWLEDGE comparison test...")
        
        # Connect to MQTT
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            time.sleep(2)  # Wait for connection
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
        
        # Test 1: ACKNOWLEDGE Response
        logger.info("\n" + "="*60)
        logger.info("TEST 1: ACKNOWLEDGE RESPONSE")
        logger.info("="*60)
        
        self.test_consultation_id = int(time.time())
        self.received_messages.clear()
        
        # Send consultation and wait
        if not self.send_test_consultation():
            return False
        time.sleep(3)
        
        # Simulate ACKNOWLEDGE response
        if not self.simulate_esp32_response("ACKNOWLEDGE"):
            return False
        
        # Wait for all system responses
        logger.info("⏳ Waiting 10 seconds for ACKNOWLEDGE response processing...")
        time.sleep(10)
        
        acknowledge_messages = self.received_messages.copy()
        
        # Test 2: BUSY Response
        logger.info("\n" + "="*60)
        logger.info("TEST 2: BUSY RESPONSE")
        logger.info("="*60)
        
        self.test_consultation_id = int(time.time()) + 1
        self.received_messages.clear()
        
        # Send consultation and wait
        if not self.send_test_consultation():
            return False
        time.sleep(3)
        
        # Simulate BUSY response
        if not self.simulate_esp32_response("BUSY"):
            return False
        
        # Wait for all system responses
        logger.info("⏳ Waiting 10 seconds for BUSY response processing...")
        time.sleep(10)
        
        busy_messages = self.received_messages.copy()
        
        # Compare Results
        self.compare_results(acknowledge_messages, busy_messages)
        
        # Cleanup
        self.client.loop_stop()
        self.client.disconnect()
        
        return True
    
    def compare_results(self, acknowledge_msgs, busy_msgs):
        """Compare ACKNOWLEDGE vs BUSY response results."""
        logger.info("\n" + "="*60)
        logger.info("COMPARISON RESULTS")
        logger.info("="*60)
        
        logger.info(f"📊 ACKNOWLEDGE Response Messages: {len(acknowledge_msgs)}")
        for i, msg in enumerate(acknowledge_msgs, 1):
            logger.info(f"   {i}. [{msg['timestamp']}] {msg['topic']}")
        
        logger.info(f"\n📊 BUSY Response Messages: {len(busy_msgs)}")
        for i, msg in enumerate(busy_msgs, 1):
            logger.info(f"   {i}. [{msg['timestamp']}] {msg['topic']}")
        
        # Analyze differences
        logger.info(f"\n🔍 ANALYSIS:")
        
        ack_topics = set(msg['topic'] for msg in acknowledge_msgs)
        busy_topics = set(msg['topic'] for msg in busy_msgs)
        
        missing_in_busy = ack_topics - busy_topics
        missing_in_ack = busy_topics - ack_topics
        
        if missing_in_busy:
            logger.warning(f"❌ Topics missing in BUSY response: {missing_in_busy}")
        
        if missing_in_ack:
            logger.warning(f"❌ Topics missing in ACKNOWLEDGE response: {missing_in_ack}")
        
        if len(acknowledge_msgs) == len(busy_msgs) and not missing_in_busy and not missing_in_ack:
            logger.info("✅ Both responses triggered the same number of messages on the same topics")
        else:
            logger.warning("⚠️ Responses differ in message count or topics")
        
        # Check for UI update messages specifically
        ui_updates_ack = [msg for msg in acknowledge_msgs if 'ui/consultation_updates' in msg['topic']]
        ui_updates_busy = [msg for msg in busy_msgs if 'ui/consultation_updates' in msg['topic']]
        
        logger.info(f"\n📱 UI Update Messages:")
        logger.info(f"   ACKNOWLEDGE: {len(ui_updates_ack)} messages")
        logger.info(f"   BUSY: {len(ui_updates_busy)} messages")
        
        if len(ui_updates_ack) > 0 and len(ui_updates_busy) == 0:
            logger.error("❌ CRITICAL: BUSY responses are not triggering UI updates!")
        elif len(ui_updates_ack) == 0 and len(ui_updates_busy) > 0:
            logger.error("❌ CRITICAL: ACKNOWLEDGE responses are not triggering UI updates!")
        elif len(ui_updates_ack) > 0 and len(ui_updates_busy) > 0:
            logger.info("✅ Both responses are triggering UI updates")
        else:
            logger.warning("⚠️ Neither response triggered UI updates")

if __name__ == "__main__":
    tester = BusyVsAcknowledgeTester()
    try:
        success = tester.run_comparison_test()
        if success:
            logger.info("✅ Comparison test completed successfully")
        else:
            logger.error("❌ Comparison test failed")
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc()) 