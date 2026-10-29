# Changelog

## 1.1.0

- Protection logic uses measured values and configured limits; protection trip log
- Stall protection for blocked doors (found with the fault matrix, see docs/design_notes.md)
- Measurement-based fault detection (`detection.py`) independent from injected fault labels
- Fault matrix for all fault modes with generated plots (`scripts/generate_docs.py`)
- Departure permission signal `door_closed_and_locked` (bus ID 0x205)
- Commissioning suite extended to 11 test cases (TC-009 to TC-011)
- STOP no longer clears a latched FAULT
- 39 automated tests, GitHub Actions CI
- Dashboard shows detections, protection trips and closed & locked status

## 1.0.0

- Door state machine, virtual CAN-style bus, 7 fault modes, diagnostic codes
- Commissioning suite TC-001 to TC-008 with CSV/HTML reports
- Streamlit dashboard
