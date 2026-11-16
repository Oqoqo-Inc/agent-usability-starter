#!/usr/bin/env bash
set -euo pipefail
work_dir=$(cd -- "$(dirname -- "$0")" && pwd)
out_dir=${1:-"$work_dir/control-output"}
python_bin=${PYTHON_BIN:-python3}
image='clickhouse/clickhouse-server@sha256:5d30ac138948b43fd928842be7da1dcd2de712d32ba6c42368ff5009ba2072ff'
trial_container="clickhouse-export-control-${RANDOM}-$$"
docker run -d --rm --name "$trial_container" -p 127.0.0.1::8123 \
  -v "$work_dir/fixture.sql:/docker-entrypoint-initdb.d/01-fixture.sql:ro" \
  -v "$work_dir/default-local.xml:/etc/clickhouse-server/users.d/fixture-local-default.xml:ro" "$image" >/dev/null
trap 'docker stop "$trial_container" >/dev/null 2>&1 || true' EXIT
port=$(docker port "$trial_container" 8123 | awk -F: '{print $NF}')
for try in {1..30}; do
  if [[ $(curl -fsS "http://127.0.0.1:$port/?user=bench_reader" \
    --data-binary 'SELECT count() FROM fixture.orders' 2>/dev/null || true) == 240 ]]; then
    "$python_bin" "$work_dir/controls.py" "$port" "$trial_container" "$out_dir"
    exit
  fi
  sleep 2
done
echo 'Fixture did not become ready.' >&2
exit 2
