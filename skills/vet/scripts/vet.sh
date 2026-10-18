#!/usr/bin/env bash
# vet.sh: the mechanical half of the vet skill. Run from anywhere inside a git repo.
#
#   vet.sh dir              print the state directory (created on first use)
#   vet.sh init             set the cursor to main's tip if no cursor exists yet
#   vet.sh pending          list unreviewed commits on main since the cursor, oldest first
#   vet.sh status [--hook]  one-line summary; --hook prints SessionStart JSON and is silent when clean
#   vet.sh advance <sha>    move the cursor to <sha> once every lane for the range returned; exits 2
#                           when <sha> is behind the cursor or not on main
#   vet.sh ci <rev>         CI conclusion on GitHub Actions: success, failure, pending, none or error
#   vet.sh block <min> <why> hold retries of a blocked range for <min> minutes
#   vet.sh watch [quiet_s]  block until main moves past the cursor, its reflog shows no move for
#                           quiet_s seconds (default 300) and no block is in force; print the new tip
#   vet.sh due-canary       exit 0 if no canary has run this calendar month (UTC), else 1
#   vet.sh canary-done      record today's UTC date as the one line of the canary file
#
# The state directory keeps the cursor (one sha), the canary date (one line) and, while a range is
# blocked, blocked_until (one number). Nothing else is written, and nothing in it grows.

set -euo pipefail

root=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "vet: not inside a git repo" >&2; exit 2; }
cd "$root"

state_dir() {
  if [ -d state/report ] && git check-ignore -q state/report/vet 2>/dev/null; then
    echo "$root/state/report/vet"
  else
    echo "$(cd "$(git rev-parse --git-common-dir)" && pwd)/vet"
  fi
}

dir=$(state_dir)
cursor_file="$dir/cursor"
canary_file="$dir/canary"
blocked_file="$dir/blocked_until"

ensure() { mkdir -p "$dir"; }

main_ref() { if git rev-parse --verify -q main >/dev/null; then echo main; else echo HEAD; fi; }

main_tip() { git rev-parse "$(main_ref)"; }

#when main last moved, read from its reflog; the tip commit's date stands in only with no reflog...
moved_at() {
  local at; at=$(git reflog show -1 --date=unix --format=%gd "$(main_ref)" 2>/dev/null || true)
  at=${at##*@\{}; at=${at%\}}
  case "$at" in ''|*[!0-9]*) git log -1 --format=%ct "$(main_ref)" ;; *) echo "$at" ;; esac
}

cursor() { [ -s "$cursor_file" ] && cat "$cursor_file" || true; }

#the date in the canary file, or nothing when the file is absent or holds no real date...
canary_date() {
  [ -f "$canary_file" ] || return 0
  local d; d=$(head -n 1 "$canary_file" 2>/dev/null || true)
  case "$d" in [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;; *) return 0 ;; esac

  #the pattern keeps basic-format dates out, which python reads; python rejects a month 13...
  if python3 -c 'import datetime, sys; datetime.date.fromisoformat(sys.argv[1])' "$d" 2>/dev/null; then
    echo "$d"
  fi
}

#the canary's part of the status line...
canary_note() {
  if [ ! -f "$canary_file" ]; then echo "no canary yet"; return; fi
  local d; d=$(canary_date)
  if [ -n "$d" ]; then echo "canary last ran $d"; else echo "canary date unknown"; fi
}

case "${1:-status}" in
  dir)
    ensure; echo "$dir" ;;
  init)
    ensure
    if [ -z "$(cursor)" ]; then main_tip > "$cursor_file"; echo "cursor set to $(cat "$cursor_file")"; else echo "cursor already at $(cursor)"; fi ;;
  pending)
    c=$(cursor); [ -n "$c" ] || { echo "vet: no cursor; run 'vet.sh init'" >&2; exit 3; }
    git rev-list --reverse --first-parent "$c..$(main_tip)" ;;
  advance)
    [ -n "${2:-}" ] || { echo "usage: vet.sh advance <sha>" >&2; exit 2; }
    sha=$(git rev-parse --verify -q "$2^{commit}") || { echo "vet: no such commit: $2" >&2; exit 2; }

    #the cursor only moves forward along main, so a range is never reviewed twice...
    git merge-base --is-ancestor "$sha" "$(main_tip)" || { echo "vet: $sha is not on main" >&2; exit 2; }
    c=$(cursor)
    [ -z "$c" ] || git merge-base --is-ancestor "$c" "$sha" || { echo "vet: $sha is behind the cursor $c" >&2; exit 2; }
    ensure; echo "$sha" > "$cursor_file"; rm -f "$blocked_file"; echo "cursor -> $sha" ;;
  ci)
    [ -n "${2:-}" ] || { echo "usage: vet.sh ci <rev>" >&2; exit 2; }
    sha=$(git rev-parse --verify -q "$2^{commit}") || { echo "vet: no such commit: $2" >&2; exit 2; }
    if ! out=$(gh run list --commit "$sha" --json status,conclusion --jq '.[] | "\(.status) \(.conclusion)"' 2>/dev/null); then echo error
    elif [ -z "$out" ]; then echo none
    elif grep -q 'failure\|cancelled\|timed_out' <<<"$out"; then echo failure
    elif grep -qv '^completed' <<<"$out"; then echo pending
    else echo success; fi ;;
  block)
    [ -n "${2:-}" ] || { echo "usage: vet.sh block <minutes> <why>" >&2; exit 2; }
    ensure; echo $(( $(date +%s) + $2 * 60 )) > "$blocked_file"
    echo "vet: retries held for $2 min: ${3:-no reason given}" ;;
  watch)
    quiet=${2:-300}
    c=$(cursor); [ -n "$c" ] || { echo "vet: no cursor" >&2; exit 3; }
    while :; do
      if [ -s "$blocked_file" ] && [ "$(date +%s)" -lt "$(cat "$blocked_file")" ]; then sleep 30; continue; fi
      c=$(cursor)
      tip=$(main_tip)
      if [ "$tip" != "$c" ]; then
        age=$(( $(date +%s) - $(moved_at) ))
        [ "$age" -ge "$quiet" ] && { echo "vet: main moved to $tip"; exit 0; }
      fi
      sleep 30
    done ;;
  due-canary)
    #due unless the canary file holds a date in this UTC month...
    d=$(canary_date)
    [ -n "$d" ] && [ "${d%-??}" = "$(date -u +%Y-%m)" ] && exit 1
    exit 0 ;;
  canary-done)
    ensure; date -u +%Y-%m-%d > "$canary_file"; echo "canary -> $(cat "$canary_file")" ;;
  status)
    c=$(cursor)
    if [ -z "$c" ]; then
      [ "${2:-}" = "--hook" ] && exit 0
      echo "vet: not set up in this repo (run /vet watch once)"; exit 0
    fi
    n=$(git rev-list --count --first-parent "$c..$(main_tip)" 2>/dev/null || echo 0)
    msg="vet: $n unreviewed commit(s) on main, $(canary_note)"
    if [ "${2:-}" = "--hook" ]; then
      if [ "$n" -gt 0 ]; then
        hint=" Unreviewed commits mean the vet loop is down or behind: start it in its own tab with /loop /vet watch."
        python3 -c 'import json, sys; print(json.dumps({"systemMessage": sys.argv[1], "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": sys.argv[2]}}, separators=(",", ":")))' "$msg" "$msg.$hint"
      fi
    else
      echo "$msg"; echo "state: $dir"
    fi ;;
  *)
    sed -n '2,16p' "$0" >&2; exit 2 ;;
esac
