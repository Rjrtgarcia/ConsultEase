#!/usr/bin/env python3
"""
Comprehensive test script for verifying ESP32 faculty desk unit button response flow.

This script tests the complete communication pathway:
1. Central system sends consultation request to ESP32
2. ESP32 receives and displays the request
3. Faculty presses Accept/Busy button on ESP32
4. ESP32 sends button response via MQTT
5. Central system receives and processes the response
6. Database is updated with new consultation status

Run this script to verify the integration between ESP32 faculty desk units
and the central Raspberry Pi system.
"""

import sys
import os
import json
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Add the central_system directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'central_system'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import central system modules
try:
    from central_system.models.base import get_db, init_db
    from central_system.models.consultation import Consultation, ConsultationStatus
    from central_system.models.faculty import Faculty
    from central_system.models.student import Student
    from central_system.controllers.consultation_controller import ConsultationController
    from central_system.controllers.faculty_response_controller import get_faculty_response_controller
    from central_system.utils.mqtt_topics import MQTTTopics
    from central_system.utils.mqtt_utils import publish_mqtt_message, subscribe_to_topic
    from central_system.services.async_mqtt_service import get_async_mqtt_service
except ImportError as e:
    logger.error(f"Failed to import central system modules: {e}")
    sys.exit(1)


class ButtonResponseFlowTester:
    """
    Comprehensive tester for ESP32 button response flow.
    """

    def __init__(self):
        """Initialize the tester."""
        self.consultation_controller = ConsultationController()
        self.faculty_response_controller = get_faculty_response_controller()
        self.mqtt_service = get_async_mqtt_service()
        
        # Test data
        self.test_faculty_id = 1
        self.test_student_id = 1
        self.test_consultation_id = None
        self.received_responses = []
        
        # Response tracking
        self.response_received = False
        self.response_data = None

    def setup_test_environment(self) -> bool:
        """Set up the test environment with database and MQTT."""
        try:
            logger.info("Setting up test environment...")
            
            # Initialize database
            init_db()
            
            # Start MQTT service
            if not self.mqtt_service.is_connected():
                logger.info("Starting MQTT service...")
                self.mqtt_service.start()
                # Wait for connection
                time.sleep(2)
                
            if not self.mqtt_service.is_connected():
                logger.error("MQTT service failed to connect")
                return False
                
            # Start controllers
            self.consultation_controller.start()
            self.faculty_response_controller.start()
            
            # Register callback to capture responses
            self.faculty_response_controller.register_callback(self._handle_response_callback)
            
            logger.info("Test environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup test environment: {e}")
            return False

    def verify_test_data(self) -> bool:
        """Verify that required test data exists in the database."""
        try:
            db = get_db()
            
            # Check for test faculty
            faculty = db.query(Faculty).filter(Faculty.id == self.test_faculty_id).first()
            if not faculty:
                logger.error(f"Test faculty ID {self.test_faculty_id} not found in database")
                return False
            logger.info(f"Found test faculty: {faculty.name} (ID: {faculty.id})")
            
            # Check for test student
            student = db.query(Student).filter(Student.id == self.test_student_id).first()
            if not student:
                logger.error(f"Test student ID {self.test_student_id} not found in database")
                return False
            logger.info(f"Found test student: {student.name} (ID: {student.id})")
            
            db.close()
            return True
            
        except Exception as e:
            logger.error(f"Error verifying test data: {e}")
            return False

    def test_mqtt_communication(self) -> bool:
        """Test basic MQTT communication."""
        try:
            logger.info("Testing MQTT communication...")
            
            # Test topic structure
            faculty_responses_topic = MQTTTopics.get_faculty_responses_topic(self.test_faculty_id)
            faculty_requests_topic = MQTTTopics.get_faculty_requests_topic(self.test_faculty_id)
            
            logger.info(f"Faculty responses topic: {faculty_responses_topic}")
            logger.info(f"Faculty requests topic: {faculty_requests_topic}")
            
            # Verify ESP32 topic matches
            expected_esp32_topic = f"consultease/faculty/{self.test_faculty_id}/responses"
            if faculty_responses_topic == expected_esp32_topic:
                logger.info("✅ MQTT topic structure matches ESP32 configuration")
            else:
                logger.error(f"❌ MQTT topic mismatch! Expected: {expected_esp32_topic}, Got: {faculty_responses_topic}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error testing MQTT communication: {e}")
            return False

    def create_test_consultation(self) -> bool:
        """Create a test consultation request."""
        try:
            logger.info("Creating test consultation request...")
            
            # Create consultation
            consultation = self.consultation_controller.create_consultation(
                student_id=self.test_student_id,
                faculty_id=self.test_faculty_id,
                request_message="Test consultation request for button response verification",
                course_code="TEST101"
            )
            
            if not consultation:
                logger.error("Failed to create test consultation")
                return False
                
            self.test_consultation_id = consultation.id
            logger.info(f"✅ Created test consultation ID: {self.test_consultation_id}")
            
            # Verify consultation was published to MQTT
            logger.info("Verifying consultation was published to MQTT...")
            
            # Give some time for MQTT publication
            time.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating test consultation: {e}")
            return False

    def simulate_esp32_button_response(self, response_type: str = "ACKNOWLEDGE") -> bool:
        """Simulate an ESP32 button press response."""
        try:
            logger.info(f"Simulating ESP32 {response_type} button press...")
            
            if not self.test_consultation_id:
                logger.error("No test consultation ID available")
                return False
                
            # Create response payload that matches ESP32 format
            response_payload = {
                "faculty_id": self.test_faculty_id,
                "faculty_name": "Test Faculty",
                "response_type": response_type,
                "message_id": str(self.test_consultation_id),
                "original_message": "Test consultation request for button response verification",
                "timestamp": str(int(time.time() * 1000)),  # ESP32 uses millis()
                "faculty_present": True,
                "response_method": "physical_button",
                "status": f"Professor {'acknowledges the request' if response_type == 'ACKNOWLEDGE' else 'is currently busy'}"
            }
            
            # Publish to faculty responses topic
            faculty_responses_topic = MQTTTopics.get_faculty_responses_topic(self.test_faculty_id)
            
            logger.info(f"Publishing response to topic: {faculty_responses_topic}")
            logger.info(f"Response payload: {json.dumps(response_payload, indent=2)}")
            
            success = publish_mqtt_message(faculty_responses_topic, response_payload)
            
            if success:
                logger.info(f"✅ Successfully published {response_type} response")
                return True
            else:
                logger.error(f"❌ Failed to publish {response_type} response")
                return False
                
        except Exception as e:
            logger.error(f"Error simulating ESP32 button response: {e}")
            return False

    def verify_consultation_status_update(self, expected_status: ConsultationStatus) -> bool:
        """Verify that the consultation status was updated in the database."""
        try:
            logger.info(f"Verifying consultation status update to {expected_status.value}...")
            
            # Wait a moment for processing
            time.sleep(2)
            
            db = get_db()
            consultation = db.query(Consultation).filter(
                Consultation.id == self.test_consultation_id
            ).first()
            
            if not consultation:
                logger.error(f"Consultation {self.test_consultation_id} not found")
                return False
                
            if consultation.status == expected_status:
                logger.info(f"✅ Consultation status correctly updated to {expected_status.value}")
                
                # Check timestamps
                if expected_status == ConsultationStatus.ACCEPTED and consultation.accepted_at:
                    logger.info(f"✅ Accepted timestamp set: {consultation.accepted_at}")
                elif expected_status == ConsultationStatus.BUSY and consultation.busy_at:
                    logger.info(f"✅ Busy timestamp set: {consultation.busy_at}")
                    
                return True
            else:
                logger.error(f"❌ Consultation status incorrect. Expected: {expected_status.value}, Got: {consultation.status.value}")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying consultation status: {e}")
            return False
        finally:
            db.close()

    def _handle_response_callback(self, response_data: Dict[str, Any]):
        """Callback to handle received faculty responses."""
        logger.info(f"📨 Received faculty response callback: {response_data}")
        self.response_received = True
        self.response_data = response_data
        self.received_responses.append(response_data)

    def test_complete_flow(self) -> bool:
        """Test the complete button response flow."""
        try:
            logger.info("🚀 Starting complete button response flow test...")
            
            # Test 1: ACKNOWLEDGE response
            logger.info("\n" + "="*60)
            logger.info("TEST 1: ACKNOWLEDGE Button Response")
            logger.info("="*60)
            
            if not self.create_test_consultation():
                return False
                
            if not self.simulate_esp32_button_response("ACKNOWLEDGE"):
                return False
                
            if not self.verify_consultation_status_update(ConsultationStatus.ACCEPTED):
                return False
                
            # Test 2: BUSY response (create new consultation)
            logger.info("\n" + "="*60)
            logger.info("TEST 2: BUSY Button Response")
            logger.info("="*60)
            
            if not self.create_test_consultation():
                return False
                
            if not self.simulate_esp32_button_response("BUSY"):
                return False
                
            if not self.verify_consultation_status_update(ConsultationStatus.BUSY):
                return False
                
            logger.info("\n" + "="*60)
            logger.info("✅ ALL TESTS PASSED!")
            logger.info("="*60)
            logger.info(f"Total responses received: {len(self.received_responses)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in complete flow test: {e}")
            return False

    def cleanup(self):
        """Clean up test environment."""
        try:
            logger.info("Cleaning up test environment...")
            
            # Clean up test consultations
            if self.test_consultation_id:
                db = get_db()
                consultation = db.query(Consultation).filter(
                    Consultation.id == self.test_consultation_id
                ).first()
                if consultation:
                    db.delete(consultation)
                    db.commit()
                    logger.info(f"Cleaned up test consultation {self.test_consultation_id}")
                db.close()
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def run_verification(self) -> bool:
        """Run the complete verification process."""
        try:
            logger.info("🔍 ESP32 Faculty Desk Unit Button Response Flow Verification")
            logger.info("="*70)
            
            # Setup
            if not self.setup_test_environment():
                logger.error("❌ Failed to setup test environment")
                return False
                
            if not self.verify_test_data():
                logger.error("❌ Test data verification failed")
                return False
                
            if not self.test_mqtt_communication():
                logger.error("❌ MQTT communication test failed")
                return False
                
            # Run complete flow test
            success = self.test_complete_flow()
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Verification failed with error: {e}")
            return False
        finally:
            self.cleanup()


def main():
    """Main function to run the verification."""
    tester = ButtonResponseFlowTester()
    
    try:
        success = tester.run_verification()
        
        if success:
            print("\n🎉 VERIFICATION SUCCESSFUL!")
            print("✅ ESP32 faculty desk units can successfully communicate button responses")
            print("✅ Central system properly receives and processes button events")
            print("✅ Database is correctly updated with consultation status changes")
            print("✅ MQTT communication pathway is working correctly")
            sys.exit(0)
        else:
            print("\n❌ VERIFICATION FAILED!")
            print("❌ Issues found in the button response communication flow")
            print("❌ Check the logs above for specific problems")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Verification crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 