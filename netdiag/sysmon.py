"""
sysmon.py — CPU, RAM, disk and network monitoring.

Wraps `psutil` to produce a single structured snapshot of local
machine health, suitable for polling from a CLI live-view or a web
dashboard.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import psutil


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float

    def to_dict(self):
        return self.__dict__


@dataclass
class SystemSnapshot:
    timestamp: float
    cpu_percent: float
    cpu_per_core: List[float] = field(default_factory=list)
    cpu_count_logical: int = 0
    cpu_count_physical: int = 0
    load_avg: Optional[List[float]] = None
    mem_total_gb: float = 0.0
    mem_used_gb: float = 0.0
    mem_percent: float = 0.0
    swap_used_gb: float = 0.0
    swap_percent: float = 0.0
    disks: List[Dict] = field(default_factory=list)
    net_sent_mb: float = 0.0
    net_recv_mb: float = 0.0
    net_sent_rate_kbps: float = 0.0
    net_recv_rate_kbps: float = 0.0
    boot_time: float = 0.0
    uptime_seconds: float = 0.0
    top_processes: List[ProcessInfo] = field(default_factory=list)

    def to_dict(self):
        d = self.__dict__.copy()
        d["top_processes"] = [p.to_dict() for p in self.top_processes]
        return d


class SystemMonitor:
    """Stateful monitor that computes network throughput between polls."""

    def __init__(self):
        self._last_net = psutil.net_io_counters()
        self._last_time = time.time()
        # Warm up per-process cpu_percent measurement
        for proc in psutil.process_iter(["pid"]):
            try:
                proc.cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def snapshot(self, top_n_processes: int = 5) -> SystemSnapshot:
        now = time.time()
        elapsed = max(now - self._last_time, 1e-6)

        cpu_percent = psutil.cpu_percent(interval=0.2)
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()

        try:
            load_avg = list(psutil.getloadavg())
        except (AttributeError, OSError):
            load_avg = None

        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024 ** 3), 2),
                    "used_gb": round(usage.used / (1024 ** 3), 2),
                    "percent": usage.percent,
                })
            except PermissionError:
                continue

        net = psutil.net_io_counters()
        sent_rate = ((net.bytes_sent - self._last_net.bytes_sent) / elapsed) / 1024
        recv_rate = ((net.bytes_recv - self._last_net.bytes_recv) / elapsed) / 1024
        self._last_net = net
        self._last_time = now

        boot_time = psutil.boot_time()

        procs = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                cpu = proc.cpu_percent(None)
                mem = proc.memory_percent()
                procs.append(ProcessInfo(
                    pid=proc.info["pid"],
                    name=proc.info["name"] or "?",
                    cpu_percent=cpu,
                    memory_percent=round(mem, 2),
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda p: p.cpu_percent, reverse=True)

        return SystemSnapshot(
            timestamp=now,
            cpu_percent=cpu_percent,
            cpu_per_core=cpu_per_core,
            cpu_count_logical=psutil.cpu_count(logical=True) or 0,
            cpu_count_physical=psutil.cpu_count(logical=False) or 0,
            load_avg=load_avg,
            mem_total_gb=round(vm.total / (1024 ** 3), 2),
            mem_used_gb=round(vm.used / (1024 ** 3), 2),
            mem_percent=vm.percent,
            swap_used_gb=round(swap.used / (1024 ** 3), 2),
            swap_percent=swap.percent,
            disks=disks,
            net_sent_mb=round(net.bytes_sent / (1024 ** 2), 2),
            net_recv_mb=round(net.bytes_recv / (1024 ** 2), 2),
            net_sent_rate_kbps=round(sent_rate, 2),
            net_recv_rate_kbps=round(recv_rate, 2),
            boot_time=boot_time,
            uptime_seconds=round(now - boot_time, 0),
            top_processes=procs[:top_n_processes],
        )
