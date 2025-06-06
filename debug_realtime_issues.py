#!/usr/bin/env python3
"""
Comprehensive Real-Time Update Issue Diagnostic & Fix Tool
For ConsultEase Application

This script diagnoses and fixes two critical real-time update issues:
1. Faculty Status Real-time Updates (ESP32 → Central System → Dashboard)
2. ESP32 Busy Button Status Updates (ESP32 → Database → UI)
"""

import sys
import os
import time
import json
import logging
from datetime import datetime
import paho.mqtt.client as mqtt

# Add central_system to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'central_system'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('realtime_debug.log')
    ]
)
logger = logging.getLogger(__name__)

class RealTimeIssueDiagnostic:
    """Comprehensive diagnostic tool for real-time update issues."""
    
    def __init__(self):
        self.mqtt_client = mqtt.Client(client_id="RealTimeDebugger")
        self.mqtt_connected = False
        self.received_messages = []
        self.test_faculty_id = 1  # Change this to match your test faculty
        
        # MQTT Configuration - Update with your broker details
        self.MQTT_BROKER = "192.168.100.3"  # Update with your MQTT broker IP
        self.MQTT_PORT = 1883
        
    def connect_mqtt(self):
        """Connect to MQTT broker."""
        try:
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.on_message = self.on_message
            self.mqtt_client.connect(self.MQTT_BROKER, self.MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.mqtt_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                
            if self.mqtt_connected:
                logger.info("✅ Connected to MQTT broker successfully")
                return True
            else:
                logger.error("❌ Failed to connect to MQTT broker within timeout")
                return False
                
        except Exception as e:
            logger.error(f"❌ MQTT connection error: {e}")
            return False
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            self.mqtt_connected = True
            logger.info("🔌 MQTT connected with result code 0")
            
            # Subscribe to all relevant topics for monitoring
            topics = [
                "consultease/#",  # All ConsultEase messages
                f"consultease/faculty/{self.test_faculty_id}/status",
                f"consultease/faculty/{self.test_faculty_id}/status_update", 
                f"consultease/faculty/{self.test_faculty_id}/responses",
                "consultease/ui/consultation_updates",
                "consultease/system/notifications"
            ]
            
            for topic in topics:
                client.subscribe(topic, qos=1)
                logger.info(f"📡 Subscribed to: {topic}")
        else:
            logger.error(f"❌ MQTT connection failed with result code {rc}")
    
    def on_message(self, client, userdata, msg):
        """MQTT message callback."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Store message for analysis
            message_data = {
                'timestamp': datetime.now().isoformat(),
                'topic': topic,
                'payload': payload,
                'qos': msg.qos
            }
            
            self.received_messages.append(message_data)
            
            # Log relevant messages
            if any(keyword in topic for keyword in ['status', 'response', 'notification']):
                logger.info(f"📨 MQTT Message: {topic}")
                logger.info(f"   📄 Payload: {payload}")
                
        except Exception as e:
            logger.error(f"❌ Error processing MQTT message: {e}")
    
    def test_faculty_status_updates(self):
        """Test faculty status real-time updates."""
        logger.info("\n" + "="*60)
        logger.info("🧪 TESTING FACULTY STATUS REAL-TIME UPDATES")
        logger.info("="*60)
        
        # Simulate ESP32 status changes
        test_statuses = [
            ("AVAILABLE", True, "Faculty is present and available"),
            ("AWAY", False, "Faculty has left their desk"),
            ("BUSY", False, "Faculty is busy in consultation")
        ]
        
        for status, present, description in test_statuses:
            logger.info(f"\n🔄 Testing {status} status...")
            
            # Create ESP32-style status message
            esp32_message = {
                "faculty_id": self.test_faculty_id,
                "faculty_name": "Test Faculty",
                "present": present,
                "status": status,
                "timestamp": int(time.time() * 1000),
                "ntp_sync_status": "SYNCED",
                "in_grace_period": False,
                "detailed_status": status
            }
            
            # Publish to ESP32 status topic
            topic = f"consultease/faculty/{self.test_faculty_id}/status"
            payload = json.dumps(esp32_message)
            
            result = self.mqtt_client.publish(topic, payload, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Published {status} status to {topic}")
                logger.info(f"   📄 Payload: {payload}")
                
                # Wait for processing
                time.sleep(3)
                
                # Check for status_update messages
                status_updates = [msg for msg in self.received_messages 
                                if 'status_update' in msg['topic'] and 
                                f"faculty/{self.test_faculty_id}" in msg['topic']]
                
                if status_updates:
                    logger.info(f"✅ Received {len(status_updates)} status_update messages")
                    for update in status_updates[-1:]:  # Show latest
                        logger.info(f"   📨 Topic: {update['topic']}")
                        logger.info(f"   📄 Payload: {update['payload']}")
                else:
                    logger.warning(f"⚠️ No status_update messages received for {status}")
                    
            else:
                logger.error(f"❌ Failed to publish {status} status, error code: {result.rc}")
    
    def test_busy_button_responses(self):
        """Test ESP32 busy button real-time updates."""
        logger.info("\n" + "="*60)
        logger.info("🧪 TESTING ESP32 BUSY BUTTON RESPONSES")
        logger.info("="*60)
        
        # Test both ACKNOWLEDGE and BUSY responses
        test_responses = [
            ("ACKNOWLEDGE", "Faculty acknowledges the consultation request"),
            ("BUSY", "Faculty is currently busy and cannot take the request")
        ]
        
        consultation_id = int(time.time())  # Mock consultation ID
        
        for response_type, description in test_responses:
            logger.info(f"\n🔄 Testing {response_type} response...")
            
            # Create ESP32-style response message
            esp32_response = {
                "faculty_id": self.test_faculty_id,
                "faculty_name": "Test Faculty",
                "response_type": response_type,
                "message_id": str(consultation_id),
                "timestamp": str(int(time.time() * 1000)),
                "faculty_present": True,
                "response_method": "physical_button",
                "status": description
            }
            
            # Publish to responses topic
            topic = f"consultease/faculty/{self.test_faculty_id}/responses"
            payload = json.dumps(esp32_response)
            
            result = self.mqtt_client.publish(topic, payload, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Published {response_type} response to {topic}")
                logger.info(f"   📄 Payload: {payload}")
                
                # Wait for processing
                time.sleep(3)
                
                # Check for UI update messages
                ui_updates = [msg for msg in self.received_messages 
                            if 'ui/consultation_updates' in msg['topic']]
                
                system_notifications = [msg for msg in self.received_messages 
                                      if 'system/notifications' in msg['topic']]
                
                logger.info(f"📊 Analysis for {response_type}:")
                logger.info(f"   📱 UI Updates: {len(ui_updates)} messages")
                logger.info(f"   🌐 System Notifications: {len(system_notifications)} messages")
                
                if ui_updates:
                    latest_ui = ui_updates[-1]
                    logger.info(f"   📨 Latest UI Update: {latest_ui['payload']}")
                
                if system_notifications:
                    latest_notification = system_notifications[-1]
                    logger.info(f"   📨 Latest Notification: {latest_notification['payload']}")
                    
                if not ui_updates and not system_notifications:
                    logger.warning(f"⚠️ No UI updates or notifications received for {response_type}")
                    
            else:
                logger.error(f"❌ Failed to publish {response_type} response, error code: {result.rc}")
                
            consultation_id += 1
    
    def analyze_message_flow(self):
        """Analyze the message flow to identify issues."""
        logger.info("\n" + "="*60)
        logger.info("🔍 ANALYZING MESSAGE FLOW")
        logger.info("="*60)
        
        # Group messages by topic patterns
        topic_groups = {
            'ESP32 Status': [msg for msg in self.received_messages if '/status' in msg['topic'] and 'status_update' not in msg['topic']],
            'Status Updates': [msg for msg in self.received_messages if 'status_update' in msg['topic']],
            'ESP32 Responses': [msg for msg in self.received_messages if '/responses' in msg['topic']],
            'UI Updates': [msg for msg in self.received_messages if 'ui/consultation_updates' in msg['topic']],
            'System Notifications': [msg for msg in self.received_messages if 'system/notifications' in msg['topic']],
            'Other Messages': [msg for msg in self.received_messages if not any(pattern in msg['topic'] for pattern in ['/status', '/responses', 'ui/', 'system/'])]
        }
        
        for group_name, messages in topic_groups.items():
            logger.info(f"\n📊 {group_name}: {len(messages)} messages")
            
            if messages:
                for msg in messages[-2:]:  # Show last 2 messages
                    logger.info(f"   📨 {msg['timestamp']}: {msg['topic']}")
                    try:
                        payload_json = json.loads(msg['payload'])
                        logger.info(f"      📄 {json.dumps(payload_json, indent=6)}")
                    except:
                        logger.info(f"      📄 {msg['payload']}")
    
    def provide_fix_recommendations(self):
        """Provide fix recommendations based on analysis."""
        logger.info("\n" + "="*60)
        logger.info("🔧 FIX RECOMMENDATIONS")
        logger.info("="*60)
        
        # Analyze message patterns
        status_messages = [msg for msg in self.received_messages if '/status' in msg['topic'] and 'update' not in msg['topic']]
        status_updates = [msg for msg in self.received_messages if 'status_update' in msg['topic']]
        response_messages = [msg for msg in self.received_messages if '/responses' in msg['topic']]
        ui_updates = [msg for msg in self.received_messages if 'ui/consultation_updates' in msg['topic']]
        system_notifications = [msg for msg in self.received_messages if 'system/notifications' in msg['topic']]
        
        logger.info("📋 ISSUE ANALYSIS:")
        
        # Issue 1: Faculty Status Updates
        if status_messages and not status_updates:
            logger.error("❌ ISSUE 1: ESP32 status messages received but no status_update messages")
            logger.info("🔧 FIX: Faculty Controller is not processing ESP32 status messages")
            logger.info("   - Check if Faculty Controller is started")
            logger.info("   - Verify MQTT subscriptions in Faculty Controller")
            logger.info("   - Check Faculty Controller logs for errors")
            
        elif not status_messages:
            logger.error("❌ ISSUE 1: No ESP32 status messages received")
            logger.info("🔧 FIX: ESP32 is not publishing status messages")
            logger.info("   - Check ESP32 WiFi/MQTT connection")
            logger.info("   - Verify ESP32 BLE presence detection")
            logger.info("   - Check ESP32 MQTT topic configuration")
            
        else:
            logger.info("✅ Faculty status message flow appears normal")
        
        # Issue 2: Busy Button Responses
        if response_messages and not ui_updates:
            logger.error("❌ ISSUE 2: ESP32 responses received but no UI update messages")
            logger.info("🔧 FIX: Faculty Response Controller is not publishing UI updates")
            logger.info("   - Check Faculty Response Controller _publish_faculty_response_notification method")
            logger.info("   - Verify UI update topic: consultease/ui/consultation_updates")
            
        elif response_messages and not system_notifications:
            logger.error("❌ ISSUE 2: ESP32 responses received but no system notifications") 
            logger.info("🔧 FIX: System notification publishing may be failing")
            logger.info("   - Check system notification topic: consultease/system/notifications")
            
        elif not response_messages:
            logger.error("❌ ISSUE 2: No ESP32 response messages received")
            logger.info("🔧 FIX: ESP32 button responses are not being sent")
            logger.info("   - Check ESP32 button handling code")
            logger.info("   - Verify MQTT topic: consultease/faculty/{id}/responses")
            
        else:
            logger.info("✅ ESP32 response message flow appears normal")
        
        # Dashboard Integration
        if system_notifications:
            logger.info("🔧 DASHBOARD INTEGRATION CHECK:")
            logger.info("   - Verify dashboard subscribes to: consultease/system/notifications")
            logger.info("   - Check _process_system_notification_safe method handles 'faculty_response_received'")
            logger.info("   - Verify update_faculty_card_status method")
    
    def run_comprehensive_test(self):
        """Run comprehensive real-time update test."""
        logger.info("🚀 Starting Comprehensive Real-Time Update Diagnostic")
        logger.info("=" * 80)
        
        # Connect to MQTT
        if not self.connect_mqtt():
            logger.error("❌ Cannot proceed without MQTT connection")
            return False
        
        # Clear previous messages
        self.received_messages = []
        
        # Wait for subscriptions to be established
        logger.info("⏳ Waiting for MQTT subscriptions to be established...")
        time.sleep(2)
        
        # Test faculty status updates
        self.test_faculty_status_updates()
        
        # Test busy button responses
        self.test_busy_button_responses()
        
        # Analyze message flow
        self.analyze_message_flow()
        
        # Provide fix recommendations
        self.provide_fix_recommendations()
        
        # Cleanup
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        
        logger.info("\n" + "="*60)
        logger.info("✅ DIAGNOSTIC COMPLETE")
        logger.info("="*60)
        logger.info(f"📊 Total messages captured: {len(self.received_messages)}")
        logger.info("📝 Check realtime_debug.log for detailed analysis")
        
        return True

if __name__ == "__main__":
    print("🔧 ConsultEase Real-Time Update Diagnostic Tool")
    print("=" * 60)
    print("This tool will help identify and fix real-time update issues.")
    print("Make sure your MQTT broker is running and accessible.")
    print()
    
    # Update MQTT configuration if needed
    diagnostic = RealTimeIssueDiagnostic()
    
    # Prompt for MQTT broker configuration
    broker_input = input(f"MQTT Broker IP (current: {diagnostic.MQTT_BROKER}): ").strip()
    if broker_input:
        diagnostic.MQTT_BROKER = broker_input
    
    faculty_input = input(f"Test Faculty ID (current: {diagnostic.test_faculty_id}): ").strip()
    if faculty_input and faculty_input.isdigit():
        diagnostic.test_faculty_id = int(faculty_input)
    
    print(f"\n🔧 Using MQTT Broker: {diagnostic.MQTT_BROKER}")
    print(f"🔧 Using Faculty ID: {diagnostic.test_faculty_id}")
    print()
    
    # Run the test
    success = diagnostic.run_comprehensive_test()
    
    if success:
        print("\n✅ Diagnostic completed successfully!")
        print("📝 Check the output above and realtime_debug.log for specific fix recommendations.")
    else:
        print("\n❌ Diagnostic failed. Check your MQTT broker connection and try again.") 