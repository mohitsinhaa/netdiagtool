"""
cli.py — Command-line interface for the Network Diagnostic &
Server Monitoring Toolkit, styled with `rich`.

Usage:
    python -m netdiag.cli ping example.com
    python -m netdiag.cli dns example.com
    python -m netdiag.cli http https://example.com
    python -m netdiag.cli port example.com --ports common
    python -m netdiag.cli monitor
    python -m netdiag.cli all example.com
"""

import argparse
import sys
import time

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich import box

from . import dns_check, http_check, pinger, port_scan, sysmon

console = Console()

BANNER = r"""
[bold cyan] _   _ ______ _______ _____ _____          _____ [/]
[bold cyan]| \ | |  ____|__   __|  __ \_   _|   /\    / ____|[/]
[bold cyan]|  \| | |__     | |  | |  | || |    /  \  | |  __ [/]
[bold cyan]| . ` |  __|    | |  | |  | || |   / /\ \ | | |_ |[/]
[bold cyan]| |\  | |____   | |  | |__| || |_ / ____ \| |__| |[/]
[bold cyan]|_| \_|______|  |_|  |_____/_____/_/    \_\\_____|[/]
[dim]        Network Diagnostic & Server Monitoring Toolkit[/]
"""


def print_banner():
    console.print(BANNER)


def cmd_ping(args):
    with console.status(f"[cyan]Pinging {args.host}..."):
        result = pinger.ping_host(args.host, count=args.count, timeout=args.timeout)

    table = Table(title=f"Ping — {args.host}", box=box.ROUNDED, show_header=False)
    table.add_row("Resolved IP", result.resolved_ip or "—")
    table.add_row("Method", result.method.upper())
    table.add_row("Sent / Received", f"{result.sent} / {result.received}")
    loss_style = "green" if result.loss_pct == 0 else (
        "yellow" if result.loss_pct < 100 else "red")
    table.add_row("Packet Loss", f"[{loss_style}]{result.loss_pct}%[/]")
    if result.min_ms is not None:
        table.add_row("Min / Avg / Max",
                       f"{result.min_ms:.1f} / {result.avg_ms:.1f} / "
                       f"{result.max_ms:.1f} ms")
    if result.error:
        table.add_row("Note", f"[yellow]{result.error}[/]")

    status = "[bold green]● REACHABLE[/]" if result.success else "[bold red]● UNREACHABLE[/]"
    console.print(Panel(table, title=status, border_style="cyan"))


def cmd_dns(args):
    with console.status(f"[cyan]Resolving {args.host}..."):
        result = dns_check.resolve_host(args.host)

    table = Table(title=f"DNS — {args.host}", box=box.ROUNDED, show_header=False)
    table.add_row("Resolve time", f"{result.resolve_time_ms} ms"
                  if result.resolve_time_ms is not None else "—")
    table.add_row("IPv4", ", ".join(result.ipv4_addresses) or "—")
    table.add_row("IPv6", ", ".join(result.ipv6_addresses) or "—")
    table.add_row("Aliases", ", ".join(result.aliases) or "—")
    table.add_row("Reverse DNS", result.reverse_dns or "—")
    for rtype, values in result.records.items():
        table.add_row(f"{rtype} record", ", ".join(values))
    if result.error:
        table.add_row("Error", f"[red]{result.error}[/]")

    status = "[bold green]● RESOLVED[/]" if result.success else "[bold red]● FAILED[/]"
    console.print(Panel(table, title=status, border_style="cyan"))


def cmd_http(args):
    with console.status(f"[cyan]Requesting {args.url}..."):
        result = http_check.check_url(args.url, timeout=args.timeout)

    table = Table(title=f"HTTP — {args.url}", box=box.ROUNDED, show_header=False)
    if result.status_code:
        code_style = "green" if result.success else "red"
        table.add_row("Status", f"[{code_style}]{result.status_code} "
                                 f"{result.reason}[/]")
    table.add_row("Response time", f"{result.response_time_ms} ms"
                  if result.response_time_ms is not None else "—")
    table.add_row("Final URL", result.final_url or "—")
    if result.redirect_chain:
        table.add_row("Redirects", " → ".join(result.redirect_chain))
    table.add_row("Content-Type", result.content_type or "—")
    table.add_row("Content length", f"{result.content_length_bytes} bytes"
                  if result.content_length_bytes is not None else "—")
    table.add_row("Server", result.server_header or "—")
    if result.tls_valid is not None:
        tls_style = "green" if result.tls_valid else "red"
        table.add_row("TLS certificate",
                       f"[{tls_style}]{'valid' if result.tls_valid else 'invalid'}[/]")
        if result.tls_expires:
            table.add_row("TLS expires",
                           f"{result.tls_expires} ({result.tls_days_remaining} days)")
    if result.error:
        table.add_row("Error", f"[red]{result.error}[/]")

    status = "[bold green]● UP[/]" if result.success else "[bold red]● DOWN[/]"
    console.print(Panel(table, title=status, border_style="cyan"))


def cmd_port(args):
    ports = port_scan.parse_port_spec(args.ports)
    with Progress(
        TextColumn("[cyan]Scanning {task.fields[host]}"),
        BarColumn(), TextColumn("{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("scan", total=1, host=args.host)
        result = port_scan.scan_ports(args.host, ports, timeout=args.timeout)
        progress.update(task, completed=1)

    if result.error:
        console.print(Panel(f"[red]{result.error}[/]", title="● ERROR",
                             border_style="red"))
        return

    table = Table(title=f"Open ports — {args.host} ({result.resolved_ip})",
                  box=box.ROUNDED)
    table.add_column("Port", justify="right", style="bold cyan")
    table.add_column("Service")
    table.add_column("Latency", justify="right")
    if result.open_ports:
        for p in result.open_ports:
            table.add_row(str(p.port), p.service,
                          f"{p.latency_ms:.1f} ms" if p.latency_ms else "—")
    else:
        table.add_row("—", "no open ports found", "—")

    console.print(Panel(
        table,
        title=f"[bold]{len(result.open_ports)}/{result.scanned} open[/] · "
              f"{result.duration_ms:.0f} ms",
        border_style="cyan",
    ))


def _render_monitor(snap: sysmon.SystemSnapshot) -> Panel:
    header = Table.grid(expand=True)
    header.add_column(justify="left")
    header.add_column(justify="right")
    uptime_h = int(snap.uptime_seconds // 3600)
    uptime_m = int((snap.uptime_seconds % 3600) // 60)
    header.add_row(
        f"[bold]CPU[/] {snap.cpu_count_physical} cores "
        f"({snap.cpu_count_logical} threads)",
        f"uptime {uptime_h}h {uptime_m}m",
    )

    def bar(pct, width=30):
        filled = int(width * pct / 100)
        color = "green" if pct < 60 else ("yellow" if pct < 85 else "red")
        return f"[{color}]{'█' * filled}{'░' * (width - filled)}[/] {pct:5.1f}%"

    table = Table(box=box.SIMPLE, show_header=False, expand=True)
    table.add_column(ratio=1)
    table.add_column(ratio=3)
    table.add_row("CPU", bar(snap.cpu_percent))
    table.add_row("Memory", bar(snap.mem_percent))
    table.add_row(
        "", f"{snap.mem_used_gb:.1f} / {snap.mem_total_gb:.1f} GB"
    )
    for disk in snap.disks[:3]:
        table.add_row(f"Disk {disk['mountpoint']}", bar(disk["percent"]))
    table.add_row(
        "Network",
        f"↑ {snap.net_sent_rate_kbps:.1f} KB/s   ↓ {snap.net_recv_rate_kbps:.1f} KB/s",
    )

    proc_table = Table(title="Top processes", box=box.SIMPLE)
    proc_table.add_column("PID", justify="right")
    proc_table.add_column("Name")
    proc_table.add_column("CPU%", justify="right")
    proc_table.add_column("MEM%", justify="right")
    for p in snap.top_processes:
        proc_table.add_row(str(p.pid), p.name, f"{p.cpu_percent:.1f}",
                            f"{p.memory_percent:.1f}")

    from rich.console import Group
    return Panel(Group(header, table, proc_table),
                 title="[bold]● LIVE SYSTEM MONITOR[/] (Ctrl+C to exit)",
                 border_style="cyan")


def cmd_monitor(args):
    monitor = sysmon.SystemMonitor()
    try:
        with Live(console=console, refresh_per_second=2) as live:
            while True:
                snap = monitor.snapshot()
                live.update(_render_monitor(snap))
                time.sleep(args.interval)
    except KeyboardInterrupt:
        console.print("\n[dim]Monitor stopped.[/]")


def cmd_all(args):
    cmd_ping(args)
    cmd_dns(args)
    if not args.url:
        args.url = args.host
    cmd_http(args)
    cmd_port(args)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="netdiag",
        description="Network Diagnostic & Server Monitoring Toolkit",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ping = sub.add_parser("ping", help="ICMP/TCP reachability check")
    p_ping.add_argument("host")
    p_ping.add_argument("--count", type=int, default=4)
    p_ping.add_argument("--timeout", type=int, default=2)
    p_ping.set_defaults(func=cmd_ping)

    p_dns = sub.add_parser("dns", help="DNS resolution diagnostics")
    p_dns.add_argument("host")
    p_dns.set_defaults(func=cmd_dns)

    p_http = sub.add_parser("http", help="HTTP/HTTPS availability check")
    p_http.add_argument("url")
    p_http.add_argument("--timeout", type=int, default=8)
    p_http.set_defaults(func=cmd_http)

    p_port = sub.add_parser("port", help="TCP port connectivity scan")
    p_port.add_argument("host")
    p_port.add_argument("--ports", default="common",
                         help='e.g. "common", "1-1024", "22,80,443"')
    p_port.add_argument("--timeout", type=float, default=1.0)
    p_port.set_defaults(func=cmd_port)

    p_mon = sub.add_parser("monitor", help="Live CPU/RAM/disk/network monitor")
    p_mon.add_argument("--interval", type=float, default=1.0)
    p_mon.set_defaults(func=cmd_monitor)

    p_all = sub.add_parser("all", help="Run ping + dns + http + port on a target")
    p_all.add_argument("host")
    p_all.add_argument("--url", default=None)
    p_all.add_argument("--count", type=int, default=4)
    p_all.add_argument("--timeout", type=int, default=4)
    p_all.add_argument("--ports", default="common")
    p_all.set_defaults(func=cmd_all)

    return parser


def main(argv=None):
    print_banner()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/]")
        sys.exit(130)


if __name__ == "__main__":
    main()
