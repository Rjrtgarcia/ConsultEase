#!/usr/bin/env python3
"""
Simple MQTT real-time test script for consultation updates.
This can be run on the Raspberry Pi to test the MQTT flow.
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

def test_mqtt_consultation_flow():
    """Test the MQTT consultation update flow."""
    logger.info("🚀 Starting simple MQTT consultation flow test...")
    
    try:
        # Import MQTT utilities
        from central_system.utils.mqtt_utils import publish_mqtt_message, subscribe_to_topic, is_mqtt_connected
        from central_system.services.async_mqtt_service import get_async_mqtt_service
        
        # Start MQTT service
        mqtt_service = get_async_mqtt_service()
        logger.info("🔧 Starting MQTT service...")
        mqtt_service.start()
        
        # Wait for connection
        timeout = 10
        start_time = time.time()
        while not is_mqtt_connected() and (time.time() - start_time) < timeout:
            time.sleep(0.5)
            logger.info("⏳ Waiting for MQTT connection...")
        
        if not is_mqtt_connected():
            logger.error("❌ Failed to connect to MQTT broker")
            return False
        
        logger.info("✅ MQTT service connected")
        
        # Track received messages
        received_messages = []
        
        def test_handler(topic, data):
            logger.info(f"🎯 TEST HANDLER: Received message on topic '{topic}'")
            logger.info(f"   Data: {data}")
            received_messages.append({'topic': topic, 'data': data, 'timestamp': datetime.now()})
        
        # Subscribe to consultation updates
        logger.info("📝 Subscribing to consultation update topics...")
        subscribe_to_topic("consultease/ui/consultation_updates", test_handler)
        subscribe_to_topic("consultease/student/+/notifications", test_handler)
        
        # Wait for subscriptions to process
        time.sleep(2)
        
        # Publish test consultation update
        logger.info("📤 Publishing test consultation update...")
        test_update = {
            'type': 'consultation_status_changed',
            'consultation_id': 99999,
            'student_id': 1,
            'faculty_id': 101,
            'old_status': 'pending',
            'new_status': 'accepted',
            'response_type': 'ACKNOWLEDGE',
            'timestamp': datetime.now().isoformat(),
            'trigger': 'faculty_response'
        }
        
        success = publish_mqtt_message("consultease/ui/consultation_updates", test_update, qos=1)
        if success:
            logger.info("✅ Published consultation update")
        else:
            logger.error("❌ Failed to publish consultation update")
        
        # Publish student notification
        student_notification = {
            'type': 'consultation_response',
            'consultation_id': 99999,
            'faculty_name': 'Test Faculty',
            'course_code': 'TEST101',
            'response_type': 'ACKNOWLEDGE',
            'new_status': 'accepted',
            'responded_at': datetime.now().isoformat()
        }
        
        success_student = publish_mqtt_message("consultease/student/1/notifications", student_notification, qos=1)
        if success_student:
            logger.info("✅ Published student notification")
        else:
            logger.error("❌ Failed to publish student notification")
        
        # Wait for messages to arrive
        logger.info("⏳ Waiting for messages to arrive...")
        time.sleep(3)
        
        # Check results
        logger.info(f"📊 Test Results:")
        logger.info(f"   Messages published: 2")
        logger.info(f"   Messages received: {len(received_messages)}")
        
        if received_messages:
            for i, msg in enumerate(received_messages, 1):
                logger.info(f"   Message {i}:")
                logger.info(f"     Topic: {msg['topic']}")
                logger.info(f"     Type: {msg['data'].get('type', 'unknown')}")
                logger.info(f"     Consultation ID: {msg['data'].get('consultation_id', 'unknown')}")
                logger.info(f"     Time: {msg['timestamp']}")
            
            logger.info("✅ MQTT flow test PASSED - messages were received!")
            return True
        else:
            logger.error("❌ MQTT flow test FAILED - no messages received!")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error in MQTT test: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return False
    finally:
        # Clean up
        try:
            mqtt_service.stop()
        except:
            pass

def test_faculty_response_simulation():
    """Simulate a faculty response and check if it publishes correctly."""
    logger.info("🧪 Testing faculty response simulation...")
    
    try:
        from central_system.controllers.faculty_response_controller import FacultyResponseController
        from central_system.utils.mqtt_utils import subscribe_to_topic
        
        # Track published messages
        published_messages = []
        
        def capture_published_message(topic, data):
            logger.info(f"📨 Captured published message: {topic}")
            published_messages.append({'topic': topic, 'data': data})
        
        # Subscribe to capture published messages
        subscribe_to_topic("consultease/ui/consultation_updates", capture_published_message)
        subscribe_to_topic("consultease/student/+/notifications", capture_published_message)
        
        time.sleep(1)  # Allow subscription
        
        # Create faculty response controller
        controller = FacultyResponseController()
        controller.start()
        
        # Simulate faculty response data
        response_data = {
            'consultation_id': 88888,
            'response_type': 'ACKNOWLEDGE',
            'timestamp': time.time()
        }
        
        # Process the response (this should trigger MQTT publications)
        logger.info("🎯 Simulating faculty response processing...")
        controller.handle_faculty_response(101, response_data)  # faculty_id=101
        
        # Wait for messages
        time.sleep(2)
        
        # Check results
        logger.info(f"📊 Faculty Response Test Results:")
        logger.info(f"   Messages captured: {len(published_messages)}")
        
        for i, msg in enumerate(published_messages, 1):
            logger.info(f"   Message {i}:")
            logger.info(f"     Topic: {msg['topic']}")
            logger.info(f"     Type: {msg['data'].get('type', 'unknown')}")
        
        if published_messages:
            logger.info("✅ Faculty response simulation PASSED")
            return True
        else:
            logger.warning("⚠️ Faculty response simulation - no messages captured")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error in faculty response test: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main function to run the tests."""
    logger.info("🔬 Starting simple MQTT real-time consultation tests...")
    
    # Test 1: Basic MQTT flow
    test1_result = test_mqtt_consultation_flow()
    
    # Test 2: Faculty response simulation
    test2_result = test_faculty_response_simulation()
    
    # Summary
    logger.info("\n📋 Test Summary:")
    logger.info(f"   MQTT Flow Test: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    logger.info(f"   Faculty Response Test: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    
    if test1_result and test2_result:
        logger.info("\n🎉 All tests PASSED! MQTT real-time updates should be working.")
        logger.info("   If the UI is still not updating, the issue is likely in the UI thread handling.")
    else:
        logger.error("\n💥 Some tests FAILED! Check MQTT broker connection and message routing.")

if __name__ == "__main__":
    main() 