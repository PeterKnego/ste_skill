---
name: ste
description: Write or rewrite English prose to ASD-STE100 Simplified Technical English. Invoke with /ste.
argument-hint: "[file or text]"
disable-model-invocation: true
allowed-tools: Read Edit Write Grep Glob Bash(python3 *)
---

# ASD-STE100 Simplified Technical English

Apply these rules to English prose you write or edit. Do not apply them to
code, identifiers, quoted user input, or third-party text you are only citing.

## Rules

**Words**

1. One word, one meaning. Pick one verb for an action and use it everywhere.
   Never vary word choice for style.
2. One word, one part of speech. `Apply the oil.` not `Oil the bearing.`
3. No synonyms. If you wrote `remove`, never later write `detach` or `take off`
   for the same action.
4. No `-ing` forms. No gerunds, no present participles, no progressive tenses.
   `Before you install the pump` not `Before installing the pump`.
   Exception: an established technical name (`bearing`, `housing`, `string`).
5. Simple tenses only: simple present, simple past, simple future. No perfect
   tenses, no continuous tenses. `The valve closed.` not `The valve has closed.`
6. Keep articles, `that`, and relative pronouns. Do not compress.
   `Make sure that the switch is off.` not `Make sure switch off.`
7. No noun clusters longer than three nouns. Break the fourth noun out with a
   preposition: `the pressure sensor of the main fuel line`, not
   `the main fuel line pressure sensor`.
8. Spell out abbreviations at first use. Do not invent new ones.
9. No Latin (`e.g.`, `i.e.`, `via`, `per`), no idioms, no metaphors, no
   humour, no rhetorical questions.

**Sentences**

10. Active voice always in instructions. Active voice by default in
    descriptions. `Turn the valve.` not `The valve must be turned.`
11. Instructions: 20 words maximum. Descriptions: 25 words maximum.
12. One instruction per sentence. Two only when the actions are simultaneous.
13. One topic per sentence. Split anything with `and` joining two ideas.
14. Start an instruction with the verb, in the imperative.
15. Put the condition before the instruction: `If the light is on, close the
    valve.` not `Close the valve if the light is on.`

**Paragraphs and structure**

16. Six sentences maximum per paragraph.
17. One topic per paragraph, and the key sentence comes first.
18. Use a vertical numbered list for a sequence of steps. Use a bulleted list
    for an unordered set.
19. Put a warning or caution before the step it applies to, never after.
20. Write a warning as a command: `Do not touch the housing. The housing is
    hot.`

## Preferred words

Use the left column, never the right.

| Use | Not |
| --- | --- |
| use | utilize, leverage, employ |
| start | commence, initiate, begin |
| stop | terminate, cease, halt |
| before / after | prior to, subsequent to, following |
| to | in order to, so as to |
| do | perform, execute, carry out, conduct |
| make sure that | ensure, verify that, confirm that |
| get | obtain, acquire, procure |
| enough | sufficient, adequate |
| about | approximately, regarding, concerning |
| help | facilitate, assist, aid |
| show | demonstrate, illustrate, indicate |
| change | modify, alter, adjust |
| let | allow, permit, enable |
| tell | inform, advise, notify |
| find | locate, identify, determine |
| need | require, necessitate |
| if | in the event that, should |
| because | due to the fact that, owing to, since (causal) |
| also | additionally, furthermore, moreover |
| but | however, nevertheless, nonetheless |
| then | subsequently, thereafter |
| many / much | numerous, a great deal of, significant |
| part | component, element |
| fault | anomaly, discrepancy, issue |
| obey | comply with, adhere to |
| put | position, install (when it just means put) |
| examine | inspect, check over |

## How to work

**When you write new prose:** follow the rules from the first draft. Do not
write a normal draft and then simplify it.

**When you rewrite existing text:** keep every fact. STE removes ambiguity, not
content. If a rule would change the meaning, keep the meaning and tell the user
which rule you broke and why.

**Always run the checker on prose you produced:**

```
python3 scripts/ste_check.py FILE
```

Fix everything it reports, then run it again. The checker is a heuristic, not a
certification — it catches structure and word choice, not full dictionary
compliance. See `references/limits.md`.

For the full rule set with examples, read `references/rules.md`. Load it only
when a rule above is unclear or the user asks for a rule-by-rule review.
