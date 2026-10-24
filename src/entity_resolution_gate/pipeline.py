"""Two-stage resolution: blocking -> scored edges -> graph clustering behind hard constraints."""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from typing import Any

import duckdb
import jellyfish
import networkx as nx
import polars as pl
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

_LEGAL = {"llc", "inc", "corp", "co", "ltd", "the", "company", "corporation", "incorporated"}
_TOKEN = re.compile(r"[a-z0-9]+")


def normalise(name: str) -> str:
    return " ".join(t for t in _TOKEN.findall(name.lower()) if t not in _LEGAL)


BLOCKING_MODES = ("base", "squash", "squash_first", "squash_first_wide")
SPLIT_MODES = ("louvain", "tax_only", "none")


def block_keys(name: str, mode: str = "base") -> set[str]:
    """Token-pair keys (metaphone and 3-char prefix), so one typo still leaves a shared pair.

    Single-token keys are far too coarse at scale: they exceed the block-size cap and are skipped.
    Every mode other than `base` only adds keys, so its candidate set is a superset of the baseline's:
    `squash` adds keys on the name with spaces removed (spacing variants), `squash_first` also adds the
    first token (a short name against a longer one), `squash_first_wide` also builds pairs from six tokens.
    """
    if mode not in BLOCKING_MODES:
        raise ValueError(f"unknown blocking mode {mode!r}")
    norm = normalise(name)
    toks = norm.split()[: 6 if mode == "squash_first_wide" else 4]
    keys: set[str] = set()
    if len(toks) == 1:
        keys = {"m:" + jellyfish.metaphone(toks[0]), "p:" + toks[0][:3]}
    else:
        for a, b in itertools.combinations(toks, 2):
            keys.add(f"m:{jellyfish.metaphone(a)}|{jellyfish.metaphone(b)}")
            keys.add(f"p:{a[:3]}|{b[:3]}")
    if mode != "base":
        squashed = norm.replace(" ", "")
        if squashed:
            keys.add("s:" + squashed)
            keys.add("q:" + squashed[:6])
    if mode in ("squash_first", "squash_first_wide") and toks:
        keys.add("f:" + toks[0])
    return keys


@dataclass(frozen=True)
class Config:
    threshold: float = 0.93  # chosen on dev seed 1 (see docs/RESULTS.md)
    max_block_size: int = 200
    min_density: float = 0.5  # components sparser than this look like chains, not entities
    w_name: float = 0.7
    w_addr: float = 0.3
    blocking: str = "base"  # see block_keys; "base" reproduces the original behaviour
    tax_veto: bool = True  # two different non-null tax ids can never be one entity
    tax_match: bool = True  # two equal non-null tax ids are certain evidence of one entity
    tax_blocking: bool = False  # also propose every pair of records that share a tax id (needed for renames)
    name_score: str = "max"  # "max": larger of Jaro-Winkler and token-sort (original); "token_sort": token-sort only
    split: str = "louvain"  # graph step: "louvain" (original: split on tax conflict or sparse chain), "tax_only", "none"


@dataclass
class AuditLog:
    events: list[dict[str, Any]] = field(default_factory=list)

    def add(self, kind: str, **kw: Any) -> None:
        self.events.append({"kind": kind, **kw})


def candidate_pairs(df: pl.DataFrame, cfg: Config, log: AuditLog) -> list[tuple[int, int]]:
    rows = [(r, k) for r, n in zip(df["rid"], df["name"], strict=True) for k in block_keys(n, cfg.blocking)]
    if cfg.tax_blocking:
        rows += [(r, "id:" + t) for r, t in zip(df["rid"], df["tax_id"], strict=True) if t]
    keys = pl.DataFrame(rows, schema={"rid": pl.Int64, "k": pl.Utf8}, orient="row")
    con = duckdb.connect()
    con.register("keys", keys.to_arrow())
    oversize = con.execute(
        "SELECT k, count(*) AS c FROM keys GROUP BY k HAVING c > ?", [cfg.max_block_size]
    ).fetchall()
    for k, c in oversize:
        log.add("block_skipped", key=k, size=c)
    pairs = con.execute(
        """
        WITH ok AS (SELECT k FROM keys GROUP BY k HAVING count(*) <= ?)
        SELECT DISTINCT a.rid, b.rid FROM keys a JOIN keys b ON a.k = b.k AND a.rid < b.rid
        WHERE a.k IN (SELECT k FROM ok)
        """,
        [cfg.max_block_size],
    ).fetchall()
    return sorted((int(a), int(b)) for a, b in pairs)  # fixed edge order: Louvain depends on it


def pair_score(a: dict[str, Any], b: dict[str, Any], cfg: Config) -> float:
    if cfg.tax_match and a["tax_id"] and a["tax_id"] == b["tax_id"]:
        return 1.0  # same verified tax id: positive evidence, independent of spelling
    na, nb = normalise(a["name"]), normalise(b["name"])
    tsr = fuzz.token_sort_ratio(na, nb) / 100.0
    name = tsr if cfg.name_score == "token_sort" else max(JaroWinkler.similarity(na, nb), tsr)
    if not (a["address"] and b["address"]):
        return name  # a missing address is no evidence either way (two empty strings are not a match)
    addr = fuzz.ratio(a["address"].lower(), b["address"].lower()) / 100.0
    if a["zip"] and b["zip"] and a["zip"] != b["zip"]:
        addr *= 0.5
    return cfg.w_name * name + cfg.w_addr * addr


def contradicts(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Hard negative constraint: two verified, different tax ids can never be one entity."""
    return bool(a["tax_id"] and b["tax_id"] and a["tax_id"] != b["tax_id"])


def _consistent(nodes: set[int], tax: dict[int, str | None]) -> bool:
    return len({tax[n] for n in nodes if tax[n]}) <= 1


def _split(
    g: nx.Graph[int], tax: dict[int, str | None], log: AuditLog, min_density: float, depth: int = 0
) -> list[set[int]]:
    nodes = set(g.nodes)
    chained = len(nodes) > 3 and nx.density(g) < min_density
    if _consistent(nodes, tax) and not chained:
        return [nodes]
    if depth < 4:
        parts = [set(c) for c in nx.community.louvain_communities(g, weight="weight", seed=0)]
        if len(parts) > 1:
            log.add(
                "component_split", method="louvain", depth=depth, size=len(nodes), parts=len(parts),
                reason="tax_conflict" if not _consistent(nodes, tax) else "sparse_chain",
            )
            out: list[set[int]] = []
            for part in parts:
                out.extend(_split(g.subgraph(part).copy(), tax, log, min_density, depth + 1))
            return out
    if _consistent(nodes, tax):
        return [nodes]  # sparse but unsplittable and tax-consistent: keep
    # Guaranteed fallback: partition by tax id; untaxed nodes join the id with most edge weight.
    groups: dict[str, set[int]] = {}
    for n in nodes:
        t = tax[n]
        if t:
            groups.setdefault(t, set()).add(n)
    loose = [n for n in nodes if not tax[n]]
    singles: list[set[int]] = []
    for n in loose:
        weight = {t: sum(g[n][m]["weight"] for m in members if g.has_edge(n, m)) for t, members in groups.items()}
        best = max(weight, key=lambda t: weight[t]) if weight else None
        if best is not None and weight[best] > 0:
            groups[best].add(n)
        else:
            singles.append({n})
    log.add("component_split", method="tax_partition", depth=depth, size=len(nodes), parts=len(groups) + len(singles))
    return list(groups.values()) + singles


def resolve(df: pl.DataFrame, cfg: Config | None = None) -> tuple[pl.DataFrame, AuditLog]:
    """Returns (df with `cluster_id`, audit log). Every merge is traceable to scored edges."""
    cfg = cfg or Config()
    if cfg.split not in SPLIT_MODES:
        raise ValueError(f"unknown split mode {cfg.split!r}")
    # rid is the record key: a duplicate would silently merge two records' tax IDs into one node
    if df["rid"].null_count():
        raise ValueError("`rid` must not contain nulls")
    if df["rid"].n_unique() != df.height:
        dups = df.filter(df["rid"].is_duplicated())["rid"].unique().sort().head(5).to_list()
        raise ValueError(f"`rid` must be unique; duplicated values include {dups}")
    log = AuditLog()
    rec = {int(r["rid"]): r for r in df.iter_rows(named=True)}
    tax = {rid: (r["tax_id"] if cfg.tax_veto else None) for rid, r in rec.items()}
    g: nx.Graph[int] = nx.Graph()
    g.add_nodes_from(rec)
    pairs = candidate_pairs(df, cfg, log)
    log.add("candidates", n=len(pairs))
    for a, b in pairs:
        if cfg.tax_veto and contradicts(rec[a], rec[b]):
            log.add("edge_blocked", a=a, b=b, reason="tax_id_contradiction")
            continue
        s = pair_score(rec[a], rec[b], cfg)
        if s >= cfg.threshold:
            g.add_edge(a, b, weight=s)
            log.add("edge_accepted", a=a, b=b, score=round(s, 4))
    assignment: dict[int, int] = {}
    cid = 0
    for comp in nx.connected_components(g):
        if cfg.split == "none":  # ablation: connected components of the thresholded graph, no splitting
            parts = [set(comp)]
        else:  # "tax_only" switches the sparse-chain criterion off (density is never below 0)
            parts = _split(g.subgraph(comp).copy(), tax, log, cfg.min_density if cfg.split == "louvain" else 0.0)
        for part in parts:
            for n in part:
                assignment[n] = cid
            cid += 1
    out = df.with_columns(pl.col("rid").replace_strict(assignment, return_dtype=pl.Int64).alias("cluster_id"))
    return out, log


def pairwise_prf(resolved: pl.DataFrame) -> tuple[float, float, float]:
    """Pairwise precision / recall / F1 against `entity_id`."""

    def pairs(col: str) -> int:
        counts = resolved.group_by(col).len()["len"].to_list()
        return int(sum(c * (c - 1) // 2 for c in counts))

    both = resolved.group_by(["cluster_id", "entity_id"]).len()["len"].to_list()
    tp = int(sum(c * (c - 1) // 2 for c in both))
    pred, true = pairs("cluster_id"), pairs("entity_id")
    p = tp / pred if pred else 1.0
    r = tp / true if true else 1.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)
