#!/usr/bin/env python3
"""
Launch the NETDIAG web dashboard.

    python run_dashboard.py
    python run_dashboard.py --port 8080 --host 0.0.0.0
"""
import argparse
import webbrowser
import threading

from netdiag.webapp import run


def main():
    parser = argparse.ArgumentParser(description="Run the NETDIAG dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--no-browser", action="store_true",
                         help="Don't auto-open the dashboard in a browser")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    print(f"\n  NETDIAG dashboard starting at {url}\n")

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
