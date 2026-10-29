"""Protection functions react to measured values and configured limits."""

import pytest

from railway_commissioning.models import DoorCommand, DoorState, FaultMode
from railway_commissioning.simulator import DoorSystemSimulator, SimulatorConfig


def open_with(fault=None, config=None, duration=0.5):
    sim = DoorSystemSimulator(config)
    if fault:
        sim.inject_fault(fault)
    sim.issue_command(DoorCommand.OPEN)
    sim.run_for(duration)
    return sim


def test_overcurrent_limit_comes_from_config():
    # normal current is 0.65 A; with a 0.5 A limit a healthy door must trip
    sim = open_with(config=SimulatorConfig(overcurrent_limit_a=0.5))
    assert sim.latest().state is DoorState.FAULT
    assert sim.protection_log[0].reason == "motor_overcurrent"
    assert sim.protection_log[0].measured == pytest.approx(0.65)


def test_undervoltage_threshold_comes_from_config():
    # injected 17.5 V is accepted when the threshold is lowered to 17 V
    sim = open_with(FaultMode.UNDERVOLTAGE, SimulatorConfig(undervoltage_threshold_v=17.0))
    assert not any(t.reason == "undervoltage" for t in sim.protection_log)


@pytest.mark.parametrize(
    "fault, reason",
    [
        (FaultMode.MOTOR_OVERCURRENT, "motor_overcurrent"),
        (FaultMode.UNDERVOLTAGE, "undervoltage"),
        (FaultMode.CONTRADICTORY_SENSORS, "sensor_implausible"),
        (FaultMode.COMMUNICATION_LOSS, "communication_timeout"),
    ],
)
def test_critical_faults_trip_on_first_step(fault, reason):
    sim = open_with(fault, duration=0.1)
    assert sim.latest().state is DoorState.FAULT
    assert sim.latest().motor_current_a == 0.0
    assert sim.protection_log[0].reason == reason


def test_blocked_door_stall_protection():
    sim = open_with(FaultMode.BLOCKED_DOOR, duration=2.0)
    trip = sim.protection_log[0]
    assert trip.reason == "motor_stall"
    assert trip.timestamp_s == pytest.approx(1.0)
    assert sim.latest().motor_current_a == 0.0


def test_new_command_does_not_hide_a_blocked_door():
    # before stall protection, CLOSE restarted the movement timer and the
    # blocked motor stayed energised for the whole test profile
    sim = open_with(FaultMode.BLOCKED_DOOR, duration=0.8)
    sim.issue_command(DoorCommand.CLOSE)
    sim.run_for(0.8)
    sim.issue_command(DoorCommand.OPEN)
    sim.run_for(2.0)
    assert sim.latest().state is DoorState.FAULT


def test_movement_timeout_still_active():
    sim = open_with(config=SimulatorConfig(travel_time_s=10.0, movement_timeout_s=2.0), duration=3.0)
    assert sim.protection_log[0].reason == "movement_timeout"


def test_fault_is_latched_until_reset():
    sim = open_with(FaultMode.MOTOR_OVERCURRENT, duration=0.2)
    sim.clear_fault(FaultMode.MOTOR_OVERCURRENT)
    sim.issue_command(DoorCommand.OPEN)
    sim.run_for(1.0)
    assert sim.latest().state is DoorState.FAULT
    assert len(sim.protection_log) == 1
    sim.issue_command(DoorCommand.RESET)
    sim.issue_command(DoorCommand.OPEN)
    sim.run_for(3.5)
    assert sim.latest().state is DoorState.OPEN


def test_reset_with_fault_still_present_trips_again():
    sim = open_with(FaultMode.UNDERVOLTAGE, duration=0.2)
    sim.issue_command(DoorCommand.RESET)
    sim.step()
    assert sim.latest().state is DoorState.FAULT
    assert len(sim.protection_log) == 2


def test_stop_command_halts_movement():
    sim = open_with(duration=1.5)
    pos = sim.latest().position_pct
    sim.issue_command(DoorCommand.STOP)
    sim.run_for(1.0)
    assert sim.latest().state is DoorState.STOPPED
    assert sim.latest().position_pct == pytest.approx(pos)
    assert sim.latest().motor_current_a == 0.0


def test_open_command_ignored_in_fault_state():
    sim = open_with(FaultMode.COMMUNICATION_LOSS, duration=0.2)
    sim.issue_command(DoorCommand.OPEN)
    sim.run_for(1.0)
    assert sim.latest().state is DoorState.FAULT


def test_negative_duration_rejected():
    with pytest.raises(ValueError):
        DoorSystemSimulator().run_for(-1)


def test_stop_does_not_clear_latched_fault():
    sim = open_with(FaultMode.BLOCKED_DOOR, duration=1.5)
    sim.clear_fault(FaultMode.BLOCKED_DOOR)
    sim.issue_command(DoorCommand.STOP)
    sim.issue_command(DoorCommand.OPEN)
    sim.run_for(1.0)
    assert sim.latest().state is DoorState.FAULT
