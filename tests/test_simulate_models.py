"""Tests for simulate API request/response models."""

import pytest
from pydantic import ValidationError

from api.models import AtomicFileTarget, AtomicTestTarget, SimulateRequest


def test_simulate_request_accepts_techniques_only():
    req = SimulateRequest(
        attack_range_id="id",
        target="ar-win-1",
        techniques=["T1003.001"],
    )
    assert req.techniques == ["T1003.001"]
    assert req.atomics == []


def test_simulate_request_accepts_atomics_only():
    req = SimulateRequest(
        attack_range_id="id",
        target="ar-win-1",
        atomics=[
            AtomicTestTarget(
                technique="T1003.001",
                guid="0be2230c-9ab3-4ac2-8826-3199b9a0ebf8",
            )
        ],
    )
    assert len(req.atomics) == 1
    assert req.atomics[0].technique == "T1003.001"


def test_simulate_request_accepts_atomic_files_only():
    req = SimulateRequest(
        attack_range_id="id",
        target="ar-win-1",
        atomic_files=[
            AtomicFileTarget(path="/tmp/custom.yaml"),
            AtomicFileTarget(content="attack_technique: T9999\natomic_tests: []"),
        ],
    )
    assert len(req.atomic_files) == 2
    assert req.atomic_files[0].path == "/tmp/custom.yaml"


def test_atomic_file_target_requires_path_or_content():
    with pytest.raises(ValidationError):
        AtomicFileTarget()


def test_simulate_request_requires_simulation_target():
    with pytest.raises(ValidationError):
        SimulateRequest(attack_range_id="id", target="ar-win-1")
