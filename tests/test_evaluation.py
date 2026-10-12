from __future__ import annotations

import itertools

import networkx as nx
import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from entity_resolution_gate.evaluation import (
    boot_f1,
    codes,
    components,
    n_pairs,
    pair_table,
    prf_counts,
)

labels_st = st.lists(st.integers(0, 4), min_size=2, max_size=14)


def brute_prf(labels: list[int], ent: list[int]) -> tuple[float, float, float]:
    idx = list(itertools.combinations(range(len(labels)), 2))
    pred = {p for p in idx if labels[p[0]] == labels[p[1]]}
    true = {p for p in idx if ent[p[0]] == ent[p[1]]}
    tp = len(pred & true)
    p = tp / len(pred) if pred else 1.0
    r = tp / len(true) if true else 1.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


@given(labels_st, st.data())
def test_prf_counts_matches_brute_force(labels: list[int], data: st.DataObject) -> None:
    ent = data.draw(st.lists(st.integers(0, 4), min_size=len(labels), max_size=len(labels)))
    got = prf_counts(np.array(labels, dtype=np.int64), np.array(ent, dtype=np.int64))
    assert np.allclose(got, brute_prf(labels, ent))


def test_n_pairs_small_cases() -> None:
    assert n_pairs(np.array([0, 0, 0, 1, 2, 2], dtype=np.int64)) == 3 + 0 + 1


def test_perfect_and_singleton_clusterings() -> None:
    ent = np.array([0, 0, 1, 1, 1, 2], dtype=np.int64)
    assert prf_counts(ent, ent) == (1.0, 1.0, 1.0)
    p, r, f = prf_counts(
        np.arange(6, dtype=np.int64), ent
    )  # everything alone: nothing merged wrongly, nothing found
    assert (p, r, f) == (1.0, 0.0, 0.0)


@settings(max_examples=60)
@given(st.integers(2, 12), st.lists(st.tuples(st.integers(0, 11), st.integers(0, 11)), max_size=20))
def test_components_match_networkx(n: int, edges: list[tuple[int, int]]) -> None:
    edges = [(a, b) for a, b in edges if a < n and b < n]
    a = np.array([e[0] for e in edges], dtype=np.int64)
    b = np.array([e[1] for e in edges], dtype=np.int64)
    got = components(n, a, b)
    g = nx.Graph()
    g.add_nodes_from(range(n))
    g.add_edges_from(edges)
    want = {frozenset(c) for c in nx.connected_components(g)}
    have = {frozenset(np.where(got == lab)[0].tolist()) for lab in np.unique(got)}
    assert have == want


def test_codes_equal_labels_share_codes() -> None:
    c = codes(["x", "y", "x", "z"])
    assert c[0] == c[2] and len({int(v) for v in c}) == 3


@given(labels_st, st.data())
def test_unit_weight_bootstrap_equals_pairwise_f1(labels: list[int], data: st.DataObject) -> None:
    ent = data.draw(st.lists(st.integers(0, 4), min_size=len(labels), max_size=len(labels)))
    lab = np.array(labels, dtype=np.int64)
    e = codes(ent)
    names = [f"n{v}" for v in labels]
    table = pair_table(lab, e, names)
    w = np.ones(int(np.max(e)) + 1)
    assert abs(boot_f1(table, w) - prf_counts(lab, e)[2]) < 1e-9


def test_bootstrap_weight_zero_removes_an_entity() -> None:
    lab = np.array([0, 0, 1, 1], dtype=np.int64)
    ent = np.array([0, 0, 1, 1], dtype=np.int64)
    table = pair_table(lab, ent, ["a", "a", "b", "b"])
    assert boot_f1(table, np.array([2.0, 0.0])) == 1.0  # only entity 0 remains, found perfectly
