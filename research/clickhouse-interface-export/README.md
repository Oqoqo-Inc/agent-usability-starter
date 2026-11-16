# ClickHouse: one export through four interfaces

This is a diagnostic product-usability experiment by Oqoqo. Four toolsets expose ClickHouse's HTTP API, Python SDK, native CLI, or official MCP server. They use one task prompt, one agent/model configuration and three fresh trials per interface. The four interfaces ultimately read the same ClickHouse table; this is not a database performance or vendor platform benchmark.

## Task and fixture

Each run has a fresh copy of ClickHouse 26.8.38.9 seeded with the same 240 synthetic orders. An agent exports the 123 paid January 2026 orders for tenant `orchid` to `export.csv`. The rows include unpaid orders, another tenant and dates outside January. The agent receives the connection details and interface selection rule. This tests completing a task through a supplied interface, not discovering ClickHouse on the open web.

The 40-row batch ceiling is a task requirement for order reads, not a database limit. A database-wide cap interfered with the SDK's settings discovery during preflight, so it was removed before the agent trials. The database user can read the orders table and cannot write. The local MCP process uses the official entry point and sets the zero-length environment value the upstream server expects for the passwordless synthetic user.

| Condition | Actual tool |
| --- | --- |
| HTTP API | Direct SQL over the ClickHouse HTTP endpoint, port 8123 |
| SDK | ClickHouse Connect Python driver 1.12.0 |
| CLI | Native ClickHouse client 26.8.38.9 |
| MCP | Official `mcp-clickhouse` 0.7.0, stdio, querying the same service |

## Reproduce the fixture controls

With Docker, curl and Python 3.12:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-controls.txt
PYTHON_BIN=.venv/bin/python bash reproduce-controls.sh
```

This runs the pinned ClickHouse image on loopback, then removes its temporary container. All four reference clients should return the same 123 rows. The verifier should reject a first-page export, an export with a duplicate replacing a required row, and an incorrect amount. Read `control-output/report.json` for the results. These controls run no model and do not use a cloud account.

## Independent grading

The grader reconstructs the fixture in Python and compares the agent's retained CSV with the exact expected ID/amount pairs. It checks the header, numeric amounts, ordering, duplicates, missing rows and extra rows. It does not infer correctness from the agent's final prose. An independent trajectory review checks that the assigned surface actually performed the database reads and that the agent respected the task's batch ceiling. If the workspace, trace, or provider is unavailable, the affected measurement is marked as such.

To verify a retained artifact independently:

```sh
python3 verify.py path/to/export.csv
```

Primary vendor documentation: [HTTP interface](https://clickhouse.com/docs/concepts/features/interfaces/http), [ClickHouse Connect](https://clickhouse.com/docs/integrations/language-clients/python/index), [native ClickHouse client](https://clickhouse.com/docs/interfaces/client), and [official MCP server](https://github.com/ClickHouse/mcp-clickhouse/tree/v0.7.0).

## November 16, 2026 results

Codex 0.167.0, GPT-6.1-Sol, medium effort. Three independently seeded trials per interface reached the agent. An independent grade and a review of the retained action trail both passed for all 12 completed trials. The four reference controls are separate and do not contribute to these results.

| Interface | Correct CSV and assigned interface, within the row limit | Setup failures before the agent started | Median agent seconds | Median reported input tokens | Median reported output tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| HTTP API | 3/3 | 0 | 33.125 | 70,538 | 1,143 |
| Python SDK | 3/3 | 0 | 32.441 | 69,396 | 1,034 |
| Native CLI | 3/3 | 3 | 32.553 | 70,056 | 1,042 |
| Official MCP | 3/3 | 0 | 37.354 | 109,883 | 1,060 |

Three initial CLI attempts stopped at runner installation before Codex started. The three CLI trials in the table used the same native binary copied from the pinned image, with the same task, fixture, model, and effort. These failures are recorded separately and are not evidence that Codex could not use the CLI. The table measures agent execution, excluding environment setup and offline grading. Reported token counts are whole-agent values, including context supplied to the model; they are not the token cost of the database query.

- **MCP: extra calls and manual transfer.** Each run fetched four nonempty pages (40, 40, 40, 3 rows). All three put the returned rows into generated Python to write the CSV; two also called `run_query` once more and received no rows. The HTTP, SDK and CLI agents instead used a local program to pass each page directly into the CSV. Two non-MCP runs also checked an empty page; there was no general protocol requirement to make that call.
- **HTTP: two failed queries inside a pass.** One trial saw HTTP 500 without details in the exception text. It reran the query while printing the response body, which exposed ClickHouse's `ILLEGAL_AGGREGATION` error. It renamed a conflicting alias and finished the export. The two failed calls are visible in the trace; there is no matched before-and-after estimate of avoidable latency or tokens.
- **CLI: setup failure and query overhead are different.** Setup never reached the agent in the initial three runs. In one completed retry, the agent probed the first page separately and then read it again in the export loop.

Inspect [the attempt ledger](results.csv), [retained CSVs](artifacts/), and [selected trace excerpts](trace-excerpts.json). Ordinals are positions in the retained action trail; the projections omit unrelated commands and data rows. The ledger's page-read counts exclude schema discovery, scalar aggregate checks, and driver metadata. For calls inside local programs, counts are derived from the executed code and output. Verify any retained file with `python3 verify.py artifacts/mcp-02.csv`. The fixture and controls reproduce the independently checked workflow, but a new model run can take a different path. This samples one task, one model and three completed trials per interface. It does not establish a general ranking of the interfaces or isolate a cause for the token differences.

For the evaluation workflow and tool shortlist, see [Oqoqo's agent usability testing tools guide](https://oqoqo.ai/guides/agent-experience-evaluation-tools#clickhouse-four-interface-export).
