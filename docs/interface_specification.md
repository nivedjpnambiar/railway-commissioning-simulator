# Interface specification

The project models a CAN-style logical interface between a vehicle control unit and a door control unit.
It is a software simulation and does not claim physical CAN conformance.

| Message ID | Source | Signal | Type | Purpose |
|---|---|---|---|---|
| `0x101` | Vehicle control unit | `door_command` | enum | OPEN, CLOSE, STOP, RESET |
| `0x201` | Door control unit | `door_state` | enum | Current state-machine state |
| `0x202` | Door control unit | `position_pct` | float | Simulated door travel from 0-100% |
| `0x203` | Door control unit | `motor_current_a` | float | Simulated actuator current |
| `0x204` | Door control unit | `supply_voltage_v` | float | Simulated low-voltage supply |
| `0x205` | Door control unit | `door_closed_and_locked` | bool | Door CLOSED **and** closed sensor confirmed **and** open sensor inactive. Used by the vehicle as departure (traction) permission. |

Status messages `0x201`-`0x205` are sent every simulation step (100 ms). When the bus is
offline (communication loss) no messages are sent and the door control unit trips to FAULT.
