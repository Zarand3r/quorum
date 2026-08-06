"""Every viewer slider must be able to REPRESENT the value the engine actually runs at.

The viewer builds each slider as min=0, max=KMAX[name], step=max/100, value=<engine value>. An HTML
range input snaps `value` onto the step grid and clamps it to [min, max], so two silent failures are
possible and both shipped:

  * value > max   -- the handle clamps to max and MISREPORTS the engine state, and the first user
                     interaction pushes the engine to that wrong value. lipid2d runs repel=12 against
                     KMAX 0.6, so touching the slider cut excluded volume 20x and collapsed the dish.
  * value < step  -- the handle snaps to 0, displays 0.00 while the engine runs non-zero, and one
                     notch of movement multiplies the parameter by a large factor. lipid2d runs
                     speed=0.001 against step 0.015, so the smallest possible drag was a 15x jump.

Neither is visible from the Python side, which is why 111 passing tests missed both: nothing covered
the server knob surface or the viewer ranges. These tests read the SHIPPED viewer.html rather than a
copy of the table, so the constants cannot drift apart from the file the browser loads.
"""
import json
import pathlib
import re

import pytest

import bicelle2d
import server

VIEWER = pathlib.Path(__file__).resolve().parent.parent / "viewer.html"

# the knob list server.py installs for the --lipid2d dish
LIPID2D_KNOBS = ("repel", "sink_repel", "repel_contact", "attract", "sink_attract",
                 "polarity", "sink_polarity", "k_tail", "k_hydro", "morph", "rigidity",
                 "selectivity", "temperature", "momentum", "speed")


def _kmax() -> dict:
    """Parse the KMAX literal out of the shipped viewer, honouring JS last-key-wins semantics."""
    src = VIEWER.read_text()
    m = re.search(r"const KMAX = \{(.*?)\};", src, re.S)
    assert m, "KMAX table not found in viewer.html"
    out = {}
    for key, val in re.findall(r"([a-z_0-9]+)\s*:\s*([0-9.]+)", m.group(1)):
        out[key] = float(val)          # later duplicate keys overwrite, exactly as JS does
    return out


def _lipid2d_engine():
    return bicelle2d.build(7, n_lip=63, bound=11.0, kt=0.02, speed=0.001, repel=12.0,
                           k_bond=30.0, satt=0.30, attract=1.0, bond_span=2.0, n_tail=2,
                           polarity=0.80, head_q=1.2, hydrophobic=0.6, n_water=250, plant=False)


@pytest.mark.parametrize("knob", LIPID2D_KNOBS)
def test_slider_can_represent_engine_value(knob: str) -> None:
    """max >= value: otherwise the slider clamps and misreports, and touching it wrecks the engine."""
    value = float(getattr(_lipid2d_engine(), knob))
    mx = server.knob_range(knob, value)
    assert value <= mx, (
        f"{knob}: engine runs at {value:g} but the slider maxes at {mx:g}. The handle clamps "
        f"to the max, so it displays the wrong value and the first drag pushes the engine to it.")


@pytest.mark.parametrize("knob", LIPID2D_KNOBS)
def test_slider_resolution_can_reach_engine_value(knob: str) -> None:
    """step <= value: otherwise the handle snaps to 0 and the smallest drag is a huge jump."""
    value = float(getattr(_lipid2d_engine(), knob))
    if value == 0.0:
        pytest.skip(f"{knob} is legitimately 0; the step grid represents it exactly")
    step = server.knob_range(knob, value) / 100.0
    assert step <= value, (
        f"{knob}: engine runs at {value:g} but the slider step is {step:g}. The handle snaps to 0 "
        f"and one notch multiplies the parameter by {step / value:.0f}x.")


def test_hard_bounded_knobs_are_not_scaled_past_their_physical_limit() -> None:
    """momentum >= 1 is an unstable integrator; a 4x-of-default rule would happily produce 1.2."""
    assert server.knob_range("momentum", 0.3) <= 0.98
    assert server.knob_range("rigidity", 0.5) <= 1.0


def test_kmax_has_no_duplicate_keys() -> None:
    """A duplicated key is silently dropped by JS, so the first value is dead config."""
    src = VIEWER.read_text()
    m = re.search(r"const KMAX = \{(.*?)\};", src, re.S)
    keys = [k for k, _ in re.findall(r"([a-z_0-9]+)\s*:\s*([0-9.]+)", m.group(1))]
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    assert not dupes, f"KMAX declares {dupes} more than once; JS keeps only the last value"


def test_every_live_knob_has_a_tooltip() -> None:
    """A slider with no KDESC entry renders a blank description and an empty title attribute."""
    src = VIEWER.read_text()
    desc = set(re.findall(r"([a-z_0-9]+)\s*:\s*\"", src[src.index("const KDESC"):]))
    missing = [k for k in LIPID2D_KNOBS if k not in desc]
    assert not missing, f"sliders rendered with no tooltip: {missing}"
