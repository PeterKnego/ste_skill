# What this skill can and cannot guarantee

ASD-STE100 has two halves. This skill covers one of them well and the other
only partly.

## Part 1 — the writing rules

Issue 9 (January 2025) has 53 writing rules. They cover word choice, part of
speech, tense, voice, sentence length, procedures, descriptive writing, safety
instructions, and punctuation. These are structural rules. Claude applies them
reliably, and `scripts/ste_check.py` catches the mechanical ones.

## Part 2 — the dictionary

The specification also carries a dictionary of roughly 900 approved words, each
with one approved part of speech and one approved meaning, plus a much longer
list of non-approved words with their approved alternatives.

Claude does **not** have that dictionary memorised word for word. The preferred
words table in `SKILL.md` is a curated subset of the well-known cases. It will
catch the common offenders. It will not tell you that a particular uncommon word
is absent from the approved list.

If you need real dictionary compliance:

1. Get the official specification free from https://asd-ste100.org — fill in the
   request form and ASD emails you the PDF. It has been free of charge since
   Issue 6 (2013).
2. Extract the approved words into a plain text file, one word per line.
3. Run the checker against it:

   ```
   python3 scripts/ste_check.py --dictionary approved-words.txt FILE
   ```

   Every word not in the list gets flagged. Add your project's technical names
   to the same file so they stop being flagged.

Do not paste the specification PDF into the repository. It is free but it is
copyrighted, and ASD's terms cover redistribution.

## Certified checkers

For contractual STE compliance, an LLM is not the tool. Commercial checkers with
the licensed dictionary built in:

- HyperSTE (Etteplan)
- Congree
- Acrolinx
- TechScribe's free term checker — https://www.simplified-english.co.uk

Use Claude to write the draft in STE style, then run the certified checker.
