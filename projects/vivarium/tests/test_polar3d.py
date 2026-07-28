"""Verify the 3-D (spherical-harmonic) contour and the contact-area van der Waals rewrite.

These are the invariants the bilayer work depends on. Each one is a property that, if it silently
broke, would make every emergence number meaningless rather than merely wrong.
"""

from __future__ import annotations

import inspect
import os
import re
import sys

import numpy as np
import pytest

import pack
import polar_pack
from config import DEFAULTS, VivariumConfig
from pack import PackEngine
from polar_pack import AMPHI, WATER, PolarPackEngine
sys.path.insert(0, os.path.dirname(__file__))       # sibling test module (tests/ is not a package)
from test_transformer_only import _FORBIDDEN, _strip_comments  # noqa: E402


def _cfg3(**over):
    return VivariumConfig(**{**DEFAULTS, "N": 24, "pos_dim": 3, "n_harmonics": 2,
                             "pos_bound": 3.0, **over})


def _cfg2(**over):
    return VivariumConfig(**{**DEFAULTS, "N": 24, **over})


# ---------------------------------------------------------------- spherical-harmonic correctness

def test_axial_coeffs_reproduce_legendre():
    """_axial_coeffs uses the SH addition theorem: coefficients = the basis at the molecule's OWN
    axis, scaled by 4π/(2l+1). The readout must then be exactly q·P_l(u·v̂) for any viewing
    direction. If the scaling were wrong the charge pattern would be silently mis-shaped."""
    e = PolarPackEngine(_cfg3(), 0, water_frac=0.0, polarity=0.0)
    rng = np.random.default_rng(0)
    u = rng.standard_normal((5, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    v = rng.standard_normal((7, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    basis_v = e._sh_basis(v)                       # (7, shape_dim)

    for amps, legendre in (([1.3, 0.0], lambda t: t),                       # P1
                           ([0.0, 0.9], lambda t: 0.5 * (3 * t * t - 1))):  # P2
        c = e._axial_coeffs(u, amps)               # (5, shape_dim)
        got = c @ basis_v.T                        # nf_i(v_j)
        q = amps[0] if amps[0] else amps[1]
        want = q * legendre(u @ v.T)
        assert np.allclose(got, want, atol=1e-10), f"amps={amps} max err {np.abs(got-want).max()}"


def test_amphiphile_has_polar_head_and_neutral_tail():
    """The whole point of the 3-D amphiphile: amps=[q/2, q/2] makes P1+P2 cancel behind, giving
    +q at the head and ~0 at the TAIL — bulky but NEUTRAL, the molecule 2-D could not express.
    A negative tail would be attracted to water's positive face and would not be hydrophobic."""
    e = PolarPackEngine(_cfg3(), 0, water_frac=0.0, polarity=0.0)
    u = np.array([[0.0, 0.0, 1.0]])
    q = 2.0
    c = e._axial_coeffs(u, [0.5 * q, 0.5 * q])
    head = float(c[0] @ e._sh_basis(u)[0])         # looking along +u
    tail = float(c[0] @ e._sh_basis(-u)[0])        # looking along −u
    side = float(c[0] @ e._sh_basis(np.array([[1.0, 0.0, 0.0]]))[0])
    assert head == pytest.approx(q, abs=1e-9)
    assert tail == pytest.approx(0.0, abs=1e-9)
    assert side < 0.0                              # net neutral ⇒ the belt carries the balance


def test_water_dipole_is_symmetric_head_to_tail():
    """Water is a pure dipole (amps=[q,0]): +q one way, −q the other. Unlike the amphiphile it has
    no neutral face — that asymmetry between the two species is what drives the assembly."""
    e = PolarPackEngine(_cfg3(), 0, water_frac=0.0, polarity=0.0)
    u = np.array([[0.0, 1.0, 0.0]])
    c = e._axial_coeffs(u, [0.7, 0.0])
    assert float(c[0] @ e._sh_basis(u)[0]) == pytest.approx(0.7, abs=1e-9)
    assert float(c[0] @ e._sh_basis(-u)[0]) == pytest.approx(-0.7, abs=1e-9)


def test_rotate_toward_keeps_axes_unit_and_moves_toward_field():
    e = PolarPackEngine(_cfg3(), 0, water_frac=0.0, polarity=0.0)
    rng = np.random.default_rng(1)
    u = rng.standard_normal((16, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    f = rng.standard_normal((16, 3))
    out = e._rotate_toward(u, f, 0.3)
    assert np.allclose(np.linalg.norm(out, axis=1), 1.0, atol=1e-9)
    fhat = f / np.linalg.norm(f, axis=1, keepdims=True)
    assert np.all(np.sum(out * fhat, axis=1) >= np.sum(u * fhat, axis=1) - 1e-12)


def test_zero_field_leaves_orientation_unchanged():
    """No field ⇒ no torque. Otherwise molecules would drift toward an arbitrary direction."""
    e = PolarPackEngine(_cfg3(), 0, water_frac=0.0, polarity=0.0)
    u = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
    assert np.allclose(e._rotate_toward(u, np.zeros((2, 3)), 0.5), u)


# ---------------------------------------------------------------- the van der Waals rewrite

def test_vdw_is_charge_independent():
    """Dispersion must depend on SIZE only. Two tokens with identical radii but wildly different
    charge patterns must feel the same attraction — that is what lets a neutral tail cohere."""
    src = _strip_comments(inspect.getsource(PackEngine.step))
    line = [ln for ln in src.split("\n") if "np.tanh(rad" in ln or "np.sqrt(eps" in ln]
    assert line, "contact-area vdW kernel not found in step()"
    assert all("S_comp" not in ln for ln in line), "vdW must not read the charge term"


def test_conservative_forces_conserve_momentum():
    """Every conservative kernel is symmetric and every direction antisymmetric ⇒ F_ij = −F_ji ⇒
    Σ_i F_i = 0. If this drifts, the system is being pushed by a phantom external force and any
    'structure' it forms is an artefact."""
    for cfg in (_cfg2(N=40), _cfg3(N=40)):
        e = PolarPackEngine(cfg, 0, water_frac=0.5, amphi_frac=0.5, polarity=1.0,
                            repel=2.0, attract=0.5, cohesion=0.0, skew=0.0)
        e.conservative = True
        e.repel_contact = 1.0
        e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, 1.0, 0.25
        e.temperature = 0.0                       # thermal noise is external by construction
        e.maxvel = 1e9                            # the per-token speed CAP is a non-conservative
        #   clamp applied after the force sum — it is deliberate overshoot control, not a pair
        #   force, so it must be disabled to test the force law itself (see test below).
        before = e.vel.sum(axis=0).copy()
        e.step()
        drift = np.abs(e.vel.sum(axis=0) - e.momentum * before).max()
        assert drift < 1e-9, f"pos_dim={cfg.pos_dim} net force {drift} ≠ 0"


# ---------------------------------------------------------------- base case + construction errors

def test_base_case_identity_holds_in_3d():
    """The reduction that makes every added feature auditable: with the polar features off, the
    engine must be bit-identical to plain PackEngine — in 3-D as well as 2-D."""
    for cfg in (_cfg2(), _cfg3()):
        a = PolarPackEngine(cfg, 3, water_frac=0.0, polarity=0.0)
        b = PackEngine(cfg, 3)
        for _ in range(60):
            a.step()
            b.step()
        assert np.max(np.abs(a.X - b.X)) == 0.0, f"pos_dim={cfg.pos_dim} diverged"


def test_3d_rejects_unimplemented_harmonics():
    """_sh_basis implements l=1,2. Anything higher must fail loudly at construction rather than
    silently returning too few coefficients for the declared shape_dim."""
    with pytest.raises(ValueError, match="n_harmonics"):
        _cfg3(n_harmonics=3)


def test_3d_shape_dim_matches_basis_width():
    for K in (1, 2):
        cfg = _cfg3(n_harmonics=K)
        e = PolarPackEngine(cfg, 0, water_frac=0.0, polarity=0.0)
        u = np.array([[0.0, 0.0, 1.0]])
        assert e._sh_basis(u).shape[-1] == cfg.shape_dim == K * (K + 2)


def test_radius_channel_does_not_overlap_the_contour():
    """Size and charge must live in DISJOINT channels — that separation is the whole fix."""
    for cfg in (_cfg2(), _cfg3()):
        e = PolarPackEngine(cfg, 0, water_frac=0.0, polarity=0.0)
        assert e.rad_idx >= e.pd + cfg.shape_dim
        assert e.rad_idx < cfg.d


def test_species_radii_are_rewritten_every_step():
    """Fixed species are rigid: their size is a constant of the species, not something the MLP
    may drift. If this stopped holding, dispersion strengths would wander mid-run."""
    e = PolarPackEngine(_cfg3(N=40), 0, water_frac=0.5, amphi_frac=0.5, polarity=1.0)
    for _ in range(25):
        e.step()
    assert np.allclose(e.X[e._wi, e.rad_idx], polar_pack.RAD_WATER)
    assert np.allclose(e.X[e._ai, e.rad_idx], polar_pack.RAD_AMPHI)


# ---------------------------------------------------------------- transformer-only, polar hooks

# Anything that is NOT part of the dynamics — rendering, measurement, diagnostics, construction.
# Everything else is audited. This list is the ONLY escape hatch, so a newly added dynamical method
# is covered by default rather than silently skipped (which is exactly what happened to the bond
# force, the stiffness step and the anisotropic contact distance).
_NON_DYNAMICAL = {
    "render_svg", "snapshot", "measure", "token_polarity", "fork", "mode_orders",
    "min_image_margin", "amphi_head", "chain_axis", "_binding_edges", "_neighbors",
    "_contour", "_periodic_delta", "_mickey_template", "_amphi_template", "_build_stiffness",
    "_build_chains", "_write_water", "_write_amphi", "_write_radii", "_write_chain",
    "_attn", "_lipid_force",
}


def _dynamical_methods(cls):
    """Every method of `cls` that participates in the dynamics, by exclusion rather than by an
    allowlist — fail-closed, so nothing new can slip through unaudited."""
    for name, fn in inspect.getmembers(cls, inspect.isfunction):
        if name.startswith("__") or name in _NON_DYNAMICAL:
            continue
        if fn.__module__ not in ("pack", "polar_pack"):
            continue
        yield name, _strip_comments(inspect.getsource(fn))


def test_every_dynamical_method_is_transformer_only():
    """Audit the FULL dynamical surface of both engines, not a hand-maintained list."""
    seen = []
    for cls in (PackEngine, PolarPackEngine):
        for name, src in _dynamical_methods(cls):
            seen.append(name)
            for pat in _FORBIDDEN:
                assert not re.search(pat, src), f"{cls.__name__}.{name} matches forbidden {pat}"
    for required in ("_bond_force", "_contact_distance", "_apply_stiffness", "_extra_force",
                     "_post_morph", "_sh_basis", "step"):
        assert required in seen, f"{required} escaped the transformer-only audit"


def test_bond_force_is_masked_attention_not_a_spring():
    """A bond must be a FIXED PAIR MASK carrying a BOUNDED symmetric kernel — masked/local attention,
    which the requirement allows — and emphatically not an unbounded harmonic spring."""
    e = PolarPackEngine(_cfg3(N=30), 0, water_frac=0.4, chain_frac=0.6, polarity=1.0)
    assert e._bond_i.size, "no bonds were built"
    src = _strip_comments(inspect.getsource(PolarPackEngine._bond_force))
    assert "np.tanh" in src, "bond kernel must be bounded"
    # bounded: stretch a bond absurdly far and the force must not grow without limit
    e.X[e._bond_j[0], :e.pd] = e.X[e._bond_i[0], :e.pd] + 500.0
    f = e._bond_force()
    # each bond contributes at most k_bond (|tanh| <= 1 times a unit vector), and a bead takes part
    # in at most TWO bonds (the head bonds to both tail beads), so 2*k_bond is the true ceiling.
    per_bead = np.bincount(np.concatenate([e._bond_i, e._bond_j]), minlength=e.cfg.N).max()
    assert np.isfinite(f).all(), "bond force produced a non-finite value"
    assert np.abs(f).max() <= e.k_bond * per_bead * 1.001, "bond force is unbounded"
    # symmetric ⇒ conservative
    assert np.abs(f.sum(axis=0)).max() < 1e-9, "bond force does not conserve momentum"


def test_no_divergent_distance_kernel_in_polar_forces():
    """Explicitly: nothing may divide by a distance. Bounded kernels only (exp/tanh/softmax)."""
    src = _strip_comments(inspect.getsource(polar_pack.PolarPackEngine._extra_force))
    assert not re.search(r"/\s*dist\b(?!\[)", src.replace("dij / dist[..., None]", ""))
    assert "np.exp(" in src or "np.tanh(" in src


def test_forces_stay_bounded_far_apart():
    """A real 1/d² kernel blows up as d→0 and never vanishes as d→∞. Ours must do neither."""
    e = PolarPackEngine(_cfg3(N=12, pos_bound=50.0), 0, water_frac=1.0, polarity=1.0)
    e.conservative = True
    e.sink_polarity = 0.25
    e.X[0, :3] = [0.0, 0.0, 0.0]
    e.X[1, :3] = [40.0, 0.0, 0.0]
    far = np.abs(e._extra_force()).max()
    e.X[1, :3] = [0.02, 0.0, 0.0]
    near = np.abs(e._extra_force()).max()
    assert far < 1e-6, f"force does not decay with distance: {far}"
    assert np.isfinite(near) and near < 100.0, f"force diverges at contact: {near}"


def test_speed_cap_is_the_only_momentum_breaking_op():
    """Honest accounting: the pair forces conserve momentum exactly, but the per-token maxvel clamp
    does not. Documented here so 'relaxes to a free-energy minimum' is read with that caveat — when
    the cap binds, momentum is injected/removed."""
    e = PolarPackEngine(_cfg2(N=40), 0, water_frac=0.5, amphi_frac=0.5, polarity=1.0,
                        repel=8.0, attract=0.5, cohesion=0.0, skew=0.0)
    e.conservative = True
    e.repel_contact = 1.0
    e.temperature = 0.0
    e.maxvel = 1e-4                               # force the clamp to bind
    before = e.vel.sum(axis=0).copy()
    e.step()
    assert np.abs(e.vel.sum(axis=0) - e.momentum * before).max() > 1e-9


def test_packing_fraction_is_physically_possible():
    """A configuration above random close packing (~0.64 in 3-D, ~0.82 in 2-D) cannot exist: the
    dish is jammed and nothing can rearrange. This is easy to create by accident, because changing a
    bead RADIUS silently changes the packing unless the box is resized too. That is exactly what
    happened when water was resized from 0.30 to 0.50 for the MARTINI convention and the showcase
    box was left alone, leaving the live dish at 92%."""
    for cfg, limit in ((_cfg3(N=40, pos_bound=4.0), 0.64), (_cfg2(N=40, pos_bound=6.0), 0.82)):
        e = PolarPackEngine(cfg, 0, water_frac=0.6, chain_frac=0.4, polarity=1.0)
        pf = e.packing_fraction()
        assert 0.0 < pf < limit, f"pos_dim={cfg.pos_dim} packing {pf:.2f} exceeds {limit}"


def test_micelle_metric_null_is_zero():
    """The radial-order metric must read ~0 on random molecules, or its threshold is meaningless.

    `outward` took rhat at the HEAD, whose position depends on the molecular axis u, so u sat on both
    sides of the dot product and the statistic read +0.67 on pure noise. Three micelle claims in this
    project rested on it. A positive control (a planted micelle scores high) does NOT catch this; only
    a null control does.
    """
    import numpy as np
    from null_control import null

    biased, cyl, shell, fixed = null(radius=2.5, trials=400, seed=3)
    assert biased.mean() > 0.5, "regression guard: the old metric's bias should still be visible"
    assert abs(fixed.mean()) < 0.05, f"outward_c must be unbiased under the null, got {fixed.mean()}"
    assert abs(shell.mean() - 0.5) < 0.02, f"shell must be unbiased, got {shell.mean()}"
