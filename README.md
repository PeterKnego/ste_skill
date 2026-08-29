# Simplified Technical English for Claude Code

A Claude Code plugin that makes Claude write English prose to
[ASD-STE100](https://asd-ste100.org) Simplified Technical English.

The plugin contains three parts:

- **The `/ste` skill** — rules, preferred words, and a procedure for prose.

- **A checker script** — `ste_check.py`, a deterministic heuristic checker.
  Python 3.8+, standard library only, no dependencies. It reports one line
  per sentence, marks each finding as an error or a warning, and exits 1 on
  errors, so it works in CI and git hooks.

- **A post-write hook** — an automatic check on Markdown files, off by
  default. When the check is on and Claude writes a Markdown file, the hook
  runs the checker on it. The errors go back into Claude's context, and
  Claude fixes those sentences in the same turn. The hook is silent on files
  with no errors and on files that are not Markdown.

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

A rewrite works by sentence, not by file. Claude runs the checker, edits only
the sentences the checker lists, runs the checker once more, and reports what
remains. It does not write the whole file again, and it does not loop until
the count is zero. The cost of a rewrite follows the number of findings, not
the length of the file.

The checker prefers precision to recall. It does not flag a bare `-ing`
word (`sibling`, `fuzzing`), only one at the start of a sentence or after a
preposition such as `before` or `by`. It does not guess at noun clusters. It
skips code, tables, paths, and links. When it flags something, Claude can
fix it.

Run the checker standalone:

```bash
python3 skills/ste/scripts/ste_check.py README.md
python3 skills/ste/scripts/ste_check.py --procedural docs/install.md
python3 skills/ste/scripts/ste_check.py --dictionary approved-words.txt docs/*.md
python3 skills/ste/scripts/ste_check.py --format json docs/install.md
```

It prints one line per sentence, with every finding for that sentence:

```
docs/install.md
  L12 [E8.6 semicolon; split the sentence] [W3.1 passive 'is set'] :: The value is set; ...
1 error, 1 warning in docs/install.md
1 error, 1 warning.
```

`E` is an error: a rule the checker is sure about. `W` is a warning: passive
voice in descriptive text, or a heuristic. The exit code is 1 on errors;
warnings do not fail the run unless you pass `--fail-on warning`.

Enforce it in CI:

```yaml
- name: Simplified Technical English
  run: python3 skills/ste/scripts/ste_check.py docs/*.md README.md
```

Existing documentation will produce a lot of output on the first run. Fix the
errors first; leave the warnings until the errors are gone.

Run the tests:

```bash
python3 -m unittest discover -s tests
```

## Tune

- `skills/ste/references/project-terms.txt` — words the checker must never
  flag. Put your crate names, product terms, and domain `-ing` nouns here.
- The preferred-words table in `skills/ste/SKILL.md` — add the words your
  team overuses.
- Hook environment variables: `STE_PATHS` (file pattern to check),
  `STE_DICTIONARY` (approved-word list), `STE_MAX` (sentences reported,
  default 15).

## Limits

The checker catches structure and common word choice, not full dictionary
compliance. Read [skills/ste/references/limits.md](skills/ste/references/limits.md)
before you claim STE compliance to anyone. For contractual compliance, use a
certified checker.

## License

MIT — see [LICENSE](LICENSE).
