from railway_commissioning.commissioning import run_commissioning_suite
from railway_commissioning.diagnostics import diagnose
from railway_commissioning.models import DoorCommand, FaultMode
from railway_commissioning.simulator import DoorSystemSimulator


def main() -> None:
    simulator = DoorSystemSimulator()
    simulator.issue_command(DoorCommand.OPEN)
    simulator.run_for(3.5)
    print("Healthy opening cycle:", simulator.latest().to_dict())

    simulator.reset(full=True)
    simulator.inject_fault(FaultMode.MOTOR_OVERCURRENT)
    simulator.issue_command(DoorCommand.OPEN)
    simulator.step()
    print("\nInjected overcurrent:")
    for event in diagnose(simulator.latest()):
        print(f"{event.code}: {event.title} — {event.recommendation}")

    print("\nCommissioning suite:")
    for result in run_commissioning_suite():
        status = "PASS" if result.passed else "FAIL"
        print(f"{result.test_id}: {status} | {result.measured}")


if __name__ == "__main__":
    main()
