"""
Enhanced Database Manager for ConsultEase.
Provides connection pooling, health monitoring, and resilient database operations.
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Database connection statistics."""
    total_connections: int = 0
    active_connections: int = 0
    failed_connections: int = 0
    total_queries: int = 0
    failed_queries: int = 0
    avg_query_time: float = 0.0
    last_connection_time: Optional[datetime] = None
    last_error: Optional[str] = None


class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""
    pass


class DatabaseManager:
    """
    Enhanced database manager with connection pooling and health monitoring.
    """

    def __init__(self, database_url: str, pool_size: int = 5, max_overflow: int = 10,
                 pool_timeout: int = 30, pool_recycle: int = 1800):
        """
        Initialize database manager.

        Args:
            database_url: Database connection URL
            pool_size: Number of connections to maintain in pool
            max_overflow: Maximum overflow connections
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Time to recycle connections (seconds)
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle

        # Connection management
        self.engine = None
        self.SessionLocal = None
        self.is_initialized = False

        # Statistics and monitoring
        self.stats = ConnectionStats()
        self.health_check_interval = 120.0  # seconds - increased to reduce conflicts with MQTT
        self.last_health_check = None
        self.is_healthy = True  # Start as healthy to avoid immediate restarts

        # Thread safety
        self.lock = threading.RLock()

        # Health monitoring
        self.health_monitor_thread = None
        self.monitoring_enabled = False

        logger.info("Database manager initialized")

    def initialize(self) -> bool:
        """
        Initialize database engine and connection pool with comprehensive error handling.

        Returns:
            bool: True if initialization successful
        """
        with self.lock:
            if self.is_initialized:
                logger.debug("Database manager already initialized")
                return True

            try:
                logger.info(f"🔄 Initializing database manager with URL: {self.database_url}")

                # Validate database configuration before proceeding
                if not self._validate_database_config():
                    logger.error("❌ Database configuration validation failed")
                    return False

                # Create engine with appropriate configuration for database type
                if self.database_url.startswith('sqlite'):
                    # Validate SQLite file system requirements
                    if not self._validate_sqlite_filesystem():
                        logger.error("❌ SQLite filesystem validation failed")
                        return False

                    # SQLite configuration - optimized for Raspberry Pi and thread safety
                    self.engine = create_engine(
                        self.database_url,
                        poolclass=StaticPool,  # Use StaticPool for SQLite
                        connect_args={
                            "check_same_thread": False,  # Allow SQLite to be used across threads
                            "timeout": 30,  # Increased timeout for Raspberry Pi
                            # Remove isolation_level=None to let SQLAlchemy handle transactions properly
                        },
                        pool_pre_ping=True,  # Validate connections before use
                        echo=False,  # Set to True for SQL debugging
                        pool_reset_on_return='commit',  # Reset connections on return
                        # Note: pool_timeout, pool_recycle are not valid for StaticPool with SQLite
                    )
                    logger.info("✅ Created SQLite engine with StaticPool and thread safety")
                else:
                    # PostgreSQL configuration - full connection pooling
                    self.engine = create_engine(
                        self.database_url,
                        poolclass=QueuePool,
                        pool_size=self.pool_size,
                        max_overflow=self.max_overflow,
                        pool_timeout=self.pool_timeout,
                        pool_recycle=self.pool_recycle,
                        pool_pre_ping=True,  # Validate connections before use
                        echo=False  # Set to True for SQL debugging
                    )
                    logger.info("✅ Created PostgreSQL engine with QueuePool")

                # Setup event listeners for monitoring
                self._setup_event_listeners()

                # Create session factory
                self.SessionLocal = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine
                )

                # Test initial connection with retry logic
                if self._test_connection_with_retry():
                    # Initialize database schema if needed
                    if not self._ensure_database_schema():
                        logger.error("❌ Database schema initialization failed")
                        return False

                    self.is_initialized = True
                    self.is_healthy = True
                    logger.info("✅ Database manager initialized successfully")

                    # Start health monitoring
                    self.start_health_monitoring()
                    return True
                else:
                    logger.error("❌ Failed to establish initial database connection after retries")
                    return False

            except Exception as e:
                logger.error(f"❌ Error initializing database manager: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.stats.last_error = str(e)
                return False

    def get_session(self, force_new: bool = False, max_retries: int = 3) -> Session:
        """
        Get database session with retry logic.

        Args:
            force_new: Force creation of new session
            max_retries: Maximum retry attempts

        Returns:
            Session: Database session

        Raises:
            DatabaseConnectionError: If unable to get session
        """
        if not self.is_initialized:
            if not self.initialize():
                raise DatabaseConnectionError("Database manager not initialized")

        last_error = None

        for attempt in range(max_retries):
            try:
                with self.lock:
                    # Create session
                    session = self.SessionLocal()

                    # Test session with health check
                    if self._test_session_health(session):
                        self.stats.total_connections += 1
                        self.stats.active_connections += 1
                        self.stats.last_connection_time = datetime.now()

                        if force_new:
                            session.expire_all()

                        logger.debug(f"Database session acquired (attempt {attempt + 1})")
                        return session
                    else:
                        session.close()
                        raise DatabaseConnectionError("Session health check failed")

            except Exception as e:
                last_error = e
                self.stats.failed_connections += 1
                logger.warning(f"Database session attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 30)  # Exponential backoff
                    logger.info(f"Retrying database connection in {wait_time} seconds...")
                    time.sleep(wait_time)

                    # Try to reinitialize if connection is completely lost
                    if isinstance(e, (DisconnectionError, OperationalError)):
                        self._reinitialize_engine()

        # All attempts failed
        self.stats.last_error = str(last_error)
        raise DatabaseConnectionError(f"Unable to get database session after {max_retries} attempts: {last_error}")

    @contextmanager
    def get_session_context(self, force_new: bool = False, max_retries: int = 3):
        """
        Context manager for database sessions with automatic cleanup.

        Args:
            force_new: Force creation of new session
            max_retries: Maximum retry attempts

        Yields:
            Session: Database session
        """
        session = None
        try:
            session = self.get_session(force_new=force_new, max_retries=max_retries)
            yield session
            session.commit()
        except Exception as e:
            if session:
                session.rollback()
            raise
        finally:
            if session:
                session.close()
                with self.lock:
                    self.stats.active_connections = max(0, self.stats.active_connections - 1)

    def execute_query(self, query: str, params: Dict = None, max_retries: int = 3) -> Any:
        """
        Execute a query with retry logic.

        Args:
            query: SQL query to execute
            params: Query parameters
            max_retries: Maximum retry attempts

        Returns:
            Query result
        """
        start_time = time.time()

        try:
            with self.get_session_context(max_retries=max_retries) as session:
                result = session.execute(text(query), params or {})

                # Update statistics
                query_time = time.time() - start_time
                self.stats.total_queries += 1
                self._update_avg_query_time(query_time)

                return result

        except Exception as e:
            self.stats.failed_queries += 1
            logger.error(f"Query execution failed: {e}")
            raise

    def start_health_monitoring(self):
        """Start health monitoring thread."""
        if self.monitoring_enabled:
            return

        self.monitoring_enabled = True
        self.health_monitor_thread = threading.Thread(
            target=self._health_monitor_loop,
            name="DatabaseHealthMonitor",
            daemon=True
        )
        self.health_monitor_thread.start()
        logger.info("Database health monitoring started")

    def stop_health_monitoring(self):
        """Stop health monitoring thread."""
        self.monitoring_enabled = False
        if self.health_monitor_thread and self.health_monitor_thread.is_alive():
            self.health_monitor_thread.join(timeout=5.0)
        logger.info("Database health monitoring stopped")

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get database health status.

        Returns:
            dict: Health status information
        """
        with self.lock:
            pool_status = {}
            if self.engine and hasattr(self.engine.pool, 'status'):
                pool = self.engine.pool
                pool_status = {
                    'pool_size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'invalid': pool.invalid()
                }

            return {
                'is_healthy': self.is_healthy,
                'is_initialized': self.is_initialized,
                'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
                'stats': {
                    'total_connections': self.stats.total_connections,
                    'active_connections': self.stats.active_connections,
                    'failed_connections': self.stats.failed_connections,
                    'total_queries': self.stats.total_queries,
                    'failed_queries': self.stats.failed_queries,
                    'avg_query_time': self.stats.avg_query_time,
                    'last_connection_time': self.stats.last_connection_time.isoformat() if self.stats.last_connection_time else None,
                    'last_error': self.stats.last_error
                },
                'pool_status': pool_status
            }

    def _test_connection(self) -> bool:
        """
        Test database connection directly using engine to avoid circular dependency.
        This method is called during initialization before the manager is fully initialized.
        """
        try:
            # Use direct engine connection to avoid circular dependency with get_session_context
            if not self.engine:
                logger.error("❌ Database engine not created yet")
                return False

            # Test connection directly using engine
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1 as health_check"))
                row = result.fetchone()
                success = row and row[0] == 1

                if success:
                    logger.debug("✅ Direct engine connection test successful")
                else:
                    logger.error("❌ Direct engine connection test failed - invalid result")

                return success

        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            import traceback
            logger.error(f"Connection test traceback: {traceback.format_exc()}")
            return False

    def _test_session_health(self, session: Session) -> bool:
        """Test session health."""
        try:
            result = session.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            return row and row[0] == 1
        except Exception as e:
            logger.debug(f"Session health check failed: {e}")
            return False

    def _test_health_check(self) -> bool:
        """
        Test database health using session context for ongoing health monitoring.
        This is different from _test_connection which is used during initialization.
        """
        try:
            if not self.is_initialized:
                logger.debug("Database manager not initialized, skipping health check")
                return False

            # Use session context for health check during normal operation
            with self.get_session_context() as session:
                result = session.execute(text("SELECT 1 as health_check"))
                row = result.fetchone()
                success = row and row[0] == 1

                if success:
                    logger.debug("✅ Database health check passed")
                else:
                    logger.warning("⚠️ Database health check failed - invalid result")

                return success

        except Exception as e:
            logger.warning(f"⚠️ Database health check failed: {e}")
            return False

    def _health_monitor_loop(self):
        """Health monitoring loop."""
        while self.monitoring_enabled:
            try:
                current_time = datetime.now()

                # Check if health check is due
                if (not self.last_health_check or
                    current_time - self.last_health_check >= timedelta(seconds=self.health_check_interval)):

                    self.is_healthy = self._test_health_check()
                    self.last_health_check = current_time

                    if not self.is_healthy:
                        logger.warning("Database health check failed")
                        # Try to reinitialize if unhealthy
                        self._reinitialize_engine()

                time.sleep(30.0)  # Check every 30 seconds to reduce conflicts with MQTT

            except Exception as e:
                logger.error(f"Error in database health monitor: {e}")
                time.sleep(10.0)  # Wait longer on error

    def _reinitialize_engine(self):
        """Reinitialize database engine."""
        try:
            logger.info("Reinitializing database engine...")

            with self.lock:
                # Dispose of old engine
                if self.engine:
                    self.engine.dispose()

                # Reset state
                self.is_initialized = False
                self.is_healthy = False

                # Reinitialize
                self.initialize()

        except Exception as e:
            logger.error(f"Error reinitializing database engine: {e}")

    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for monitoring."""
        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            logger.debug("Database connection established")

        @event.listens_for(self.engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Database connection checked out from pool")

        @event.listens_for(self.engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            logger.debug("Database connection checked in to pool")

    def _update_avg_query_time(self, query_time: float):
        """Update average query time."""
        if self.stats.total_queries == 1:
            self.stats.avg_query_time = query_time
        else:
            # Running average
            self.stats.avg_query_time = (
                (self.stats.avg_query_time * (self.stats.total_queries - 1) + query_time) /
                self.stats.total_queries
            )

    def _validate_database_config(self) -> bool:
        """Validate database configuration before initialization."""
        try:
            if not self.database_url:
                logger.error("❌ Database URL is empty")
                return False

            if self.database_url.startswith('sqlite'):
                # Extract database file path from URL
                db_path = self.database_url.replace('sqlite:///', '')
                if not db_path:
                    logger.error("❌ SQLite database path is empty")
                    return False

                logger.info(f"📁 SQLite database path: {db_path}")
                return True
            else:
                # For other database types, basic URL validation
                if '://' not in self.database_url:
                    logger.error("❌ Invalid database URL format")
                    return False
                return True

        except Exception as e:
            logger.error(f"❌ Database configuration validation error: {e}")
            return False

    def _validate_sqlite_filesystem(self) -> bool:
        """Validate SQLite filesystem requirements."""
        try:
            import os
            import stat

            # Extract database file path from URL
            db_path = self.database_url.replace('sqlite:///', '')
            db_dir = os.path.dirname(os.path.abspath(db_path)) if os.path.dirname(db_path) else '.'

            logger.info(f"🔍 Validating SQLite filesystem for: {db_path}")
            logger.info(f"📁 Database directory: {db_dir}")

            # Check if directory exists, create if needed
            if not os.path.exists(db_dir):
                logger.info(f"📁 Creating database directory: {db_dir}")
                try:
                    os.makedirs(db_dir, exist_ok=True)
                except PermissionError:
                    logger.error(f"❌ Permission denied creating directory: {db_dir}")
                    return False
                except Exception as e:
                    logger.error(f"❌ Error creating directory {db_dir}: {e}")
                    return False

            # Check directory permissions
            if not os.access(db_dir, os.W_OK):
                logger.error(f"❌ No write permission for directory: {db_dir}")
                return False

            # Check disk space (require at least 100MB)
            try:
                statvfs = os.statvfs(db_dir)
                free_space = statvfs.f_frsize * statvfs.f_bavail
                free_space_mb = free_space / (1024 * 1024)

                logger.info(f"💾 Available disk space: {free_space_mb:.1f} MB")

                if free_space_mb < 100:
                    logger.error(f"❌ Insufficient disk space: {free_space_mb:.1f} MB (minimum 100 MB required)")
                    return False
            except Exception as e:
                logger.warning(f"⚠️ Could not check disk space: {e}")

            # If database file exists, check if it's accessible
            if os.path.exists(db_path):
                logger.info(f"📄 Database file exists: {db_path}")

                # Check file permissions
                if not os.access(db_path, os.R_OK | os.W_OK):
                    logger.error(f"❌ No read/write permission for database file: {db_path}")
                    return False

                # Check if file is locked
                try:
                    with open(db_path, 'r+b') as f:
                        pass  # Just try to open for read/write
                except PermissionError:
                    logger.error(f"❌ Database file is locked or permission denied: {db_path}")
                    return False
                except Exception as e:
                    logger.warning(f"⚠️ Could not test file access: {e}")

                # Get file size
                file_size = os.path.getsize(db_path)
                logger.info(f"📊 Database file size: {file_size} bytes")

                # Check if file is corrupted (basic check)
                if file_size > 0:
                    try:
                        with open(db_path, 'rb') as f:
                            header = f.read(16)
                            if not header.startswith(b'SQLite format 3'):
                                logger.error(f"❌ Database file appears to be corrupted (invalid SQLite header)")
                                return False
                    except Exception as e:
                        logger.warning(f"⚠️ Could not validate SQLite header: {e}")
            else:
                logger.info(f"📄 Database file does not exist, will be created: {db_path}")

            logger.info("✅ SQLite filesystem validation passed")
            return True

        except Exception as e:
            logger.error(f"❌ SQLite filesystem validation error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def _test_connection_with_retry(self, max_retries: int = 3) -> bool:
        """Test database connection with retry logic and enhanced error reporting."""
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"🔌 Testing database connection (attempt {attempt + 1}/{max_retries})")

                # Perform detailed connection diagnostics
                self._log_connection_diagnostics(attempt + 1)

                # Try SQLAlchemy engine connection first
                if self._test_connection():
                    logger.info("✅ Database connection test successful")
                    return True
                else:
                    logger.warning(f"⚠️ SQLAlchemy connection test failed (attempt {attempt + 1})")

                    # Try direct SQLite connection as fallback
                    if self.database_url.startswith('sqlite'):
                        logger.info("🔄 Attempting direct SQLite connection as fallback...")
                        if self._test_direct_sqlite_connection():
                            logger.info("✅ Direct SQLite connection successful - SQLAlchemy engine may have issues")
                            # The direct connection works, so the issue is with SQLAlchemy configuration
                            # Let's try to recreate the engine with simpler configuration
                            if self._recreate_engine_simple():
                                logger.info("🔄 Retesting with simplified engine configuration...")
                                if self._test_connection():
                                    logger.info("✅ Database connection successful with simplified configuration")
                                    return True

                    error_msg = f"Both SQLAlchemy and direct connection tests failed (attempt {attempt + 1})"
                    logger.error(f"❌ {error_msg}")
                    last_error = error_msg

            except Exception as e:
                error_msg = f"Database connection test exception (attempt {attempt + 1}): {e}"
                logger.error(f"❌ {error_msg}")
                import traceback
                logger.error(f"Exception traceback: {traceback.format_exc()}")
                last_error = str(e)

            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

        logger.error(f"❌ All database connection attempts failed. Last error: {last_error}")
        return False

    def _log_connection_diagnostics(self, attempt: int):
        """Log detailed connection diagnostics for troubleshooting."""
        try:
            logger.info(f"🔍 Connection diagnostics (attempt {attempt}):")
            logger.info(f"   📁 Database URL: {self.database_url}")
            logger.info(f"   🔧 Engine created: {self.engine is not None}")

            if self.engine:
                logger.info(f"   🏊 Pool class: {type(self.engine.pool).__name__}")
                try:
                    pool_size = getattr(self.engine.pool, 'size', None)
                    if callable(pool_size):
                        pool_size = pool_size()
                    logger.info(f"   🔗 Pool size: {pool_size}")
                except Exception as e:
                    logger.info(f"   🔗 Pool size: N/A ({e})")

                try:
                    checked_in = getattr(self.engine.pool, 'checkedin', None)
                    checked_out = getattr(self.engine.pool, 'checkedout', None)
                    if callable(checked_in) and callable(checked_out):
                        logger.info(f"   📊 Pool status: checked_in={checked_in()}, checked_out={checked_out()}")
                    else:
                        logger.info(f"   📊 Pool status: N/A (StaticPool doesn't track connections)")
                except Exception as e:
                    logger.info(f"   📊 Pool status: N/A ({e})")

            # Check database file if SQLite
            if self.database_url.startswith('sqlite'):
                db_path = self.database_url.replace('sqlite:///', '')
                import os
                logger.info(f"   📄 Database file exists: {os.path.exists(db_path)}")
                if os.path.exists(db_path):
                    logger.info(f"   📏 Database file size: {os.path.getsize(db_path)} bytes")
                    logger.info(f"   🔐 File readable: {os.access(db_path, os.R_OK)}")
                    logger.info(f"   ✏️  File writable: {os.access(db_path, os.W_OK)}")

        except Exception as e:
            logger.warning(f"⚠️ Could not log connection diagnostics: {e}")

    def _test_direct_sqlite_connection(self) -> bool:
        """
        Test SQLite connection directly using sqlite3 module as fallback.
        This bypasses SQLAlchemy entirely for basic connectivity testing.
        """
        try:
            if not self.database_url.startswith('sqlite'):
                logger.debug("Direct SQLite test only works with SQLite databases")
                return False

            import sqlite3
            db_path = self.database_url.replace('sqlite:///', '')

            logger.info(f"🔌 Testing direct SQLite connection to: {db_path}")

            # Test direct SQLite connection
            with sqlite3.connect(db_path, timeout=30) as conn:
                cursor = conn.execute("SELECT 1 as direct_test")
                row = cursor.fetchone()
                success = row and row[0] == 1

                if success:
                    logger.info("✅ Direct SQLite connection test successful")

                    # Also test basic table creation to ensure write access
                    try:
                        conn.execute("CREATE TABLE IF NOT EXISTS connection_test (id INTEGER PRIMARY KEY, timestamp TEXT)")
                        conn.execute("INSERT INTO connection_test (timestamp) VALUES (?)", (time.time(),))
                        conn.execute("DELETE FROM connection_test WHERE id = last_insert_rowid()")
                        conn.commit()
                        logger.info("✅ Direct SQLite write test successful")
                    except Exception as write_e:
                        logger.warning(f"⚠️ Direct SQLite write test failed: {write_e}")
                        # Read-only access might still be sufficient for some operations

                else:
                    logger.error("❌ Direct SQLite connection test failed - invalid result")

                return success

        except Exception as e:
            logger.error(f"❌ Direct SQLite connection test failed: {e}")
            import traceback
            logger.error(f"Direct connection traceback: {traceback.format_exc()}")
            return False

    def _recreate_engine_simple(self) -> bool:
        """
        Recreate the SQLAlchemy engine with simplified configuration.
        This is used as a fallback when the standard configuration fails.
        """
        try:
            logger.info("🔄 Recreating SQLAlchemy engine with simplified configuration...")

            # Dispose of the current engine
            if self.engine:
                self.engine.dispose()

            # Create a simplified SQLite engine
            if self.database_url.startswith('sqlite'):
                self.engine = create_engine(
                    self.database_url,
                    # Minimal configuration for maximum compatibility
                    poolclass=StaticPool,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 30
                        # Remove all other parameters that might cause issues
                    },
                    echo=False,
                    # Remove pool configuration that might cause issues
                )
                logger.info("✅ Created simplified SQLite engine")

                # Recreate session factory
                self.SessionLocal = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine
                )

                return True
            else:
                logger.warning("⚠️ Simplified engine recreation only supports SQLite")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to recreate simplified engine: {e}")
            import traceback
            logger.error(f"Engine recreation traceback: {traceback.format_exc()}")
            return False

    def _ensure_database_schema(self) -> bool:
        """Ensure database schema is properly initialized."""
        try:
            logger.info("🔧 Ensuring database schema is initialized...")

            # Import models to ensure they're registered
            try:
                from ..models.base import Base
                from ..models import Faculty, Student, Admin, Consultation
                logger.info("📋 Imported database models")
            except ImportError as e:
                logger.error(f"❌ Failed to import database models: {e}")
                return False

            # Create tables if they don't exist
            try:
                Base.metadata.create_all(bind=self.engine)
                logger.info("✅ Database schema created/verified")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to create database schema: {e}")
                return False

        except Exception as e:
            logger.error(f"❌ Database schema initialization error: {e}")
            return False

    def shutdown(self):
        """Shutdown database manager."""
        logger.info("Shutting down database manager...")

        # Stop health monitoring
        self.stop_health_monitoring()

        # Dispose of engine
        with self.lock:
            if self.engine:
                self.engine.dispose()
                self.engine = None

            self.SessionLocal = None
            self.is_initialized = False
            self.is_healthy = False

        logger.info("Database manager shutdown complete")


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get or create global database manager instance."""
    global _database_manager
    if _database_manager is None:
        from ..utils.config_manager import get_config

        # Get database configuration
        db_config = get_config('database', {})
        database_url = _build_database_url(db_config)

        _database_manager = DatabaseManager(
            database_url=database_url,
            pool_size=db_config.get('pool_size', 5),
            max_overflow=db_config.get('max_overflow', 10),
            pool_timeout=db_config.get('pool_timeout', 30),
            pool_recycle=db_config.get('pool_recycle', 1800)
        )

        # Initialize the manager
        _database_manager.initialize()

    return _database_manager


def _build_database_url(db_config: Dict[str, Any]) -> str:
    """Build database URL from configuration."""
    db_type = db_config.get('type', 'sqlite')

    if db_type == 'sqlite':
        db_name = db_config.get('name', 'consultease.db')
        return f"sqlite:///{db_name}"
    elif db_type == 'postgresql':
        host = db_config.get('host', 'localhost')
        port = db_config.get('port', 5432)
        name = db_config.get('name', 'consultease')
        user = db_config.get('user', '')
        password = db_config.get('password', '')

        if user and password:
            return f"postgresql://{user}:{password}@{host}:{port}/{name}"
        else:
            return f"postgresql://{host}:{port}/{name}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def set_database_manager(manager: DatabaseManager):
    """Set global database manager instance."""
    global _database_manager
    _database_manager = manager
