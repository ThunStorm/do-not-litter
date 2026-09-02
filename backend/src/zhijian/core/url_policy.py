from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class HttpsHostPolicy:
    """Purpose-specific HTTPS allowlist with safe subdomain matching."""

    exact_hosts: frozenset[str] = field(default_factory=frozenset)
    host_suffixes: frozenset[str] = field(default_factory=frozenset)

    def allows(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower().rstrip(".")
            port = parsed.port
        except ValueError:
            return False
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username is not None
            or parsed.password is not None
            or port not in {None, 443}
        ):
            return False
        exact = {item.lower().rstrip(".") for item in self.exact_hosts}
        suffixes = {item.lower().strip(".") for item in self.host_suffixes}
        return host in exact or any(host == suffix or host.endswith(f".{suffix}") for suffix in suffixes)
