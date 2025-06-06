#!/usr/bin/env python3
"""
Test script to verify faculty availability system is working correctly
"""

import os
import sys
import time
import json
import logging

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_faculty_availability_system():
    """Test the complete faculty availability system"""
    logger.info("🧪 Starting comprehensive faculty availability test...")
    
    try:
        # Import required modules
        from central_system.services.async_mqtt_service import get_async_mqtt_service
        from central_system.controllers.faculty_controller import FacultyController
        from central_system.utils.mqtt_utils import subscribe_to_topic, publish_mqtt_message
        from central_system.models.base import get_db
        from central_system.models.faculty import Faculty
        
        # Step 1: Start MQTT service
        logger.info("📡 Step 1: Starting MQTT service...")
        mqtt_service = get_async_mqtt_service()
        mqtt_service.start()
        mqtt_service.connect()
        
        # Wait for connection
        logger.info("⏳ Waiting for MQTT connection...")
        timeout = 15
        start_time = time.time()
        
        while not mqtt_service.is_connected and (time.time() - start_time) < timeout:
            time.sleep(0.5)
        
        if not mqtt_service.is_connected:
            logger.error("❌ Failed to connect to MQTT broker")
            return False
        
        logger.info("✅ MQTT service connected")
        
        # Step 2: Initialize faculty controller
        logger.info("👥 Step 2: Initializing faculty controller...")
        faculty_controller = FacultyController()
        faculty_controller.start()
        logger.info("✅ Faculty controller started")
        
        # Step 3: Wait for subscriptions to be processed
        logger.info("⏳ Step 3: Waiting for subscriptions to be processed...")
        time.sleep(3)
        
        # Step 4: Check what topics are subscribed
        logger.info(f"📋 Step 4: Current MQTT subscriptions: {list(mqtt_service.message_handlers.keys())}")
        for topic, handlers in mqtt_service.message_handlers.items():
            logger.info(f"   Topic: '{topic}' - Handlers: {len(handlers)}")
            for i, handler in enumerate(handlers):
                handler_name = getattr(handler, '__name__', str(handler))
                logger.info(f"     Handler {i+1}: {handler_name}")
        
        # Step 5: Check faculty in database
        logger.info("💾 Step 5: Checking faculty in database...")
        with get_db() as db:
            faculties = db.query(Faculty).all()
            logger.info(f"   Found {len(faculties)} faculty members:")
            for faculty in faculties:
                logger.info(f"     Faculty ID {faculty.id}: {faculty.name} - Status: {faculty.status}")
        
        if not faculties:
            logger.warning("⚠️ No faculty members found in database. Creating test faculty...")
            # Create a test faculty member
            with get_db() as db:
                test_faculty = Faculty(
                    name="Dr. Test Faculty",
                    department="Computer Science",
                    email="test.faculty@consultease.com",
                    ble_id="00:11:22:33:44:55",
                    status=False  # Initially unavailable
                )
                db.add(test_faculty)
                db.commit()
                test_faculty_id = test_faculty.id
                logger.info(f"✅ Created test faculty with ID: {test_faculty_id}")
        else:
            test_faculty_id = faculties[0].id
            logger.info(f"📝 Using existing faculty ID: {test_faculty_id}")
        
        # Step 6: Test MQTT status updates
        test_messages = [
            {
                "topic": f"consultease/faculty/{test_faculty_id}/status",
                "payload": {
                    "faculty_id": test_faculty_id,
                    "status": "AVAILABLE",
                    "present": True,
                    "timestamp": time.time()
                },
                "expected_status": True,
                "description": "Make faculty available"
            },
            {
                "topic": f"consultease/faculty/{test_faculty_id}/status",
                "payload": {
                    "faculty_id": test_faculty_id,
                    "status": "AWAY",
                    "present": False,
                    "timestamp": time.time()
                },
                "expected_status": False,
                "description": "Make faculty unavailable"
            },
            {
                "topic": f"consultease/faculty/{test_faculty_id}/mac_status",
                "payload": {
                    "faculty_id": test_faculty_id,
                    "status": "PRESENT",
                    "mac_address": "00:11:22:33:44:55",
                    "timestamp": time.time()
                },
                "expected_status": True,
                "description": "Faculty presence detected via BLE"
            }
        ]
        
        for i, test_msg in enumerate(test_messages, 1):
            logger.info(f"\n🚀 Step {5+i}: {test_msg['description']}")
            logger.info(f"   Publishing to: {test_msg['topic']}")
            logger.info(f"   Payload: {json.dumps(test_msg['payload'], indent=2)}")
            
            # Get current status before update
            with get_db() as db:
                faculty_before = db.query(Faculty).filter(Faculty.id == test_faculty_id).first()
                status_before = faculty_before.status if faculty_before else None
                logger.info(f"   Status BEFORE: {status_before}")
            
            # Publish message
            success = publish_mqtt_message(
                test_msg['topic'],
                test_msg['payload'],
                qos=1
            )
            
            if success:
                logger.info("   ✅ Message published successfully")
            else:
                logger.error("   ❌ Failed to publish message")
                continue
            
            # Wait for processing
            logger.info("   ⏳ Waiting 3 seconds for message processing...")
            time.sleep(3)
            
            # Check if status was updated in database
            with get_db() as db:
                faculty_after = db.query(Faculty).filter(Faculty.id == test_faculty_id).first()
                status_after = faculty_after.status if faculty_after else None
                logger.info(f"   Status AFTER: {status_after}")
                
                if status_after == test_msg['expected_status']:
                    logger.info(f"   ✅ SUCCESS: Status updated correctly to {status_after}")
                else:
                    logger.error(f"   ❌ FAILURE: Expected {test_msg['expected_status']}, got {status_after}")
        
        # Step 9: Get final service stats
        stats = mqtt_service.get_stats()
        logger.info(f"\n📊 Final MQTT Service Stats:")
        logger.info(f"   Connected: {stats.get('connected', False)}")
        logger.info(f"   Messages received: {stats.get('messages_received', 0)}")
        logger.info(f"   Messages published: {stats.get('messages_published', 0)}")
        logger.info(f"   Publish errors: {stats.get('publish_errors', 0)}")
        
        # Stop MQTT service
        mqtt_service.stop()
        logger.info("🛑 MQTT service stopped")
        
        logger.info("\n🎉 Faculty availability test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = test_faculty_availability_system()
        if success:
            print("\n✅ ALL TESTS PASSED - Faculty availability system is working!")
        else:
            print("\n❌ TESTS FAILED - Please check the logs above")
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 