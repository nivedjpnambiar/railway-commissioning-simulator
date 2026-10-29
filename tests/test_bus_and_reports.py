from railway_commissioning.commissioning import run_commissioning_suite
from railway_commissioning.models import DoorCommand
from railway_commissioning.plotting import scenario_svg
from railway_commissioning.scenarios import run_scenario
from railway_commissioning.simulator import DoorSystemSimulator


def test_status_messages_published_each_step():
    sim = DoorSystemSimulator()
    sim.issue_command(DoorCommand.OPEN)
    sim.step()
    ids = [m.message_id for m in sim.bus.messages()]
    assert ids[0] == 0x101
    assert {0x201, 0x202, 0x203, 0x204, 0x205} <= set(ids)


def test_closed_and_locked_signal_follows_door():
    sim = DoorSystemSimulator()
    assert sim.latest().closed_and_locked
    sim.issue_command(DoorCommand.OPEN)
    sim.step()
    assert not sim.latest().closed_and_locked


def test_commissioning_suite_ids_unique_and_passing():
    results = run_commissioning_suite()
    assert len({r.test_id for r in results}) == len(results) == 11
    assert all(r.passed for r in results)


def test_scenario_plot_is_svg():
    svg = scenario_svg(run_scenario(None))
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
