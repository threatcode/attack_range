"""Fixtures for end-to-end tests that deploy real cloud infrastructure."""

import os
import socket
import time

import pytest


def wait_for_port(host: str, port: int, timeout: int = 300, interval: int = 5) -> bool:
    """Return True when host:port accepts TCP connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            if sock.connect_ex((host, port)) == 0:
                return True
        finally:
            sock.close()
        time.sleep(interval)
    return False


@pytest.fixture
def wait_for_port_fn():
    return wait_for_port


def pytest_collection_modifyitems(config, items):
    if os.environ.get("ATTACK_RANGE_E2E") == "1":
        return
    skip_e2e = pytest.mark.skip(reason="E2E tests only run when ATTACK_RANGE_E2E=1")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)
