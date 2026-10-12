from __future__ import annotations

from typing import Any

import polars as pl

from entity_resolution_gate.pipeline import Config, pair_score, resolve


def _frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    base = {"address": "", "zip": None, "tax_id": None}
    full = [{**base, **r, "rid": i} for i, r in enumerate(rows)]
    return pl.DataFrame(
        full, schema_overrides={"zip": pl.Utf8, "tax_id": pl.Utf8, "address": pl.Utf8}
    )


def _clusters(df: pl.DataFrame, cfg: Config) -> list[int]:
    out, _ = resolve(df, cfg)
    return out.sort("rid")["cluster_id"].to_list()


def name_only(tax_veto: bool = True, tax_match: bool = True, tax_blocking: bool = False) -> Config:
    return Config(
        w_name=1.0, w_addr=0.0, threshold=0.9,
        tax_veto=tax_veto, tax_match=tax_match, tax_blocking=tax_blocking,
    )  # fmt: skip


def test_veto_keeps_identical_names_with_different_ids_apart() -> None:
    df = _frame([{"name": "Acme Tooling", "tax_id": "A"}, {"name": "Acme Tooling", "tax_id": "B"}])
    on = _clusters(df, name_only())
    off = _clusters(df, name_only(tax_veto=False, tax_blocking=True))
    assert on[0] != on[1]
    assert off[0] == off[1]  # without the veto the two registrations merge


def test_matching_ids_link_records_whose_names_share_nothing() -> None:
    df = _frame(
        [{"name": "Borealis Marine", "tax_id": "Z"}, {"name": "Quartz Holdings", "tax_id": "Z"}]
    )
    assert len(set(_clusters(df, name_only(tax_blocking=True)))) == 1
    assert len(set(_clusters(df, name_only(tax_match=False, tax_blocking=True)))) == 2


def test_switches_are_independent() -> None:
    df = _frame(
        [
            {"name": "Borealis Marine", "tax_id": "Z"},
            {"name": "Quartz Holdings", "tax_id": "Z"},
            {"name": "Acme Tooling", "tax_id": "A"},
            {"name": "Acme Tooling", "tax_id": "B"},
        ]
    )
    both_off = _clusters(df, name_only(tax_veto=False, tax_match=False, tax_blocking=True))
    assert both_off[0] != both_off[1] and both_off[2] == both_off[3]
    match_only = _clusters(df, name_only(tax_veto=False, tax_blocking=True))
    assert match_only[0] == match_only[1] and match_only[2] == match_only[3]
    veto_only = _clusters(df, name_only(tax_match=False, tax_blocking=True))
    assert veto_only[0] != veto_only[1] and veto_only[2] != veto_only[3]


def test_missing_address_is_not_evidence() -> None:
    cfg = Config()  # default weights 0.7 / 0.3
    a = {"name": "Acme Tooling", "address": "", "zip": None, "tax_id": None}
    b = {"name": "Acme Toolings", "address": "", "zip": None, "tax_id": None}
    name_only = pair_score(a, b, Config(w_name=1.0, w_addr=0.0))
    assert pair_score(a, b, cfg) == name_only  # two empty addresses add nothing
    c = {**b, "address": "1 High Street London"}
    assert (
        pair_score({**a, "address": "1 High Street London"}, c, cfg)
        > pair_score(a, c, cfg) * 0 + 0.7 * name_only
    )


def test_defaults_enable_everything() -> None:
    cfg = Config()
    assert cfg.tax_veto and cfg.tax_match


def test_equal_ids_are_not_even_proposed_without_tax_blocking() -> None:
    """Blocking looks only at names unless tax_blocking is on, so a rename never reaches the scorer."""
    from entity_resolution_gate.pipeline import AuditLog, candidate_pairs

    df = _frame(
        [{"name": "Borealis Marine", "tax_id": "Z"}, {"name": "Quartz Holdings", "tax_id": "Z"}]
    )
    assert candidate_pairs(df, name_only(), AuditLog()) == []
    assert candidate_pairs(df, name_only(tax_blocking=True), AuditLog()) == [(0, 1)]
