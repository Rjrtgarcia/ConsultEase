#!/usr/bin/env python3
"""
Real-time consultation update debugging script.
Tests the complete flow from MQTT message publication to UI update.
"""

import sys
import os
import time
import json
import logging
from datetime import datetime

# Add the central_system directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealtimeConsultationDebugger:
    """Debug real-time consultation updates step by step."""
    
    def __init__(self):
        self.mqtt_service = None
        self.test_handlers = []
        self.received_messages = []
        
    def setup_mqtt_service(self):
        """Set up and start the MQTT service."""
        try:
            from central_system.services.async_mqtt_service import get_async_mqtt_service
            self.mqtt_service = get_async_mqtt_service()
            
            logger.info("🔧 Starting MQTT service...")
            self.mqtt_service.start()
            
            # Wait for connection
            timeout = 15
            start_time = time.time()
            while not self.mqtt_service.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.5)
                logger.info("⏳ Waiting for MQTT connection...")
            
            if self.mqtt_service.is_connected:
                logger.info("✅ MQTT service connected successfully")
                return True
            else:
                logger.error("❌ Failed to connect to MQTT broker")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error setting up MQTT service: {e}")
            return False
    
    def register_test_handlers(self):
        """Register test handlers for consultation update topics."""
        from central_system.utils.mqtt_utils import subscribe_to_topic
        
        def consultation_update_handler(topic, data):
            logger.info(f"🎯 TEST HANDLER: Consultation update received")
            logger.info(f"   Topic: {topic}")
            logger.info(f"   Data: {data}")
            self.received_messages.append({
                'topic': topic,
                'data': data,
                'timestamp': datetime.now()
            })
        
        def general_handler(topic, data):
            logger.info(f"🎯 GENERAL HANDLER: Message received")
            logger.info(f"   Topic: {topic}")
            logger.info(f"   Data: {data}")
        
        # Subscribe to consultation updates
        logger.info("📝 Registering test handlers...")
        subscribe_to_topic("consultease/ui/consultation_updates", consultation_update_handler)
        subscribe_to_topic("consultease/student/+/notifications", general_handler)
        subscribe_to_topic("test/consultation", general_handler)
        
        logger.info("✅ Test handlers registered")
        time.sleep(2)  # Allow subscriptions to process
    
    def test_manual_consultation_panel_creation(self):
        """Test creating a consultation panel manually and checking its MQTT setup."""
        try:
            from central_system.views.consultation_panel import ConsultationPanel
            from PyQt5.QtWidgets import QApplication
            
            # Ensure we have a QApplication instance
            if not QApplication.instance():
                app = QApplication(sys.argv)
            
            # Create a test student
            test_student = {
                'id': 1,
                'name': 'Test Student',
                'department': 'Computer Science'
            }
            
            logger.info("🧪 Creating consultation panel with test student...")
            consultation_panel = ConsultationPanel(student=test_student)
            
            # Check if MQTT subscriptions were set up
            has_mqtt_setup = hasattr(consultation_panel, '_mqtt_subscriptions_setup')
            logger.info(f"📊 Consultation panel MQTT setup: {has_mqtt_setup}")
            
            if has_mqtt_setup:
                logger.info("✅ MQTT subscriptions were set up in consultation panel")
            else:
                logger.error("❌ MQTT subscriptions were NOT set up in consultation panel")
            
            # Check current handlers in MQTT service
            handlers = dict(self.mqtt_service.message_handlers)
            logger.info(f"📋 Current MQTT handlers: {list(handlers.keys())}")
            
            for topic, handler_list in handlers.items():
                logger.info(f"   Topic '{topic}': {len(handler_list)} handlers")
            
            return consultation_panel
            
        except Exception as e:
            logger.error(f"❌ Error creating consultation panel: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return None
    
    def test_publish_consultation_update(self, student_id=1, consultation_id=12345):
        """Test publishing a consultation update message."""
        from central_system.utils.mqtt_utils import publish_mqtt_message
        
        logger.info(f"📤 Publishing test consultation update for student {student_id}, consultation {consultation_id}")
        
        # Create test consultation update
        test_update = {
            'type': 'consultation_status_changed',
            'consultation_id': consultation_id,
            'student_id': student_id,
            'faculty_id': 101,
            'old_status': 'pending',
            'new_status': 'accepted',
            'response_type': 'ACKNOWLEDGE',
            'timestamp': datetime.now().isoformat(),
            'trigger': 'faculty_response'
        }
        
        # Publish to consultation updates topic
        topic = "consultease/ui/consultation_updates"
        success = publish_mqtt_message(topic, test_update, qos=1)
        
        if success:
            logger.info(f"✅ Published test update to {topic}")
        else:
            logger.error(f"❌ Failed to publish test update to {topic}")
        
        # Also publish to student-specific topic
        student_topic = f"consultease/student/{student_id}/notifications"
        student_notification = {
            'type': 'consultation_response',
            'consultation_id': consultation_id,
            'faculty_name': 'Test Faculty',
            'course_code': 'TEST101',
            'response_type': 'ACKNOWLEDGE',
            'new_status': 'accepted',
            'responded_at': datetime.now().isoformat()
        }
        
        success_student = publish_mqtt_message(student_topic, student_notification, qos=1)
        
        if success_student:
            logger.info(f"✅ Published student notification to {student_topic}")
        else:
            logger.error(f"❌ Failed to publish student notification to {student_topic}")
        
        return success and success_student
    
    def test_direct_handler_call(self, consultation_panel):
        """Test calling the consultation panel handler directly."""
        if not consultation_panel:
            logger.error("❌ No consultation panel to test")
            return False
        
        logger.info("🧪 Testing direct handler call...")
        
        # Create test data
        test_topic = "consultease/ui/consultation_updates"
        test_data = {
            'type': 'consultation_status_changed',
            'consultation_id': 67890,
            'student_id': 1,
            'faculty_id': 101,
            'old_status': 'pending',
            'new_status': 'accepted',
            'response_type': 'ACKNOWLEDGE',
            'timestamp': datetime.now().isoformat(),
            'trigger': 'faculty_response'
        }
        
        try:
            # Call the handler directly
            consultation_panel.handle_realtime_consultation_update(test_topic, test_data)
            logger.info("✅ Direct handler call completed successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error in direct handler call: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return False
    
    def check_received_messages(self):
        """Check if any messages were received by test handlers."""
        logger.info(f"📊 Checking received messages... (count: {len(self.received_messages)})")
        
        if self.received_messages:
            for i, msg in enumerate(self.received_messages):
                logger.info(f"   Message {i+1}:")
                logger.info(f"     Topic: {msg['topic']}")
                logger.info(f"     Data: {msg['data']}")
                logger.info(f"     Time: {msg['timestamp']}")
            return True
        else:
            logger.warning("❌ No messages received by test handlers")
            return False
    
    def run_comprehensive_test(self):
        """Run the complete diagnostic test."""
        logger.info("🚀 Starting comprehensive real-time consultation update test...")
        
        # Step 1: Set up MQTT service
        if not self.setup_mqtt_service():
            logger.error("❌ Test failed: Could not set up MQTT service")
            return False
        
        # Step 2: Register test handlers
        self.register_test_handlers()
        
        # Step 3: Create consultation panel
        consultation_panel = self.test_manual_consultation_panel_creation()
        
        # Step 4: Test direct handler call
        if consultation_panel:
            self.test_direct_handler_call(consultation_panel)
        
        # Step 5: Test publishing messages
        self.test_publish_consultation_update()
        
        # Step 6: Wait for messages to arrive
        logger.info("⏳ Waiting for messages to arrive...")
        time.sleep(5)
        
        # Step 7: Check results
        self.check_received_messages()
        
        # Step 8: Check MQTT service stats
        stats = self.mqtt_service.get_stats()
        logger.info(f"📊 Final MQTT stats: {stats}")
        
        logger.info("🏁 Comprehensive test completed")
        return True

def main():
    """Main function to run the debug test."""
    debugger = RealtimeConsultationDebugger()
    
    try:
        # Run the comprehensive test
        success = debugger.run_comprehensive_test()
        
        if success:
            logger.info("✅ Debug test completed successfully")
        else:
            logger.error("❌ Debug test failed")
            
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
    finally:
        # Clean up
        if debugger.mqtt_service:
            debugger.mqtt_service.stop()

if __name__ == "__main__":
    main() 