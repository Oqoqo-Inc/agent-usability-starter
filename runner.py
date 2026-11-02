#!/usr/bin/env python3
"""Small, independent SDK artifact verifier. No model calls or paid services."""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
import math
import pathlib
import shutil
import subprocess
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
IMAGE = "oqoqo-agent-usability-starter:v1"
TASKS = ("search", "export", "persistence")
SOURCE = "https://raw.githubusercontent.com/qdrant/qdrant-client/v1.15.1/README.md"
SOURCE_HASH = "668410ed85174072122d80788c50ef7f19ea1ac88ebf394c4d9e0b6f8504561e"
METRICS = ("input_tokens", "output_tokens", "agent_seconds")

def load_manifest(path):
    rows = json.loads(path.read_text())
    if not isinstance(rows, list):
        raise ValueError("Manifest must be a list of attempts")
    seen = set()
    for row in rows:
        for field in ("id", "agent", "condition", "task", "artifact"):
            if not isinstance(row.get(field), str) or not row[field]:
                raise ValueError("Each attempt requires a nonempty " + field)
        if row["id"] in seen:
            raise ValueError("Duplicate attempt id: " + row["id"])
        seen.add(row["id"])
        if row["task"] not in TASKS:
            raise ValueError("Unsupported task: " + row["task"])
        for metric in METRICS:
            value = row.get(metric)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
                raise ValueError("Invalid " + metric)
    return rows

def verify_attempt(row, manifest_dir, image=IMAGE):
    result = {key: row[key] for key in ("id", "agent", "condition", "task")}
    result.update({key: row.get(key) for key in METRICS})
    result.update(status="unmeasured", passed=None, verification_seconds=None)
    artifact = (manifest_dir / row["artifact"]).resolve()
    source = artifact / "store.py"
    if not source.is_file():
        return dict(result, reason="missing store.py")
    result["artifact_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    verifier = ROOT / "verifier"
    # Only the artifact and trusted verifier are mounted. No credentials or Docker socket.
    command = ["docker", "run", "--pull=never", "--rm", "--network=none", "--read-only",
               "--cap-drop=ALL", "--security-opt=no-new-privileges", "--memory=512m", "--cpus=1",
               "--pids-limit=64", "--tmpfs=/tmp:rw,nosuid,size=64m",
               "--mount", "type=bind,src=" + str(artifact) + ",dst=/candidate,readonly",
               "--mount", "type=bind,src=" + str(verifier) + ",dst=/verifier,readonly",
               image, "python", "-c",
               "import shutil,sys,runpy; shutil.copy('/candidate/store.py','/tmp/store.py'); "
               "sys.path.insert(0,'/tmp'); sys.argv=['checks.py',sys.argv[1]]; "
               "runpy.run_path('/verifier/checks.py',run_name='__main__')", row["task"]]
    start = time.monotonic()
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        return dict(result, reason=type(error).__name__)
    result["verification_seconds"] = round(time.monotonic() - start, 3)
    result.update(stdout=done.stdout[-12000:], stderr=done.stderr[-12000:], exit_code=done.returncode)
    if done.returncode in (125, 126, 127):
        return dict(result, reason="Docker/runtime could not execute the verifier")
    return dict(result, status="measured", passed=done.returncode == 0)

def summarize(rows):
    groups = collections.defaultdict(list)
    for row in rows:
        groups[(row["agent"], row["condition"], row["task"])].append(row)
    summary = []
    for (agent, condition, task), attempts in sorted(groups.items()):
        measured = [r for r in attempts if r["status"] == "measured"]
        item = dict(agent=agent, condition=condition, task=task, attempts=len(attempts),
                    measured=len(measured), passes=sum(r["passed"] is True for r in measured),
                    pass_rate=sum(r["passed"] is True for r in measured)/len(measured) if measured else None)
        for metric in METRICS:
            values = [r[metric] for r in attempts if r.get(metric) is not None]
            item[metric + "_coverage"] = len(values)
            item[metric + "_mean"] = sum(values)/len(values) if values else None
        summary.append(item)
    return summary

def save_report(rows, destination, label):
    destination.mkdir(parents=True, exist_ok=True)
    summary = summarize(rows)
    (destination / "report.json").write_text(json.dumps({"label": label, "attempts": rows, "summary": summary}, indent=2) + "\n")
    fields = ["id", "agent", "condition", "task", "status", "passed", *METRICS, "verification_seconds", "artifact_sha256", "reason"]
    with (destination / "attempts.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# " + label, "", "Missing or blocked measurements remain unmeasured. Agent metrics are supplied by the operator; verifier time is separate.", "", "| Agent | Condition | Task | Passes / measured | Total attempts |", "| --- | --- | --- | --- | --- |"]
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    for row in summary:
        lines.append("| " + " | ".join(cell(value) for value in [row["agent"], row["condition"], row["task"], str(row["passes"]) + " / " + str(row["measured"]), row["attempts"]]) + " |")
    lines += ["", "Small samples describe these attempts. This runner does not measure natural product discovery, SDK participation from traces, model tokens, or production authentication automatically.", ""]
    (destination / "report.md").write_text("\n".join(lines))

def prepare(destination, repeats):
    if destination.exists():
        raise ValueError("Choose a new workspace directory; existing work is never overwritten")
    with urllib.request.urlopen(SOURCE, timeout=30) as response:
        readme = response.read()
    if hashlib.sha256(readme).hexdigest() != SOURCE_HASH:
        raise ValueError("Upstream source hash differs from the pinned experiment")
    rows = []
    for condition in ("baseline", "revised"):
        for task in TASKS:
            for repeat in range(1, repeats + 1):
                name = condition + "-" + task + "-" + str(repeat)
                workspace = destination / name
                shutil.copytree(ROOT / "fixture", workspace)
                docs = workspace / "qdrant-docs"
                docs.mkdir()
                shutil.copy(ROOT / "docs/SKILL.md", docs / "SKILL.md")
                reference = readme.decode()
                if condition == "revised":
                    reference += (ROOT / "docs/workflow-notes.md").read_text()
                (docs / "reference.md").write_text(reference)
                (workspace / "TASK.md").write_text((ROOT / "tasks" / (task + ".md")).read_text())
                rows.append(dict(id=name, agent="record-model-harness-and-effort", condition=condition, task=task, artifact=name,
                                 input_tokens=None, output_tokens=None, agent_seconds=None))
    (destination / "attempts.json").write_text(json.dumps(rows, indent=2) + "\n")
    print("Prepared", len(rows), "fresh workspaces. Run each task in a separate fresh agent session; update agent settings and measured metrics in attempts.json.")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("prepare")
    init.add_argument("--output", type=pathlib.Path, required=True)
    init.add_argument("--repeats", type=int, choices=range(1, 11), default=2)
    verify = sub.add_parser("verify")
    verify.add_argument("manifest", type=pathlib.Path)
    verify.add_argument("--output", type=pathlib.Path, required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.output, args.repeats)
        return
    if args.command == "demo":
        rows = [dict(id=condition + "-" + task, agent="deterministic-fixture-control", condition=condition, task=task, artifact=str(ROOT / ("reference" if condition == "reference" else "fixture"))) for condition in ("starter", "reference") for task in TASKS]
        parent = ROOT
        label = "Fixture validation — not model benchmark results"
    else:
        rows = load_manifest(args.manifest)
        parent = args.manifest.resolve().parent
        label = "Independent SDK artifact checks"
    results = [verify_attempt(row, parent) for row in rows]
    save_report(results, args.output, label)
    print(json.dumps({"attempts": len(results), "measured": sum(r["status"] == "measured" for r in results), "passes": sum(r["passed"] is True for r in results), "report": str(args.output / "report.md")}))
    if any(r["status"] == "unmeasured" for r in results):
        raise SystemExit(2)

if __name__ == "__main__":
    main()
