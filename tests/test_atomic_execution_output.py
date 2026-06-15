"""Tests for structured atomic simulation output parsing."""

from attack_range.managers.ansible_manager import _extract_atomic_simulation_output


def test_extract_atomic_simulation_output_from_summary_task():
    events = [
        {
            "event": "runner_on_ok",
            "event_data": {
                "host": "10.0.2.11",
                "task": "Atomic Red Team execution summary",
                "res": {
                    "msg": {
                        "results": [
                            {
                                "technique": "T1190",
                                "guid": "abc",
                                "success": True,
                                "return_code": 0,
                                "failed": False,
                                "stdout_lines": ["done"],
                                "stderr_lines": [],
                            },
                            {
                                "technique": "T1105",
                                "guid": "def",
                                "success": False,
                                "return_code": 1,
                                "failed": True,
                                "stdout_lines": [],
                                "stderr_lines": ["error"],
                                "error": "boom",
                            },
                        ],
                        "summary": {"total": 2, "succeeded": 1, "failed": 1},
                    }
                },
            },
        }
    ]

    output = _extract_atomic_simulation_output(events)

    assert output["status"] == "failed"
    assert output["summary"] == {"total": 2, "succeeded": 1, "failed": 1}
    assert len(output["results"]) == 2
    assert output["results"][0]["technique"] == "T1190"
    assert output["results"][0]["success"] is True
    assert output["results"][1]["success"] is False
    assert output["by_host"]["10.0.2.11"]["status"] == "failed"


def test_extract_atomic_simulation_output_from_run_tasks():
    events = [
        {
            "event": "runner_on_ok",
            "event_data": {
                "host": "10.0.2.11",
                "task": "Run specified Atomic Red Team Technique",
                "task_vars": {"item": {"technique": "T1003.001", "guid": "g1"}},
                "res": {
                    "rc": 0,
                    "failed": False,
                    "stdout": "ok",
                    "stdout_lines": ["ok"],
                    "stderr_lines": [],
                },
            },
        }
    ]

    output = _extract_atomic_simulation_output(events)

    assert output["summary"]["total"] == 1
    assert output["summary"]["succeeded"] == 1
    assert output["results"][0]["technique"] == "T1003.001"
    assert output["results"][0]["guid"] == "g1"
    assert output["results"][0]["success"] is True
