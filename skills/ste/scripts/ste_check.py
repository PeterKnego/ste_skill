#!/usr/bin/env python3
"""Heuristic ASD-STE100 checker. Python 3.8+, standard library only.

Usage:
    python3 ste_check.py FILE [FILE ...]
    python3 ste_check.py --procedural FILE      # 20-word limit everywhere
    python3 ste_check.py --dictionary approved-words.txt FILE
    python3 ste_check.py --format json FILE
    cat draft.md | python3 ste_check.py -

Output is one line per sentence with all of that sentence's findings:

    L12 [E8.6 semicolon; split the sentence] [W3.1 passive 'is set'] :: The ...

E is an error, W is a warning. Exit code 1 on errors (--fail-on warning to
include warnings), so it works as a pre-commit hook or in CI. This is a
heuristic. It catches structure and common word choice, not full dictionary
compliance. See references/limits.md.
"""

import argparse
import collections
import json
import os
import re
import sys

Finding = collections.namedtuple("Finding", "line rule severity message sentence")

SEVERITIES = ("error", "warning")

# ---------------------------------------------------------------- word lists

NOT_APPROVED = {
    "utilize": "use", "utilise": "use", "utilizing": "use", "leverage": "use",
    "employ": "use", "commence": "start", "initiate": "start",
    "terminate": "stop", "cease": "stop", "halt": "stop",
    "prior": "before (as 'prior to')", "subsequent": "after",
    "subsequently": "then", "thereafter": "then", "hereafter": "after this",
    "perform": "do", "execute": "do", "conduct": "do",
    "ensure": "make sure that", "verify": "make sure that",
    "obtain": "get", "acquire": "get", "procure": "get",
    "sufficient": "enough", "adequate": "enough",
    "approximately": "about", "regarding": "about", "concerning": "about",
    "facilitate": "help", "assist": "help",
    "demonstrate": "show", "illustrate": "show", "indicate": "show",
    "modify": "change", "alter": "change",
    "permit": "let", "inform": "tell", "advise": "tell", "notify": "tell",
    "locate": "find", "ascertain": "find", "determine": "find",
    "require": "need", "necessitate": "need",
    "however": "but", "nevertheless": "but", "nonetheless": "but",
    "additionally": "also", "furthermore": "also", "moreover": "also",
    "numerous": "many", "myriad": "many",
    "component": "part", "element": "part",
    "anomaly": "fault", "discrepancy": "fault",
    "comply": "obey", "adhere": "obey",
    "inspect": "examine", "endeavour": "try", "endeavor": "try",
    "commencement": "start", "termination": "stop",
    "aforementioned": "this", "utilization": "use",
    "via": "by / through", "vice": "instead of",
    "whilst": "while", "amongst": "among",
    "shall": "must (or the imperative)",
    "should": "must (or the imperative)",
    "may": "can (permission) / is possible (possibility)",
    "please": "omit it",
}

# Non-approved words that are a warning, not an error. A hedge carries the
# author's confidence. "may have failed" -> "failed" is a different claim, so
# Claude must change these only when the meaning stays the same.
HEDGES = {"may"}

# Modals before "have + participle" make a hedge ("may have failed"), not a
# present perfect. "will" and "shall" are left out: "will have finished" is a
# future perfect, a compound tense.
MODALS = {"may", "might", "could", "should", "would", "must", "can"}
NEGATIONS = {"not", "never", "also", "already"}

# Rule 1.4 — verbs that writers rotate for one action. Each group holds only
# words that are not in NOT_APPROVED; those already get a 1.1 error. Words
# with a common second meaning stay out: "correct" (adjective), "display"
# (noun for a screen).
SYNONYM_GROUPS = [
    ("check", "confirm", "validate"),
    ("delete", "remove", "erase"),
    ("start", "launch", "begin"),
    ("fix", "repair"),
    ("send", "transmit"),
    ("get", "retrieve", "fetch"),
]

IRREGULAR_FORMS = {
    "begin": ("began", "begun", "beginning"),
    "send": ("sent",),
    "get": ("got", "gotten", "getting"),
    "transmit": ("transmitted", "transmitting"),
}


def _verb_forms(verb):
    """Base, -s, -ed, and -ing forms of a regular verb, plus known irregulars."""
    if verb.endswith("e"):
        forms = {verb, verb + "s", verb + "d", verb[:-1] + "ing"}
    elif verb.endswith(("ch", "sh", "x")):
        forms = {verb, verb + "es", verb + "ed", verb + "ing"}
    else:
        forms = {verb, verb + "s", verb + "ed", verb + "ing"}
    forms.update(IRREGULAR_FORMS.get(verb, ()))
    return forms


# word form -> (group index, base verb)
SYNONYM_FORMS = {
    form: (index, verb)
    for index, group in enumerate(SYNONYM_GROUPS)
    for verb in group
    for form in _verb_forms(verb)
}

LATIN = {
    "e.g.": "for example", "i.e.": "that is", "etc.": "and so on (or list them)",
    "et al.": "and others", "vs.": "compared to", "n.b.": "note",
    "ad hoc": "for this purpose", "per se": "omit it",
}

# -ing words that are established technical nouns, not gerunds
ING_ALLOWED = {
    "bearing", "bearings", "housing", "housings", "coupling", "couplings",
    "wiring", "casing", "casings", "tubing", "piping", "fitting", "fittings",
    "string", "strings", "thing", "things", "ring", "rings", "spring",
    "springs", "wing", "wings", "during", "morning", "engineering",
    "warning", "warnings", "setting", "settings", "building", "buildings",
    "ceiling", "opening", "openings", "reading", "readings", "heading",
    "headings", "meaning", "meanings", "logging", "training", "padding",
    "encoding", "encodings", "mapping", "mappings", "binding", "bindings",
    "listing", "listings", "sing", "king", "swing", "everything", "nothing",
    "something", "anything", "according", "outstanding", "notwithstanding",
}

BE_FORMS = {"is", "are", "was", "were", "be", "been", "being", "am"}
HAVE_FORMS = {"have", "has", "had"}

IRREGULAR_PARTICIPLES = {
    "done", "made", "put", "set", "run", "sent", "kept", "held", "left",
    "found", "built", "shown", "given", "taken", "written", "read", "seen",
    "known", "lost", "met", "paid", "told", "brought", "bought", "caught",
    "chosen", "driven", "drawn", "fallen", "gone", "grown", "hidden", "hit",
    "cut", "let", "shut", "split", "spread", "thrown", "worn", "broken",
    "spoken", "frozen", "stolen", "woken", "torn", "born",
}

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
# Split on . ! ? followed by whitespace, ignoring common abbreviations.
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
ABBREV_TAIL_RE = re.compile(
    r"\b(e\.g|i\.e|etc|vs|Mr|Mrs|Dr|Fig|No|approx|min|max|sec)\.$", re.I
)


def is_participle(word):
    w = word.lower()
    return w in IRREGULAR_PARTICIPLES or (len(w) > 4 and w.endswith("ed"))


# A word that ends in -ing after one of these is a gerund, not a noun.
# "of", "for", "on", "in", "to" are left out: "the cost of sharding" is a noun.
GERUND_PREPOSITIONS = {
    "by", "before", "after", "without", "while", "when", "upon", "instead",
    "besides", "despite",
}

# word/word with lowercase words on both sides: and/or, read/write, on/off.
# Paths (../how-to), abbreviations (I/O), and units (frames/s) do not match.
AND_OR_SLASH_RE = re.compile(r"(?<![\w./-])[a-z]{2,}/[a-z]{2,}(?![\w./-])")


def _blocks(text):
    """Yield (joined_text, first_line_number) for each paragraph or list item.

    A sentence wrapped over several lines must be measured as one sentence, so
    lines are joined before they are split into sentences. A new list item or a
    blank line starts a new block.
    """
    buf, start = [], 1
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        starts_item = bool(re.match(r"^([-*+]|\d+[.)])\s", stripped))
        if not stripped or stripped.startswith("#") or starts_item:
            if buf:
                yield " ".join(buf), start
                buf = []
        if not stripped:
            continue
        if stripped.startswith("#"):
            yield stripped, lineno
            continue
        if not buf:
            start = lineno
        buf.append(stripped)
    if buf:
        yield " ".join(buf), start


def split_sentences(text):
    """Yield (sentence, line_number)."""
    for block, start in _blocks(text):
        parts = SENT_SPLIT_RE.split(block)
        buf = ""
        for part in parts:
            buf = (buf + " " + part).strip() if buf else part
            # "1." of a numbered list item is not a sentence end.
            if ABBREV_TAIL_RE.search(buf) or re.fullmatch(r"\d+[.)]", buf):
                continue
            if buf.strip():
                yield buf.strip(), start
            buf = ""
        if buf.strip():
            yield buf.strip(), start


def strip_code(text):
    """Blank out fenced code blocks, inline code, and URLs; keep line count."""
    def blank(match):
        return re.sub(r"[^\n]", " ", match.group(0))

    text = re.sub(r"```.*?```", blank, text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", blank, text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", blank, text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"^(?: {4}|\t).*$", blank, text, flags=re.M)
    # Table rows are not sentences.
    text = re.sub(r"^\s*\|.*$", blank, text, flags=re.M)
    return text


def is_list_item(sentence):
    return bool(re.match(r"^([-*+]|\d+[.)])\s", sentence))


def is_heading(sentence):
    return sentence.startswith("#") or bool(re.match(r"^[|:\-\s]+$", sentence))


# ---------------------------------------------------------------- the checks

def check_sentence(sentence, lineno, opts, approved, extra_terms):
    out = []

    def flag(rule, message, severity="error"):
        out.append(Finding(lineno, rule, severity, message, sentence))

    body = re.sub(r"^([-*+]|\d+[.)])\s+", "", sentence)
    words = WORD_RE.findall(body)
    lower = [w.lower() for w in words]
    if not words:
        return out

    instruction = opts.procedural or is_list_item(sentence)

    # Rule 4.1 — sentence length
    limit = 20 if instruction else 25
    if len(words) > limit:
        kind = "an instruction" if limit == 20 else "a description"
        flag("4.1", f"{len(words)} words in {kind} (limit {limit})")

    # Rule 1.5 — -ing forms used as verbs. A bare -ing word is as often a
    # noun (sibling, fuzzing) as a gerund, so only flag the positions where
    # it must be a gerund: at the start of the sentence, or after a
    # preposition. "be + -ing" is rule 1.6 below.
    def is_gerund_candidate(word, lw):
        return (
            lw.endswith("ing") and len(lw) > 4
            and lw not in ING_ALLOWED and lw not in extra_terms
        )

    if is_gerund_candidate(words[0], lower[0]):
        flag("1.5", f"-ing form '{words[0]}' starts the sentence")
    for i in range(1, len(words)):
        if lower[i - 1] in GERUND_PREPOSITIONS and is_gerund_candidate(words[i], lower[i]):
            flag("1.5", f"-ing form '{lower[i - 1]} {words[i]}'")

    # Rule 1.6 — compound tenses
    def after_modal(i):
        """True if a modal comes before position i, with at most one 'not'."""
        j = i - 1
        if j >= 0 and lower[j] in NEGATIONS:
            j -= 1
        return j >= 0 and lower[j] in MODALS

    for i, lw in enumerate(lower[:-1]):
        nxt = lower[i + 1]
        if lw in HAVE_FORMS and (is_participle(nxt) or nxt == "been"):
            if not after_modal(i):
                flag("1.6", f"perfect tense '{lw} {nxt}'")
        if lw in BE_FORMS and nxt.endswith("ing") and nxt not in ING_ALLOWED:
            flag("1.6", f"continuous tense '{lw} {nxt}'")

    # Rule 3.1/3.2 — passive voice. An error in an instruction; a warning in
    # descriptive text, where STE permits the passive when the agent is
    # unknown or unimportant and where "is configured" is often a state.
    passive_severity = "error" if instruction else "warning"
    for i, lw in enumerate(lower[:-1]):
        if lw in BE_FORMS and is_participle(lower[i + 1]):
            flag("3.1", f"passive '{lw} {lower[i + 1]}'", passive_severity)
        if lw in BE_FORMS and i + 2 < len(lower) and is_participle(lower[i + 2]):
            if lower[i + 1] in {"not", "also", "then", "already", "now"}:
                flag("3.1", f"passive '{lw} {lower[i+1]} {lower[i+2]}'", passive_severity)

    # Rule 1.1/1.3 — non-approved words
    for w, lw in zip(words, lower):
        if lw in extra_terms:
            continue
        if lw in HEDGES:
            flag("1.1", f"'{w}' -> use '{NOT_APPROVED[lw]}'; keep the hedge", "warning")
        elif lw in NOT_APPROVED:
            flag("1.1", f"'{w}' -> use '{NOT_APPROVED[lw]}'")
        elif approved is not None and lw not in approved:
            flag("1.1", f"'{w}' is not in the approved dictionary")

    # Rule 1.9 — Latin and abbreviations
    low_body = " " + body.lower() + " "
    for term, better in LATIN.items():
        if term in low_body:
            flag("1.9", f"'{term}' -> use '{better}'")

    # Rule 4.2 — more than one instruction
    if re.match(r"^[A-Z][a-z]+\s", body) and re.search(r",?\s+and\s+then\s", low_body):
        flag("4.2", "two instructions in one sentence")

    # Rule 4.4 — trailing condition. Heuristic: a warning.
    if re.search(r"\S,?\s+(if|when|unless)\s+\w", body[10:], re.I):
        if not re.match(r"^(if|when|unless)\b", body, re.I):
            flag("4.4", "condition after the instruction; move it to the front", "warning")

    # Rule 8.6 — semicolons
    if ";" in body:
        flag("8.6", "semicolon; split the sentence")

    # Rule 8.2 — and/or slash
    match = AND_OR_SLASH_RE.search(body)
    if match:
        flag("8.2", f"slash in '{match.group(0)}'; write 'and' or 'or'")

    # Rule 2.1 (noun clusters) is not checked. Without part-of-speech data a
    # run of content words is not a noun cluster often enough to be useful.

    return out


def synonym_findings(sentences, extra_terms):
    """Rule 1.4 — two words from one SYNONYM_GROUP in the same file.

    The word used most often in the file is the one to keep (the first one
    used wins a tie). Each sentence that uses another word of the group gets
    a warning: "remove" and "delete" can be two real actions, so only the
    author can say that they are one.
    """
    uses = collections.defaultdict(list)  # group -> [(verb, sentence, line)]
    for sentence, lineno in sentences:
        for word in WORD_RE.findall(sentence):
            lw = word.lower()
            if lw in SYNONYM_FORMS and lw not in extra_terms:
                group, verb = SYNONYM_FORMS[lw]
                uses[group].append((verb, sentence, lineno))

    out = []
    for group_uses in uses.values():
        counts = collections.Counter(verb for verb, _, _ in group_uses)
        if len(counts) < 2:
            continue
        first_seen = [verb for verb, _, _ in group_uses]
        keep = max(counts, key=lambda v: (counts[v], -first_seen.index(v)))
        flagged = set()
        for verb, sentence, lineno in group_uses:
            if verb != keep and (lineno, sentence, verb) not in flagged:
                flagged.add((lineno, sentence, verb))
                out.append(Finding(
                    lineno, "1.4", "warning",
                    f"'{verb}' and '{keep}' in one file; use '{keep}' "
                    f"if they are one action", sentence,
                ))
    return out


def check_text(text, opts, approved, extra_terms):
    text = strip_code(text)
    findings = []
    prose = []
    para_sentences, para_start = 0, None
    for sentence, lineno in split_sentences(text):
        if is_heading(sentence):
            para_sentences, para_start = 0, None
            continue
        if para_start is None:
            para_start = lineno
        para_sentences += 1
        findings.extend(check_sentence(sentence, lineno, opts, approved, extra_terms))
        prose.append((sentence, lineno))

    findings.extend(synonym_findings(prose, extra_terms))

    # Rule 6.1 — paragraph length
    for block_start, count in paragraph_sizes(text):
        if count > 6:
            findings.append(Finding(
                block_start, "6.1", "error",
                f"{count} sentences in one paragraph (limit 6)", "",
            ))
    findings.sort(key=lambda f: (f.line, f.rule))
    return findings


# ---------------------------------------------------------------- reporting

def count_by_severity(findings):
    counts = collections.Counter(f.severity for f in findings)
    return counts["error"], counts["warning"]


def summary(errors, warnings):
    e = "error" if errors == 1 else "errors"
    w = "warning" if warnings == 1 else "warnings"
    return f"{errors} {e}, {warnings} {w}"


def format_report(path, findings, width=80):
    """One line per sentence: all its findings, then the sentence once.

    The reader is usually a model that must fix the sentence. It needs the
    line, the rules, and the text once, not the text repeated per finding.
    """
    lines = []
    if findings:
        lines.append(path)
        groups = collections.OrderedDict()
        for f in findings:
            groups.setdefault((f.line, f.sentence), []).append(f)
        for (lineno, sentence), group in groups.items():
            tags = " ".join(
                f"[{f.severity[0].upper()}{f.rule} {f.message}]" for f in group
            )
            text = f" :: {sentence[:width]}" if sentence else ""
            lines.append(f"  L{lineno} {tags}{text}")
    errors, warnings = count_by_severity(findings)
    lines.append(f"{summary(errors, warnings)} in {path}")
    return "\n".join(lines)


def format_json(path, findings):
    return json.dumps([
        {
            "file": path, "line": f.line, "rule": f.rule,
            "severity": f.severity, "message": f.message, "sentence": f.sentence,
        }
        for f in findings
    ], indent=1)


def paragraph_sizes(text):
    lineno, buf, start = 0, [], 1
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            if not buf:
                start = lineno
            buf.append(line.strip())
        elif buf:
            joined = " ".join(buf)
            if not joined.startswith("#"):
                yield start, len([s for s in SENT_SPLIT_RE.split(joined) if s.strip()])
            buf = []
    if buf:
        joined = " ".join(buf)
        if not joined.startswith("#"):
            yield start, len([s for s in SENT_SPLIT_RE.split(joined) if s.strip()])


def load_words(path):
    with open(path, encoding="utf-8") as handle:
        return {
            line.strip().lower()
            for line in handle
            if line.strip() and not line.startswith("#")
        }


def main():
    parser = argparse.ArgumentParser(description="Heuristic ASD-STE100 checker.")
    parser.add_argument("files", nargs="+", help="files to check, or - for stdin")
    parser.add_argument(
        "--procedural", action="store_true",
        help="treat every sentence as an instruction (20-word limit)",
    )
    parser.add_argument(
        "--dictionary", metavar="FILE",
        help="approved words, one per line; every other word is flagged",
    )
    parser.add_argument(
        "--terms", metavar="FILE",
        help="project terms to never flag, one per line "
             "(default: references/project-terms.txt next to this script)",
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="text: one line per sentence (default); json: one object per finding",
    )
    parser.add_argument(
        "--fail-on", choices=SEVERITIES, default="error",
        help="lowest severity that sets exit code 1 (default: error)",
    )
    parser.add_argument("--quiet", action="store_true", help="only print the count")
    opts = parser.parse_args()

    approved = load_words(opts.dictionary) if opts.dictionary else None

    terms_path = opts.terms
    if not terms_path:
        guess = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "references", "project-terms.txt",
        )
        terms_path = guess if os.path.exists(guess) else None
    extra_terms = load_words(terms_path) if terms_path else set()

    total_errors = total_warnings = 0
    json_records = []
    for path in opts.files:
        text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        findings = check_text(text, opts, approved, extra_terms)
        errors, warnings = count_by_severity(findings)
        total_errors += errors
        total_warnings += warnings
        if opts.format == "json":
            json_records.extend(json.loads(format_json(path, findings)))
        elif findings and not opts.quiet:
            print(format_report(path, findings))

    if opts.format == "json":
        print(json.dumps(json_records, indent=1))
    else:
        print(f"{summary(total_errors, total_warnings)}.")

    failing = total_errors if opts.fail_on == "error" else total_errors + total_warnings
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
