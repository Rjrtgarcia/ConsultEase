import paho.mqtt.client as mqtt
import json
import logging
import threading
import time
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MQTTService:
    """
    MQTT Service for communicating with the Faculty Desk Unit.
    """

    def __init__(self):
        # MQTT settings
        self.broker_host = os.environ.get('MQTT_BROKER_HOST', 'localhost')
        self.broker_port = int(os.environ.get('MQTT_BROKER_PORT', 1883))
        self.client_id = "central_system"
        self.username = os.environ.get('MQTT_USERNAME', None)
        self.password = os.environ.get('MQTT_PASSWORD', None)

        # Initialize MQTT client
        self.client = mqtt.Client(client_id=self.client_id)
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        # Set callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        # Topic handlers
        self.topic_handlers = {}

        # Connection management
        self.is_connected = False
        self.reconnect_delay = 5  # seconds
        self.reconnect_thread = None
        self.stop_reconnect = False

    def connect(self):
        """
        Connect to the MQTT broker.
        """
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {str(e)}")
            self.schedule_reconnect()

    def disconnect(self):
        """
        Disconnect from the MQTT broker.
        """
        logger.info("Disconnecting from MQTT broker")
        self.stop_reconnect = True
        self.client.loop_stop()
        if self.is_connected:
            self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        """
        Callback when connected to the MQTT broker.
        """
        if rc == 0:
            self.is_connected = True
            logger.info("Connected to MQTT broker")
            # Subscribe to topics
            for topic in self.topic_handlers.keys():
                self.client.subscribe(topic)
                logger.info(f"Subscribed to {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")
            self.schedule_reconnect()

    def on_disconnect(self, client, userdata, rc):
        """
        Callback when disconnected from the MQTT broker.
        """
        self.is_connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker with code {rc}")
            self.schedule_reconnect()
        else:
            logger.info("Disconnected from MQTT broker")

    def on_message(self, client, userdata, msg):
        """
        Callback when message is received.
        """
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.debug(f"Received message on topic {topic}: {payload}")

            # Process message with registered handler
            if topic in self.topic_handlers:
                try:
                    # Try to parse as JSON
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    logger.warning(f"Message is not JSON, treating as string: {payload}")
                    data = payload  # Use the raw string as data

                for handler in self.topic_handlers[topic]:
                    try:
                        handler(topic, data)
                    except Exception as e:
                        logger.error(f"Error in message handler for topic {topic}: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {str(e)}")

    def register_topic_handler(self, topic, handler):
        """
        Register a handler for a specific topic.

        Args:
            topic (str): MQTT topic to subscribe to
            handler (callable): Function to call when a message is received on this topic
        """
        if topic not in self.topic_handlers:
            self.topic_handlers[topic] = []
            # If already connected, subscribe to the topic
            if self.is_connected:
                self.client.subscribe(topic)
                logger.info(f"Subscribed to {topic}")

        self.topic_handlers[topic].append(handler)
        logger.info(f"Registered handler for topic {topic}")

    def publish(self, topic, data, qos=0, retain=False, max_retries=3):
        """
        Publish a message to a topic with retry logic.

        Args:
            topic (str): MQTT topic to publish to
            data (dict): Data to publish (will be converted to JSON)
            qos (int): Quality of Service level (0, 1, or 2)
            retain (bool): Whether to retain the message on the broker
            max_retries (int): Maximum number of retry attempts if publishing fails

        Returns:
            bool: True if publishing was successful, False otherwise
        """
        if not self.is_connected:
            logger.warning(f"Cannot publish to {topic}: Not connected to MQTT broker")
            # Try to reconnect
            self.schedule_reconnect()
            return False

        try:
            # Format the payload for the faculty desk unit
            # If this is a consultation request, format it for the faculty desk unit
            if "consultease/faculty/" in topic and "/requests" in topic:
                # Format the message for the faculty desk unit
                formatted_data = self._format_for_faculty_desk_unit(data)
                payload = json.dumps(formatted_data)
            else:
                # Regular JSON payload
                payload = json.dumps(data)

            # Try to publish with retries
            for attempt in range(max_retries):
                try:
                    result = self.client.publish(topic, payload, qos=qos, retain=retain)

                    # Check if the publish was successful
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        logger.debug(f"Published message to {topic}: {payload}")
                        return True
                    else:
                        logger.warning(f"Failed to publish message to {topic} (attempt {attempt+1}/{max_retries}): MQTT error code {result.rc}")

                        # If we're not connected, try to reconnect
                        if not self.is_connected:
                            self.schedule_reconnect()
                            time.sleep(1)  # Wait a bit before retrying
                except Exception as e:
                    logger.error(f"Error publishing message to {topic} (attempt {attempt+1}/{max_retries}): {str(e)}")
                    time.sleep(0.5)  # Short delay before retry

            # If we get here, all retries failed
            logger.error(f"Failed to publish message to {topic} after {max_retries} attempts")
            return False

        except Exception as e:
            logger.error(f"Failed to prepare message for {topic}: {str(e)}")
            return False

    def publish_raw(self, topic, message, qos=0, retain=False, max_retries=3):
        """
        Publish a raw message to a topic with retry logic.
        This is used for the faculty desk unit which expects a plain string message.

        Args:
            topic (str): MQTT topic to publish to
            message (str): Message to publish (will be sent as-is, not converted to JSON)
            qos (int): Quality of Service level (0, 1, or 2)
            retain (bool): Whether to retain the message on the broker
            max_retries (int): Maximum number of retry attempts if publishing fails

        Returns:
            bool: True if publishing was successful, False otherwise
        """
        if not self.is_connected:
            logger.warning(f"Cannot publish to {topic}: Not connected to MQTT broker")
            # Try to reconnect
            self.schedule_reconnect()
            return False

        try:
            # Try to publish with retries
            for attempt in range(max_retries):
                try:
                    result = self.client.publish(topic, message, qos=qos, retain=retain)

                    # Check if the publish was successful
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        logger.debug(f"Published raw message to {topic}: {message}")
                        return True
                    else:
                        logger.warning(f"Failed to publish raw message to {topic} (attempt {attempt+1}/{max_retries}): MQTT error code {result.rc}")

                        # If we're not connected, try to reconnect
                        if not self.is_connected:
                            self.schedule_reconnect()
                            time.sleep(1)  # Wait a bit before retrying
                except Exception as e:
                    logger.error(f"Error publishing raw message to {topic} (attempt {attempt+1}/{max_retries}): {str(e)}")
                    time.sleep(0.5)  # Short delay before retry

            # If we get here, all retries failed
            logger.error(f"Failed to publish raw message to {topic} after {max_retries} attempts")
            return False

        except Exception as e:
            logger.error(f"Failed to prepare raw message for {topic}: {str(e)}")
            return False

    def _format_for_faculty_desk_unit(self, data):
        """
        Format a consultation request message for the faculty desk unit.

        Args:
            data (dict): The original consultation data

        Returns:
            dict: Formatted data for the faculty desk unit
        """
        try:
            # Extract relevant information
            student_name = data.get('student_name', 'Unknown Student')
            request_message = data.get('request_message', '')
            course_code = data.get('course_code', '')

            # Format the message for the faculty desk unit display
            message = f"Student: {student_name}\n"
            if course_code:
                message += f"Course: {course_code}\n"
            message += f"Request: {request_message}"

            # Create a simplified payload for the faculty desk unit
            formatted_data = {
                'message': message,
                'student_name': student_name,
                'course_code': course_code,
                'consultation_id': data.get('id'),
                'timestamp': data.get('requested_at')
            }

            return formatted_data
        except Exception as e:
            logger.error(f"Error formatting message for faculty desk unit: {str(e)}")
            # Return the original data if there's an error
            return data

    def schedule_reconnect(self):
        """
        Schedule a reconnection attempt.
        """
        if self.reconnect_thread is not None and self.reconnect_thread.is_alive():
            return

        self.stop_reconnect = False
        self.reconnect_thread = threading.Thread(target=self._reconnect_worker)
        self.reconnect_thread.daemon = True
        self.reconnect_thread.start()

    def _reconnect_worker(self):
        """
        Worker thread for reconnecting to the MQTT broker.
        Uses exponential backoff for reconnection attempts.
        """
        # Start with initial delay and increase up to a maximum
        current_delay = self.reconnect_delay
        max_delay = 60  # Maximum delay in seconds
        attempt = 1

        while not self.stop_reconnect and not self.is_connected:
            logger.info(f"Attempting to reconnect to MQTT broker in {current_delay} seconds (attempt {attempt})")
            time.sleep(current_delay)

            if self.stop_reconnect:
                break

            try:
                # Try to reconnect
                logger.info(f"Reconnecting to MQTT broker at {self.broker_host}:{self.broker_port}")
                self.client.reconnect()

                # If we get here without exception, we're connected
                logger.info("Successfully reconnected to MQTT broker")

                # Reset delay for next time
                current_delay = self.reconnect_delay
                attempt = 1
            except Exception as e:
                logger.error(f"Failed to reconnect to MQTT broker (attempt {attempt}): {str(e)}")

                # Increase delay with exponential backoff, but cap at max_delay
                current_delay = min(current_delay * 1.5, max_delay)
                attempt += 1

                # If we've tried many times, log a more severe message
                if attempt > 10:
                    logger.critical(
                        f"Multiple failed attempts to connect to MQTT broker. "
                        f"Please check network connectivity and broker status."
                    )

# Singleton instance
mqtt_service = None

def get_mqtt_service():
    """
    Get the singleton MQTT service instance.
    """
    global mqtt_service
    if mqtt_service is None:
        mqtt_service = MQTTService()
    return mqtt_service