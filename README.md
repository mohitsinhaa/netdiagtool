# NETDIAG — Network Diagnostic & Server Monitoring Toolkit

A Python toolkit for everyday network and server diagnostics, with two
ways to use it:

1. **A premium web dashboard** — a control-room style live UI for
   pinging, DNS lookups, HTTP checks, port scans, and real-time
   CPU/RAM/disk/network monitoring.
2. **A CLI** — the same diagnostics, scriptable, with a `rich`-styled
   terminal UI and a live monitor mode.

Both sit on top of one shared Python library (`netdiag/`), so anything
the dashboard can do, you can also call directly from your own scripts.

## Features

- **Ping diagnostics** — ICMP reachability, packet loss, min/avg/max
  latency (falls back to a TCP-connect probe if ICMP is unavailable).
- **DNS diagnostics** — forward resolution timing, IPv4/IPv6, aliases,
  reverse DNS, and (if `dnspython` is installed) A/AAAA/MX/NS/TXT
  record lookups.
- **HTTP/HTTPS checks** — status code, response time, redirect chain,
  content type/size, server header, and TLS certificate validity +
  expiry countdown.
- **Port connectivity testing** — fast threaded TCP-connect scan of
  common ports or a custom list/range (`22,80,443`, `1-1024`, etc).
- **System monitoring** — CPU (overall + per-core), memory, swap,
  per-disk usage, live network throughput, uptime, and top processes
  by CPU usage.

## 1. Install

```bash
cd netdiag
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Requires Python 3.9+. The system `ping` binary should already be
present on Linux, macOS, and Windows — no extra setup needed.

## 2. Run the web dashboard

```bash
python run_dashboard.py
```

This starts a local Flask server and opens the dashboard at
`http://127.0.0.1:5050` in your browser. From there you can:

- Type a host or URL into **Target** and run Ping / DNS / HTTP / Port
  Scan individually, or hit **Run Full Diagnostic** to run all four.
- Watch live CPU, memory and disk gauges plus network throughput —
  refreshed every 2 seconds.
- See a lit port map after a scan and the top CPU-consuming processes
  on the machine running the dashboard.

Useful flags:

```bash
python run_dashboard.py --port 8080          # different port
python run_dashboard.py --host 0.0.0.0        # expose on your LAN
python run_dashboard.py --no-browser          # don't auto-open a tab
```

## 3. Use the CLI

```bash
python run_cli.py ping example.com
python run_cli.py dns example.com
python run_cli.py http https://example.com
python run_cli.py port example.com --ports common
python run_cli.py port example.com --ports 1-1024
python run_cli.py monitor                     # live CPU/RAM/disk/network view
python run_cli.py all example.com             # run everything at once
```

## 4. Use it as a library

```python
from netdiag import pinger, dns_check, http_check, port_scan, sysmon

result = pinger.ping_host("example.com", count=4)
print(result.avg_ms, result.loss_pct)

snap = sysmon.SystemMonitor().snapshot()
print(snap.cpu_percent, snap.mem_percent)
```

Every check function returns a plain dataclass with a `.to_dict()`
method, so results are easy to log, pipe into another tool, or feed
into your own alerting logic.

## Project structure

```
netdiag/
├── netdiag/                 # core library
│   ├── pinger.py            # ICMP / TCP ping
│   ├── dns_check.py         # DNS resolution & records
│   ├── http_check.py        # HTTP/HTTPS + TLS checks
│   ├── port_scan.py         # threaded TCP port scanner
│   ├── sysmon.py            # CPU/RAM/disk/network monitor
│   ├── cli.py                # rich-based CLI
│   └── webapp.py            # Flask backend for the dashboard
├── static/                  # dashboard front-end (HTML/CSS/JS)
├── run_dashboard.py         # launch the web dashboard
├── run_cli.py                # launch the CLI
└── requirements.txt
```

## Notes

- Port scanning only performs TCP-connect tests against hosts you
  specify — always make sure you're authorized to scan a target
  before running it.
- ICMP ping shells out to your OS's `ping` binary rather than using
  raw sockets, so it works without root/admin privileges.
- The dashboard's system gauges reflect the machine **running the
  dashboard**, not the remote host you're diagnosing.
