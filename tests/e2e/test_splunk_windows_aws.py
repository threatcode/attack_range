"""
End-to-end test: build, verify, and destroy aws/splunk_windows_e2e_aws.

Requires real AWS credentials and WireGuard (wg-quick). Intended for GitHub Actions
with secrets AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.

GitHub Actions: set ATTACK_RANGE_CI=1 (passwordless sudo).
Local runs: omit ATTACK_RANGE_CI to connect VPN manually when prompted.
"""

import logging
import os
from pathlib import Path

import pytest

from attack_range.attack_range_controller import AttackRangeController
from attack_range.utils import load_yaml_file, prepare_config_from_template

E2E_TEMPLATE = "aws/splunk_windows_e2e_aws"
SPLUNK_HOST = "10.0.2.10"
WINDOWS_HOST = "10.0.2.11"
logger = logging.getLogger("attack_range.e2e")


@pytest.mark.e2e
def test_splunk_windows_build_verify_destroy(wait_for_port_fn):
    """Deploy Splunk + Windows in eu-west-2, verify lab connectivity, then destroy."""
    project_root = Path(__file__).resolve().parents[2]
    templates_dir = project_root / "templates"
    config_dir = project_root / "config"

    config, config_path, attack_range_id = prepare_config_from_template(
        E2E_TEMPLATE,
        str(templates_dir),
        str(config_dir),
        generate_id=True,
    )

    controller = AttackRangeController(config, config_path=config_path)
    try:
        controller.build()

        saved = load_yaml_file(config_path)
        assert saved["general"]["status"] == "running", (
            f"Expected status 'running', got {saved['general'].get('status')!r}"
        )
        assert saved["aws"]["region"] == "eu-west-2"

        assert wait_for_port_fn(SPLUNK_HOST, 22, timeout=300), (
            f"Splunk host {SPLUNK_HOST}:22 not reachable over VPN"
        )
        assert wait_for_port_fn(WINDOWS_HOST, 3389, timeout=300), (
            f"Windows host {WINDOWS_HOST}:3389 not reachable over VPN"
        )
    finally:
        try:
            controller.ansible_manager.disconnect_wireguard_ci()
        except Exception:
            pass
        try:
            controller.destroy()
        except Exception as exc:
            logger.warning("Destroy failed (manual cleanup may be required): %s", exc)
