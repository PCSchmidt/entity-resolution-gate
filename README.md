# entity-resolution-gate — deciding which records are the same company, with hard rules that similarity can never override

**Status: v0.1, portfolio project.** Blocking, scoring, the graph gate, an audit log, a synthetic data generator and a benchmark are built and tested. The synthetic benchmark reaches 39,369 records, and a **real-data study on federal-contractor names** has now been run under a protocol written in advance: the tuned pipeline scored F1 0.763 against 0.732 for a tuned plain fuzzy matcher, a narrow edge whose interval just clears zero, and blocking turned out to be the recall bottleneck ([Results](#results)). The hard tax-ID rule could not be tested on public data, and the 100k+ record benchmark is not done.

```text
$ python examples/demo.py                      # 7 vendor records; entity_id is the hidden truth
 rid  name                      tax_id      entity_id  cluster_id
  0   Aegis Falcon Defense LLC  11-1111111  A          0
  2   AEGIS FALCON DEFENSE INC  11-1111111  A          0
  1   Aegis Falcon Defence      null        A          1      <- no tax ID: looks like A and B equally
  3   Aegis Falcon Defense LLC  22-2222222  B          1
  4   Boreal Systems Inc        null        C          2
  5   The Boreal Systems        null        C          2
  6   Zenith Logistics Co       33-3333333  D          3

audit log (what the gate decided and why):
  {'kind': 'edge_blocked', 'a': 2, 'b': 3, 'reason': 'tax_id_contradiction'}
  {'kind': 'edge_blocked', 'a': 0, 'b': 3, 'reason': 'tax_id_contradiction'}
  {'kind': 'component_split', 'method': 'louvain', 'depth': 0, 'size': 4, 'parts': 2, 'reason': 'tax_conflict'}
  ... plus 5 accepted edges
```

*Real output of [examples/demo.py](examples/demo.py), table lightly reformatted. Look at record 1: the gate never put A's and B's verified IDs together (records 0 and 2 stayed away from record 3), but record 1 has no tax ID and matches both look-alike companies equally well, so it was grouped with B, which is wrong. The gate guarantees clusters never contradict a known ID; it cannot guarantee correctness when the data does not decide. That limit is deliberate to show, and it is discussed below.*

## What is this? (plain-language overview)

Organisations keep records of the same company in many places, spelled differently: "Aegis Falcon Defense LLC", "AEGIS FALCON DEFENSE INC", "Aegis Falcon Defence". To analyse suppliers, contracts or ownership you first have to decide which records refer to the **same real-world entity**. That is entity resolution, and it fails in two opposite ways:

- **Missed matches:** the same company counted as three, so spend looks smaller and relationships are lost.
- **False merges:** two *different* companies with similar names fused into one, which is worse: it can attribute one firm's contracts to another.

Fuzzy name matching alone cannot tell "Aegis Falcon Defense LLC" with one tax ID from "Aegis Falcon Defense LLC" with another. They are different legal entities that happen to look identical.

entity-resolution-gate adds a **hard rule that similarity can never override**: if two records both carry a verified identifier (here, a tax ID) and the identifiers differ, they can never end up in the same group. Everything else is soft evidence, scored and thresholded; that rule is a gate:

1. **Candidate pairs.** Records are compared only if they share a block key built from sounds and prefixes of their name words, so you do not compare every record to every other.
2. **Hard constraint.** A pair with two different tax IDs is dropped immediately and logged.
3. **Score.** Remaining pairs get a similarity score from name and address. A shared tax ID scores 1.0.
4. **Graph and gate.** Pairs above the threshold become edges; connected groups are checked. A group holding two tax IDs, or a group that is only a thin chain of weak links, is split by community detection; if that cannot fix it, a final fallback splits by tax ID.
5. **Audit log.** Every blocked pair, accepted pair, skipped block and split is recorded.

**What it is not.** It is not a learned matcher, and it does not use embeddings, executive names or geography yet. It does not decide which of two ambiguous records is right; it only guarantees it will not break a rule it was told is absolute.

### Who it is for, and when it earns its place

| If you are... | the project gives you... |
| --- | --- |
| working with supplier, vendor or contract data from several systems | a way to merge records while guaranteeing identifiers are never contradicted |
| an analyst who must explain a merge | an audit log saying why each pair was joined, blocked or split |
| building a matching pipeline | a pattern of candidate blocking, scoring, then deterministic constraints on a graph |
| evaluating matchers | a seeded synthetic generator with known ground truth, trap cases included |

It is a poor fit if your records have no reliable identifier to constrain on, if you need a learned or probabilistic matcher today, or if you need results proven on real data.

### Why constraints on the graph, and not a better similarity score?

Any similarity score can be fooled by two look-alike companies. A rule that holds regardless of the score is the only thing that makes a merge guarantee possible. The score decides what is *likely*; the constraints decide what is *allowed*.

**What's real and what's not.** The pipeline, the constraints, the audit log and the benchmark run today and are tested, including a property test that no cluster ever contains two tax IDs. The scale and constraint claims rest on **synthetic data**. A name-only study on real USAspending names exists ([docs/RESULTS_REAL.md](docs/RESULTS_REAL.md)), but public data has no tax IDs or alternate-name addresses, so the constraint and address scoring were not exercised on real data.

## At a glance

| | |
| --- | --- |
| Input | a table with `rid`, `name`, `address`, `zip`, `tax_id` (nullable) |
| Output | the same table plus `cluster_id`, and an audit log |
| Guarantee | no cluster contains two different non-null tax IDs (property-tested over seeds, trap rates and thresholds) |
| Measured (synthetic, held-out seeds) | F1 0.91 at 2,000 records, 0.80 at 39,000 records; 0 tax-ID violations in every run |
| Measured (real USAspending names, name-only) | F1 0.763 against 0.732 for tuned plain fuzzy matching (difference +0.031, 95% interval +0.004 to +0.059); 17% of true pairs are renames no string method finds |
| Speed | 39,369 records in 6.7 s on one machine, single thread |
| Stack | Polars, DuckDB, NetworkX, RapidFuzz, jellyfish (Metaphone) |
| Tests | 15, including property-based; `mypy --strict`; ruff |

## Architecture at a glance

```mermaid
flowchart TD
    REC[/"vendor records<br>name, address, zip, tax_id"/]
    subgraph cand["1 · Candidate pairs"]
        KEYS["token-pair block keys<br>Metaphone + 3-char prefix"]
        JOIN["DuckDB self-join on key<br>oversize blocks skipped and logged"]
        KEYS --> JOIN
    end
    subgraph pair["2 · Pairwise decision"]
        HARD{"both tax IDs present<br>and different?"}
        SCORE["score = 0.7 name + 0.3 address<br>same tax ID scores 1.0"]
        THR{"score ≥ threshold?"}
    end
    subgraph clus["3 · Graph gate"]
        CC["connected components"]
        CHK{"two tax IDs in one component,<br>or sparse chain<br>density below 0.5?"}
        LOU["Louvain split<br>recursive"]
        FALL["fallback: partition by tax ID"]
    end
    OUT(["cluster_id per record<br>no cluster holds two tax IDs"])
    AUDIT[("audit log<br>blocked edges, accepted edges,<br>skipped blocks, splits")]
    REC --> KEYS
    JOIN --> HARD
    HARD -- "yes: never merge" --> AUDIT
    HARD -- "no" --> SCORE --> THR
    THR -- "yes: add edge" --> CC
    THR -- "no" --> AUDIT
    CC --> CHK
    CHK -- "no" --> OUT
    CHK -- "yes" --> LOU --> CHK
    LOU -.->|"cannot split further"| FALL
    FALL --> OUT
    CC -.-> AUDIT
    LOU -.-> AUDIT
    classDef det fill:#e8f1fb,stroke:#2f6db5,color:#102a43
    classDef bad fill:#fde8e8,stroke:#c0392b,color:#4a1010
    classDef ok fill:#e3f5e8,stroke:#2e8b57,color:#0f3b21
    classDef io fill:#f2f2f2,stroke:#666,color:#222
    class KEYS,JOIN,SCORE,CC,LOU,FALL,HARD,THR,CHK det
    class OUT ok
    class AUDIT bad
    class REC io
    style cand fill:#f4f8fd,stroke:#2f6db5,color:#102a43
    style pair fill:#f4f8fd,stroke:#2f6db5,color:#102a43
    style clus fill:#f4f8fd,stroke:#2f6db5,color:#102a43
```

*There is no learned model in this version: the "soft" step is a hand-built similarity score. What makes it a gated system is that the tax-ID rule and the graph check hold whatever that score says, and a later learned or embedding-based scorer could replace the score without touching the gate.*

## Quickstart

```bash
git clone https://github.com/PCSchmidt/entity-resolution-gate && cd entity-resolution-gate
uv venv && uv pip install -e ".[dev]"

python examples/demo.py              # the output shown above
python scripts/benchmark.py          # the held-out synthetic table below
pytest -q                            # 8 passed
```

```python
from entity_resolution_gate import generate, resolve, pairwise_prf

df = generate(1000, seed=2)          # rid, name, address, zip, tax_id, entity_id (truth)
resolved, audit = resolve(df)        # adds cluster_id; audit.events lists every decision
pairwise_prf(resolved)               # (precision, recall, F1) against entity_id
```

## Approach: why it is built this way

- **Allowed versus likely.** Similarity says what is likely; constraints say what is allowed. Only the second can be guaranteed.
- **Guarantee by construction, then test it.** The fallback in the graph gate makes an inconsistent cluster impossible; a property test tries to break that over many seeds, trap rates and thresholds.
- **Explainable merges.** Each decision lands in an audit log, so a reviewer can see why two records are, or are not, together.
- **Honest about ambiguity.** Where the data does not decide (record 1 above), the gate does not pretend to.
- **Measure on data you did not tune on.** The threshold was picked on one synthetic seed; results are reported on others.

## Motivation

This is the entity-resolution step behind the kind of analysis I do on defense and federal-contracting data (the Hard Power Intelligence and Grey-Resolve projects touch the same problem from other angles): cross-referencing suppliers across public databases fails if you rely on fuzzy strings or vector similarity alone. It is the portfolio's "probabilistic evidence, deterministic boundary" idea applied to record linkage.

## Method (what the pipeline actually does)

1. **Normalise** names: lowercase, strip punctuation, drop legal words (`llc`, `inc`, `corp`, `co`, `ltd`, `the`, `company`, ...).
2. **Block keys** (`block_keys`): for the first four name tokens, every token pair gives a Metaphone key and a 3-character prefix key, so one typo still leaves a shared pair. Single-token names use single keys.
3. **Candidate pairs**: a DuckDB self-join on key; blocks larger than 200 records are skipped and logged.
4. **Hard constraint**: both tax IDs present and different means the pair is dropped (`edge_blocked`).
5. **Score**: `0.7 * name + 0.3 * address`, where name is the larger of Jaro-Winkler and token-sort ratio, address is a string ratio halved if ZIPs differ. A shared tax ID scores 1.0. Edges are kept at or above 0.93.
6. **Graph gate**: connected components; a component is split if it holds two tax IDs, or has more than three nodes and density below 0.5. Splitting uses recursive Louvain (fixed seed); if a tax-conflicted component still cannot be split, nodes are partitioned by tax ID, and untaxed nodes join the ID with most edge weight.
7. **Output** `cluster_id` and the audit log.

## Results

Synthetic data only: typos, case changes, trading prefixes and suffixes, address drift, 40% of entities without a tax ID, and 10% "trap" twins sharing a name and address with a differently-taxed entity. The threshold (0.93) and the density rule were chosen on seed 1; the rows below use other seeds. Pairwise precision, recall and F1 against the hidden truth. Reproduce: `python scripts/benchmark.py`.

| Entities | Records | Precision | Recall | F1 | Tax-ID violations | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 1,000 (seed 2) | 2,021 | 0.858 | 0.973 | 0.912 | 0 | 0.3 |
| 1,000 (seed 3) | 1,964 | 0.856 | 0.972 | 0.910 | 0 | 0.2 |
| 5,000 (seed 2) | 9,870 | 0.816 | 0.977 | 0.889 | 0 | 4.4 |
| 20,000 (seed 2) | 39,369 | 0.770 | 0.842 | 0.804 | 0 | 6.7 |

- Zero tax-ID violations in every run, which is the guarantee the gate exists to give.
- Precision is capped near 0.86 at small scale by the trap twins' records that carry no tax ID: nothing in the data separates them (the demo's record 1).
- Quality falls at 20,000 entities. The synthetic name space has only 4,032 base names, so many distinct vendors collide; this is partly the generator and partly a real scaling cost, and the two are not separated here.
- Two design flaws were found by running the benchmark: a threshold of 0.82 chained unrelated vendors into one component (precision 0.61), and single-token blocking keys collapsed recall to 0.005 at 5,000 entities. Both are fixed and described in [docs/RESULTS.md](docs/RESULTS.md).

### Real data: federal-contractor names (USAspending, January 2024)

A separate study, planned before any matcher was run ([docs/PROTOCOL_REAL.md](docs/PROTOCOL_REAL.md)), scores four matchers on 367 held-out registry entities (1,138 name strings), with the registry's own identifier as the hidden answer key. Each matcher has one number tuned on development data; the test split was scored once.

| Matcher | Precision | Recall | F1 |
| --- | --- | --- | --- |
| Exact normalised name | 0.927 | 0.556 | 0.695 |
| Plain fuzzy, tuned | 0.886 | 0.623 | 0.732 |
| Splink (two configurations) | 0.927 / 0.897 | 0.556 / 0.592 | 0.695 / 0.713 |
| **This pipeline, tuned** | 0.876 | 0.675 | **0.763** |
| This pipeline, default threshold | 0.888 | 0.636 | 0.741 |

- The tuned pipeline beats the tuned plain fuzzy matcher by 0.031 F1 (95% interval +0.004 to +0.059), mostly through recall. The untuned default does not (+0.009, interval spans zero). Read this as suggestive: a richer Splink variant was added after the first development run, and the interval's lower end is thin.
- 17% of true pairs are renames that share almost no text; **no matcher recovers any of them**, so overall recall is capped near 0.83.
- Of the findable pairs the pipeline misses, 86% were never proposed by blocking, so better blocking, not better scoring, is the lever (post-hoc finding, not yet tested as a fix).
- Public data has no tax IDs, so this study does **not** test the hard constraint the design is built around.

## Limitations

- **Constraint and scale claims are synthetic-only.** The real-data study covers names only, one month and one agency; mergers, subsidiaries and transliteration are barely represented.
- **One hard rule.** Only the tax-ID contradiction is enforced. CAGE codes, parent-subsidiary rules and other absolute constraints are not built.
- **Missing identifiers defeat the gate.** A record with no tax ID can be grouped with the wrong twin, as the demo shows; the gate guarantees consistency, not correctness.
- **Thresholds are not portable.** 0.93 and density 0.5 were picked on synthetic data and will need re-tuning.
- **Small name space.** The generator saturates near 20,000 entities, so the largest rows are pessimistic in a way unrelated to the algorithm.
- **Not at scale.** No 100k+ run and no F1-versus-latency curve. Splink was compared only on the small real-data study, with a fixed hand-set configuration.
- **No embeddings or extra features** (executive names, geography, vector search) yet.

## Operational notes

### What runs where

Everything runs locally on one machine, single-threaded. No services, database server or network access.

### Data and keys

No keys. The benchmark data is generated from a seed. Real data later should come from public sources (USASpending, SAM.gov, SEC EDGAR) and never include non-public or employer data.

### Verify the claims (a reviewer's path)

```bash
pytest -q                         # 8 passed, includes the property test of the guarantee
mypy src tests scripts            # strict, clean
python examples/demo.py           # the table and audit log shown at the top
python scripts/benchmark.py       # the held-out synthetic table
```

### Documentation map

| Doc | What it covers |
| --- | --- |
| [docs/RESULTS_REAL.md](docs/RESULTS_REAL.md) | the real-data study: results, criteria, the rename ceiling, where recall is lost |
| [docs/PROTOCOL_REAL.md](docs/PROTOCOL_REAL.md) | its plan, written before any matcher was run, and the two deviations |
| [docs/RESULTS.md](docs/RESULTS.md) | synthetic protocol, the table, how to read it, the two development findings |
| [examples/demo.py](examples/demo.py) | the worked example above |
| [src/entity_resolution_gate/pipeline.py](src/entity_resolution_gate/pipeline.py) | blocking, scoring and the graph gate |

## License

MIT. See [LICENSE](LICENSE).

## Author

Chris Schmidt ([PCSchmidt](https://github.com/PCSchmidt)). Part of a portfolio on evaluator-gated AI systems: probabilistic components propose, deterministic gates decide.
