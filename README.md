# Inflector

Model-word inflection for Danetian. Install the dependencies with:

```bash
python -m pip install -r requirements.txt
```

## Dictionary pipeline

The modules have separate responsibilities:

- `dictionary.py` loads raw files with Lexerat and returns enriched entry copies.
- `inflect.py` supplies model classes and resolves dictionary model references.
- `cli.py` handles command-line arguments and JSON output.

```bash
python cli.py /path/to/raw -o dictionary.json
python cli.py first.txt second.txt --models /path/to/model-words
```

Input is raw Lexerat source: a file, directories of immediate `*.txt` files,
or multiple sources. All sources are parsed together, allowing expression
links between files. Files such as `*.txt.ignore` are not selected by directory
loading. JSON is the enriched output, not a second parsing stage.

Command-line handling has moved out of `inflect.py` and `dictionary.py`.
Invoke `cli.py` to process a dictionary. For individual model operations from
Python, the original model classes remain available.

## Python interface

```python
from dictionary import enrich_dictionary, load_dictionary
from inflect import Inflector, Viros

entries = load_dictionary('/path/to/raw')
engine = Inflector(entries)
table = engine.inflect('apojekmi')

enriched = enrich_dictionary(entries)
standalone_table = Viros().inflect(['stauros'])
```

`enrich_dictionary` returns `InflectedEntry` objects, a subclass of Lexerat's
`Entry` with an `inflections` field. Only lemma entries with nonempty `infl`
values request tables. Untagged entries and expressions remain in the result
with `inflections=None`. The input entries are not modified, and expression
links point to the enriched expression objects.

Use `dataclasses.asdict` to export these objects as JSON, or pass them directly
to Lexerat's existing renderer. Rendering requires Lexerat's optional Jinja2
dependency:

```bash
python -m pip install "lexerat[render] @ git+https://github.com/elementalbasis/lexerat.git@v0.2.1"
```

A custom template can access `entry.inflections`:

```python
from lexerat import render

html = render(enriched, 'dictionary.html.j2')
```

Generating tables does not add table markup to existing templates. The template
must decide how to display each model's nested table structure.

## Model references

Principal parts are an ordered list matching the selected model's `endings`:

```text
@key(megmi, mygmos, megsym, mygsme, memoga, memygme) @infl(megmi)
@key(jekmi, ikmos, jeksym, iksme, jejoka, jeikme) @infl(megmi)
@key(apojekmi) @infl(jekmi)
```

The resolver follows immediate references and adapts each intermediate table.
Here it adapts *megmi* to *jekmi* before prefixing the complete resulting table
with `apo`. Thus the perfect is `apojejoka`. A bare compound may omit its own
principal parts when its lemma ends with the referenced lemma. The prefix is
attached literally to every cell, including suppletive forms; no additional
sound-change rules are inferred. Other entries need the model's complete
principal-part list.

A self-reference such as `@infl(megmi)` requires a registered model table.
A registered model can also be referenced without a dictionary entry. Supplied
principal parts adapt the example words in that table. Unknown references,
other cycles, duplicate target lemmas, and insufficient principal parts are
errors. The resolver caches completed models; `inflect` returns independent
copies of their tables.

Lexerat leaves `infl` uninterpreted. By default this engine recognizes its
registered model names and dictionary lemmas. Custom class labels can be
registered through the Python interface:

```python
engine = Inflector(entries, models={**MODELS, 'o-stem': Viros})
```

Import `MODELS` from `inflect` when extending the default registry.

## Tests

```bash
python -m unittest discover -s tests -v
```
