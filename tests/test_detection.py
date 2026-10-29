"""Measurement-based detection finds the fault without knowing which was injected."""

import dataclasses

import pytest

from railway_commissioning.detection import detect_faults
from railway_commissioning.diagnostics import FAULT_CATALOG
from railway_commissioning.models import FaultMode
from railway_commissioning.scenarios import fault_matrix_markdown, run_fault_matrix, run_scenario


@pytest.fixture(scope="module")
def matrix():
    return run_fault_matrix()


def test_healthy_cycle_has_no_findings():
    r = run_scenario(None)
    assert r.detections == []
    assert r.history[-1].closed_and_locked


@pytest.mark.parametrize("fault", list(FaultMode), ids=lambda f: f.value)
def test_each_fault_detected_with_expected_code(fault):
    r = run_scenario(fault)
    assert r.detected_codes == [FAULT_CATALOG[fault][0]], r.detections


def test_detection_ignores_injected_fault_labels():
    # remove the injected-fault information from the telemetry: result must not change
    r = run_scenario(FaultMode.UNDERVOLTAGE)
    stripped = [dataclasses.replace(t, active_faults=()) for t in r.history]
    assert [d.code for d in detect_faults(stripped, r.trips)] == ["D106"]


def test_critical_faults_reach_safe_state_fast(matrix):
    critical = {"D101", "D104", "D105", "D106", "D107"}
    for r in matrix:
        if r.expected_code in critical:
            assert r.time_to_fault_s is not None and r.time_to_fault_s <= 1.0, r.name


def test_sensor_faults_inhibit_departure_or_are_diagnosed(matrix):
    by_name = {r.name: r for r in matrix}
    assert not by_name["closed_sensor_failed"].history[-1].closed_and_locked
    assert by_name["open_sensor_failed"].detection_time_s is not None


def test_unclassified_fault_code():
    r = run_scenario(FaultMode.MOTOR_OVERCURRENT)
    assert [d.code for d in detect_faults(r.history, [])] == ["D199"]


def test_matrix_markdown(matrix):
    md = fault_matrix_markdown(matrix)
    assert md.startswith(f"{len(matrix)}/{len(matrix)} scenarios passed")
    assert "motor_stall" in md
