"""
SpartaFlash - Local User Activity Logging & Audit Service.
Developer: Rohidfkra777

Provides secure, private, 100% local activity logging for operator and station audits.
Zero telemetry / zero data transmission to external servers or developer.
"""

import sqlite3
import csv
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtCore import QObject, Signal

from src.config.constants import ACTIVITY_DB_PATH, DATABASE_DIR
from src.utils.logger import get_logger

logger = get_logger()


class ActivityCategory:
    AUTH = "AUTH"
    FLASHING = "FLASHING"
    CONFIG = "CONFIG"
    HARDWARE = "HARDWARE"
    SENSITIVE = "SENSITIVE"
    NAVIGATION = "NAVIGATION"


class ActivityStatus:
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ActivityLogService(QObject):
    """
    Singleton service managing local SQLite storage for operator activities.
    Guaranteed private to the local machine.
    """
    sig_activity_logged = Signal(dict)

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ActivityLogService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        super().__init__()
        self._db_path: Path = ACTIVITY_DB_PATH
        self._db_lock = threading.Lock()
        self._init_db()
        self._initialized = True

    def _init_db(self):
        """Initializes the local SQLite database schema."""
        try:
            DATABASE_DIR.mkdir(parents=True, exist_ok=True)
            with self._db_lock:
                with sqlite3.connect(str(self._db_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS user_activities (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            username TEXT NOT NULL,
                            role TEXT NOT NULL,
                            category TEXT NOT NULL,
                            action TEXT NOT NULL,
                            details TEXT,
                            status TEXT NOT NULL DEFAULT 'INFO'
                        )
                    """)
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_time ON user_activities(timestamp DESC)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_cat ON user_activities(category)")
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize activity log database: {e}")

    def log(
        self,
        category: str,
        action: str,
        details: str = "",
        status: str = ActivityStatus.INFO,
        username: Optional[str] = None,
        role: Optional[str] = None
    ):
        """
        Records a user activity event asynchronously and thread-safely.
        """
        try:
            if username is None or role is None:
                try:
                    from src.services.auth_service import auth_service
                    user = auth_service.current_user
                    if user:
                        username = username or user.username
                        role = role or getattr(user.role, "value", str(user.role))
                    else:
                        username = username or "Operator"
                        role = role or "Operator"
                except Exception:
                    username = username or "Operator"
                    role = role or "Operator"

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            event_dict = {
                "timestamp": now_str,
                "username": username,
                "role": role,
                "category": category,
                "action": action,
                "details": details,
                "status": status,
            }

            def _write():
                try:
                    with self._db_lock:
                        with sqlite3.connect(str(self._db_path)) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO user_activities 
                                (timestamp, username, role, category, action, details, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (now_str, username, role, category, action, details, status))
                            conn.commit()
                            event_dict["id"] = cursor.lastrowid
                    try:
                        self.sig_activity_logged.emit(event_dict)
                    except RuntimeError:
                        pass
                except Exception as ex:
                    logger.warning(f"Error persisting user activity: {ex}")

            # Run in thread or synchronously
            threading.Thread(target=_write, daemon=True).start()

        except Exception as e:
            logger.warning(f"Failed to log user activity: {e}")

    def get_activities(
        self,
        limit: int = 500,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves filtered activities from local SQLite storage."""
        results = []
        try:
            with self._db_lock:
                with sqlite3.connect(str(self._db_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    query = "SELECT * FROM user_activities WHERE 1=1"
                    params = []

                    if category and category != "ALL":
                        query += " AND category = ?"
                        params.append(category)

                    if date_from:
                        query += " AND timestamp >= ?"
                        params.append(date_from)

                    if search:
                        query += " AND (action LIKE ? OR details LIKE ? OR username LIKE ?)"
                        like_str = f"%{search}%"
                        params.extend([like_str, like_str, like_str])

                    query += " ORDER BY id DESC LIMIT ?"
                    params.append(limit)

                    cursor.execute(query, params)
                    for row in cursor.fetchall():
                        results.append(dict(row))
        except Exception as e:
            logger.error(f"Error reading activity logs: {e}")
        return results

    def get_stats_today(self) -> Dict[str, Any]:
        """Calculates today's activity metrics."""
        today_prefix = datetime.now().strftime("%Y-%m-%d")
        stats = {
            "total_today": 0,
            "flashing_count": 0,
            "config_changes": 0,
            "last_action": "-",
        }
        try:
            with self._db_lock:
                with sqlite3.connect(str(self._db_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT COUNT(*) FROM user_activities WHERE timestamp LIKE ?",
                        (f"{today_prefix}%",)
                    )
                    stats["total_today"] = cursor.fetchone()[0]

                    cursor.execute(
                        "SELECT COUNT(*) FROM user_activities WHERE timestamp LIKE ? AND category = 'FLASHING'",
                        (f"{today_prefix}%",)
                    )
                    stats["flashing_count"] = cursor.fetchone()[0]

                    cursor.execute(
                        "SELECT COUNT(*) FROM user_activities WHERE timestamp LIKE ? AND category = 'CONFIG'",
                        (f"{today_prefix}%",)
                    )
                    stats["config_changes"] = cursor.fetchone()[0]

                    cursor.execute(
                        "SELECT action, timestamp FROM user_activities ORDER BY id DESC LIMIT 1"
                    )
                    row = cursor.fetchone()
                    if row:
                        stats["last_action"] = f"{row[0]} ({row[1].split(' ')[1]})"
        except Exception as e:
            logger.warning(f"Error fetching today's stats: {e}")
        return stats

    def export_to_csv(self, filepath: str, category: Optional[str] = None, search: Optional[str] = None) -> bool:
        """Exports activity audit trail into a clean CSV file."""
        try:
            records = self.get_activities(limit=10000, category=category, search=search)
            with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Timestamp", "User", "Role", "Category", "Action", "Details", "Status"])
                for r in records:
                    writer.writerow([
                        r.get("id"),
                        r.get("timestamp"),
                        r.get("username"),
                        r.get("role"),
                        r.get("category"),
                        r.get("action"),
                        r.get("details"),
                        r.get("status")
                    ])
            return True
        except Exception as e:
            logger.error(f"Failed to export activity logs to CSV: {e}")
            return False

    def clear_activities(self) -> bool:
        """Clears all activity logs upon authorized operator request."""
        try:
            with self._db_lock:
                with sqlite3.connect(str(self._db_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM user_activities")
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name='user_activities'")
                    conn.commit()

            # Record that the logs were cleared
            self.log(
                category=ActivityCategory.SENSITIVE,
                action="CLEAR_LOGS",
                details="Operator cleared local activity audit log.",
                status=ActivityStatus.WARNING
            )
            return True
        except Exception as e:
            logger.error(f"Failed to clear activity logs: {e}")
            return False


# Global singleton instance
activity_logger = ActivityLogService()
