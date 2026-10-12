from __future__ import annotations

import itertools

import jellyfish
import polars as pl
import pytest
from hypothesis import given
from hypothesis import strategies as st

from entity_resolution_gate.pipeline import (
    BLOCKING_MODES,
    AuditLog,
    Config,
    block_keys,
    candidate_pairs,
    normalise,
)

names_st = st.text(alphabet="abcdefgh ijklm0123.,&", min_size=0, max_size=40)


def original_block_keys(name: str) -> set[str]:
    """The blocking function as it was before modes existed, kept here as the reference."""
    toks = normalise(name).split()[:4]
    keys: set[str] = set()
    if len(toks) == 1:
        return {"m:" + jellyfish.metaphone(toks[0]), "p:" + toks[0][:3]}
    for a, b in itertools.combinations(toks, 2):
        keys.add(f"m:{jellyfish.metaphone(a)}|{jellyfish.metaphone(b)}")
        keys.add(f"p:{a[:3]}|{b[:3]}")
    return keys


@given(names_st)
def test_base_mode_is_unchanged(name: str) -> None:
    assert block_keys(name, "base") == original_block_keys(name)
    assert block_keys(name) == original_block_keys(name)


@given(names_st, st.sampled_from(BLOCKING_MODES))
def test_every_mode_only_adds_keys(name: str, mode: str) -> None:
    assert block_keys(name, "base") <= block_keys(name, mode)


@given(names_st, st.sampled_from(BLOCKING_MODES))
def test_identical_normalised_names_always_share_a_key(name: str, mode: str) -> None:
    variant = name.upper() + " ,"  # normalises to the same string
    if normalise(name).split():
        assert block_keys(name, mode) & block_keys(variant, mode)


def test_modes_are_nested() -> None:
    n = "alpha beta gamma delta epsilon zeta eta"
    sizes = [len(block_keys(n, m)) for m in BLOCKING_MODES]
    assert sizes == sorted(sizes)


def test_unknown_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        block_keys("acme", "nonsense")


def test_squash_catches_spacing_variants_that_base_misses() -> None:
    a, b = "A123 Systems", "a123systems"
    assert not block_keys(a, "base") & block_keys(b, "base")
    assert block_keys(a, "squash") & block_keys(b, "squash")


def test_first_token_catches_short_against_long_name() -> None:
    a, b = "ABT", "ABT Associates"
    assert not block_keys(a, "base") & block_keys(b, "base")
    assert not block_keys(a, "squash") & block_keys(b, "squash")
    assert block_keys(a, "squash_first") & block_keys(b, "squash_first")


def test_wide_window_uses_tokens_beyond_the_fourth() -> None:
    a = "one two three four five six"
    b = "uno dos tres quatro five six"  # shares only tokens 5 and 6
    assert not block_keys(a, "squash_first") & block_keys(b, "squash_first")
    assert block_keys(a, "squash_first_wide") & block_keys(b, "squash_first_wide")


def _frame(names: list[str]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "rid": list(range(len(names))),
            "name": names,
            "address": [""] * len(names),
            "zip": [None] * len(names),
            "tax_id": [None] * len(names),
        },
        schema_overrides={"zip": pl.Utf8, "tax_id": pl.Utf8},
    )


def test_candidate_pairs_grow_monotonically_with_mode() -> None:
    names = [
        "A123 Systems",
        "a123systems",
        "ABT",
        "ABT Associates",
        "Acme Tooling",
        "Acme Tooling Inc",
    ]
    counts = []
    previous: set[tuple[int, int]] = set()
    for mode in BLOCKING_MODES:
        pairs = set(candidate_pairs(_frame(names), Config(blocking=mode), AuditLog()))
        assert previous <= pairs
        previous = pairs
        counts.append(len(pairs))
    assert counts == sorted(counts)
    assert (0, 1) in previous and (2, 3) in previous


def test_candidate_pairs_are_returned_in_sorted_order() -> None:
    names = [
        "Acme Tooling",
        "Acme Tooling Inc",
        "Acme Tool",
        "Borealis Marine",
        "Borealis Marine Co",
    ] * 3
    pairs = candidate_pairs(_frame(names), Config(blocking="squash_first"), AuditLog())
    assert pairs == sorted(pairs)


@given(names_st, names_st)
def test_token_sort_score_never_exceeds_the_default_score(a: str, b: str) -> None:
    from entity_resolution_gate.pipeline import pair_score

    ra = {"name": a, "address": "", "zip": None, "tax_id": None}
    rb = {"name": b, "address": "", "zip": None, "tax_id": None}
    hi = pair_score(ra, rb, Config(w_name=1.0, w_addr=0.0))
    lo = pair_score(ra, rb, Config(w_name=1.0, w_addr=0.0, name_score="token_sort"))
    assert lo <= hi + 1e-12


def test_long_shared_prefix_scores_lower_under_token_sort() -> None:
    from entity_resolution_gate.pipeline import pair_score

    ra = {"name": "advanced technology systems", "address": "", "zip": None, "tax_id": None}
    rb = {"name": "advanced technology solutions", "address": "", "zip": None, "tax_id": None}
    default = pair_score(ra, rb, Config(w_name=1.0, w_addr=0.0))
    tsr = pair_score(ra, rb, Config(w_name=1.0, w_addr=0.0, name_score="token_sort"))
    assert tsr < default
