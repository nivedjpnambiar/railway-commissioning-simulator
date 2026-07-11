from __future__ import annotations

import pandas as pd
import streamlit as st

from railway_commissioning.commissioning import run_commissioning_suite
from railway_commissioning.diagnostics import diagnose
from railway_commissioning.models import DoorCommand, FaultMode
from railway_commissioning.reporting import results_to_csv, results_to_html
from railway_commissioning.simulator import DoorSystemSimulator


st.set_page_config(
    page_title="Railway Door Commissioning Simulator",
    page_icon="🚆",
    layout="wide",
)


def get_simulator() -> DoorSystemSimulator:
    if "simulator" not in st.session_state:
        st.session_state.simulator = DoorSystemSimulator()
    return st.session_state.simulator


def telemetry_dataframe(simulator: DoorSystemSimulator) -> pd.DataFrame:
    return pd.DataFrame(item.to_dict() for item in simulator.history)


simulator = get_simulator()

st.title("Virtual Railway Door Commissioning & Diagnostics")
st.caption(
    "Python-based digital testbench for system integration, fault injection, "
    "diagnostics and requirement-oriented acceptance testing."
)

with st.sidebar:
    st.header("Control panel")
    c1, c2 = st.columns(2)
    if c1.button("Open", use_container_width=True):
        simulator.issue_command(DoorCommand.OPEN)
    if c2.button("Close", use_container_width=True):
        simulator.issue_command(DoorCommand.CLOSE)
    c3, c4 = st.columns(2)
    if c3.button("Stop", use_container_width=True):
        simulator.issue_command(DoorCommand.STOP)
    if c4.button("Reset state", use_container_width=True):
        simulator.issue_command(DoorCommand.RESET)

    duration = st.slider("Simulation duration per run (s)", 0.5, 10.0, 1.0, 0.5)
    if st.button("Run simulation", type="primary", use_container_width=True):
        simulator.run_for(duration)

    st.divider()
    st.subheader("Fault injection")
    fault_labels = {
        "Blocked door": FaultMode.BLOCKED_DOOR,
        "Open sensor failed": FaultMode.OPEN_SENSOR_FAILED,
        "Closed sensor failed": FaultMode.CLOSED_SENSOR_FAILED,
        "Contradictory sensors": FaultMode.CONTRADICTORY_SENSORS,
        "Communication loss": FaultMode.COMMUNICATION_LOSS,
        "Undervoltage": FaultMode.UNDERVOLTAGE,
        "Motor overcurrent": FaultMode.MOTOR_OVERCURRENT,
    }
    selected_faults = st.multiselect(
        "Active faults",
        options=list(fault_labels),
        default=[label for label, mode in fault_labels.items() if mode in simulator.faults],
    )
    desired = {fault_labels[label] for label in selected_faults}
    for fault in list(simulator.faults - desired):
        simulator.clear_fault(fault)
    for fault in desired - simulator.faults:
        simulator.inject_fault(fault)

    if st.button("Clear faults and restart", use_container_width=True):
        simulator.clear_all_faults()
        simulator.reset(full=True)
        st.rerun()

latest = simulator.latest()

metric_columns = st.columns(5)
metric_columns[0].metric("State", latest.state.value)
metric_columns[1].metric("Position", f"{latest.position_pct:.1f}%")
metric_columns[2].metric("Motor current", f"{latest.motor_current_a:.2f} A")
metric_columns[3].metric("Supply", f"{latest.supply_voltage_v:.1f} V")
metric_columns[4].metric("Communication", "OK" if latest.communication_ok else "LOST")

left, right = st.columns([1.4, 1])
with left:
    st.subheader("Live measurement history")
    history = telemetry_dataframe(simulator)
    if len(history) > 1:
        chart_data = history.set_index("timestamp_s")[["position_pct", "motor_current_a", "supply_voltage_v"]]
        st.line_chart(chart_data)
    else:
        st.info("Issue a command and run the simulation to create measurement history.")

with right:
    st.subheader("Digital inputs and fault status")
    st.write(
        {
            "Open-position sensor": latest.open_sensor,
            "Closed-position sensor": latest.closed_sensor,
            "Active injected faults": [fault.value for fault in latest.active_faults] or ["none"],
        }
    )
    events = diagnose(latest)
    if not events:
        st.success("No active diagnostic events")
    for event in events:
        st.error(f"{event.code} — {event.title}")
        st.write(event.details)
        st.caption(f"Recommended action: {event.recommendation}")

st.subheader("Virtual CAN-style message log")
messages = simulator.bus.messages(limit=40)
if messages:
    st.dataframe(
        pd.DataFrame(
            {
                "Time [s]": [message.timestamp_s for message in messages],
                "ID": [f"0x{message.message_id:03X}" for message in messages],
                "Source": [message.source for message in messages],
                "Signal": [message.signal for message in messages],
                "Value": [message.value for message in messages],
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No messages are available. Communication may be interrupted or no cycle has run yet.")

st.divider()
st.header("Automated commissioning and acceptance tests")
if st.button("Run commissioning suite", type="primary"):
    st.session_state.test_results = run_commissioning_suite()

if "test_results" in st.session_state:
    results = st.session_state.test_results
    table = pd.DataFrame(result.to_dict() for result in results)
    st.dataframe(table, use_container_width=True, hide_index=True)
    passed = sum(result.passed for result in results)
    if passed == len(results):
        st.success(f"Overall result: PASS — {passed}/{len(results)} tests passed")
    else:
        st.error(f"Overall result: FAIL — {passed}/{len(results)} tests passed")

    d1, d2 = st.columns(2)
    d1.download_button(
        "Download CSV report",
        results_to_csv(results),
        file_name="commissioning_report.csv",
        mime="text/csv",
        use_container_width=True,
    )
    d2.download_button(
        "Download HTML report",
        results_to_html(results),
        file_name="commissioning_report.html",
        mime="text/html",
        use_container_width=True,
    )
