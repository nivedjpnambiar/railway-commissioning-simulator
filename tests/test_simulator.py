import pytest

from railway_commissioning.diagnostics import diagnose
from railway_commissioning.models import DoorCommand, DoorState, FaultMode
from railway_commissioning.simulator import DoorSystemSimulator


def test_healthy_open_and_close_cycle() -> None:
    simulator = DoorSystemSimulator()
    simulator.issue_command(DoorCommand.OPEN)
    simulator.run_for(3.5)
    assert simulator.latest().state is DoorState.OPEN
    assert simulator.latest().open_sensor
    assert simulator.latest().position_pct == pytest.approx(100.0)

    simulator.issue_command(DoorCommand.CLOSE)
    simulator.run_for(3.5)
    assert simulator.latest().state is DoorState.CLOSED
    assert simulator.latest().closed_sensor
    assert simulator.latest().position_pct == pytest.approx(0.0)


def test_overcurrent_triggers_fault_and_diagnostic_code() -> None:
    simulator = DoorSystemSimulator()
    simulator.inject_fault(FaultMode.MOTOR_OVERCURRENT)
    simulator.issue_command(DoorCommand.OPEN)
    simulator.step()
    assert simulator.latest().state is DoorState.FAULT
    assert simulator.latest().motor_current_a == 0.0
    assert "D107" in {event.code for event in diagnose(simulator.latest())}


def test_communication_loss_blocks_bus_messages() -> None:
    simulator = DoorSystemSimulator()
    simulator.inject_fault(FaultMode.COMMUNICATION_LOSS)
    before = len(simulator.bus.messages())
    simulator.issue_command(DoorCommand.OPEN)
    simulator.step()
    assert len(simulator.bus.messages()) == before
    assert simulator.latest().communication_ok is False
    assert simulator.latest().state is DoorState.FAULT


def test_contradictory_sensors_are_detected() -> None:
    simulator = DoorSystemSimulator()
    simulator.inject_fault(FaultMode.CONTRADICTORY_SENSORS)
    simulator.step()
    telemetry = simulator.latest()
    assert telemetry.open_sensor and telemetry.closed_sensor
    assert telemetry.state is DoorState.FAULT
    assert "D104" in {event.code for event in diagnose(telemetry)}


def test_invalid_step_rejected() -> None:
    simulator = DoorSystemSimulator()
    with pytest.raises(ValueError):
        simulator.step(0)
