#!/usr/bin/env python3
"""Entry point for the NETDIAG command-line interface.

    python run_cli.py ping example.com
    python run_cli.py monitor
"""
from netdiag.cli import main

if __name__ == "__main__":
    main()
