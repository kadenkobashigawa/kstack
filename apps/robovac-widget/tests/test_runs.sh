#!/bin/sh
# test_runs — builds tests/runs/main.swift with mac/Runs.swift and runs it on the Esc lines
# skills/robovac/tests/esc_lines.json holds, which runs.py's tests read too, then typechecks the
# whole app with build.sh's own flags, since no other suite compiles Robovac.swift. Exits 1 on a
# FAIL.

set -e
here=$(cd "$(dirname "$0")" && pwd)
out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT
trap 'exit 130' INT TERM HUP
swiftc -O -o "$out/test_runs" "$here/../mac/Runs.swift" "$here/runs/main.swift"
"$out/test_runs" "$here/../../../skills/robovac/tests/esc_lines.json"

# the app itself, Robovac.swift with Runs.swift, typechecked with the flags build.sh compiles with...
flags=$(sed -n 's/^swiftc \(.*\) \\$/\1/p' "$here/../mac/build.sh")
mac="$here/../mac"
if [ -n "$flags" ] && swiftc -typecheck $flags "$mac/Robovac.swift" "$mac/Runs.swift"; then
  echo "PASS R22 the app's sources typecheck with build.sh's flags"
else
  echo "FAIL R22 the app's sources typecheck with build.sh's flags  [flags: $flags]"
  exit 1
fi
