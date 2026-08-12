# Simplified Technical English for Claude Code

A Claude Code plugin that makes Claude write English prose to
[ASD-STE100](https://asd-ste100.org) Simplified Technical English.

The plugin contains three parts:

- **The `/ste` skill** — rules, preferred words, and a procedure for prose.

- **A checker script** — `ste_check.py`, a deterministic heuristic checker.
  Python 3.8+, standard library only, no dependencies. Its exit code is 1 on
  violations, so it works in CI and git hooks.

- **A post-write hook** — an automatic check on Markdown files, off by
  default. When the check is on and Claude writes or edits a Markdown file,
  the hook runs the checker on it. The violations go back into Claude's
  context, and Claude fixes them in the same turn. The hook is silent on
  clean files and on files that are not Markdown.

## Install

Add the marketplace, then install the plugin:

```
/plugin marketplace add PeterKnego/ste_skill
/plugin install ste@ste-skill
```

The automatic check is off by default. To turn it on or off, run
`/plugin configure ste@ste-skill` in Claude Code, or pass the option on the
command line:

```bash
claude plugin install ste@ste-skill --config auto_check=true
```

`STE_AUTO_CHECK=1` in your environment also turns the check on.

For a manual install of the skill alone, see [INSTALL.md](INSTALL.md).

## Use

Invoke the skill directly:

```
/ste rewrite docs/architecture.md
/ste write an install guide for the pump controller
```

Run the checker standalone:

```bash
python3 skills/ste/scripts/ste_check.py README.md
python3 skills/ste/scripts/ste_check.py --procedural docs/install.md
python3 skills/ste/scripts/ste_check.py --dictionary approved-words.txt docs/*.md
```

Enforce it in CI:

```yaml
- name: Simplified Technical English
  run: python3 skills/ste/scripts/ste_check.py docs/*.md README.md
```

Start with the checker as a warning, not a gate. Existing documentation will
produce a lot of output on the first run.

## Tune

- `skills/ste/references/project-terms.txt` — words the checker must never
  flag. Put your crate names, product terms, and domain `-ing` nouns here.
- The preferred-words table in `skills/ste/SKILL.md` — add the words your
  team overuses.
- Hook environment variables: `STE_PATHS` (file pattern to check),
  `STE_DICTIONARY` (approved-word list), `STE_MAX` (violation cap,
  default 40).

## Limits

The checker catches structure and common word choice, not full dictionary
compliance. Read [skills/ste/references/limits.md](skills/ste/references/limits.md)
before you claim STE compliance to anyone. For contractual compliance, use a
certified checker.

## License

MIT — see [LICENSE](LICENSE).
