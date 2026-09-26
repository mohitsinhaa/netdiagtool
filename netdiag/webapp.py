"""
webapp.py — Flask backend for the premium web dashboard.

Serves the static dashboard UI and exposes a small REST API that the
frontend polls / calls for live diagnostics.
"""

import os

from flask import Flask, jsonify, request, send_from_directory

from . import dns_check, http_check, pinger, port_scan, sysmon

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
_monitor = sysmon.SystemMonitor()


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/system")
def api_system():
    snap = _monitor.snapshot()
    return jsonify(snap.to_dict())


@app.route("/api/ping", methods=["POST"])
def api_ping():
    data = request.get_json(force=True) or {}
    host = (data.get("host") or "").strip()
    if not host:
        return jsonify({"error": "host is required"}), 400
    count = int(data.get("count", 4))
    timeout = int(data.get("timeout", 2))
    result = pinger.ping_host(host, count=count, timeout=timeout)
    return jsonify(result.to_dict())


@app.route("/api/dns", methods=["POST"])
def api_dns():
    data = request.get_json(force=True) or {}
    host = (data.get("host") or "").strip()
    if not host:
        return jsonify({"error": "host is required"}), 400
    result = dns_check.resolve_host(host)
    return jsonify(result.to_dict())


@app.route("/api/http", methods=["POST"])
def api_http():
    data = request.get_json(force=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "url is required"}), 400
    timeout = int(data.get("timeout", 8))
    result = http_check.check_url(url, timeout=timeout)
    return jsonify(result.to_dict())


@app.route("/api/portscan", methods=["POST"])
def api_portscan():
    data = request.get_json(force=True) or {}
    host = (data.get("host") or "").strip()
    if not host:
        return jsonify({"error": "host is required"}), 400
    ports_spec = data.get("ports", "common")
    timeout = float(data.get("timeout", 1.0))
    ports = port_scan.parse_port_spec(ports_spec)
    result = port_scan.scan_ports(host, ports, timeout=timeout)
    return jsonify(result.to_dict())


def run(host=None, port=None, debug=False):
    host = host or os.environ.get("HOST", "127.0.0.1")
    port = port or int(os.environ.get("PORT", 5050))
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run(debug=True)
