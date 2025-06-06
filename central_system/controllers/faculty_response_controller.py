"""
Faculty Response Controller for ConsultEase system.
Handles faculty responses (ACKNOWLEDGE, BUSY) from faculty desk units.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from ..models.base import get_db
from ..models.consultation import Consultation, ConsultationStatus
from ..utils.mqtt_utils import subscribe_to_topic, publish_mqtt_message
from ..utils.mqtt_topics import MQTTTopics

logger = logging.getLogger(__name__)


class FacultyResponseController:
    """
    Controller for handling faculty responses from desk units.
    """

    def __init__(self):
        """
        Initialize the faculty response controller.
        """
        self.callbacks = []

    def start(self):
        """
        Start the faculty response controller and subscribe to faculty response topics.
        """
        logger.info("Starting Faculty Response controller")
        
        # Add debug logging to confirm subscription setup
        logger.info("🔔 Subscribing to faculty response topics...")

        # Subscribe to faculty response updates using async MQTT service
        try:
            subscribe_to_topic("consultease/faculty/+/responses", self.handle_faculty_response)
            logger.info("✅ Successfully subscribed to: consultease/faculty/+/responses")
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to faculty responses: {e}")

        # Subscribe to faculty heartbeat for NTP sync status
        try:
            subscribe_to_topic("consultease/faculty/+/heartbeat", self.handle_faculty_heartbeat)
            logger.info("✅ Successfully subscribed to: consultease/faculty/+/heartbeat")
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to faculty heartbeat: {e}")
            
        logger.info("🎯 Faculty Response Controller started and waiting for messages...")

    def stop(self):
        """
        Stop the faculty response controller.
        """
        logger.info("Stopping Faculty Response controller")

    def register_callback(self, callback):
        """
        Register a callback to be called when a faculty response is received.

        Args:
            callback (callable): Function that takes response data as argument
        """
        self.callbacks.append(callback)
        logger.info(f"Registered Faculty Response controller callback: {callback.__name__}")

    def _notify_callbacks(self, response_data):
        """
        Notify all registered callbacks with the response data.

        Args:
            response_data (dict): Faculty response data
        """
        for callback in self.callbacks:
            try:
                callback(response_data)
            except Exception as e:
                logger.error(f"Error in Faculty Response controller callback: {str(e)}")

    def handle_faculty_response(self, topic: str, data: Any):
        """
        Handle faculty response from MQTT.

        Args:
            topic (str): MQTT topic
            data (dict or str): Response data
        """
        # DEBUG: Log every message received to diagnose MQTT connectivity
        logger.info(f"🔥 FACULTY RESPONSE HANDLER TRIGGERED - Topic: {topic}, Data Type: {type(data)}")
        logger.info(f"🔥 Raw Data: {data}")
        
        try:
            # Parse response data
            if isinstance(data, str):
                try:
                    response_data = json.loads(data)
                    logger.info(f"🔥 Parsed JSON data: {response_data}")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in faculty response: {data}")
                    return
            elif isinstance(data, dict):
                response_data = data
                logger.info(f"🔥 Dict data received: {response_data}")
            else:
                logger.error(f"Invalid data type for faculty response: {type(data)}")
                return

            # Extract faculty ID from topic
            faculty_id = None
            try:
                faculty_id = int(topic.split("/")[2])
                logger.info(f"🔥 Extracted faculty ID: {faculty_id}")
            except (IndexError, ValueError):
                logger.error(f"Could not extract faculty ID from topic: {topic}")
                return

            # Validate required fields
            required_fields = ['faculty_id', 'response_type', 'message_id']
            for field in required_fields:
                if field not in response_data:
                    logger.error(f"Missing required field '{field}' in faculty response")
                    return

            response_type = response_data.get('response_type')
            message_id = response_data.get('message_id')
            faculty_name = response_data.get('faculty_name', 'Unknown')

            logger.info(f"Received {response_type} response from faculty {faculty_id} ({faculty_name}) for message {message_id}")

            # Process the response
            success = self._process_faculty_response(response_data)

            if success:
                # Notify callbacks
                self._notify_callbacks(response_data)

                # Publish notification about the response
                notification = {
                    'type': 'faculty_response',
                    'faculty_id': faculty_id,
                    'faculty_name': faculty_name,
                    'response_type': response_type,
                    'message_id': message_id,
                    'timestamp': datetime.now().isoformat()
                }
                publish_mqtt_message(MQTTTopics.SYSTEM_NOTIFICATIONS, notification)

        except Exception as e:
            logger.error(f"Error handling faculty response: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    def handle_faculty_heartbeat(self, topic: str, data: Any):
        """
        Handle faculty heartbeat messages for NTP sync status and system health.

        Args:
            topic (str): MQTT topic
            data (dict or str): Heartbeat data
        """
        try:
            # Parse heartbeat data
            if isinstance(data, str):
                try:
                    heartbeat_data = json.loads(data)
                except json.JSONDecodeError:
                    logger.debug(f"Non-JSON heartbeat data: {data}")
                    return
            elif isinstance(data, dict):
                heartbeat_data = data
            else:
                return

            # Extract faculty ID from topic
            faculty_id = None
            try:
                faculty_id = int(topic.split("/")[2])
            except (IndexError, ValueError):
                return

            # Log NTP sync status if present
            if 'ntp_sync_status' in heartbeat_data:
                ntp_status = heartbeat_data['ntp_sync_status']
                if ntp_status in ['FAILED', 'SYNCING']:
                    logger.warning(f"Faculty {faculty_id} NTP sync status: {ntp_status}")
                elif ntp_status == 'SYNCED':
                    logger.debug(f"Faculty {faculty_id} NTP sync: {ntp_status}")

            # Log system health issues
            if 'free_heap' in heartbeat_data:
                free_heap = heartbeat_data.get('free_heap', 0)
                if free_heap < 50000:  # Less than 50KB free
                    logger.warning(f"Faculty {faculty_id} low memory: {free_heap} bytes")

        except Exception as e:
            logger.debug(f"Error processing faculty heartbeat: {str(e)}")

    def _process_faculty_response(self, response_data: Dict[str, Any]) -> bool:
        """
        Process faculty response and update consultation status with enhanced real-time support.

        Args:
            response_data (dict): Faculty response data

        Returns:
            bool: True if response was processed successfully
        """
        try:
            faculty_id = response_data.get('faculty_id')
            response_type = response_data.get('response_type')
            message_id = response_data.get('message_id')

            logger.info(f"🔄 [FACULTY RESPONSE] Processing {response_type} response from faculty {faculty_id} for message {message_id}")

            if not all([faculty_id, response_type, message_id]):
                logger.error(f"❌ [FACULTY RESPONSE] Missing required fields in response data: {response_data}")
                return False

            # Get consultation from database
            db = get_db()
            try:
                consultation = db.query(Consultation).filter(
                    Consultation.id == int(message_id)
                ).first()

                if not consultation:
                    logger.error(f"❌ [FACULTY RESPONSE] Consultation {message_id} not found")
                    return False

                # Check if consultation is in a state that can be responded to
                if consultation.status not in [ConsultationStatus.PENDING]:
                    logger.warning(f"⚠️ [FACULTY RESPONSE] Consultation {message_id} is not pending (status: {consultation.status.value})")
                    # Still process the response for logging purposes
                    
                logger.info(f"📋 [FACULTY RESPONSE] Processing response '{response_type}' for {consultation.status.value} consultation {message_id}")

                # Map response types to consultation statuses
                new_status_enum = None
                if response_type == "ACKNOWLEDGE" or response_type == "ACCEPTED":
                    new_status_enum = ConsultationStatus.ACCEPTED
                    logger.info(f"✅ [FACULTY RESPONSE] Mapping ACKNOWLEDGE/ACCEPTED to ACCEPTED status")
                elif response_type == "BUSY" or response_type == "UNAVAILABLE":
                    new_status_enum = ConsultationStatus.BUSY
                    logger.info(f"⏰ [FACULTY RESPONSE] Mapping BUSY/UNAVAILABLE to BUSY status")
                elif response_type == "REJECTED" or response_type == "DECLINED":
                    new_status_enum = ConsultationStatus.CANCELLED
                    logger.info(f"❌ [FACULTY RESPONSE] Mapping REJECTED/DECLINED to CANCELLED status")
                elif response_type == "COMPLETED":
                    new_status_enum = ConsultationStatus.COMPLETED
                    logger.info(f"✅ [FACULTY RESPONSE] Mapping COMPLETED to COMPLETED status")

                if new_status_enum:
                    # Store consultation details before updating for real-time notifications
                    consultation_details = {
                        'id': consultation.id,
                        'student_id': consultation.student_id,
                        'student_name': consultation.student.name if consultation.student else 'Unknown',
                        'faculty_id': consultation.faculty_id,
                        'faculty_name': consultation.faculty.name if consultation.faculty else 'Unknown',
                        'course_code': consultation.course_code,
                        'request_message': consultation.request_message,
                        'old_status': consultation.status.value,
                        'new_status': new_status_enum.value,
                        'response_type': response_type
                    }
                    
                    logger.info(f"🔄 [FACULTY RESPONSE] Updating consultation {consultation.id} from {consultation_details['old_status']} to {consultation_details['new_status']}")
                    
                    # Import ConsultationController locally to avoid circular imports
                    from .consultation_controller import ConsultationController as SystemConsultationController
                    cc = SystemConsultationController()
                    updated_consultation = cc.update_consultation_status(consultation.id, new_status_enum)
                    
                    if updated_consultation:
                        logger.info(f"✅ [FACULTY RESPONSE] Successfully updated consultation {consultation.id} to status {new_status_enum.value}")
                        
                        # Publish comprehensive real-time faculty response notifications
                        self._publish_faculty_response_notification(consultation_details)
                        
                        # Add consultation_id and student_id to response_data for callbacks, if not already there
                        response_data['consultation_id'] = consultation.id 
                        response_data['student_id'] = consultation.student_id
                        
                        logger.info(f"✅ [FACULTY RESPONSE] {response_type} response for consultation {consultation.id} processed successfully")
                        return True
                    else:
                        logger.error(f"❌ [FACULTY RESPONSE] Failed to update consultation {consultation.id} to {new_status_enum.value}")
                        return False
                else:
                    logger.warning(f"⚠️ [FACULTY RESPONSE] Unknown or unhandled response_type: '{response_type}' for consultation {consultation.id}")
                    return False
            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ [FACULTY RESPONSE] Critical error in _process_faculty_response: {str(e)}")
            import traceback
            logger.error(f"❌ [FACULTY RESPONSE] Traceback: {traceback.format_exc()}")
            return False

    def _publish_faculty_response_notification(self, consultation_details):
        """
        Publish comprehensive real-time faculty response notifications to all relevant parties.
        
        Args:
            consultation_details (dict): Consultation details for notifications
        """
        try:
            from ..utils.mqtt_utils import publish_mqtt_message
            import datetime
            
            timestamp = datetime.datetime.now().isoformat()
            
            logger.info(f"📤 [FACULTY RESPONSE] Publishing notifications for consultation {consultation_details['id']} ({consultation_details['response_type']})")
            
            # 1. Notify the central system for real-time UI updates
            ui_update_topic = "consultease/ui/consultation_updates"
            ui_message = {
                'type': 'consultation_status_changed',
                'consultation_id': consultation_details['id'],
                'student_id': consultation_details['student_id'],
                'faculty_id': consultation_details['faculty_id'],
                'old_status': consultation_details['old_status'],
                'new_status': consultation_details['new_status'],
                'response_type': consultation_details['response_type'],
                'timestamp': timestamp,
                'trigger': 'faculty_response'
            }
            
            publish_success_ui = publish_mqtt_message(
                ui_update_topic,
                ui_message,
                qos=1
            )
            
            # 2. Student-specific notification
            student_notification_topic = f"consultease/student/{consultation_details['student_id']}/notifications"
            student_message = {
                'type': 'consultation_response',
                'consultation_id': consultation_details['id'],
                'faculty_name': consultation_details['faculty_name'],
                'course_code': consultation_details['course_code'],
                'response_type': consultation_details['response_type'],
                'new_status': consultation_details['new_status'],
                'responded_at': timestamp
            }
            
            publish_success_student = publish_mqtt_message(
                student_notification_topic,
                student_message,
                qos=1
            )
            
            # 3. General system notification
            system_notification_topic = "consultease/system/notifications"
            system_message = {
                'type': 'faculty_response_received',
                'consultation_id': consultation_details['id'],
                'student_id': consultation_details['student_id'],
                'student_name': consultation_details['student_name'],
                'faculty_id': consultation_details['faculty_id'],
                'faculty_name': consultation_details['faculty_name'],
                'response_type': consultation_details['response_type'],
                'new_status': consultation_details['new_status'],
                'responded_at': timestamp
            }
            
            publish_success_system = publish_mqtt_message(
                system_notification_topic,
                system_message,
                qos=0
            )
            
            # Enhanced logging for debugging
            logger.info(f"📤 [FACULTY RESPONSE] Notification results:")
            logger.info(f"   📱 UI Update ({ui_update_topic}): {'✅ SUCCESS' if publish_success_ui else '❌ FAILED'}")
            logger.info(f"   👤 Student Notification ({student_notification_topic}): {'✅ SUCCESS' if publish_success_student else '❌ FAILED'}")
            logger.info(f"   🌐 System Notification ({system_notification_topic}): {'✅ SUCCESS' if publish_success_system else '❌ FAILED'}")
            
            # Overall success check
            if publish_success_ui or publish_success_student or publish_success_system:
                logger.info(f"✅ [FACULTY RESPONSE] At least one notification published successfully for {consultation_details['response_type']} response")
            else:
                logger.error(f"❌ [FACULTY RESPONSE] All notification publishing failed for {consultation_details['response_type']} response")
            
        except Exception as e:
            logger.error(f"❌ [FACULTY RESPONSE] Error publishing faculty response notifications: {str(e)}")
            import traceback
            logger.error(f"❌ [FACULTY RESPONSE] Traceback: {traceback.format_exc()}")

    def get_response_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about faculty responses.

        Returns:
            dict: Response statistics
        """
        try:
            db = get_db()
            try:
                # Get response statistics from the database
                total_acknowledged = db.query(Consultation).filter(
                    Consultation.status == ConsultationStatus.ACCEPTED
                ).count()

                total_busy = db.query(Consultation).filter(
                    Consultation.status == ConsultationStatus.BUSY
                ).count()

                total_declined = db.query(Consultation).filter(
                    Consultation.status == ConsultationStatus.CANCELLED
                ).count()

                total_pending = db.query(Consultation).filter(
                    Consultation.status == ConsultationStatus.PENDING
                ).count()

                total_completed = db.query(Consultation).filter(
                    Consultation.status == ConsultationStatus.COMPLETED
                ).count()

                total_responded = total_acknowledged + total_busy + total_declined
                total_all = total_responded + total_pending + total_completed

                return {
                    'total_acknowledged': total_acknowledged,
                    'total_busy': total_busy,
                    'total_declined': total_declined,
                    'total_completed': total_completed,
                    'total_pending': total_pending,
                    'total_responded': total_responded,
                    'response_rate': (total_responded / max(1, total_all)) * 100
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error getting response statistics: {str(e)}")
            return {
                'total_acknowledged': 0,
                'total_busy': 0,
                'total_declined': 0,
                'total_completed': 0,
                'total_pending': 0,
                'total_responded': 0,
                'response_rate': 0
            }


# Global controller instance
_faculty_response_controller: Optional[FacultyResponseController] = None


def get_faculty_response_controller() -> FacultyResponseController:
    """Get the global faculty response controller instance."""
    global _faculty_response_controller
    if _faculty_response_controller is None:
        _faculty_response_controller = FacultyResponseController()
    return _faculty_response_controller
