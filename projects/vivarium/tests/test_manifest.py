"""The manifest is the single source of truth for what this project runs. This test enforces it.

Without enforcement a manifest is a comment. Three things must hold, and each corresponds to a way
this directory has actually gone wrong:

  1. EVERY module is classified. A new simulation cannot appear un-tiered -- at one point eleven
     different things here could be called "the simulation" and a result was scored against the wrong
     one.
  2. ACTIVE never imports ARCHIVED. The production stack must not grow a dependency on a superseded
     one; that is how a retracted force law keeps influencing results.
  3. ACTIVE never imports ORACLE. An oracle is the independent known-answer case the ACTIVE stack is
     checked against. The moment production imports it, it stops being independent -- and
     `docs/WHY_THE_ORACLE_DOES_NOT_TRANSFER.md` measured why that matters: the oracle's vesicle is
     BOUGHT (beta = spontaneous curvature; set it to zero and the same code makes flat sheets), so
     importing it would import the answer.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

import manifest

HERE = pathlib.Path(__file__).resolve().parent.parent


def _modules():
    return {p.stem for p in HERE.glob("*.py")} - {"manifest"}


def _imports(mod):
    try:
        tree = ast.parse((HERE / f"{mod}.py").read_text())
    except (OSError, SyntaxError):
        return set()
    got = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            got |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            got.add(n.module.split(".")[0])
    return got


def test_every_module_is_classified():
    """A module with no tier is a simulation nobody has decided the status of."""
    listed = set().union(*manifest.TIERS.values())
    unclassified = sorted(_modules() - listed)
    assert not unclassified, (
        f"{len(unclassified)} module(s) missing from manifest.py: {unclassified}. "
        "Add each to ACTIVE, ORACLE, ARCHIVED or SUPPORT.")


def test_manifest_lists_no_module_that_was_deleted():
    """A stale entry makes the manifest describe a tree that no longer exists."""
    ghosts = sorted(set().union(*manifest.TIERS.values()) - _modules())
    assert not ghosts, f"manifest.py lists deleted modules: {ghosts}"


def test_the_tiers_do_not_overlap():
    seen, dupes = set(), []
    for tier, mods in manifest.TIERS.items():
        for m in mods:
            if m in seen:
                dupes.append(m)
            seen.add(m)
    assert not dupes, f"modules in more than one tier: {sorted(set(dupes))}"


@pytest.mark.parametrize("mod", sorted(manifest.ACTIVE))
def test_active_does_not_import_archived_or_oracle(mod):
    """The production stack stays independent of what it superseded and of what checks it."""
    bad_arch = sorted(_imports(mod) & manifest.ARCHIVED)
    bad_orac = sorted(_imports(mod) & manifest.ORACLE)
    assert not bad_arch, f"ACTIVE module {mod!r} imports ARCHIVED {bad_arch}"
    assert not bad_orac, (
        f"ACTIVE module {mod!r} imports ORACLE {bad_orac} — an oracle that production depends on is "
        "no longer an independent check")
