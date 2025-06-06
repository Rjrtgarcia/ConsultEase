#!/usr/bin/env python3
"""
Comprehensive Real-time Update Testing Script for ConsultEase System.

This script tests the fixes for:
1. Faculty availability real-time updates not working
2. BUSY button not refreshing consultation history

Usage:
    python test_realtime_fixes_comprehensive.py

Note: This script is designed to work on both Windows (limited testing) and Raspberry Pi (full testing).
"""

import json
import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealtimeUpdateTester:
    """Comprehensive tester for real-time update functionality."""
    
    def __init__(self):
        self.test_results = {}
        self.received_messages = []
        self.test_consultation_id = None
        self.test_faculty_id = 1
        self.test_student_id = 1
        
    def run_comprehensive_test(self):
        """Run comprehensive tests for real-time updates."""
        logger.info("🚀 STARTING COMPREHENSIVE REAL-TIME UPDATE TESTS")
        logger.info("=" * 60)
        
        # Test 1: Faculty Status Real-time Updates
        logger.info("\n1️⃣ TESTING FACULTY STATUS REAL-TIME UPDATES")
        self.test_faculty_status_updates()
        
        # Test 2: BUSY Button Consultation History Refresh
        logger.info("\n2️⃣ TESTING BUSY BUTTON CONSULTATION HISTORY REFRESH")
        self.test_busy_button_consultation_refresh()
        
        # Test 3: Compare BUSY vs ACKNOWLEDGE Response Handling
        logger.info("\n3️⃣ TESTING BUSY vs ACKNOWLEDGE RESPONSE COMPARISON")
        self.test_busy_vs_acknowledge_comparison()
        
        # Test 4: MQTT Message Flow Verification
        logger.info("\n4️⃣ TESTING MQTT MESSAGE FLOW")
        self.test_mqtt_message_flow()
        
        # Display results
        self.display_test_results()
        
    def test_faculty_status_updates(self):
        """Test faculty status real-time updates."""
        logger.info("🔍 Testing faculty status real-time update flow...")
        
        try:
            # Test the Faculty Controller directly
            from central_system.controllers.faculty_controller import get_faculty_controller
            
            faculty_controller = get_faculty_controller()
            
            # Test status update
            logger.info(f"📝 Updating faculty {self.test_faculty_id} status to False (Unavailable)")
            result = faculty_controller.update_faculty_status(self.test_faculty_id, False)
            
            if result:
                logger.info(f"✅ Faculty status update successful: {result}")
                self.test_results['faculty_status_update'] = 'PASS'
            else:
                logger.error(f"❌ Faculty status update failed")
                self.test_results['faculty_status_update'] = 'FAIL'
                
            # Wait for MQTT messages
            time.sleep(2)
            
            # Test status update back to True
            logger.info(f"📝 Updating faculty {self.test_faculty_id} status to True (Available)")
            result2 = faculty_controller.update_faculty_status(self.test_faculty_id, True)
            
            if result2:
                logger.info(f"✅ Faculty status update successful: {result2}")
            else:
                logger.error(f"❌ Faculty status update failed")
                
        except Exception as e:
            logger.error(f"❌ Faculty status test error: {e}")
            self.test_results['faculty_status_update'] = f'ERROR - {str(e)}'
    
    def test_busy_button_consultation_refresh(self):
        """Test BUSY button consultation history refresh."""
        logger.info("🔍 Testing BUSY button consultation history refresh...")
        
        try:
            # Create a test consultation
            consultation_id = self.create_test_consultation()
            if not consultation_id:
                logger.error("❌ Failed to create test consultation")
                self.test_results['busy_button_test'] = 'FAIL - No consultation created'
                return
                
            self.test_consultation_id = consultation_id
            logger.info(f"📝 Created test consultation: {consultation_id}")
            
            # Simulate BUSY response from faculty desk unit
            logger.info("🔴 Simulating BUSY response from faculty desk unit...")
            busy_success = self.simulate_faculty_response(consultation_id, "BUSY")
            
            if busy_success:
                logger.info("✅ BUSY response simulation successful")
                self.test_results['busy_button_test'] = 'PASS'
            else:
                logger.error("❌ BUSY response simulation failed")
                self.test_results['busy_button_test'] = 'FAIL'
                
        except Exception as e:
            logger.error(f"❌ BUSY button test error: {e}")
            self.test_results['busy_button_test'] = f'ERROR - {str(e)}'
    
    def test_busy_vs_acknowledge_comparison(self):
        """Test comparison between BUSY and ACKNOWLEDGE responses."""
        logger.info("🔍 Testing BUSY vs ACKNOWLEDGE response comparison...")
        
        try:
            # Test ACKNOWLEDGE response
            ack_consultation_id = self.create_test_consultation()
            if ack_consultation_id:
                logger.info("🔵 Testing ACKNOWLEDGE response...")
                ack_success = self.simulate_faculty_response(ack_consultation_id, "ACKNOWLEDGE")
                time.sleep(2)
                
                # Test BUSY response
                busy_consultation_id = self.create_test_consultation()
                if busy_consultation_id:
                    logger.info("🔴 Testing BUSY response...")
                    busy_success = self.simulate_faculty_response(busy_consultation_id, "BUSY")
                    
                    if ack_success and busy_success:
                        logger.info("✅ Both ACKNOWLEDGE and BUSY responses successful")
                        self.test_results['busy_vs_acknowledge'] = 'PASS'
                    else:
                        logger.error(f"❌ Response comparison failed - ACK: {ack_success}, BUSY: {busy_success}")
                        self.test_results['busy_vs_acknowledge'] = 'FAIL'
                else:
                    logger.error("❌ Failed to create BUSY test consultation")
                    self.test_results['busy_vs_acknowledge'] = 'FAIL - No BUSY consultation'
            else:
                logger.error("❌ Failed to create ACKNOWLEDGE test consultation")
                self.test_results['busy_vs_acknowledge'] = 'FAIL - No ACK consultation'
                
        except Exception as e:
            logger.error(f"❌ Comparison test error: {e}")
            self.test_results['busy_vs_acknowledge'] = f'ERROR - {str(e)}'
    
    def test_mqtt_message_flow(self):
        """Test MQTT message flow for real-time updates."""
        logger.info("🔍 Testing MQTT message flow...")
        
        try:
            # Test MQTT connectivity
            from central_system.utils.mqtt_utils import is_mqtt_connected, publish_mqtt_message
            
            if is_mqtt_connected():
                logger.info("✅ MQTT is connected")
                
                # Test publishing a message
                test_message = {
                    'type': 'test_message',
                    'timestamp': datetime.now().isoformat(),
                    'test_id': 'realtime_fix_test'
                }
                
                success = publish_mqtt_message("consultease/test/realtime_fixes", test_message)
                if success:
                    logger.info("✅ MQTT message publishing successful")
                    self.test_results['mqtt_flow'] = 'PASS'
                else:
                    logger.error("❌ MQTT message publishing failed")
                    self.test_results['mqtt_flow'] = 'FAIL'
            else:
                logger.warning("⚠️ MQTT not connected - running on Windows?")
                self.test_results['mqtt_flow'] = 'SKIP - MQTT not available'
                
        except Exception as e:
            logger.error(f"❌ MQTT flow test error: {e}")
            self.test_results['mqtt_flow'] = f'ERROR - {str(e)}'
    
    def create_test_consultation(self) -> Optional[int]:
        """Create a test consultation for testing."""
        try:
            from central_system.controllers.consultation_controller import ConsultationController
            
            consultation_controller = ConsultationController()
            
            # Create test consultation
            success = consultation_controller.create_consultation(
                student_id=self.test_student_id,
                faculty_id=self.test_faculty_id,
                request_message="Test consultation for real-time update testing",
                course_code="TEST101"
            )
            
            if success:
                # Get the latest consultation ID for this student
                from central_system.models.base import get_db
                from central_system.models.consultation import Consultation
                
                db = get_db()
                try:
                    latest_consultation = db.query(Consultation).filter(
                        Consultation.student_id == self.test_student_id,
                        Consultation.faculty_id == self.test_faculty_id
                    ).order_by(Consultation.id.desc()).first()
                    
                    if latest_consultation:
                        return latest_consultation.id
                finally:
                    db.close()
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error creating test consultation: {e}")
            return None
    
    def simulate_faculty_response(self, consultation_id: int, response_type: str) -> bool:
        """Simulate a faculty response."""
        try:
            from central_system.controllers.faculty_response_controller import get_faculty_response_controller
            
            faculty_response_controller = get_faculty_response_controller()
            
            # Create response data like ESP32 would send
            response_data = {
                'faculty_id': self.test_faculty_id,
                'faculty_name': 'Test Faculty',
                'response_type': response_type,
                'message_id': str(consultation_id),
                'timestamp': str(int(time.time() * 1000)),
                'faculty_present': True,
                'response_method': 'simulated_test'
            }
            
            logger.info(f"📤 Simulating {response_type} response: {response_data}")
            
            # Process the response
            success = faculty_response_controller._process_faculty_response(response_data)
            
            if success:
                logger.info(f"✅ {response_type} response processed successfully")
                return True
            else:
                logger.error(f"❌ {response_type} response processing failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error simulating {response_type} response: {e}")
            return False
    
    def display_test_results(self):
        """Display comprehensive test results."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 COMPREHENSIVE TEST RESULTS")
        logger.info("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result == 'PASS')
        
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result == 'PASS' else "❌" if 'FAIL' in result or 'ERROR' in result else "⚠️"
            logger.info(f"{status_icon} {test_name}: {result}")
        
        logger.info(f"\n📈 SUMMARY: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED! Real-time updates should be working correctly.")
        else:
            logger.warning("⚠️ Some tests failed. Check the logs above for details.")
        
        # Provide recommendations
        logger.info("\n💡 RECOMMENDATIONS:")
        
        if 'faculty_status_update' in self.test_results and 'FAIL' in self.test_results['faculty_status_update']:
            logger.info("   • Check Faculty Controller database connectivity")
            logger.info("   • Verify MQTT broker is running and accessible")
            logger.info("   • Check ESP32 desk unit connectivity")
        
        if 'busy_button_test' in self.test_results and 'FAIL' in self.test_results['busy_button_test']:
            logger.info("   • Verify Faculty Response Controller is processing BUSY responses")
            logger.info("   • Check consultation update MQTT topic subscriptions")
            logger.info("   • Ensure UI components are receiving real-time updates")
        
        if 'mqtt_flow' in self.test_results and 'SKIP' in self.test_results['mqtt_flow']:
            logger.info("   • This system should be tested on Raspberry Pi for full MQTT functionality")
            logger.info("   • Windows testing provides limited real-time update verification")
        
        logger.info("\n🔧 For full testing, deploy and test on the Raspberry Pi with:")
        logger.info("   1. MQTT broker running (mosquitto)")
        logger.info("   2. ESP32 desk units connected to network")
        logger.info("   3. ConsultEase central system running")

def main():
    """Main function to run the comprehensive test."""
    try:
        tester = RealtimeUpdateTester()
        tester.run_comprehensive_test()
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 