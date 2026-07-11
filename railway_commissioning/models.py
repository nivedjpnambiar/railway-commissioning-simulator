from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class DoorState(str, Enum):
    CLOSED = "CLOSED"
    OPENING = "OPENING"
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    STOPPED = "STOPPED"
    FAULT = "FAULT"


class DoorCommand(str, Enum):
    NONE = "NONE"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    STOP = "STOP"
    RESET = "RESET"


class FaultMode(str, Enum):
    BLOCKED_DOOR = "blocked_door"
    OPEN_SENSOR_FAILED = "open_sensor_failed"
    CLOSED_SENSOR_FAILED = "closed_sensor_failed"
    CONTRADICTORY_SENSORS = "contradictory_sensors"
    COMMUNICATION_LOSS = "communication_loss"
    UNDERVOLTAGE = "undervoltage"
    MOTOR_OVERCURRENT = "motor_overcurrent"


@dataclass(frozen=True)
class BusMessage:
    timestamp_s: float
    message_id: int
    signal: str
    value: Any
    source: str


@dataclass(frozen=True)
class DiagnosticEvent:
    timestamp_s: float
    code: str
    severity: str
    title: str
    details: str
    recommendation: str


@dataclass(frozen=True)
class Telemetry:
    timestamp_s: float
    state: DoorState
    command: DoorCommand
    position_pct: float
    motor_current_a: float
    supply_voltage_v: float
    open_sensor: bool
    closed_sensor: bool
    communication_ok: bool
    active_faults: tuple[FaultMode, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        data["command"] = self.command.value
        data["active_faults"] = [fault.value for fault in self.active_faults]
        return data


@dataclass(frozen=True)
class TestResult:
    test_id: str
    requirement: str
    expected: str
    measured: str
    passed: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "Test ID": self.test_id,
            "Requirement": self.requirement,
            "Expected": self.expected,
            "Measured": self.measured,
            "Result": "PASS" if self.passed else "FAIL",
            "Notes": self.notes,
        }
