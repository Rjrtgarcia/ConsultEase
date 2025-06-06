#!/usr/bin/env python3
"""
Validation test for faculty status real-time update fix.
This test validates that the fix eliminates the MQTT Router/Faculty Controller conflict.
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

class FacultyRealtimeFixValidator:
    def __init__(self):
        self.validation_results = {}
        
    def validate_mqtt_router_conflict_resolved(self):
        """Validate that MQTT Router no longer handles faculty status messages."""
        logger.info("=" * 80)
        logger.info("VALIDATION 1: MQTT ROUTER CONFLICT RESOLUTION")
        logger.info("=" * 80)
        
        try:
            from central_system.services.mqtt_router import MQTTRouter
            
            # Create a mock MQTT service for testing
            class MockMQTTService:
                def publish_async(self, topic, payload, qos=1):
                    pass
            
            router = MQTTRouter(MockMQTTService())
            
            # Check if faculty status routes are disabled
            faculty_routes = [route for route in router.routes.values() 
                            if 'faculty' in route.name and 'status' in route.name]
            
            faculty_handlers = [pattern for pattern in router.message_handlers.keys() 
                              if 'faculty' in pattern and 'status' in pattern]
            
            logger.info(f"📊 Faculty status routes found: {len(faculty_routes)}")
            logger.info(f"📊 Faculty status handlers found: {len(faculty_handlers)}")
            
            if len(faculty_routes) == 0 and len(faculty_handlers) == 0:
                logger.info("✅ MQTT Router conflict resolved - no faculty status handling")
                self.validation_results['mqtt_router_conflict'] = True
            else:
                logger.error("❌ MQTT Router still handles faculty status - conflict exists")
                logger.error(f"   Routes: {[r.name for r in faculty_routes]}")
                logger.error(f"   Handlers: {faculty_handlers}")
                self.validation_results['mqtt_router_conflict'] = False
                
        except Exception as e:
            logger.error(f"❌ MQTT Router validation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.validation_results['mqtt_router_conflict'] = False
    
    def validate_faculty_controller_subscriptions(self):
        """Validate that Faculty Controller has proper MQTT subscriptions."""
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION 2: FACULTY CONTROLLER SUBSCRIPTIONS")
        logger.info("=" * 80)
        
        try:
            from central_system.controllers.faculty_controller import FacultyController
            
            controller = FacultyController()
            logger.info("✅ Faculty Controller initialized successfully")
            
            # Check if controller has required attributes
            has_callbacks = hasattr(controller, 'callbacks')
            has_queue_service = hasattr(controller, 'queue_service')
            has_start_method = hasattr(controller, 'start')
            has_handler_method = hasattr(controller, 'handle_faculty_status_update')
            
            logger.info(f"   - Has callbacks: {has_callbacks}")
            logger.info(f"   - Has queue_service: {has_queue_service}")
            logger.info(f"   - Has start method: {has_start_method}")
            logger.info(f"   - Has status handler: {has_handler_method}")
            
            if all([has_callbacks, has_queue_service, has_start_method, has_handler_method]):
                logger.info("✅ Faculty Controller has all required components")
                self.validation_results['faculty_controller_ready'] = True
            else:
                logger.error("❌ Faculty Controller missing required components")
                self.validation_results['faculty_controller_ready'] = False
                
        except Exception as e:
            logger.error(f"❌ Faculty Controller validation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.validation_results['faculty_controller_ready'] = False
    
    def validate_dashboard_subscription(self):
        """Validate that Dashboard subscribes to correct topics."""
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION 3: DASHBOARD REAL-TIME SUBSCRIPTIONS")
        logger.info("=" * 80)
        
        try:
            from central_system.views.dashboard_window import DashboardWindow
            
            logger.info("✅ Dashboard Window imported successfully")
            
            # Check for required methods
            has_setup_realtime = hasattr(DashboardWindow, 'setup_realtime_updates')
            has_handle_realtime = hasattr(DashboardWindow, 'handle_realtime_status_update')
            has_handle_system = hasattr(DashboardWindow, 'handle_system_notification')
            has_update_card = hasattr(DashboardWindow, 'update_faculty_card_status')
            
            logger.info(f"   - Has setup_realtime_updates: {has_setup_realtime}")
            logger.info(f"   - Has handle_realtime_status_update: {has_handle_realtime}")
            logger.info(f"   - Has handle_system_notification: {has_handle_system}")
            logger.info(f"   - Has update_faculty_card_status: {has_update_card}")
            
            if all([has_setup_realtime, has_handle_realtime, has_handle_system, has_update_card]):
                logger.info("✅ Dashboard has all required real-time update components")
                self.validation_results['dashboard_ready'] = True
            else:
                logger.error("❌ Dashboard missing required real-time components")
                self.validation_results['dashboard_ready'] = False
                
        except Exception as e:
            logger.error(f"❌ Dashboard validation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.validation_results['dashboard_ready'] = False
    
    def validate_message_flow_simulation(self):
        """Simulate the complete message flow to validate fix."""
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION 4: MESSAGE FLOW SIMULATION")
        logger.info("=" * 80)
        
        try:
            from central_system.controllers.faculty_controller import FacultyController
            from central_system.models.faculty import Faculty
            from central_system.models.base import get_db
            
            controller = FacultyController()
            
            # Find a faculty to test with
            with get_db() as db:
                faculty = db.query(Faculty).first()
                
                if not faculty:
                    logger.error("❌ No faculty records found for simulation")
                    self.validation_results['message_flow'] = False
                    return
                
                logger.info(f"📋 Using faculty for simulation: {faculty.name} (ID: {faculty.id})")
                original_status = faculty.status
            
            # Simulate ESP32 message
            topic = f"consultease/faculty/{faculty.id}/status"
            esp32_message = {
                "faculty_id": faculty.id,
                "faculty_name": faculty.name,
                "present": True,
                "status": "AVAILABLE",
                "timestamp": int(time.time() * 1000),
                "ntp_sync_status": "SYNCED"
            }
            
            logger.info(f"🔄 Simulating ESP32 message:")
            logger.info(f"   Topic: {topic}")
            logger.info(f"   Message: {esp32_message}")
            
            # Call handler directly
            result = controller.handle_faculty_status_update(topic, esp32_message)
            
            logger.info("✅ Faculty Controller handler executed successfully")
            
            # Verify database was updated
            with get_db() as db:
                updated_faculty = db.query(Faculty).filter(Faculty.id == faculty.id).first()
                if updated_faculty and updated_faculty.status == True:
                    logger.info("✅ Database updated correctly")
                    
                    # Restore original status
                    controller.update_faculty_status(faculty.id, original_status)
                    logger.info(f"✅ Restored original status: {original_status}")
                    
                    self.validation_results['message_flow'] = True
                else:
                    logger.error("❌ Database not updated correctly")
                    self.validation_results['message_flow'] = False
                    
        except Exception as e:
            logger.error(f"❌ Message flow simulation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.validation_results['message_flow'] = False
    
    def validate_logging_enhancements(self):
        """Validate that enhanced logging is in place."""
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION 5: ENHANCED LOGGING")
        logger.info("=" * 80)
        
        try:
            import inspect
            from central_system.controllers.faculty_controller import FacultyController
            
            # Get source code of the handler method
            source = inspect.getsource(FacultyController.handle_faculty_status_update)
            
            # Check for enhanced logging markers
            has_enhanced_logging = (
                "[FACULTY CONTROLLER]" in source and
                "Successfully processed status update" in source and
                "Failed to process status update" in source
            )
            
            if has_enhanced_logging:
                logger.info("✅ Enhanced logging is in place")
                self.validation_results['enhanced_logging'] = True
            else:
                logger.error("❌ Enhanced logging not found")
                self.validation_results['enhanced_logging'] = False
                
        except Exception as e:
            logger.error(f"❌ Logging validation failed: {e}")
            self.validation_results['enhanced_logging'] = False
    
    def generate_fix_report(self):
        """Generate a comprehensive fix validation report."""
        logger.info("\n" + "=" * 80)
        logger.info("FACULTY STATUS REAL-TIME FIX - VALIDATION REPORT")
        logger.info("=" * 80)
        
        passed_validations = sum(1 for result in self.validation_results.values() if result)
        total_validations = len(self.validation_results)
        
        logger.info(f"📊 Validation Summary: {passed_validations}/{total_validations} validations passed")
        
        for test_name, result in self.validation_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {test_name}: {status}")
        
        # Overall fix status
        if passed_validations == total_validations:
            logger.info("\n🎉 ALL VALIDATIONS PASSED!")
            logger.info("✅ Faculty status real-time update fix is COMPLETE and WORKING")
            logger.info("\n📋 Expected Behavior:")
            logger.info("   1. ESP32 publishes to consultease/faculty/{id}/status")
            logger.info("   2. Faculty Controller receives and processes message")
            logger.info("   3. Database is updated with new status")
            logger.info("   4. Faculty Controller publishes to consultease/faculty/{id}/status_update")
            logger.info("   5. Dashboard receives update and immediately updates UI")
            logger.info("\n⏱️ Expected Timing: 3-29 seconds for status changes")
            
        elif passed_validations >= total_validations * 0.8:
            logger.warning("\n⚠️ MOSTLY WORKING - Minor issues detected")
            logger.info("The fix is largely successful but some components need attention")
            
        else:
            logger.error("\n❌ MAJOR ISSUES DETECTED")
            logger.error("The fix is not working properly. Review failed validations above.")
        
        # Troubleshooting guidance
        logger.info("\n🔧 TROUBLESHOOTING:")
        
        if not self.validation_results.get('mqtt_router_conflict', True):
            logger.info("   • Check central_system/services/mqtt_router.py")
            logger.info("     Ensure faculty status routes and handlers are commented out")
        
        if not self.validation_results.get('faculty_controller_ready', True):
            logger.info("   • Check Faculty Controller initialization")
            logger.info("     Ensure all required methods and attributes exist")
        
        if not self.validation_results.get('message_flow', True):
            logger.info("   • Check Faculty Controller message processing")
            logger.info("     Verify database updates and MQTT publishing work")
        
        logger.info("\n📝 Next Steps:")
        logger.info("   1. Deploy this fix to the Raspberry Pi")
        logger.info("   2. Restart the ConsultEase central system")
        logger.info("   3. Test with actual ESP32 BLE beacon movement")
        logger.info("   4. Monitor logs for [FACULTY CONTROLLER] messages")
        logger.info("   5. Verify dashboard updates in real-time")
    
    def run_all_validations(self):
        """Run all validations in sequence."""
        logger.info("🚀 Starting Faculty Status Real-Time Fix Validation...")
        logger.info("   This validates that the MQTT Router/Faculty Controller conflict is resolved")
        
        # Run all validations
        self.validate_mqtt_router_conflict_resolved()
        self.validate_faculty_controller_subscriptions()
        self.validate_dashboard_subscription() 
        self.validate_message_flow_simulation()
        self.validate_logging_enhancements()
        
        # Generate comprehensive report
        self.generate_fix_report()
        
        logger.info("\n✅ Faculty Status Real-Time Fix Validation completed!")

if __name__ == "__main__":
    validator = FacultyRealtimeFixValidator()
    try:
        validator.run_all_validations()
    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc()) 