import math
from aisr.analysis.coverage.collector import ExecutionMatrix
from aisr.analysis.coverage.jacoco import Line
from aisr.localization.base import Spectrum, build_spectra
from aisr.localization.dstar import dstar
from aisr.localization.jaccard import jaccard
from aisr.localization.ochiai import ochiai
from aisr.localization.tarantula import tarantula
from aisr.localization.aggregator import FaultLocalizer, aggregate
from aisr.testing.results import Outcome

# ef=2 ep=1 nf=0 np=3  =>  F=2, P=4
S = Spectrum(ef=2, ep=1, nf=0, np=3)

def test_ochiai_formula():
    assert math.isclose(ochiai(S), 2 / math.sqrt(2 * 3))

def test_tarantula_formula():
    assert math.isclose(tarantula(S), (2 / 2) / ((2 / 2) + (1 / 4)))

def test_jaccard_formula():
    assert math.isclose(jaccard(S), 2 / (2 + 1))

def test_dstar_formula_and_unbounded_case():
    assert math.isclose(dstar(S), 4 / (1 + 0))
    assert dstar(Spectrum(2, 0, 0, 3)) > 1e6          # denominator 0 -> ranked first, finite
    assert dstar(Spectrum(0, 5, 2, 0)) == 0.0

def test_zero_division_safe():
    z = Spectrum(0, 0, 0, 0)
    assert ochiai(z) == tarantula(z) == jaccard(z) == dstar(z) == 0.0

def matrix():
    m = ExecutionMatrix()
    a, b, c = Line("A.java", 1), Line("A.java", 2), Line("B.java", 9)
    m.coverage = {"t_fail": {a, b}, "t_p1": {a}, "t_p2": {a, c}}
    m.outcomes = {"t_fail": Outcome.FAIL, "t_p1": Outcome.PASS, "t_p2": Outcome.PASS}
    m.methods = {"A.java": [(1, "A", "f")], "B.java": [(9, "B", "g")]}
    return m, (a, b, c)

def test_build_spectra_counts():
    m, (a, b, c) = matrix()
    sp = build_spectra(m)
    assert (sp[a].ef, sp[a].ep, sp[a].nf, sp[a].np) == (1, 2, 0, 0)
    assert (sp[b].ef, sp[b].ep, sp[b].nf, sp[b].np) == (1, 0, 0, 2)
    assert (sp[c].ef, sp[c].ep, sp[c].nf, sp[c].np) == (0, 1, 1, 1)

def test_ranking_puts_failing_only_line_first_and_normalises():
    m, (a, b, c) = matrix()
    r = FaultLocalizer("ochiai").rank(m)
    assert (r[0].file, r[0].line, r[0].rank, r[0].score) == ("A.java", 2, 1, 1.0)
    assert r[-1].line == 9 and r[-1].score == 0.0
    assert all(0 <= s.score <= 1 for s in r)

def test_ties_share_rank():
    m, _ = matrix()
    m.coverage["t_fail"] = {Line("A.java", 1), Line("A.java", 2)}
    m.coverage["t_p1"] = set(); m.coverage["t_p2"] = set()
    r = FaultLocalizer("tarantula").rank(m)
    assert [s.rank for s in r] == [1, 1]

def test_no_failing_tests_gives_empty_ranking():
    m, _ = matrix(); m.outcomes["t_fail"] = Outcome.PASS
    assert FaultLocalizer().rank(m) == []

def test_aggregate_levels():
    m, _ = matrix()
    r = FaultLocalizer().rank(m)
    assert aggregate(r, "file")[0][0] == "A.java"
    assert aggregate(r, "method")[0][0] == "A#f"

def test_unknown_metric():
    import pytest
    with pytest.raises(ValueError): FaultLocalizer("nope")
