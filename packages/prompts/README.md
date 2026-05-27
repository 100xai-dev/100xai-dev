# Prompt Package

This package is intentionally editable by the prompt/content owner.

Each prompt folder should contain:

- the prompt markdown
- expected input JSON shape
- expected output JSON shape
- at least one good example
- at least one bad example or rejection case

Application code should load prompts from this package instead of hard-coding them.
