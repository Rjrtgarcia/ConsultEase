"""
MQTT utility functions for ConsultEase system.
Provides convenient access to the async MQTT service.
"""

import logging
from typing import Any, Optional
from ..services.async_mqtt_service import get_async_mqtt_service

logger = logging.getLogger(__name__)


def get_mqtt_service():
    """
    Get the global async MQTT service instance.

    Returns:
        AsyncMQTTService: The global async MQTT service instance
    """
    return get_async_mqtt_service()


def publish_mqtt_message(topic: str, data: Any, qos: int = 1, retain: bool = False) -> bool:
    """
    Convenience function for publishing MQTT messages asynchronously.

    Args:
        topic: MQTT topic to publish to
        data: Data to publish (will be JSON encoded if not string)
        qos: Quality of service level (0, 1, or 2)
        retain: Whether to retain the message on the broker

    Returns:
        bool: True if message was queued successfully, False otherwise
    """
    try:
        service = get_mqtt_service()
        service.publish_async(topic, data, qos, retain)
        logger.debug(f"Queued MQTT message for topic: {topic}")
        return True
    except Exception as e:
        logger.error(f"Failed to queue MQTT message for topic {topic}: {e}")
        return False


def subscribe_to_topic(topic: str, callback: callable) -> bool:
    """
    Subscribe to an MQTT topic with a callback function.

    Args:
        topic: MQTT topic to subscribe to
        callback: Function to call when message is received

    Returns:
        bool: True if subscription was successful, False otherwise
    """
    try:
        service = get_mqtt_service()
        service.register_topic_handler(topic, callback)
        logger.info(f"✅ Subscribed to MQTT topic: {topic}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to subscribe to topic {topic}: {e}")
        return False


def get_mqtt_stats() -> dict:
    """
    Get MQTT service statistics.

    Returns:
        dict: Statistics about the MQTT service
    """
    try:
        service = get_mqtt_service()
        return service.get_stats()
    except Exception as e:
        logger.error(f"Failed to get MQTT stats: {e}")
        return {}


def is_mqtt_connected() -> bool:
    """
    Check if MQTT service is connected.

    Returns:
        bool: True if connected, False otherwise
    """
    try:
        service = get_mqtt_service()
        return service.is_connected
    except Exception as e:
        logger.error(f"Failed to check MQTT connection status: {e}")
        return False


def publish_faculty_status(faculty_id: int, status: str, additional_data: dict = None) -> bool:
    """
    Publish faculty status update.

    Args:
        faculty_id: ID of the faculty member
        status: Status string (e.g., 'available', 'busy', 'offline')
        additional_data: Optional additional data to include

    Returns:
        bool: True if message was queued successfully
    """
    import time

    data = {
        "faculty_id": faculty_id,
        "status": status,
        "timestamp": time.time()
    }

    if additional_data:
        data.update(additional_data)

    topic = f"consultease/faculty/{faculty_id}/status"
    return publish_mqtt_message(topic, data)


def publish_consultation_request(consultation_data: dict) -> bool:
    """
    Publish consultation request to multiple topics.

    Args:
        consultation_data: Dictionary containing consultation information

    Returns:
        bool: True if all messages were queued successfully
    """
    success_count = 0
    total_topics = 3

    consultation_id = consultation_data.get('id')
    faculty_id = consultation_data.get('faculty_id')

    if not consultation_id or not faculty_id:
        logger.error("Missing consultation_id or faculty_id in consultation data")
        return False

    # 1. General consultation topic
    general_topic = f"consultease/consultations/{consultation_id}"
    if publish_mqtt_message(general_topic, consultation_data):
        success_count += 1

    # 2. Faculty-specific topic
    faculty_topic = f"consultease/faculty/{faculty_id}/requests"
    if publish_mqtt_message(faculty_topic, consultation_data):
        success_count += 1

    # 3. Faculty messages topic (plain text for desk unit)
    student_name = consultation_data.get('student_name', 'Unknown')
    student_id = consultation_data.get('student_id', 'Unknown')
    message = consultation_data.get('message', 'No message')

    plain_message = f"Consultation request from {student_name} ({student_id}): {message}"
    faculty_messages_topic = f"consultease/faculty/{faculty_id}/messages"
    if publish_mqtt_message(faculty_messages_topic, plain_message, qos=2):
        success_count += 1

    logger.info(f"Published consultation {consultation_id} to {success_count}/{total_topics} topics")
    return success_count == total_topics
