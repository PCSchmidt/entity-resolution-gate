from __future__ import annotations

from typing import Any

import networkx as nx
import polars as pl
import pytest

from entity_resolution_gate.pipeline import AuditLog, Config, _split, resolve


def _frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    base = {"address": "", "zip": None, "tax_id": None}
    full = [{**base, **r, "rid": i} for i, r in enumerate(rows)]
    return pl.DataFrame(
        full, schema_overrides={"zip": pl.Utf8, "tax_id": pl.Utf8, "address": pl.Utf8}
    )


def _cfg(split: str) -> Config:
    return Config(w_name=1.0, w_addr=0.0, threshold=0.9, split=split)


def _ids_per_cluster(df: pl.DataFrame, split: str) -> list[set[str]]:
    out, _ = resolve(df, _cfg(split))
    groups: dict[int, set[str]] = {}
    for cid, tax in zip(out["cluster_id"], out["tax_id"], strict=True):
        groups.setdefault(cid, set())
        if tax:
            groups[cid].add(tax)
    return list(groups.values())


def _bridge() -> pl.DataFrame:
    # an untaxed record that looks like both registered companies chains them together
    return _frame(
        [
            {"name": "Alpha Trading", "tax_id": "X"},
            {"name": "Alpha Trading Co"},
            {"name": "Alpha Trading", "tax_id": "Y"},
        ]
    )


def test_without_the_split_a_chain_through_an_untaxed_record_breaks_the_rule() -> None:
    assert max(len(s) for s in _ids_per_cluster(_bridge(), "none")) == 2


@pytest.mark.parametrize("split", ["louvain", "tax_only"])
def test_the_split_restores_the_rule(split: str) -> None:
    assert max(len(s) for s in _ids_per_cluster(_bridge(), split)) <= 1


def test_unknown_split_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        resolve(_bridge(), _cfg("bogus"))


def test_sparse_chain_is_split_by_louvain_mode_only() -> None:
    g: nx.Graph[int] = nx.path_graph(8)
    for a, b in g.edges:
        g[a][b]["weight"] = 1.0
    tax: dict[int, str | None] = dict.fromkeys(range(8))
    assert len(_split(g, tax, AuditLog(), 0.5)) > 1  # density 7/28 is below 0.5
    assert len(_split(g, tax, AuditLog(), 0.0)) == 1  # the tax_only mode never looks at density


def test_default_mode_is_the_original_behaviour() -> None:
    assert Config().split == "louvain"
