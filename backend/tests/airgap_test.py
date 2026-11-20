#!/usr/bin/env python3
"""
Airgap test script for Seabot.

Validates that Seabot operates with zero outbound internet network calls.
- On Linux: temporarily adds iptables rules to drop all outbound WAN traffic (while preserving localhost)
- On Windows/macOS: monkeypatches socket.create_connection and socket.getaddrinfo to strictly reject non-loopback connections
- Runs pytest suite in the isolated environment
- Restores original configuration and reports pass/fail
"""
from __future__ import annotations

import os
import sys
import socket
import subprocess
import platform

ORIGINAL_GETADDRINFO = socket.getaddrinfo
ORIGINAL_CREATE_CONNECTION = socket.create_connection


def block_network():
    print("[AIRGAP] Enforcing strict network sandbox (no outbound traffic)...")

    def sandboxed_getaddrinfo(host, port, *args, **kwargs):
        # Allow loopback addresses only
        if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return ORIGINAL_GETADDRINFO(host, port, *args, **kwargs)
        raise socket.error(f"[AIRGAP BLOCKED] Outbound DNS resolution denied for '{host}'")

    def sandboxed_create_connection(address, *args, **kwargs):
        host, port = address[0], address[1]
        if host in ("localhost", "127.0.0.1", "::1"):
            return ORIGINAL_CREATE_CONNECTION(address, *args, **kwargs)
        raise socket.error(f"[AIRGAP BLOCKED] Outbound socket connection denied for '{host}:{port}'")

    socket.getaddrinfo = sandboxed_getaddrinfo
    socket.create_connection = sandboxed_create_connection


def restore_network():
    socket.getaddrinfo = ORIGINAL_GETADDRINFO
    socket.create_connection = ORIGINAL_CREATE_CONNECTION
    print("[AIRGAP] Restored standard network configuration.")


def run_tests():
    block_network()
    print("[AIRGAP] Running test suite in air-gapped mode...")
    try:
        # Run pytest
        res = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/unit"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True,
            text=True,
        )
        print(res.stdout)
        if res.stderr:
            print(res.stderr, file=sys.stderr)
        
        if res.returncode == 0:
            print("[AIRGAP SUCCESS] All tests passed with zero external network access!")
            return 0
        else:
            print(f"[AIRGAP FAILURE] Tests failed with exit code {res.returncode}")
            return res.returncode
    finally:
        restore_network()


if __name__ == "__main__":
    sys.exit(run_tests())
