# Fault catalog

| Code | Fault | How it is detected (measured values only) | Safe reaction | Recommended first check |
|---|---|---|---|---|
| D101 | Door movement blocked | motor energised, position unchanged for 1 s | `motor_stall` protection trip, FAULT, motor off | Mechanical freedom of movement |
| D102 | Open sensor unavailable | door at open end position (100 %) but open sensor not active | Diagnostic event | Sensor and wiring |
| D103 | Closed sensor unavailable | door at closed end position (0 %) but closed sensor not active | Diagnostic event, **no departure permission** (`door_closed_and_locked` = false) | Sensor and wiring |
| D104 | Contradictory position sensors | open and closed sensor active together | `sensor_implausible` trip, FAULT | Both end-position circuits |
| D105 | Communication loss | no status messages on the bus | `communication_timeout` trip, FAULT | Controller and bus interface |
| D106 | Supply undervoltage | supply below 19 V | `undervoltage` trip, FAULT | Supply and voltage drop |
| D107 | Motor overcurrent | current above 1.5 A | `motor_overcurrent` trip, FAULT, motor off | Actuator, mechanics and wiring |
| D199 | Unclassified fault | FAULT state without any of the above | - | Event log, compare with acceptance limits |

The limits come from `SimulatorConfig`. The results of all faults are in the [fault matrix](fault_matrix.md).
