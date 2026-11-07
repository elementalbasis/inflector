# Inflector

Generate inflection tables from model words, either directly from principal
parts or by resolving `@infl` references in a Lexerat dictionary.
Requires Python 3.10+ and PyYAML (`pip install PyYAML`).

## Direct use

```bash
python inflect.py stauros --model viros
python inflect.py 'jekmi, ikmos; jeksym, iksme; jejoka, jeikme' --model megmi
python inflect.py '@key(lipnumi; lipym; leloipa, lelipme)' --model lipnumi
```

A dictionary remains optional. Without `--model`, the existing recognition
suffixes select a model when there is exactly one match. Ambiguous matches
require `--model`. `--typ noun|adjective|verb` can restrict recognition.

## Lexerat dictionary

Export your raw lexicon using the updated Lexerat, then look up any lemma:

```bash
python ../lexerat/lexerat.py /path/to/raw/*.txt -o dictionary.json
python inflect.py apojekmi --dictionary dictionary.json
python inflect.py opidukmi --dictionary dictionary.json
```

`--dictionary` accepts one or more Lexerat JSON files, raw text files, or
directories of `*.txt` files. Raw input requires Lexerat to be importable,
or its repository to be alongside this repository. JSON input needs only
PyYAML. Put the positional word before `--dictionary`, whose file list is
variable length.

A dictionary entry has a flat `forms` list, optional `principal_parts` groups,
and an optional `infl` reference. The first form is the lemma. Old JSON without
`principal_parts` still supports complete, flat principal-part lists.

Given:

```text
@key(jekmi, ikmos; jeksym, iksme; jejoka, jeikme) @infl(megmi)
@key(apojekmi) @infl(jekmi)
```

the resolver first adapts the *megmi* table to *jekmi*'s principal parts, then
prefixes that resulting table with `apo`. Every step retains the intermediate
stems: the perfect is `apojejoka`. A bare compound inherits every cell,
including suppletive stems. Its lemma must end with the referenced lemma;
otherwise supply principal parts explicitly. Prefix attachment is literal;
this does not introduce additional sound-change or sandhi rules.

A self-reference such as `@infl(megmi)` stops at the registered YAML model.
Any principal parts supplied by that entry adapt the model's pattern, so the
lexicon's explicit parts take precedence over the example words in the YAML.
A self-reference without a registered table is an error. Other cycles,
missing targets, and duplicate target lemmas also produce errors, naming the
problem rather than silently choosing another model.

For verbs, semicolons separate present, aorist, and perfect groups, and commas
separate anchors within each group. Most athematic models use 1sg and 1pl per
group. *Esmi* additionally uses present 3pl. A group may supply fewer anchors:

```text
@key(sjostrunumi; sjostrum; sjostestruka) @infl(strunumi)
```

This supplies 1sg for each tense; the other forms are inferred from the model.
Without semicolons, supply the model's complete ordered list. Nouns and
adjectives use their complete ordered lists with either separator.

You can also use a resolved dictionary lemma as an explicit model:

```bash
python inflect.py upojekmi --model jekmi --dictionary dictionary.json
```

`--models DIRECTORY` selects an alternative directory of registered YAML
models. The registered verbs include `dekmi`, `edmi`, `esmi`, and `imi`.

## Python API

```python
from inflect import Lexicon, load_dictionary

lexicon = Lexicon(load_dictionary(['dictionary.json']))
table = lexicon.resolve('apojekmi').table
```

`resolve` caches complete models within a lexicon. Dictionary entries retain
immediate references, so their JSON has no object-reference cycles.

## Tests

```bash
python -m unittest discover -s tests -v
```
