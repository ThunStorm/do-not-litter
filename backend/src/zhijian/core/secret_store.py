from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path
from typing import Protocol


class SecretStore(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...


class FileSecretStore:
    """Development-only secret store with owner-only permissions."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)

    def _path(self, key: str) -> Path:
        safe_key = "".join(char for char in key if char.isalnum() or char in "-_")
        return self.root / safe_key

    def get(self, key: str) -> str | None:
        path = self._path(key)
        return path.read_text(encoding="utf-8") if path.exists() else None

    def set(self, key: str, value: str) -> None:
        path = self._path(key)
        path.write_text(value, encoding="utf-8")
        os.chmod(path, 0o600)


class MacKeychainSecretStore:
    def __init__(self, service: str = "cn.zhijian.local") -> None:
        self.service = service

    def get(self, key: str) -> str | None:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", self.service, "-a", key, "-w"],
            capture_output=True,
            check=False,
            text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    def set(self, key: str, value: str) -> None:
        subprocess.run(
            [
                "security",
                "add-generic-password",
                "-U",
                "-s",
                self.service,
                "-a",
                key,
                "-w",
                value,
            ],
            check=True,
            capture_output=True,
            text=True,
        )


class WindowsDPAPISecretStore:
    """Current-user DPAPI store; testable with injected protect/unprotect functions."""

    def __init__(self, root: Path, *, protect=None, unprotect=None) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.protect = protect or self._protect
        self.unprotect = unprotect or self._unprotect

    def _path(self, key: str) -> Path:
        safe = "".join(char for char in key if char.isalnum() or char in "-_")
        return self.root / f"{safe}.dpapi"

    def get(self, key: str) -> str | None:
        path = self._path(key)
        if not path.exists():
            return None
        return self.unprotect(path.read_bytes()).decode("utf-8")

    def set(self, key: str, value: str) -> None:
        path = self._path(key)
        path.write_bytes(self.protect(value.encode("utf-8")))

    @staticmethod
    def _protect(value: bytes) -> bytes:
        if os.name != "nt":
            raise RuntimeError("DPAPI 仅可在 Windows 当前用户会话中使用")
        # CryptProtectData via PowerShell avoids retaining plaintext on disk.
        encoded = base64.b64encode(value).decode("ascii")
        script = (
            "[Convert]::ToBase64String([Security.Cryptography.ProtectedData]::Protect("
            "[Convert]::FromBase64String($args[0]),$null,"
            "[Security.Cryptography.DataProtectionScope]::CurrentUser))"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script, encoded],
            capture_output=True,
            text=True,
            check=True,
        )
        return base64.b64decode(result.stdout.strip())

    @staticmethod
    def _unprotect(value: bytes) -> bytes:
        if os.name != "nt":
            raise RuntimeError("DPAPI 仅可在 Windows 当前用户会话中使用")
        encoded = base64.b64encode(value).decode("ascii")
        script = (
            "[Convert]::ToBase64String([Security.Cryptography.ProtectedData]::Unprotect("
            "[Convert]::FromBase64String($args[0]),$null,"
            "[Security.Cryptography.DataProtectionScope]::CurrentUser))"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script, encoded],
            capture_output=True,
            text=True,
            check=True,
        )
        return base64.b64decode(result.stdout.strip())


def build_secret_store(kind: str, data_dir: Path) -> SecretStore:
    if kind == "dpapi":
        return WindowsDPAPISecretStore(data_dir / "secrets")
    if kind == "keychain":
        return MacKeychainSecretStore()
    return FileSecretStore(data_dir / "secrets")
