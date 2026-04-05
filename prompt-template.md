# Prompt template for Codex: translate a localization file

Use the `translate-loc` skill to translate the following localization file from English to Spanish (Spain):

SOURCE: `Data/Localization/english/global.ini`
DESTINATION: `Data/Localization/spanish/global.ini`

Mandatory rules:
- Do not modify any key to the left of `=`.
- Translate only the user-facing value.
- Preserve placeholders exactly: `%s`, `%d`, `%i`, `%f`, `{0}`, `{name}`.
- Preserve escaped sequences exactly: `\n`, `\t`, `\"`.
- Preserve tags, wrappers, and markup exactly, including `[[...]]` and `<...>`.
- Keep comments, blank lines, order, and file structure unchanged.
- Use `references/glossary.md` for approved terminology.
- Do not translate Star Citizen proper nouns unless the glossary explicitly says so.

Workflow:
1. Read the glossary.
2. Translate the file.
3. Save the result to the destination path.
4. Run:
   `python .codex/skills/translate-loc/scripts/checks.py "Data/Localization/english/global.ini" "Data/Localization/spanish/global.ini"`
5. Report:
   - total lines
   - number of translated entries
   - ambiguous strings
   - validation result

If the file is too large, process it in batches of 500 lines and validate after each batch.
