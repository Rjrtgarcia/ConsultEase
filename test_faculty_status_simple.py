#!/usr/bin/env python3
"""
Simple test script for faculty status real-time updates.
Simulates ESP32 status messages and verifies database updates.
"""

import sys
import os
import time
import logging
import json

# Add the central_system path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'central_system'))

from central_system.models import Faculty, get_db
from central_system.controllers.faculty_controller import FacultyController
from central_system.utils.mqtt_utils import publish_mqtt_message

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_faculty_status_updates():
    """Test faculty status updates with ESP32-style MQTT messages."""
    
    logger.info("🧪 Testing Faculty Status Real-Time Updates")
    logger.info("=" * 50)
    
    # Initialize faculty controller
    faculty_controller = FacultyController()
    
    # Get first faculty member for testing
    faculties = faculty_controller.get_all_faculty()
    if not faculties:
        logger.error("❌ No faculty members found in database")
        return
    
    test_faculty = faculties[0]
    faculty_id = test_faculty.id
    faculty_name = test_faculty.name
    original_status = test_faculty.status
    
    logger.info(f"🧪 Testing with faculty: {faculty_name} (ID: {faculty_id})")
    logger.info(f"📝 Original status: {'Available' if original_status else 'Unavailable'}")
    
    # Test messages simulating ESP32 desk unit
    test_messages = [
        {
            "topic": f"consultease/faculty/{faculty_id}/status",
            "payload": {
                "faculty_id": faculty_id,
                "faculty_name": faculty_name,
                "present": True,
                "status": "AVAILABLE",
                "timestamp": int(time.time()),
                "ntp_sync_status": "SYNCED"
            },
            "expected_status": True,
            "description": "ESP32 Available Status"
        },
        {
            "topic": f"consultease/faculty/{faculty_id}/status",
            "payload": {
                "faculty_id": faculty_id,
                "faculty_name": faculty_name,
                "present": False,
                "status": "AWAY",
                "timestamp": int(time.time()),
                "grace_period_active": False
            },
            "expected_status": False,
            "description": "ESP32 Away Status"
        },
        {
            "topic": f"consultease/faculty/{faculty_id}/status",
            "payload": {
                "faculty_id": faculty_id,
                "faculty_name": faculty_name,
                "present": True,
                "status": "BUSY",
                "timestamp": int(time.time()),
                "in_consultation": True
            },
            "expected_status": False,  # Busy = not available for new consultations
            "description": "ESP32 Busy Status"
        }
    ]
    
    success_count = 0
    total_tests = len(test_messages)
    
    for i, test_case in enumerate(test_messages, 1):
        logger.info(f"\n📡 Test {i}/{total_tests}: {test_case['description']}")
        logger.info(f"   Topic: {test_case['topic']}")
        logger.info(f"   Payload: {json.dumps(test_case['payload'], indent=2)}")
        logger.info(f"   Expected Status: {'Available' if test_case['expected_status'] else 'Unavailable'}")
        
        try:
            # Publish MQTT message
            result = publish_mqtt_message(test_case['topic'], test_case['payload'])
            
            if result:
                logger.info(f"   ✅ Message published successfully")
                
                # Wait for message processing
                time.sleep(3)
                
                # Check database for status change
                db = get_db()
                try:
                    updated_faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
                    if updated_faculty:
                        actual_status = updated_faculty.status
                        expected_status = test_case['expected_status']
                        
                        logger.info(f"   📊 Database status: {'Available' if actual_status else 'Unavailable'}")
                        logger.info(f"   📊 Last seen: {updated_faculty.last_seen}")
                        
                        if actual_status == expected_status:
                            logger.info(f"   ✅ Status update successful!")
                            success_count += 1
                        else:
                            logger.error(f"   ❌ Status mismatch! Expected: {expected_status}, Got: {actual_status}")
                    else:
                        logger.error(f"   ❌ Faculty not found in database")
                finally:
                    db.close()
            else:
                logger.error(f"   ❌ Message publish failed")
                
        except Exception as e:
            logger.error(f"   ❌ Test error: {e}")
        
        # Small delay between tests
        time.sleep(2)
    
    # Restore original status
    logger.info(f"\n🔄 Restoring original status: {'Available' if original_status else 'Unavailable'}")
    try:
        restore_result = faculty_controller.update_faculty_status(faculty_id, original_status)
        if restore_result:
            logger.info("✅ Original status restored")
        else:
            logger.warning("⚠️ Failed to restore original status")
    except Exception as e:
        logger.error(f"❌ Error restoring status: {e}")
    
    # Print test summary
    logger.info("\n" + "=" * 50)
    logger.info("📋 TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"🧪 Total Tests: {total_tests}")
    logger.info(f"✅ Passed: {success_count}")
    logger.info(f"❌ Failed: {total_tests - success_count}")
    
    if success_count == total_tests:
        logger.info("🎉 All tests passed! Faculty status real-time updates are working correctly.")
    else:
        logger.warning("⚠️ Some tests failed. Faculty status updates may have issues.")
        logger.info("\n💡 Troubleshooting tips:")
        logger.info("   - Check MQTT broker connectivity")
        logger.info("   - Verify faculty controller MQTT subscriptions")
        logger.info("   - Check database update logic in MQTT router")
        logger.info("   - Ensure faculty desk unit WiFi/MQTT connections are stable")

def main():
    """Run the faculty status test."""
    test_faculty_status_updates()

if __name__ == "__main__":
    main() 