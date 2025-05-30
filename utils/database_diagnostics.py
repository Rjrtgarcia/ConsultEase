#!/usr/bin/env python3
"""
Database Diagnostics and Recovery Tool for ConsultEase

This tool provides comprehensive database diagnostics, validation, and recovery
capabilities for the ConsultEase system running on Raspberry Pi.
"""

import os
import sys
import logging
import sqlite3
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseDiagnostics:
    """Comprehensive database diagnostics and recovery tool."""

    def __init__(self, db_path: str = "consultease.db"):
        """
        Initialize database diagnostics.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_dir = os.path.dirname(os.path.abspath(db_path)) if os.path.dirname(db_path) else '.'
        self.backup_dir = os.path.join(self.db_dir, 'backups')

        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)

        logger.info(f"🔍 Database Diagnostics initialized for: {self.db_path}")
        logger.info(f"📁 Database directory: {self.db_dir}")
        logger.info(f"💾 Backup directory: {self.backup_dir}")

    def run_full_diagnostics(self) -> Dict[str, any]:
        """
        Run comprehensive database diagnostics.

        Returns:
            Dict containing diagnostic results
        """
        logger.info("🚀 Starting comprehensive database diagnostics...")

        results = {
            'timestamp': datetime.now().isoformat(),
            'database_path': self.db_path,
            'filesystem_check': self._check_filesystem(),
            'file_validation': self._validate_database_file(),
            'connection_test': self._test_database_connection(),
            'schema_validation': self._validate_schema(),
            'data_integrity': self._check_data_integrity(),
            'performance_check': self._check_performance(),
            'recommendations': []
        }

        # Generate recommendations based on results
        results['recommendations'] = self._generate_recommendations(results)

        # Print summary
        self._print_diagnostic_summary(results)

        return results

    def _check_filesystem(self) -> Dict[str, any]:
        """Check filesystem requirements and permissions."""
        logger.info("📁 Checking filesystem requirements...")

        result = {
            'directory_exists': os.path.exists(self.db_dir),
            'directory_writable': False,
            'disk_space_mb': 0,
            'permissions_ok': False,
            'issues': []
        }

        try:
            # Check directory permissions
            if result['directory_exists']:
                result['directory_writable'] = os.access(self.db_dir, os.W_OK)
                if not result['directory_writable']:
                    result['issues'].append("Directory is not writable")
            else:
                result['issues'].append("Database directory does not exist")

            # Check disk space
            try:
                statvfs = os.statvfs(self.db_dir)
                free_space = statvfs.f_frsize * statvfs.f_bavail
                result['disk_space_mb'] = free_space / (1024 * 1024)

                if result['disk_space_mb'] < 100:
                    result['issues'].append(f"Low disk space: {result['disk_space_mb']:.1f} MB")
            except Exception as e:
                result['issues'].append(f"Could not check disk space: {e}")

            # Overall permissions check
            result['permissions_ok'] = (
                result['directory_exists'] and
                result['directory_writable'] and
                result['disk_space_mb'] >= 100
            )

        except Exception as e:
            result['issues'].append(f"Filesystem check error: {e}")

        return result

    def _validate_database_file(self) -> Dict[str, any]:
        """Validate the database file itself."""
        logger.info("📄 Validating database file...")

        result = {
            'file_exists': os.path.exists(self.db_path),
            'file_size_bytes': 0,
            'file_readable': False,
            'file_writable': False,
            'sqlite_header_valid': False,
            'file_locked': False,
            'issues': []
        }

        try:
            if result['file_exists']:
                # Get file size
                result['file_size_bytes'] = os.path.getsize(self.db_path)

                # Check file permissions
                result['file_readable'] = os.access(self.db_path, os.R_OK)
                result['file_writable'] = os.access(self.db_path, os.W_OK)

                if not result['file_readable']:
                    result['issues'].append("Database file is not readable")
                if not result['file_writable']:
                    result['issues'].append("Database file is not writable")

                # Check SQLite header
                if result['file_size_bytes'] > 0:
                    try:
                        with open(self.db_path, 'rb') as f:
                            header = f.read(16)
                            result['sqlite_header_valid'] = header.startswith(b'SQLite format 3')
                            if not result['sqlite_header_valid']:
                                result['issues'].append("Invalid SQLite header - file may be corrupted")
                    except Exception as e:
                        result['issues'].append(f"Could not read SQLite header: {e}")

                # Check if file is locked
                try:
                    with open(self.db_path, 'r+b') as f:
                        pass  # Just try to open for read/write
                    result['file_locked'] = False
                except PermissionError:
                    result['file_locked'] = True
                    result['issues'].append("Database file appears to be locked")
                except Exception as e:
                    result['issues'].append(f"Could not test file lock: {e}")
            else:
                result['issues'].append("Database file does not exist")

        except Exception as e:
            result['issues'].append(f"File validation error: {e}")

        return result

    def _test_database_connection(self) -> Dict[str, any]:
        """Test database connection and basic operations."""
        logger.info("🔌 Testing database connection...")

        result = {
            'connection_successful': False,
            'query_test_passed': False,
            'write_test_passed': False,
            'sqlalchemy_test_passed': False,
            'connection_time_ms': 0,
            'issues': []
        }

        try:
            start_time = time.time()

            # Test direct SQLite connection first
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                # Test connection
                result['connection_successful'] = True
                result['connection_time_ms'] = (time.time() - start_time) * 1000

                # Test basic query
                try:
                    cursor = conn.execute("SELECT 1 as test")
                    row = cursor.fetchone()
                    if row and row[0] == 1:
                        result['query_test_passed'] = True
                    else:
                        result['issues'].append("Basic query test failed")
                except Exception as e:
                    result['issues'].append(f"Query test failed: {e}")

                # Test write operation
                try:
                    conn.execute("CREATE TABLE IF NOT EXISTS diagnostic_test (id INTEGER PRIMARY KEY, timestamp TEXT)")
                    conn.execute("INSERT INTO diagnostic_test (timestamp) VALUES (?)", (datetime.now().isoformat(),))
                    conn.execute("DELETE FROM diagnostic_test WHERE id = last_insert_rowid()")
                    conn.commit()
                    result['write_test_passed'] = True
                except Exception as e:
                    result['issues'].append(f"Write test failed: {e}")

            # Test SQLAlchemy connection if direct connection works
            if result['connection_successful']:
                try:
                    logger.info("🔧 Testing SQLAlchemy database manager connection...")

                    # Import and test the database manager
                    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from services.database_manager import DatabaseManager

                    # Create a test database manager
                    test_manager = DatabaseManager(f"sqlite:///{self.db_path}")

                    if test_manager.initialize():
                        result['sqlalchemy_test_passed'] = True
                        logger.info("✅ SQLAlchemy database manager test successful")
                        test_manager.shutdown()
                    else:
                        result['issues'].append("SQLAlchemy database manager initialization failed")

                except Exception as e:
                    result['issues'].append(f"SQLAlchemy test failed: {e}")
                    logger.warning(f"⚠️ SQLAlchemy test failed: {e}")

        except Exception as e:
            result['issues'].append(f"Connection test failed: {e}")

        return result

    def _validate_schema(self) -> Dict[str, any]:
        """Validate database schema and tables."""
        logger.info("🔧 Validating database schema...")

        result = {
            'tables_found': [],
            'expected_tables': ['faculty', 'student', 'admin', 'consultation'],
            'missing_tables': [],
            'table_counts': {},
            'schema_valid': False,
            'issues': []
        }

        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                # Get list of tables
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                result['tables_found'] = tables

                # Check for missing tables
                result['missing_tables'] = [
                    table for table in result['expected_tables']
                    if table not in tables
                ]

                # Get row counts for each table
                for table in tables:
                    try:
                        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        result['table_counts'][table] = count
                    except Exception as e:
                        result['issues'].append(f"Could not count rows in {table}: {e}")

                # Schema is valid if all expected tables exist
                result['schema_valid'] = len(result['missing_tables']) == 0

                if result['missing_tables']:
                    result['issues'].append(f"Missing tables: {', '.join(result['missing_tables'])}")

        except Exception as e:
            result['issues'].append(f"Schema validation failed: {e}")

        return result

    def _check_data_integrity(self) -> Dict[str, any]:
        """Check data integrity and consistency."""
        logger.info("🔍 Checking data integrity...")

        result = {
            'integrity_check_passed': False,
            'foreign_key_check_passed': False,
            'admin_account_exists': False,
            'issues': []
        }

        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                # SQLite integrity check
                try:
                    cursor = conn.execute("PRAGMA integrity_check")
                    integrity_result = cursor.fetchone()[0]
                    result['integrity_check_passed'] = integrity_result == 'ok'
                    if not result['integrity_check_passed']:
                        result['issues'].append(f"Integrity check failed: {integrity_result}")
                except Exception as e:
                    result['issues'].append(f"Integrity check error: {e}")

                # Foreign key check
                try:
                    cursor = conn.execute("PRAGMA foreign_key_check")
                    fk_violations = cursor.fetchall()
                    result['foreign_key_check_passed'] = len(fk_violations) == 0
                    if fk_violations:
                        result['issues'].append(f"Foreign key violations found: {len(fk_violations)}")
                except Exception as e:
                    result['issues'].append(f"Foreign key check error: {e}")

                # Check for admin account
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM admin WHERE username = 'admin'")
                    admin_count = cursor.fetchone()[0]
                    result['admin_account_exists'] = admin_count > 0
                    if not result['admin_account_exists']:
                        result['issues'].append("No admin account found")
                except Exception as e:
                    result['issues'].append(f"Admin account check error: {e}")

        except Exception as e:
            result['issues'].append(f"Data integrity check failed: {e}")

        return result

    def _check_performance(self) -> Dict[str, any]:
        """Check database performance metrics."""
        logger.info("⚡ Checking database performance...")

        result = {
            'query_time_ms': 0,
            'index_usage': {},
            'database_size_mb': 0,
            'page_count': 0,
            'issues': []
        }

        try:
            # Get database file size
            if os.path.exists(self.db_path):
                result['database_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)

            with sqlite3.connect(self.db_path, timeout=30) as conn:
                # Test query performance
                start_time = time.time()
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM faculty")
                    cursor.fetchone()
                    result['query_time_ms'] = (time.time() - start_time) * 1000
                except Exception as e:
                    result['issues'].append(f"Performance test query failed: {e}")

                # Get page count
                try:
                    cursor = conn.execute("PRAGMA page_count")
                    result['page_count'] = cursor.fetchone()[0]
                except Exception as e:
                    result['issues'].append(f"Could not get page count: {e}")

                # Check index usage
                try:
                    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
                    indexes = [row[0] for row in cursor.fetchall()]
                    result['index_usage']['total_indexes'] = len(indexes)
                    result['index_usage']['indexes'] = indexes
                except Exception as e:
                    result['issues'].append(f"Could not check indexes: {e}")

        except Exception as e:
            result['issues'].append(f"Performance check failed: {e}")

        return result

    def _generate_recommendations(self, results: Dict[str, any]) -> List[str]:
        """Generate recommendations based on diagnostic results."""
        recommendations = []

        # Filesystem recommendations
        fs_check = results.get('filesystem_check', {})
        if not fs_check.get('permissions_ok', False):
            recommendations.append("Fix filesystem permissions and ensure adequate disk space")

        # File validation recommendations
        file_check = results.get('file_validation', {})
        if not file_check.get('file_exists', False):
            recommendations.append("Create new database file - run database initialization")
        elif not file_check.get('sqlite_header_valid', False):
            recommendations.append("Database file is corrupted - restore from backup or recreate")
        elif file_check.get('file_locked', False):
            recommendations.append("Database file is locked - check for running processes")

        # Connection recommendations
        conn_check = results.get('connection_test', {})
        if not conn_check.get('connection_successful', False):
            recommendations.append("Database connection failed - check file permissions and SQLite installation")
        elif not conn_check.get('write_test_passed', False):
            recommendations.append("Database write operations failed - check file permissions")

        # Schema recommendations
        schema_check = results.get('schema_validation', {})
        if not schema_check.get('schema_valid', False):
            recommendations.append("Database schema is incomplete - run database initialization")

        # Data integrity recommendations
        integrity_check = results.get('data_integrity', {})
        if not integrity_check.get('integrity_check_passed', False):
            recommendations.append("Database integrity check failed - consider restoring from backup")
        if not integrity_check.get('admin_account_exists', False):
            recommendations.append("No admin account found - run admin account creation")

        # Performance recommendations
        perf_check = results.get('performance_check', {})
        if perf_check.get('query_time_ms', 0) > 1000:
            recommendations.append("Database queries are slow - consider optimization")

        if not recommendations:
            recommendations.append("Database appears to be healthy - no issues detected")

        return recommendations

    def _print_diagnostic_summary(self, results: Dict[str, any]):
        """Print a formatted summary of diagnostic results."""
        print("\n" + "="*60)
        print("🔍 DATABASE DIAGNOSTIC SUMMARY")
        print("="*60)
        print(f"📅 Timestamp: {results['timestamp']}")
        print(f"📁 Database: {results['database_path']}")
        print()

        # Print each check result
        checks = [
            ('filesystem_check', '📁 Filesystem Check'),
            ('file_validation', '📄 File Validation'),
            ('connection_test', '🔌 Connection Test'),
            ('schema_validation', '🔧 Schema Validation'),
            ('data_integrity', '🔍 Data Integrity'),
            ('performance_check', '⚡ Performance Check')
        ]

        for check_key, check_name in checks:
            check_result = results.get(check_key, {})
            issues = check_result.get('issues', [])

            if issues:
                print(f"{check_name}: ❌ FAILED")
                for issue in issues:
                    print(f"  • {issue}")
            else:
                print(f"{check_name}: ✅ PASSED")
            print()

        # Print recommendations
        print("💡 RECOMMENDATIONS:")
        for i, rec in enumerate(results.get('recommendations', []), 1):
            print(f"  {i}. {rec}")
        print()
        print("="*60)

    def create_backup(self) -> Optional[str]:
        """Create a backup of the current database."""
        if not os.path.exists(self.db_path):
            logger.error("❌ Cannot backup - database file does not exist")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"consultease_backup_{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"✅ Database backup created: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None

    def repair_database(self) -> bool:
        """Attempt to repair database issues."""
        logger.info("🔧 Attempting database repair...")

        # Create backup first
        backup_path = self.create_backup()
        if not backup_path:
            logger.error("❌ Cannot proceed with repair - backup failed")
            return False

        try:
            # Run diagnostics to identify issues
            results = self.run_full_diagnostics()

            # Attempt repairs based on issues found
            repair_success = True

            # Fix schema issues
            schema_check = results.get('schema_validation', {})
            if not schema_check.get('schema_valid', False):
                logger.info("🔧 Attempting to fix schema issues...")
                if not self._repair_schema():
                    repair_success = False

            # Fix admin account issues
            integrity_check = results.get('data_integrity', {})
            if not integrity_check.get('admin_account_exists', False):
                logger.info("🔧 Attempting to create admin account...")
                if not self._repair_admin_account():
                    repair_success = False

            if repair_success:
                logger.info("✅ Database repair completed successfully")
            else:
                logger.error("❌ Database repair failed - consider restoring from backup")

            return repair_success

        except Exception as e:
            logger.error(f"❌ Database repair failed: {e}")
            return False

    def _repair_schema(self) -> bool:
        """Repair database schema by recreating tables."""
        try:
            # Import and run database initialization
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from models.base import init_db

            logger.info("🔧 Running database initialization to repair schema...")
            init_db()
            logger.info("✅ Schema repair completed")
            return True

        except Exception as e:
            logger.error(f"❌ Schema repair failed: {e}")
            return False

    def _repair_admin_account(self) -> bool:
        """Repair admin account by creating default account."""
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                # Check if admin table exists
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin'")
                if not cursor.fetchone():
                    logger.error("❌ Admin table does not exist - run schema repair first")
                    return False

                # Create default admin account (simplified version)
                import hashlib
                import secrets

                password = "TempPass123!"
                salt = secrets.token_hex(32)
                password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

                conn.execute("""
                    INSERT OR REPLACE INTO admin (username, password_hash, salt, is_active, force_password_change)
                    VALUES (?, ?, ?, ?, ?)
                """, ("admin", password_hash, salt, True, True))

                conn.commit()
                logger.info("✅ Default admin account created")
                logger.warning("🔑 Default credentials: admin / TempPass123!")
                logger.warning("⚠️  SECURITY NOTICE: Change password on first login!")
                return True

        except Exception as e:
            logger.error(f"❌ Admin account repair failed: {e}")
            return False


def main():
    """Main function for running database diagnostics."""
    import argparse

    parser = argparse.ArgumentParser(description="ConsultEase Database Diagnostics Tool")
    parser.add_argument("--db-path", default="consultease.db", help="Path to database file")
    parser.add_argument("--repair", action="store_true", help="Attempt to repair database issues")
    parser.add_argument("--backup", action="store_true", help="Create database backup")

    args = parser.parse_args()

    # Initialize diagnostics
    diagnostics = DatabaseDiagnostics(args.db_path)

    if args.backup:
        diagnostics.create_backup()

    if args.repair:
        diagnostics.repair_database()
    else:
        # Run diagnostics only
        diagnostics.run_full_diagnostics()


if __name__ == "__main__":
    main()
