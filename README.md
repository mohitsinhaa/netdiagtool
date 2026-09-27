# NETDIAG — Network Diagnostic & Server Monitoring Toolkit

A Python toolkit for everyday network and server diagnostics, with two
ways to use it:

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

<img width="1366" height="768" alt="Screenshot (79)" src="https://github.com/user-attachments/assets/d0dbedbd-e922-4ece-b100-88c54be9587d" />

