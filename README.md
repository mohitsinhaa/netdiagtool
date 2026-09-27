# NETDIAG — Network Diagnostic & Server Monitoring Toolkit

A Python toolkit for everyday network and server diagnostics, with two
ways to use it:

## Features

- **Ping diagnostics**
- **DNS diagnostics** 
- **HTTP/HTTPS checks** 
- **Port connectivity testing**
- **System monitoring** 

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

