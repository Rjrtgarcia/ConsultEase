#!/usr/bin/env python3
"""
Test script to verify dashboard UI loop fix is working
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

def test_dashboard_ui_loop_fix():
    """Test that the dashboard UI loop fix is working correctly"""
    logger.info("🧪 Testing dashboard UI loop fix...")
    
    try:
        # Import required modules
        from central_system.services.async_mqtt_service import get_async_mqtt_service
        from central_system.utils.mqtt_utils import publish_mqtt_message
        from central_system.models.base import get_db
        from central_system.models.faculty import Faculty
        
        # Start MQTT service
        logger.info("📡 Starting MQTT service...")
        mqtt_service = get_async_mqtt_service()
        mqtt_service.start()
        mqtt_service.connect()
        
        # Wait for connection
        timeout = 15
        start_time = time.time()
        
        while not mqtt_service.is_connected and (time.time() - start_time) < timeout:
            time.sleep(0.5)
        
        if not mqtt_service.is_connected:
            logger.error("❌ Failed to connect to MQTT broker")
            return False
        
        logger.info("✅ MQTT service connected")
        
        # Get a test faculty member
        with get_db() as db:
            faculty = db.query(Faculty).first()
            if not faculty:
                logger.warning("⚠️ No faculty found in database")
                return False
            
            test_faculty_id = faculty.id
            logger.info(f"📝 Using faculty ID: {test_faculty_id} ({faculty.name})")
        
        # Test rapid status changes to see if UI loop occurs
        test_count = 5
        logger.info(f"🚀 Publishing {test_count} rapid status changes...")
        
        for i in range(test_count):
            # Alternate between available and away
            status = "AVAILABLE" if i % 2 == 0 else "AWAY"
            present = i % 2 == 0
            
            message = {
                "faculty_id": test_faculty_id,
                "status": status,
                "present": present,
                "timestamp": time.time(),
                "test_sequence": i + 1
            }
            
            logger.info(f"   📤 Test {i+1}/{test_count}: {status}")
            
            # Publish to status topic
            success = publish_mqtt_message(
                f"consultease/faculty/{test_faculty_id}/status",
                message,
                qos=1
            )
            
            if success:
                logger.info(f"   ✅ Published successfully")
            else:
                logger.error(f"   ❌ Failed to publish")
            
            # Short delay between messages
            time.sleep(1)
        
        # Wait for processing and check statistics
        logger.info("⏳ Waiting 10 seconds for all messages to be processed...")
        time.sleep(10)
        
        # Get MQTT service stats
        stats = mqtt_service.get_stats()
        logger.info(f"\n📊 MQTT Service Stats:")
        logger.info(f"   Messages received: {stats.get('messages_received', 0)}")
        logger.info(f"   Messages published: {stats.get('messages_published', 0)}")
        logger.info(f"   Connected: {stats.get('connected', False)}")
        
        # Check final faculty status
        with get_db() as db:
            faculty_final = db.query(Faculty).filter(Faculty.id == test_faculty_id).first()
            if faculty_final:
                logger.info(f"🏁 Final faculty status: {faculty_final.status}")
        
        logger.info("\n✅ Dashboard UI loop test completed!")
        logger.info("📝 Check the console output above for any signs of infinite loops")
        logger.info("📝 If you see repeated 'request_ui_refresh' or 'Populating faculty grid' messages")
        logger.info("📝 after the test, then the fix needs more work.")
        
        # Stop MQTT service
        mqtt_service.stop()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = test_dashboard_ui_loop_fix()
        if success:
            print("\n✅ UI LOOP TEST COMPLETED - Check logs for infinite loops")
        else:
            print("\n❌ UI LOOP TEST FAILED")
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 