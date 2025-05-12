import logging
import datetime
from ..services import get_mqtt_service
from ..models import Consultation, ConsultationStatus, get_db

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConsultationController:
    """
    Controller for managing consultation requests.
    """

    def __init__(self):
        """
        Initialize the consultation controller.
        """
        self.mqtt_service = get_mqtt_service()
        self.callbacks = []

    def start(self):
        """
        Start the consultation controller.
        """
        logger.info("Starting Consultation controller")

        # Connect MQTT service
        if not self.mqtt_service.is_connected:
            self.mqtt_service.connect()

    def stop(self):
        """
        Stop the consultation controller.
        """
        logger.info("Stopping Consultation controller")

    def register_callback(self, callback):
        """
        Register a callback to be called when a consultation status changes.

        Args:
            callback (callable): Function that takes a Consultation object as argument
        """
        self.callbacks.append(callback)
        logger.info(f"Registered Consultation controller callback: {callback.__name__}")

    def _notify_callbacks(self, consultation):
        """
        Notify all registered callbacks with the updated consultation information.

        Args:
            consultation (Consultation): Updated consultation object
        """
        for callback in self.callbacks:
            try:
                callback(consultation)
            except Exception as e:
                logger.error(f"Error in Consultation controller callback: {str(e)}")

    def create_consultation(self, student_id, faculty_id, request_message, course_code=None):
        """
        Create a new consultation request.

        Args:
            student_id (int): Student ID
            faculty_id (int): Faculty ID
            request_message (str): Consultation request message
            course_code (str, optional): Course code

        Returns:
            Consultation: New consultation object or None if error
        """
        try:
            db = get_db()

            # Create new consultation
            consultation = Consultation(
                student_id=student_id,
                faculty_id=faculty_id,
                request_message=request_message,
                course_code=course_code,
                status=ConsultationStatus.PENDING,
                requested_at=datetime.datetime.now()
            )

            db.add(consultation)
            db.commit()

            logger.info(f"Created consultation request: {consultation.id} (Student: {student_id}, Faculty: {faculty_id})")

            # Publish to MQTT
            self._publish_consultation(consultation)

            # Notify callbacks
            self._notify_callbacks(consultation)

            return consultation
        except Exception as e:
            logger.error(f"Error creating consultation: {str(e)}")
            return None

    def _publish_consultation(self, consultation):
        """
        Publish consultation to MQTT.

        Args:
            consultation (Consultation): Consultation object to publish
        """
        try:
            # Get full consultation data with related objects
            db = get_db()
            db.refresh(consultation)

            # Create payload
            payload = {
                'id': consultation.id,
                'student_id': consultation.student_id,
                'student_name': consultation.student.name,
                'student_department': consultation.student.department,
                'faculty_id': consultation.faculty_id,
                'faculty_name': consultation.faculty.name,
                'request_message': consultation.request_message,
                'course_code': consultation.course_code,
                'status': consultation.status.value,
                'requested_at': consultation.requested_at.isoformat() if consultation.requested_at else None
            }

            # Publish to faculty-specific topic
            topic = f"consultease/faculty/{consultation.faculty_id}/requests"

            # The MQTT service will format the message for the faculty desk unit
            success = self.mqtt_service.publish(topic, payload)

            if success:
                logger.info(f"Published consultation request to {topic}")
            else:
                logger.error(f"Failed to publish consultation request to {topic}")

            # Also publish to the professor/messages topic for the faculty desk unit
            # This is the topic used in the faculty desk unit code
            alt_topic = "professor/messages"

            # Format the message for the faculty desk unit display
            message = f"Student: {consultation.student.name}\n"
            if consultation.course_code:
                message += f"Course: {consultation.course_code}\n"
            message += f"Request: {consultation.request_message}"

            # Publish the message directly (not as JSON) to match the faculty desk unit code
            self.mqtt_service.publish_raw(alt_topic, message)
            logger.info(f"Published consultation request to faculty desk unit topic {alt_topic}")

            return True
        except Exception as e:
            logger.error(f"Error publishing consultation: {str(e)}")
            return False

    def update_consultation_status(self, consultation_id, status):
        """
        Update consultation status.

        Args:
            consultation_id (int): Consultation ID
            status (ConsultationStatus): New status

        Returns:
            Consultation: Updated consultation object or None if error
        """
        try:
            db = get_db()
            consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()

            if not consultation:
                logger.error(f"Consultation not found: {consultation_id}")
                return None

            # Update status and timestamp
            consultation.status = status

            if status == ConsultationStatus.ACCEPTED:
                consultation.accepted_at = datetime.datetime.now()
            elif status == ConsultationStatus.COMPLETED:
                consultation.completed_at = datetime.datetime.now()
            elif status == ConsultationStatus.CANCELLED:
                # No specific timestamp for cancellation, but we could add one if needed
                pass

            db.commit()

            logger.info(f"Updated consultation status: {consultation.id} -> {status}")

            # Publish updated consultation
            self._publish_consultation(consultation)

            # Notify callbacks
            self._notify_callbacks(consultation)

            return consultation
        except Exception as e:
            logger.error(f"Error updating consultation status: {str(e)}")
            return None

    def cancel_consultation(self, consultation_id):
        """
        Cancel a consultation request.

        Args:
            consultation_id (int): Consultation ID

        Returns:
            Consultation: Updated consultation object or None if error
        """
        return self.update_consultation_status(consultation_id, ConsultationStatus.CANCELLED)

    def get_consultations(self, student_id=None, faculty_id=None, status=None):
        """
        Get consultations, optionally filtered by student, faculty, or status.

        Args:
            student_id (int, optional): Filter by student ID
            faculty_id (int, optional): Filter by faculty ID
            status (ConsultationStatus, optional): Filter by status

        Returns:
            list: List of Consultation objects
        """
        try:
            db = get_db()
            query = db.query(Consultation)

            # Apply filters
            if student_id is not None:
                query = query.filter(Consultation.student_id == student_id)

            if faculty_id is not None:
                query = query.filter(Consultation.faculty_id == faculty_id)

            if status is not None:
                query = query.filter(Consultation.status == status)

            # Order by requested_at (newest first)
            query = query.order_by(Consultation.requested_at.desc())

            # Execute query
            consultations = query.all()

            return consultations
        except Exception as e:
            logger.error(f"Error getting consultations: {str(e)}")
            return []

    def get_consultation_by_id(self, consultation_id):
        """
        Get a consultation by ID.

        Args:
            consultation_id (int): Consultation ID

        Returns:
            Consultation: Consultation object or None if not found
        """
        try:
            db = get_db()
            consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
            return consultation
        except Exception as e:
            logger.error(f"Error getting consultation by ID: {str(e)}")
            return None