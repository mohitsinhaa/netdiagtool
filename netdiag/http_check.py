"""
http_check.py — HTTP/HTTPS availability and response-time diagnostics.

Measures status code, total round-trip time, redirect chain, response
headers, payload size, and (for HTTPS) certificate expiry.
"""

import socket
import ssl
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests


@dataclass
class HttpResult:
    url: str
    success: bool = False
    status_code: Optional[int] = None
    reason: Optional[str] = None
    response_time_ms: Optional[float] = None
    redirect_chain: List[str] = field(default_factory=list)
    final_url: Optional[str] = None
    content_length_bytes: Optional[int] = None
    server_header: Optional[str] = None
    content_type: Optional[str] = None
    tls_valid: Optional[bool] = None
    tls_issuer: Optional[str] = None
    tls_expires: Optional[str] = None
    tls_days_remaining: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self):
        return self.__dict__


def _check_tls_certificate(hostname: str, port: int = 443, timeout: int = 5) -> dict:
    info: Dict = {"tls_valid": None, "tls_issuer": None,
                  "tls_expires": None, "tls_days_remaining": None}
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        issuer = dict(x[0] for x in cert.get("issuer", []))
        expires_str = cert.get("notAfter")
        expires_dt = datetime.strptime(expires_str, "%b %d %H:%M:%S %Y %Z")
        expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        days_remaining = (expires_dt - datetime.now(timezone.utc)).days
        info.update({
            "tls_valid": True,
            "tls_issuer": issuer.get("organizationName") or issuer.get("commonName"),
            "tls_expires": expires_dt.strftime("%Y-%m-%d"),
            "tls_days_remaining": days_remaining,
        })
    except Exception:  # noqa: BLE001
        info["tls_valid"] = False
    return info


def check_url(url: str, timeout: int = 8, verify_tls: bool = True) -> HttpResult:
    """Perform an HTTP(S) availability + timing check against a URL."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    result = HttpResult(url=url)
    parsed = urlparse(url)

    try:
        start = time.perf_counter()
        resp = requests.get(
            url, timeout=timeout, allow_redirects=True,
            verify=verify_tls,
            headers={"User-Agent": "netdiag-toolkit/1.0"},
        )
        result.response_time_ms = round((time.perf_counter() - start) * 1000, 2)
        result.status_code = resp.status_code
        result.reason = resp.reason
        result.final_url = resp.url
        result.redirect_chain = [r.url for r in resp.history]
        result.content_length_bytes = len(resp.content)
        result.server_header = resp.headers.get("Server")
        result.content_type = resp.headers.get("Content-Type")
        result.success = resp.ok

        if parsed.scheme == "https":
            tls_info = _check_tls_certificate(parsed.hostname, parsed.port or 443)
            result.tls_valid = tls_info["tls_valid"]
            result.tls_issuer = tls_info["tls_issuer"]
            result.tls_expires = tls_info["tls_expires"]
            result.tls_days_remaining = tls_info["tls_days_remaining"]

    except requests.exceptions.SSLError as exc:
        result.error = f"TLS/SSL error: {exc}"
        result.tls_valid = False
    except requests.exceptions.ConnectTimeout:
        result.error = f"Connection timed out after {timeout}s."
    except requests.exceptions.ConnectionError as exc:
        result.error = f"Connection failed: {exc}"
    except Exception as exc:  # noqa: BLE001
        result.error = str(exc)

    return result
