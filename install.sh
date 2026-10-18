#!/usr/bin/env bash
# install.sh: link every kstack skill and agent into ~/.claude, so every project and every Claude Code
# surface (terminal, VS Code, the Desktop app) sees them, and merge kstack's hooks into
# ~/.claude/settings.json, backing that file up beside itself first. Safe to re-run: a link that
# points elsewhere is relinked, and a real file or folder in a link's place is reported, never
# overwritten.
#
#   ./install.sh                      link every skill and agent, and merge kstack's hooks
#   python3 tests/test_install_sh.py  run it on throwaway HOMEs and check what it links and skips
#
# A project's own verify-<app> skill lives in that project's .claude/skills/, made there by
# /create-verification-skill, so no skill here is tied to one project.

set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$HOME/.claude/skills" "$HOME/.claude/agents"

link() {
  local src=$1 dst=$2
  if [ -L "$dst" ]; then
    [ "$(readlink "$dst")" = "$src" ] && return 0
    echo "relinked  $dst (was $(readlink "$dst"))"
    ln -sfn "$src" "$dst"
  elif [ -e "$dst" ]; then
    echo "skipped   $dst: a real file or folder is there; move it aside and re-run"
  else
    ln -s "$src" "$dst"
    echo "linked    $dst"
  fi
}

for skill in "$here"/skills/*/; do
  [ -f "${skill}SKILL.md" ] || continue
  link "${skill%/}" "$HOME/.claude/skills/$(basename "$skill")"
done

for agent in "$here"/agents/*.md; do
  link "$agent" "$HOME/.claude/agents/$(basename "$agent")"
done

# kstack's hooks (robovac's run log for the app, vet's session-start line) merge into the settings...
python3 "$here/hooks/install.py" "$here/hooks/hooks.json" "$HOME/.claude/settings.json" "$here/skills"

# the links in a folder whose target is inside this checkout, by path prefix, not by pattern...
count() {
  local n=0 l
  for l in "$1"/*; do
    case "$(readlink "$l")" in "$here"/*) n=$((n + 1)) ;; esac
  done
  echo "$n"
}

echo "done: $(count "$HOME/.claude/skills") skill link(s), $(count "$HOME/.claude/agents") agent link(s) into $here"
