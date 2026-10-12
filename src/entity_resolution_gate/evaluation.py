"""Pairwise clustering metrics and an entity-level bootstrap, used by the real-data study."""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt
from rapidfuzz import fuzz

IntArray = npt.NDArray[np.int64]
Table = dict[str, npt.NDArray[Any]]


def codes(values: list[Any]) -> IntArray:
    """Integer codes for arbitrary labels, so equal labels get equal codes."""
    _, inv = np.unique(np.array(values), return_inverse=True)
    return np.asarray(inv, dtype=np.int64).reshape(-1)


def n_pairs(x: IntArray) -> int:
    """Number of unordered pairs of items that share a label."""
    _, c = np.unique(x, return_counts=True)
    return int((c * (c - 1) // 2).sum())


def prf_counts(labels: IntArray, ent: IntArray) -> tuple[float, float, float]:
    """Pairwise precision, recall and F1 of cluster `labels` against entity codes `ent`."""
    pred, true = n_pairs(labels), n_pairs(ent)
    tp = n_pairs(labels * (int(np.max(ent)) + 1) + ent)
    p = tp / pred if pred else 1.0
    r = tp / true if true else 1.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def components(n: int, a: IntArray, b: IntArray) -> IntArray:
    """Connected-component label for each of `n` nodes given edges (a[k], b[k])."""
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j in zip(a.tolist(), b.tolist(), strict=True):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)
    return np.array([find(i) for i in range(n)], dtype=np.int64)


def pair_table(labels: IntArray, ent: IntArray, names: list[str]) -> Table:
    """Every pair that is a true match or a predicted match, with what the cuts need."""
    n = len(labels)
    same_cluster = labels[:, None] == labels[None, :]
    same_entity = ent[:, None] == ent[None, :]
    upper = np.triu(np.ones((n, n), dtype=bool), k=1)
    ii, jj = np.where((same_cluster | same_entity) & upper)
    pairs = list(zip(ii.tolist(), jj.tolist(), strict=True))
    return {
        "i": ii, "j": jj, "ea": ent[ii], "eb": ent[jj],
        "true": same_entity[ii, jj], "pred": same_cluster[ii, jj],
        "tsr": np.array([fuzz.token_set_ratio(names[a], names[b]) for a, b in pairs], dtype=float),
        "same_name": np.array([names[a] == names[b] for a, b in pairs], dtype=bool),
    }  # fmt: skip


def boot_f1(t: Table, w: npt.NDArray[np.float64]) -> float:
    """F1 for one bootstrap draw. `w[e]` is how many times entity e was drawn.

    A pair inside entity e counts w[e] times; a pair across entities a and b counts w[a] * w[b] times.
    With all weights equal to one this is the ordinary pairwise F1.
    """
    wa, wb = w[t["ea"]], w[t["eb"]]
    weight = np.where(t["ea"] == t["eb"], wa, wa * wb)
    tp = float((weight * (t["true"] & t["pred"])).sum())
    pred = float((weight * t["pred"]).sum())
    true = float((weight * t["true"]).sum())
    p = tp / pred if pred else 1.0
    r = tp / true if true else 1.0
    return 2 * p * r / (p + r) if p + r else 0.0


def rid_pairs_to_positions(pairs: list[tuple[int, int]], rids: list[int]) -> set[tuple[int, int]]:
    """Translate pairs of record ids into sorted pairs of row positions.

    Record ids are global across splits and need not equal row positions; `pair_table` and the cluster
    labels are positional. Comparing the two without translating silently mismatches them.
    """
    pos = {r: i for i, r in enumerate(rids)}
    return {(min(pos[a], pos[b]), max(pos[a], pos[b])) for a, b in pairs}


def bcubed_per_record(
    labels: IntArray, ent: IntArray
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """B-cubed precision and recall for every record.

    For record r: precision = (records in r's cluster that share r's entity) / (size of r's cluster);
    recall = (same count) / (size of r's entity). Unlike pairwise counts, an entity's weight grows
    linearly with its number of records, so one very large entity cannot dominate the score.
    """
    _, lab = np.unique(labels, return_inverse=True)
    lab = np.asarray(lab, dtype=np.int64).reshape(-1)
    cluster_size = np.bincount(lab)[lab].astype(np.float64)
    entity_size = np.bincount(ent)[ent].astype(np.float64)
    joint = lab * (int(np.max(ent)) + 1) + ent
    _, inv, cnt = np.unique(joint, return_inverse=True, return_counts=True)
    same = cnt[np.asarray(inv).reshape(-1)].astype(np.float64)
    return same / cluster_size, same / entity_size


def bcubed_f1(
    p_rec: npt.NDArray[np.float64],
    r_rec: npt.NDArray[np.float64],
    ent: IntArray | None = None,
    w: npt.NDArray[np.float64] | None = None,
) -> tuple[float, float, float]:
    """Mean per-record precision and recall and their F1; `w[e]` optionally weights records by entity."""
    weights = np.ones(len(p_rec)) if w is None or ent is None else w[ent]
    total = float(weights.sum())
    if total == 0.0:
        return 1.0, 1.0, 1.0
    p = float((weights * p_rec).sum() / total)
    r = float((weights * r_rec).sum() / total)
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)
