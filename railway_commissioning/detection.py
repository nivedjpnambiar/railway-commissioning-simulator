"""Measurement-based fault detection.

``diagnostics.diagnose`` looks up the catalogue entry of an *injected* fault,
which is useful for the dashboard. This module does what a real door
controller or a commissioning engineer has to do instead: find the fault code
only from recorded measurements (telemetry) and protection trips, without
knowing which fault was injected.

The fault matrix (``scenarios.run_fault_matrix``) injects every fault and
checks that this detection finds exactly the expected code.
"""

from __future__ import annotations

from .models import Detection, DoorState, ProtectionTrip, Telemetry
from .simulator import SimulatorConfig

BLOCKED_AFTER_S = 1.0  # commanded movement without position change


def detect_faults(
    history: list[Telemetry],
    trips: list[ProtectionTrip] | None = None,
    config: SimulatorConfig | None = None,
) -> list[Detection]:
    cfg = config or SimulatorConfig()
    trips = trips or []
    found: dict[str, Detection] = {}

    def add(code: str, t: float, evidence: str) -> None:
        if code not in found:
            found[code] = Detection(code, t, evidence)

    for trip in trips:
        if trip.reason == "motor_overcurrent":
            add("D107", trip.timestamp_s, f"protection trip: {trip.measured} A > {trip.limit} A")
        if trip.reason == "motor_stall":
            add("D101", trip.timestamp_s, f"protection trip: motor energised without movement for {trip.measured:g} s")

    stuck_since = None
    last_pos = None
    tol = cfg.sensor_tolerance_pct
    for t in history:
        if t.motor_current_a > cfg.overcurrent_limit_a:
            add("D107", t.timestamp_s, f"current {t.motor_current_a} A > {cfg.overcurrent_limit_a} A")
        if t.supply_voltage_v < cfg.undervoltage_threshold_v:
            add("D106", t.timestamp_s, f"supply {t.supply_voltage_v} V < {cfg.undervoltage_threshold_v} V")
        if not t.communication_ok:
            add("D105", t.timestamp_s, "no status messages on the bus")
        if t.open_sensor and t.closed_sensor:
            add("D104", t.timestamp_s, "open and closed end-position sensors active together")
        if t.state is DoorState.OPEN and t.position_pct >= 100.0 - tol and not t.open_sensor:
            add("D102", t.timestamp_s, f"position {t.position_pct} % but open sensor not confirmed")
        if t.state is DoorState.CLOSED and t.position_pct <= tol and not t.closed_sensor:
            add("D103", t.timestamp_s, f"position {t.position_pct} % but closed sensor not confirmed")

        moving = t.state in (DoorState.OPENING, DoorState.CLOSING)
        if moving and t.motor_current_a > 0 and last_pos is not None and abs(t.position_pct - last_pos) < 1e-9:
            stuck_since = t.timestamp_s if stuck_since is None else stuck_since
            if t.timestamp_s - stuck_since >= BLOCKED_AFTER_S - 1e-9:
                add("D101", t.timestamp_s, f"motor energised ({t.motor_current_a} A) but position unchanged for {BLOCKED_AFTER_S:g} s")
        else:
            stuck_since = None
        last_pos = t.position_pct

    if any(t.state is DoorState.FAULT for t in history) and not found:
        first = next(t for t in history if t.state is DoorState.FAULT)
        add("D199", first.timestamp_s, "FAULT state without classified cause")

    return sorted(found.values(), key=lambda d: (d.first_seen_s, d.code))
