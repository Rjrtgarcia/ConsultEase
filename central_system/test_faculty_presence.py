#!/usr/bin/env python3
"""
Test script to verify faculty presence detection is working properly
"""

import os
import sys
import time
import json
import logging

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from central_system.utils.mqtt_utils import publish_mqtt_message, get_mqtt_service
from central_system.services.async_mqtt_service import get_async_mqtt_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_faculty_presence():
    """Test faculty presence detection"""
    logger.info("🧪 Starting faculty presence detection test...")
    
    # Start MQTT service
    mqtt_service = get_async_mqtt_service()
    mqtt_service.start()
    mqtt_service.connect()
    
    # Wait for connection
    logger.info("⏳ Waiting for MQTT connection...")
    timeout = 10
    start_time = time.time()
    
    while not mqtt_service.is_connected and (time.time() - start_time) < timeout:
        time.sleep(0.5)
    
    if not mqtt_service.is_connected:
        logger.error("❌ Failed to connect to MQTT broker")
        return False
    
    logger.info("✅ Connected to MQTT broker")
    
    # Wait a bit for subscriptions to be set up
    time.sleep(2)
    
    # Test faculty status messages
    test_cases = [
        {
            "topic": "consultease/faculty/1/status",
            "payload": {
                "faculty_id": 1,
                "status": "AVAILABLE",
                "present": True,
                "timestamp": time.time()
            },
            "description": "Faculty 1 becomes available"
        },
        {
            "topic": "consultease/faculty/1/mac_status", 
            "payload": {
                "status": "faculty_present",
                "mac": "aa:bb:cc:dd:ee:ff",
                "timestamp": time.time()
            },
            "description": "Faculty 1 MAC detected"
        },
        {
            "topic": "consultease/faculty/2/status",
            "payload": {
                "faculty_id": 2,
                "status": "BUSY",
                "present": True,
                "timestamp": time.time()
            },
            "description": "Faculty 2 becomes busy"
        },
        {
            "topic": "consultease/faculty/1/status",
            "payload": {
                "faculty_id": 1,
                "status": "AWAY",
                "present": False,
                "timestamp": time.time()
            },
            "description": "Faculty 1 goes away"
        }
    ]
    
    logger.info(f"🔄 Running {len(test_cases)} test cases...")
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n📨 Test {i}: {test_case['description']}")
        logger.info(f"   Topic: {test_case['topic']}")
        logger.info(f"   Payload: {json.dumps(test_case['payload'], indent=2)}")
        
        success = publish_mqtt_message(
            test_case['topic'],
            test_case['payload'],
            qos=1
        )
        
        if success:
            logger.info(f"   ✅ Message published successfully")
        else:
            logger.error(f"   ❌ Failed to publish message")
        
        # Wait between messages
        time.sleep(3)
    
    logger.info("\n🏁 Test completed. Check the logs for handler execution details.")
    
    # Keep running for a bit to see the responses
    logger.info("⏳ Waiting 10 seconds for message processing...")
    time.sleep(10)
    
    # Stop MQTT service
    mqtt_service.stop()
    logger.info("🛑 MQTT service stopped")
    
    return True

if __name__ == "__main__":
    try:
        test_faculty_presence()
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 