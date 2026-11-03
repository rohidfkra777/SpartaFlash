"""
SpartaFlash - Workstation Authentication & RBAC Configuration
Developer: Rohidfkra777 (https://github.com/rohidfkra777)
"""
import os
import hashlib
import binascii
from enum import Enum
from typing import Optional, Dict, Any, Tuple

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"

class AuthenticatedUser:
    def __init__(self, username: str, role: UserRole, display_name: str):
        self.username = username
        self.role = role
        self.display_name = display_name

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_operator(self) -> bool:
        return self.role == UserRole.OPERATOR



    def can_manage_users(self) -> bool:
        return self.role == UserRole.ADMIN

    def can_access_settings(self) -> bool:
        return self.role == UserRole.ADMIN

    def can_flash(self) -> bool:
        return True

    def can_view_history(self) -> bool:
        return True

    def can_export_csv(self) -> bool:
        return True


# Default Initial Station Accounts (Salted PBKDF2-HMAC-SHA256)
# Admin default: admin / alfa@admin2026
_CREDENTIAL_VAULT: Dict[str, Dict[str, Any]] = {
    "admin": {
        "role": UserRole.ADMIN,
        "display_name": "System Administrator",
        "salt": "a1f4_adm1n_54lt_9921",
        "hash": "ff2e1226d3e014d89277076115ddff16b942cbadac7f8ade59e893477a4b8ead"
    },
    "operator": {
        "role": UserRole.OPERATOR,
        "display_name": "Line Operator 01",
        "salt": "a1f4_0p3r4t0r_54lt_1102",
        "hash": "d3dc05395246cbb6a392f5fdb807de7a684ba68dfcc963029bff10c46207b3cf"
    }
}

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    if not salt:
        salt = binascii.hexlify(os.urandom(16)).decode("utf-8")
    phash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return salt, phash

def get_active_vault() -> Dict[str, Dict[str, Any]]:
    return _CREDENTIAL_VAULT

def verify_user(username: str, password: str) -> Optional[AuthenticatedUser]:
    user_key = username.strip().lower()
    user_entry = _CREDENTIAL_VAULT.get(user_key)
    if not user_entry:
        return None
        
    salt = user_entry["salt"]
    expected_hash = user_entry["hash"]
    calc_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    
    if calc_hash == expected_hash:
        return AuthenticatedUser(
            username=user_key,
            role=user_entry["role"],
            display_name=user_entry["display_name"]
        )
    return None
