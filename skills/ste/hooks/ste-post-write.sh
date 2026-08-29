#!/usr/bin/env bash
# PostToolUse hook: run the STE checker on any Markdown file Claude writes,
# and feed the errors back so Claude fixes them in the same turn.
#
# Match Write only, not Edit. Claude fixes the reported sentences with Edit,
# and a hook on Edit would run again after each fix and inject the report
# again each time.
#
# Deterministic — no second model, no paraphrase drift, no local LLM to install.
#
# Wire it up in .claude/settings.json:
#
#   {
#     "hooks": {
#       "PostToolUse": [
#         {
#           "matcher": "Write",
#           "hooks": [
#             { "type": "command",
#               "command": "$CLAUDE_PROJECT_DIR/.claude/skills/ste/hooks/ste-post-write.sh",
#               "timeout": 20 }
#           ]
#         }
#       ]
#     }
#   }
#
# Environment:
#   STE_AUTO_CHECK  with --opt-in: set to 1 to turn the automatic check on
#   STE_PATHS       glob-ish grep pattern for files to check (default: \.(md|mdx)$)
#   STE_DICTIONARY  path to an approved-word list; enables full dictionary check
#   STE_MAX         stop reporting after this many sentences (default 15)

set -euo pipefail

# The plugin invokes this hook with --opt-in, and the hook then runs only
# when the user turned the automatic check on: the auto_check plugin option
# (asked at install), or STE_AUTO_CHECK=1 in the environment. A manual
# install that wires the hook without the flag always runs.
if [ "${1:-}" = "--opt-in" ]; then
  case "${CLAUDE_PLUGIN_OPTION_AUTO_CHECK:-${STE_AUTO_CHECK:-}}" in
    1|true|yes|on) ;;
    *) exit 0 ;;
  esac
fi

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKER="$SKILL_DIR/scripts/ste_check.py"
PATTERN="${STE_PATHS:-\.(md|mdx)$}"
MAX="${STE_MAX:-15}"

payload="$(cat)"

# jq is nice to have, but do not require it.
if command -v jq >/dev/null 2>&1; then
  file="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty')"
else
  file="$(printf '%s' "$payload" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
fi

[ -n "$file" ] || exit 0
[ -f "$file" ] || exit 0

# Never check the skill's own files: SKILL.md lists forbidden words as examples.
case "$file" in "$SKILL_DIR"/*) exit 0;; esac
printf '%s' "$file" | grep -Eq "$PATTERN" || exit 0

python3 --version >/dev/null 2>&1 || exit 0

args=("$CHECKER")
[ -n "${STE_DICTIONARY:-}" ] && [ -f "${STE_DICTIONARY}" ] && args+=(--dictionary "$STE_DICTIONARY")
args+=("$file")

set +e
report="$(python3 "${args[@]}" 2>/dev/null)"
rc=$?
set -e

# Exit code 1 means errors. Warnings alone do not interrupt the turn.
[ "$rc" -eq 1 ] || exit 0
[ -n "$report" ] || exit 0

# One line per sentence; keep the first MAX sentences and the summary.
report="$(printf '%s\n' "$report" | grep -E '^  L[0-9]+ ' | head -n "$MAX"; printf '%s\n' "$report" | tail -n 1)"

# Emit JSON without depending on jq for the encode.
printf '%s' "$report" | python3 -c '
import json, sys
report = sys.stdin.read().strip("\n")
path = sys.argv[1]
message = (
    "The ASD-STE100 checker found errors in " + path + ". "
    "Each line below is one sentence: E is an error, W is a warning. "
    "Fix each E sentence with Edit on that sentence. Do not write the whole "
    "file again. Fix a W sentence only when the meaning stays the same. "
    "Keep every fact - STE removes ambiguity, not content. If a rule would "
    "change the meaning, keep the meaning and say which rule you broke. "
    "Do this once; do not loop on the checker.\n\n" + report
)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": message[:9500],
    },
    "suppressOutput": True,
}))
' "$file"
