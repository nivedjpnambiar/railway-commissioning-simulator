from __future__ import annotations

from dataclasses import dataclass

from .bus import VirtualCanBus
from .models import DoorCommand, DoorState, FaultMode, Telemetry


@dataclass(frozen=True)
class SimulatorConfig:
    nominal_voltage_v: float = 24.0
    undervoltage_threshold_v: float = 19.0
    normal_motor_current_a: float = 0.65
    overcurrent_limit_a: float = 1.50
    travel_time_s: float = 3.0
    sensor_tolerance_pct: float = 1.0
    movement_timeout_s: float = 5.0


class DoorSystemSimulator:
    """Deterministic low-voltage model of a railway passenger-door subsystem."""

    def __init__(self, config: SimulatorConfig | None = None) -> None:
        self.config = config or SimulatorConfig()
        self.bus = VirtualCanBus()
        self.reset(full=True)

    def reset(self, *, full: bool = False) -> None:
        self.time_s = 0.0
        self.state = DoorState.CLOSED
        self.command = DoorCommand.NONE
        self.position_pct = 0.0
        self.supply_voltage_v = self.config.nominal_voltage_v
        self.motor_current_a = 0.0
        self.motion_elapsed_s = 0.0
        if full or not hasattr(self, "faults"):
            self.faults: set[FaultMode] = set()
        self.history: list[Telemetry] = []
        self.bus.clear()
        self.bus.online = FaultMode.COMMUNICATION_LOSS not in self.faults
        self._record_telemetry()

    def inject_fault(self, fault: FaultMode) -> None:
        self.faults.add(fault)
        self.bus.online = FaultMode.COMMUNICATION_LOSS not in self.faults
        if fault is FaultMode.UNDERVOLTAGE:
            self.supply_voltage_v = 17.5

    def clear_fault(self, fault: FaultMode) -> None:
        self.faults.discard(fault)
        self.bus.online = FaultMode.COMMUNICATION_LOSS not in self.faults
        if fault is FaultMode.UNDERVOLTAGE:
            self.supply_voltage_v = self.config.nominal_voltage_v

    def clear_all_faults(self) -> None:
        self.faults.clear()
        self.bus.online = True
        self.supply_voltage_v = self.config.nominal_voltage_v

    def issue_command(self, command: DoorCommand) -> None:
        self.command = command
        self.bus.send(
            timestamp_s=self.time_s,
            message_id=0x101,
            signal="door_command",
            value=command.value,
            source="vehicle_control_unit",
        )

        if command is DoorCommand.RESET:
            self.state = self._state_from_position()
            self.motion_elapsed_s = 0.0
            self.motor_current_a = 0.0
            self.command = DoorCommand.NONE
            return
        if command is DoorCommand.STOP:
            self.state = DoorState.STOPPED
            self.motor_current_a = 0.0
            return
        if command is DoorCommand.OPEN and self.state not in {DoorState.OPEN, DoorState.FAULT}:
            self.state = DoorState.OPENING
            self.motion_elapsed_s = 0.0
        elif command is DoorCommand.CLOSE and self.state not in {DoorState.CLOSED, DoorState.FAULT}:
            self.state = DoorState.CLOSING
            self.motion_elapsed_s = 0.0

    def step(self, dt_s: float = 0.1) -> Telemetry:
        if dt_s <= 0:
            raise ValueError("dt_s must be positive")

        self.time_s = round(self.time_s + dt_s, 10)
        self._update_power()
        self._update_motion(dt_s)
        self._apply_protection_logic()
        telemetry = self._record_telemetry()
        self._publish_status(telemetry)
        return telemetry

    def run_for(self, duration_s: float, dt_s: float = 0.1) -> list[Telemetry]:
        if duration_s < 0:
            raise ValueError("duration_s must not be negative")
        steps = int(round(duration_s / dt_s))
        return [self.step(dt_s) for _ in range(steps)]

    def latest(self) -> Telemetry:
        return self.history[-1]

    def _update_power(self) -> None:
        if FaultMode.UNDERVOLTAGE in self.faults:
            self.supply_voltage_v = 17.5
        else:
            self.supply_voltage_v = self.config.nominal_voltage_v

    def _update_motion(self, dt_s: float) -> None:
        moving = self.state in {DoorState.OPENING, DoorState.CLOSING}
        if not moving:
            self.motor_current_a = 0.0
            return

        self.motion_elapsed_s += dt_s
        self.motor_current_a = self.config.normal_motor_current_a

        if FaultMode.BLOCKED_DOOR in self.faults:
            self.motor_current_a = 1.25
            return
        if FaultMode.MOTOR_OVERCURRENT in self.faults:
            self.motor_current_a = 2.10
            return
        if FaultMode.UNDERVOLTAGE in self.faults:
            self.motor_current_a = 0.95
            return

        delta = 100.0 * dt_s / self.config.travel_time_s
        if self.state is DoorState.OPENING:
            self.position_pct = min(100.0, self.position_pct + delta)
            if self.position_pct >= 100.0:
                self.position_pct = 100.0
                self.state = DoorState.OPEN
                self.motor_current_a = 0.0
                self.motion_elapsed_s = 0.0
        elif self.state is DoorState.CLOSING:
            self.position_pct = max(0.0, self.position_pct - delta)
            if self.position_pct <= 0.0:
                self.position_pct = 0.0
                self.state = DoorState.CLOSED
                self.motor_current_a = 0.0
                self.motion_elapsed_s = 0.0

    def _apply_protection_logic(self) -> None:
        critical = {
            FaultMode.CONTRADICTORY_SENSORS,
            FaultMode.COMMUNICATION_LOSS,
            FaultMode.UNDERVOLTAGE,
            FaultMode.MOTOR_OVERCURRENT,
        }
        if self.faults.intersection(critical):
            self.state = DoorState.FAULT
            self.motor_current_a = 0.0
            return

        if self.motion_elapsed_s > self.config.movement_timeout_s:
            self.state = DoorState.FAULT
            self.motor_current_a = 0.0

    def _sensors(self) -> tuple[bool, bool]:
        tol = self.config.sensor_tolerance_pct
        open_sensor = self.position_pct >= 100.0 - tol
        closed_sensor = self.position_pct <= tol

        if FaultMode.OPEN_SENSOR_FAILED in self.faults:
            open_sensor = False
        if FaultMode.CLOSED_SENSOR_FAILED in self.faults:
            closed_sensor = False
        if FaultMode.CONTRADICTORY_SENSORS in self.faults:
            open_sensor = True
            closed_sensor = True
        return open_sensor, closed_sensor

    def _state_from_position(self) -> DoorState:
        if self.position_pct <= self.config.sensor_tolerance_pct:
            return DoorState.CLOSED
        if self.position_pct >= 100.0 - self.config.sensor_tolerance_pct:
            return DoorState.OPEN
        return DoorState.STOPPED

    def _record_telemetry(self) -> Telemetry:
        open_sensor, closed_sensor = self._sensors()
        telemetry = Telemetry(
            timestamp_s=self.time_s,
            state=self.state,
            command=self.command,
            position_pct=round(self.position_pct, 2),
            motor_current_a=round(self.motor_current_a, 3),
            supply_voltage_v=round(self.supply_voltage_v, 2),
            open_sensor=open_sensor,
            closed_sensor=closed_sensor,
            communication_ok=self.bus.online,
            active_faults=tuple(sorted(self.faults, key=lambda fault: fault.value)),
        )
        self.history.append(telemetry)
        return telemetry

    def _publish_status(self, telemetry: Telemetry) -> None:
        payloads = (
            (0x201, "door_state", telemetry.state.value),
            (0x202, "position_pct", telemetry.position_pct),
            (0x203, "motor_current_a", telemetry.motor_current_a),
            (0x204, "supply_voltage_v", telemetry.supply_voltage_v),
        )
        for message_id, signal, value in payloads:
            self.bus.send(
                timestamp_s=self.time_s,
                message_id=message_id,
                signal=signal,
                value=value,
                source="door_control_unit",
            )
