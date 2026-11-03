"""
SpartaFlash - Hardware Abstraction & Profile Interface.
Developer: Rohidfkra777
"""
from pathlib import Path
from typing import Optional

class SecurityVault:
    @classmethod
    def is_encrypted_vault_file(cls, path: Path) -> bool:
        return False

    @classmethod
    def decrypt_file_bytes(cls, path: Path) -> bytes:
        p = Path(path)
        return p.read_bytes() if p.exists() else b""

    @classmethod
    def get_ephemeral_firmware(cls, path: Path) -> Path:
        return Path(path)
