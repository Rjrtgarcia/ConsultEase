from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import urllib.parse
import getpass

# Database connection settings
DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')  # Default to SQLite for development

if DB_TYPE.lower() == 'sqlite':
    # Use SQLite for development/testing
    DB_PATH = os.environ.get('DB_PATH', 'consultease.db')
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    print(f"Connecting to SQLite database: {DB_PATH}")
else:
    # Get current username - this will match PostgreSQL's peer authentication on Linux
    current_user = getpass.getuser()

    # PostgreSQL connection settings
    DB_USER = os.environ.get('DB_USER', current_user)
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')  # Empty password for peer authentication
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')  # Default PostgreSQL port
    DB_NAME = os.environ.get('DB_NAME', 'consultease')

    # Create PostgreSQL connection URL
    if DB_HOST == 'localhost' and not DB_PASSWORD:
        # Use Unix socket connection for peer authentication
        DATABASE_URL = f"postgresql+psycopg2://{DB_USER}@/{DB_NAME}"
        print(f"Connecting to PostgreSQL database: {DB_NAME} as {DB_USER} using peer authentication")
    else:
        # Use TCP connection with password
        encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
        DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        print(f"Connecting to PostgreSQL database: {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}")

engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def get_db(force_new=False):
    """
    Get database session.

    Args:
        force_new (bool): If True, create a new session even if one exists
    """
    # Create a new session
    db = SessionLocal()

    # If force_new is True, ensure we're getting fresh data
    if force_new:
        # Expire all objects in the session to force a refresh from the database
        db.expire_all()

        # You can also use this to clear the session entirely
        # db.close()
        # db = SessionLocal()

    try:
        return db
    except Exception as e:
        db.close()
        raise e

def init_db():
    """
    Initialize database tables and create default data if needed.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Check if we need to create default data
    db = SessionLocal()
    try:
        # Import models here to avoid circular imports
        from .admin import Admin
        from .faculty import Faculty
        from .student import Student

        # Check if admin table is empty
        admin_count = db.query(Admin).count()
        if admin_count == 0:
            # Create default admin with bcrypt hashed password
            password_hash, salt = Admin.hash_password("admin123")
            default_admin = Admin(
                username="admin",
                password_hash=password_hash,
                salt=salt,
                email="admin@consultease.com",
                is_active=True
            )
            db.add(default_admin)
            print("Created default admin user: admin / admin123")

        # Check if faculty table is empty
        faculty_count = db.query(Faculty).count()
        if faculty_count == 0:
            # Create some sample faculty
            sample_faculty = [
                Faculty(
                    name="Dr. John Smith",
                    department="Computer Science",
                    email="john.smith@university.edu",
                    ble_id="11:22:33:44:55:66",
                    status=True  # Set to True to make Dr. John Smith available for testing
                ),
                Faculty(
                    name="Dr. Jane Doe",
                    department="Mathematics",
                    email="jane.doe@university.edu",
                    ble_id="AA:BB:CC:DD:EE:FF",
                    status=False
                ),
                Faculty(
                    name="Jeysibn",
                    department="Computer Science",
                    email="jeysibn@university.edu",
                    ble_id="4fafc201-1fb5-459e-8fcc-c5c9c331914b",  # Match the SERVICE_UUID in the faculty desk unit code
                    status=True,  # Set to available for testing
                    always_available=True  # This faculty member is always available (BLE always on)
                )
            ]
            db.add_all(sample_faculty)
            print("Created sample faculty data")

        # Check if student table is empty
        student_count = db.query(Student).count()
        if student_count == 0:
            # Create some sample students
            sample_students = [
                Student(
                    name="Alice Johnson",
                    department="Computer Science",
                    rfid_uid="TESTCARD123"
                ),
                Student(
                    name="Bob Williams",
                    department="Mathematics",
                    rfid_uid="TESTCARD456"
                )
            ]
            db.add_all(sample_students)
            print("Created sample student data")

        db.commit()
    except Exception as e:
        print(f"Error creating default data: {str(e)}")
        db.rollback()
    finally:
        db.close()