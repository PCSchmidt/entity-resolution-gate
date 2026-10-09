"""Seeded synthetic vendor records with typos, trading names, address drift and tax-ID traps."""

from __future__ import annotations

import random

import polars as pl

_STEMS = [
    "Aegis", "Boreal", "Cobalt", "Dunmore", "Evergreen", "Falcon", "Granite", "Harbor", "Ironside",
    "Juniper", "Keystone", "Lattice", "Meridian", "Northgate", "Orbital", "Pioneer", "Quantum",
    "Ridgeway", "Sentinel", "Talon", "Union", "Vanguard", "Westbrook", "Zenith",
]
_KINDS = ["Defense", "Aerospace", "Logistics", "Dynamics", "Systems", "Industries", "Technologies"]
_SUFFIX = ["LLC", "Inc", "Corp", "Co", "Ltd"]
_STREETS = ["Main St", "Oak Ave", "Industrial Pkwy", "Commerce Dr", "Harbor Rd", "Federal Way"]


def _typo(rng: random.Random, s: str) -> str:
    if len(s) < 4 or rng.random() < 0.4:
        return s
    i = rng.randrange(1, len(s) - 1)
    op = rng.choice(["drop", "swap", "dup"])
    if op == "drop":
        return s[:i] + s[i + 1 :]
    if op == "swap":
        return s[:i] + s[i + 1] + s[i] + s[i + 2 :]
    return s[:i] + s[i] + s[i:]


def generate(n_entities: int, seed: int = 0, trap_rate: float = 0.1) -> pl.DataFrame:
    """Records with columns rid, name, address, zip, tax_id (nullable), entity_id (truth)."""
    rng = random.Random(seed)
    rows: list[dict[str, object]] = []
    rid = 0
    entities: list[tuple[int, str, str, str, str | None]] = []
    for e in range(n_entities):
        base = f"{rng.choice(_STEMS)} {rng.choice(_STEMS)} {rng.choice(_KINDS)}"
        zipc = f"{rng.randrange(10000, 99999)}"
        addr = f"{rng.randrange(1, 9999)} {rng.choice(_STREETS)}"
        tax = f"{rng.randrange(10, 99)}-{rng.randrange(1000000, 9999999)}" if rng.random() < 0.6 else None
        entities.append((e, base, addr, zipc, tax))
        # Trap: a different legal entity with a near-identical name and a *different* tax id.
        if rng.random() < trap_rate:
            entities.append(
                (len(entities) + n_entities, base, addr, zipc,
                 f"{rng.randrange(10, 99)}-{rng.randrange(1000000, 9999999)}")
            )  # fmt: skip
    for e, base, addr, zipc, tax in entities:
        for _ in range(rng.choice([1, 1, 2, 2, 3])):
            name = _typo(rng, base)
            if rng.random() < 0.5:
                name += " " + rng.choice(_SUFFIX)
            if rng.random() < 0.15:
                name = name.upper()
            if rng.random() < 0.1:
                name = "The " + name
            rows.append(
                {
                    "rid": rid,
                    "name": name,
                    "address": _typo(rng, addr) if rng.random() < 0.3 else addr,
                    "zip": zipc if rng.random() < 0.9 else None,
                    "tax_id": tax if (tax and rng.random() < 0.8) else None,
                    "entity_id": e,
                }
            )
            rid += 1
    rng.shuffle(rows)
    return pl.DataFrame(rows, schema_overrides={"zip": pl.Utf8, "tax_id": pl.Utf8})
