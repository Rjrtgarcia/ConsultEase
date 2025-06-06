#!/usr/bin/env python3
"""
Comprehensive diagnostic script for faculty status/availability real-time updates.
Tests the entire flow from ESP32 desk unit MQTT messages to dashboard UI updates.
"""

import sys
import os
import time
import logging
import json
from datetime import datetime

# Add the central_system path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'central_system'))

from central_system.models import Faculty, get_db
from central_system.controllers.faculty_controller import FacultyController
from central_system.utils.mqtt_utils import publish_mqtt_message, subscribe_to_topic
from central_system.services.async_mqtt_service import get_mqtt_service

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FacultyStatusDiagnostic:
    """Comprehensive diagnostic for faculty status real-time updates."""
    
    def __init__(self):
        self.faculty_controller = FacultyController()
        self.mqtt_service = get_mqtt_service()
        self.test_results = {}
        self.received_messages = []
        
    def run_diagnostics(self):
        """Run all diagnostic tests."""
        logger.info("🔍 Starting Faculty Status Real-Time Update Diagnostics")
        logger.info("=" * 60)
        
        # Test database and basic functionality first
        test_faculty = self.test_database_connectivity()
        self.test_mqtt_connectivity()
        self.test_database_model_fields()
        
        if test_faculty:
            self.test_faculty_controller_updates()
            self.test_mqtt_subscription_handling()
            self.test_esp32_status_simulation()
            self.test_dashboard_update_simulation()
        
        # Print comprehensive summary
        self.print_diagnostics_summary()
        
    def test_database_connectivity(self):
        """Test database connectivity and faculty data retrieval."""
        logger.info("\n1️⃣ Testing Database Connectivity and Faculty Data")
        logger.info("-" * 50)
        
        try:
            db = get_db()
            faculties = db.query(Faculty).all()
            
            logger.info(f"✅ Database connection successful")
            logger.info(f"📊 Found {len(faculties)} faculty members in database")
            
            if faculties:
                for faculty in faculties:
                    logger.info(f"  👤 {faculty.name} (ID: {faculty.id})")
                    logger.info(f"      Status: {faculty.status}")
                    logger.info(f"      Always Available: {getattr(faculty, 'always_available', 'N/A')}")
                    logger.info(f"      Last Seen: {faculty.last_seen}")
                    logger.info(f"      Department: {faculty.department}")
                    
                self.test_results['database'] = 'PASS'
                return faculties[0]  # Return first faculty for testing
            else:
                logger.warning("⚠️ No faculty members found in database")
                self.test_results['database'] = 'FAIL - No faculty'
                return None
                
        except Exception as e:
            logger.error(f"❌ Database connectivity failed: {e}")
            self.test_results['database'] = f'FAIL - {str(e)}'
            return None
        finally:
            db.close()
            
    def test_mqtt_connectivity(self):
        """Test MQTT service connectivity."""
        logger.info("\n2️⃣ Testing MQTT Service Connectivity")
        logger.info("-" * 50)
        
        try:
            if self.mqtt_service.is_connected():
                logger.info("✅ MQTT service is connected")
                self.test_results['mqtt_connectivity'] = 'PASS'
            else:
                logger.warning("⚠️ MQTT service is not connected")
                self.test_results['mqtt_connectivity'] = 'FAIL - Not connected'
                    
        except Exception as e:
            logger.error(f"❌ MQTT connectivity test failed: {e}")
            self.test_results['mqtt_connectivity'] = f'FAIL - {str(e)}'
            
    def test_faculty_controller_updates(self):
        """Test faculty controller status update functionality."""
        logger.info("\n3️⃣ Testing Faculty Controller Status Updates")
        logger.info("-" * 50)
        
        try:
            # Get first faculty member for testing
            faculties = self.faculty_controller.get_all_faculty()
            if not faculties:
                logger.error("❌ No faculty members available for testing")
                self.test_results['faculty_controller'] = 'FAIL - No faculty'
                return
                
            test_faculty = faculties[0]
            original_status = test_faculty.status
            logger.info(f"🧪 Testing with faculty: {test_faculty.name} (ID: {test_faculty.id})")
            logger.info(f"📝 Original status: {original_status}")
            
            # Test status change to True
            logger.info("🔄 Updating status to True (Available)...")
            result = self.faculty_controller.update_faculty_status(test_faculty.id, True)
            
            if result:
                logger.info("✅ Status update to True successful")
                time.sleep(2)
                
                # Test status change to False  
                logger.info("🔄 Updating status to False (Unavailable)...")
                result2 = self.faculty_controller.update_faculty_status(test_faculty.id, False)
                
                if result2:
                    logger.info("✅ Status update to False successful")
                    
                    # Restore original status
                    time.sleep(1)
                    self.faculty_controller.update_faculty_status(test_faculty.id, original_status)
                    logger.info(f"🔄 Restored original status: {original_status}")
                    
                    self.test_results['faculty_controller'] = 'PASS'
                else:
                    logger.error("❌ Status update to False failed")
                    self.test_results['faculty_controller'] = 'FAIL - Update to False'
            else:
                logger.error("❌ Status update to True failed")
                self.test_results['faculty_controller'] = 'FAIL - Update to True'
                
        except Exception as e:
            logger.error(f"❌ Faculty controller test failed: {e}")
            self.test_results['faculty_controller'] = f'FAIL - {str(e)}'
            
    def test_mqtt_subscription_handling(self):
        """Test MQTT subscription and message handling."""
        logger.info("\n4️⃣ Testing MQTT Subscription and Message Handling")
        logger.info("-" * 50)
        
        try:
            # Subscribe to faculty status topics
            topics_to_test = [
                "consultease/faculty/+/status",
                "consultease/faculty/+/status_update", 
                "consultease/system/notifications"
            ]
            
            # Set up message handler
            def message_handler(topic, data):
                logger.info(f"📨 Received MQTT message - Topic: {topic}")
                logger.info(f"📊 Message data: {data}")
                self.received_messages.append({
                    'topic': topic,
                    'data': data,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Subscribe to topics
            for topic in topics_to_test:
                try:
                    subscribe_to_topic(topic, message_handler)
                    logger.info(f"✅ Subscribed to: {topic}")
                except Exception as e:
                    logger.error(f"❌ Failed to subscribe to {topic}: {e}")
                    
            self.test_results['mqtt_subscription'] = 'PASS'
            
        except Exception as e:
            logger.error(f"❌ MQTT subscription test failed: {e}")
            self.test_results['mqtt_subscription'] = f'FAIL - {str(e)}'
            
    def test_esp32_status_simulation(self):
        """Test ESP32 desk unit status message simulation."""
        logger.info("\n5️⃣ Testing ESP32 Status Message Simulation")
        logger.info("-" * 50)
        
        try:
            # Get test faculty
            faculties = self.faculty_controller.get_all_faculty()
            if not faculties:
                logger.error("❌ No faculty available for ESP32 simulation")
                self.test_results['esp32_simulation'] = 'FAIL - No faculty'
                return
                
            test_faculty = faculties[0]
            faculty_id = test_faculty.id
            faculty_name = test_faculty.name
            
            # Clear received messages
            self.received_messages.clear()
            
            # Test different ESP32 status message formats
            test_messages = [
                {
                    "topic": f"consultease/faculty/{faculty_id}/status",
                    "payload": {
                        "faculty_id": faculty_id,
                        "faculty_name": faculty_name,
                        "present": True,
                        "status": "AVAILABLE",
                        "timestamp": int(time.time())
                    },
                    "description": "ESP32 Available Status"
                },
                {
                    "topic": f"consultease/faculty/{faculty_id}/status",
                    "payload": {
                        "faculty_id": faculty_id,
                        "faculty_name": faculty_name,
                        "present": False,
                        "status": "AWAY",
                        "timestamp": int(time.time())
                    },
                    "description": "ESP32 Away Status"
                }
            ]
            
            success_count = 0
            for i, test_case in enumerate(test_messages, 1):
                logger.info(f"📡 Test {i}: {test_case['description']}")
                logger.info(f"   Topic: {test_case['topic']}")
                logger.info(f"   Payload: {test_case['payload']}")
                
                try:
                    result = publish_mqtt_message(test_case['topic'], test_case['payload'])
                    if result:
                        logger.info(f"   ✅ Message published successfully")
                        success_count += 1
                        
                        # Wait for message processing
                        time.sleep(3)
                        
                        # Check database for status change
                        db = get_db()
                        try:
                            updated_faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
                            if updated_faculty:
                                logger.info(f"   📊 Database status after update: {updated_faculty.status}")
                                logger.info(f"   📊 Last seen: {updated_faculty.last_seen}")
                            else:
                                logger.warning(f"   ⚠️ Faculty not found in database")
                        finally:
                            db.close()
                            
                    else:
                        logger.error(f"   ❌ Message publish failed")
                        
                except Exception as e:
                    logger.error(f"   ❌ Message publish error: {e}")
                
                time.sleep(2)  # Wait between tests
                
            if success_count == len(test_messages):
                self.test_results['esp32_simulation'] = 'PASS'
            else:
                self.test_results['esp32_simulation'] = f'PARTIAL - {success_count}/{len(test_messages)}'
                
        except Exception as e:
            logger.error(f"❌ ESP32 simulation test failed: {e}")
            self.test_results['esp32_simulation'] = f'FAIL - {str(e)}'
            
    def test_dashboard_update_simulation(self):
        """Test dashboard update message simulation."""
        logger.info("\n6️⃣ Testing Dashboard Update Message Simulation")
        logger.info("-" * 50)
        
        try:
            # Get test faculty
            faculties = self.faculty_controller.get_all_faculty()
            if not faculties:
                logger.error("❌ No faculty available for dashboard simulation")
                self.test_results['dashboard_simulation'] = 'FAIL - No faculty'
                return
                
            test_faculty = faculties[0]
            faculty_id = test_faculty.id
            faculty_name = test_faculty.name
            
            # Test dashboard-style status update messages
            dashboard_messages = [
                {
                    "topic": f"consultease/faculty/{faculty_id}/status_update",
                    "payload": {
                        "type": "faculty_status",
                        "faculty_id": faculty_id,
                        "faculty_name": faculty_name,
                        "status": True,
                        "previous_status": False,
                        "timestamp": int(time.time())
                    },
                    "description": "Dashboard Available Update"
                },
                {
                    "topic": "consultease/system/notifications",
                    "payload": {
                        "type": "faculty_status",
                        "faculty_id": faculty_id,
                        "faculty_name": faculty_name,
                        "status": False,
                        "timestamp": int(time.time())
                    },
                    "description": "System Notification Unavailable"
                }
            ]
            
            success_count = 0
            for i, test_case in enumerate(dashboard_messages, 1):
                logger.info(f"🖥️ Dashboard Test {i}: {test_case['description']}")
                logger.info(f"   Topic: {test_case['topic']}")
                logger.info(f"   Payload: {test_case['payload']}")
                
                try:
                    result = publish_mqtt_message(test_case['topic'], test_case['payload'])
                    if result:
                        logger.info(f"   ✅ Dashboard message published successfully")
                        success_count += 1
                    else:
                        logger.error(f"   ❌ Dashboard message publish failed")
                        
                except Exception as e:
                    logger.error(f"   ❌ Dashboard message error: {e}")
                
                time.sleep(2)
                
            if success_count == len(dashboard_messages):
                self.test_results['dashboard_simulation'] = 'PASS'
            else:
                self.test_results['dashboard_simulation'] = f'PARTIAL - {success_count}/{len(dashboard_messages)}'
                
        except Exception as e:
            logger.error(f"❌ Dashboard simulation test failed: {e}")
            self.test_results['dashboard_simulation'] = f'FAIL - {str(e)}'
            
    def test_database_model_fields(self):
        """Test database model field verification."""
        logger.info("\n7️⃣ Testing Database Model Field Verification")
        logger.info("-" * 50)
        
        try:
            db = get_db()
            faculty = db.query(Faculty).first()
            
            if faculty:
                # Check for expected fields
                expected_fields = ['id', 'name', 'department', 'email', 'ble_id', 'status', 'always_available', 'last_seen']
                logger.info("📋 Checking faculty model fields:")
                
                for field in expected_fields:
                    if hasattr(faculty, field):
                        value = getattr(faculty, field)
                        logger.info(f"   ✅ {field}: {value} (type: {type(value).__name__})")
                    else:
                        logger.warning(f"   ⚠️ {field}: Field not found")
                
                # Check for problematic fields that might not exist
                problematic_fields = ['availability', 'room']
                logger.info("\n🔍 Checking for problematic fields:")
                for field in problematic_fields:
                    if hasattr(faculty, field):
                        value = getattr(faculty, field)
                        logger.info(f"   ⚠️ {field}: {value} (exists but may cause issues)")
                    else:
                        logger.info(f"   ✅ {field}: Not present (good)")
                        
                self.test_results['database_model'] = 'PASS'
            else:
                logger.error("❌ No faculty found for model verification")
                self.test_results['database_model'] = 'FAIL - No faculty'
                
        except Exception as e:
            logger.error(f"❌ Database model test failed: {e}")
            self.test_results['database_model'] = f'FAIL - {str(e)}'
        finally:
            db.close()
            
    def print_diagnostics_summary(self):
        """Print comprehensive diagnostics summary."""
        logger.info("\n" + "=" * 60)
        logger.info("📋 FACULTY STATUS DIAGNOSTICS SUMMARY")
        logger.info("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result == 'PASS')
        
        logger.info(f"🧪 Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {total_tests - passed_tests}")
        logger.info("")
        
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result == 'PASS' else "❌" if result.startswith('FAIL') else "⚠️"
            logger.info(f"{status_icon} {test_name.replace('_', ' ').title()}: {result}")
            
        if self.received_messages:
            logger.info(f"\n📨 Received {len(self.received_messages)} MQTT messages during testing:")
            for msg in self.received_messages[-5:]:  # Show last 5 messages
                logger.info(f"   📍 {msg['timestamp']}: {msg['topic']}")
                
        logger.info("\n🔧 RECOMMENDED ACTIONS:")
        
        # Check for specific issues and provide recommendations
        if self.test_results.get('database') != 'PASS':
            logger.info("   🔴 Fix database connectivity issues")
            
        if self.test_results.get('mqtt_connectivity') != 'PASS':
            logger.info("   🔴 Fix MQTT service connectivity")
            
        if self.test_results.get('faculty_controller') != 'PASS':
            logger.info("   🔴 Debug faculty controller status update logic")
            
        if self.test_results.get('esp32_simulation') != 'PASS':
            logger.info("   🔴 Check ESP32 MQTT message format and routing")
            
        if self.test_results.get('dashboard_simulation') != 'PASS':
            logger.info("   🔴 Debug dashboard MQTT subscription and UI update logic")
            
        if passed_tests == total_tests:
            logger.info("   🎉 All tests passed! Faculty status system should be working correctly.")
        else:
            logger.info("   📝 Address the failed tests above to fix real-time faculty status updates.")
            
        logger.info("\n💡 For connection issues similar to consultation system:")
        logger.info("   - Check faculty desk unit WiFi/MQTT connections using network fixes")
        logger.info("   - Apply FACULTY_DESK_UNIT_CONNECTION_FIX_GUIDE.md solutions")
        logger.info("   - Verify ESP32 is publishing to correct MQTT topics")
        logger.info("   - Ensure central system MQTT router handles faculty status properly")

def main():
    """Run the faculty status diagnostics."""
    diagnostic = FacultyStatusDiagnostic()
    diagnostic.run_diagnostics()

if __name__ == "__main__":
    main() 