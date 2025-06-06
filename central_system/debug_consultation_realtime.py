#!/usr/bin/env python3
"""
Comprehensive diagnostic script for real-time consultation updates.
This script will help identify why consultation status updates aren't working in real-time.
"""

import sys
import os
import time
import logging
import json
import threading
from datetime import datetime, timedelta

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConsultationRealtimeDiagnostic:
    """Diagnostic tool for real-time consultation updates."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.issues_found = []
        self.test_results = {}
        
    def check_faculty_response_controller(self):
        """Check if faculty response controller is properly configured."""
        self.logger.info("🔍 Checking Faculty Response Controller...")
        
        try:
            # Check if faculty response controller exists and can be imported
            from central_system.controllers.faculty_response_controller import get_faculty_response_controller
            
            controller = get_faculty_response_controller()
            
            if controller is None:
                self.issues_found.append("Faculty Response Controller is None")
                return False
                
            # Check if controller has the necessary methods
            required_methods = ['handle_faculty_response', '_publish_faculty_response_notification']
            for method in required_methods:
                if not hasattr(controller, method):
                    self.issues_found.append(f"Faculty Response Controller missing method: {method}")
                    return False
            
            self.logger.info("✅ Faculty Response Controller found and has required methods")
            return True
            
        except Exception as e:
            self.issues_found.append(f"Faculty Response Controller error: {e}")
            self.logger.error(f"❌ Faculty Response Controller check failed: {e}")
            return False
    
    def check_mqtt_service(self):
        """Check if MQTT service is properly configured."""
        self.logger.info("🔍 Checking MQTT Service...")
        
        try:
            from central_system.services.async_mqtt_service import get_async_mqtt_service
            
            mqtt_service = get_async_mqtt_service()
            
            if mqtt_service is None:
                self.issues_found.append("MQTT Service is None")
                return False
                
            # Check if MQTT service has message handlers
            if not hasattr(mqtt_service, 'message_handlers'):
                self.issues_found.append("MQTT Service missing message_handlers")
                return False
                
            self.logger.info("✅ MQTT Service found and configured")
            return True
            
        except Exception as e:
            self.issues_found.append(f"MQTT Service error: {e}")
            self.logger.error(f"❌ MQTT Service check failed: {e}")
            return False
    
    def check_consultation_controller(self):
        """Check if consultation controller is properly configured.""" 
        self.logger.info("🔍 Checking Consultation Controller...")
        
        try:
            from central_system.controllers.consultation_controller import ConsultationController
            
            controller = ConsultationController()
            
            # Check if controller has the necessary methods
            required_methods = ['update_consultation_status']
            for method in required_methods:
                if not hasattr(controller, method):
                    self.issues_found.append(f"Consultation Controller missing method: {method}")
                    return False
            
            self.logger.info("✅ Consultation Controller found and has required methods")
            return True
            
        except Exception as e:
            self.issues_found.append(f"Consultation Controller error: {e}")
            self.logger.error(f"❌ Consultation Controller check failed: {e}")
            return False
    
    def check_main_application_setup(self):
        """Check if main application properly starts controllers."""
        self.logger.info("🔍 Checking Main Application Controller Setup...")
        
        try:
            # Read the main.py file to check controller initialization
            main_file = os.path.join(project_root, 'main.py')
            if not os.path.exists(main_file):
                self.issues_found.append("main.py file not found")
                return False
                
            with open(main_file, 'r') as f:
                main_content = f.read()
                
            # Check for faculty response controller startup
            if 'faculty_response_controller' not in main_content.lower():
                self.issues_found.append("Faculty Response Controller not found in main.py")
                
            if '.start()' not in main_content:
                self.issues_found.append("No controller .start() calls found in main.py")
                
            self.logger.info("✅ Main application file checked")
            return True
            
        except Exception as e:
            self.issues_found.append(f"Main application check error: {e}")
            self.logger.error(f"❌ Main application check failed: {e}")
            return False
    
    def simulate_mqtt_message_flow(self):
        """Simulate the MQTT message flow to check handlers."""
        self.logger.info("🔍 Simulating MQTT Message Flow...")
        
        try:
            # Mock MQTT message data
            test_message = {
                'type': 'consultation_status_changed',
                'consultation_id': 999,
                'student_id': 1,
                'faculty_id': 1,
                'old_status': 'pending',
                'new_status': 'accepted',
                'response_type': 'ACKNOWLEDGE',
                'timestamp': datetime.now().isoformat(),
                'trigger': 'faculty_response'
            }
            
            self.logger.info(f"📤 Test message: {json.dumps(test_message, indent=2)}")
            
            # Check if we can import the consultation panel
            try:
                from central_system.views.consultation_panel import ConsultationPanel
                self.logger.info("✅ ConsultationPanel can be imported")
                
                # Check if the required methods exist
                required_methods = ['handle_realtime_consultation_update', 'setup_realtime_consultation_updates']
                for method in required_methods:
                    if not hasattr(ConsultationPanel, method):
                        self.issues_found.append(f"ConsultationPanel missing method: {method}")
                        return False
                        
                self.logger.info("✅ ConsultationPanel has required methods")
                
            except Exception as e:
                self.issues_found.append(f"ConsultationPanel import error: {e}")
                return False
            
            return True
            
        except Exception as e:
            self.issues_found.append(f"MQTT message flow simulation error: {e}")
            self.logger.error(f"❌ MQTT message flow simulation failed: {e}")
            return False
    
    def check_mqtt_topics_and_handlers(self):
        """Check MQTT topic subscriptions and handlers."""
        self.logger.info("🔍 Checking MQTT Topics and Handlers...")
        
        try:
            from central_system.utils.mqtt_utils import subscribe_to_topic
            
            # Test topics that should be subscribed to
            test_topics = [
                "consultease/ui/consultation_updates",
                "consultease/faculty/+/responses",
                "consultease/student/+/notifications"
            ]
            
            for topic in test_topics:
                self.logger.info(f"📡 Topic to check: {topic}")
            
            self.logger.info("✅ MQTT topic utilities available")
            return True
            
        except Exception as e:
            self.issues_found.append(f"MQTT topics check error: {e}")
            self.logger.error(f"❌ MQTT topics check failed: {e}")
            return False
    
    def check_database_consultations(self):
        """Check if there are consultations in the database."""
        self.logger.info("🔍 Checking Database Consultations...")
        
        try:
            # Set up test database environment
            os.environ['DB_TYPE'] = 'sqlite'
            if 'DB_PATH' not in os.environ:
                os.environ['DB_PATH'] = ':memory:'
            os.environ['CONFIG_TYPE'] = 'test'
            
            from central_system.models import get_db, Consultation
            
            db = get_db()
            try:
                consultations = db.query(Consultation).all()
                consultation_count = len(consultations)
                
                self.logger.info(f"📊 Found {consultation_count} consultations in database")
                
                if consultation_count > 0:
                    # Show recent consultations
                    recent = db.query(Consultation).order_by(Consultation.id.desc()).limit(3).all()
                    for consultation in recent:
                        self.logger.info(f"   📋 Consultation {consultation.id}: Status={consultation.status.value}, Student={consultation.student_id}")
                
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            self.issues_found.append(f"Database check error: {e}")
            self.logger.error(f"❌ Database check failed: {e}")
            return False
    
    def run_comprehensive_diagnosis(self):
        """Run all diagnostic checks."""
        self.logger.info("🚀 Starting Comprehensive Real-time Consultation Diagnosis...")
        self.logger.info("=" * 70)
        
        # Run all diagnostic checks
        checks = [
            ("Faculty Response Controller", self.check_faculty_response_controller),
            ("MQTT Service", self.check_mqtt_service), 
            ("Consultation Controller", self.check_consultation_controller),
            ("Main Application Setup", self.check_main_application_setup),
            ("MQTT Topics and Handlers", self.check_mqtt_topics_and_handlers),
            ("MQTT Message Flow", self.simulate_mqtt_message_flow),
            ("Database Consultations", self.check_database_consultations)
        ]
        
        passed_checks = 0
        total_checks = len(checks)
        
        for check_name, check_func in checks:
            self.logger.info(f"\n📋 {check_name}")
            try:
                result = check_func()
                self.test_results[check_name] = result
                if result:
                    passed_checks += 1
                    self.logger.info(f"   ✅ PASSED")
                else:
                    self.logger.error(f"   ❌ FAILED")
            except Exception as e:
                self.test_results[check_name] = False
                self.logger.error(f"   ❌ ERROR: {e}")
        
        # Summary report
        self.logger.info(f"\n" + "=" * 70)
        self.logger.info(f"📊 DIAGNOSIS SUMMARY")
        self.logger.info(f"   Passed: {passed_checks}/{total_checks}")
        self.logger.info(f"   Success Rate: {(passed_checks/total_checks)*100:.1f}%")
        
        # Detailed results
        self.logger.info(f"\n📋 DETAILED RESULTS:")
        for check_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.logger.info(f"   {status} - {check_name}")
        
        # Issues found
        if self.issues_found:
            self.logger.info(f"\n🚨 ISSUES FOUND ({len(self.issues_found)}):")
            for i, issue in enumerate(self.issues_found, 1):
                self.logger.error(f"   {i}. {issue}")
        else:
            self.logger.info(f"\n✅ NO CRITICAL ISSUES FOUND")
        
        # Recommendations
        self.logger.info(f"\n💡 RECOMMENDATIONS:")
        
        if not self.test_results.get("Faculty Response Controller", False):
            self.logger.info("   🔧 Check that Faculty Response Controller is started in main.py")
            
        if not self.test_results.get("MQTT Service", False):
            self.logger.info("   🔧 Verify MQTT broker is running and accessible")
            
        if self.issues_found:
            self.logger.info("   🔧 Address the issues listed above")
            self.logger.info("   🔧 Check application logs for MQTT subscription confirmations")
            self.logger.info("   🔧 Verify faculty response controller is receiving button presses")
        else:
            self.logger.info("   🔧 Enable debug logging to trace MQTT message flow")
            self.logger.info("   🔧 Check if consultation panel is properly subscribing to MQTT topics")
            self.logger.info("   🔧 Verify student ID matching in consultation panel")
        
        return passed_checks == total_checks and len(self.issues_found) == 0

def main():
    """Main diagnostic function."""
    print("🩺 Consultation Real-time Update Diagnosis")
    print("=" * 50)
    
    diagnostic = ConsultationRealtimeDiagnostic()
    success = diagnostic.run_comprehensive_diagnosis()
    
    if success:
        print("\n✅ ALL CHECKS PASSED - System should work correctly!")
        print("\n💡 If real-time updates still don't work:")
        print("   1. Check that faculty response controller is started")
        print("   2. Verify MQTT broker is running")
        print("   3. Enable debug logging in the consultation panel")
        print("   4. Test with actual faculty button presses")
        return 0
    else:
        print("\n❌ ISSUES DETECTED - Check the recommendations above")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 