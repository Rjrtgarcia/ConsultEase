#!/usr/bin/env python3
"""
Debug script to test MQTT handler registration and message reception
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
    level=logging.DEBUG,  # Set to DEBUG to see all logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_handler_1(topic, data):
    """Test handler 1"""
    logger.info(f"🔥 HANDLER 1 CALLED - Topic: {topic}, Data: {data}")

def test_handler_2(topic, data):
    """Test handler 2"""
    logger.info(f"🔥 HANDLER 2 CALLED - Topic: {topic}, Data: {data}")

def debug_mqtt_handlers():
    """Debug MQTT handler registration and message reception"""
    logger.info("🧪 Starting MQTT handlers debug test...")
    
    try:
        # Import MQTT service
        from central_system.services.async_mqtt_service import get_async_mqtt_service
        from central_system.utils.mqtt_utils import subscribe_to_topic, publish_mqtt_message
        
        # Start MQTT service
        mqtt_service = get_async_mqtt_service()
        logger.info(f"📡 MQTT service initialized: {mqtt_service}")
        
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
        
        logger.info("✅ Connected to MQTT broker")
        
        # Register test handlers using subscribe_to_topic
        logger.info("📝 Registering test handlers...")
        
        subscribe_to_topic("consultease/faculty/+/status", test_handler_1)
        subscribe_to_topic("consultease/faculty/+/status", test_handler_2)
        subscribe_to_topic("test/debug", test_handler_1)
        
        # Wait a bit for subscriptions to be processed
        time.sleep(3)
        
        # Check registered handlers
        logger.info(f"📋 Registered message handlers: {dict(mqtt_service.message_handlers)}")
        
        # Test publishing messages
        test_messages = [
            {
                "topic": "consultease/faculty/1/status",
                "payload": {
                    "faculty_id": 1,
                    "status": "AVAILABLE",
                    "present": True,
                    "timestamp": time.time()
                },
                "description": "Faculty 1 status update"
            },
            {
                "topic": "test/debug",
                "payload": {
                    "message": "Debug test message",
                    "timestamp": time.time()
                },
                "description": "Debug test message"
            }
        ]
        
        for i, test_msg in enumerate(test_messages, 1):
            logger.info(f"\n🚀 Publishing test message {i}: {test_msg['description']}")
            logger.info(f"   Topic: {test_msg['topic']}")
            logger.info(f"   Payload: {json.dumps(test_msg['payload'], indent=2)}")
            
            success = publish_mqtt_message(
                test_msg['topic'],
                test_msg['payload'],
                qos=1
            )
            
            if success:
                logger.info("   ✅ Message published successfully")
            else:
                logger.error("   ❌ Failed to publish message")
            
            # Wait for message processing
            time.sleep(2)
        
        # Keep running for a bit to see responses
        logger.info("\n⏳ Waiting 10 seconds for message processing...")
        time.sleep(10)
        
        # Get service stats
        stats = mqtt_service.get_stats()
        logger.info(f"\n📊 MQTT Service Stats: {json.dumps(stats, indent=2)}")
        
        # Stop MQTT service
        mqtt_service.stop()
        logger.info("🛑 MQTT service stopped")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Debug test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        debug_mqtt_handlers()
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 