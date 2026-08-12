# ASD-STE100 rules with before/after examples

Load this file only when a rule in `SKILL.md` is ambiguous, or when the user
asks for a rule-by-rule review of a document.

This is a working paraphrase of the rule set, not the specification text.
The specification itself is free from https://asd-ste100.org.

---

## 1. Words

### 1.1 Approved words only

Every word must be in the approved dictionary, or be a technical name, or be a
technical verb defined by your project. Everything else has an approved
alternative.

- ✗ The system will subsequently commence the calibration procedure.
- ✓ The system then starts the calibration procedure.

### 1.2 One part of speech per word

A word that the dictionary lists as a noun stays a noun. A word listed as a
verb stays a verb.

- ✗ Oil the bearing. / Test the unit for a leak.
- ✓ Apply oil to the bearing. / Do a test of the unit for a leak.

### 1.3 One approved meaning per word

`follow` means "come after", never "obey". `since` means "from that time",
never "because".

- ✗ Follow the safety instructions.
- ✓ Obey the safety instructions.

### 1.4 No synonyms

Choose one term per concept and repeat it. Repetition is correct in STE;
variation is a defect.

- ✗ Remove the panel. Then detach the second cover and take off the seal.
- ✓ Remove the panel. Then remove the second cover and remove the seal.

### 1.5 No `-ing` forms

No gerunds, no present participles, no progressive tenses. Rewrite with a
finite verb, a `that` clause, or a noun.

- ✗ Before installing the pump, make sure the line is empty.
- ✓ Before you install the pump, make sure that the line is empty.

- ✗ The pump is operating at full pressure.
- ✓ The pump operates at full pressure.

Exception: established technical names — `bearing`, `housing`, `coupling`,
`wiring`, `string`, `logging` (as a noun for the subsystem).

### 1.6 Simple tenses only

Simple present, simple past, simple future. No `has done`, no `had done`, no
`is doing`, no `will be doing`.

- ✗ The controller has detected a fault.
- ✓ The controller detected a fault.

### 1.7 Keep every word

Do not drop articles, `that`, `which`, or auxiliary verbs to save space.

- ✗ Make sure valve closed before start.
- ✓ Make sure that the valve is closed before you start.

### 1.8 Abbreviations

Write the full term at first use with the abbreviation in parentheses. Then use
the abbreviation. Do not invent abbreviations that are not already standard in
your domain.

### 1.9 No Latin, idiom, or figurative language

- ✗ Kill the process, e.g. with SIGTERM.
- ✓ Stop the process. For example, send SIGTERM.

---

## 2. Noun clusters

### 2.1 Three nouns maximum

Break longer clusters with prepositions, and put the head noun first.

- ✗ main fuel line pressure sensor housing
- ✓ the housing of the pressure sensor in the main fuel line

### 2.2 Define a cluster you must keep

If a three-noun cluster is a product term, define it once and then use it
consistently.

---

## 3. Verbs

### 3.1 Active voice in procedures — always

- ✗ The bolts must be tightened to 30 N·m.
- ✓ Tighten the bolts to 30 N·m.

### 3.2 Active voice in descriptions — by default

Passive is permitted only when the agent is unknown or irrelevant and the
active form would be worse.

- ✗ The signal is received by the decoder.
- ✓ The decoder receives the signal.

### 3.3 Imperative for instructions

Start with the verb. No `you should`, no `please`, no `it is recommended
that`.

- ✗ You should now restart the service.
- ✓ Restart the service.

### 3.4 No past participle as an adjective unless approved

- ✗ the reduced pressure
- ✓ the low pressure / the pressure that decreased

---

## 4. Sentences

### 4.1 Length

- Instructions: 20 words maximum.
- Descriptions: 25 words maximum.

### 4.2 One instruction per sentence

Two only when the actions happen at the same time.

- ✗ Remove the cover and disconnect the cable and drain the tank.
- ✓ 1. Remove the cover. 2. Disconnect the cable. 3. Drain the tank.

### 4.3 One topic per sentence

### 4.4 Condition first

- ✗ Close the valve if the warning light comes on.
- ✓ If the warning light comes on, close the valve.

### 4.5 Connect related sentences

Use `then`, `also`, `but` to show the relation. Do not leave the reader to
infer it.

---

## 5. Procedures

### 5.1 Numbered vertical list, one step per item

### 5.2 Each step is one imperative sentence

### 5.3 State the conditions before the step, not inside it

### 5.4 Put the result of a step in a separate sentence

- ✓ Turn the switch to ON. The green light comes on.

### 5.5 Do not mix description into a procedure

Explanation goes in a preceding descriptive paragraph.

---

## 6. Descriptive writing

### 6.1 Six sentences maximum per paragraph

### 6.2 One topic per paragraph

### 6.3 Key sentence first

### 6.4 Vary paragraph length, but never a one-sentence paragraph run

---

## 7. Safety

### 7.1 A warning covers injury or death. A caution covers damage to equipment.

### 7.2 The warning goes before the step it applies to.

### 7.3 Start with a clear command, then the reason.

- ✗ The housing may reach 200 °C during operation, so care should be taken.
- ✓ Do not touch the housing. The housing becomes hot and can burn you.

### 7.4 One warning per hazard. Do not stack unrelated hazards in one block.

---

## 8. Punctuation and numbers

### 8.1 Hyphenate a compound modifier: `a 30-second delay`.

### 8.2 Do not use a slash to mean "and/or". Write it out.

### 8.3 Use a space between a number and its unit: `30 N·m`, `5 mm`.

### 8.4 Do not start a sentence with a numeral.

### 8.5 Avoid parentheses in instructions. Make it a separate sentence.

### 8.6 No semicolons. Split the sentence.

---

## 9. Practices for this project

Add your own project terms here — approved verbs, product names, and the
three-noun clusters you decided to keep. The checker reads
`references/project-terms.txt` if it exists, and stops flagging anything listed
there.
