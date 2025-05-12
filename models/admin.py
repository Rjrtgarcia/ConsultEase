from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
import bcrypt
import os
import logging
from .base import Base

# Set up logging
logger = logging.getLogger(__name__)

class Admin(Base):
    """
    Admin model.
    Represents an administrator in the system.
    """
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Admin {self.username}>"

    @staticmethod
    def hash_password(password, salt=None):
        """
        Hash a password using bcrypt.

        Args:
            password (str): The password to hash
            salt (str, optional): Not used with bcrypt, kept for backward compatibility

        Returns:
            tuple: (password_hash, empty string) - salt is included in the hash with bcrypt
        """
        try:
            # Generate a salt and hash the password
            password_bytes = password.encode('utf-8')
            hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(12))
            password_hash = hashed.decode('utf-8')

            # With bcrypt, the salt is included in the hash, so we don't need to store it separately
            return password_hash, ""
        except Exception as e:
            logger.error(f"Error hashing password: {str(e)}")
            # Fallback to a simple hash if bcrypt fails
            import hashlib
            simple_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            return simple_hash, ""

    def check_password(self, password):
        """
        Check if a password matches the stored hash using bcrypt.

        Args:
            password (str): The password to check

        Returns:
            bool: True if the password matches, False otherwise
        """
        try:
            # If the hash starts with $2b$, it's a bcrypt hash
            if self.password_hash.startswith('$2b$') or self.password_hash.startswith('$2a$'):
                password_bytes = password.encode('utf-8')
                hash_bytes = self.password_hash.encode('utf-8')
                return bcrypt.checkpw(password_bytes, hash_bytes)
            else:
                # Fallback for old-style hashes (SHA-256)
                import hashlib
                hash_obj = hashlib.sha256()
                hash_obj.update(self.salt.encode('utf-8'))
                hash_obj.update(password.encode('utf-8'))
                password_hash = hash_obj.hexdigest()
                return password_hash == self.password_hash
        except Exception as e:
            logger.error(f"Error checking password: {str(e)}")
            return False

    def to_dict(self):
        """
        Convert model instance to dictionary.
        """
        return {
            "id": self.id,
            "username": self.username,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }