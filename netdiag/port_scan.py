"""
port_scan.py — Basic TCP port connectivity testing.

Performs a lightweight TCP-connect scan (no raw sockets / root
required) across a supplied port list or range, using a thread pool
for speed.
"""

import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

COMMON_PORTS: Dict[int, str] = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 123: "NTP", 143: "IMAP", 443: "HTTPS",
    445: "SMB", 465: "SMTPS", 587: "SMTP-Sub", 993: "IMAPS", 995: "POP3S",
    3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
    6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt", 27017: "MongoDB",
}


@dataclass
class PortResult:
    port: int
    open: bool
    service: str = ""
    latency_ms: Optional[float] = None

    def to_dict(self):
        return self.__dict__


@dataclass
class PortScanResult:
    host: str
    resolved_ip: Optional[str] = None
    scanned: int = 0
    open_ports: List[PortResult] = field(default_factory=list)
    closed_ports: List[PortResult] = field(default_factory=list)
    error: Optional[str] = None
    duration_ms: Optional[float] = None

    def to_dict(self):
        return {
            **{k: v for k, v in self.__dict__.items()
               if k not in ("open_ports", "closed_ports")},
            "open_ports": [p.to_dict() for p in self.open_ports],
            "closed_ports": [p.to_dict() for p in self.closed_ports],
        }


def _probe_port(ip: str, port: int, timeout: float) -> PortResult:
    start = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        conn_result = sock.connect_ex((ip, port))
        latency = round((time.perf_counter() - start) * 1000, 2)
        is_open = conn_result == 0
        return PortResult(
            port=port, open=is_open,
            service=COMMON_PORTS.get(port, "unknown"),
            latency_ms=latency if is_open else None,
        )
    finally:
        sock.close()


def scan_ports(host: str, ports: Optional[Iterable[int]] = None,
               timeout: float = 1.0, max_workers: int = 100) -> PortScanResult:
    """Scan a host across the given ports (defaults to COMMON_PORTS)."""
    if ports is None:
        ports = list(COMMON_PORTS.keys())
    ports = list(ports)

    result = PortScanResult(host=host, scanned=len(ports))
    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror:
        result.error = f"Could not resolve hostname: {host}"
        return result

    result.resolved_ip = ip
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=min(max_workers, len(ports) or 1)) as pool:
        futures = {pool.submit(_probe_port, ip, p, timeout): p for p in ports}
        for future in as_completed(futures):
            port_result = future.result()
            if port_result.open:
                result.open_ports.append(port_result)
            else:
                result.closed_ports.append(port_result)

    result.open_ports.sort(key=lambda p: p.port)
    result.closed_ports.sort(key=lambda p: p.port)
    result.duration_ms = round((time.perf_counter() - start) * 1000, 2)
    return result


def parse_port_spec(spec: str) -> List[int]:
    """
    Parse a port specification string into a list of ints.
    Supports: "22,80,443", "1-1024", "22,80,8000-8010", or "common".
    """
    spec = spec.strip().lower()
    if spec in ("", "common", "default"):
        return list(COMMON_PORTS.keys())

    ports: List[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if "-" in chunk:
            lo, hi = chunk.split("-", 1)
            ports.extend(range(int(lo), int(hi) + 1))
        elif chunk:
            ports.append(int(chunk))
    return sorted(set(ports))
