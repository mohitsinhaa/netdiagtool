"""
dns_check.py — DNS connectivity & resolution diagnostics.

Provides forward resolution (A/AAAA via socket, plus optional rich
record lookups if `dnspython` is installed), reverse DNS, and
resolution timing.
"""

import socket
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    import dns.resolver  # type: ignore
    _HAS_DNSPYTHON = True
except ImportError:
    _HAS_DNSPYTHON = False


@dataclass
class DnsResult:
    host: str
    success: bool = False
    resolve_time_ms: Optional[float] = None
    ipv4_addresses: List[str] = field(default_factory=list)
    ipv6_addresses: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    reverse_dns: Optional[str] = None
    records: Dict[str, List[str]] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self):
        return self.__dict__


def _reverse_lookup(ip: str) -> Optional[str]:
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, OSError):
        return None


def _extended_records(host: str) -> Dict[str, List[str]]:
    """Best-effort lookup of A, AAAA, MX, NS, TXT records via dnspython."""
    records: Dict[str, List[str]] = {}
    if not _HAS_DNSPYTHON:
        return records
    resolver = dns.resolver.Resolver()
    resolver.lifetime = 3.0
    for rtype in ("A", "AAAA", "MX", "NS", "TXT"):
        try:
            answers = resolver.resolve(host, rtype)
            records[rtype] = [str(a).strip('"') for a in answers]
        except Exception:  # noqa: BLE001 — record type may simply not exist
            continue
    return records


def resolve_host(host: str, do_reverse: bool = True) -> DnsResult:
    """Resolve a hostname to IPv4/IPv6 addresses and report timing."""
    result = DnsResult(host=host)
    start = time.perf_counter()
    try:
        name, aliases, addrs = socket.gethostbyname_ex(host)
        result.resolve_time_ms = round((time.perf_counter() - start) * 1000, 2)
        result.aliases = aliases
        result.ipv4_addresses = addrs
        result.success = True

        try:
            infos = socket.getaddrinfo(host, None, socket.AF_INET6)
            result.ipv6_addresses = sorted({info[4][0] for info in infos})
        except socket.gaierror:
            pass

        if do_reverse and addrs:
            result.reverse_dns = _reverse_lookup(addrs[0])

        result.records = _extended_records(host)

    except socket.gaierror as exc:
        result.resolve_time_ms = round((time.perf_counter() - start) * 1000, 2)
        result.error = f"DNS resolution failed: {exc.strerror or exc}"
    except Exception as exc:  # noqa: BLE001
        result.error = str(exc)

    return result
