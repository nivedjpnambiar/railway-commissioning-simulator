from __future__ import annotations

from .detection import detect_faults
from .diagnostics import diagnose
from .models import DoorCommand, DoorState, FaultMode, TestResult
from .simulator import DoorSystemSimulator


def _healthy_open_cycle() -> DoorSystemSimulator:
    simulator = DoorSystemSimulator()
    simulator.issue_command(DoorCommand.OPEN)
    simulator.run_for(3.5)
    return simulator


def _healthy_close_cycle() -> DoorSystemSimulator:
    simulator = _healthy_open_cycle()
    simulator.issue_command(DoorCommand.CLOSE)
    simulator.run_for(3.5)
    return simulator


def run_commissioning_suite() -> list[TestResult]:
    """Run reproducible, requirement-oriented virtual acceptance tests."""
    results: list[TestResult] = []

    startup = DoorSystemSimulator()
    t = startup.latest()
    results.append(
        TestResult(
            "TC-001",
            "The subsystem shall initialize in a safe closed state.",
            "State CLOSED and closed sensor active",
            f"State {t.state.value}; closed sensor={t.closed_sensor}",
            t.state is DoorState.CLOSED and t.closed_sensor and not t.open_sensor,
        )
    )

    opened = _healthy_open_cycle()
    t = opened.latest()
    results.append(
        TestResult(
            "TC-002",
            "The door shall reach the open end position within 5 s.",
            "OPEN within 5 s",
            f"State {t.state.value} after {opened.time_s:.1f} s",
            t.state is DoorState.OPEN and t.open_sensor and opened.time_s <= 5.0,
        )
    )

    closed = _healthy_close_cycle()
    t = closed.latest()
    results.append(
        TestResult(
            "TC-003",
            "The door shall return to the closed end position.",
            "CLOSED and closed sensor active",
            f"State {t.state.value}; position={t.position_pct:.1f}%",
            t.state is DoorState.CLOSED and t.closed_sensor,
        )
    )

    current_peak = max(item.motor_current_a for item in closed.history)
    results.append(
        TestResult(
            "TC-004",
            "Actuator current shall remain below 1.50 A in normal operation.",
            "Peak < 1.50 A",
            f"Peak {current_peak:.2f} A",
            current_peak < 1.50,
        )
    )

    comm = DoorSystemSimulator()
    comm.inject_fault(FaultMode.COMMUNICATION_LOSS)
    comm.issue_command(DoorCommand.OPEN)
    comm.step()
    t = comm.latest()
    results.append(
        TestResult(
            "TC-005",
            "A communication loss shall be detected and trigger a safe fault state.",
            "communication_ok=False and state FAULT",
            f"communication_ok={t.communication_ok}; state={t.state.value}",
            not t.communication_ok and t.state is DoorState.FAULT,
        )
    )

    overcurrent = DoorSystemSimulator()
    overcurrent.inject_fault(FaultMode.MOTOR_OVERCURRENT)
    overcurrent.issue_command(DoorCommand.OPEN)
    overcurrent.step()
    t = overcurrent.latest()
    codes = {event.code for event in diagnose(t)}
    results.append(
        TestResult(
            "TC-006",
            "Motor overcurrent shall be diagnosed and motion shall stop.",
            "D107 present and state FAULT",
            f"Codes {sorted(codes)}; state={t.state.value}",
            "D107" in codes and t.state is DoorState.FAULT and t.motor_current_a == 0.0,
        )
    )

    sensors = DoorSystemSimulator()
    sensors.inject_fault(FaultMode.CONTRADICTORY_SENSORS)
    sensors.step()
    t = sensors.latest()
    codes = {event.code for event in diagnose(t)}
    results.append(
        TestResult(
            "TC-007",
            "Contradictory position signals shall be rejected as implausible.",
            "Both sensors active, D104 present, state FAULT",
            f"open={t.open_sensor}; closed={t.closed_sensor}; codes={sorted(codes)}",
            t.open_sensor and t.closed_sensor and "D104" in codes and t.state is DoorState.FAULT,
        )
    )

    undervoltage = DoorSystemSimulator()
    undervoltage.inject_fault(FaultMode.UNDERVOLTAGE)
    undervoltage.issue_command(DoorCommand.OPEN)
    undervoltage.step()
    t = undervoltage.latest()
    results.append(
        TestResult(
            "TC-008",
            "Operation shall be inhibited below 19 V.",
            "Voltage < 19 V and state FAULT",
            f"Voltage {t.supply_voltage_v:.1f} V; state={t.state.value}",
            t.supply_voltage_v < 19.0 and t.state is DoorState.FAULT,
        )
    )

    blocked = DoorSystemSimulator()
    blocked.inject_fault(FaultMode.BLOCKED_DOOR)
    blocked.issue_command(DoorCommand.OPEN)
    blocked.run_for(2.0)
    t = blocked.latest()
    stall = next((trip for trip in blocked.protection_log if trip.reason == "motor_stall"), None)
    results.append(
        TestResult(
            "TC-009",
            "A blocked door shall be de-energised within 1.5 s (stall protection).",
            "motor_stall trip <= 1.5 s, state FAULT, current 0 A",
            f"trip at {stall.timestamp_s if stall else '-'} s; state={t.state.value}; current={t.motor_current_a:.2f} A",
            stall is not None and stall.timestamp_s <= 1.5 and t.state is DoorState.FAULT and t.motor_current_a == 0.0,
        )
    )

    no_closed = DoorSystemSimulator()
    no_closed.inject_fault(FaultMode.CLOSED_SENSOR_FAILED)
    no_closed.issue_command(DoorCommand.OPEN)
    no_closed.run_for(3.5)
    no_closed.issue_command(DoorCommand.CLOSE)
    no_closed.run_for(3.5)
    t = no_closed.latest()
    results.append(
        TestResult(
            "TC-010",
            "Departure shall not be permitted without a confirmed closed end position.",
            "door_closed_and_locked=False while closed sensor failed",
            f"state={t.state.value}; closed sensor={t.closed_sensor}; closed_and_locked={t.closed_and_locked}",
            t.state is DoorState.CLOSED and not t.closed_and_locked,
        )
    )

    healthy = _healthy_close_cycle()
    findings = detect_faults(healthy.history, healthy.protection_log, healthy.config)
    results.append(
        TestResult(
            "TC-011",
            "A healthy open/close cycle shall produce no diagnostic findings and permit departure.",
            "no findings, door_closed_and_locked=True",
            f"findings={[d.code for d in findings] or 'none'}; closed_and_locked={healthy.latest().closed_and_locked}",
            not findings and healthy.latest().closed_and_locked,
        )
    )

    return results
