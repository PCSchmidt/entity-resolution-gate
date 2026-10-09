# entity-resolution-gate

Entity resolution with **graph-gated fusion**: similarity proposes merges, deterministic constraints decide whether they are allowed. Two records with different verified tax IDs can never end up in one cluster, whatever their name and address similarity.

**Status:** v0.1 scaffold on synthetic data only. Real USASpending / SAM.gov / EDGAR data and the 100k+ record benchmark are **not done** (largest run: 39k records). See [docs/RESULTS.md](docs/RESULTS.md).

## Pipeline

1. **Blocking** (DuckDB self-join): token-pair keys, Metaphone and 3-char prefix, so a single typo still leaves a shared key. Blocks over `max_block_size` are skipped *and logged*.
2. **Pairwise scoring**: `0.7 * name + 0.3 * address`, where name is max(Jaro-Winkler, token-sort ratio) after legal-suffix normalisation. Same non-null tax ID scores 1.0.
3. **Hard constraint**: a pair with two non-null, different tax IDs is dropped before scoring (`edge_blocked` in the audit log).
4. **Graph gate**: connected components, then Louvain splitting of any component that either holds two tax IDs or is sparse (density < 0.5, a chain of weak links). A tax-ID partition fallback guarantees no cluster is ever inconsistent.
5. **Audit log**: every blocked edge, accepted edge, skipped block and split, as JSON-serialisable events.

## Use

```bash
uv pip install -e ".[dev]"
python scripts/benchmark.py
```

```python
from entity_resolution_gate import generate, resolve, pairwise_prf
df = generate(1000, seed=2)          # rid, name, address, zip, tax_id, entity_id (truth)
resolved, audit = resolve(df)        # adds cluster_id
pairwise_prf(resolved)
```

## Checks

```bash
pytest          # incl. hypothesis: no cluster ever holds two tax IDs, any seed / trap rate / threshold
mypy src tests scripts   # strict
```

## Limits

- Threshold 0.93 was picked on synthetic seed 1; it will need re-tuning on real data.
- The synthetic name space is small (24 x 24 x 7 base names), so it saturates at 20k entities and distinct vendors collide; part of the drop at that size is the generator.
- "Trap" vendors share name and address with a differently-taxed twin; their records without a tax ID are inherently ambiguous and cap precision.
- No embeddings / pgvector stage, no executive-name or geographic features, no Splink comparison yet.
