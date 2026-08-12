# Manual install

The easy path is the plugin — see [README.md](README.md). If you want the
skill without the plugin system, or if you want to vendor it into one
repository, use this manual path.

## Personal — every project

```bash
git clone https://github.com/PeterKnego/ste_skill
cp -r ste_skill/skills/ste ~/.claude/skills/
```

You get `~/.claude/skills/ste/SKILL.md`. Claude Code picks it up in the
current session, no restart needed.

## Project — one repo, shared with the team

```bash
git clone https://github.com/PeterKnego/ste_skill
mkdir -p .claude/skills
cp -r ste_skill/skills/ste .claude/skills/
git add .claude/skills/ste
```

When both exist, personal overrides project.

## Use it

When Claude writes documentation, it loads the skill on its own. You can
also invoke it directly:

```
/ste rewrite docs/architecture.md
```

The checker runs standalone too:

```bash
python3 ~/.claude/skills/ste/scripts/ste_check.py README.md
python3 ~/.claude/skills/ste/scripts/ste_check.py --procedural docs/install.md
python3 ~/.claude/skills/ste/scripts/ste_check.py --dictionary approved-words.txt docs/*.md
```

When it finds a violation, its exit code is 1, so it drops into CI or a git
hook unchanged. Python 3.8+, standard library only, no dependencies.

## Scope it to documentation only

If you do not want STE applied to commit messages and chat, add `paths` to the
frontmatter in `SKILL.md`:

```yaml
paths: docs/**, README.md, **/*.md
```

When Claude works on those files, and only then, it loads the skill
automatically.

## Tune it

- `references/project-terms.txt` — words the checker must never flag. Put your
  crate names, product terms, and domain `-ing` nouns here.
- The preferred-words table in `SKILL.md` — add the words your team overuses.
- `references/limits.md` — what this can and cannot guarantee. Read this before
  you claim STE compliance to anyone.

## Close the loop automatically (recommended)

The plugin install wires this hook for you. For a manual install, wire it
yourself as follows.

`hooks/ste-post-write.sh` is a `PostToolUse` hook. Each time Claude writes or
edits a Markdown file, the hook runs the checker. The violations go back into
Claude's context, and Claude fixes them in the same turn. Add to
`.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/skills/ste/hooks/ste-post-write.sh",
            "timeout": 20
          }
        ]
      }
    ]
  }
}
```

The hook stays silent on a clean file and on any file that is not `.md`.
Environment variables: `STE_PATHS` (file pattern), `STE_DICTIONARY` (approved
word list), `STE_MAX` (violation cap, default 40).

This is the deterministic version of what an LLM-based rewrite hook does. No
second model, no paraphrase drift, no GPU.

## Enforce it in CI

```yaml
- name: Simplified Technical English
  run: python3 .claude/skills/ste/scripts/ste_check.py docs/*.md README.md
```

Or as a pre-commit hook:

```bash
#!/bin/sh
git diff --cached --name-only --diff-filter=ACM | grep '\.md$' | \
  xargs -r python3 .claude/skills/ste/scripts/ste_check.py
```

Start with the checker as a warning, not a gate. Existing documentation will
produce a lot of output on the first run.
