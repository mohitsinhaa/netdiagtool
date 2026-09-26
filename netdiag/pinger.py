"""
pinger.py — Ping connectivity diagnostics.

Uses the system `ping` binary (works cross-platform without needing
raw-socket / root privileges) and parses its output into structured
data. Falls back to a TCP-connect latency probe if the system ping
utility is unavailable (e.g. locked-down containers).
"""

import platform
import re
import subprocess
import socket
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PingResult:
    host: str
    resolved_ip: Optional[str] = None
    sent: int = 0
    received: int = 0
    loss_pct: float = 100.0
    min_ms: Optional[float] = None
    avg_ms: Optional[float] = None
    max_ms: Optional[float] = None
    mdev_ms: Optional[float] = None
    samples_ms: List[float] = field(default_factory=list)
    method: str = "icmp"
    success: bool = False
    error: Optional[str] = None
    raw_output: str = ""

    def to_dict(self):
        return self.__dict__


def _resolve(host: str) -> Optional[str]:
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return None


def _build_command(host: str, count: int, timeout: int) -> List[str]:
    system = platform.system().lower()
    if system == "windows":
        return ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
    # Linux / macOS
    return ["ping", "-c", str(count), "-W", str(timeout), host]


def _parse_unix_output(output: str) -> dict:
    samples = [float(m) for m in re.findall(r"time[=<]([\d.]+)\s*ms", output)]
    sent_match = re.search(r"(\d+)\s+packets transmitted", output)
    recv_match = re.search(r"(\d+)\s+(?:packets\s+)?received", output)
    loss_match = re.search(r"([\d.]+)%\s+packet loss", output)
    stats_match = re.search(
        r"= ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", output
    )  # min/avg/max/mdev
    result = {
        "sent": int(sent_match.group(1)) if sent_match else 0,
        "received": int(recv_match.group(1)) if recv_match else 0,
        "loss_pct": float(loss_match.group(1)) if loss_match else 100.0,
        "samples_ms": samples,
    }
    if stats_match:
        result["min_ms"] = float(stats_match.group(1))
        result["avg_ms"] = float(stats_match.group(2))
        result["max_ms"] = float(stats_match.group(3))
        result["mdev_ms"] = float(stats_match.group(4))
    elif samples:
        result["min_ms"] = min(samples)
        result["avg_ms"] = sum(samples) / len(samples)
        result["max_ms"] = max(samples)
    return result


def _parse_windows_output(output: str) -> dict:
    samples = [float(m) for m in re.findall(r"time[=<](\d+)ms", output)]
    sent_match = re.search(r"Sent = (\d+)", output)
    recv_match = re.search(r"Received = (\d+)", output)
    loss_match = re.search(r"\((\d+)% loss\)", output)
    stats_match = re.search(
        r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms", output
    )
    result = {
        "sent": int(sent_match.group(1)) if sent_match else 0,
        "received": int(recv_match.group(1)) if recv_match else 0,
        "loss_pct": float(loss_match.group(1)) if loss_match else 100.0,
        "samples_ms": samples,
    }
    if stats_match:
        result["min_ms"] = float(stats_match.group(1))
        result["max_ms"] = float(stats_match.group(2))
        result["avg_ms"] = float(stats_match.group(3))
    return result


def tcp_latency_probe(host: str, port: int = 80, count: int = 4,
                       timeout: int = 2) -> PingResult:
    """Fallback probe: measures TCP connect latency instead of ICMP."""
    ip = _resolve(host)
    result = PingResult(host=host, resolved_ip=ip, method="tcp", sent=count)
    if ip is None:
        result.error = f"Could not resolve hostname: {host}"
        return result

    samples = []
    for _ in range(count):
        start = time.perf_counter()
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                elapsed = (time.perf_counter() - start) * 1000
                samples.append(elapsed)
        except OSError:
            pass

    result.received = len(samples)
    result.loss_pct = round(100 * (1 - len(samples) / count), 2) if count else 100.0
    result.samples_ms = samples
    if samples:
        result.min_ms = min(samples)
        result.avg_ms = sum(samples) / len(samples)
        result.max_ms = max(samples)
        result.success = True
    else:
        result.error = f"No response on TCP port {port}"
    return result


def ping_host(host: str, count: int = 4, timeout: int = 2) -> PingResult:
    """
    Ping a host using the system ping utility.
    Returns a PingResult with structured statistics.
    """
    ip = _resolve(host)
    result = PingResult(host=host, resolved_ip=ip, sent=count)

    if ip is None:
        result.error = f"Could not resolve hostname: {host}"
        return result

    cmd = _build_command(host, count, timeout)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout * count + 5
        )
        result.raw_output = proc.stdout + proc.stderr
        parsed = (
            _parse_windows_output(result.raw_output)
            if platform.system().lower() == "windows"
            else _parse_unix_output(result.raw_output)
        )
        result.sent = parsed.get("sent", count) or count
        result.received = parsed.get("received", 0)
        result.loss_pct = parsed.get("loss_pct", 100.0)
        result.min_ms = parsed.get("min_ms")
        result.avg_ms = parsed.get("avg_ms")
        result.max_ms = parsed.get("max_ms")
        result.mdev_ms = parsed.get("mdev_ms")
        result.samples_ms = parsed.get("samples_ms", [])
        result.success = result.received > 0
        if not result.success and not result.error:
            result.error = "Host did not respond to ICMP echo requests " \
                            "(may be blocked by firewall)."
    except FileNotFoundError:
        # system ping binary not available — fall back to TCP probe
        return tcp_latency_probe(host, port=443, count=count, timeout=timeout)
    except subprocess.TimeoutExpired:
        result.error = "Ping command timed out."
    except Exception as exc:  # noqa: BLE001
        result.error = str(exc)

    return result
