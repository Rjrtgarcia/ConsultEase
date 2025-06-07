#!/usr/bin/env python3
"""
Raspberry Pi Faculty Status Debugging Script

This script tests the complete faculty status update flow on the actual Raspberry Pi
where the ConsultEase system is deployed to identify why real-time updates aren't working.

Run this on the Raspberry Pi where ConsultEase is installed.
"""

import sys
import os
import time
import logging
import json
import signal
from datetime import datetime

# Add the central_system path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
central_system_path = os.path.join(current_dir, 'central_system')
sys.path.insert(0, central_system_path)

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FacultyStatusRaspberryPiDebugger:
    """Debug faculty status updates on Raspberry Pi."""
    
    def __init__(self):
        self.test_results = {}
        self.mqtt_messages_received = []
        self.running = True
        
    def signal_handler(self, sig, frame):
        logger.info("🛑 Stopping debugger...")
        self.running = False

    def test_database_connection(self):
        """Test database connection and faculty records."""
        logger.info("🧪 Testing Database Connection and Faculty Records")
        logger.info("-" * 60)
        
        try:
            from central_system.models import Faculty, get_db
            
            db = get_db()
            faculties = db.query(Faculty).all()
            
            logger.info(f"✅ Database connection successful")
            logger.info(f"📊 Found {len(faculties)} faculty records:")
            
            for faculty in faculties:
                logger.info(f"   ID: {faculty.id}")
                logger.info(f"   Name: {faculty.name}")
                logger.info(f"   Status: {'Available' if faculty.status else 'Unavailable'}")
                logger.info(f"   Last seen: {faculty.last_seen}")
                logger.info(f"   BLE ID: {faculty.ble_id}")
                logger.info("   " + "-" * 40)
            
            db.close()
            self.test_results['database'] = True
            return faculties
            
        except Exception as e:
            logger.error(f"❌ Database test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.test_results['database'] = False
            return []

    def test_faculty_controller_initialization(self):
        """Test Faculty Controller initialization."""
        logger.info("🧪 Testing Faculty Controller Initialization")
        logger.info("-" * 60)
        
        try:
            from central_system.controllers.faculty_controller import FacultyController
            
            controller = FacultyController()
            logger.info("✅ Faculty Controller created successfully")
            
            # Test start method
            controller.start()
            logger.info("✅ Faculty Controller started successfully")
            
            self.test_results['faculty_controller'] = True
            return controller
            
        except Exception as e:
            logger.error(f"❌ Faculty Controller test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.test_results['faculty_controller'] = False
            return None

    def test_direct_status_update(self, controller, faculty_id):
        """Test direct faculty status update."""
        logger.info("🧪 Testing Direct Faculty Status Update")
        logger.info("-" * 60)
        
        try:
            if not controller:
                logger.error("❌ No Faculty Controller available")
                return False
            
            # Get current status
            from central_system.models import Faculty, get_db
            db = get_db()
            faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
            
            if not faculty:
                logger.error(f"❌ Faculty {faculty_id} not found")
                db.close()
                return False
                
            original_status = faculty.status
            logger.info(f"📝 Original status: {'Available' if original_status else 'Unavailable'}")
            
            # Toggle status
            new_status = not original_status
            
            logger.info(f"🔄 Updating faculty {faculty_id} status to: {'Available' if new_status else 'Unavailable'}")
            
            # Use the Faculty Controller's update method
            result = controller.update_faculty_status(faculty_id, new_status)
            
            if result:
                logger.info("✅ Faculty Controller status update successful")
                logger.info(f"   Result: {result}")
                
                # Verify in database
                db.refresh(faculty)
                db_status = faculty.status
                logger.info(f"✅ Database verification: {'Available' if db_status else 'Unavailable'}")
                
                if db_status == new_status:
                    logger.info("✅ Database update successful")
                    self.test_results['direct_update'] = True
                else:
                    logger.error("❌ Database update failed - status mismatch")
                    self.test_results['direct_update'] = False
            else:
                logger.error("❌ Faculty Controller status update failed")
                self.test_results['direct_update'] = False
            
            db.close()
            return result is not None
            
        except Exception as e:
            logger.error(f"❌ Direct status update test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.test_results['direct_update'] = False
            return False

    def test_mqtt_status_handler(self, controller, faculty_id):
        """Test MQTT status message handler."""
        logger.info("🧪 Testing MQTT Status Message Handler")
        logger.info("-" * 60)
        
        try:
            if not controller:
                logger.error("❌ No Faculty Controller available")
                return False
            
            # Get faculty info
            from central_system.models import Faculty, get_db
            db = get_db()
            faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
            
            if not faculty:
                logger.error(f"❌ Faculty {faculty_id} not found")
                db.close()
                return False
            
            original_status = faculty.status
            logger.info(f"📝 Original status: {'Available' if original_status else 'Unavailable'}")
            
            # Create ESP32-style MQTT message
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
            
            topic = f"consultease/faculty/{faculty_id}/status"
            
            logger.info(f"🔄 Simulating ESP32 MQTT message:")
            logger.info(f"   Topic: {topic}")
            logger.info(f"   Message: {esp32_message}")
            
            # Call the handler directly
            controller.handle_faculty_status_update(topic, esp32_message)
            
            # Wait for processing
            time.sleep(2)
            
            # Check database
            db.refresh(faculty)
            new_status = faculty.status
            logger.info(f"✅ Status after MQTT handler: {'Available' if new_status else 'Unavailable'}")
            
            if new_status != original_status:
                logger.info("✅ MQTT handler successfully changed status")
                self.test_results['mqtt_handler'] = True
            else:
                logger.warning("⚠️ MQTT handler didn't change status")
                self.test_results['mqtt_handler'] = False
            
            db.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ MQTT handler test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.test_results['mqtt_handler'] = False
            return False

    def test_mqtt_service_connection(self):
        """Test MQTT service connection."""
        logger.info("🧪 Testing MQTT Service Connection")
        logger.info("-" * 60)
        
        try:
            from central_system.services.async_mqtt_service import get_async_mqtt_service
            
            mqtt_service = get_async_mqtt_service()
            
            if mqtt_service:
                logger.info("✅ MQTT service instance obtained")
                
                # Check connection status
                stats = mqtt_service.get_stats()
                logger.info(f"📊 MQTT Stats: {stats}")
                
                connected = stats.get('connected', False)
                if connected:
                    logger.info("✅ MQTT service is connected")
                    self.test_results['mqtt_connection'] = True
                else:
                    logger.error("❌ MQTT service is not connected")
                    self.test_results['mqtt_connection'] = False
                
                return connected
            else:
                logger.error("❌ Could not get MQTT service instance")
                self.test_results['mqtt_connection'] = False
                return False
                
        except Exception as e:
            logger.error(f"❌ MQTT service test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.test_results['mqtt_connection'] = False
            return False

    def test_mqtt_router_conflicts(self):
        """Test for MQTT Router conflicts."""
        logger.info("🧪 Testing MQTT Router Conflicts")
        logger.info("-" * 60)
        
        try:
            from central_system.services.mqtt_router import get_mqtt_router
            
            router = get_mqtt_router()
            
            if router:
                logger.info("✅ MQTT Router instance found")
                
                # Check for faculty status routes
                routes = router.get_route_info()
                faculty_routes = [r for r in routes if 'faculty' in r.get('name', '').lower() and 'status' in r.get('name', '').lower()]
                
                logger.info(f"📊 Total routes: {len(routes)}")
                logger.info(f"📊 Faculty status routes: {len(faculty_routes)}")
                
                if faculty_routes:
                    logger.error("❌ MQTT Router has faculty status routes - CONFLICT DETECTED!")
                    for route in faculty_routes:
                        logger.error(f"   Conflicting route: {route['name']} - {route['pattern']}")
                    self.test_results['mqtt_router_conflict'] = True
                else:
                    logger.info("✅ No faculty status routes in MQTT Router - good!")
                    self.test_results['mqtt_router_conflict'] = False
                
                # Check handlers
                handlers = getattr(router, 'message_handlers', {})
                faculty_handlers = [p for p in handlers.keys() if 'faculty' in p.lower() and 'status' in p.lower()]
                
                if faculty_handlers:
                    logger.error("❌ MQTT Router has faculty status handlers - CONFLICT DETECTED!")
                    for handler in faculty_handlers:
                        logger.error(f"   Conflicting handler: {handler}")
                else:
                    logger.info("✅ No faculty status handlers in MQTT Router - good!")
                
            else:
                logger.info("ℹ️ No MQTT Router instance found - this is okay")
                self.test_results['mqtt_router_conflict'] = False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ MQTT Router test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.test_results['mqtt_router_conflict'] = None
            return False

    def test_dashboard_mqtt_subscription(self):
        """Test Dashboard MQTT subscription."""
        logger.info("🧪 Testing Dashboard MQTT Subscription")
        logger.info("-" * 60)
        
        try:
            # This test can't run the full dashboard, but we can check the subscription code
            import re
            
            dashboard_file = os.path.join(current_dir, 'central_system', 'views', 'dashboard_window.py')
            
            if os.path.exists(dashboard_file):
                with open(dashboard_file, 'r') as f:
                    content = f.read()
                
                # Check for correct subscription
                if 'consultease/faculty/+/status_update' in content:
                    logger.info("✅ Dashboard subscribes to correct topic: consultease/faculty/+/status_update")
                else:
                    logger.error("❌ Dashboard subscription to status_update topic not found")
                
                # Check for incorrect subscription
                if 'consultease/faculty/+/status"' in content and 'status_update' not in content:
                    logger.error("❌ Dashboard still subscribes to raw ESP32 topic - this will cause conflicts")
                else:
                    logger.info("✅ Dashboard doesn't subscribe to raw ESP32 topic - good!")
                
                # Check for handler method
                if 'handle_realtime_status_update' in content:
                    logger.info("✅ Dashboard has real-time status update handler")
                else:
                    logger.error("❌ Dashboard missing real-time status update handler")
                
                self.test_results['dashboard_subscription'] = True
            else:
                logger.error("❌ Dashboard file not found")
                self.test_results['dashboard_subscription'] = False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Dashboard subscription test failed: {e}")
            self.test_results['dashboard_subscription'] = False
            return False

    def run_comprehensive_diagnosis(self):
        """Run all diagnostic tests."""
        logger.info("🔍 FACULTY STATUS COMPREHENSIVE DIAGNOSIS")
        logger.info("=" * 80)
        logger.info(f"🕐 Start time: {datetime.now().isoformat()}")
        logger.info("=" * 80)
        
        # Signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Test 1: Database
        faculties = self.test_database_connection()
        
        if not faculties:
            logger.error("❌ Cannot continue without faculty records")
            return
        
        test_faculty_id = faculties[0].id
        logger.info(f"🎯 Using faculty ID {test_faculty_id} for testing: {faculties[0].name}")
        
        # Test 2: Faculty Controller
        controller = self.test_faculty_controller_initialization()
        
        # Test 3: MQTT Service
        self.test_mqtt_service_connection()
        
        # Test 4: MQTT Router conflicts
        self.test_mqtt_router_conflicts()
        
        # Test 5: Dashboard subscription
        self.test_dashboard_mqtt_subscription()
        
        # Test 6: Direct status update
        self.test_direct_status_update(controller, test_faculty_id)
        
        # Test 7: MQTT handler
        self.test_mqtt_status_handler(controller, test_faculty_id)
        
        # Results summary
        self.print_diagnosis_summary()

    def print_diagnosis_summary(self):
        """Print comprehensive diagnosis summary."""
        logger.info("\n🏁 DIAGNOSIS SUMMARY")
        logger.info("=" * 80)
        
        all_passed = True
        
        for test_name, result in self.test_results.items():
            if result is True:
                status = "✅ PASS"
            elif result is False:
                status = "❌ FAIL"
                all_passed = False
            else:
                status = "⚠️ UNKNOWN"
                all_passed = False
            
            logger.info(f"{status}: {test_name}")
        
        logger.info("\n🔧 RECOMMENDATIONS:")
        
        if not self.test_results.get('database', True):
            logger.info("   1. Fix database connection and ensure faculty records exist")
            
        if not self.test_results.get('faculty_controller', True):
            logger.info("   2. Check Faculty Controller initialization in main.py")
            
        if not self.test_results.get('mqtt_connection', True):
            logger.info("   3. Check MQTT broker service - run: sudo systemctl status mosquitto")
            
        if self.test_results.get('mqtt_router_conflict', False):
            logger.info("   4. MQTT Router conflict detected - this is the main issue!")
            
        if not self.test_results.get('direct_update', True):
            logger.info("   5. Check Faculty Controller update_faculty_status method")
            
        if not self.test_results.get('mqtt_handler', True):
            logger.info("   6. Check Faculty Controller handle_faculty_status_update method")
        
        if all_passed:
            logger.info("   🎉 All tests passed! Faculty status system should be working.")
            logger.info("   💡 If real-time updates still don't work, check ESP32 publishing.")
        else:
            logger.info("   ⚠️ Some tests failed. Fix the issues above and re-run this script.")
        
        logger.info(f"\n🕐 Diagnosis completed at: {datetime.now().isoformat()}")

if __name__ == "__main__":
    debugger = FacultyStatusRaspberryPiDebugger()
    debugger.run_comprehensive_diagnosis() 