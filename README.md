# Agent usability starter

A runnable SDK fixture and independent outcome checker from [Oqoqo](https://oqoqo.ai). Compare the artifacts coding agents produce with original documentation versus the same documentation plus workflow notes.

The fixture uses **qdrant-client 1.15.1 local mode** and synthetic vectors. It covers tenant-filtered search, paginated export, and payload updates that survive reopening. No product account, API key, embedding model, or network service is needed for verification.

## Run the fixture controls

Requires Python 3.9+ on the host and Docker. Building the image downloads the pinned SDK; verification runs with networking disabled and fresh temporary state.

```sh
docker build -t oqoqo-agent-usability-starter:v1 .
python3 runner.py demo --output results/demo
cat results/demo/report.md
python3 -m unittest discover -s tests
```

Expected: **six measured checks; three reference passes and three incomplete-starter failures**. These deterministic controls validate the fixture. They are not agent benchmark results.

## Compare actual agent outputs

```sh
python3 runner.py prepare --output workspaces/docs-v1 --repeats 2
```

This fetches the exact upstream README by tag and SHA-256, and creates twelve independent task directories. Each contains `TASK.md`, `store.py`, and a `qdrant-docs` reference. Both conditions have the identical `SKILL.md` wrapper; only the revised reference adds Oqoqo workflow notes.

1. Use the same model, harness version, effort, SDK environment and starting state for both conditions. Run each directory's `TASK.md` in a fresh session. Expose its documentation folder the same way in both conditions. Keep the reference solution and verifier outside the agent workspace.
2. Record the actual model/harness/effort in `workspaces/docs-v1/attempts.json`. Repeat this preparation under a new output directory for a second agent configuration. Read the returned artifacts and trace to check required product use, documentation reads, and any network/source-code lookup.
3. Add measured `input_tokens`, `output_tokens` and `agent_seconds` if your harness provides them. Leave unknown values `null`. Cached input is generally a subset of input; confirm provider accounting before adding categories.
4. Verify the retained code with an independent copy of the checks:

```sh
python3 runner.py verify workspaces/docs-v1/attempts.json --output results/docs-v1
```

The runner writes JSON, CSV and a Markdown comparison grouped by **agent, condition and task**. Missing artifacts and runtime failures remain unmeasured. A task assertion failure is a measured failure. Verifier wall time is stored separately from agent execution time. The runner never calls a model or infers its token usage.

## What this verifies

- Search: tenant filtering, ranking, limit and empty results.
- Export: every matching record across multiple pages, without duplicates, plus empty results.
- Persistence: close/reopen, independent read-back, record count, requested payload fields and unrelated payload preservation.

The persistence check asserts vector dimensionality, **not bit-for-bit vector magnitude**. Cosine normalization needs a semantic contract: exact magnitude and similarity direction are different assertions. The [32-attempt research report](https://oqoqo.ai/guides/agent-documentation-evaluation) preserves an original grader disagreement on this point. The starter verifier uses Python 3.13; the original remote experiment used Python 3.12.3. It is an artifact-checking adaptation, not a byte-identical recreation of those model runs.

## Evidence and attribution

- [Inspect the original experiment, grades, traces and outputs](https://gallery.oqoqo.ai/experiments/pub_a504f0d3e916e8cba223f7dd3f33acd3).
- [Research index](https://oqoqo.ai/research) and [SDK agent usability guide](https://oqoqo.ai/guides/sdk-agent-usability-testing).
- Qdrant upstream [README v1.15.1](https://github.com/qdrant/qdrant-client/blob/v1.15.1/README.md), SHA-256 `668410ed85174072122d80788c50ef7f19ea1ac88ebf394c4d9e0b6f8504561e`. Downloaded documentation and the SDK retain their [upstream Apache 2.0 license](https://github.com/qdrant/qdrant-client/blob/v1.15.1/LICENSE). They are not relicensed by this repository.

This small fixture does not establish production Qdrant behavior, authentication quality, natural product discovery, statistical significance, or a general documentation uplift. For managed repeated experiments, task grading and agent observability, see [Oqoqo](https://oqoqo.ai/guides/build-vs-buy-agent-usability-harness).
