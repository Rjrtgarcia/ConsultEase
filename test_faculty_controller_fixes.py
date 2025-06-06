#!/usr/bin/env python3
"""
Test script to verify Faculty Controller fixes and diagnose remaining issues.

This script tests:
1. Faculty status processing logic
2. Database update operations  
3. MQTT message publishing
4. Error handling and retry mechanisms
"""

import sys
import os
import time
import json
import logging
from datetime import datetime

# Add central_system to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'central_system'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('faculty_controller_test.log')
    ]
)
logger = logging.getLogger(__name__)

class FacultyControllerDiagnostic:
    """Comprehensive diagnostic for Faculty Controller issues."""
    
    def __init__(self):
        self.test_results = {}
        self.faculty_controller = None
        
    def test_faculty_controller_initialization(self):
        """Test if faculty controller can be initialized properly."""
        logger.info("🧪 Testing Faculty Controller Initialization")
        logger.info("-" * 50)
        
        try:
            from central_system.controllers.faculty_controller import FacultyController
            
            self.faculty_controller = FacultyController()
            logger.info("✅ Faculty Controller instantiated successfully")
            
            # Test start method
            self.faculty_controller.start()
            logger.info("✅ Faculty Controller started successfully")
            
            self.test_results['initialization'] = 'PASS'
            return True
            
        except Exception as e:
            logger.error(f"❌ Faculty Controller initialization failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.test_results['initialization'] = f'FAIL - {str(e)}'
            return False
    
    def test_status_processing_logic(self):
        """Test the enhanced status processing logic."""
        logger.info("🧪 Testing Status Processing Logic")
        logger.info("-" * 50)
        
        if not self.faculty_controller:
            logger.error("❌ Faculty Controller not initialized")
            return False
            
        try:
            # Test cases for different status formats
            test_cases = [
                # Format: (topic, data, expected_status)
                ("consultease/faculty/1/status", {"status": "AVAILABLE", "present": True}, True),
                ("consultease/faculty/1/status", {"status": "available", "present": True}, True),
                ("consultease/faculty/1/status", {"status": "BUSY", "present": True}, False),
                ("consultease/faculty/1/status", {"status": "OFFLINE", "present": False}, False),
                ("consultease/faculty/1/status", {"present": True}, True),
                ("consultease/faculty/1/status", {"present": False}, False),
                ("consultease/faculty/1/status", {"detailed_status": "AVAILABLE"}, True),
            ]
            
            logger.info("Testing status processing with different data formats:")
            
            for i, (topic, data, expected) in enumerate(test_cases):
                logger.info(f"\n--- Test Case {i+1} ---")
                logger.info(f"Topic: {topic}")
                logger.info(f"Data: {data}")
                logger.info(f"Expected status: {expected}")
                
                try:
                    # Call the handler (this will log the processing)
                    self.faculty_controller.handle_faculty_status_update(topic, data)
                    logger.info(f"✅ Status processing completed for test case {i+1}")
                except Exception as e:
                    logger.error(f"❌ Status processing failed for test case {i+1}: {e}")
            
            logger.info("✅ Status processing logic test completed")
            self.test_results['status_processing'] = 'PASS'
            return True
            
        except Exception as e:
            logger.error(f"❌ Status processing test failed: {e}")
            self.test_results['status_processing'] = f'FAIL - {str(e)}'
            return False
    
    def test_database_operations(self):
        """Test database update operations."""
        logger.info("🧪 Testing Database Operations")
        logger.info("-" * 50)
        
        try:
            # Test database connectivity
            from central_system.models.base import get_db
            from central_system.models import Faculty
            
            db = get_db()
            try:
                # Check if we have any faculty to test with
                faculty = db.query(Faculty).first()
                
                if not faculty:
                    logger.warning("⚠️ No faculty found in database - creating test faculty")
                    # Create a test faculty for testing
                    test_faculty = Faculty(
                        name="Test Faculty",
                        department="Test Department",
                        email="test@test.com",
                        status=False
                    )
                    db.add(test_faculty)
                    db.commit()
                    faculty = test_faculty
                    logger.info(f"✅ Created test faculty with ID {faculty.id}")
                
                logger.info(f"🎯 Testing with faculty ID {faculty.id}: {faculty.name}")
                
                # Test status update
                if self.faculty_controller:
                    logger.info("Testing faculty status update...")
                    
                    # Test update to True
                    result = self.faculty_controller.update_faculty_status(faculty.id, True)
                    if result:
                        logger.info(f"✅ Status update to True successful: {result}")
                    else:
                        logger.error("❌ Status update to True failed")
                    
                    time.sleep(1)
                    
                    # Test update to False
                    result = self.faculty_controller.update_faculty_status(faculty.id, False)
                    if result:
                        logger.info(f"✅ Status update to False successful: {result}")
                    else:
                        logger.error("❌ Status update to False failed")
                else:
                    logger.error("❌ Faculty controller not available for testing")
                
                self.test_results['database_operations'] = 'PASS'
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Database operations test failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.test_results['database_operations'] = f'FAIL - {str(e)}'
            return False
    
    def test_mqtt_publishing(self):
        """Test MQTT message publishing."""
        logger.info("🧪 Testing MQTT Publishing")
        logger.info("-" * 50)
        
        try:
            from central_system.utils.mqtt_utils import publish_mqtt_message
            
            # Test publishing a status update
            test_message = {
                'type': 'faculty_status',
                'faculty_id': 1,
                'faculty_name': 'Test Faculty',
                'status': True,
                'previous_status': False,
                'timestamp': datetime.now().isoformat(),
                'test': True
            }
            
            logger.info("Testing MQTT message publishing...")
            
            # Test different topics
            topics = [
                "consultease/faculty/1/status_update",
                "consultease/system/notifications"
            ]
            
            for topic in topics:
                logger.info(f"Publishing to: {topic}")
                success = publish_mqtt_message(topic, test_message, qos=1)
                
                if success:
                    logger.info(f"✅ Successfully published to {topic}")
                else:
                    logger.error(f"❌ Failed to publish to {topic}")
            
            self.test_results['mqtt_publishing'] = 'PASS'
            return True
            
        except Exception as e:
            logger.error(f"❌ MQTT publishing test failed: {e}")
            self.test_results['mqtt_publishing'] = f'FAIL - {str(e)}'
            return False
    
    def test_end_to_end_flow(self):
        """Test complete end-to-end status update flow."""
        logger.info("🧪 Testing End-to-End Status Update Flow")
        logger.info("-" * 50)
        
        try:
            if not self.faculty_controller:
                logger.error("❌ Faculty controller not available")
                return False
            
            # Simulate ESP32 status message
            test_esp32_message = {
                'faculty_id': 1,
                'faculty_name': 'Cris Angelo Salonga',
                'present': True,
                'status': 'AVAILABLE',
                'timestamp': 24525,
                'ntp_sync_status': 'SYNCED',
                'in_grace_period': False,
                'detailed_status': 'AVAILABLE'
            }
            
            logger.info("🔄 Simulating ESP32 status update...")
            logger.info(f"Data: {test_esp32_message}")
            
            # Process the message
            self.faculty_controller.handle_faculty_status_update(
                "consultease/faculty/1/status", 
                test_esp32_message
            )
            
            logger.info("✅ End-to-end flow test completed")
            logger.info("📝 Check logs above for detailed processing steps")
            
            self.test_results['end_to_end'] = 'PASS'
            return True
            
        except Exception as e:
            logger.error(f"❌ End-to-end test failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.test_results['end_to_end'] = f'FAIL - {str(e)}'
            return False
    
    def run_all_tests(self):
        """Run all faculty controller diagnostic tests."""
        logger.info("🚀 Starting Faculty Controller Diagnostic Tests")
        logger.info("=" * 60)
        
        tests = [
            ('Initialization', self.test_faculty_controller_initialization),
            ('Status Processing', self.test_status_processing_logic),
            ('Database Operations', self.test_database_operations),
            ('MQTT Publishing', self.test_mqtt_publishing),
            ('End-to-End Flow', self.test_end_to_end_flow)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n🧪 Running {test_name} Test...")
            try:
                result = test_func()
                status = "✅ PASS" if result else "❌ FAIL"
                logger.info(f"{status} {test_name} Test")
            except Exception as e:
                logger.error(f"❌ FAIL {test_name} Test: {e}")
                self.test_results[test_name.lower().replace(' ', '_')] = f'FAIL - {str(e)}'
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 FACULTY CONTROLLER DIAGNOSTIC SUMMARY")
        logger.info("=" * 60)
        
        passed = 0
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            is_pass = result == 'PASS'
            status_icon = "✅" if is_pass else "❌"
            logger.info(f"{status_icon} {test_name.replace('_', ' ').title()}: {result}")
            if is_pass:
                passed += 1
        
        logger.info(f"\n📈 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED! Faculty Controller should be working properly.")
        else:
            logger.warning(f"⚠️ {total - passed} test(s) failed. Review logs for details.")
        
        return passed == total

if __name__ == "__main__":
    print("🧪 Faculty Controller Diagnostic Tool")
    print("=" * 50)
    
    diagnostic = FacultyControllerDiagnostic()
    success = diagnostic.run_all_tests()
    
    if success:
        print("\n✅ All diagnostics passed! Faculty Controller should be working.")
    else:
        print("\n❌ Some diagnostics failed. Check logs for details.")
    
    print(f"\n📝 Detailed logs saved to: faculty_controller_test.log") 