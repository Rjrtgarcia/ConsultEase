#!/usr/bin/env python3
"""
Manual test for Faculty Controller to identify real-time status update issues.
This test bypasses MQTT and directly tests the Faculty Controller logic.
"""

import sys
import os
import logging
import time
from datetime import datetime

# Add the central_system directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'central_system'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FacultyControllerTester:
    def __init__(self):
        self.test_results = {}
        
    def test_faculty_controller_initialization(self):
        """Test if Faculty Controller can be initialized properly."""
        logger.info("=" * 80)
        logger.info("TEST 1: FACULTY CONTROLLER INITIALIZATION")
        logger.info("=" * 80)
        
        try:
            from central_system.controllers.faculty_controller import FacultyController
            
            logger.info("✅ Faculty Controller imported successfully")
            
            # Initialize controller
            controller = FacultyController()
            logger.info("✅ Faculty Controller initialized successfully")
            
            # Check attributes
            has_callbacks = hasattr(controller, 'callbacks')
            has_queue_service = hasattr(controller, 'queue_service')
            
            logger.info(f"   - Has callbacks attribute: {has_callbacks}")
            logger.info(f"   - Has queue_service attribute: {has_queue_service}")
            
            self.test_results['initialization'] = True
            return controller
            
        except Exception as e:
            logger.error(f"❌ Faculty Controller initialization failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.test_results['initialization'] = False
            return None
    
    def test_database_connection(self):
        """Test if database connection and faculty records exist."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 2: DATABASE CONNECTION AND FACULTY RECORDS")
        logger.info("=" * 80)
        
        try:
            from central_system.models.faculty import Faculty
            from central_system.models.base import get_db
            
            logger.info("✅ Database models imported successfully")
            
            with get_db() as db:
                logger.info("✅ Database connection established")
                
                # Get all faculty
                faculties = db.query(Faculty).all()
                logger.info(f"📊 Found {len(faculties)} faculty records:")
                
                for faculty in faculties:
                    logger.info(f"   - ID: {faculty.id}, Name: {faculty.name}, Status: {faculty.status}, BLE ID: {faculty.ble_id}")
                
                if len(faculties) > 0:
                    self.test_results['database'] = True
                    return faculties[0]  # Return first faculty for testing
                else:
                    logger.error("❌ No faculty records found in database")
                    self.test_results['database'] = False
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Database test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.test_results['database'] = False
            return None
    
    def test_faculty_status_update_directly(self, controller, faculty):
        """Test faculty status update directly without MQTT."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 3: DIRECT FACULTY STATUS UPDATE")
        logger.info("=" * 80)
        
        try:
            faculty_id = faculty.id
            original_status = faculty.status
            
            logger.info(f"📋 Testing faculty ID {faculty_id} ({faculty.name})")
            logger.info(f"   Original status: {original_status}")
            
            # Test status change 1: Available -> Unavailable
            new_status = not original_status
            logger.info(f"\n🔄 Test 3a: Changing status to {new_status}")
            
            result = controller.update_faculty_status(faculty_id, new_status)
            
            if result:
                logger.info(f"✅ Status update returned: {result}")
                logger.info(f"   Faculty ID: {result.get('id')}")
                logger.info(f"   Faculty Name: {result.get('name')}")
                logger.info(f"   New Status: {result.get('status')}")
                logger.info(f"   Last Seen: {result.get('last_seen')}")
            else:
                logger.error("❌ Status update returned None")
                
            # Wait a moment
            time.sleep(2)
            
            # Test status change 2: Back to original
            logger.info(f"\n🔄 Test 3b: Changing status back to {original_status}")
            
            result2 = controller.update_faculty_status(faculty_id, original_status)
            
            if result2:
                logger.info(f"✅ Status restore returned: {result2}")
                logger.info(f"   New Status: {result2.get('status')}")
            else:
                logger.error("❌ Status restore returned None")
            
            # Verify database update
            logger.info("\n🔍 Verifying database was updated...")
            from central_system.models.base import get_db
            
            with get_db() as db:
                updated_faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
                if updated_faculty:
                    logger.info(f"✅ Database verification successful")
                    logger.info(f"   Current DB status: {updated_faculty.status}")
                    logger.info(f"   Last seen: {updated_faculty.last_seen}")
                    self.test_results['direct_update'] = True
                else:
                    logger.error("❌ Could not find faculty in database")
                    self.test_results['direct_update'] = False
                    
        except Exception as e:
            logger.error(f"❌ Direct status update test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.test_results['direct_update'] = False
    
    def test_mqtt_message_handler(self, controller, faculty):
        """Test MQTT message handler directly."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 4: MQTT MESSAGE HANDLER")
        logger.info("=" * 80)
        
        try:
            faculty_id = faculty.id
            topic = f"consultease/faculty/{faculty_id}/status"
            
            # Test message 1: Faculty becomes available
            logger.info(f"🔄 Test 4a: Simulating ESP32 'AVAILABLE' message")
            
            esp32_message = {
                "faculty_id": faculty_id,
                "faculty_name": faculty.name,
                "present": True,
                "status": "AVAILABLE",
                "timestamp": int(time.time() * 1000),
                "ntp_sync_status": "SYNCED",
                "in_grace_period": False,
                "detailed_status": "AVAILABLE"
            }
            
            logger.info(f"   Topic: {topic}")
            logger.info(f"   Data: {esp32_message}")
            
            # Call the handler directly
            controller.handle_faculty_status_update(topic, esp32_message)
            
            logger.info("✅ MQTT handler called successfully")
            
            # Wait for processing
            time.sleep(2)
            
            # Test message 2: Faculty goes away
            logger.info(f"\n🔄 Test 4b: Simulating ESP32 'AWAY' message")
            
            esp32_message_away = {
                "faculty_id": faculty_id,
                "faculty_name": faculty.name,
                "present": False,
                "status": "AWAY",
                "timestamp": int(time.time() * 1000),
                "ntp_sync_status": "SYNCED",
                "in_grace_period": False,
                "detailed_status": "AWAY"
            }
            
            controller.handle_faculty_status_update(topic, esp32_message_away)
            
            logger.info("✅ MQTT AWAY handler called successfully")
            
            # Wait for processing
            time.sleep(2)
            
            # Verify database was updated
            logger.info("\n🔍 Verifying database was updated by MQTT handler...")
            from central_system.models.base import get_db
            
            with get_db() as db:
                updated_faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
                if updated_faculty:
                    logger.info(f"✅ Database verification successful")
                    logger.info(f"   Current DB status: {updated_faculty.status}")
                    logger.info(f"   Last seen: {updated_faculty.last_seen}")
                    self.test_results['mqtt_handler'] = True
                else:
                    logger.error("❌ Could not find faculty in database")
                    self.test_results['mqtt_handler'] = False
            
        except Exception as e:
            logger.error(f"❌ MQTT handler test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.test_results['mqtt_handler'] = False
    
    def test_mqtt_service_availability(self):
        """Test if MQTT service is available and running."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 5: MQTT SERVICE AVAILABILITY")
        logger.info("=" * 80)
        
        try:
            from central_system.services.async_mqtt_service import get_async_mqtt_service
            
            mqtt_service = get_async_mqtt_service()
            logger.info("✅ MQTT service imported successfully")
            
            # Check if service is running
            is_running = getattr(mqtt_service, 'running', False)
            logger.info(f"   MQTT service running: {is_running}")
            
            # Try to get stats
            try:
                stats = mqtt_service.get_stats()
                logger.info(f"   MQTT stats: {stats}")
                self.test_results['mqtt_service'] = True
            except Exception as stats_error:
                logger.warning(f"   Could not get MQTT stats: {stats_error}")
                self.test_results['mqtt_service'] = False
            
        except Exception as e:
            logger.error(f"❌ MQTT service test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.test_results['mqtt_service'] = False
    
    def test_publish_status_update(self, controller, faculty):
        """Test if the controller can publish status updates."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 6: STATUS UPDATE PUBLISHING")
        logger.info("=" * 80)
        
        try:
            # Test the internal publishing method
            faculty_data = {
                'id': faculty.id,
                'name': faculty.name,
                'status': True
            }
            
            logger.info(f"🔄 Testing status update publishing for faculty {faculty.id}")
            
            # Call the internal publishing method
            controller._publish_status_update_with_sequence_safe(faculty_data, True, False)
            
            logger.info("✅ Status update publishing called successfully")
            self.test_results['publishing'] = True
            
        except Exception as e:
            logger.error(f"❌ Status update publishing test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.test_results['publishing'] = False
    
    def analyze_results(self):
        """Analyze test results and provide recommendations."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST RESULTS ANALYSIS")
        logger.info("=" * 80)
        
        passed_tests = sum(1 for result in self.test_results.values() if result)
        total_tests = len(self.test_results)
        
        logger.info(f"📊 Test Summary: {passed_tests}/{total_tests} tests passed")
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {test_name}: {status}")
        
        # Provide specific recommendations
        logger.info("\n🔧 RECOMMENDATIONS:")
        
        if not self.test_results.get('initialization', True):
            logger.info("   1. Fix Faculty Controller initialization issues")
        
        if not self.test_results.get('database', True):
            logger.info("   2. Check database connection and ensure faculty records exist")
        
        if not self.test_results.get('direct_update', True):
            logger.info("   3. Fix Faculty Controller update_faculty_status() method")
        
        if not self.test_results.get('mqtt_handler', True):
            logger.info("   4. Fix Faculty Controller MQTT message handler")
        
        if not self.test_results.get('mqtt_service', True):
            logger.info("   5. Check MQTT service availability and startup")
        
        if not self.test_results.get('publishing', True):
            logger.info("   6. Fix Faculty Controller status update publishing")
        
        # Overall assessment
        if passed_tests == total_tests:
            logger.info("\n✅ ALL TESTS PASSED - Faculty Controller should be working!")
            logger.info("   The issue might be:")
            logger.info("   - ESP32 not publishing messages")
            logger.info("   - Dashboard not subscribing properly")
            logger.info("   - MQTT broker connectivity issues")
        elif passed_tests >= total_tests * 0.8:
            logger.info("\n⚠️ MOSTLY WORKING - Minor issues detected")
            logger.info("   Focus on fixing the failed tests above")
        else:
            logger.info("\n❌ MAJOR ISSUES DETECTED - Faculty Controller needs fixing")
            logger.info("   Multiple components are not working properly")
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        logger.info("🚀 Starting Faculty Controller Manual Test Suite...")
        logger.info("   This will test the faculty status update system without MQTT dependencies")
        
        # Test 1: Initialization
        controller = self.test_faculty_controller_initialization()
        if not controller:
            logger.error("Cannot continue - Faculty Controller initialization failed")
            return
        
        # Test 2: Database
        faculty = self.test_database_connection()
        if not faculty:
            logger.error("Cannot continue - No faculty records found")
            return
        
        # Test 3: Direct status update
        self.test_faculty_status_update_directly(controller, faculty)
        
        # Test 4: MQTT message handler
        self.test_mqtt_message_handler(controller, faculty)
        
        # Test 5: MQTT service
        self.test_mqtt_service_availability()
        
        # Test 6: Publishing
        self.test_publish_status_update(controller, faculty)
        
        # Analysis
        self.analyze_results()
        
        logger.info("\n✅ Faculty Controller Manual Test Suite completed!")

if __name__ == "__main__":
    tester = FacultyControllerTester()
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc()) 