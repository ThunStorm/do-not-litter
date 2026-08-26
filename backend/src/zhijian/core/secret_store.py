from __future__ import annotations

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
            ["security", "add-generic-password", "-U", "-s", self.service, "-a", key, "-w", value],
            check=True,
            capture_output=True,
            text=True,
        )


def build_secret_store(kind: str, data_dir: Path) -> SecretStore:
    if kind == "keychain":
        return MacKeychainSecretStore()
    return FileSecretStore(data_dir / "secrets")
