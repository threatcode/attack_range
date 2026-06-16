import json
import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from attack_range.managers.ansible_manager import AnsibleManager


@pytest.fixture
def ansible_manager(tmp_path):
    ansible_dir = tmp_path / "ansible"
    ansible_dir.mkdir()
    (ansible_dir / "roles").mkdir()
    return AnsibleManager(
        ansible_dir=str(ansible_dir),
        inventory_path=str(ansible_dir / "inventory.yaml"),
        config={},
        cloud_provider="aws",
        logger=logging.getLogger("test"),
    )


class TestGetLocalRoleOverrides:
    def test_empty_when_unset(self, ansible_manager, monkeypatch):
        monkeypatch.delenv("ATTACK_RANGE_LOCAL_ROLES", raising=False)
        assert ansible_manager._get_local_role_overrides() == {}

    def test_parses_valid_json(self, ansible_manager, monkeypatch):
        monkeypatch.setenv(
            "ATTACK_RANGE_LOCAL_ROLES",
            json.dumps({"P4T12ICK.ludus_ar_splunk": "/local_roles/ludus_ar_splunk"}),
        )
        assert ansible_manager._get_local_role_overrides() == {
            "P4T12ICK.ludus_ar_splunk": "/local_roles/ludus_ar_splunk",
        }

    def test_expands_tilde(self, ansible_manager, monkeypatch):
        monkeypatch.setenv(
            "ATTACK_RANGE_LOCAL_ROLES",
            json.dumps({"ns.role": "~/my-role"}),
        )
        assert ansible_manager._get_local_role_overrides() == {
            "ns.role": os.path.expanduser("~/my-role"),
        }

    def test_ignores_invalid_json(self, ansible_manager, monkeypatch):
        monkeypatch.setenv("ATTACK_RANGE_LOCAL_ROLES", "not-json")
        assert ansible_manager._get_local_role_overrides() == {}

    def test_ignores_non_object_json(self, ansible_manager, monkeypatch):
        monkeypatch.setenv("ATTACK_RANGE_LOCAL_ROLES", '["a"]')
        assert ansible_manager._get_local_role_overrides() == {}


class TestResolveRoleDir:
    def test_finds_role_with_dots(self, ansible_manager):
        role_path = os.path.join(ansible_manager._roles_install_path(), "ns.role")
        os.makedirs(role_path)
        assert ansible_manager._resolve_role_dir("ns.role") == role_path

    def test_finds_role_with_underscores(self, ansible_manager):
        role_path = os.path.join(ansible_manager._roles_install_path(), "ns_role")
        os.makedirs(role_path)
        assert ansible_manager._resolve_role_dir("ns.role") == role_path

    def test_returns_none_when_missing(self, ansible_manager):
        assert ansible_manager._resolve_role_dir("missing.role") is None


class TestInstallAnsibleGalaxyRole:
    @patch("attack_range.managers.ansible_manager.subprocess.run")
    def test_galaxy_install_uses_roles_path(self, mock_run, ansible_manager, monkeypatch):
        monkeypatch.delenv("ATTACK_RANGE_LOCAL_ROLES", raising=False)
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        assert ansible_manager.install_ansible_galaxy_role("geerlingguy.nginx") is True

        cmd = mock_run.call_args[0][0]
        roles_path = ansible_manager._roles_install_path()
        assert cmd == [
            "ansible-galaxy",
            "install",
            "geerlingguy.nginx",
            "-p",
            roles_path,
            "--force",
        ]

    @patch("attack_range.managers.ansible_manager.subprocess.run")
    def test_local_override_installs_from_path(self, mock_run, ansible_manager, monkeypatch, tmp_path):
        local_role = tmp_path / "my_role"
        local_role.mkdir()
        monkeypatch.setenv(
            "ATTACK_RANGE_LOCAL_ROLES",
            json.dumps({"P4T12ICK.ludus_ar_splunk": str(local_role)}),
        )
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        assert ansible_manager.install_ansible_galaxy_role("P4T12ICK.ludus_ar_splunk") is True

        cmd = mock_run.call_args[0][0]
        roles_path = ansible_manager._roles_install_path()
        assert cmd[0:2] == ["ansible-galaxy", "install"]
        assert cmd[2] == f"{local_role},P4T12ICK.ludus_ar_splunk"
        assert cmd[3:5] == ["-p", roles_path]
        assert "--force" in cmd

    def test_local_override_missing_path_returns_false(self, ansible_manager, monkeypatch):
        monkeypatch.setenv(
            "ATTACK_RANGE_LOCAL_ROLES",
            json.dumps({"ns.role": "/does/not/exist"}),
        )
        assert ansible_manager.install_ansible_galaxy_role("ns.role") is False
