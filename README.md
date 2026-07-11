# Virtual Railway Door Commissioning & Diagnostics

A Python-based digital testbench that demonstrates virtual commissioning, system integration, fault injection, diagnostic logic and requirement-oriented acceptance testing for a simulated railway passenger-door subsystem.

> This is an educational low-voltage software simulation. It is not certified railway software and is not intended to control real equipment.

## Features

- Deterministic railway-door state machine
- Simulated position sensors, supply voltage and actuator current
- Virtual CAN-style command and status messages
- Seven injectable fault modes
- Diagnostic trouble codes and recommended troubleshooting actions
- Automated commissioning and acceptance-test suite
- CSV and HTML report export
- Streamlit dashboard
- Unit tests with pytest

## Architecture

```text
Streamlit diagnostics dashboard
              |
     Commissioning test runner
              |
      Virtual CAN-style bus
       /                 \
Vehicle control      Door control
                         |
          Door, motor, sensors, supply
```

## Windows setup

Open PowerShell in the extracted project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m pytest
py -m streamlit run app.py
```

If PowerShell blocks activation, run this once in the current PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the environment again.

## macOS / Linux setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
python -m streamlit run app.py
```

Streamlit opens the dashboard in your browser. The terminal also prints the local URL.

## Quick command-line demonstration

```bash
python run_demo.py
```

## Suggested demonstration workflow

1. Run the healthy open and close cycle.
2. Inspect the measurement history and virtual message log.
3. Inject a motor-overcurrent fault.
4. Show the D107 diagnostic and safe-state reaction.
5. Clear the fault and run the commissioning suite.
6. Download the generated HTML report.

## Project structure

```text
railway-commissioning-simulator/
├── app.py
├── run_demo.py
├── railway_commissioning/
│   ├── bus.py
│   ├── commissioning.py
│   ├── diagnostics.py
│   ├── models.py
│   ├── reporting.py
│   └── simulator.py
├── tests/
├── docs/
├── requirements.txt
└── pyproject.toml
```

## CV wording after you understand and can demonstrate the project

- Developed a Python-based virtual commissioning environment for a simulated railway passenger-door subsystem.
- Implemented state-machine control, CAN-style interface modelling, fault injection and diagnostic trouble codes.
- Automated requirement-oriented acceptance tests and generated traceable HTML/CSV test reports.

## Honest scope statement

Use the terms **virtual CAN-style communication** or **CAN message modelling** unless you later connect real CAN hardware. Do not claim practical CAN-bus commissioning from this software-only version.
