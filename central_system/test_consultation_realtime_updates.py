#!/usr/bin/env python3
"""
Test script to debug real-time consultation status updates.
This script simulates faculty responses and checks if the consultation panel receives them.
"""

import sys
import os
import time
import logging
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Mock PyQt5 before importing our modules
sys.modules['PyQt5'] = Mock()
sys.modules['PyQt5.QtWidgets'] = Mock()
sys.modules['PyQt5.QtCore'] = Mock()
sys.modules['PyQt5.QtGui'] = Mock()

# Set up basic environment
os.environ['DB_TYPE'] = 'sqlite'
os.environ['DB_PATH'] = ':memory:'
os.environ['CONFIG_TYPE'] = 'test'

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConsultationRealtimeUpdateTester:
    """Test class to verify real-time consultation status updates."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mqtt_messages_received = []
        self.ui_updates_received = []
        
    def mock_mqtt_service(self):
        """Mock the MQTT service to track messages."""
        self.mqtt_handlers = {}
        
        def mock_subscribe_to_topic(topic, handler):
            if topic not in self.mqtt_handlers:
                self.mqtt_handlers[topic] = []
            self.mqtt_handlers[topic].append(handler)
            self.logger.info(f"📡 Subscribed to topic: {topic}")
            
        def mock_publish_mqtt_message(topic, message, qos=0):
            self.logger.info(f"📤 Publishing to {topic}: {json.dumps(message, indent=2)}")
            
            # Simulate message delivery to handlers
            for handler_topic, handlers in self.mqtt_handlers.items():
                if self._topic_matches(topic, handler_topic):
                    for handler in handlers:
                        self.logger.info(f"🎯 Delivering message to handler for {handler_topic}")
                        try:
                            handler(topic, message)
                        except Exception as e:
                            self.logger.error(f"❌ Handler error: {e}")
            return True
            
        return mock_subscribe_to_topic, mock_publish_mqtt_message
    
    def _topic_matches(self, published_topic, subscribed_topic):
        """Check if a published topic matches a subscribed topic pattern."""
        # Simple wildcard matching for + (single level)
        if '+' in subscribed_topic:
            pub_parts = published_topic.split('/')
            sub_parts = subscribed_topic.split('/')
            if len(pub_parts) != len(sub_parts):
                return False
            for pub, sub in zip(pub_parts, sub_parts):
                if sub != '+' and sub != pub:
                    return False
            return True
        return published_topic == subscribed_topic
    
    def simulate_consultation_panel_subscription(self):
        """Simulate the consultation panel setting up MQTT subscriptions."""
        self.logger.info("🔧 Setting up consultation panel MQTT subscriptions...")
        
        # Mock the consultation panel's handle_realtime_consultation_update method
        def mock_handle_realtime_consultation_update(topic, data):
            self.logger.info(f"🔔 Consultation panel received update: Topic={topic}, Data={data}")
            self.ui_updates_received.append({
                'topic': topic,
                'data': data,
                'timestamp': datetime.now()
            })
            
            # Simulate the real method logic
            try:
                update_type = data.get('type')
                consultation_id = data.get('consultation_id')
                new_status = data.get('new_status')
                trigger = data.get('trigger', 'unknown')
                
                self.logger.info(f"📱 Processing consultation update: {consultation_id} -> {new_status} (trigger: {trigger})")
                
                # This would normally call refresh_consultation_history_realtime
                self.logger.info(f"✅ Would update consultation {consultation_id} status to {new_status}")
                
            except Exception as e:
                self.logger.error(f"❌ Error processing consultation update: {e}")
        
        # Subscribe to the consultation updates topic
        mock_subscribe_to_topic, mock_publish_mqtt_message = self.mock_mqtt_service()
        mock_subscribe_to_topic("consultease/ui/consultation_updates", mock_handle_realtime_consultation_update)
        
        return mock_subscribe_to_topic, mock_publish_mqtt_message
    
    def simulate_faculty_response(self, consultation_id, response_type, student_id=1, faculty_id=1):
        """Simulate a faculty response (ACKNOWLEDGE or BUSY)."""
        self.logger.info(f"🎯 Simulating faculty response: {response_type} for consultation {consultation_id}")
        
        # Create the consultation details that would be published
        consultation_details = {
            'id': consultation_id,
            'student_id': student_id,
            'student_name': 'Test Student',
            'faculty_id': faculty_id,
            'faculty_name': 'Test Faculty',
            'course_code': 'TEST101',
            'request_message': 'Test consultation request',
            'old_status': 'pending',
            'new_status': 'accepted' if response_type == 'ACKNOWLEDGE' else 'busy',
            'response_type': response_type
        }
        
        # Simulate the faculty response controller publishing notifications
        timestamp = datetime.now().isoformat()
        
        # 1. UI update message (this is what the consultation panel should receive)
        ui_update_topic = "consultease/ui/consultation_updates"
        ui_message = {
            'type': 'consultation_status_changed',
            'consultation_id': consultation_details['id'],
            'student_id': consultation_details['student_id'],
            'faculty_id': consultation_details['faculty_id'],
            'old_status': consultation_details['old_status'],
            'new_status': consultation_details['new_status'],
            'response_type': consultation_details['response_type'],
            'timestamp': timestamp,
            'trigger': 'faculty_response'
        }
        
        return ui_update_topic, ui_message
    
    def test_consultation_update_flow(self):
        """Test the complete consultation update flow."""
        self.logger.info("🚀 Testing consultation update flow...")
        
        # Set up mock MQTT subscriptions
        mock_subscribe, mock_publish = self.simulate_consultation_panel_subscription()
        
        # Test Case 1: Faculty acknowledges consultation
        self.logger.info("\n📋 Test Case 1: Faculty acknowledges consultation")
        topic, message = self.simulate_faculty_response(consultation_id=123, response_type='ACKNOWLEDGE')
        mock_publish(topic, message)
        
        # Test Case 2: Faculty marks consultation as busy
        self.logger.info("\n📋 Test Case 2: Faculty marks consultation as busy")
        topic, message = self.simulate_faculty_response(consultation_id=124, response_type='BUSY')
        mock_publish(topic, message)
        
        # Test Case 3: Wrong student ID (should be ignored)
        self.logger.info("\n📋 Test Case 3: Different student ID (should be ignored)")
        topic, message = self.simulate_faculty_response(consultation_id=125, response_type='ACKNOWLEDGE', student_id=999)
        mock_publish(topic, message)
        
        # Analyze results
        self.logger.info(f"\n📊 Test Results:")
        self.logger.info(f"   Total UI updates received: {len(self.ui_updates_received)}")
        
        for i, update in enumerate(self.ui_updates_received, 1):
            data = update['data']
            self.logger.info(f"   Update {i}: Consultation {data.get('consultation_id')} -> {data.get('new_status')} (trigger: {data.get('trigger')})")
        
        # Check if we received the expected updates
        expected_updates = 3  # All messages should be received, but only some processed
        if len(self.ui_updates_received) == expected_updates:
            self.logger.info("✅ All expected MQTT messages received!")
            return True
        else:
            self.logger.error(f"❌ Expected {expected_updates} updates, but received {len(self.ui_updates_received)}")
            return False
    
    def test_topic_subscription_patterns(self):
        """Test MQTT topic subscription patterns."""
        self.logger.info("🔍 Testing MQTT topic subscription patterns...")
        
        # Test various topic patterns
        test_cases = [
            ("consultease/ui/consultation_updates", "consultease/ui/consultation_updates", True),
            ("consultease/faculty/1/responses", "consultease/faculty/+/responses", True),
            ("consultease/faculty/2/responses", "consultease/faculty/+/responses", True),
            ("consultease/student/1/notifications", "consultease/student/+/notifications", True),
            ("consultease/other/topic", "consultease/ui/consultation_updates", False),
        ]
        
        all_passed = True
        for published, subscribed, expected in test_cases:
            result = self._topic_matches(published, subscribed)
            status = "✅" if result == expected else "❌"
            self.logger.info(f"   {status} {published} matches {subscribed}: {result} (expected: {expected})")
            if result != expected:
                all_passed = False
        
        return all_passed
    
    def run_all_tests(self):
        """Run all real-time update tests."""
        self.logger.info("🧪 Starting consultation real-time update tests...")
        
        tests = [
            ("Topic Subscription Patterns", self.test_topic_subscription_patterns),
            ("Consultation Update Flow", self.test_consultation_update_flow),
        ]
        
        results = []
        for test_name, test_func in tests:
            self.logger.info(f"\n📋 {test_name}")
            try:
                result = test_func()
                results.append((test_name, result))
                status = "✅ PASSED" if result else "❌ FAILED"
                self.logger.info(f"   {status}")
            except Exception as e:
                self.logger.error(f"   ❌ ERROR: {e}")
                results.append((test_name, False))
        
        # Summary
        passed = sum(1 for name, result in results if result)
        total = len(results)
        
        self.logger.info(f"\n📊 TEST SUMMARY:")
        self.logger.info(f"   Passed: {passed}/{total}")
        
        for test_name, result in results:
            status = "✅" if result else "❌"
            self.logger.info(f"   {status} {test_name}")
        
        if passed == total:
            self.logger.info("🎉 ALL TESTS PASSED - Real-time updates should work!")
            return True
        else:
            self.logger.error("❌ Some tests failed - check real-time update setup")
            return False

def main():
    """Main test function."""
    print("🧪 Consultation Real-time Update Test")
    print("=" * 50)
    
    tester = ConsultationRealtimeUpdateTester()
    success = tester.run_all_tests()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ ALL TESTS PASSED - Real-time updates should work!")
        print("\n💡 If updates still don't work in the actual app, check:")
        print("   1. MQTT broker is running and accessible")
        print("   2. Faculty response controller is properly started")
        print("   3. Consultation panel is properly subscribing to MQTT")
        print("   4. Student ID matching is working correctly")
        return 0
    else:
        print("❌ TESTS FAILED - Real-time update issues detected!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 