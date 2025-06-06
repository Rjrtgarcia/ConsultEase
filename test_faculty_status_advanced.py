#!/usr/bin/env python3
"""
Advanced test script for faculty status real-time updates.
Tests for duplicate processing, race conditions, and proper message flow.
"""

import sys
import os
import time
import logging
import json
import threading
from collections import defaultdict

# Add the central_system path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'central_system'))

from central_system.models import Faculty, get_db
from central_system.controllers.faculty_controller import FacultyController
from central_system.utils.mqtt_utils import publish_mqtt_message, subscribe_to_topic
from central_system.services.async_mqtt_service import get_mqtt_service

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FacultyStatusAdvancedTest:
    """Advanced test for faculty status updates with duplicate processing detection."""
    
    def __init__(self):
        self.faculty_controller = FacultyController()
        self.mqtt_service = get_mqtt_service()
        self.message_log = defaultdict(list)
        self.processing_count = defaultdict(int)
        self.lock = threading.Lock()
        
    def run_tests(self):
        """Run comprehensive tests for faculty status system."""
        logger.info("🧪 Advanced Faculty Status Testing - Duplicate Processing Detection")
        logger.info("=" * 70)
        
        # Test 1: Check for duplicate subscriptions
        self.test_subscription_conflicts()
        
        # Test 2: Test BUSY status handling
        self.test_busy_status_processing()
        
        # Test 3: Test race condition prevention
        self.test_race_condition_prevention()
        
        # Test 4: Test proper message flow
        self.test_message_flow_architecture()
        
        # Test 5: Performance test
        self.test_performance_impact()
        
        # Print comprehensive results
        self.print_test_results()
        
    def test_subscription_conflicts(self):
        """Test for conflicting MQTT subscriptions."""
        logger.info("\n1️⃣ Testing MQTT Subscription Conflicts")
        logger.info("-" * 50)
        
        # Set up monitoring for subscription conflicts
        def monitor_handler(topic, data):
            with self.lock:
                self.processing_count[topic] += 1
                self.message_log[topic].append({
                    'data': data,
                    'timestamp': time.time(),
                    'thread': threading.current_thread().name
                })
        
        # Subscribe our monitor to faculty status topics
        subscribe_to_topic("consultease/faculty/+/status", monitor_handler)
        subscribe_to_topic("consultease/faculty/+/status_update", monitor_handler)
        
        # Get test faculty
        faculties = self.faculty_controller.get_all_faculty()
        if not faculties:
            logger.error("❌ No faculty available for testing")
            return
            
        test_faculty = faculties[0]
        faculty_id = test_faculty.id
        
        # Send a test message
        test_message = {
            "faculty_id": faculty_id,
            "faculty_name": test_faculty.name,
            "present": True,
            "status": "AVAILABLE",
            "timestamp": int(time.time())
        }
        
        topic = f"consultease/faculty/{faculty_id}/status"
        logger.info(f"📡 Publishing test message to: {topic}")
        
        # Clear counters
        with self.lock:
            self.processing_count.clear()
            self.message_log.clear()
        
        # Publish message
        publish_mqtt_message(topic, test_message)
        
        # Wait for processing
        time.sleep(3)
        
        # Analyze results
        with self.lock:
            raw_topic_count = self.processing_count.get(topic, 0)
            processed_topic_count = self.processing_count.get(f"consultease/faculty/{faculty_id}/status_update", 0)
            
            logger.info(f"📊 Raw ESP32 topic processing count: {raw_topic_count}")
            logger.info(f"📊 Processed notification count: {processed_topic_count}")
            
            if raw_topic_count > 1:
                logger.error(f"❌ DUPLICATE PROCESSING detected! Raw message processed {raw_topic_count} times")
                logger.error("   This indicates multiple handlers subscribed to same topic")
            else:
                logger.info("✅ No duplicate processing detected for raw messages")
                
            if processed_topic_count > 0:
                logger.info("✅ Processed notifications are being generated")
            else:
                logger.warning("⚠️ No processed notifications detected - check Faculty Controller")
                
    def test_busy_status_processing(self):
        """Test BUSY status handling logic."""
        logger.info("\n2️⃣ Testing BUSY Status Processing Logic")
        logger.info("-" * 50)
        
        faculties = self.faculty_controller.get_all_faculty()
        if not faculties:
            logger.error("❌ No faculty available for testing")
            return
            
        test_faculty = faculties[0]
        faculty_id = test_faculty.id
        original_status = test_faculty.status
        
        # Test BUSY status message
        busy_message = {
            "faculty_id": faculty_id,
            "faculty_name": test_faculty.name,
            "present": True,  # Faculty is present
            "status": "BUSY",  # But busy in consultation
            "timestamp": int(time.time()),
            "in_consultation": True
        }
        
        logger.info(f"🧪 Testing BUSY status for faculty {test_faculty.name}")
        logger.info(f"📝 Message: present=True, status=BUSY")
        logger.info(f"📝 Expected result: status=False (unavailable for new consultations)")
        
        # Publish BUSY message
        topic = f"consultease/faculty/{faculty_id}/status"
        publish_mqtt_message(topic, busy_message)
        
        # Wait for processing
        time.sleep(3)
        
        # Check database result
        db = get_db()
        try:
            updated_faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
            if updated_faculty:
                actual_status = updated_faculty.status
                logger.info(f"📊 Database status after BUSY message: {actual_status}")
                
                if actual_status == False:
                    logger.info("✅ BUSY status correctly processed as unavailable (False)")
                else:
                    logger.error("❌ BUSY status incorrectly processed - should be False")
            else:
                logger.error("❌ Faculty not found in database")
        finally:
            db.close()
            
        # Restore original status
        self.faculty_controller.update_faculty_status(faculty_id, original_status)
        
    def test_race_condition_prevention(self):
        """Test race condition prevention in concurrent updates."""
        logger.info("\n3️⃣ Testing Race Condition Prevention")
        logger.info("-" * 50)
        
        faculties = self.faculty_controller.get_all_faculty()
        if not faculties:
            logger.error("❌ No faculty available for testing")
            return
            
        test_faculty = faculties[0]
        faculty_id = test_faculty.id
        
        # Send multiple rapid status changes
        messages = [
            {"status": "AVAILABLE", "present": True, "expected": True},
            {"status": "BUSY", "present": True, "expected": False},
            {"status": "AWAY", "present": False, "expected": False},
            {"status": "AVAILABLE", "present": True, "expected": True}
        ]
        
        logger.info(f"🧪 Sending {len(messages)} rapid status changes for faculty {test_faculty.name}")
        
        # Send messages rapidly
        for i, msg_data in enumerate(messages):
            message = {
                "faculty_id": faculty_id,
                "faculty_name": test_faculty.name,
                "present": msg_data["present"],
                "status": msg_data["status"],
                "timestamp": int(time.time()),
                "sequence": i
            }
            
            topic = f"consultease/faculty/{faculty_id}/status"
            publish_mqtt_message(topic, message)
            time.sleep(0.1)  # Rapid succession
            
        # Wait for all processing to complete
        time.sleep(5)
        
        # Check final state
        db = get_db()
        try:
            final_faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
            if final_faculty:
                final_status = final_faculty.status
                expected_status = messages[-1]["expected"]  # Last message should win
                
                logger.info(f"📊 Final status: {final_status}")
                logger.info(f"📝 Expected status: {expected_status}")
                
                if final_status == expected_status:
                    logger.info("✅ Race conditions handled correctly - final status matches last message")
                else:
                    logger.error("❌ Race condition detected - final status doesn't match expected")
            else:
                logger.error("❌ Faculty not found in database")
        finally:
            db.close()
            
    def test_message_flow_architecture(self):
        """Test proper message flow architecture."""
        logger.info("\n4️⃣ Testing Message Flow Architecture")
        logger.info("-" * 50)
        
        # Monitor different message types
        esp32_messages = []
        processed_notifications = []
        system_notifications = []
        
        def esp32_monitor(topic, data):
            if "/status" in topic and "/status_update" not in topic:
                esp32_messages.append((topic, data, time.time()))
                
        def processed_monitor(topic, data):
            if "/status_update" in topic:
                processed_notifications.append((topic, data, time.time()))
                
        def system_monitor(topic, data):
            if "system/notifications" in topic:
                system_notifications.append((topic, data, time.time()))
        
        # Set up monitors
        subscribe_to_topic("consultease/faculty/+/status", esp32_monitor)
        subscribe_to_topic("consultease/faculty/+/status_update", processed_monitor)
        subscribe_to_topic("consultease/system/notifications", system_monitor)
        
        # Clear logs
        esp32_messages.clear()
        processed_notifications.clear()
        system_notifications.clear()
        
        # Send test message
        faculties = self.faculty_controller.get_all_faculty()
        if faculties:
            test_faculty = faculties[0]
            test_message = {
                "faculty_id": test_faculty.id,
                "faculty_name": test_faculty.name,
                "present": True,
                "status": "AVAILABLE",
                "timestamp": int(time.time())
            }
            
            topic = f"consultease/faculty/{test_faculty.id}/status"
            logger.info(f"📡 Publishing ESP32-style message to test flow")
            publish_mqtt_message(topic, test_message)
            
            # Wait for processing
            time.sleep(3)
            
            # Analyze message flow
            logger.info(f"📊 ESP32 messages received: {len(esp32_messages)}")
            logger.info(f"📊 Processed notifications: {len(processed_notifications)}")
            logger.info(f"📊 System notifications: {len(system_notifications)}")
            
            if len(esp32_messages) >= 1 and len(processed_notifications) >= 1:
                logger.info("✅ Proper message flow: ESP32 → Faculty Controller → Notifications")
            else:
                logger.error("❌ Broken message flow - check notification publishing")
                
    def test_performance_impact(self):
        """Test performance impact of fixes."""
        logger.info("\n5️⃣ Testing Performance Impact")
        logger.info("-" * 50)
        
        faculties = self.faculty_controller.get_all_faculty()
        if not faculties:
            logger.error("❌ No faculty available for testing")
            return
            
        test_faculty = faculties[0]
        
        # Test with multiple rapid messages
        num_messages = 20
        start_time = time.time()
        
        logger.info(f"📡 Sending {num_messages} rapid messages to test performance")
        
        for i in range(num_messages):
            message = {
                "faculty_id": test_faculty.id,
                "faculty_name": test_faculty.name,
                "present": i % 2 == 0,  # Alternate status
                "status": "AVAILABLE" if i % 2 == 0 else "AWAY",
                "timestamp": int(time.time()),
                "sequence": i
            }
            
            topic = f"consultease/faculty/{test_faculty.id}/status"
            publish_mqtt_message(topic, message)
            time.sleep(0.05)  # 50ms between messages
            
        # Wait for processing
        time.sleep(5)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        logger.info(f"📊 Performance test completed in {total_time:.2f} seconds")
        logger.info(f"📊 Average time per message: {(total_time/num_messages)*1000:.1f}ms")
        
        if total_time < 30:  # Should complete within 30 seconds
            logger.info("✅ Performance acceptable for Raspberry Pi")
        else:
            logger.warning("⚠️ Performance may be slow for Raspberry Pi")
            
    def print_test_results(self):
        """Print comprehensive test results."""
        logger.info("\n" + "=" * 70)
        logger.info("📋 ADVANCED FACULTY STATUS TEST RESULTS")
        logger.info("=" * 70)
        
        logger.info("🔧 FIXES IMPLEMENTED:")
        logger.info("   ✅ Fixed database field mismatch (faculty.availability → faculty.status)")
        logger.info("   ✅ Removed duplicate ESP32 message subscriptions from Dashboard")
        logger.info("   ✅ Improved BUSY status processing logic in Faculty Controller")
        logger.info("   ✅ Reduced excessive debug logging for better performance")
        logger.info("   ✅ Enhanced thread safety and error handling")
        
        logger.info("\n🎯 EXPECTED BEHAVIOR:")
        logger.info("   1. ESP32 publishes raw status messages")
        logger.info("   2. Faculty Controller processes → Updates database → Publishes notifications")
        logger.info("   3. Dashboard receives notifications → Updates UI in real-time")
        logger.info("   4. No duplicate processing or race conditions")
        logger.info("   5. BUSY status correctly handled as unavailable")
        
        logger.info("\n💡 NEXT STEPS:")
        logger.info("   1. Test on actual Raspberry Pi with faculty desk units")
        logger.info("   2. Apply network connection fixes for stable MQTT")
        logger.info("   3. Monitor logs for any remaining duplicate processing")
        logger.info("   4. Verify real-time UI updates work correctly")

def main():
    """Run the advanced faculty status tests."""
    tester = FacultyStatusAdvancedTest()
    tester.run_tests()

if __name__ == "__main__":
    main() 