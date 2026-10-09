from __future__ import annotations

import json

import polars as pl
from hypothesis import given, settings
from hypothesis import strategies as st

from entity_resolution_gate import Config, generate, pairwise_prf, resolve
from entity_resolution_gate.pipeline import block_keys, contradicts, normalise


def test_normalise_and_blocking_tolerate_typos() -> None:
    assert normalise("The Aegis Defense LLC") == "aegis defense"
    assert block_keys("Aegis Defense") & block_keys("Aegsi Defense Inc")


def test_contradiction_rule() -> None:
    a = {"tax_id": "11-1111111"}
    assert contradicts(a, {"tax_id": "22-2222222"})
    assert not contradicts(a, {"tax_id": "11-1111111"})
    assert not contradicts(a, {"tax_id": None})


def test_identical_names_with_different_tax_ids_never_merge() -> None:
    df = pl.DataFrame(
        {
            "rid": [0, 1, 2],
            "name": ["Acme Defense Systems", "Acme Defense Systems", "Acme Defense Systems"],
            "address": ["1 Main St"] * 3,
            "zip": ["12345"] * 3,
            "tax_id": ["11-1111111", "22-2222222", None],
            "entity_id": [0, 1, 0],
        }
    )
    out, log = resolve(df)
    ids = dict(zip(out["rid"], out["cluster_id"], strict=True))
    assert ids[0] != ids[1]
    assert any(e["kind"] == "edge_blocked" for e in log.events)


def assert_gate_invariants(out: pl.DataFrame) -> None:
    assert out["cluster_id"].null_count() == 0 and out.height == out["rid"].n_unique()
    for _, g in out.group_by("cluster_id"):
        assert len({t for t in g["tax_id"].to_list() if t}) <= 1


@settings(max_examples=15, deadline=None)
@given(st.integers(0, 10_000), st.floats(0.0, 0.6))
def test_no_cluster_ever_holds_two_tax_ids(seed: int, trap: float) -> None:
    out, _ = resolve(generate(60, seed=seed, trap_rate=trap), Config(threshold=0.6))
    assert_gate_invariants(out)


def test_low_threshold_forces_splitting_path_but_stays_consistent() -> None:
    out, log = resolve(generate(80, seed=7, trap_rate=0.5), Config(threshold=0.2))
    assert_gate_invariants(out)
    assert any(e["kind"] == "component_split" for e in log.events)


def test_deterministic_and_audit_log_is_json() -> None:
    df = generate(100, seed=3)
    a, la = resolve(df)
    b, _ = resolve(df)
    assert a["cluster_id"].to_list() == b["cluster_id"].to_list()
    for e in la.events:
        json.dumps(e)


def test_quality_on_easy_synthetic_data() -> None:
    p, r, f1 = pairwise_prf(resolve(generate(300, seed=1))[0])
    assert p > 0.75 and r > 0.9 and 0 <= f1 <= 1


def test_prf_perfect_and_singletons() -> None:
    df = pl.DataFrame({"cluster_id": [0, 0, 1], "entity_id": [5, 5, 6]})
    assert pairwise_prf(df) == (1.0, 1.0, 1.0)
    solo = pl.DataFrame({"cluster_id": [0, 1], "entity_id": [5, 5]})
    assert pairwise_prf(solo)[1] == 0.0
