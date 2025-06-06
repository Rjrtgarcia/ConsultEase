import logging
import datetime
from sqlalchemy import or_, func
from ..models import Faculty, get_db
from ..utils.mqtt_utils import publish_faculty_status, subscribe_to_topic, publish_mqtt_message
from ..utils.mqtt_topics import MQTTTopics
from ..utils.cache_manager import cached, invalidate_faculty_cache, cache_faculty_list_key, get_cache_manager
from ..utils.query_cache import cached_query, paginate_query, invalidate_cache_pattern
from ..utils.validators import (
    validate_name_safe, validate_department_safe, validate_email_safe,
    validate_ble_id_safe, InputValidator, ValidationError
)
from ..services.consultation_queue_service import get_consultation_queue_service

# Set up logging
logger = logging.getLogger(__name__)

class FacultyController:
    """
    Controller for managing faculty data and status.
    """

    def __init__(self):
        """
        Initialize the faculty controller.
        """
        self.callbacks = []
        self.queue_service = get_consultation_queue_service()
        # Pending status updates for faculty that don't exist yet
        self._pending_status_updates = {}

    def start(self):
        """
        Start the faculty controller and subscribe to faculty status updates.
        """
        logger.info("Starting Faculty controller")

        # Subscribe to faculty status updates using async MQTT service
        subscribe_to_topic("consultease/faculty/+/status", self.handle_faculty_status_update)

        # Subscribe to faculty MAC address status updates (from ESP32 units)
        subscribe_to_topic("consultease/faculty/+/mac_status", self.handle_faculty_status_update)

        # Subscribe to legacy faculty desk unit status updates for backward compatibility
        subscribe_to_topic(MQTTTopics.LEGACY_FACULTY_STATUS, self.handle_faculty_status_update)

        # Note: Faculty heartbeat is handled by FacultyResponseController to avoid duplicate subscriptions

    def stop(self):
        """
        Stop the faculty controller.
        """
        logger.info("Stopping Faculty controller")

    def register_callback(self, callback):
        """
        Register a callback to be called when faculty status changes.

        Args:
            callback (callable): Function that takes a Faculty object as argument
        """
        self.callbacks.append(callback)
        logger.info(f"Registered Faculty controller callback: {callback.__name__}")

    def _notify_callbacks(self, faculty_data):
        """
        Notify all registered callbacks with the updated faculty information.

        Args:
            faculty_data (dict): Updated faculty data dictionary
        """
        for callback in self.callbacks:
            try:
                callback(faculty_data) # Pass the dictionary
            except Exception as e:
                logger.error(f"Error in Faculty controller callback: {str(e)}")

    def handle_faculty_status_update(self, topic, data):
        logger.info(f"🔄 [FACULTY CONTROLLER] Received MQTT message")
        logger.info(f"   Topic: {topic}")
        logger.info(f"   Data Type: {type(data)}")
        logger.info(f"   Data: {data}")

        faculty_id = None
        status = None
        # faculty_name = None # Not directly used for update_faculty_status call

        faculty_dict_for_callbacks = None # Initialize a variable to hold the dict for callbacks

        if topic.endswith("/mac_status"):
            try:
                faculty_id = int(topic.split("/")[2])
                if isinstance(data, dict):
                    status_str = data.get("status", "")
                    detected_mac = data.get("mac", "")
                    if status_str == "faculty_present": status = True
                    elif status_str == "faculty_absent": status = False
                    else: logger.warning(f"Unknown MAC status: {status_str}"); return

                    faculty_dict_for_callbacks = self.update_faculty_status(faculty_id, status)

                    if faculty_dict_for_callbacks:
                        if detected_mac and status:
                            normalized_mac = Faculty.normalize_mac_address(detected_mac)
                            if normalized_mac != faculty_dict_for_callbacks.get('ble_id'): 
                                self.update_faculty_ble_id(faculty_id, normalized_mac)
                        # self._notify_callbacks is called at the end if faculty_dict_for_callbacks is set
                        # Publish notification logic can use faculty_dict_for_callbacks
                        try:
                            notification = {
                                'type': 'faculty_mac_status',
                                'faculty_id': faculty_dict_for_callbacks['id'],
                                'faculty_name': faculty_dict_for_callbacks['name'],
                                'status': status,
                                'detected_mac': detected_mac,
                                'timestamp': faculty_dict_for_callbacks['last_seen']
                            }
                            publish_mqtt_message(MQTTTopics.SYSTEM_NOTIFICATIONS, notification)
                        except Exception as e:
                            logger.error(f"Error publishing MAC status notification: {str(e)}")
                    # return # Don't return early, let common callback notification run
            except (ValueError, IndexError) as e:
                logger.error(f"Error parsing MAC status topic {topic}: {str(e)}")
                return # Return on parsing error

        elif topic == MQTTTopics.LEGACY_FACULTY_STATUS:
            db_session_legacy = get_db() # Session for fetching faculty if needed
            try:
                faculty_to_update = None
                if isinstance(data, str):
                    if data == "keychain_connected" or data == "faculty_present": status = True
                    elif data == "keychain_disconnected" or data == "faculty_absent": status = False
                    else: logger.warning(f"Unknown legacy status string: {data}"); db_session_legacy.close(); return
                    
                    # Try to find faculty with BLE configured
                    faculty_to_update = db_session_legacy.query(Faculty).filter(Faculty.ble_id.isnot(None)).first()
                    if faculty_to_update: faculty_id = faculty_to_update.id
                    else: logger.error("No faculty with BLE configuration found for legacy update"); db_session_legacy.close(); return

                elif isinstance(data, dict):
                    status = data.get('status', False)
                    faculty_id_from_data = data.get('faculty_id')
                    faculty_name_from_data = data.get('faculty_name')
                    if faculty_id_from_data:
                        faculty_id = faculty_id_from_data
                    elif faculty_name_from_data:
                        faculty_to_update = db_session_legacy.query(Faculty).filter(Faculty.name == faculty_name_from_data).first()
                        if faculty_to_update: faculty_id = faculty_to_update.id
                        else: logger.error(f"Faculty '{faculty_name_from_data}' not found for legacy update"); db_session_legacy.close(); return
                    else: # Fallback to any BLE configured faculty
                        faculty_to_update = db_session_legacy.query(Faculty).filter(Faculty.ble_id.isnot(None)).first()
                        if faculty_to_update: faculty_id = faculty_to_update.id
                        else: logger.error("No faculty identified for legacy JSON update"); db_session_legacy.close(); return
                else: logger.error(f"Invalid data type for legacy status: {type(data)}"); db_session_legacy.close(); return

                if faculty_id is not None and status is not None:
                    faculty_dict_for_callbacks = self.update_faculty_status(faculty_id, status)
            finally:
                db_session_legacy.close()

        else: # Standard topic format: consultease/faculty/{id}/status
            parts = topic.split('/')
            if len(parts) == 4 and parts[0] == "consultease" and parts[1] == "faculty" and parts[3] == "status":
                try:
                    faculty_id = int(parts[2])
                    if isinstance(data, dict):
                        # Improved status processing logic to handle BUSY status correctly
                        status_str = data.get("status", "").upper()
                        present_bool = data.get("present", None)
                        
                        # Determine status based on both status string and present boolean
                        # Priority: Use status string for semantic meaning, fall back to present boolean
                        if status_str:
                            if status_str in ["AVAILABLE", "PRESENT"]:
                                status = True
                            elif status_str in ["AWAY", "OFFLINE", "UNAVAILABLE"]:
                                status = False
                            elif "BUSY" in status_str:
                                status = False  # Busy faculty are not available for new consultations
                            else:
                                logger.warning(f"Unknown status string: {status_str}, falling back to present field")
                                status = bool(present_bool) if present_bool is not None else None
                        elif present_bool is not None:
                            # Fallback to present boolean if no status string
                            status = bool(present_bool)
                        else:
                            logger.warning(f"No valid status information found in data: {data}")
                            return
                        
                        if status is None:
                            logger.warning(f"Could not determine status from data: {data}")
                            return

                        # Enhanced status details (optional)
                        ntp_sync_status = data.get('ntp_sync_status')
                        grace_period_active = data.get('in_grace_period')
                        
                        faculty_dict_for_callbacks = self.update_faculty_status(faculty_id, status)
                        
                        if faculty_dict_for_callbacks and (ntp_sync_status or grace_period_active is not None):
                             # If update_faculty_status does not handle these, we might need another method call
                             # For now, assume update_faculty_status is the primary source of truth for 'status'
                             # and these are for logging or minor adjustments if needed later.
                             logger.info(f"Faculty {faculty_id} enhanced info: NTP: {ntp_sync_status}, Grace: {grace_period_active}")
                             # Potentially call: self._update_faculty_enhanced_status(faculty_id, status, ntp_sync_status, grace_period_active)
                             # But this might cause another DB write. For now, focus on the main status update.

                    elif isinstance(data, (bool, int)): # Direct status true/false or 1/0
                        status = bool(data)
                        faculty_dict_for_callbacks = self.update_faculty_status(faculty_id, status)
                    else:
                        logger.error(f"Invalid data type for status: {type(data)} on topic {topic}")
                        return
                except ValueError:
                    logger.error(f"Invalid faculty ID in topic: {parts[2]}")
                    return
                except IndexError:
                    logger.error(f"Invalid topic format: {topic}")
                    return
            else:
                logger.warning(f"Unhandled MQTT topic in FacultyController: {topic}")
                return

        # Common actions after status update attempt
        if faculty_dict_for_callbacks:
            # Notify consultation queue service about faculty status change
            self.queue_service.update_faculty_status(faculty_dict_for_callbacks['id'], faculty_dict_for_callbacks['status'])
            # Notify registered callbacks with the dictionary
            self._notify_callbacks(faculty_dict_for_callbacks)
            # Publish general notification (already handled by update_faculty_status via _publish_status_update_with_sequence_safe)
            logger.info(f"✅ [FACULTY CONTROLLER] Successfully processed status update")
            logger.info(f"   Faculty ID: {faculty_dict_for_callbacks['id']}")
            logger.info(f"   New Status: {faculty_dict_for_callbacks['status']}")
            logger.info(f"   Publishing to: consultease/faculty/{faculty_dict_for_callbacks['id']}/status_update")
        elif faculty_id is not None: # Log if update attempt was made but failed
            logger.error(f"❌ [FACULTY CONTROLLER] Failed to process status update for faculty {faculty_id}")

    def update_faculty_status(self, faculty_id, status):
        """
        Update faculty status in the database with enhanced real-time support.
        
        Args:
            faculty_id (int): Faculty ID
            status (bool): New status (True for available, False for unavailable)
            
        Returns:
            dict: Faculty data dictionary if successful, None if failed
        """
        if faculty_id is None or status is None:
            logger.error(f"Invalid parameters: faculty_id={faculty_id}, status={status}")
            return None

        try:
            from ..models.base import DatabaseManager
            import datetime
            
            db_manager = DatabaseManager()
            
            # Enhanced transaction handling with isolation
            with db_manager.get_session_context() as db:
                # Use SELECT FOR UPDATE to prevent concurrent modifications
                faculty = db.query(Faculty).filter(Faculty.id == faculty_id).with_for_update().first()
                
                if not faculty:
                    logger.warning(f"❌ Faculty with ID {faculty_id} not found in database")
                    # Create pending update for faculty that doesn't exist yet
                    self._pending_status_updates[faculty_id] = status
                    logger.info(f"🔄 Added pending status update for faculty {faculty_id}: {status}")
                    return None

                # Capture previous status for change detection
                previous_status = faculty.status
                status_changed = previous_status != status
                
                logger.info(f"🔄 [FACULTY CONTROLLER] Updating faculty {faculty_id} status: {previous_status} -> {status}")

                if status_changed:
                    # Update faculty status
                    faculty.status = status
                    faculty.last_seen = datetime.datetime.now()
                    
                    # Force immediate commit to ensure changes are persisted
                    db.commit()
                    db.refresh(faculty)
                    
                    # Prepare safe faculty data for callbacks and notifications
                    faculty_data = {
                        'id': faculty.id,
                        'name': faculty.name,
                        'department': faculty.department,
                        'status': faculty.status,
                        'last_seen': faculty.last_seen.isoformat() if faculty.last_seen else None,
                        'ble_id': faculty.ble_id,
                        'version': getattr(faculty, 'version', 1)
                    }
                    
                    logger.info(f"✅ [FACULTY CONTROLLER] Faculty {faculty_id} status updated in database: {status}")
                    
                    # Publish status update immediately after successful commit
                    self._publish_status_update_with_sequence_safe(faculty_data, status, previous_status)
                    
                    # Invalidate caches
                    self._invalidate_faculty_caches()
                    
                    return faculty_data
                else:
                    logger.debug(f"🔄 Faculty {faculty_id} status unchanged ({status}), skipping update")
                    # Still return faculty data for consistency
                    faculty_data = {
                        'id': faculty.id,
                        'name': faculty.name,
                        'department': faculty.department,
                        'status': faculty.status,
                        'last_seen': faculty.last_seen.isoformat() if faculty.last_seen else None,
                        'ble_id': faculty.ble_id,
                        'version': getattr(faculty, 'version', 1)
                    }
                    return faculty_data

        except Exception as e:
            logger.error(f"❌ [FACULTY CONTROLLER] Exception during update_faculty_status for ID {faculty_id} (status: {status}): {str(e)}")
            import traceback
            logger.error(f"❌ [FACULTY CONTROLLER] Traceback: {traceback.format_exc()}")
            return None

    def _publish_status_update_with_sequence_safe(self, faculty_data, new_status, previous_status):
        """
        Publish faculty status update with enhanced reliability and sequence number.
        
        Args:
            faculty_data (dict): Safe faculty data dictionary
            new_status: New status value
            previous_status: Previous status value
        """
        try:
            # Generate sequence number for message ordering
            if not hasattr(self, '_message_sequence'):
                self._message_sequence = 0

            self._message_sequence += 1

            # Create comprehensive notification with sequence number and timestamp
            notification = {
                'type': 'faculty_status',
                'faculty_id': faculty_data['id'],
                'faculty_name': faculty_data['name'],
                'status': new_status,
                'previous_status': previous_status,
                'sequence': self._message_sequence,
                'timestamp': faculty_data.get('last_seen'),
                'version': faculty_data.get('version', 1),
                'change_detected': new_status != previous_status
            }

            # Enhanced topic publishing with retry logic
            topics = [
                # Primary topic for dashboard consumption
                f"consultease/faculty/{faculty_data['id']}/status_update",
                # System notifications for broader consumption
                "consultease/system/notifications",
                # Legacy compatibility topic
                f"faculty/{faculty_data['id']}/status"
            ]

            publish_success_count = 0
            for topic in topics:
                try:
                    from ..utils.mqtt_utils import publish_mqtt_message
                    success = publish_mqtt_message(topic, notification, retain=True, qos=1)
                    if success:
                        publish_success_count += 1
                        logger.info(f"✅ [FACULTY CONTROLLER] Published status update to {topic} (seq: {self._message_sequence})")
                    else:
                        logger.error(f"❌ [FACULTY CONTROLLER] Failed to publish to {topic}")
                except Exception as e:
                    logger.error(f"❌ [FACULTY CONTROLLER] Error publishing to {topic}: {str(e)}")

            if publish_success_count > 0:
                logger.info(f"✅ [FACULTY CONTROLLER] Status update published to {publish_success_count}/{len(topics)} topics")
            else:
                logger.error(f"❌ [FACULTY CONTROLLER] Failed to publish status update to any topics!")

        except Exception as e:
            logger.error(f"❌ [FACULTY CONTROLLER] Error publishing faculty status notification: {str(e)}")
            import traceback
            logger.error(f"❌ [FACULTY CONTROLLER] Traceback: {traceback.format_exc()}")

    def _invalidate_faculty_caches(self):
        """Invalidate all faculty-related caches."""
        try:
            from ..utils.cache_manager import invalidate_faculty_cache
            from ..utils.query_cache import invalidate_cache_pattern
            
            invalidate_faculty_cache()
            invalidate_cache_pattern("get_all_faculty")

            if hasattr(self.get_all_faculty, 'cache_clear'):
                self.get_all_faculty.cache_clear()
                
            logger.debug("🗑️ [FACULTY CONTROLLER] Faculty caches invalidated")
        except Exception as e:
            logger.error(f"❌ [FACULTY CONTROLLER] Error invalidating caches: {str(e)}")

    def _queue_pending_status_update(self, faculty_id, status):
        """Queue a status update for a faculty member that doesn't exist yet."""
        self._pending_status_updates[faculty_id] = {
            'status': status,
            'timestamp': datetime.datetime.now()
        }
        logger.info(f"Queued pending status update for faculty ID {faculty_id}: {status}")

    def _process_pending_status_updates(self, faculty_id):
        """Process any pending status updates for a newly created faculty member."""
        if faculty_id in self._pending_status_updates:
            pending_update = self._pending_status_updates.pop(faculty_id)
            logger.info(f"Processing pending status update for faculty ID {faculty_id}: {pending_update['status']}")
            # Apply the pending status update
            self.update_faculty_status(faculty_id, pending_update['status'])

    def handle_concurrent_status_update(self, faculty_id, status, source="unknown"):
        """
        Handle concurrent status updates with conflict resolution.

        Args:
            faculty_id (int): Faculty ID
            status (bool): New status
            source (str): Source of the update (e.g., "mqtt", "ble", "manual")

        Returns:
            Faculty: Updated faculty object or None if failed
        """
        max_retries = 3
        retry_delay = 0.1  # 100ms

        for attempt in range(max_retries):
            try:
                # Attempt atomic update
                faculty = self.update_faculty_status(faculty_id, status)

                if faculty:
                    logger.info(f"Successfully updated faculty {faculty_id} status to {status} from {source} (attempt {attempt + 1})")
                    return faculty
                else:
                    logger.warning(f"Failed to update faculty {faculty_id} status (attempt {attempt + 1})")

            except Exception as e:
                logger.warning(f"Concurrent update conflict for faculty {faculty_id} (attempt {attempt + 1}): {e}")

                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff

        logger.error(f"Failed to update faculty {faculty_id} status after {max_retries} attempts")
        return None

    @cached_query(ttl=30)  # Reduced cache time to 30 seconds for more frequent updates
    def get_all_faculty(self, filter_available=None, search_term=None, page=None, page_size=50):
        """
        Get all faculty, optionally filtered by availability or search term.
        Results are cached for improved performance with optional pagination.

        Args:
            filter_available (bool, optional): Filter by availability status
            search_term (str, optional): Search term for name or department
            page (int, optional): Page number for pagination (1-based)
            page_size (int): Number of items per page

        Returns:
            list or dict: List of Faculty objects, or paginated results if page is specified
        """
        try:
            db = get_db(force_new=True)  # Force new session to avoid DetachedInstanceError
            try:
                query = db.query(Faculty)

                # Apply filters
                if filter_available is not None:
                    query = query.filter(Faculty.status == filter_available)

                if search_term:
                    search_pattern = f"%{search_term}%"
                    query = query.filter(
                        or_(
                            Faculty.name.ilike(search_pattern),
                            Faculty.department.ilike(search_pattern)
                        )
                    )

                # Order by name for consistent results
                query = query.order_by(Faculty.name)

                # Return paginated results if page is specified
                if page is not None:
                    return paginate_query(query, page, page_size)

                # For backward compatibility, return all results if no pagination
                faculties = query.all()

                # Ensure all attributes are loaded before returning
                for faculty in faculties:
                    # Access attributes to ensure they're loaded
                    _ = faculty.id, faculty.name, faculty.department, faculty.status
                    _ = getattr(faculty, 'always_available', False)
                    _ = getattr(faculty, 'email', '')

                logger.debug(f"Retrieved {len(faculties)} faculty members")
                return faculties

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error getting faculty list: {str(e)}")
            return [] if page is None else {'items': [], 'total_count': 0, 'page': 1, 'total_pages': 0}

    def get_faculty_by_id(self, faculty_id):
        """
        Get a faculty member by ID.

        Args:
            faculty_id (int): Faculty ID

        Returns:
            Faculty: Faculty object or None if not found
        """
        try:
            db = get_db()
            faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
            return faculty
        except Exception as e:
            logger.error(f"Error getting faculty by ID: {str(e)}")
            return None

    def get_faculty_by_ble_id(self, ble_id):
        """
        Get a faculty member by BLE ID.

        Args:
            ble_id (str): BLE beacon ID

        Returns:
            Faculty: Faculty object or None if not found
        """
        try:
            db = get_db()
            faculty = db.query(Faculty).filter(Faculty.ble_id == ble_id).first()

            if faculty:
                logger.info(f"Found faculty with BLE ID {ble_id}: {faculty.name} (ID: {faculty.id})")
            else:
                logger.warning(f"No faculty found with BLE ID: {ble_id}")

            return faculty
        except Exception as e:
            logger.error(f"Error getting faculty by BLE ID: {str(e)}")
            return None

    def add_faculty(self, name, department, email, ble_id, image_path=None, always_available=False):
        """
        Add a new faculty member with comprehensive input validation.

        Args:
            name (str): Faculty name
            department (str): Faculty department
            email (str): Faculty email
            ble_id (str): Faculty BLE beacon ID
            image_path (str, optional): Path to faculty image
            always_available (bool, optional): Deprecated parameter, no longer used

        Returns:
            tuple: (Faculty object or None, list of validation errors)
        """
        from ..utils.code_quality import safe_operation, OperationResult

        @safe_operation(log_errors=True)
        def _add_faculty_operation():
            # Validate inputs
            validation_errors = self._validate_faculty_inputs(name, department, email, ble_id)
            if validation_errors:
                return None, validation_errors

            # Check for duplicates
            duplicate_error = self._check_faculty_duplicates(email, ble_id)
            if duplicate_error:
                return None, [duplicate_error]

            # Create and save faculty
            faculty = self._create_and_save_faculty(name, department, email, ble_id, image_path)

            # Post-creation tasks
            self._handle_faculty_creation_success(faculty)

            return faculty, []

        result = _add_faculty_operation()
        if result.is_success():
            return result.get_data()
        else:
            error_msg = result.get_error_message()
            logger.error(f"Error adding faculty: {error_msg}")
            return None, [error_msg]

    def _validate_faculty_inputs(self, name, department, email, ble_id):
        """Validate all faculty input fields."""
        validation_errors = []

        validators = [
            (validate_name_safe, name),
            (validate_department_safe, department),
            (validate_email_safe, email),
            (validate_ble_id_safe, ble_id)
        ]

        for validator_func, value in validators:
            try:
                validator_func(value)
            except ValidationError as e:
                validation_errors.append(str(e))

        return validation_errors

    def _check_faculty_duplicates(self, email, ble_id):
        """Check for duplicate email or BLE ID."""
        try:
            db = get_db()
            existing = db.query(Faculty).filter(
                or_(Faculty.email == email, Faculty.ble_id == ble_id)
            ).first()

            if existing:
                return f"Faculty with email {email} or BLE ID {ble_id} already exists"
            return None
        except Exception as e:
            logger.error(f"Error checking faculty duplicates: {e}")
            return f"Error checking for duplicates: {str(e)}"

    def _create_and_save_faculty(self, name, department, email, ble_id, image_path):
        """Create and save new faculty to database."""
        db = get_db()

        faculty = Faculty(
            name=name,
            department=department,
            email=email,
            ble_id=ble_id,
            image_path=image_path,
            status=False,  # Initial status is False, will be updated by BLE
            always_available=False  # Always set to False
        )

        db.add(faculty)
        db.commit()

        logger.info(f"Added new faculty: {faculty.name} (ID: {faculty.id})")
        return faculty

    def _handle_faculty_creation_success(self, faculty):
        """Handle post-creation tasks for new faculty."""
        # Invalidate caches
        self._invalidate_faculty_caches()

        # Process any pending status updates for this faculty
        self._process_pending_status_updates(faculty.id)

        # Publish notification
        self._publish_faculty_creation_notification(faculty)

    def _publish_faculty_creation_notification(self, faculty):
        """Publish MQTT notification for new faculty creation."""
        try:
            notification = {
                'type': 'faculty_status',
                'faculty_id': faculty.id,
                'faculty_name': faculty.name,
                'status': faculty.status,
                'timestamp': faculty.last_seen.isoformat() if faculty.last_seen else None
            }
            publish_mqtt_message(MQTTTopics.SYSTEM_NOTIFICATIONS, notification)
            logger.info(f"Faculty {faculty.name} (ID: {faculty.id}) created with BLE-based availability")
        except Exception as e:
            logger.error(f"Error publishing faculty status notification: {str(e)}")

    def handle_faculty_heartbeat(self, topic: str, data):
        """
        Handle faculty heartbeat messages for enhanced monitoring.

        Args:
            topic (str): MQTT topic
            data (dict or str): Heartbeat data
        """
        try:
            # Parse heartbeat data
            if isinstance(data, str):
                try:
                    import json
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

            # Update last seen timestamp for the faculty
            db = get_db()
            try:
                faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
                if faculty:
                    faculty.last_seen = datetime.datetime.now()
                    db.commit()

                    # Log important status changes
                    if 'ntp_sync_status' in heartbeat_data:
                        ntp_status = heartbeat_data['ntp_sync_status']
                        if ntp_status == 'FAILED':
                            logger.warning(f"Faculty {faculty_id} ({faculty.name}) NTP sync failed")
                        elif ntp_status == 'SYNCED':
                            logger.debug(f"Faculty {faculty_id} ({faculty.name}) NTP synced")

                    # Monitor system health
                    if 'free_heap' in heartbeat_data:
                        free_heap = heartbeat_data.get('free_heap', 0)
                        if free_heap < 50000:  # Less than 50KB free
                            logger.warning(f"Faculty {faculty_id} ({faculty.name}) low memory: {free_heap} bytes")

            finally:
                db.close()

        except Exception as e:
            logger.debug(f"Error processing faculty heartbeat: {str(e)}")

    def _update_faculty_enhanced_status(self, faculty_id, status, ntp_sync_status, grace_period_active):
        """
        Update faculty with enhanced status information including NTP sync and grace period.

        Args:
            faculty_id (int): Faculty ID
            status (bool): Presence status
            ntp_sync_status (str): NTP synchronization status
            grace_period_active (bool): Whether grace period is active
        """
        try:
            # Use database manager for thread-safe operations
            from ..services.database_manager import get_database_manager
            db_manager = get_database_manager()

            with db_manager.get_session_context() as db:
                faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
                if faculty:
                    # Update enhanced status fields
                    faculty.ntp_sync_status = ntp_sync_status
                    faculty.grace_period_active = grace_period_active
                    faculty.last_seen = datetime.datetime.now()

                    # Only update main status if it actually changed
                    if faculty.status != status:
                        faculty.status = status
                        logger.info(f"Faculty {faculty_id} status updated: {status} (NTP: {ntp_sync_status}, Grace: {grace_period_active})")

                    # Commit happens automatically via context manager
                else:
                    logger.warning(f"Faculty {faculty_id} not found for enhanced status update")
        except Exception as e:
            logger.error(f"Error updating enhanced faculty status: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def update_faculty(self, faculty_id, name=None, department=None, email=None, ble_id=None, image_path=None, always_available=None):
        """
        Update an existing faculty member.

        Args:
            faculty_id (int): Faculty ID
            name (str, optional): New faculty name
            department (str, optional): New faculty department
            email (str, optional): New faculty email
            ble_id (str, optional): New faculty BLE beacon ID
            image_path (str, optional): New faculty image path
            always_available (bool, optional): Deprecated parameter, no longer used

        Returns:
            Faculty: Updated faculty object or None if error
        """
        try:
            db = get_db()
            faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()

            if not faculty:
                logger.error(f"Faculty not found: {faculty_id}")
                return None

            # Update fields if provided
            if name is not None:
                faculty.name = name

            if department is not None:
                faculty.department = department

            if email is not None and email != faculty.email:
                # Check if email already exists
                existing = db.query(Faculty).filter(Faculty.email == email).first()
                if existing and existing.id != faculty_id:
                    logger.error(f"Faculty with email {email} already exists")
                    return None
                faculty.email = email

            if ble_id is not None and ble_id != faculty.ble_id:
                # Check if BLE ID already exists
                existing = db.query(Faculty).filter(Faculty.ble_id == ble_id).first()
                if existing and existing.id != faculty_id:
                    logger.error(f"Faculty with BLE ID {ble_id} already exists")
                    return None
                faculty.ble_id = ble_id

            if image_path is not None:
                faculty.image_path = image_path

            # Set always_available to False regardless of input
            # Status is always determined by BLE connection
            if faculty.always_available:
                faculty.always_available = False
                logger.info(f"Faculty {faculty.name} (ID: {faculty.id}) status will be determined by BLE connection")

            db.commit()

            logger.info(f"Updated faculty: {faculty.name} (ID: {faculty.id})")

            # Invalidate faculty cache
            invalidate_faculty_cache()
            invalidate_cache_pattern("get_all_faculty")

            # Clear method-level cache if it exists
            if hasattr(self.get_all_faculty, 'cache_clear'):
                self.get_all_faculty.cache_clear()

            return faculty
        except Exception as e:
            logger.error(f"Error updating faculty: {str(e)}")
            return None

    def update_faculty_ble_id(self, faculty_id, ble_id):
        """
        Update a faculty member's BLE ID (for beacon assignment).

        Args:
            faculty_id (int): Faculty ID
            ble_id (str): New BLE ID (beacon MAC address)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = get_db()
            faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()

            if not faculty:
                logger.error(f"Faculty with ID {faculty_id} not found")
                return False

            # Validate BLE ID format
            if ble_id and not Faculty.validate_ble_id(ble_id):
                logger.error(f"Invalid BLE ID format: {ble_id}")
                return False

            # Check if BLE ID is already in use by another faculty
            if ble_id:
                existing = db.query(Faculty).filter(
                    Faculty.ble_id == ble_id,
                    Faculty.id != faculty_id
                ).first()

                if existing:
                    logger.error(f"BLE ID {ble_id} is already in use by faculty {existing.name}")
                    return False

            # Update BLE ID
            faculty.ble_id = ble_id
            faculty.updated_at = func.now()
            db.commit()

            logger.info(f"Updated BLE ID for faculty {faculty.name} (ID: {faculty_id}) to {ble_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating faculty BLE ID: {str(e)}")
            db.rollback()
            return False

    def delete_faculty(self, faculty_id):
        """
        Delete a faculty member.

        Args:
            faculty_id (int): Faculty ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = get_db()
            faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()

            if not faculty:
                logger.error(f"Faculty not found: {faculty_id}")
                return False

            db.delete(faculty)
            db.commit()

            logger.info(f"Deleted faculty: {faculty.name} (ID: {faculty.id})")

            # Invalidate faculty cache
            invalidate_faculty_cache()
            invalidate_cache_pattern("get_all_faculty")

            # Clear method-level cache if it exists
            if hasattr(self.get_all_faculty, 'cache_clear'):
                self.get_all_faculty.cache_clear()

            return True
        except Exception as e:
            logger.error(f"Error deleting faculty: {str(e)}")
            return False

    def ensure_available_faculty(self):
        """
        Ensure at least one faculty member is available for testing.
        If no faculty is available, make Dr. John Smith available.

        Returns:
            Faculty: The available faculty member or None if error
        """
        try:
            db = get_db()

            # Check if any faculty is available
            available_faculty = db.query(Faculty).filter(Faculty.status == True).first()

            if available_faculty:
                logger.info(f"Found available faculty: {available_faculty.name} (ID: {available_faculty.id})")
                return available_faculty

            # If no faculty is available, make Dr. John Smith available
            dr_john = db.query(Faculty).filter(Faculty.name == "Dr. John Smith").first()

            if dr_john:
                logger.info(f"Making Dr. John Smith (ID: {dr_john.id}) available for testing")
                dr_john.status = True
                db.commit()
                return dr_john

            # If Dr. John Smith doesn't exist, make the first faculty available
            first_faculty = db.query(Faculty).first()

            if first_faculty:
                logger.info(f"Making {first_faculty.name} (ID: {first_faculty.id}) available for testing")
                first_faculty.status = True
                db.commit()
                return first_faculty

            logger.warning("No faculty found in the database")
            return None
        except Exception as e:
            logger.error(f"Error ensuring available faculty: {str(e)}")
            return None