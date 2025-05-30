"""
Asynchronous MQTT service for ConsultEase system.
Provides non-blocking MQTT operations to improve UI responsiveness on Raspberry Pi.
"""

import asyncio
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
from typing import Dict, Callable, Optional, Any
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class AsyncMQTTService:
    """
    Asynchronous MQTT service that handles publishing and subscribing without blocking the UI.
    Uses a background thread pool and message queuing for optimal performance on Raspberry Pi.
    """

    def __init__(self, broker_host='localhost', broker_port=1883, username=None, password=None, max_queue_size=1000):
        """
        Initialize the asynchronous MQTT service.

        Args:
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
            username: MQTT username (optional)
            password: MQTT password (optional)
            max_queue_size: Maximum queue size for pending messages
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.max_queue_size = max_queue_size

        # MQTT client
        self.client = None
        self.is_connected = False

        # Asynchronous components
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mqtt")
        self.publish_queue = Queue()
        self.message_handlers: Dict[str, Callable] = {}

        # Background threads
        self.publish_thread = None
        self.connection_monitor_thread = None
        self.running = False

        # Connection monitoring
        self.last_ping = 0
        self.ping_interval = 30  # seconds
        self.reconnect_delay = 5  # seconds
        self.max_reconnect_attempts = 10

        # Performance metrics
        self.messages_published = 0
        self.messages_received = 0
        self.publish_errors = 0
        self.dropped_messages = 0
        self.last_error = None

        # Message batching for performance optimization
        self.batch_queue = Queue()
        self.batch_size = 10  # Maximum messages per batch
        self.batch_timeout = 0.1  # 100ms timeout for batching
        self.last_batch_time = 0
        self.batched_messages = 0

        # Initialize client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize MQTT client with callbacks and enhanced error handling."""
        try:
            # Create client with clean session and protocol version specification
            self.client = mqtt.Client(
                client_id=f"consultease_central_{int(time.time())}",
                clean_session=True,
                protocol=mqtt.MQTTv311  # Use MQTT 3.1.1 for better compatibility
            )

            # Set authentication if provided
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish

            # Configure client options for reliability and error prevention
            self.client.reconnect_delay_set(min_delay=1, max_delay=120)
            self.client.max_inflight_messages_set(20)
            self.client.max_queued_messages_set(100)

            # Set socket options to prevent connection issues
            self.client.socket_timeout = 60
            self.client.keepalive = 60

            # Enable message ordering and duplicate detection
            self.client.message_retry_set(5)  # Retry failed messages up to 5 times

            logger.debug("MQTT client initialized with enhanced configuration")

        except Exception as e:
            logger.error(f"Error initializing MQTT client: {e}")
            self.last_error = str(e)

    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        if rc == 0:
            self.is_connected = True
            self.last_ping = time.time()
            logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")

            # Resubscribe to all topics
            for topic in self.message_handlers.keys():
                try:
                    client.subscribe(topic)
                    logger.debug(f"Resubscribed to topic: {topic}")
                except Exception as e:
                    logger.error(f"Error resubscribing to topic {topic}: {e}")
        else:
            self.is_connected = False
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection."""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection. Return code: {rc}")
        else:
            logger.info("MQTT client disconnected")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages with enhanced error handling."""
        try:
            self.messages_received += 1
            topic = msg.topic

            # Validate message structure
            if not hasattr(msg, 'payload') or msg.payload is None:
                logger.warning(f"Received message with no payload on topic: {topic}")
                return

            # Decode payload with multiple fallback strategies
            try:
                # Try UTF-8 decoding first
                payload = msg.payload.decode('utf-8')

                # Validate payload is not empty or just whitespace
                if not payload or payload.isspace():
                    logger.debug(f"Received empty payload on topic: {topic}")
                    return

                # Try to parse as JSON
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    # If not JSON, treat as string but validate it's printable
                    if all(ord(c) < 128 and (c.isprintable() or c.isspace()) for c in payload):
                        data = payload.strip()
                    else:
                        logger.warning(f"Received non-printable string payload on topic {topic}")
                        return

            except UnicodeDecodeError:
                # Try alternative encodings
                try:
                    payload = msg.payload.decode('latin-1')
                    logger.warning(f"Used latin-1 fallback decoding for topic {topic}")
                    data = payload.strip()
                except Exception:
                    logger.error(f"Failed to decode message payload for topic {topic} with any encoding")
                    return
            except Exception as decode_error:
                logger.error(f"Unexpected error decoding payload for topic {topic}: {decode_error}")
                return

            # Additional validation for data
            if data is None:
                logger.debug(f"Processed payload resulted in None for topic: {topic}")
                return

            # Find matching handler
            handler = self._find_message_handler(topic)
            if handler:
                # Execute handler in thread pool to avoid blocking
                self.executor.submit(self._execute_handler, handler, topic, data)
            else:
                logger.debug(f"No handler found for topic: {topic}")

        except Exception as e:
            logger.error(f"Error processing MQTT message for topic {getattr(msg, 'topic', 'unknown')}: {e}")
            import traceback
            logger.error(f"MQTT message processing traceback: {traceback.format_exc()}")

    def _on_publish(self, client, userdata, mid):
        """Handle successful message publication."""
        logger.debug(f"Message published successfully (mid: {mid})")

    def _find_message_handler(self, topic: str) -> Optional[Callable]:
        """Find the appropriate message handler for a topic."""
        # Exact match first
        if topic in self.message_handlers:
            return self.message_handlers[topic]

        # Wildcard matching
        for pattern, handler in self.message_handlers.items():
            if self._topic_matches(topic, pattern):
                return handler

        return None

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern with wildcards."""
        if '+' not in pattern and '#' not in pattern:
            return topic == pattern

        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')

        # Handle # wildcard
        if pattern.endswith('#'):
            pattern_parts = pattern_parts[:-1]
            return topic_parts[:len(pattern_parts)] == pattern_parts

        # Handle + wildcards
        if len(topic_parts) != len(pattern_parts):
            return False

        for topic_part, pattern_part in zip(topic_parts, pattern_parts):
            if pattern_part != '+' and pattern_part != topic_part:
                return False

        return True

    def _execute_handler(self, handler: Callable, topic: str, data: Any):
        """Execute message handler safely."""
        try:
            handler(topic, data)
        except Exception as e:
            logger.error(f"Error in message handler for topic {topic}: {e}")

    def start(self):
        """Start the asynchronous MQTT service."""
        if self.running:
            logger.warning("MQTT service is already running")
            return

        self.running = True

        # Start background threads
        self.publish_thread = threading.Thread(
            target=self._publish_worker,
            name="mqtt-publisher",
            daemon=True
        )
        self.publish_thread.start()

        self.connection_monitor_thread = threading.Thread(
            target=self._connection_monitor,
            name="mqtt-monitor",
            daemon=True
        )
        self.connection_monitor_thread.start()

        # Connect to broker
        self.connect()

        logger.info("Asynchronous MQTT service started")

    def stop(self):
        """Stop the asynchronous MQTT service."""
        self.running = False

        # Disconnect from broker
        if self.client and self.is_connected:
            self.client.disconnect()

        # Shutdown thread pool
        self.executor.shutdown(wait=True)

        logger.info("Asynchronous MQTT service stopped")

    def connect(self):
        """Connect to MQTT broker asynchronously."""
        if not self.client:
            self._initialize_client()

        def _connect():
            try:
                self.client.connect_async(self.broker_host, self.broker_port, 60)
                self.client.loop_start()
                logger.debug("MQTT connection initiated")
            except Exception as e:
                logger.error(f"Error connecting to MQTT broker: {e}")
                self.last_error = str(e)

        # Execute connection in thread pool
        self.executor.submit(_connect)

    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

    def publish_async(self, topic: str, data: Any, qos: int = 1, retain: bool = False, batch: bool = True):
        """
        Publish message asynchronously without blocking with optional batching.

        Args:
            topic: MQTT topic
            data: Data to publish (will be JSON encoded if not string)
            qos: Quality of service level
            retain: Whether to retain the message
            batch: Whether to use message batching for performance
        """
        message = {
            'topic': topic,
            'data': data,
            'qos': qos,
            'retain': retain,
            'timestamp': time.time()
        }

        try:
            # Use batching for better performance if enabled
            if batch and qos <= 1 and not retain:  # Only batch non-critical messages
                self._add_to_batch(message)
            else:
                # Direct queue for critical messages
                self._queue_message_direct(message)

        except Exception as e:
            logger.error(f"Failed to queue message for topic {topic}: {e}")
            self.publish_errors += 1

    def _add_to_batch(self, message):
        """Add message to batch queue for optimized publishing."""
        try:
            current_time = time.time()

            # Check if we should flush the current batch
            if (self.batch_queue.qsize() >= self.batch_size or
                (self.last_batch_time > 0 and current_time - self.last_batch_time > self.batch_timeout)):
                self._flush_batch()

            self.batch_queue.put(message, timeout=0.1)

            if self.last_batch_time == 0:
                self.last_batch_time = current_time

        except Exception as e:
            logger.warning(f"Failed to add message to batch, using direct queue: {e}")
            self._queue_message_direct(message)

    def _queue_message_direct(self, message):
        """Queue message directly without batching."""
        # Check queue size before adding
        if self.publish_queue.qsize() >= self.max_queue_size:
            # Remove oldest message to make room
            try:
                self.publish_queue.get_nowait()
                self.dropped_messages += 1
                logger.warning(f"Dropped oldest message due to queue overflow. Total dropped: {self.dropped_messages}")
            except Empty:
                pass

        self.publish_queue.put(message, timeout=1)
        logger.debug(f"Message queued for publication to {message['topic']}")

    def _flush_batch(self):
        """Flush the current batch of messages to the publish queue."""
        if self.batch_queue.empty():
            return

        batch_messages = []
        batch_count = 0

        # Collect all messages from batch queue
        while not self.batch_queue.empty() and batch_count < self.batch_size:
            try:
                message = self.batch_queue.get_nowait()
                batch_messages.append(message)
                batch_count += 1
            except Empty:
                break

        if batch_messages:
            # For now, just queue all messages individually
            # Future enhancement: group by topic for true batching
            for message in batch_messages:
                self._queue_message_direct(message)
                self.batched_messages += 1

            logger.debug(f"Flushed batch of {len(batch_messages)} messages")

        self.last_batch_time = 0

    def _publish_worker(self):
        """Background worker for publishing messages with enhanced validation."""
        while self.running:
            try:
                # Get message from queue with timeout
                message = self.publish_queue.get(timeout=1)

                if not self.is_connected:
                    logger.warning(f"Cannot publish to {message['topic']}: not connected")
                    self.publish_errors += 1
                    continue

                # Validate message structure
                if not message or 'topic' not in message or 'data' not in message:
                    logger.error("Invalid message structure in publish queue")
                    self.publish_errors += 1
                    continue

                topic = message['topic']
                data = message['data']

                # Validate topic
                if not topic or not isinstance(topic, str) or len(topic.strip()) == 0:
                    logger.error(f"Invalid topic: {topic}")
                    self.publish_errors += 1
                    continue

                # Prepare and validate payload
                try:
                    if isinstance(data, str):
                        # Validate string payload
                        if not all(ord(c) < 128 for c in data):
                            logger.warning(f"Non-ASCII characters in string payload for topic {topic}")
                            # Convert to safe ASCII
                            payload = data.encode('ascii', 'ignore').decode('ascii')
                        else:
                            payload = data
                    elif data is None:
                        payload = ""
                    else:
                        # Convert to JSON with error handling
                        try:
                            payload = json.dumps(data, ensure_ascii=True, separators=(',', ':'))
                        except (TypeError, ValueError) as json_error:
                            logger.error(f"Failed to serialize data to JSON for topic {topic}: {json_error}")
                            self.publish_errors += 1
                            continue

                    # Final payload validation
                    if len(payload.encode('utf-8')) > 268435455:  # MQTT max payload size
                        logger.error(f"Payload too large for topic {topic}: {len(payload)} bytes")
                        self.publish_errors += 1
                        continue

                except Exception as payload_error:
                    logger.error(f"Error preparing payload for topic {topic}: {payload_error}")
                    self.publish_errors += 1
                    continue

                # Publish message with additional error checking
                try:
                    result = self.client.publish(
                        topic,
                        payload,
                        qos=message.get('qos', 1),
                        retain=message.get('retain', False)
                    )

                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        self.messages_published += 1
                        logger.debug(f"Published message to {topic}")
                    else:
                        logger.error(f"Failed to publish to {topic}: MQTT error code {result.rc}")
                        self.publish_errors += 1

                except Exception as publish_error:
                    logger.error(f"Exception during publish to {topic}: {publish_error}")
                    self.publish_errors += 1

            except Empty:
                # Timeout - continue loop
                continue
            except Exception as e:
                logger.error(f"Error in publish worker: {e}")
                import traceback
                logger.error(f"Publish worker traceback: {traceback.format_exc()}")
                self.publish_errors += 1

    def _connection_monitor(self):
        """Monitor connection and handle reconnection."""
        reconnect_attempts = 0

        while self.running:
            try:
                current_time = time.time()

                # Check if we need to reconnect
                if not self.is_connected and reconnect_attempts < self.max_reconnect_attempts:
                    logger.info(f"Attempting to reconnect to MQTT broker (attempt {reconnect_attempts + 1})")
                    self.connect()
                    reconnect_attempts += 1
                    time.sleep(self.reconnect_delay)
                elif self.is_connected:
                    # Reset reconnect attempts on successful connection
                    reconnect_attempts = 0

                    # Update last ping time (ping functionality removed as paho-mqtt doesn't have ping method)
                    if current_time - self.last_ping > self.ping_interval:
                        # Just update the timestamp - the MQTT client handles keepalive automatically
                        self.last_ping = current_time
                        logger.debug("MQTT keepalive check - connection is active")

                time.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")
                time.sleep(10)

    def register_topic_handler(self, topic: str, handler: Callable):
        """
        Register a handler for a specific topic.

        Args:
            topic: MQTT topic (supports wildcards + and #)
            handler: Callable that takes (topic, data) as arguments
        """
        self.message_handlers[topic] = handler

        # Subscribe to topic if connected
        if self.is_connected and self.client:
            try:
                self.client.subscribe(topic)
                logger.info(f"Subscribed to topic: {topic}")
            except Exception as e:
                logger.error(f"Error subscribing to topic {topic}: {e}")

        logger.debug(f"Registered handler for topic: {topic}")

    def unregister_topic_handler(self, topic: str):
        """Unregister a topic handler."""
        if topic in self.message_handlers:
            del self.message_handlers[topic]

            # Unsubscribe from topic if connected
            if self.is_connected and self.client:
                try:
                    self.client.unsubscribe(topic)
                    logger.info(f"Unsubscribed from topic: {topic}")
                except Exception as e:
                    logger.error(f"Error unsubscribing from topic {topic}: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics including batching metrics."""
        return {
            'connected': self.is_connected,
            'messages_published': self.messages_published,
            'messages_received': self.messages_received,
            'publish_errors': self.publish_errors,
            'dropped_messages': self.dropped_messages,
            'batched_messages': self.batched_messages,
            'queue_size': self.publish_queue.qsize(),
            'batch_queue_size': self.batch_queue.qsize(),
            'max_queue_size': self.max_queue_size,
            'batch_size': self.batch_size,
            'last_error': self.last_error,
            'last_ping': self.last_ping
        }


# Global service instance
_async_mqtt_service: Optional[AsyncMQTTService] = None


def get_async_mqtt_service() -> AsyncMQTTService:
    """Get the global asynchronous MQTT service instance."""
    global _async_mqtt_service
    if _async_mqtt_service is None:
        # Import configuration
        from ..utils.config_manager import get_config

        _async_mqtt_service = AsyncMQTTService(
            broker_host=get_config('mqtt.broker_host', 'localhost'),
            broker_port=get_config('mqtt.broker_port', 1883),
            username=get_config('mqtt.username'),
            password=get_config('mqtt.password')
        )

    return _async_mqtt_service
