#!/usr/bin/env python3
"""Heuristic ASD-STE100 checker. Python 3.8+, standard library only.

Usage:
    python3 ste_check.py FILE [FILE ...]
    python3 ste_check.py --procedural FILE      # 20-word limit everywhere
    python3 ste_check.py --dictionary approved-words.txt FILE
    cat draft.md | python3 ste_check.py -

Exit code 1 if any violation is found, so it works as a pre-commit hook or in
CI. This is a heuristic. It catches structure and common word choice, not full
dictionary compliance. See references/limits.md.
"""

import argparse
import os
import re
import sys

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
            if ABBREV_TAIL_RE.search(buf):
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
    return text


def is_list_item(sentence):
    return bool(re.match(r"^([-*+]|\d+[.)])\s", sentence))


def is_heading(sentence):
    return sentence.startswith("#") or bool(re.match(r"^[|:\-\s]+$", sentence))


# ---------------------------------------------------------------- the checks

def check_sentence(sentence, lineno, opts, approved, extra_terms):
    out = []

    def flag(rule, message):
        out.append((lineno, rule, message, sentence))

    body = re.sub(r"^([-*+]|\d+[.)])\s+", "", sentence)
    words = WORD_RE.findall(body)
    lower = [w.lower() for w in words]
    if not words:
        return out

    # Rule 4.1 — sentence length
    limit = 20 if (opts.procedural or is_list_item(sentence)) else 25
    if len(words) > limit:
        kind = "instruction" if limit == 20 else "description"
        flag("4.1", f"{len(words)} words in a {kind} (limit {limit})")

    # Rule 1.5 — -ing forms
    for w, lw in zip(words, lower):
        if lw.endswith("ing") and lw not in ING_ALLOWED and lw not in extra_terms:
            if len(lw) > 4 and w[0].islower():
                flag("1.5", f"-ing form '{w}'")

    # Rule 1.6 — compound tenses
    for i, lw in enumerate(lower[:-1]):
        nxt = lower[i + 1]
        if lw in HAVE_FORMS and (is_participle(nxt) or nxt == "been"):
            flag("1.6", f"perfect tense '{lw} {nxt}'")
        if lw in BE_FORMS and nxt.endswith("ing") and nxt not in ING_ALLOWED:
            flag("1.6", f"continuous tense '{lw} {nxt}'")

    # Rule 3.1/3.2 — passive voice
    for i, lw in enumerate(lower[:-1]):
        if lw in BE_FORMS and is_participle(lower[i + 1]):
            flag("3.1", f"passive voice '{lw} {lower[i + 1]}'")
        if lw in BE_FORMS and i + 2 < len(lower) and is_participle(lower[i + 2]):
            if lower[i + 1] in {"not", "also", "then", "already", "now"}:
                flag("3.1", f"passive voice '{lw} {lower[i+1]} {lower[i+2]}'")

    # Rule 1.1/1.3 — non-approved words
    for w, lw in zip(words, lower):
        if lw in extra_terms:
            continue
        if lw in NOT_APPROVED:
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

    # Rule 4.4 — trailing condition
    if re.search(r"\S,?\s+(if|when|unless)\s+\w", body[10:], re.I):
        if not re.match(r"^(if|when|unless)\b", body, re.I):
            flag("4.4", "condition comes after the instruction; move it to the front")

    # Rule 8.6 — semicolons
    if ";" in body:
        flag("8.6", "semicolon; split the sentence")

    # Rule 8.2 — and/or slash
    if re.search(r"\w/\w", body) and not re.search(r"\w+/\w+\.\w", body):
        flag("8.2", "slash used as and/or; write it out")

    # Rule 2.1 — noun clusters (rough: 4+ consecutive lowercase non-function words)
    function_words = {
        "the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or",
        "with", "from", "by", "as", "is", "are", "was", "were", "be", "that",
        "this", "these", "those", "it", "its", "you", "your", "not", "if",
        "when", "then", "do", "does", "can", "must", "will", "into", "over",
    }
    run = []
    for w in body.split():
        token = WORD_RE.match(w)
        clean = token.group(0).lower() if token else ""
        breaks_run = (
            not clean
            or clean in function_words
            or clean in NOT_APPROVED
            or not clean.isalpha()
            or len(clean) < 3
            or clean.endswith("ly")
            or clean.endswith("ed")
            or clean.endswith("ing")
            or not w[0].islower()
            or w[-1] in ",;:.!?)("
        )
        if breaks_run:
            run = []
            continue
        run.append(clean)
        if len(run) == 4:
            flag("2.1", f"possible 4-noun cluster '{' '.join(run)}'")
            run = []

    return out


def check_text(text, opts, approved, extra_terms):
    text = strip_code(text)
    findings = []
    para_sentences, para_start = 0, None
    for sentence, lineno in split_sentences(text):
        if is_heading(sentence):
            para_sentences, para_start = 0, None
            continue
        if para_start is None:
            para_start = lineno
        para_sentences += 1
        findings.extend(check_sentence(sentence, lineno, opts, approved, extra_terms))

    # Rule 6.1 — paragraph length
    for block_start, count in paragraph_sizes(text):
        if count > 6:
            findings.append(
                (block_start, "6.1", f"{count} sentences in one paragraph (limit 6)", "")
            )
    findings.sort(key=lambda f: (f[0], f[1]))
    return findings


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

    total = 0
    for path in opts.files:
        text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        findings = check_text(text, opts, approved, extra_terms)
        total += len(findings)
        if findings and not opts.quiet:
            print(f"\n{path}")
            last = None
            for lineno, rule, message, sentence in findings:
                if sentence and sentence != last:
                    print(f"  line {lineno}: {sentence[:100]}")
                    last = sentence
                print(f"      [{rule}] {message}")

    label = "violation" if total == 1 else "violations"
    print(f"\n{total} {label}.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
