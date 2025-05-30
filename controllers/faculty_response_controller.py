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

        # Subscribe to faculty response updates using async MQTT service
        subscribe_to_topic("consultease/faculty/+/responses", self.handle_faculty_response)

        # Subscribe to faculty heartbeat for NTP sync status
        subscribe_to_topic("consultease/faculty/+/heartbeat", self.handle_faculty_heartbeat)

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
        try:
            # Parse response data
            if isinstance(data, str):
                try:
                    response_data = json.loads(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in faculty response: {data}")
                    return
            elif isinstance(data, dict):
                response_data = data
            else:
                logger.error(f"Invalid data type for faculty response: {type(data)}")
                return

            # Extract faculty ID from topic
            faculty_id = None
            try:
                faculty_id = int(topic.split("/")[2])
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
        Process faculty response and update consultation status.

        Args:
            response_data (dict): Faculty response data

        Returns:
            bool: True if processed successfully
        """
        try:
            faculty_id = response_data.get('faculty_id')
            response_type = response_data.get('response_type')
            message_id = response_data.get('message_id')
            original_message = response_data.get('original_message', '')

            # Find the most recent pending consultation for this faculty
            db = get_db()
            try:
                consultation = db.query(Consultation).filter(
                    Consultation.faculty_id == faculty_id,
                    Consultation.status == ConsultationStatus.PENDING
                ).order_by(Consultation.requested_at.desc()).first()

                if not consultation:
                    logger.warning(f"No pending consultation found for faculty {faculty_id}")
                    return False

                # Update consultation status based on response type
                if response_type == 'ACKNOWLEDGE':
                    consultation.status = ConsultationStatus.ACCEPTED
                    consultation.accepted_at = datetime.now()
                    logger.info(f"Consultation {consultation.id} acknowledged by faculty {faculty_id}")

                elif response_type == 'BUSY':
                    consultation.status = ConsultationStatus.DECLINED
                    consultation.completed_at = datetime.now()
                    logger.info(f"Consultation {consultation.id} declined (busy) by faculty {faculty_id}")

                else:
                    logger.warning(f"Unknown response type: {response_type}")
                    return False

                db.commit()

                # Add response metadata to the response data for callbacks
                response_data['consultation_id'] = consultation.id
                response_data['student_id'] = consultation.student_id
                response_data['processed_at'] = datetime.now().isoformat()

                return True

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error processing faculty response: {str(e)}")
            return False

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

                total_declined = db.query(Consultation).filter(
                    Consultation.status == ConsultationStatus.DECLINED
                ).count()

                total_pending = db.query(Consultation).filter(
                    Consultation.status == ConsultationStatus.PENDING
                ).count()

                return {
                    'total_acknowledged': total_acknowledged,
                    'total_declined': total_declined,
                    'total_pending': total_pending,
                    'response_rate': (total_acknowledged + total_declined) / max(1, total_acknowledged + total_declined + total_pending) * 100
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error getting response statistics: {str(e)}")
            return {
                'total_acknowledged': 0,
                'total_declined': 0,
                'total_pending': 0,
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
