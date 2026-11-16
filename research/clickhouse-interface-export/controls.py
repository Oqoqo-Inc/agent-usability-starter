"""Positive transport controls and negative verifier controls; no model runs."""
import asyncio
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.parse
import urllib.request

import clickhouse_connect
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from verify import expected, grade

base = """SELECT order_id, amount_cents FROM fixture.orders
WHERE tenant='orchid' AND status='paid'
AND ordered_on >= '2026-01-01' AND ordered_on < '2026-02-01'
ORDER BY order_id LIMIT 40 OFFSET {offset}"""


def api(sql, port):
    url = "http://127.0.0.1:" + str(port) + "/?" + urllib.parse.urlencode({"user": "bench_reader"})
    with urllib.request.urlopen(urllib.request.Request(url, data=(sql + " FORMAT CSV").encode())) as response:
        return list(csv.reader(io.StringIO(response.read().decode())))


def native(sql, container):
    completed = subprocess.run(["docker", "exec", container, "clickhouse-client", "--user", "bench_reader",
                                "--query", sql + " FORMAT CSV"], check=True, text=True, capture_output=True)
    return list(csv.reader(io.StringIO(completed.stdout)))


def csv_bytes(rows):
    text = io.StringIO(newline="")
    writer = csv.writer(text)
    writer.writerow(["order_id", "amount_cents"])
    writer.writerows(rows)
    return text.getvalue().encode()


async def collect_mcp(port):
    venv = str(Path(sys.executable).parent)
    params = StdioServerParameters(command=venv + "/mcp-clickhouse", env={
        "PATH": venv + ":/usr/bin:/bin", "CLICKHOUSE_HOST": "127.0.0.1", "CLICKHOUSE_PORT": str(port),
        "CLICKHOUSE_USER": "bench_reader", "CLICKHOUSE_PASSWORD": "", "CLICKHOUSE_SECURE": "false",
        "CLICKHOUSE_DATABASE": "fixture", "CLICKHOUSE_MCP_SERVER_TRANSPORT": "stdio",
    })
    all_rows = []
    async with stdio_client(params) as (rx, tx):
        async with ClientSession(rx, tx) as client:
            await client.initialize()
            tools = await client.list_tools()
            assert "run_query" in {t.name for t in tools.tools}
            for offset in range(0, 160, 40):
                result = await client.call_tool("run_query", {"query": base.format(offset=offset)})
                if result.is_error:
                    raise RuntimeError(str(result.content))
                payload = result.structured_content
                if not payload or "rows" not in payload:
                    payload = json.loads(result.content[0].text)
                assert "rows" in payload and "columns" in payload, list(payload)
                all_rows.extend(payload["rows"])
    return all_rows


def main():
    port, container, dest = int(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    dest.mkdir(parents=True, exist_ok=True)
    sdk = clickhouse_connect.get_client(host="127.0.0.1", port=port, username="bench_reader", database="fixture")
    details = {}
    for label, fn in (("http", lambda sql: api(sql, port)),
                      ("sdk", lambda sql: sdk.query(sql).result_rows),
                      ("cli", lambda sql: native(sql, container))) :
        rows = [row for offset in range(0, 160, 40) for row in fn(base.format(offset=offset))]
        result = csv_bytes(rows)
        (dest / (label + ".csv")).write_bytes(result)
        details[label] = grade(result)
    mcp_result = csv_bytes(asyncio.run(collect_mcp(port)))
    (dest / "mcp.csv").write_bytes(mcp_result)
    details["mcp"] = grade(mcp_result)
    want = list(expected().items())
    details["negative_first_page_only"] = grade(csv_bytes(want[:40]))
    details["negative_duplicate"] = grade(csv_bytes(want[:-1] + [want[-2]]))
    details["negative_wrong_amount"] = grade(csv_bytes(want[:-1] + [(want[-1][0], want[-1][1] + 1)]))
    (dest / "report.json").write_text(json.dumps(details, indent=2) + "\n")
    assert all(details[k]["passed"] == (not k.startswith("negative")) for k in details), details
    print(json.dumps({k: (v["passed"], v["actual_rows"]) for k, v in details.items()}))


if __name__ == "__main__":
    main()
