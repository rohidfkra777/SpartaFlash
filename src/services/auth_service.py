"""
SpartaFlash - Station Authentication & Session Management Service.
Developer: Rohidfkra777
"""

import time
from typing import Optional, Tuple
from PySide6.QtCore import QObject, Signal

from src.config.auth_credentials import verify_user, AuthenticatedUser, UserRole
from src.utils.logger import get_logger
from src.services.activity_log_service import activity_logger, ActivityCategory, ActivityStatus


logger = get_logger()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 30

class AuthService(QObject):
    """
    Singleton service managing operator identity, session state, and security rate-limiting.
    """
    sig_auth_state_changed = Signal(object)  # Emits Optional[AuthenticatedUser]
    sig_lockout_triggered = Signal(int)     # Emits lockout duration in seconds

    def __init__(self):
        super().__init__()
        self._current_user: Optional[AuthenticatedUser] = None
        self._failed_attempts: int = 0
        self._lockout_until: float = 0.0

    @property
    def current_user(self) -> Optional[AuthenticatedUser]:
        return self._current_user

    @property
    def is_authenticated(self) -> bool:
        return self._current_user is not None



    @property
    def is_admin(self) -> bool:
        return self._current_user is not None and self._current_user.is_admin

    def get_display_name(self) -> str:
        if self._current_user:
            return self._current_user.display_name
        return "Unauthenticated"

    def get_lockout_seconds_remaining(self) -> int:
        now = time.time()
        if now < self._lockout_until:
            return int(self._lockout_until - now) + 1
        return 0

    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[AuthenticatedUser]]:
        """
        Attempts user authentication with brute-force lockout guard.
        Returns: (success: bool, message: str, user: Optional[AuthenticatedUser])
        """
        # Check brute force lockout
        remaining = self.get_lockout_seconds_remaining()
        if remaining > 0:
            return False, f"Too many failed attempts. Station locked for {remaining}s.", None

        user = verify_user(username, password)
        if user:
            self._current_user = user
            self._failed_attempts = 0
            self._lockout_until = 0.0
            logger.info(f"Station access granted: {user.username} ({user.role})")
            activity_logger.log(
                category=ActivityCategory.AUTH,
                action="LOGIN",
                details=f"Operator '{user.username}' successfully authenticated.",
                status=ActivityStatus.SUCCESS,
                username=user.username,
                role=getattr(user.role, "value", str(user.role))
            )
            pass
            self.sig_auth_state_changed.emit(self._current_user)
            return True, "Login successful", user

        # Failed attempt
        self._failed_attempts += 1
        logger.warning(f"Failed login attempt for username '{username}' (Attempt {self._failed_attempts}/{MAX_FAILED_ATTEMPTS})")
        activity_logger.log(
            category=ActivityCategory.AUTH,
            action="LOGIN_FAILED",
            details=f"Failed login attempt for username '{username}' ({self._failed_attempts}/{MAX_FAILED_ATTEMPTS})",
            status=ActivityStatus.WARNING,
            username=username,
            role="Unknown"
        )

        if self._failed_attempts >= MAX_FAILED_ATTEMPTS:
            self._lockout_until = time.time() + LOCKOUT_DURATION_SECONDS
            self.sig_lockout_triggered.emit(LOCKOUT_DURATION_SECONDS)
            activity_logger.log(
                category=ActivityCategory.AUTH,
                action="LOCKOUT_TRIGGERED",
                details=f"Station locked for {LOCKOUT_DURATION_SECONDS}s due to brute-force attempts on '{username}'",
                status=ActivityStatus.ERROR,
                username=username,
                role="Unknown"
            )
            pass
            return False, f"Too many failed attempts! Station locked for {LOCKOUT_DURATION_SECONDS} seconds.", None

        pass
        remaining_tries = MAX_FAILED_ATTEMPTS - self._failed_attempts
        return False, f"Invalid username or password ({remaining_tries} tries remaining).", None

    def set_authenticated_user(self, user: Optional[AuthenticatedUser]) -> None:
        """Explicitly sets the active authenticated user and emits auth state change."""
        self._current_user = user
        self.sig_auth_state_changed.emit(self._current_user)

    def logout(self) -> None:
        """Terminates the active session and locks the station."""
        if self._current_user:
            logger.info(f"User {self._current_user.username} logged out.")
            activity_logger.log(
                category=ActivityCategory.AUTH,
                action="LOGOUT",
                details=f"Operator '{self._current_user.username}' signed out or locked station.",
                status=ActivityStatus.INFO,
                username=self._current_user.username,
                role=getattr(self._current_user.role, "value", str(self._current_user.role))
            )
        self._current_user = None
        self.sig_auth_state_changed.emit(None)


# Global Singleton Instance
auth_service = AuthService()
