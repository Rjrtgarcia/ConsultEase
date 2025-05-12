import logging
from ..models import Admin, get_db

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdminController:
    """
    Controller for handling admin authentication and management.
    """
    
    def __init__(self):
        """
        Initialize the admin controller.
        """
        self.current_admin = None
    
    def authenticate(self, username, password):
        """
        Authenticate an admin user.
        
        Args:
            username (str): Admin username
            password (str): Admin password
            
        Returns:
            Admin: Admin object if authenticated, None otherwise
        """
        try:
            db = get_db()
            admin = db.query(Admin).filter(Admin.username == username, Admin.is_active == True).first()
            
            if not admin:
                logger.warning(f"Admin not found or inactive: {username}")
                return None
            
            if admin.check_password(password):
                logger.info(f"Admin authenticated: {username}")
                self.current_admin = admin
                return admin
            else:
                logger.warning(f"Invalid password for admin: {username}")
                return None
        except Exception as e:
            logger.error(f"Error authenticating admin: {str(e)}")
            return None
    
    def create_admin(self, username, password):
        """
        Create a new admin user.
        
        Args:
            username (str): Admin username
            password (str): Admin password
            
        Returns:
            Admin: New admin object or None if error
        """
        try:
            db = get_db()
            
            # Check if username already exists
            existing = db.query(Admin).filter(Admin.username == username).first()
            if existing:
                logger.error(f"Admin with username {username} already exists")
                return None
            
            # Hash password
            password_hash, salt = Admin.hash_password(password)
            
            # Create new admin
            admin = Admin(
                username=username,
                password_hash=password_hash,
                salt=salt,
                is_active=True
            )
            
            db.add(admin)
            db.commit()
            
            logger.info(f"Created new admin: {admin.username} (ID: {admin.id})")
            
            return admin
        except Exception as e:
            logger.error(f"Error creating admin: {str(e)}")
            return None
    
    def get_all_admins(self):
        """
        Get all admin users.
        
        Returns:
            list: List of Admin objects
        """
        try:
            db = get_db()
            admins = db.query(Admin).all()
            return admins
        except Exception as e:
            logger.error(f"Error getting admins: {str(e)}")
            return []
    
    def change_password(self, admin_id, old_password, new_password):
        """
        Change an admin user's password.
        
        Args:
            admin_id (int): Admin ID
            old_password (str): Current password
            new_password (str): New password
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = get_db()
            admin = db.query(Admin).filter(Admin.id == admin_id).first()
            
            if not admin:
                logger.error(f"Admin not found: {admin_id}")
                return False
            
            # Verify old password
            if not admin.check_password(old_password):
                logger.warning(f"Invalid old password for admin: {admin.username}")
                return False
            
            # Hash new password
            password_hash, salt = Admin.hash_password(new_password)
            
            # Update admin
            admin.password_hash = password_hash
            admin.salt = salt
            
            db.commit()
            
            logger.info(f"Changed password for admin: {admin.username}")
            
            return True
        except Exception as e:
            logger.error(f"Error changing admin password: {str(e)}")
            return False
    
    def deactivate_admin(self, admin_id):
        """
        Deactivate an admin user.
        
        Args:
            admin_id (int): Admin ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = get_db()
            admin = db.query(Admin).filter(Admin.id == admin_id).first()
            
            if not admin:
                logger.error(f"Admin not found: {admin_id}")
                return False
            
            # Check if this is the last active admin
            active_count = db.query(Admin).filter(Admin.is_active == True).count()
            if active_count <= 1 and admin.is_active:
                logger.error(f"Cannot deactivate the last active admin: {admin.username}")
                return False
            
            admin.is_active = False
            db.commit()
            
            logger.info(f"Deactivated admin: {admin.username}")
            
            return True
        except Exception as e:
            logger.error(f"Error deactivating admin: {str(e)}")
            return False
    
    def activate_admin(self, admin_id):
        """
        Activate an admin user.
        
        Args:
            admin_id (int): Admin ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = get_db()
            admin = db.query(Admin).filter(Admin.id == admin_id).first()
            
            if not admin:
                logger.error(f"Admin not found: {admin_id}")
                return False
            
            admin.is_active = True
            db.commit()
            
            logger.info(f"Activated admin: {admin.username}")
            
            return True
        except Exception as e:
            logger.error(f"Error activating admin: {str(e)}")
            return False
    
    def is_authenticated(self):
        """
        Check if an admin is currently authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        return self.current_admin is not None
    
    def logout(self):
        """
        Log out the current admin.
        """
        self.current_admin = None
        logger.info("Admin logged out")
    
    def ensure_default_admin(self):
        """
        Ensure that at least one admin user exists in the system.
        Creates a default admin if none exist.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = get_db()
            admin_count = db.query(Admin).count()
            
            if admin_count == 0:
                logger.info("No admin users found, creating default admin")
                
                # Create default admin
                default_username = "admin"
                default_password = "admin123"  # Should be changed immediately
                
                self.create_admin(default_username, default_password)
                
                logger.warning(
                    "Created default admin user with username 'admin' and password 'admin123'. "
                    "Please change this password immediately!"
                )
                
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error ensuring default admin: {str(e)}")
            return False 