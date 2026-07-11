from __future__ import annotations

from .models import DiagnosticEvent, DoorState, FaultMode, Telemetry


FAULT_CATALOG: dict[FaultMode, tuple[str, str, str, str]] = {
    FaultMode.BLOCKED_DOOR: (
        "D101",
        "ERROR",
        "Door movement blocked",
        "The actuator is commanded to move, but the simulated door position does not change.",
    ),
    FaultMode.OPEN_SENSOR_FAILED: (
        "D102",
        "ERROR",
        "Open-position sensor unavailable",
        "The door reaches the open end position without a valid open-position signal.",
    ),
    FaultMode.CLOSED_SENSOR_FAILED: (
        "D103",
        "ERROR",
        "Closed-position sensor unavailable",
        "The door reaches the closed end position without a valid closed-position signal.",
    ),
    FaultMode.CONTRADICTORY_SENSORS: (
        "D104",
        "CRITICAL",
        "Position sensors implausible",
        "Open and closed position sensors are active at the same time.",
    ),
    FaultMode.COMMUNICATION_LOSS: (
        "D105",
        "CRITICAL",
        "Controller communication lost",
        "Status and command messages cannot be exchanged on the virtual bus.",
    ),
    FaultMode.UNDERVOLTAGE: (
        "D106",
        "ERROR",
        "Supply undervoltage",
        "The simulated supply voltage is below the permitted operating threshold.",
    ),
    FaultMode.MOTOR_OVERCURRENT: (
        "D107",
        "CRITICAL",
        "Motor overcurrent",
        "The simulated actuator current exceeds the configured safety limit.",
    ),
}

RECOMMENDATIONS: dict[FaultMode, str] = {
    FaultMode.BLOCKED_DOOR: "Inspect the door mechanism and verify that the actuator can move freely.",
    FaultMode.OPEN_SENSOR_FAILED: "Inspect the open-position sensor, wiring and signal plausibility.",
    FaultMode.CLOSED_SENSOR_FAILED: "Inspect the closed-position sensor, wiring and signal plausibility.",
    FaultMode.CONTRADICTORY_SENSORS: "Check both end-position circuits and compare the signals with the physical position.",
    FaultMode.COMMUNICATION_LOSS: "Check controller availability, bus configuration, wiring and timeout settings.",
    FaultMode.UNDERVOLTAGE: "Check the power supply, voltage drop and current demand before resetting the system.",
    FaultMode.MOTOR_OVERCURRENT: "Stop the actuator and inspect for mechanical blockage, wiring faults or motor damage.",
}


def diagnose(telemetry: Telemetry) -> list[DiagnosticEvent]:
    events: list[DiagnosticEvent] = []
    for fault in telemetry.active_faults:
        code, severity, title, details = FAULT_CATALOG[fault]
        events.append(
            DiagnosticEvent(
                timestamp_s=telemetry.timestamp_s,
                code=code,
                severity=severity,
                title=title,
                details=details,
                recommendation=RECOMMENDATIONS[fault],
            )
        )

    if telemetry.state is DoorState.FAULT and not events:
        events.append(
            DiagnosticEvent(
                timestamp_s=telemetry.timestamp_s,
                code="D199",
                severity="ERROR",
                title="Unclassified subsystem fault",
                details="The subsystem entered the fault state without a catalogued injected fault.",
                recommendation="Review the event log and compare measured values with the acceptance limits.",
            )
        )
    return events
