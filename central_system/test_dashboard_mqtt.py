#!/usr/bin/env python3
"""
Test script to simulate faculty status updates and verify dashboard MQTT reception.
"""

import json
import time
import logging
from utils.mqtt_utils import publish_mqtt_message

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_faculty_status_updates():
    """Test faculty status updates to verify dashboard reception."""
    
    logger.info("🧪 Testing faculty status updates...")
    
    # Simulate ESP32 status update (direct format)
    esp32_status = {
        "faculty_id": 1,
        "faculty_name": "Cris Angelo Salonga",
        "present": True,
        "status": "AVAILABLE",
        "timestamp": int(time.time())
    }
    
    # Test 1: Publish to direct ESP32 topic
    topic1 = "consultease/faculty/1/status"
    logger.info(f"📡 Publishing to {topic1}: {esp32_status}")
    result1 = publish_mqtt_message(topic1, esp32_status)
    logger.info(f"   Result: {result1}")
    
    time.sleep(2)
    
    # Test 2: Publish processed status update
    processed_status = {
        "type": "faculty_status",
        "faculty_id": 1,
        "faculty_name": "Cris Angelo Salonga", 
        "status": True,
        "previous_status": False,
        "timestamp": int(time.time())
    }
    
    topic2 = "consultease/faculty/1/status_update"
    logger.info(f"📡 Publishing to {topic2}: {processed_status}")
    result2 = publish_mqtt_message(topic2, processed_status)
    logger.info(f"   Result: {result2}")
    
    time.sleep(2)
    
    # Test 3: System notification
    system_notification = {
        "type": "faculty_status",
        "faculty_id": 1,
        "faculty_name": "Cris Angelo Salonga",
        "status": True,
        "timestamp": int(time.time())
    }
    
    topic3 = "consultease/system/notifications"
    logger.info(f"📡 Publishing to {topic3}: {system_notification}")
    result3 = publish_mqtt_message(topic3, system_notification)
    logger.info(f"   Result: {result3}")
    
    # Test 4: Change to busy status
    time.sleep(3)
    busy_status = {
        "faculty_id": 1,
        "faculty_name": "Cris Angelo Salonga",
        "present": True,
        "status": "BUSY",
        "timestamp": int(time.time())
    }
    
    logger.info(f"📡 Publishing BUSY status to {topic1}: {busy_status}")
    result4 = publish_mqtt_message(topic1, busy_status)
    logger.info(f"   Result: {result4}")
    
    # Test 5: Change to away status
    time.sleep(3)
    away_status = {
        "faculty_id": 1,
        "faculty_name": "Cris Angelo Salonga",
        "present": False,
        "status": "AWAY",
        "timestamp": int(time.time())
    }
    
    logger.info(f"📡 Publishing AWAY status to {topic1}: {away_status}")
    result5 = publish_mqtt_message(topic1, away_status)
    logger.info(f"   Result: {result5}")
    
    logger.info("✅ Faculty status update tests completed!")
    logger.info("📊 Check the dashboard for real-time updates...")

if __name__ == "__main__":
    test_faculty_status_updates() 