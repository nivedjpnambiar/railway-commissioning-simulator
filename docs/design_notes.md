# Design notes and findings

## v1.1: protection based on measured values

In v1.0 the protection logic switched to FAULT when a fault from a list of
"critical" fault modes was *injected*. The limits in `SimulatorConfig`
(`overcurrent_limit_a`, `undervoltage_threshold_v`) existed but were never
used. A test bench cannot work like that: the controller only sees currents,
voltages, sensor inputs and bus messages.

**Change:** `_apply_protection_logic` now compares measured values with the
configured limits (current, voltage, sensor plausibility, bus status, stall
time, movement timeout). Each trip is written to `protection_log` with time,
measured value and limit. The FAULT state is latched until RESET. Tests show
that changing a limit in the configuration changes the reaction
(`tests/test_protection.py`).

## v1.1: a blocked door was not detected in the standard test profile

While building the fault matrix (OPEN at 0 s, CLOSE at 4 s), the scenario
`blocked_door` ended in state CLOSING with the motor still energised at 1.25 A
and no FAULT.

**Root cause:** the only protection for a blocked door was the 5 s movement
timeout. Every new command restarts the movement timer, so a CLOSE after 4 s
hid the blockage. The current of a blocked door (1.25 A) is also below the
overcurrent limit (1.5 A), so the overcurrent protection does not react either.

**Correction:** stall protection. If the motor is energised and the position
does not change for `stall_time_s` (1 s), the door trips to FAULT
(`motor_stall`). The movement timeout stays as a second, independent
protection. Covered by TC-009 and `test_new_command_does_not_hide_a_blocked_door`.

## v1.1: STOP command cleared a latched fault

A STOP command set the state to STOPPED in every state, also in FAULT. After a
trip whose cause was gone (for example a stall), STOP followed by OPEN moved
the door again without RESET. STOP is now ignored in FAULT; only RESET leaves
the safe state (`test_stop_does_not_clear_latched_fault`).

## v1.1: measurement-based detection

`diagnostics.diagnose` returns the catalogue entry of an injected fault. This
is useful in the dashboard, but it cannot show whether a fault would really be
*found*. `detection.detect_faults` works only on recorded telemetry and
protection trips. The fault matrix injects every fault and checks that exactly
the expected code is found, and a test removes the injected-fault labels from
the telemetry to prove the detection does not use them.

## v1.1: departure permission signal

A failed closed-position sensor does not stop the door, but the train must not
depart without a confirmed closed end position. The new signal
`door_closed_and_locked` (bus ID `0x205`) is only true when the door is CLOSED,
the closed sensor is active and the open sensor is inactive (TC-010).

## Simplifications

* constant motor current, linear door movement, no mechanical model
* sensor faults are modelled as stuck-at values
* one door, one controller, no redundancy
