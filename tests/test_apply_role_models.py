"""Tests for apply-role API request/response models."""

import pytest
from pydantic import ValidationError

from api.models import ApplyRoleRequest, ApplyRoleResponse, LocalRoleTarget


def test_apply_role_request_accepts_single_role():
    req = ApplyRoleRequest(
        attack_range_id="id",
        target="splunk",
        roles=[LocalRoleTarget(content_base64="dGVzdA==")],
    )
    assert len(req.roles) == 1
    assert req.roles[0].content_base64 == "dGVzdA=="


def test_apply_role_request_accepts_role_vars():
    req = ApplyRoleRequest(
        attack_range_id="id",
        target="splunk",
        roles=[
            LocalRoleTarget(
                content_base64="dGVzdA==",
                name="custom.my_role",
                vars={"foo": "bar"},
            )
        ],
    )
    assert req.roles[0].name == "custom.my_role"
    assert req.roles[0].vars == {"foo": "bar"}


def test_apply_role_request_requires_at_least_one_role():
    with pytest.raises(ValidationError):
        ApplyRoleRequest(attack_range_id="id", target="splunk", roles=[])


def test_apply_role_response_shape():
    resp = ApplyRoleResponse(
        status="success",
        message="ok",
        attack_range_id="id",
        target="splunk",
        roles_applied=["custom.my_role"],
    )
    assert resp.roles_applied == ["custom.my_role"]
