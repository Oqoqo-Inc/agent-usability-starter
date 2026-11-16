"""Check exported contents against the deterministic seed, outside the agent workspace."""
from __future__ import annotations
from collections import Counter
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path


def fixture_rows():
    for i in range(240):
        yield dict(order_id=hashlib.md5(f"oqoqo-order-export-nov16-v1:{i}".encode()).hexdigest().upper(),
                   tenant="cedar" if i % 4 == 0 else "orchid",
                   status="void" if i % 5 == 0 else "paid",
                   ordered_on="2026-02-01" if i % 7 == 0 else f"2026-01-{1 + i % 31:02d}",
                   amount_cents=1200 + (i * 7919) % 100003)


def expected():
    return dict(sorted((row["order_id"], row["amount_cents"]) for row in fixture_rows()
                       if row["tenant"] == "orchid" and row["status"] == "paid"
                       and row["ordered_on"].startswith("2026-01-")))


def grade(data: bytes):
    want = expected()
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True))
    header = rows.pop(0) if rows else []
    pairs = [(r[0], int(r[1])) for r in rows if len(r) == 2 and re.fullmatch(r"[0-9]{1,9}", r[1])]
    keys = [k for k, _ in pairs]
    counts = Counter(keys)
    verdict = {
        "expected_rows": len(want), "actual_rows": len(rows),
        "header_exact": header == ["order_id", "amount_cents"],
        "invalid_rows": len(rows) - len(pairs),
        "missing_ids": sorted(set(want) - counts.keys()),
        "extra_ids": sorted(counts.keys() - set(want)),
        "duplicate_ids": sorted(k for k, n in counts.items() if n > 1),
        "wrong_amount_ids": sorted({k for k, v in pairs if k in want and want[k] != v}),
        "ordered": keys == sorted(keys),
        "artifact_sha256": hashlib.sha256(data).hexdigest(),
    }
    verdict["passed"] = bool(verdict["header_exact"] and verdict["ordered"] and
                             len(rows) == len(want) and not any(verdict[k] for k in (
                               "invalid_rows", "missing_ids", "extra_ids", "duplicate_ids", "wrong_amount_ids")))
    return verdict


if __name__ == "__main__":
    try:
        report = grade(Path(sys.argv[1]).read_bytes())
    except (OSError, UnicodeError, csv.Error) as error:
        report = {"passed": False, "error": type(error).__name__, "details": str(error)}
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
