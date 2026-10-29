"""Standard test scenario and fault matrix.

Every scenario runs the same command profile (open, wait, close, wait) so the
results are comparable. The fault matrix injects each fault mode once and
checks the reaction of the subsystem and of the measurement-based detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .detection import detect_faults
from .diagnostics import FAULT_CATALOG
from .models import Detection, DoorCommand, DoorState, FaultMode, ProtectionTrip, Telemetry
from .simulator import DoorSystemSimulator

OPEN_PHASE_S = 4.0
CLOSE_PHASE_S = 4.0


@dataclass
class ScenarioResult:
    name: str
    fault: FaultMode | None
    history: list[Telemetry] = field(repr=False)
    trips: list[ProtectionTrip]
    detections: list[Detection]

    @property
    def expected_code(self) -> str | None:
        return FAULT_CATALOG[self.fault][0] if self.fault else None

    @property
    def detected_codes(self) -> list[str]:
        return [d.code for d in self.detections]

    @property
    def final_state(self) -> DoorState:
        return self.history[-1].state

    @property
    def time_to_fault_s(self) -> float | None:
        for t in self.history:
            if t.state is DoorState.FAULT:
                return t.timestamp_s
        return None

    @property
    def detection_time_s(self) -> float | None:
        for d in self.detections:
            if d.code == self.expected_code:
                return d.first_seen_s
        return None

    @property
    def passed(self) -> bool:
        if self.fault is None:
            return not self.detections and self.final_state is DoorState.CLOSED
        return self.detected_codes == [self.expected_code]


def run_scenario(fault: FaultMode | None = None) -> ScenarioResult:
    sim = DoorSystemSimulator()
    if fault is not None:
        sim.inject_fault(fault)
    sim.issue_command(DoorCommand.OPEN)
    sim.run_for(OPEN_PHASE_S)
    sim.issue_command(DoorCommand.CLOSE)
    sim.run_for(CLOSE_PHASE_S)
    name = fault.value if fault else "healthy"
    return ScenarioResult(name, fault, list(sim.history), list(sim.protection_log), detect_faults(sim.history, sim.protection_log, sim.config))


def run_fault_matrix() -> list[ScenarioResult]:
    return [run_scenario(None)] + [run_scenario(f) for f in FaultMode]


def fault_matrix_markdown(results: list[ScenarioResult]) -> str:
    ok = sum(r.passed for r in results)
    lines = [
        "| Scenario | Expected code | Detected (from measurements) | Detected at | Safe state (FAULT) at | Protection trip | Final state | Closed & locked at end | Result |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        trip = r.trips[0] if r.trips else None
        trip_txt = f"{trip.reason} ({trip.measured:g} {trip.unit})" if trip and trip.unit not in ("-",) else (trip.reason if trip else "-")
        lines.append(
            f"| {r.name} | {r.expected_code or '-'} | {', '.join(r.detected_codes) or 'none'} | "
            f"{'-' if r.detection_time_s is None else f'{r.detection_time_s:.1f} s'} | "
            f"{'-' if r.time_to_fault_s is None else f'{r.time_to_fault_s:.1f} s'} | {trip_txt} | "
            f"{r.final_state.value} | {'yes' if r.history[-1].closed_and_locked else 'no'} | {'PASS' if r.passed else 'FAIL'} |"
        )
    return f"{ok}/{len(results)} scenarios passed.\n\n" + "\n".join(lines) + "\n"
