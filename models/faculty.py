from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .base import Base
import os

class Faculty(Base):
    """
    Faculty model.
    Represents a faculty member in the system.
    """
    __tablename__ = "faculty"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    ble_id = Column(String, unique=True, index=True)
    image_path = Column(String, nullable=True)  # Path to faculty image
    status = Column(Boolean, default=False)  # False = Unavailable, True = Available
    always_available = Column(Boolean, default=False)  # If True, faculty is always shown as available
    last_seen = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Faculty {self.name}>"

    def to_dict(self):
        """
        Convert model instance to dictionary.
        """
        return {
            "id": self.id,
            "name": self.name,
            "department": self.department,
            "email": self.email,
            "ble_id": self.ble_id,
            "image_path": self.image_path,
            "status": self.status,
            "always_available": self.always_available,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def get_image_path(self):
        """
        Get the full path to the faculty image.
        If no image is set, returns None.
        """
        if not self.image_path:
            return None

        # Check if the path is absolute
        if os.path.isabs(self.image_path):
            return self.image_path

        # Otherwise, assume it's relative to the images directory
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        images_dir = os.path.join(base_dir, 'images', 'faculty')

        # Create the directory if it doesn't exist
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)

        return os.path.join(images_dir, self.image_path)