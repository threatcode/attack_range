"""Tests for local Ansible role staging helpers."""

import base64
import io
import os
import tarfile
import tempfile

import pytest

from attack_range.managers.ansible_manager import (
    AnsibleManager,
    LOCAL_ROLE_MAX_TAR_BYTES,
    resolve_local_role_name,
)


def _make_minimal_role(tmp_path, role_dir_name="my_role", namespace="custom", role_name="my_role"):
    role_path = tmp_path / role_dir_name
    role_path.mkdir()
    (role_path / "tasks").mkdir()
    (role_path / "tasks" / "main.yml").write_text("- debug:\n    msg: hello\n")
    (role_path / "meta").mkdir()
    (role_path / "meta" / "main.yml").write_text(
        f"galaxy_info:\n  role_name: {role_name}\n  namespace: {namespace}\n"
    )
    return role_path


def _tar_role(role_path: str) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(role_path, arcname=os.path.basename(role_path))
    return buf.getvalue()


@pytest.fixture
def ansible_manager(tmp_path):
    ansible_dir = tmp_path / "ansible"
    ansible_dir.mkdir()
    inventory_path = ansible_dir / "inventory.yaml"
    inventory_path.write_text("all:\n  hosts: {}\n")
    logger = __import__("logging").getLogger("test")
    return AnsibleManager(
        str(ansible_dir),
        str(inventory_path),
        {"attack_range": [{"name": "splunk", "linux": True}]},
        "aws",
        logger,
    )


def test_resolve_local_role_name_from_meta(tmp_path):
    role_path = _make_minimal_role(tmp_path)
    assert resolve_local_role_name(str(role_path)) == "custom.my_role"


def test_resolve_local_role_name_override(tmp_path):
    role_path = _make_minimal_role(tmp_path)
    assert resolve_local_role_name(str(role_path), "override.role") == "override.role"


def test_stage_local_role_copies_to_roles_dir(ansible_manager, tmp_path):
    role_path = _make_minimal_role(tmp_path)
    resolved = ansible_manager.stage_local_role(str(role_path))
    assert resolved == "custom.my_role"
    staged = os.path.join(ansible_manager.ansible_dir, "roles", "custom.my_role", "tasks", "main.yml")
    assert os.path.isfile(staged)


def test_stage_local_role_rejects_invalid_directory(ansible_manager, tmp_path):
    invalid = tmp_path / "not_a_role"
    invalid.mkdir()
    with pytest.raises(ValueError, match="tasks/main.yml"):
        ansible_manager.stage_local_role(str(invalid))


def test_stage_local_role_from_tarball(ansible_manager, tmp_path):
    role_path = _make_minimal_role(tmp_path)
    tarball = _tar_role(str(role_path))
    encoded = base64.b64encode(tarball).decode("ascii")
    resolved = ansible_manager.stage_local_role_from_tarball(encoded)
    assert resolved == "custom.my_role"


def test_stage_local_role_from_tarball_rejects_traversal(ansible_manager):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name="../escape/tasks/main.yml")
        info.size = 0
        tar.addfile(info)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    with pytest.raises(ValueError, match="Unsafe path"):
        ansible_manager.stage_local_role_from_tarball(encoded)


def test_stage_local_role_from_tarball_rejects_oversized(ansible_manager):
    oversized = b"x" * (LOCAL_ROLE_MAX_TAR_BYTES + 1)
    encoded = base64.b64encode(oversized).decode("ascii")
    with pytest.raises(ValueError, match="maximum size"):
        ansible_manager.stage_local_role_from_tarball(encoded)


def test_update_apply_roles_playbook_linux_become(ansible_manager):
    ansible_manager.update_apply_roles_playbook(
        "splunk",
        [{"name": "custom.my_role", "vars": {"foo": "bar"}}],
        True,
    )
    playbook_path = os.path.join(ansible_manager.ansible_dir, "apply_local_roles.yaml")
    content = open(playbook_path, encoding="utf-8").read()
    assert "hosts: splunk" in content
    assert "become: true" in content
    assert "custom.my_role" in content
    assert "foo: bar" in content


def test_get_server_become_windows_default_none(ansible_manager):
    ansible_manager.config = {
        "attack_range": [{"name": "win", "windows": True}],
    }
    assert ansible_manager.get_server_become("win") is None


def test_get_server_become_linux_default_true(ansible_manager):
    assert ansible_manager.get_server_become("splunk") is True
