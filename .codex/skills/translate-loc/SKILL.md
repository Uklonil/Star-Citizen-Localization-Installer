---
name: translate-loc
description: Translate localization files while preserving keys, placeholders, escaped sequences, markup, and file structure.
---

# Purpose
Use this skill for localization files such as `.ini`, `.cfg`, `.json`, `.xml`, and other key-value resource files.

# When to use
Use this skill when the task involves:
- translating game strings
- creating a new language file from an existing source file
- updating a translated file from an upstream English file
- reviewing localization diffs for formatting safety

# Main workflow
1. Identify the file format and encoding.
2. Read `references/glossary.md` before translating.
3. Translate only user-facing text.
4. Preserve keys, placeholders, escaped sequences, tags, wrappers, comments, and ordering.
5. Save output to the requested destination path.
6. Run `scripts/checks.py SOURCE DESTINATION`.
7. Report:
   - files touched
   - total lines
   - translated entries
   - ambiguous strings
   - validation output

# Format rules
## INI-like files
For lines shaped like `KEY=value`:
- preserve `KEY=`
- translate only `value`
- preserve spacing exactly if spacing is significant in the file

## JSON and XML
- preserve structural syntax exactly
- translate only string values that are user-facing
- do not rename fields, tags, or attributes unless explicitly requested

# Preservation checklist
Never alter:
- `%s`, `%d`, `%i`, `%f`
- `{0}`, `{1}`, `{name}`, `{player}`
- `\n`, `\t`, `\"`
- `[[token]]`, `[[/save]]`, or similar game markup
- HTML/XML tags
- developer comments
- ordering of entries

# Translation style
- Spanish (Spain) by default
- concise UI wording
- natural gameplay phrasing
- consistent use of glossary terms
- avoid over-translating lore names

# Batch mode
For very large files:
- translate in batches of 300 to 800 lines
- validate each batch
- keep a running list of doubtful terms

# Optional helper commands
Example validation:
```bash
python .codex/skills/translate-loc/scripts/checks.py source.ini translated.ini
```

Example explicit prompt:
```text
Use the translate-loc skill to translate `Data/Localization/english/global.ini` into Spanish (Spain).
Keep keys and placeholders intact, save it to `Data/Localization/spanish/global.ini`,
then run validation and report ambiguous strings.
```
