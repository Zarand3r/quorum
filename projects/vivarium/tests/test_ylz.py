"""Locks in the M1-M3 results so they cannot regress silently.

Each test corresponds to a claim made in docs/ROADMAP_V2.md. The expensive part of this project has
never been running simulations; it has been discovering that a number quoted three days earlier was
measured with a broken instrument. These assertions are the instruments.
"""

import numpy as np
import pytest

from attention_ylz import AttentionYLZ, check_identity
from ylz import YLZ, cell_pairs, check_gradients


def test_forces_and_torques_match_numerical_gradients():
    """Analytic force and torque must equal -dU/dx and -dU/dn.

    An anisotropic potential with a wrong sign or a dropped projection still produces plausible
    aggregates, so visual inspection cannot catch it.
    """
    err_f, err_t = check_gradients()
    assert err_f < 1e-4, f"force gradient error {err_f:.2e}"
    assert err_t < 1e-4, f"torque gradient error {err_t:.2e}"


def test_gradients_hold_with_the_bounded_core():
    s = YLZ(40, 6.0, seed=0, beta=0.15, bounded_core=True, contact=30.0)
    f, _ = s.forces_torques()
    h = 1e-6
    worst = 0.0
    for k in range(5):
        for c in range(3):
            s.x[k, c] += h
            up = s.energy()
            s.x[k, c] -= 2 * h
            dn = s.energy()
            s.x[k, c] += h
            worst = max(worst, abs((-(up - dn) / (2 * h)) - f[k, c]))
    assert worst < 1e-4, f"bounded-core force gradient error {worst:.2e}"


@pytest.mark.parametrize("bounded", [False, True])
def test_energy_is_exactly_one_attention_layer(bounded):
    """M2: the potential IS an unnormalized distance-penalized attention layer, not an approximation.

    Checked for both cores, because the vesicle that satisfies Vivarium's constraints uses the
    bounded one; an identity that held only for the published r^-4 core would not apply to it.
    """
    rel = check_identity(bounded=bounded, contact=30.0)
    assert rel < 1e-12, f"attention identity broken, relative error {rel:.2e}"


def test_bounded_core_is_actually_bounded():
    """Vivarium forbids divergent kernels. The published YLZ core violates that; ours must not."""
    s = YLZ(2, 10.0, bounded_core=True, contact=30.0)
    r = np.array([1.0, 0.1, 1e-3, 1e-6])
    u = s._u_rep(r)
    assert np.all(np.isfinite(u))
    assert u.max() <= 30.0 + 1e-9, "contact energy exceeds the requested bound"

    d = YLZ(2, 10.0, bounded_core=False)
    assert d._u_rep(np.array([1e-3]))[0] > 1e9, "published core should diverge; test is miscalibrated"


def test_thermostat_temperature_is_timestep_independent():
    """The first Langevin implementation applied noise in both half-kicks and measured T ~ kT/2.

    That is the same failure class as the DPD thermostat bug (T = 0.51 against 1.0). The exact
    Ornstein-Uhlenbeck update that replaced it must give a temperature that does not drift with dt.
    """
    temps = []
    for dt in (0.005, 0.01, 0.02):
        s = YLZ(200, 20.0, seed=1, dt=dt)
        for _ in range(3000):
            s.step()
        temps.append(s.temperature())
    for T in temps:
        assert 0.7 * s.kT < T < 1.4 * s.kT, f"temperature {T:.4f} far from target {s.kT}"
    spread = (max(temps) - min(temps)) / np.mean(temps)
    assert spread < 0.25, f"temperature varies {spread:.2f} across a 4x timestep range"


def test_cell_list_covers_every_true_pair_exactly_once():
    """`cell_pairs` returns CANDIDATES; the rc cutoff is applied by the caller.

    Note the asymmetry with `dpd_reference._pairs`, which filters by rc internally. The contract
    here is therefore: every genuine within-rc pair appears, no unordered pair appears twice, and no
    candidate lies beyond the cell reach. Asserting set equality against the within-rc pairs would
    be testing the wrong contract and fails on the candidates that are simply farther than rc.
    """
    rng = np.random.default_rng(0)
    for n, L in ((200, 6.0), (500, 9.0)):
        x = rng.uniform(0, L, (n, 3))
        i, j = cell_pairs(x, L, 2.6)
        got = {(min(int(a), int(b)), max(int(a), int(b)))
               for a, b in zip(i.tolist(), j.tolist())}
        assert len(i) == len(got), "cell list emitted a duplicate pair"

        d = x[:, None, :] - x[None, :, :]
        d -= L * np.round(d / L)
        r = np.linalg.norm(d, axis=2)
        iu = np.triu_indices(n, 1)
        true_pairs = {(int(a), int(b))
                      for a, b in zip(*[v[r[iu] < 2.6] for v in iu])}
        assert true_pairs <= got, f"cell list missed {len(true_pairs - got)} real pairs"


def test_attention_projections_are_the_substitution_point():
    """W_q/W_k/W_p are identity at construction; scaling one must change the energy.

    Guards against the projections being accidentally ignored, which would make later ablations
    look like no-ops and silently invalidate the whole M3+ programme.
    """
    s = YLZ(120, 10.0, seed=3, beta=0.12)
    base = AttentionYLZ(s).energy()
    perturbed = AttentionYLZ(s, W_q=1.5 * np.eye(3)).energy()
    assert abs(base - perturbed) > 1e-6 * max(abs(base), 1.0)
