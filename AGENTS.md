# AGENTS.md

## Scope
This repository contains localization files for Star Citizen and related translation assets.

## Core rule
When translating localization files, change only user-facing text values.
Never change keys, identifiers, ordering, comments, file encoding, or structural syntax.

## Translation target
- Default target language: Spanish (Spain).
- Tone: clear, natural, concise.
- UI labels should be short and readable in constrained interfaces.
- Action verbs in buttons and prompts should be direct and consistent.

## Mandatory preservation rules
Preserve exactly, without rewriting or reordering:
- keys to the left of `=`
- placeholders such as `%s`, `%d`, `%i`, `%f`
- brace variables such as `{0}`, `{name}`, `{player}`
- escaped sequences such as `\n`, `\t`, `\"`
- markup, tags, and wrappers such as `[[...]]`, `<...>`, `&lt;...&gt;`
- file comments and blank lines
- capitalization of fixed tokens, item codes, product names, and internal IDs
- line order

## Lore and terminology
- Do not translate proper nouns from the Star Citizen universe unless the glossary explicitly provides an approved Spanish form.
- Prefer glossary terms over ad hoc wording.
- Keep terminology consistent across files and sessions.

## Ambiguity handling
- If a string is ambiguous, choose the most neutral translation that fits UI and gameplay context.
- Record ambiguous entries in the final report with the original text and chosen translation.

## Validation requirements
After editing a localization file:
1. Verify the line count matches the source.
2. Verify every original key is still present and unchanged.
3. Verify placeholders and escaped sequences are unchanged.
4. Summarize:
   - source file
   - destination file
   - number of entries processed
   - ambiguous strings
   - validation result

## Recommended workflow
For large files, work in batches instead of rewriting everything at once.
Default batch size: 300 to 800 lines unless the user requests otherwise.
Run validation after each batch and once again at the end.
