#!/usr/bin/env bash
# install.sh: link every kstack skill and agent into ~/.claude, so every project and every Claude
# Code surface (terminal, VS Code, the Desktop app) sees them. Then hooks/install.py merges kstack's
# hooks into ~/.claude/settings.json, backing that file up beside itself before any change, and
# removes dead links in ~/.claude/skills and ~/.claude/agents into this checkout's skills/ and
# agents/, such as a retired skill's. Safe to re-run: a link at a skill's or agent's name that
# points elsewhere is relinked, a real file or folder in its place is reported and never
# overwritten, and a dead link that points anywhere but those two folders is kept.
#
#   ./install.sh                      link every skill and agent, merge hooks, prune dead links
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

# the hooks merge into the settings, then dead links into skills/ and agents/ go, then a count...
python3 "$here/hooks/install.py" "$here/hooks/hooks.json" "$HOME/.claude/settings.json" "$here/skills"
