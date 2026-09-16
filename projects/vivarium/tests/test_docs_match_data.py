"""Every headline number in SUMMARY.md and ROADMAP.md must equal the data that produced it.

This project's documentation has drifted from its own results repeatedly: two gates that disagreed
fourteen-fold on the same runs with no record of which one counted; a headline rate quoted from a
run whose states had been overwritten; SUMMARY declaring a gate settled while a later section of the
same file still called it undecided. None of that was caught by reading, because reading is how it
got there.

`CLAUDE.md`: "Every number in the writeup is generated, never typed." These tests are the mechanical
form of that rule -- the documented rate is recomputed from the TSV on every run, so a doc that drifts
from its data fails the suite rather than sitting there looking authoritative.
"""
import csv
import pathlib
import re

import pytest

import manifest
import vesicle_gate

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUMMARY = (ROOT / "SUMMARY.md").read_text(encoding="utf-8")
ROADMAP = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
GATE2 = ROOT / "docs" / "results" / "emerge_gate2.tsv"

# Column -> the name the docs use for that gate. `new_ckpts` is `vesicle_gate`, the live criterion.
GATES = {"enc_ckpts": "enclosure", "old_ckpts": "vesicle_call", "new_ckpts": "vesicle_gate"}


def _rates():
    """(hits per gate, n runs) recomputed from the append-only result file."""
    with GATE2.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert rows, f"{GATE2} is empty"
    return {col: sum(1 for r in rows if int(r[col]) > 0) for col in GATES}, len(rows)


# The docs state each rate in a fixed shape next to the gate's own name. These patterns PARSE that
# claim rather than grepping for a substring: a stale number elsewhere in the file must not satisfy
# them, which an `in` check would allow -- the first version of this test was fooled exactly that way.
SUMMARY_ROW = r"\|\s*\*?\*?`?{gate}`?\*?\*?[^|]*\|[^|]*\|[^|]*?(\d+)/(\d+)\s*—\s*(\d+)%"
ROADMAP_CELL = r"`?{gate}`?[^|]*?\*\*(\d+)/(\d+)\s*\((\d+)%\)\*\*"


def _claimed(text, pattern, gate):
    m = re.search(pattern.format(gate=re.escape(gate)), text)
    assert m, f"no parsable rate claimed for {gate!r} (pattern did not match)"
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


@pytest.mark.skipif(not GATE2.exists(), reason="gate comparison has not been run")
@pytest.mark.parametrize("col", list(GATES))
def test_summary_states_the_measured_rate_for_every_gate(col):
    """Each rate SUMMARY prints must equal the one recomputed from the TSV."""
    hits, n = _rates()
    hit, tot, pct = _claimed(SUMMARY, SUMMARY_ROW, GATES[col])
    assert (hit, tot) == (hits[col], n), f"SUMMARY.md claims {hit}/{tot} for {GATES[col]}, data says {hits[col]}/{n}"
    assert pct == round(100 * hits[col] / n), f"SUMMARY.md percentage for {GATES[col]} is {pct}%"


@pytest.mark.skipif(not GATE2.exists(), reason="gate comparison has not been run")
@pytest.mark.parametrize("col", list(GATES))
def test_roadmap_states_the_measured_rate_for_every_gate(col):
    """The roadmap must report all three gates on the same runs, so no row quotes only the flattering one."""
    hits, n = _rates()
    hit, tot, pct = _claimed(ROADMAP, ROADMAP_CELL, GATES[col])
    assert (hit, tot) == (hits[col], n), f"ROADMAP.md claims {hit}/{tot} for {GATES[col]}, data says {hits[col]}/{n}"
    assert pct == round(100 * hits[col] / n), f"ROADMAP.md percentage for {GATES[col]} is {pct}%"


@pytest.mark.skipif(not GATE2.exists(), reason="gate comparison has not been run")
def test_the_headline_is_the_strict_gate_not_the_flattering_one():
    """SUMMARY's section heading must carry `vesicle_gate`'s number, not enclosure's."""
    hits, n = _rates()
    m = re.search(r"### 3\. How often does it happen\? — \*\*(\d+) in (\d+)\*\*", SUMMARY)
    assert m, "SUMMARY.md has no parsable headline rate heading"
    assert (int(m.group(1)), int(m.group(2))) == (hits["new_ckpts"], n), (
        f"headline says {m.group(1)} in {m.group(2)}; vesicle_gate measured {hits['new_ckpts']}/{n}"
    )
    assert hits["new_ckpts"] != hits["enc_ckpts"], "gates agree; this test can no longer discriminate"


def test_the_gate_the_docs_name_is_the_gate_that_exists():
    """SUMMARY names `vesicle_gate.vesicle()`; it must be importable and be the scored one."""
    assert "vesicle_gate" in SUMMARY, "SUMMARY.md does not name the live gate"
    assert callable(vesicle_gate.vesicle)
    assert "vesicle_gate" in manifest.SUPPORT | manifest.ACTIVE, (
        "the live gate is not classified in manifest.py"
    )


def test_scope_documents_match_the_scope_flag():
    """`manifest.THREE_D` is the switch; the docs must say what it is actually set to."""
    if not manifest.THREE_D:
        assert "ARCHIVED — 3-D" in SUMMARY, "3-D is gated off but SUMMARY does not say so"
        assert "2-D only" in ROADMAP, "3-D is gated off but ROADMAP does not state the 2-D scope"
    else:
        assert "ARCHIVED — 3-D" not in SUMMARY, "3-D is enabled but SUMMARY calls it archived"
